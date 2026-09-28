from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.emergency_tool import EmergencyTool

from app.config.settings import get_settings
from app.notifications.notification_service import NotificationService


class EmergencyAgent(BaseAgent):
    """
    Agent responsible for executing emergency operational actions.

    Current supported action:
        REQUEST_TRANSPORT

    Architecture:

        EmergencyAgent
            ↓
        EmergencyTool
            ↓
        ActionGateway
            ↓
        Stored Procedure / Database
    """

    SUPPORTED_DECISIONS = {
        "REQUEST_TRANSPORT",
    }

    def __init__(
        self,
        emergency_tool: EmergencyTool | None = None,
    ) -> None:
        super().__init__(agent_name="EmergencyAgent")

        self.emergency_tool = emergency_tool or EmergencyTool()

        settings = get_settings()

        self.notification_service = NotificationService(
            n8n_webhook_url=settings.N8N_WEBHOOK_URL,
            timeout=settings.N8N_WEBHOOK_TIMEOUT,
        )

    def process(self, context: AgentContext) -> AgentResult:
        """
        Execute the emergency action requested by the workflow.
        """

        # ---------------------------------------------------------
        # 1. Validate context
        # ---------------------------------------------------------

        if context is None:
            return AgentResult(
                status="FAILED",
                reason="AgentContext cannot be None.",
            )

        if context.incident_id is None:
            return AgentResult(
                status="FAILED",
                reason="Incident ID is required for EmergencyAgent.",
            )

        # ---------------------------------------------------------
        # 2. Validate the requested decision
        # ---------------------------------------------------------

        decision = None

        if context.decisions:
            latest_decision = context.decisions[-1]

            if isinstance(latest_decision, dict):
                decision = latest_decision.get("decision")

        if decision is None:
            return AgentResult(
                status="FAILED",
                reason=(
                    "EmergencyAgent requires a decision in AgentContext."
                ),
            )

        if decision not in self.SUPPORTED_DECISIONS:
            return AgentResult(
                status="FAILED",
                reason=(
                    f"EmergencyAgent does not support decision: "
                    f"{decision}"
                ),
            )

        # ---------------------------------------------------------
        # 3. Execute REQUEST_TRANSPORT through EmergencyTool
        # ---------------------------------------------------------

        tool_result = self.emergency_tool.run(
            operation="request_transport",
            incident_id=context.incident_id,
            requested_by_agent="EmergencyAgent",
        )

        # ---------------------------------------------------------
        # 4. Validate tool result
        # ---------------------------------------------------------

        if not tool_result:
            return AgentResult(
                status="FAILED",
                decision=decision,
                reason=(
                    "EmergencyTool returned an empty result "
                    "for REQUEST_TRANSPORT."
                ),
            )

        # ---------------------------------------------------------
        # 5. Determine whether the gateway action succeeded
        # ---------------------------------------------------------

        execution_status = tool_result.get("execution_status")

        if execution_status != "COMPLETED":
            error_message = tool_result.get(
                "error_message",
                "Emergency transport request failed.",
            )

            return AgentResult(
                status="FAILED",
                decision=decision,
                reason=error_message,
                data=tool_result,
                actions=[],
            )

        # ---------------------------------------------------------
        # 6. Record completed action in shared context
        # ---------------------------------------------------------

        context.add_action(
            {
                "agent": "EmergencyAgent",
                "action": "REQUEST_TRANSPORT",
                "status": "COMPLETED",
                "incident_id": context.incident_id,
            }
        )

        # ---------------------------------------------------------
        # 7. Send emergency notification
        # ---------------------------------------------------------

        recipient_email = context.data.get("recipient_email")

        if recipient_email:

            notification_result = (
                self.notification_service.send_emergency_alert(
                    patient_id=context.patient_id,
                    admission_id=context.admission_id,
                    incident_id=context.incident_id,
                    title="Emergency Transport Requested",
                    message=(
                        context.data.get("message")
                        or
                        (
                            f"Emergency transport has been requested "
                            f"for incident {context.incident_id}."
                        )
                    ),
                    recipient_email=recipient_email,
                    source_agent="EmergencyAgent",
                )
            )

        else:

            notification_result = {
                "success": False,
                "status": "SKIPPED",
                "reason": (
                    "No recipient_email was provided "
                    "in AgentContext."
                ),
            }

        # ---------------------------------------------------------
        # 8. Return successful AgentResult
        # ---------------------------------------------------------

        return AgentResult(
            status="SUCCESS",
            decision="ASSIGN_BED",
            reason=(
                f"Emergency transport successfully requested "
                f"for incident {context.incident_id}."
            ),
            data={
                "gateway_result": tool_result,
                "notification_result": notification_result,
            },
            actions=[
                {
                    "agent": "EmergencyAgent",
                    "action": "REQUEST_TRANSPORT",
                    "status": "COMPLETED",
                    "incident_id": context.incident_id,
                }
            ],
        )