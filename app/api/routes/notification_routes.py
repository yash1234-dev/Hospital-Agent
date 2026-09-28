from fastapi import APIRouter, HTTPException

from app.api.schemas.notification_schema import NotificationRequest
from app.config.settings import get_settings
from app.notifications.notification_service import NotificationService


router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"]
)


# ---------------------------------------------------------
# Application settings
# ---------------------------------------------------------

settings = get_settings()


# ---------------------------------------------------------
# Notification service
# ---------------------------------------------------------

notification_service = NotificationService(
    n8n_webhook_url=settings.N8N_WEBHOOK_URL,
    timeout=settings.N8N_WEBHOOK_TIMEOUT
)


# ---------------------------------------------------------
# Send notification
# ---------------------------------------------------------

@router.post("/send")
def send_notification(request: NotificationRequest):
    """
    Send a hospital notification through n8n.
    """

    result = notification_service.send_notification(
        event_type=request.event_type,
        priority=request.priority,
        patient_id=request.patient_id,
        title=request.title,
        message=request.message,
        recipient_email=request.recipient_email,
        source_agent=request.source_agent,
        admission_id=request.admission_id,
        incident_id=request.incident_id
    )

    if not result["success"]:
        raise HTTPException(
            status_code=502,
            detail=result
        )

    return result