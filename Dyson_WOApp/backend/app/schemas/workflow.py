from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class EmailDateExtractionRequest(BaseModel):
    """Request to extract date from email and update work order"""
    email_subject: str = Field(..., min_length=1, description="Email subject containing WO number")
    email_body: str = Field(..., min_length=10, description="Email body text")


class EmailDateExtractionResponse(BaseModel):
    """Response after extracting date and updating work order"""
    status: str = Field(..., description="'Success' or 'Error'")
    wo_number: Optional[str] = Field(None, description="Work order number found")
    wo_id: Optional[int] = Field(None, description="Work order database ID")
    extracted_date: Optional[date] = Field(None, description="Date extracted by AI")
    confidence: Optional[float] = Field(None, description="AI confidence score (0.0-1.0)")
    message: str = Field(..., description="Human-readable message")
    updated: bool = Field(False, description="Whether work order was updated")
