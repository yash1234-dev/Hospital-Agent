from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.lab_tool import LabTool


class LabAgent(BaseAgent):
    """
    Agent responsible for Lab Management.

    Responsibilities:
        - Inspect lab orders
        - Inspect lab results
        - Update lab-order lifecycle
        - Record new lab results
        - Interpret result severity
        - Generate the next workflow decision

    Important:
        LabAgent does not directly modify MySQL.
        All state-changing operations go through LabTool
        and ActionGateway.
    """

    def __init__(
        self,
        lab_tool: LabTool | None = None,
    ) -> None:

        super().__init__(
            agent_name="LabAgent"
        )

        self.lab_tool = (
            lab_tool
            if lab_tool is not None
            else LabTool()
        )

    # =========================================================
    # MAIN PROCESS
    # =========================================================

    def process(
        self,
        context: AgentContext,
    ) -> AgentResult:

        if context is None:
            raise ValueError(
                "AgentContext cannot be None."
            )

        if not context.data.get("lab_order_id"):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="lab_order_id is required for LabAgent.",
                data={},
                actions=[],
            )

        lab_order_id = int(
            context.data["lab_order_id"]
        )

        # -----------------------------------------------------
        # Retrieve lab order
        # -----------------------------------------------------

        lab_order = self.lab_tool.get_lab_order(
            lab_order_id
        )

        if lab_order is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    f"Lab order {lab_order_id} "
                    "was not found."
                ),
                data={},
                actions=[],
            )

        context.add_data(
            "lab_order",
            lab_order
        )

        # -----------------------------------------------------
        # Ensure patient_id is available in context
        # -----------------------------------------------------

        if not context.patient_id:
            patient_id = lab_order.get(
                "patient_id"
            )

            if patient_id:
                context.patient_id = patient_id

        # -----------------------------------------------------
        # If a new result was supplied
        # -----------------------------------------------------

        result_payload = context.data.get(
            "lab_result"
        )

        if result_payload is not None:

            return self._record_result(
                context=context,
                lab_order=lab_order,
                result_payload=result_payload,
            )

        # -----------------------------------------------------
        # If a lifecycle update was requested
        # -----------------------------------------------------

        requested_status = context.data.get(
            "requested_status"
        )

        if requested_status is not None:

            return self._update_order(
                context=context,
                lab_order=lab_order,
                new_status=requested_status,
            )

        # -----------------------------------------------------
        # Otherwise inspect existing results
        # -----------------------------------------------------

        results = self.lab_tool.get_lab_results(
            lab_order_id=lab_order_id,
            limit=20,
        )

        context.add_data(
            "lab_results",
            results
        )

        # -----------------------------------------------------
        # No result available
        # -----------------------------------------------------

        if not results:

            return AgentResult(
                status="SUCCESS",
                decision="WAIT_FOR_RESULT",
                reason=(
                    f"No lab result is available yet "
                    f"for lab order {lab_order_id}."
                ),
                data={
                    "lab_order": lab_order,
                    "lab_results": [],
                },
                actions=[],
            )

        # -----------------------------------------------------
        # Select latest result
        # -----------------------------------------------------

        latest_result = results[0]

        context.add_data(
            "latest_lab_result",
            latest_result
        )

        result_status = latest_result.get(
            "result_status"
        )

        # -----------------------------------------------------
        # CRITICAL
        # -----------------------------------------------------

        if result_status == "CRITICAL":

            self._prepare_critical_escalation_context(
                context=context,
                lab_order=lab_order,
                latest_result=latest_result,
            )

            self.add_decision(
                context=context,
                decision="ESCALATE_CRITICAL_LAB",
                reason=(
                    f"Critical laboratory result detected "
                    f"for lab order {lab_order_id}."
                ),
            )

            return AgentResult(
                status="SUCCESS",
                decision="ESCALATE_CRITICAL_LAB",
                reason=(
                    "Critical laboratory result requires "
                    "clinical escalation."
                ),
                data={
                    "lab_order": lab_order,
                    "latest_result": latest_result,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # ABNORMAL
        # -----------------------------------------------------

        if result_status == "ABNORMAL":

            self.add_decision(
                context=context,
                decision="REVIEW_ABNORMAL_LAB",
                reason=(
                    f"Abnormal laboratory result detected "
                    f"for lab order {lab_order_id}."
                ),
            )

            return AgentResult(
                status="SUCCESS",
                decision="REVIEW_ABNORMAL_LAB",
                reason=(
                    "Abnormal laboratory result requires "
                    "clinical review."
                ),
                data={
                    "lab_order": lab_order,
                    "latest_result": latest_result,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # NORMAL
        # -----------------------------------------------------

        if result_status == "NORMAL":

            self.add_decision(
                context=context,
                decision="NO_ACTION",
                reason=(
                    f"Laboratory result for lab order "
                    f"{lab_order_id} is normal."
                ),
            )

            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason=(
                    "Normal laboratory result does not "
                    "require additional LabAgent action."
                ),
                data={
                    "lab_order": lab_order,
                    "latest_result": latest_result,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # PENDING / unknown
        # -----------------------------------------------------

        return AgentResult(
            status="SUCCESS",
            decision="WAIT_FOR_RESULT",
            reason=(
                f"Laboratory result status is "
                f"{result_status}."
            ),
            data={
                "lab_order": lab_order,
                "latest_result": latest_result,
            },
            actions=[],
        )

    # =========================================================
    # PREPARE CRITICAL ESCALATION CONTEXT
    # =========================================================

    def _prepare_critical_escalation_context(
        self,
        context: AgentContext,
        lab_order: dict[str, Any],
        latest_result: dict[str, Any],
    ) -> None:
        """
        Prepare all information required by
        ClinicalEscalationAgent.

        LabAgent only prepares workflow context here.
        It does not execute the escalation itself.
        """

        lab_order_id = int(
            lab_order["lab_order_id"]
        )

        # -----------------------------------------------------
        # Patient
        # -----------------------------------------------------

        if not context.patient_id:
            patient_id = (
                lab_order.get("patient_id")
                or latest_result.get("patient_id")
            )

            if patient_id:
                context.patient_id = patient_id

        # -----------------------------------------------------
        # Lab order
        # -----------------------------------------------------

        context.add_data(
            "lab_order_id",
            lab_order_id,
        )

        # -----------------------------------------------------
        # Doctor
        # -----------------------------------------------------

        doctor_id = lab_order.get(
            "doctor_id"
        )

        context.add_data(
            "doctor_id",
            doctor_id,
        )

        # -----------------------------------------------------
        # Department
        # -----------------------------------------------------

        department_id = lab_order.get(
            "department_id"
        )

        context.add_data(
            "department_id",
            department_id,
        )

        # -----------------------------------------------------
        # Result information
        # -----------------------------------------------------

        test_name = (
            latest_result.get("test_name")
            or lab_order.get("test_name")
        )

        context.add_data(
            "test_name",
            test_name,
        )

        context.add_data(
            "result_value",
            latest_result.get("result_value"),
        )

        context.add_data(
            "numeric_value",
            latest_result.get("numeric_value"),
        )

        context.add_data(
            "unit",
            latest_result.get("unit"),
        )

        context.add_data(
            "reference_range",
            latest_result.get("reference_range"),
        )

        context.add_data(
            "message",
            (
                "Critical laboratory result requires "
                "immediate clinical review."
            ),
        )

    # =========================================================
    # UPDATE LAB ORDER
    # =========================================================

    def _update_order(
        self,
        context: AgentContext,
        lab_order: dict[str, Any],
        new_status: str,
    ) -> AgentResult:

        lab_order_id = int(
            lab_order["lab_order_id"]
        )

        current_status = lab_order[
            "order_status"
        ]

        gateway_result = (
            self.lab_tool.update_lab_order(
                lab_order_id=lab_order_id,
                new_status=new_status,
                requested_by_agent="LabAgent",
            )
        )

        if not isinstance(
            gateway_result,
            dict
        ):

            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "LabTool returned an invalid "
                    "gateway response."
                ),
                data={
                    "lab_order": lab_order,
                    "gateway_result": gateway_result,
                },
                actions=[],
            )

        if gateway_result.get(
            "execution_status"
        ) != "COMPLETED":

            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    gateway_result.get(
                        "error_message"
                    )
                    or "Lab order update failed."
                ),
                data={
                    "lab_order": lab_order,
                    "gateway_result": gateway_result,
                },
                actions=[],
            )

        action = {
            "agent": "LabAgent",
            "action": "UPDATE_LAB_ORDER",
            "status": "COMPLETED",
            "lab_order_id": lab_order_id,
            "old_status": current_status,
            "new_status": new_status,
            "gateway_request_id": gateway_result.get(
                "gateway_request_id"
            ),
        }

        self.add_action(
            context=context,
            action=action,
        )

        context.add_data(
            "updated_lab_order_status",
            new_status,
        )

        return AgentResult(
            status="SUCCESS",
            decision="LAB_ORDER_UPDATED",
            reason=(
                f"Lab order {lab_order_id} "
                f"updated from {current_status} "
                f"to {new_status}."
            ),
            data={
                "lab_order": lab_order,
                "gateway_result": gateway_result,
            },
            actions=[
                action
            ],
        )

    # =========================================================
    # RECORD LAB RESULT
    # =========================================================

    def _record_result(
        self,
        context: AgentContext,
        lab_order: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> AgentResult:

        lab_order_id = int(
            lab_order["lab_order_id"]
        )

        required_fields = [
            "patient_id",
            "test_name",
            "result_value",
            "result_status",
            "performed_at",
        ]

        missing_fields = [
            field
            for field in required_fields
            if result_payload.get(field) is None
        ]

        if missing_fields:

            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "Missing lab result fields: "
                    + ", ".join(missing_fields)
                ),
                data={
                    "lab_order": lab_order,
                    "result_payload": result_payload,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # Ensure patient ID is available
        # -----------------------------------------------------

        if not context.patient_id:
            context.patient_id = (
                result_payload.get("patient_id")
                or lab_order.get("patient_id")
            )

        gateway_result = (
            self.lab_tool.record_lab_result(
                lab_order_id=lab_order_id,
                patient_id=result_payload[
                    "patient_id"
                ],
                test_name=result_payload[
                    "test_name"
                ],
                result_value=result_payload.get(
                    "result_value"
                ),
                numeric_value=result_payload.get(
                    "numeric_value"
                ),
                unit=result_payload.get(
                    "unit"
                ),
                reference_range=result_payload.get(
                    "reference_range"
                ),
                result_status=result_payload[
                    "result_status"
                ],
                performed_at=result_payload[
                    "performed_at"
                ],
                verified_by_doctor_id=result_payload.get(
                    "verified_by_doctor_id"
                ),
                interpretation=result_payload.get(
                    "interpretation"
                ),
                requested_by_agent="LabAgent",
            )
        )

        if not isinstance(
            gateway_result,
            dict
        ):

            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "LabTool returned an invalid "
                    "gateway response."
                ),
                data={
                    "lab_order": lab_order,
                    "gateway_result": gateway_result,
                },
                actions=[],
            )

        if gateway_result.get(
            "execution_status"
        ) != "COMPLETED":

            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    gateway_result.get(
                        "error_message"
                    )
                    or "Lab result recording failed."
                ),
                data={
                    "lab_order": lab_order,
                    "gateway_result": gateway_result,
                },
                actions=[],
            )

        action = {
            "agent": "LabAgent",
            "action": "RECORD_LAB_RESULT",
            "status": "COMPLETED",
            "lab_order_id": lab_order_id,
            "result_status": result_payload[
                "result_status"
            ],
            "gateway_request_id": gateway_result.get(
                "gateway_request_id"
            ),
        }

        self.add_action(
            context=context,
            action=action,
        )

        result_status = result_payload[
            "result_status"
        ]

        # -----------------------------------------------------
        # Decide based on newly recorded result
        # -----------------------------------------------------

        if result_status == "CRITICAL":

            decision = (
                "ESCALATE_CRITICAL_LAB"
            )

            reason = (
                "Critical laboratory result "
                "recorded and requires clinical escalation."
            )

            # Prepare context for ClinicalEscalationAgent.
            self._prepare_critical_escalation_context(
                context=context,
                lab_order=lab_order,
                latest_result=result_payload,
            )

        elif result_status == "ABNORMAL":

            decision = (
                "REVIEW_ABNORMAL_LAB"
            )

            reason = (
                "Abnormal laboratory result "
                "recorded and requires clinical review."
            )

        elif result_status == "NORMAL":

            decision = "NO_ACTION"

            reason = (
                "Normal laboratory result recorded."
            )

        else:

            decision = "WAIT_FOR_RESULT"

            reason = (
                f"Laboratory result recorded with "
                f"status {result_status}."
            )

        self.add_decision(
            context=context,
            decision=decision,
            reason=reason,
        )

        return AgentResult(
            status="SUCCESS",
            decision=decision,
            reason=reason,
            data={
                "lab_order": lab_order,
                "gateway_result": gateway_result,
                "result_status": result_status,
            },
            actions=[
                action
            ],
        )