from typing import Any

from app.gateway.action_gateway import ActionGateway


class AdmissionToolError(Exception):
    """Raised when an admission tool operation cannot be completed."""


class AdmissionTool:
    """
    Tool layer for patient admission management.

    Responsibilities:
    - Read admission information from MySQL.
    - Create state-changing gateway requests.
    - Execute admission stored procedures through ActionGateway.

    Business rules remain authoritative in MySQL stored procedures.
    """

    VALID_ADMISSION_TYPES = {
        "EMERGENCY",
        "ELECTIVE",
        "TRANSFER",
        "OBSERVATION",
    }

    VALID_STATUSES = {
        "ADMITTED",
        "OBSERVATION",
        "DISCHARGED",
        "CANCELLED",
    }

    def __init__(self, action_gateway: ActionGateway | None = None):
        self.action_gateway = action_gateway or ActionGateway()

    # =========================================================
    # READ OPERATIONS
    # =========================================================

    def get_admission(self, admission_id: int) -> dict[str, Any] | None:
        if not isinstance(admission_id, int) or admission_id <= 0:
            raise ValueError("admission_id must be a positive integer.")

        query = """
            SELECT
                admission_id,
                patient_id,
                bed_id,
                doctor_id,
                department_id,
                encounter_id,
                admission_type,
                admission_time,
                expected_discharge_time,
                actual_discharge_time,
                status,
                diagnosis,
                notes,
                created_at,
                updated_at
            FROM admissions
            WHERE admission_id = %s
            LIMIT 1
        """

        from app.database.connection import get_db_connection

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (admission_id,))
            result = cursor.fetchone()
            cursor.close()
            return result

    def get_active_admission(
        self,
        patient_id: str,
    ) -> dict[str, Any] | None:
        if not patient_id or not isinstance(patient_id, str):
            raise ValueError("patient_id must be a non-empty string.")

        query = """
            SELECT
                admission_id,
                patient_id,
                bed_id,
                doctor_id,
                department_id,
                encounter_id,
                admission_type,
                admission_time,
                expected_discharge_time,
                actual_discharge_time,
                status,
                diagnosis,
                notes,
                created_at,
                updated_at
            FROM admissions
            WHERE patient_id = %s
              AND status IN ('ADMITTED', 'OBSERVATION')
            ORDER BY admission_time DESC
            LIMIT 1
        """

        from app.database.connection import get_db_connection

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (patient_id,))
            result = cursor.fetchone()
            cursor.close()
            return result

    def list_admissions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        patient_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or limit <= 0 or limit > 500:
            raise ValueError("limit must be between 1 and 500.")

        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be >= 0.")

        if status is not None and status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid admission status: {status}")

        if patient_id is not None and not isinstance(patient_id, str):
            raise ValueError("patient_id must be a string.")

        query = """
            SELECT
                admission_id,
                patient_id,
                bed_id,
                doctor_id,
                department_id,
                encounter_id,
                admission_type,
                admission_time,
                expected_discharge_time,
                actual_discharge_time,
                status,
                diagnosis,
                notes,
                created_at,
                updated_at
            FROM admissions
            WHERE (%s IS NULL OR status = %s)
              AND (%s IS NULL OR patient_id = %s)
            ORDER BY admission_time DESC
            LIMIT %s OFFSET %s
        """

        from app.database.connection import get_db_connection

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                query,
                (
                    status,
                    status,
                    patient_id,
                    patient_id,
                    limit,
                    offset,
                ),
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    # =========================================================
    # CREATE ADMISSION
    # =========================================================

    def create_admission(
        self,
        patient_id: str,
        department_id: int,
        admission_type: str,
        encounter_id: str | None = None,
        expected_discharge_time: Any = None,
        diagnosis: str | None = None,
        notes: str | None = None,
        requested_by_agent: str = "AdmissionAgent",
    ) -> dict[str, Any]:
        if not patient_id or not isinstance(patient_id, str):
            raise ValueError("patient_id must be a non-empty string.")

        if not isinstance(department_id, int) or department_id <= 0:
            raise ValueError("department_id must be a positive integer.")

        if admission_type not in self.VALID_ADMISSION_TYPES:
            raise ValueError(
                f"Invalid admission_type: {admission_type}"
            )

        if not requested_by_agent:
            raise ValueError("requested_by_agent is required.")

        request_id = self.action_gateway.create_request(
            action_type="CREATE_ADMISSION",
            requested_by_agent=requested_by_agent,
            patient_id=patient_id,
            target_type="PATIENT",
            target_id=patient_id,
            request_payload={
                "patient_id": patient_id,
                "department_id": department_id,
                "admission_type": admission_type,
                "encounter_id": encounter_id,
                "expected_discharge_time": expected_discharge_time,
                "diagnosis": diagnosis,
                "notes": notes,
            },
        )

        return self.action_gateway.execute_action(request_id)

    # =========================================================
    # UPDATE STATUS
    # =========================================================

    def update_admission_status(
        self,
        admission_id: int,
        new_status: str,
        requested_by_agent: str = "AdmissionAgent",
    ) -> dict[str, Any]:
        if not isinstance(admission_id, int) or admission_id <= 0:
            raise ValueError("admission_id must be a positive integer.")

        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid admission status: {new_status}")

        if not requested_by_agent:
            raise ValueError("requested_by_agent is required.")

        admission = self.get_admission(admission_id)

        if admission is None:
            raise AdmissionToolError(
                f"Admission {admission_id} not found."
            )

        request_id = self.action_gateway.create_request(
            action_type="UPDATE_ADMISSION_STATUS",
            requested_by_agent=requested_by_agent,
            patient_id=admission["patient_id"],
            admission_id=admission_id,
            target_type="ADMISSION",
            target_id=str(admission_id),
            request_payload={
                "admission_id": admission_id,
                "new_status": new_status,
            },
        )

        return self.action_gateway.execute_action(request_id)

    # =========================================================
    # DISCHARGE
    # =========================================================

    def discharge_admission(
        self,
        admission_id: int,
        notes: str | None = None,
        requested_by_agent: str = "AdmissionAgent",
    ) -> dict[str, Any]:
        if not isinstance(admission_id, int) or admission_id <= 0:
            raise ValueError("admission_id must be a positive integer.")

        if not requested_by_agent:
            raise ValueError("requested_by_agent is required.")

        admission = self.get_admission(admission_id)

        if admission is None:
            raise AdmissionToolError(
                f"Admission {admission_id} not found."
            )

        request_id = self.action_gateway.create_request(
            action_type="DISCHARGE_ADMISSION",
            requested_by_agent=requested_by_agent,
            patient_id=admission["patient_id"],
            admission_id=admission_id,
            target_type="ADMISSION",
            target_id=str(admission_id),
            request_payload={
                "admission_id": admission_id,
                "notes": notes,
            },
        )

        return self.action_gateway.execute_action(request_id)

    # =========================================================
    # CANCEL
    # =========================================================

    def cancel_admission(
        self,
        admission_id: int,
        notes: str | None = None,
        requested_by_agent: str = "AdmissionAgent",
    ) -> dict[str, Any]:
        if not isinstance(admission_id, int) or admission_id <= 0:
            raise ValueError("admission_id must be a positive integer.")

        if not requested_by_agent:
            raise ValueError("requested_by_agent is required.")

        admission = self.get_admission(admission_id)

        if admission is None:
            raise AdmissionToolError(
                f"Admission {admission_id} not found."
            )

        request_id = self.action_gateway.create_request(
            action_type="CANCEL_ADMISSION",
            requested_by_agent=requested_by_agent,
            patient_id=admission["patient_id"],
            admission_id=admission_id,
            target_type="ADMISSION",
            target_id=str(admission_id),
            request_payload={
                "admission_id": admission_id,
                "notes": notes,
            },
        )

        return self.action_gateway.execute_action(request_id)

    # =========================================================
    # GENERIC DISPATCH
    # =========================================================

    def execute(
        self,
        operation: str,
        **kwargs: Any,
    ) -> Any:
        if operation == "get_admission":
            return self.get_admission(
                admission_id=int(kwargs["admission_id"])
            )

        if operation == "get_active_admission":
            return self.get_active_admission(
                patient_id=kwargs["patient_id"]
            )

        if operation == "list_admissions":
            return self.list_admissions(
                limit=int(kwargs.get("limit", 50)),
                offset=int(kwargs.get("offset", 0)),
                status=kwargs.get("status"),
                patient_id=kwargs.get("patient_id"),
            )

        if operation == "create_admission":
            return self.create_admission(
                patient_id=kwargs["patient_id"],
                department_id=int(kwargs["department_id"]),
                admission_type=kwargs["admission_type"],
                encounter_id=kwargs.get("encounter_id"),
                expected_discharge_time=kwargs.get(
                    "expected_discharge_time"
                ),
                diagnosis=kwargs.get("diagnosis"),
                notes=kwargs.get("notes"),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "AdmissionAgent",
                ),
            )

        if operation == "update_admission_status":
            return self.update_admission_status(
                admission_id=int(kwargs["admission_id"]),
                new_status=kwargs["new_status"],
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "AdmissionAgent",
                ),
            )

        if operation == "discharge_admission":
            return self.discharge_admission(
                admission_id=int(kwargs["admission_id"]),
                notes=kwargs.get("notes"),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "AdmissionAgent",
                ),
            )

        if operation == "cancel_admission":
            return self.cancel_admission(
                admission_id=int(kwargs["admission_id"]),
                notes=kwargs.get("notes"),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "AdmissionAgent",
                ),
            )

        raise ValueError(f"Unsupported admission operation: {operation}")
