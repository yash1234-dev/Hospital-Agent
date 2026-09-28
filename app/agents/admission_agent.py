from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.tools.admission_tool import AdmissionTool, AdmissionToolError


class AdmissionAgent(BaseAgent):
    """
    Agent responsible for patient admission management.

    Responsibilities:
    - Validate admission workflow context.
    - Detect an existing active admission.
    - Create a new admission when required.
    - Synchronize the created admission into AgentContext.
    - Route successful admissions to bed assignment.

    State-changing operations always follow:

        AdmissionAgent
            -> AdmissionTool
            -> ActionGateway
            -> MySQL stored procedure
    """

    VALID_ADMISSION_TYPES = {
        "EMERGENCY",
        "ELECTIVE",
        "TRANSFER",
        "OBSERVATION",
    }

    def __init__(
        self,
        admission_tool: AdmissionTool | None = None,
    ) -> None:
        super().__init__(
            agent_name="AdmissionAgent"
        )

        self.admission_tool = (
            admission_tool
            if admission_tool is not None
            else AdmissionTool()
        )

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

        if not context.patient_id:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Patient ID is required for admission management.",
                data={},
                actions=[],
            )

        if context.department_id is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Department ID is required for admission management.",
                data={},
                actions=[],
            )

        if not isinstance(context.department_id, int):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Department ID must be an integer.",
                data={},
                actions=[],
            )

        if context.department_id <= 0:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="Department ID must be a positive integer.",
                data={},
                actions=[],
            )

        # -----------------------------------------------------
        # 2. Determine requested admission type
        # -----------------------------------------------------

        admission_type = context.data.get(
            "admission_type"
        )

        if admission_type is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "admission_type is required in AgentContext.data "
                    "for AdmissionAgent."
                ),
                data={},
                actions=[],
            )

        if not isinstance(admission_type, str):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason="admission_type must be a string.",
                data={},
                actions=[],
            )

        admission_type = admission_type.upper()

        if admission_type not in self.VALID_ADMISSION_TYPES:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    f"Invalid admission_type: {admission_type}"
                ),
                data={},
                actions=[],
            )

        context.add_data(
            "admission_type",
            admission_type,
        )

        # -----------------------------------------------------
        # 3. Check whether context already contains an admission
        # -----------------------------------------------------

        if context.admission_id is not None:

            if not isinstance(context.admission_id, int):
                return AgentResult(
                    status="FAILED",
                    decision="NO_ACTION",
                    reason="Admission ID must be an integer.",
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

            admission = self.admission_tool.get_admission(
                context.admission_id
            )

            if admission is None:
                return AgentResult(
                    status="FAILED",
                    decision="NO_ACTION",
                    reason=(
                        f"Admission {context.admission_id} "
                        "was not found."
                    ),
                    data={},
                    actions=[],
                )

            context.add_data(
                "admission",
                admission,
            )

            if admission["patient_id"] != context.patient_id:
                return AgentResult(
                    status="FAILED",
                    decision="NO_ACTION",
                    reason=(
                        "Existing admission belongs to a different "
                        "patient."
                    ),
                    data={
                        "admission": admission,
                    },
                    actions=[],
                )

            admission_status = admission["status"]

            # Active admission can continue to bed assignment.
            if admission_status in {
                "ADMITTED",
                "OBSERVATION",
            }:
                reason = (
                    f"Active admission {context.admission_id} "
                    "already exists. Bed assignment is required."
                )

                self.add_decision(
                    context=context,
                    decision="ASSIGN_BED",
                    reason=reason,
                )

                return AgentResult(
                    status="SUCCESS",
                    decision="ASSIGN_BED",
                    reason=reason,
                    data={
                        "admission": admission,
                    },
                    actions=[],
                )

            # A completed/cancelled admission must not be reused.
            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason=(
                    f"Admission {context.admission_id} has status "
                    f"{admission_status}. No admission action is required."
                ),
                data={
                    "admission": admission,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 4. Check database for an active admission
        # -----------------------------------------------------

        active_admission = (
            self.admission_tool.get_active_admission(
                context.patient_id
            )
        )

        if active_admission is not None:

            context.admission_id = int(
                active_admission["admission_id"]
            )

            context.add_data(
                "admission",
                active_admission,
            )

            reason = (
                f"Active admission {context.admission_id} already "
                "exists for the patient. Bed assignment is required."
            )

            self.add_decision(
                context=context,
                decision="ASSIGN_BED",
                reason=reason,
            )

            return AgentResult(
                status="SUCCESS",
                decision="ASSIGN_BED",
                reason=reason,
                data={
                    "admission": active_admission,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 5. Create new admission
        # -----------------------------------------------------

        try:
            create_result = (
                self.admission_tool.create_admission(
                    patient_id=context.patient_id,
                    department_id=context.department_id,
                    admission_type=admission_type,
                    encounter_id=context.data.get(
                        "encounter_id"
                    ),
                    expected_discharge_time=context.data.get(
                        "expected_discharge_time"
                    ),
                    diagnosis=context.data.get(
                        "diagnosis"
                    ),
                    notes=context.data.get(
                        "notes"
                    ),
                    requested_by_agent=self.agent_name,
                )
            )

        except AdmissionToolError as exc:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=str(exc),
                data={},
                actions=[],
            )

        if not isinstance(create_result, dict):
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "AdmissionTool returned an invalid admission "
                    "creation response."
                ),
                data={
                    "create_result": create_result,
                },
                actions=[],
            )

        if create_result.get("execution_status") != "COMPLETED":
            reason = (
                create_result.get("error_message")
                or "Admission creation failed."
            )

            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=reason,
                data={
                    "create_result": create_result,
                },
                actions=[],
            )

        # -----------------------------------------------------
        # 6. Retrieve the newly created admission
        # -----------------------------------------------------

        created_admission = (
            self.admission_tool.get_active_admission(
                context.patient_id
            )
        )

        if created_admission is None:
            return AgentResult(
                status="FAILED",
                decision="NO_ACTION",
                reason=(
                    "Admission was created successfully, but the "
                    "new active admission could not be retrieved."
                ),
                data={
                    "create_result": create_result,
                },
                actions=[],
            )

        context.admission_id = int(
            created_admission["admission_id"]
        )

        context.add_data(
            "admission",
            created_admission,
        )

        context.add_data(
            "created_admission",
            created_admission,
        )

        # -----------------------------------------------------
        # 7. Record completed action
        # -----------------------------------------------------

        self.add_action(
            context=context,
            action={
                "agent": self.agent_name,
                "action": "CREATE_ADMISSION",
                "status": "COMPLETED",
                "admission_id": context.admission_id,
                "patient_id": context.patient_id,
            },
        )

        # -----------------------------------------------------
        # 8. Route to bed assignment
        # -----------------------------------------------------

        reason = (
            f"Admission {context.admission_id} was successfully "
            "created. Bed assignment is required."
        )

        self.add_decision(
            context=context,
            decision="ASSIGN_BED",
            reason=reason,
        )

        return AgentResult(
            status="SUCCESS",
            decision="ASSIGN_BED",
            reason=reason,
            data={
                "admission": created_admission,
                "create_result": create_result,
            },
            actions=[
                {
                    "agent": self.agent_name,
                    "action": "CREATE_ADMISSION",
                    "status": "COMPLETED",
                    "admission_id": context.admission_id,
                    "patient_id": context.patient_id,
                }
            ],
        )
