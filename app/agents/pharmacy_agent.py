from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.pharmacy_tool import PharmacyTool


class PharmacyAgent(BaseAgent):
    """
    Agent responsible for pharmacy request analysis.

    Current responsibilities:
        - Inspect medication requests
        - Inspect medication inventory
        - Check medication stock
        - Determine the next pharmacy workflow decision

    State-changing responsibilities:
        - Approve valid medication requests through PharmacyTool
        - Dispense approved medication requests through PharmacyTool
        - Record completed pharmacy actions in AgentContext

    Important:
        PharmacyAgent never updates MySQL directly.

        All state-changing operations follow:
            PharmacyAgent -> PharmacyTool -> ActionGateway
            -> MySQL stored procedure
    """

    def __init__(
        self,
        pharmacy_tool: PharmacyTool | None = None,
    ) -> None:

        super().__init__(
            agent_name="PharmacyAgent"
        )

        self.pharmacy_tool = (
            pharmacy_tool
            if pharmacy_tool is not None
            else PharmacyTool()
        )

    # =========================================================
    # MAIN PROCESS
    # =========================================================

    def process(
        self,
        context: AgentContext,
    ) -> AgentResult:

        # -----------------------------------------------------
        # 1. Validate context
        # -----------------------------------------------------

        if context is None:
            raise ValueError(
                "AgentContext cannot be None."
            )

        # -----------------------------------------------------
        # 2. Get request ID
        # -----------------------------------------------------

        request_id = context.data.get(
            "request_id"
        )

        if not request_id:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "request_id is required "
                    "for PharmacyAgent."
                ),
                data={},
                actions=[],
            )

        try:
            request_id = int(request_id)
        except (TypeError, ValueError):

            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "request_id must be a valid integer."
                ),
                data={},
                actions=[],
            )

        if request_id <= 0:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "request_id must be a positive integer."
                ),
                data={},
                actions=[],
            )

        # -----------------------------------------------------
        # 3. Retrieve medication request
        # -----------------------------------------------------

        medication_request = (
            self.pharmacy_tool.get_medication_request(
                request_id=request_id
            )
        )

        if medication_request is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    f"Medication request {request_id} "
                    "was not found."
                ),
                data={},
                actions=[],
            )

        context.add_data(
            "medication_request",
            medication_request,
        )

        # -----------------------------------------------------
        # Synchronize core identifiers into shared context
        # -----------------------------------------------------
        #
        # Pharmacy API starts this workflow with request_id only.
        # The medication request itself contains the patient and
        # admission identifiers, so propagate them into the shared
        # AgentContext for downstream agents and API/UI responses.
        #
        # admission_id may legitimately be None for medication
        # requests that are not linked to an admission.
        # -----------------------------------------------------

        patient_id = medication_request.get("patient_id")
        admission_id = medication_request.get("admission_id")

        if patient_id:
            context.patient_id = str(patient_id)

        if admission_id is not None:
            context.admission_id = int(admission_id)
        else:
            context.admission_id = None    

        context.add_data(
            "patient_id",
            context.patient_id,
        )

        context.add_data(
            "admission_id",
            context.admission_id,
        )

        # -----------------------------------------------------
        # 4. Validate required request information
        # -----------------------------------------------------

        medication_inventory_id = (
            medication_request.get(
                "medication_inventory_id"
            )
        )

        requested_quantity = (
            medication_request.get(
                "requested_quantity"
            )
        )

        if medication_inventory_id is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "Medication request does not contain "
                    "medication_inventory_id."
                ),
                data={
                    "medication_request": medication_request
                },
                actions=[],
            )

        if requested_quantity is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "Medication request does not contain "
                    "requested_quantity."
                ),
                data={
                    "medication_request": medication_request
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 5. Check medication stock
        # -----------------------------------------------------

        stock_result = (
            self.pharmacy_tool.check_stock(
                medication_inventory_id=int(
                    medication_inventory_id
                ),
                requested_quantity=int(
                    requested_quantity
                ),
            )
        )

        context.add_data(
            "stock_check",
            stock_result,
        )

        # -----------------------------------------------------
        # 6. Validate stock response
        # -----------------------------------------------------

        if not isinstance(stock_result, dict):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "PharmacyTool returned an invalid "
                    "stock-check response."
                ),
                data={
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                },
                actions=[],
            )

        if not stock_result.get("found"):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "Medication inventory record "
                    "was not found."
                ),
                data={
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 7. Read request state
        # -----------------------------------------------------

        request_status = (
            medication_request.get("status")
        )

        priority = (
            medication_request.get("priority")
        )

        medication_name = (
            medication_request.get(
                "medication_name"
            )
            or stock_result.get(
                "medication_name"
            )
        )

        # -----------------------------------------------------
        # 8. Already completed / non-pending requests
        # -----------------------------------------------------

        if request_status in {
            "DISPENSED",
            "ADMINISTERED",
            "REJECTED",
            "CANCELLED",
        }:

            reason = (
                f"Medication request {request_id} "
                f"has status {request_status} and "
                "does not require further pharmacy processing."
            )

            self.add_decision(
                context=context,
                decision="NO_ACTION",
                reason=reason,
            )

            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason=reason,
                data={
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                    "request_status": request_status,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 9. Only REQUESTED requests can move forward
        # -----------------------------------------------------

        if request_status != "REQUESTED":

            reason = (
                f"Medication request {request_id} "
                f"has unsupported processing status "
                f"{request_status}."
            )

            self.add_decision(
                context=context,
                decision="NO_ACTION",
                reason=reason,
            )

            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason=reason,
                data={
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                    "request_status": request_status,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 10. Medication unavailable
        # -----------------------------------------------------

        if not stock_result.get("available"):

            decision = "REVIEW_STOCK"

            reason = (
                f"Medication request {request_id} "
                f"cannot currently be fulfilled. "
                f"{stock_result.get('reason', 'Stock unavailable.')}"
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
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                    "medication_name": medication_name,
                    "priority": priority,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 11. State-changing pharmacy workflow
        # -----------------------------------------------------
        #
        # At this point:
        #   - request is REQUESTED
        #   - inventory exists
        #   - sufficient stock is available
        #
        # The PharmacyAgent is now allowed to move the request
        # through the controlled Tool -> Gateway -> Stored
        # Procedure path.
        #
        # Approval and dispensing are intentionally performed
        # in this single agent execution. The current
        # Orchestrator protects against executing the same
        # agent twice in one dynamic workflow, so splitting
        # these two mutations across repeated PharmacyAgent
        # executions would incorrectly trigger loop protection.
        # -----------------------------------------------------

        approval_result = self.pharmacy_tool.approve_medication_request(
            request_id=request_id,
            requested_by_agent=self.agent_name,
        )

        if not isinstance(approval_result, dict):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "PharmacyTool returned an invalid approval "
                    "response."
                ),
                data={
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                    "approval_result": approval_result,
                },
                actions=[],
            )

        approval_execution_status = approval_result.get(
            "execution_status"
        )

        if approval_execution_status != "COMPLETED":
            reason = (
                f"Medication request {request_id} approval "
                "did not complete successfully."
            )

            self.add_decision(
                context=context,
                decision="APPROVAL_FAILED",
                reason=reason,
            )

            return AgentResult(
                status="FAILED",
                decision="APPROVAL_FAILED",
                reason=reason,
                data={
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                    "approval_result": approval_result,
                },
                actions=[],
            )

        self.add_action(
            context=context,
            action={
                "agent": self.agent_name,
                "action": "APPROVE_MEDICATION_REQUEST",
                "status": "COMPLETED",
                "request_id": request_id,
            },
        )

        # -----------------------------------------------------
        # Refresh the request after approval.
        # -----------------------------------------------------

        approved_request = (
            self.pharmacy_tool.get_medication_request(
                request_id=request_id
            )
        )

        if approved_request is None:
            reason = (
                f"Medication request {request_id} could not "
                "be retrieved after approval."
            )

            self.add_decision(
                context=context,
                decision="APPROVAL_FAILED",
                reason=reason,
            )

            return AgentResult(
                status="FAILED",
                decision="APPROVAL_FAILED",
                reason=reason,
                data={
                    "medication_request": medication_request,
                    "stock_check": stock_result,
                    "approval_result": approval_result,
                },
                actions=[],
            )

        context.add_data(
            "approved_medication_request",
            approved_request,
        )

        # -----------------------------------------------------
        # Dispense the approved request.
        # -----------------------------------------------------

        dispense_result = self.pharmacy_tool.dispense_medication(
            request_id=request_id,
            requested_by_agent=self.agent_name,
        )

        if not isinstance(dispense_result, dict):
            return AgentResult(
                status="FAILED",
                decision="DISPENSING_FAILED",
                reason=(
                    "PharmacyTool returned an invalid dispensing "
                    "response after approval."
                ),
                data={
                    "medication_request": medication_request,
                    "approved_medication_request": approved_request,
                    "stock_check": stock_result,
                    "approval_result": approval_result,
                    "dispense_result": dispense_result,
                },
                actions=[],
            )

        dispense_execution_status = dispense_result.get(
            "execution_status"
        )

        if dispense_execution_status != "COMPLETED":
            reason = (
                f"Medication request {request_id} was approved "
                "but dispensing did not complete successfully."
            )

            self.add_decision(
                context=context,
                decision="DISPENSING_FAILED",
                reason=reason,
            )

            return AgentResult(
                status="FAILED",
                decision="DISPENSING_FAILED",
                reason=reason,
                data={
                    "medication_request": medication_request,
                    "approved_medication_request": approved_request,
                    "stock_check": stock_result,
                    "approval_result": approval_result,
                    "dispense_result": dispense_result,
                },
                actions=[],
            )

        self.add_action(
            context=context,
            action={
                "agent": self.agent_name,
                "action": "DISPENSE_MEDICATION",
                "status": "COMPLETED",
                "request_id": request_id,
            },
        )

        # -----------------------------------------------------
        # Refresh final request state.
        # -----------------------------------------------------

        dispensed_request = (
            self.pharmacy_tool.get_medication_request(
                request_id=request_id
            )
        )

        if dispensed_request is not None:
            context.add_data(
                "dispensed_medication_request",
                dispensed_request,
            )

        # -----------------------------------------------------
        # Final workflow decision
        # -----------------------------------------------------

        decision = "PHARMACY_COMPLETED"

        priority_text = (
            f"{priority} priority "
            if priority
            else ""
        )

        reason = (
            f"{priority_text}Medication request {request_id} "
            "was successfully approved and dispensed."
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
                "medication_request": medication_request,
                "approved_medication_request": approved_request,
                "dispensed_medication_request": dispensed_request,
                "stock_check": stock_result,
                "approval_result": approval_result,
                "dispense_result": dispense_result,
                "medication_name": medication_name,
                "priority": priority,
            },
            actions=[
                {
                    "action": "APPROVE_MEDICATION_REQUEST",
                    "status": "COMPLETED",
                    "request_id": request_id,
                },
                {
                    "action": "DISPENSE_MEDICATION",
                    "status": "COMPLETED",
                    "request_id": request_id,
                },
            ],
        )
