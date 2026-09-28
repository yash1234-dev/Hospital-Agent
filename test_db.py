import sys
from pathlib import Path


# Ensure the project root is available when this script is run directly.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.config.settings import get_settings
from app.notifications.notification_service import NotificationService  # pyright: ignore[reportMissingImports]


settings = get_settings()

notification_service = NotificationService(
    n8n_webhook_url=settings.N8N_WEBHOOK_URL,
    timeout=settings.N8N_WEBHOOK_TIMEOUT
)


result = notification_service.send_critical_lab_alert(
    patient_id="test-patient-001",
    admission_id=651,
    title="Critical Laboratory Result",
    message="Test notification from ClinicalEscalationAgent.",
    recipient_email="yashkkalyani@gmail.com"
)


print("\nNotification Result:")
print(result)