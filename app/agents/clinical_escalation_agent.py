from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.clinical_escalation_tool import ClinicalEscalationTool

from app.config.settings import get_settings
from app.notifications.notification_service import NotificationService


class ClinicalEscalationAgent(BaseAgent):

    def __init__(self):
        super().__init__("ClinicalEscalationAgent")

        self.tool = ClinicalEscalationTool()

        settings = get_settings()

        self.notification_service = NotificationService(
            n8n_webhook_url=settings.N8N_WEBHOOK_URL,
            timeout=settings.N8N_WEBHOOK_TIMEOUT
        )

    def process(self, context: AgentContext) -> AgentResult:

        patient_id = context.patient_id

        if not patient_id:
            return AgentResult(
                status="FAILED",
                decision="ESCALATION_FAILED",
                reason="Patient ID is required for clinical escalation.",
                errors=["Missing patient_id"],
            )

        lab_order_id = context.data.get("lab_order_id")

        if not lab_order_id:
            return AgentResult(
                status="FAILED",
                decision="ESCALATION_FAILED",
                reason="Lab order ID is required for clinical escalation.",
                errors=["Missing lab_order_id"],
            )

        doctor_id = context.data.get("doctor_id")

        if not doctor_id:
            return AgentResult(
                status="FAILED",
                decision="ESCALATION_FAILED",
                reason="Doctor ID is required for clinical escalation.",
                errors=["Missing doctor_id"],
            )

        department_id = context.data.get("department_id")

        if not department_id:
            return AgentResult(
                status="FAILED",
                decision="ESCALATION_FAILED",
                reason="Department ID is required for clinical escalation.",
                errors=["Missing department_id"],
            )

        test_name = context.data.get("test_name")

        if not test_name:
            return AgentResult(
                status="FAILED",
                decision="ESCALATION_FAILED",
                reason="Test name is required for clinical escalation.",
                errors=["Missing test_name"],
            )

        try:

            # --------------------------------------------------
            # 1. Execute clinical escalation through gateway
            # --------------------------------------------------

            result = self.tool.escalate_critical_lab(
                patient_id=patient_id,
                lab_order_id=int(lab_order_id),
                doctor_id=int(doctor_id),
                department_id=int(department_id),
                test_name=test_name,
                result_value=context.data.get("result_value"),
                numeric_value=context.data.get("numeric_value"),
                unit=context.data.get("unit"),
                reference_range=context.data.get("reference_range"),
                message=context.data.get("message"),
                admission_id=context.admission_id,
                incident_id=context.incident_id,
            )

            if not result:
                return AgentResult(
                    status="FAILED",
                    decision="ESCALATION_FAILED",
                    reason="Clinical escalation returned no gateway result.",
                    errors=["Empty gateway result"],
                )

            if result.get("execution_status") != "COMPLETED":
                return AgentResult(
                    status="FAILED",
                    decision="ESCALATION_FAILED",
                    reason="Clinical escalation was not completed.",
                    data={
                        "gateway_result": result
                    },
                    errors=[
                        result.get(
                            "error_message",
                            "Gateway execution failed."
                        )
                    ],
                )

            # --------------------------------------------------
            # 2. Record agent action
            # --------------------------------------------------

            context.add_action(
                {
                    "action": "CLINICAL_ESCALATION",
                    "gateway_request_id": result.get(
                        "gateway_request_id"
                    ),
                    "lab_order_id": lab_order_id,
                    "doctor_id": doctor_id,
                }
            )

            # --------------------------------------------------
            # 3. Send notification email
            # --------------------------------------------------

            recipient_email = context.data.get("recipient_email")

            if recipient_email:

                notification_result = (
                    self.notification_service.send_critical_lab_alert(
                        patient_id=patient_id,
                        admission_id=context.admission_id,
                        incident_id=context.incident_id,
                        title="Critical Laboratory Result",
                        message=(
                            context.data.get("message")
                            or
                            f"Critical laboratory result for "
                            f"{test_name} requires immediate clinical review."
                        ),
                        recipient_email=recipient_email,
                        source_agent="ClinicalEscalationAgent",
                    )
                )

            else:

                notification_result = {
                    "success": False,
                    "status": "SKIPPED",
                    "reason": (
                        "No recipient_email was provided "
                        "in AgentContext."
                    )
                }

            # --------------------------------------------------
            # 4. Return final agent result
            # --------------------------------------------------

            return AgentResult(
                status="SUCCESS",
                decision="ESCALATION_COMPLETED",
                reason=(
                    "Critical laboratory result was successfully "
                    "escalated for clinical review."
                ),
                data={
                    "gateway_result": result,
                    "lab_order_id": lab_order_id,
                    "doctor_id": doctor_id,
                    "notification_result": notification_result,
                },
                actions=[
                    "CLINICAL_ESCALATION"
                ],
            )

        except Exception as exc:

            return AgentResult(
                status="FAILED",
                decision="ESCALATION_FAILED",
                reason="Clinical escalation execution failed.",
                errors=[str(exc)],
            )