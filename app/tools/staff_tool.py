from datetime import date
from typing import Any

from app.tools.base_tool import BaseTool
from app.tools.staff_tools import (
    get_available_doctors,
    get_available_nurses,
    get_unassigned_admissions,
)
from app.gateway.action_gateway import ActionGateway


class StaffTool(BaseTool):
    """
    Agent-facing tool for hospital staff operations.

    Read operations are delegated to staff_tools.py.

    State-changing operations are delegated to the
    ActionGateway.
    """

    def __init__(
        self,
        action_gateway: ActionGateway | None = None,
    ) -> None:
        super().__init__(
            tool_name="staff_tool",
            description=(
                "Retrieve available hospital doctors and nurses "
                "and perform authorized staff assignments."
            ),
        )

        self.action_gateway = (
            action_gateway
            if action_gateway is not None
            else ActionGateway()
        )

    # =========================================================
    # DOCTOR READ OPERATION
    # =========================================================

    def get_available_doctors(
        self,
        schedule_date: date | None = None,
        department_id: int | None = None,
        speciality: str | None = None,
        shift_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve active doctors with available schedules.
        """

        return get_available_doctors(
            schedule_date=schedule_date,
            department_id=department_id,
            speciality=speciality,
            shift_type=shift_type,
        )

    # =========================================================
    # NURSE READ OPERATION
    # =========================================================

    def get_available_nurses(
        self,
        schedule_date: date | None = None,
        department_id: int | None = None,
        shift_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve active nurses with available schedules.
        """

        return get_available_nurses(
            schedule_date=schedule_date,
            department_id=department_id,
            shift_type=shift_type,
        )

    # =========================================================
    # ASSIGN DOCTOR
    # =========================================================

    def assign_doctor(
        self,
        admission_id: int,
        doctor_id: int,
        requested_by_agent: str = "StaffAgent",
    ) -> dict[str, Any]:
        """
        Assign a doctor to an admission.

        Before creating a state-changing gateway request,
        the tool verifies that:

        1. The admission exists.
        2. The admission is active.
        3. The admission already has a bed assigned.

        The StaffTool does not directly modify the admissions
        table.

        The request is sent through the ActionGateway, which
        performs further validation and invokes assign_doctor_v2.
        """

        if admission_id <= 0:
            raise ValueError(
                "admission_id must be a positive integer."
            )

        if doctor_id <= 0:
            raise ValueError(
                "doctor_id must be a positive integer."
            )

        if not requested_by_agent.strip():
            raise ValueError(
                "requested_by_agent cannot be empty."
            )

        # -----------------------------------------------------
        # Doctor schedule validation
        # -----------------------------------------------------
        # The ActionGateway validates the doctor's schedule against
        # today's date. Validate the same condition here so StaffAgent
        # does not select a doctor from an old AVAILABLE schedule row.
        available_today = self.get_available_doctors(
            schedule_date=date.today()
        )

        doctor_is_available_today = any(
            doctor.get("doctor_id") == doctor_id
            and doctor.get("schedule_status") == "AVAILABLE"
            and doctor.get("employment_status") == "ACTIVE"
            for doctor in available_today
        )

        if not doctor_is_available_today:
            return {
                "status": "FAILED",
                "message": (
                    f"Doctor {doctor_id} is not scheduled as available today."
                ),
                "admission_id": admission_id,
                "doctor_id": doctor_id,
            }

        # -----------------------------------------------------
        # Bed prerequisite validation
        # -----------------------------------------------------

        bed_check = self._validate_bed_assignment_prerequisite(
            admission_id
        )

        if not bed_check["valid"]:
            return bed_check

        # -----------------------------------------------------
        # Create gateway request
        # -----------------------------------------------------

        gateway_request_id = (
            self.action_gateway.create_request(
                action_type="ASSIGN_DOCTOR",
                requested_by_agent=requested_by_agent,
                request_payload={
                    "admission_id": admission_id,
                    "doctor_id": doctor_id,
                },
                admission_id=admission_id,
                target_type="DOCTOR",
                target_id=str(doctor_id),
            )
        )

        # -----------------------------------------------------
        # Execute through Action Gateway
        # -----------------------------------------------------

        result = self.action_gateway.execute_action(
            gateway_request_id
        )

        return result

    # =========================================================
    # ASSIGN NURSE
    # =========================================================

    def assign_nurse(
        self,
        admission_id: int,
        nurse_id: int,
        requested_by_agent: str = "StaffAgent",
    ) -> dict[str, Any]:
        """
        Assign a nurse to an admission.

        Before creating a state-changing gateway request,
        the tool verifies that:

        1. The admission exists.
        2. The admission is active.
        3. The admission already has a bed assigned.

        The StaffTool does not directly modify the
        admission_staff table.

        The request is sent through the ActionGateway,
        which invokes assign_nurse_v1.
        """

        if admission_id <= 0:
            raise ValueError(
                "admission_id must be a positive integer."
            )

        if nurse_id <= 0:
            raise ValueError(
                "nurse_id must be a positive integer."
            )

        if not requested_by_agent.strip():
            raise ValueError(
                "requested_by_agent cannot be empty."
            )

        # -----------------------------------------------------
        # Bed prerequisite validation
        # -----------------------------------------------------

        bed_check = self._validate_bed_assignment_prerequisite(
            admission_id
        )

        if not bed_check["valid"]:
            return bed_check

        # -----------------------------------------------------
        # Create gateway request
        # -----------------------------------------------------

        gateway_request_id = (
            self.action_gateway.create_request(
                action_type="ASSIGN_NURSE",
                requested_by_agent=requested_by_agent,
                request_payload={
                    "admission_id": admission_id,
                    "nurse_id": nurse_id,
                },
                admission_id=admission_id,
                target_type="NURSE",
                target_id=str(nurse_id),
            )
        )

        # -----------------------------------------------------
        # Execute through Action Gateway
        # -----------------------------------------------------

        result = self.action_gateway.execute_action(
            gateway_request_id
        )

        return result

    # =========================================================
    # GET UNASSIGNED ADMISSIONS
    # =========================================================

    def get_unassigned_admissions(
        self,
    ) -> list[dict[str, Any]]:
        """
        Retrieve active admissions requiring doctor assignment.

        The underlying database query is implemented in
        staff_tools.py.
        """

        return get_unassigned_admissions()

    # =========================================================
    # BED PREREQUISITE VALIDATION
    # =========================================================

    def _validate_bed_assignment_prerequisite(
        self,
        admission_id: int,
    ) -> dict[str, Any]:
        """
        Verify that the admission exists, is active,
        and already has a bed assigned.

        This validation happens before a state-changing
        ActionGateway request is created.
        """

        from app.database.connection import get_db_connection

        query = """
            SELECT
                admission_id,
                patient_id,
                department_id,
                bed_id,
                status
            FROM admissions
            WHERE admission_id = %s
            LIMIT 1
        """

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                query,
                (admission_id,),
            )

            admission = cursor.fetchone()

            cursor.close()

        # -----------------------------------------------------
        # Admission does not exist
        # -----------------------------------------------------

        if not admission:
            return {
                "valid": False,
                "status": "ADMISSION_NOT_FOUND",
                "message": (
                    f"Admission {admission_id} was not found."
                ),
                "admission_id": admission_id,
                "bed_id": None,
            }

        # -----------------------------------------------------
        # Admission is not active
        # -----------------------------------------------------

        if admission["status"] not in (
            "ADMITTED",
            "OBSERVATION",
        ):
            return {
                "valid": False,
                "status": "INVALID_ADMISSION_STATUS",
                "message": (
                    f"Admission {admission_id} is not active. "
                    f"Current status: {admission['status']}."
                ),
                "admission_id": admission_id,
                "bed_id": admission["bed_id"],
            }

        # -----------------------------------------------------
        # Bed is missing
        # -----------------------------------------------------

        if admission["bed_id"] is None:
            return {
                "valid": False,
                "status": "BED_REQUIRED",
                "message": (
                    "This patient has not been assigned a "
                    "room/bed. Please assign a bed before "
                    "assigning staff."
                ),
                "admission_id": admission_id,
                "bed_id": None,
            }

        # -----------------------------------------------------
        # Bed prerequisite satisfied
        # -----------------------------------------------------

        return {
            "valid": True,
            "status": "VALID",
            "message": "Bed prerequisite satisfied.",
            "admission_id": admission_id,
            "bed_id": admission["bed_id"],
        }

    # =========================================================
    # BASE TOOL EXECUTION INTERFACE
    # =========================================================

    def execute(
        self,
        operation: str,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a supported StaffTool operation.

        Supported operations:

            get_available_doctors
            get_available_nurses
            get_unassigned_admissions
            assign_doctor
            assign_nurse
        """

        # -----------------------------------------------------
        # GET AVAILABLE DOCTORS
        # -----------------------------------------------------

        if operation == "get_available_doctors":

            return self.get_available_doctors(
                schedule_date=kwargs.get("schedule_date"),
                department_id=kwargs.get("department_id"),
                speciality=kwargs.get("speciality"),
                shift_type=kwargs.get("shift_type"),
            )

        # -----------------------------------------------------
        # GET AVAILABLE NURSES
        # -----------------------------------------------------

        if operation == "get_available_nurses":

            return self.get_available_nurses(
                schedule_date=kwargs.get("schedule_date"),
                department_id=kwargs.get("department_id"),
                shift_type=kwargs.get("shift_type"),
            )

        # -----------------------------------------------------
        # GET UNASSIGNED ADMISSIONS
        # -----------------------------------------------------

        if operation == "get_unassigned_admissions":

            return self.get_unassigned_admissions()

        # -----------------------------------------------------
        # ASSIGN DOCTOR
        # -----------------------------------------------------

        if operation == "assign_doctor":

            if "admission_id" not in kwargs:
                raise ValueError(
                    "admission_id is required for assign_doctor."
                )

            if "doctor_id" not in kwargs:
                raise ValueError(
                    "doctor_id is required for assign_doctor."
                )

            return self.assign_doctor(
                admission_id=int(
                    kwargs["admission_id"]
                ),
                doctor_id=int(
                    kwargs["doctor_id"]
                ),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "StaffAgent",
                ),
            )

        # -----------------------------------------------------
        # ASSIGN NURSE
        # -----------------------------------------------------

        if operation == "assign_nurse":

            if "admission_id" not in kwargs:
                raise ValueError(
                    "admission_id is required for assign_nurse."
                )

            if "nurse_id" not in kwargs:
                raise ValueError(
                    "nurse_id is required for assign_nurse."
                )

            return self.assign_nurse(
                admission_id=int(
                    kwargs["admission_id"]
                ),
                nurse_id=int(
                    kwargs["nurse_id"]
                ),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "StaffAgent",
                ),
            )

        # -----------------------------------------------------
        # INVALID OPERATION
        # -----------------------------------------------------

        raise ValueError(
            f"Unsupported StaffTool operation: {operation}"
        )