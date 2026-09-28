import re
import requests

from datetime import datetime
from typing import Optional, Dict, Any


class NotificationService:
    """
    Service responsible for sending hospital notifications
    through the n8n automation webhook.

    Python agents are responsible for deciding WHEN a
    notification is required.

    n8n is responsible for external communication such
    as sending the actual email.
    """

    def __init__(
        self,
        n8n_webhook_url: str,
        timeout: int = 10
    ):
        self.n8n_webhook_url = n8n_webhook_url
        self.timeout = timeout

    # ---------------------------------------------------------
    # Email validation
    # ---------------------------------------------------------

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Perform basic email format validation.
        """

        if not email:
            return False

        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

        return bool(re.match(pattern, email))

    # ---------------------------------------------------------
    # Build notification payload
    # ---------------------------------------------------------

    def build_payload(
        self,
        event_type: str,
        priority: str,
        patient_id: Optional[str],
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str,
        admission_id: Optional[int] = None,
        incident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build the standard notification payload
        that will be sent to n8n.
        """

        if not self.validate_email(recipient_email):
            raise ValueError(
                f"Invalid recipient email: {recipient_email}"
            )

        payload = {
            "event_type": event_type,
            "priority": priority,
            "patient_id": patient_id,
            "admission_id": admission_id,
            "incident_id": incident_id,
            "title": title,
            "recipient": {
                "type": "TEST_RECIPIENT",
                "email": recipient_email
            },
            "message": message,
            "source_agent": source_agent,
            "timestamp": datetime.now().isoformat()
        }

        return payload

    # ---------------------------------------------------------
    # Core notification method
    # ---------------------------------------------------------

    def send_notification(
        self,
        event_type: str,
        priority: str,
        patient_id: Optional[str],
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str,
        admission_id: Optional[int] = None,
        incident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a notification payload to the n8n webhook.

        This is the core method used internally by all
        hospital-specific notification methods.
        """

        payload = self.build_payload(
            event_type=event_type,
            priority=priority,
            patient_id=patient_id,
            title=title,
            message=message,
            recipient_email=recipient_email,
            source_agent=source_agent,
            admission_id=admission_id,
            incident_id=incident_id
        )

        try:

            response = requests.post(
                self.n8n_webhook_url,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            try:
                n8n_response = response.json()

            except ValueError:
                n8n_response = {
                    "raw_response": response.text
                }

            return {
                "success": True,
                "status": "SENT",
                "event_type": event_type,
                "recipient": recipient_email,
                "n8n_response": n8n_response
            }

        except requests.exceptions.Timeout:

            return {
                "success": False,
                "status": "FAILED",
                "error": "n8n webhook request timed out",
                "event_type": event_type,
                "recipient": recipient_email
            }

        except requests.exceptions.RequestException as e:

            return {
                "success": False,
                "status": "FAILED",
                "error": str(e),
                "event_type": event_type,
                "recipient": recipient_email
            }

        except Exception as e:

            return {
                "success": False,
                "status": "FAILED",
                "error": str(e),
                "event_type": event_type,
                "recipient": recipient_email
            }

    # ---------------------------------------------------------
    # Critical laboratory result notification
    # ---------------------------------------------------------

    def send_critical_lab_alert(
        self,
        patient_id: str,
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str = "ClinicalEscalationAgent",
        admission_id: Optional[int] = None,
        incident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a notification for a critical laboratory result.
        """

        return self.send_notification(
            event_type="CRITICAL_LAB_RESULT",
            priority="HIGH",
            patient_id=patient_id,
            title=title,
            message=message,
            recipient_email=recipient_email,
            source_agent=source_agent,
            admission_id=admission_id,
            incident_id=incident_id
        )

    # ---------------------------------------------------------
    # Emergency notification
    # ---------------------------------------------------------

    def send_emergency_alert(
        self,
        patient_id: str,
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str = "EmergencyAgent",
        admission_id: Optional[int] = None,
        incident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send an emergency-related notification.
        """

        return self.send_notification(
            event_type="EMERGENCY_ALERT",
            priority="URGENT",
            patient_id=patient_id,
            title=title,
            message=message,
            recipient_email=recipient_email,
            source_agent=source_agent,
            admission_id=admission_id,
            incident_id=incident_id
        )

    # ---------------------------------------------------------
    # Bed assignment notification
    # ---------------------------------------------------------

    def send_bed_assigned(
        self,
        patient_id: str,
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str = "BedAgent",
        admission_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a notification when a bed is successfully assigned.
        """

        return self.send_notification(
            event_type="BED_ASSIGNED",
            priority="NORMAL",
            patient_id=patient_id,
            title=title,
            message=message,
            recipient_email=recipient_email,
            source_agent=source_agent,
            admission_id=admission_id
        )

    # ---------------------------------------------------------
    # Staff assignment notification
    # ---------------------------------------------------------

    def send_staff_assigned(
        self,
        patient_id: str,
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str = "StaffAgent",
        admission_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a notification when a doctor or nurse
        is successfully assigned to an admission.
        """

        return self.send_notification(
            event_type="STAFF_ASSIGNED",
            priority="NORMAL",
            patient_id=patient_id,
            title=title,
            message=message,
            recipient_email=recipient_email,
            source_agent=source_agent,
            admission_id=admission_id
        )

    # ---------------------------------------------------------
    # Medication dispensed notification
    # ---------------------------------------------------------

    def send_medication_dispensed(
        self,
        patient_id: str,
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str = "PharmacyAgent",
        admission_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a notification when medication is dispensed.
        """

        return self.send_notification(
            event_type="MEDICATION_DISPENSED",
            priority="NORMAL",
            patient_id=patient_id,
            title=title,
            message=message,
            recipient_email=recipient_email,
            source_agent=source_agent,
            admission_id=admission_id
        )

    # ---------------------------------------------------------
    # Admission created notification
    # ---------------------------------------------------------

    def send_admission_created(
        self,
        patient_id: str,
        title: str,
        message: str,
        recipient_email: str,
        source_agent: str = "AdmissionAgent",
        admission_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a notification when a new admission is created.
        """

        return self.send_notification(
            event_type="ADMISSION_CREATED",
            priority="NORMAL",
            patient_id=patient_id,
            title=title,
            message=message,
            recipient_email=recipient_email,
            source_agent=source_agent,
            admission_id=admission_id
        )