from typing import Any, Dict, Optional

from app.gateway.action_gateway import ActionGateway


class ClinicalEscalationTool:

    def __init__(self):
        self.gateway = ActionGateway()

    def escalate_critical_lab(
        self,
        patient_id: str,
        lab_order_id: int,
        doctor_id: int,
        department_id: int,
        test_name: str,
        result_value: Optional[str] = None,
        numeric_value: Optional[float] = None,
        unit: Optional[str] = None,
        reference_range: Optional[str] = None,
        message: Optional[str] = None,
        admission_id: Optional[int] = None,
        incident_id: Optional[int] = None,
    ) -> Dict[str, Any]:

        payload = {
            "doctor_id": doctor_id,
            "department_id": department_id,
            "test_name": test_name,
            "result_value": result_value,
            "numeric_value": numeric_value,
            "unit": unit,
            "reference_range": reference_range,
            "message": message,
        }

        gateway_request_id = self.gateway.create_request(
            action_type="CLINICAL_ESCALATION",
            requested_by_agent="ClinicalEscalationAgent",
            request_payload=payload,
            patient_id=patient_id,
            admission_id=admission_id,
            incident_id=incident_id,
            target_type="LAB_ORDER",
            target_id=str(lab_order_id),
        )

        result = self.gateway.execute_action(
            gateway_request_id
        )

        return result