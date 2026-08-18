from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..services.ai_service import AIService
from ..services.machine_service import MachineService
from ..schemas.ai_decision import (
    AIDecisionResponse,
    AIDecisionRequest
)

router = APIRouter()


@router.post("/decision/{machine_id}", response_model=AIDecisionResponse)
async def get_ai_decision(
    machine_id: int,
    request_data: Optional[AIDecisionRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Get AI decision for a specific machine's preventive maintenance.

    This endpoint analyzes machine data, maintenance history, and existing work orders
    to provide an AI-recommended action.

    - **machine_id**: Database ID of the machine
    - **force_decision**: Optional flag to force new decision even if recent one exists

    Returns AI decision with:
    - decision: CREATE_WORK_ORDER, WAIT, or SEND_NOTIFICATION
    - priority: Low, Medium, or High
    - confidence: 0.0 to 1.0
    - explanation: Human-readable explanation
    """
    # Verify machine exists
    machine_service = MachineService(db)
    machine = machine_service.get_machine_by_id(machine_id)

    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found"
        )

    # Create AI service and get decision
    ai_service = AIService(db)

    try:
        result = await ai_service.make_decision(machine_id)

        ai_decision = result["ai_decision"]

        # Add additional metadata to response
        response_data = AIDecisionResponse.model_validate(ai_decision)

        return response_data

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating AI decision: {str(e)}"
        )


@router.post("/decision/{ai_decision_id}/execute")
async def execute_ai_decision(
    ai_decision_id: int,
    force: bool = Query(False, description="Force execution even if confidence is low"),
    db: Session = Depends(get_db)
):
    """
    Execute an AI decision (create work order, send notification, etc.).

    - **ai_decision_id**: Database ID of the AI decision
    - **force**: Force execution even if confidence is below threshold

    Returns execution results including created work order or notification status.
    """
    ai_service = AIService(db)

    try:
        result = await ai_service.execute_decision(ai_decision_id, force=force)

        return {
            "success": True,
            "ai_decision_id": ai_decision_id,
            **result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing AI decision: {str(e)}"
        )


@router.get("/decisions/recent", response_model=List[AIDecisionResponse])
async def get_recent_decisions(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of decisions"),
    machine_id: Optional[int] = Query(None, description="Filter by machine ID"),
    db: Session = Depends(get_db)
):
    """
    Get recent AI decisions for audit purposes.

    - **limit**: Maximum number of decisions to return (1-100)
    - **machine_id**: Optional filter by machine ID

    Returns list of recent AI decisions ordered by creation date (newest first).
    """
    ai_service = AIService(db)

    decisions = ai_service.get_recent_decisions(limit=limit, machine_id=machine_id)

    return [AIDecisionResponse.model_validate(d) for d in decisions]


@router.get("/decisions/{ai_decision_id}", response_model=AIDecisionResponse)
async def get_ai_decision_by_id(
    ai_decision_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific AI decision by ID.

    - **ai_decision_id**: Database ID of the AI decision

    Returns the AI decision details including input context and raw response.
    """
    from ..models.ai_decision import AIDecision

    ai_decision = db.query(AIDecision).filter(AIDecision.id == ai_decision_id).first()

    if not ai_decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI decision with ID {ai_decision_id} not found"
        )

    return AIDecisionResponse.model_validate(ai_decision)


@router.get("/statistics")
async def get_ai_statistics(
    db: Session = Depends(get_db)
):
    """
    Get statistics about AI decisions.

    Returns:
    - Total decisions made
    - Decisions by type (CREATE_WORK_ORDER, WAIT, SEND_NOTIFICATION)
    - Average confidence score
    - Decisions requiring review
    - Auto-executed vs manual review
    """
    from ..models.ai_decision import AIDecision
    from sqlalchemy import func

    # Total decisions
    total_decisions = db.query(func.count(AIDecision.id)).scalar()

    # Decisions by type
    decisions_by_type = (
        db.query(AIDecision.decision, func.count(AIDecision.id))
        .group_by(AIDecision.decision)
        .all()
    )

    # Average confidence
    avg_confidence = db.query(func.avg(AIDecision.confidence)).scalar() or 0.0

    # Decisions requiring review
    requiring_review = (
        db.query(func.count(AIDecision.id))
        .filter(AIDecision.requires_review == True)
        .scalar()
    )

    # Auto-executed decisions
    auto_executed = (
        db.query(func.count(AIDecision.id))
        .filter(AIDecision.auto_executed == True)
        .scalar()
    )

    # Provider distribution
    provider_distribution = (
        db.query(AIDecision.llm_provider, func.count(AIDecision.id))
        .group_by(AIDecision.llm_provider)
        .all()
    )

    return {
        "total_decisions": total_decisions,
        "decisions_by_type": dict(decisions_by_type),
        "average_confidence": round(float(avg_confidence), 2),
        "requiring_review": requiring_review,
        "auto_executed": auto_executed,
        "manual_review": total_decisions - auto_executed,
        "provider_distribution": dict(provider_distribution)
    }
