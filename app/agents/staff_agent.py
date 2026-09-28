from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.staff_tool import StaffTool

from app.config.settings import get_settings
from app.notifications.notification_service import NotificationService


class StaffAgent(BaseAgent):
    """
    Agent responsible for assigning doctors and nurses
    to an active hospital admission.
    """

    def __init__(
        self,
        staff_tool: StaffTool | None = None,
    ) -> None:

        super().__init__(
            agent_name="StaffAgent",
        )

        self.staff_tool = (
            staff_tool
            if staff_tool is not None
            else StaffTool()
        )

        # ---------------------------------------------------------
        # Notification Service
        # ---------------------------------------------------------

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
        # Validate context
        # ---------------------------------------------------------

        if context is None:
            raise ValueError("AgentContext cannot be None.")

        if context.admission_id is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Admission ID is required for staff assignment.",
                data={},
                actions=[],
            )

        if context.admission_id <= 0:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Admission ID must be a positive integer.",
                data={},
                actions=[],
            )

        # ---------------------------------------------------------
        # Validate latest decision
        # ---------------------------------------------------------

        if not context.decisions:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="No staff assignment decision was provided.",
                data={},
                actions=[],
            )

        latest_decision = context.decisions[-1]

        if not isinstance(latest_decision, dict):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Latest decision must be a dictionary.",
                data={},
                actions=[],
            )

        decision = latest_decision.get("decision")

        if decision not in {
            "ASSIGN_DOCTOR",
            "ASSIGN_NURSE",
        }:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    f"Unsupported StaffAgent decision: {decision}"
                ),
                data={
                    "decision": decision,
                },
                actions=[],
            )

        # =========================================================
        # ASSIGN DOCTOR
        # =========================================================

        if decision == "ASSIGN_DOCTOR":

            available_doctors = self.staff_tool.run(
                operation="get_available_doctors",
                department_id=context.department_id,
            )

            if not isinstance(available_doctors, list):
                return AgentResult(
                    status="FAILED",
                    decision="NO_ACTION",
                    reason=(
                        "StaffTool returned an invalid doctor response."
                    ),
                    data={
                        "available_doctors": available_doctors,
                    },
                    actions=[],
                )

            if not available_doctors:
                return AgentResult(
                    status="SUCCESS",
                    decision="NO_ACTION",
                    reason="No available doctor was found.",
                    data={
                        "available_doctors": [],
                    },
                    actions=[],
                )

            selected_doctor = available_doctors[0]

            if "doctor_id" not in selected_doctor:
                return AgentResult(
                    status="FAILED",
                    decision="NO_ACTION",
                    reason=(
                        "Available doctor record does not contain doctor_id."
                    ),
                    data={
                        "doctor": selected_doctor,
                    },
                    actions=[],
                )

            doctor_id = int(selected_doctor["doctor_id"])

            # -----------------------------------------------------
            # Assign doctor through StaffTool / ActionGateway
            # -----------------------------------------------------

            tool_result = self.staff_tool.run(
                operation="assign_doctor",
                admission_id=context.admission_id,
                doctor_id=doctor_id,
                requested_by_agent="StaffAgent",
            )

            if not isinstance(tool_result, dict):
                return AgentResult(
                    status="FAILED",
                    decision="NO_ACTION",
                    reason="Invalid doctor assignment response.",
                    data={
                        "doctor": selected_doctor,
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
                        or "Doctor assignment failed."
                    ),
                    data={
                        "doctor": selected_doctor,
                        "tool_result": tool_result,
                    },
                    actions=[],
                )

            # -----------------------------------------------------
            # Record completed action
            # -----------------------------------------------------

            action = {
                "agent": "StaffAgent",
                "action": "ASSIGN_DOCTOR",
                "status": "COMPLETED",
                "admission_id": context.admission_id,
                "doctor_id": doctor_id,
            }

            context.add_action(action)

            context.add_data(
                "assigned_doctor",
                selected_doctor,
            )

            # -----------------------------------------------------
            # Send notification
            # -----------------------------------------------------

            recipient_email = context.data.get("recipient_email")

            if recipient_email:

                notification_result = (
                    self.notification_service.send_staff_assigned(
                        patient_id=context.patient_id,
                        title="Doctor Assigned",
                        message=(
                            context.data.get("message")
                            or (
                                f"Doctor {doctor_id} has been successfully "
                                f"assigned to admission "
                                f"{context.admission_id}."
                            )
                        ),
                        recipient_email=recipient_email,
                        source_agent="StaffAgent",
                        admission_id=context.admission_id,
                    )
                )

            else:

                notification_result = {
                    "success": False,
                    "status": "SKIPPED",
                    "reason": (
                        "No recipient_email was provided in AgentContext."
                    ),
                }

            # -----------------------------------------------------
            # Return doctor assignment result
            # -----------------------------------------------------

            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason=(
                    f"Doctor {doctor_id} successfully assigned "
                    f"to admission {context.admission_id}."
                ),
                data={
                    "doctor": selected_doctor,
                    "assignment": tool_result,
                    "notification_result": notification_result,
                },
                actions=[action],
            )

        # =========================================================
        # ASSIGN NURSE
        # =========================================================

        available_nurses = self.staff_tool.run(
            operation="get_available_nurses",
            department_id=context.department_id,
        )

        if not isinstance(available_nurses, list):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "StaffTool returned an invalid nurse response."
                ),
                data={
                    "available_nurses": available_nurses,
                },
                actions=[],
            )

        if not available_nurses:
            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason="No available nurse was found.",
                data={
                    "available_nurses": [],
                },
                actions=[],
            )

        selected_nurse = available_nurses[0]

        if "nurse_id" not in selected_nurse:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "Available nurse record does not contain nurse_id."
                ),
                data={
                    "nurse": selected_nurse,
                },
                actions=[],
            )

        nurse_id = int(selected_nurse["nurse_id"])

        # ---------------------------------------------------------
        # Assign nurse through StaffTool / ActionGateway
        # ---------------------------------------------------------

        tool_result = self.staff_tool.run(
            operation="assign_nurse",
            admission_id=context.admission_id,
            nurse_id=nurse_id,
            requested_by_agent="StaffAgent",
        )

        if not isinstance(tool_result, dict):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Invalid nurse assignment response.",
                data={
                    "nurse": selected_nurse,
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
                    or "Nurse assignment failed."
                ),
                data={
                    "nurse": selected_nurse,
                    "tool_result": tool_result,
                },
                actions=[],
            )

        # ---------------------------------------------------------
        # Record completed action
        # ---------------------------------------------------------

        action = {
            "agent": "StaffAgent",
            "action": "ASSIGN_NURSE",
            "status": "COMPLETED",
            "admission_id": context.admission_id,
            "nurse_id": nurse_id,
        }

        context.add_action(action)

        context.add_data(
            "assigned_nurse",
            selected_nurse,
        )

        # ---------------------------------------------------------
        # Send notification
        # ---------------------------------------------------------

        recipient_email = context.data.get("recipient_email")

        if recipient_email:

            notification_result = (
                self.notification_service.send_staff_assigned(
                    patient_id=context.patient_id,
                    title="Nurse Assigned",
                    message=(
                        context.data.get("message")
                        or (
                            f"Nurse {nurse_id} has been successfully "
                            f"assigned to admission "
                            f"{context.admission_id}."
                        )
                    ),
                    recipient_email=recipient_email,
                    source_agent="StaffAgent",
                    admission_id=context.admission_id,
                )
            )

        else:

            notification_result = {
                "success": False,
                "status": "SKIPPED",
                "reason": (
                    "No recipient_email was provided in AgentContext."
                ),
            }

        # ---------------------------------------------------------
        # Return nurse assignment result
        # ---------------------------------------------------------

        return AgentResult(
            status="SUCCESS",
            decision="NO_ACTION",
            reason=(
                f"Nurse {nurse_id} successfully assigned "
                f"to admission {context.admission_id}."
            ),
            data={
                "nurse": selected_nurse,
                "assignment": tool_result,
                "notification_result": notification_result,
            },
            actions=[action],
        )