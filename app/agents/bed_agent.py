from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.bed_tool import BedTool

from app.config.settings import get_settings
from app.notifications.notification_service import NotificationService


class BedAgent(BaseAgent):
    """
    Agent responsible for selecting and reserving
    an available hospital bed for a patient.
    """

    def __init__(
        self,
        bed_tool: BedTool | None = None,
    ) -> None:

        super().__init__(
            agent_name="BedAgent",
        )

        self.bed_tool = (
            bed_tool if bed_tool is not None else BedTool()
        )

        settings = get_settings()

        self.notification_service = NotificationService(
            n8n_webhook_url=settings.N8N_WEBHOOK_URL,
            timeout=settings.N8N_WEBHOOK_TIMEOUT,
        )

    def process(
        self,
        context: AgentContext,
    ) -> AgentResult:

        # ---------------------------------------------------------
        # 1. Validate context
        # ---------------------------------------------------------

        if context is None:
            raise ValueError("AgentContext cannot be None.")

        if not context.patient_id:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Patient ID is required for bed reservation.",
                data={},
                actions=[],
            )

        if not context.admission_id:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Admission ID is required for bed reservation.",
                data={},
                actions=[],
            )

        # ---------------------------------------------------------
        # 2. Retrieve available beds
        # ---------------------------------------------------------

        available_beds = self.bed_tool.run(
            operation="get_available_beds",
            department_id=context.department_id,
        )

        if not isinstance(available_beds, list):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="BedTool returned an invalid available-bed response.",
                data={
                    "available_beds": available_beds
                },
                actions=[],
            )

        # ---------------------------------------------------------
        # 3. No available bed
        # ---------------------------------------------------------

        if not available_beds:
            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason="No suitable available bed was found.",
                data={
                    "available_beds": [],
                },
                actions=[],
            )

        # ---------------------------------------------------------
        # 4. Select first available bed
        # ---------------------------------------------------------

        selected_bed = available_beds[0]

        if "bed_id" not in selected_bed:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Available bed record does not contain bed_id.",
                data={
                    "available_beds": available_beds,
                },
                actions=[],
            )

        bed_id = int(selected_bed["bed_id"])

        # ---------------------------------------------------------
        # 5. Reserve selected bed
        # ---------------------------------------------------------

        tool_result = self.bed_tool.run(
            operation="reserve_bed",
            bed_id=bed_id,
            patient_id=context.patient_id,
            admission_id=context.admission_id,
            requested_by_agent="BedAgent",
        )

        # ---------------------------------------------------------
        # 6. Validate gateway result
        # ---------------------------------------------------------

        if not isinstance(tool_result, dict):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="BedTool returned an invalid reservation response.",
                data={
                    "bed": selected_bed,
                    "tool_result": tool_result,
                },
                actions=[],
            )

        if tool_result.get("execution_status") != "COMPLETED":
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    tool_result.get("error_message")
                    or "Bed reservation failed."
                ),
                data={
                    "bed": selected_bed,
                    "tool_result": tool_result,
                },
                actions=[],
            )

        # ---------------------------------------------------------
        # 7. Record successful action in shared context
        # ---------------------------------------------------------

        action = {
            "agent": "BedAgent",
            "action": "RESERVE_BED",
            "status": "COMPLETED",
            "bed_id": bed_id,
            "patient_id": context.patient_id,
            "admission_id": context.admission_id,
        }

        context.add_action(action)

        reserved_bed = dict(selected_bed)

        reserved_bed["bed_status"] = "RESERVED"
        reserved_bed["patient_id"] = context.patient_id
        reserved_bed["admission_id"] = context.admission_id

        context.add_data(
            "reserved_bed",
            reserved_bed,
        )

        # ---------------------------------------------------------
        # 8. Send bed-assigned notification
        # ---------------------------------------------------------

        recipient_email = context.data.get(
            "recipient_email"
        )

        if recipient_email:

            notification_result = (
                self.notification_service.send_bed_assigned(
                    patient_id=context.patient_id,
                    admission_id=context.admission_id,
                    title="Hospital Bed Assigned",
                    message=(
                        context.data.get("message")
                        or
                        (
                            f"Bed {bed_id} has been successfully "
                            f"reserved for patient "
                            f"{context.patient_id}."
                        )
                    ),
                    recipient_email=recipient_email,
                    source_agent="BedAgent",
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
        # 9. Return result
        # ---------------------------------------------------------

        return AgentResult(
            status="SUCCESS",
            decision="ASSIGN_DOCTOR",
            reason=(
                f"Bed {bed_id} successfully reserved "
                f"for patient {context.patient_id}."
            ),
            data={
                "bed": selected_bed,
                "reservation": tool_result,
                "notification_result": notification_result,
            },
            actions=[
                action
            ],
        )