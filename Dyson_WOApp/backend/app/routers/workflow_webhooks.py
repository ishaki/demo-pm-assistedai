from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
import re
import logging

from ..database import get_db
from ..services.work_order_service import WorkOrderService
from ..services.date_extraction_service import DateExtractionService
from ..schemas.workflow import EmailDateExtractionRequest, EmailDateExtractionResponse
from ..schemas.work_order import WorkOrderUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


def extract_wo_number_from_subject(subject: str) -> Optional[str]:
    """
    Extract work order number from email subject.

    Pattern: WO-YYYY-NNNN (e.g., WO-2024-001, WO-2024-0123)

    Args:
        subject: Email subject line

    Returns:
        Work order number or None
    """
    # Pattern: WO- followed by 4 digits, hyphen, 3-4 digits
    match = re.search(r'WO-\d{4}-\d{3,4}', subject, re.IGNORECASE)
    if match:
        return match.group(0).upper()  # Normalize to uppercase
    return None


def validate_scheduled_date(date_str: str) -> tuple[Optional[date], Optional[str]]:
    """
    Validate and parse scheduled date.

    Args:
        date_str: Date string in ISO format (YYYY-MM-DD)

    Returns:
        Tuple of (parsed_date, error_message)
    """
    try:
        parsed_date = datetime.fromisoformat(date_str).date()

        # Check if date is in the past
        today = datetime.now().date()
        if parsed_date < today:
            return None, f"Date {parsed_date} is in the past"

        return parsed_date, None

    except (ValueError, TypeError) as e:
        return None, f"Invalid date format: {str(e)}"


@router.post("/email-date-extraction", response_model=EmailDateExtractionResponse)
async def extract_date_from_email(
    request: EmailDateExtractionRequest,
    db: Session = Depends(get_db)
):
    """
    Extract scheduled date from email and update work order.

    This endpoint is designed to be called by workflow systems (like n8n)
    when a supplier replies with a scheduled maintenance date.

    **Example Request:**
    ```json
    {
      "email_subject": "RE: Work Order WO-2024-001",
      "email_body": "We can schedule the maintenance for January 15, 2024..."
    }
    ```

    **Example Success Response:**
    ```json
    {
      "status": "Success",
      "wo_number": "WO-2024-001",
      "wo_id": 123,
      "extracted_date": "2024-01-15",
      "confidence": 0.95,
      "message": "Work order WO-2024-001 scheduled date updated to 2024-01-15",
      "updated": true
    }
    ```

    **Validation:**
    - Work order must exist
    - Work order status must be "Approved"
    - AI confidence must be >= 0.7
    - Extracted date must not be in the past
    """
    logger.info(f"Email date extraction request: {request.email_subject[:50]}...")

    try:
        # 1. Extract WO number from subject
        wo_number = extract_wo_number_from_subject(request.email_subject)
        if not wo_number:
            return EmailDateExtractionResponse(
                status="Error",
                message="No work order number found in email subject"
            )

        # 2. Find work order
        wo_service = WorkOrderService(db)
        work_order = wo_service.get_work_order_by_wo_number(wo_number)

        if not work_order:
            return EmailDateExtractionResponse(
                status="Error",
                wo_number=wo_number,
                message=f"Work order {wo_number} not found"
            )

        # 3. Validate work order status
        if work_order.status != "Approved":
            return EmailDateExtractionResponse(
                status="Error",
                wo_number=wo_number,
                wo_id=work_order.id,
                message=f"Work order status is '{work_order.status}', must be 'Approved'"
            )

        # 4. Extract date using AI
        date_service = DateExtractionService()
        extraction_result = await date_service.extract_date_from_email(request.email_body)

        selected_date_str = extraction_result.get("selected_date")
        confidence = extraction_result.get("confidence", 0.0)
        explanation = extraction_result.get("explanation", "")

        # 5. Validate confidence
        if confidence < 0.7:
            return EmailDateExtractionResponse(
                status="Error",
                wo_number=wo_number,
                wo_id=work_order.id,
                confidence=confidence,
                message=f"AI confidence too low ({confidence:.2f}). {explanation}"
            )

        # 6. Validate and parse date
        if not selected_date_str:
            return EmailDateExtractionResponse(
                status="Error",
                wo_number=wo_number,
                wo_id=work_order.id,
                confidence=confidence,
                message="No date extracted from email"
            )

        parsed_date, error = validate_scheduled_date(selected_date_str)
        if error:
            return EmailDateExtractionResponse(
                status="Error",
                wo_number=wo_number,
                wo_id=work_order.id,
                confidence=confidence,
                message=error
            )

        # 7. Update work order
        wo_update = WorkOrderUpdate(scheduled_date=parsed_date)
        updated_wo = wo_service.update_work_order(work_order.id, wo_update)

        if not updated_wo:
            return EmailDateExtractionResponse(
                status="Error",
                wo_number=wo_number,
                wo_id=work_order.id,
                message="Failed to update work order"
            )

        # 8. Success!
        logger.info(f"Updated {wo_number} scheduled_date to {parsed_date}")
        return EmailDateExtractionResponse(
            status="Success",
            wo_number=wo_number,
            wo_id=work_order.id,
            extracted_date=parsed_date,
            confidence=confidence,
            message=f"Work order {wo_number} scheduled date updated to {parsed_date}",
            updated=True
        )

    except Exception as e:
        logger.error(f"Error in email date extraction: {e}")
        return EmailDateExtractionResponse(
            status="Error",
            message=f"Internal error: {str(e)}"
        )
