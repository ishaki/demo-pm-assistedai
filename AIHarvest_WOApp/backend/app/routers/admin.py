"""
Admin endpoints backing the demo reset page at /demo-reset.

POST /demo-reset deletes every machine, work order, AI decision, maintenance
record and workflow log, then reseeds the demo estate. There is no other
authentication in this application, so the guard below is the whole of it --
see require_demo_reset_token.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging
import secrets
import time

from ..config import get_settings
from ..database import get_db
from ..schemas.demo_reset import (
    DemoResetDefaults,
    DemoResetRequest,
    DemoResetResponse,
)
from ..services import demo_seed_service
from ..services.demo_seed_service import DemoSeedConfig

logger = logging.getLogger(__name__)

router = APIRouter()

# The header the page sends. Not Authorization: this is a shared demo
# passphrase, not a bearer token belonging to anyone, and putting it under its
# own name keeps it out of the way of any real auth added later.
TOKEN_HEADER = "X-Demo-Reset-Token"


def require_demo_reset_token(
    x_demo_reset_token: Optional[str] = Header(None, alias=TOKEN_HEADER),
) -> None:
    """
    Three gates, in the order a misconfiguration is most likely:

      403  DEMO_RESET_ENABLED=False. The endpoint is inert -- what a deployment
           that must never be wiped sets.
      503  Enabled but DEMO_RESET_TOKEN is blank. Refusing is deliberate: the
           alternative is an unauthenticated endpoint that deletes the database,
           reachable by anyone who guesses the URL.
      401  Token missing or wrong.

    Nothing here is rate limited. The passphrase is the only thing stopping a
    caller who has found the URL, so make it long.
    """
    settings = get_settings()

    if not settings.DEMO_RESET_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo reset is disabled on this deployment "
                   "(DEMO_RESET_ENABLED=False).",
        )

    configured = settings.DEMO_RESET_TOKEN or ""
    if not configured:
        logger.error(
            "Demo reset is enabled but DEMO_RESET_TOKEN is not set -- refusing "
            "the request rather than leaving the endpoint open."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo reset is enabled but no DEMO_RESET_TOKEN is "
                   "configured, so the endpoint refuses every request. Set one "
                   "in the backend environment and restart.",
        )

    supplied = x_demo_reset_token or ""
    # compare_digest over == so a wrong token cannot be recovered a character
    # at a time from response timing.
    if not secrets.compare_digest(supplied, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing or incorrect {TOKEN_HEADER}.",
        )


@router.get(
    "/demo-reset/defaults",
    response_model=DemoResetDefaults,
    dependencies=[Depends(require_demo_reset_token)],
)
def get_demo_reset_defaults(db: Session = Depends(get_db)):
    """
    Prefill values for the reset page, plus current row counts.

    Behind the same guard as the reset itself: it returns the configured
    notification addresses, and the page uses a successful call here to check
    the passphrase before showing the form.
    """
    config = DemoSeedConfig.defaults()

    return DemoResetDefaults(
        admin_email=config.admin_email,
        supplier_email=config.supplier_email,
        machine_count=config.machine_count,
        reserve_overdue_without_wo=config.reserve_overdue_without_wo,
        status_counts=config.status_counts,
        current_row_counts=demo_seed_service.current_row_counts(db),
    )


@router.post(
    "/demo-reset",
    response_model=DemoResetResponse,
    dependencies=[Depends(require_demo_reset_token)],
)
def run_demo_reset(
    request: DemoResetRequest,
    db: Session = Depends(get_db),
):
    """
    Reset the demo database and reseed it.

    **DESTRUCTIVE.** Deletes every row from machines, maintenance_history,
    work_orders, ai_decisions and workflow_logs, then builds a fresh estate from
    the supplied numbers. One transaction: a failure part way through rolls back
    and changes nothing.

    workflow_logs is always cleared here, so a reset is a genuinely clean slate
    with no run history from earlier rehearsals. The CLI seed scripts leave that
    table alone, which is the behaviour they have always had.

    Creates no schema -- the tables must already exist.
    """
    config = DemoSeedConfig(
        admin_email=str(request.admin_email),
        supplier_email=str(request.supplier_email),
        machine_count=request.machine_count,
        reserve_overdue_without_wo=request.reserve_overdue_without_wo,
        status_counts=request.status_counts(),
    )

    logger.warning(
        "Demo reset requested: %d machines, %d work orders, admin=%s",
        config.machine_count, config.total_order_count, config.admin_email,
    )

    started = time.monotonic()
    try:
        result = demo_seed_service.reset_and_seed(
            db, config, clear_workflow_logs=True
        )
    except ValueError as exc:
        # The schema validator catches this first for anything the page sends.
        # Reachable by a caller posting past it, so it answers 422 rather than
        # surfacing as a 500.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    elapsed = time.monotonic() - started

    return DemoResetResponse(
        machines=result.machines,
        maintenance_history=result.maintenance_history,
        work_orders=result.work_orders,
        ai_decisions=result.ai_decisions,
        workflow_logs=result.workflow_logs,
        work_orders_by_status=result.work_orders_by_status,
        machines_by_pm_status=result.machines_by_pm_status,
        ai_sourced_orders=result.ai_sourced_orders,
        decisions_below_threshold=result.decisions_below_threshold,
        overdue_machines_without_open_wo=result.overdue_machines_without_open_wo,
        workflow_logs_cleared=result.workflow_logs_cleared,
        elapsed_seconds=round(elapsed, 2),
    )
