from typing import Optional

from pydantic import BaseModel, EmailStr


class NotificationRequest(BaseModel):
    """
    Request model used by the FastAPI notification endpoint.
    """

    event_type: str
    priority: str

    patient_id: Optional[str] = None
    admission_id: Optional[int] = None
    incident_id: Optional[int] = None

    title: str
    message: str

    recipient_email: EmailStr

    source_agent: str