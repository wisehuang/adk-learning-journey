from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class Attendee(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class MeetingRequest(BaseModel):
    summary: str
    start_time: datetime
    duration_minutes: int = Field(gt=0, le=480)  # Max 8 hours
    attendees: List[Attendee]
    description: Optional[str] = None
    location: Optional[str] = None

class MeetingResponse(BaseModel):
    status: str
    event_id: Optional[str] = None
    message: Optional[str] = None
    conflicts: Optional[List[str]] = None
    alternative_times: Optional[List[datetime]] = None

class ValidationResponse(BaseModel):
    valid: bool
    invalid_emails: Optional[List[str]] = None
    message: Optional[str] = None 