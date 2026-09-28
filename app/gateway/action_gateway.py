from typing import Any
import json

from app.database.connection import get_db_connection


class ActionGatewayError(Exception):
    """Raised when an action cannot be processed by the gateway."""


class ActionGateway:
    """
    Python interface to the hospital action gateway.

    Responsibilities:
    - Create gateway requests
    - Retrieve gateway requests
    - Validate request structure
    - Execute approved action procedures

    Important:
    - Python performs structural validation.
    - MySQL stored procedures perform authoritative
      hospital business-rule validation.
    """

    SUPPORTED_ACTIONS = {
        "RESERVE_BED",
        "ASSIGN_DOCTOR",
        "ASSIGN_NURSE",
        "REQUEST_TRANSPORT",
        "DISPATCH_AMBULANCE",
        "UPDATE_LAB_ORDER",
        "RECORD_LAB_RESULT",
        "CLINICAL_ESCALATION",
        "APPROVE_MEDICATION_REQUEST",
        "DISPENSE_MEDICATION",
        # Admission management
        "CREATE_ADMISSION",
        "UPDATE_ADMISSION_STATUS",
        "DISCHARGE_ADMISSION",
        "CANCEL_ADMISSION",
    }

    # =========================================================
    # CREATE REQUEST
    # =========================================================

    def create_request(
        self,
        action_type: str,
        requested_by_agent: str,
        request_payload: dict[str, Any],
        patient_id: str | None = None,
        admission_id: int | None = None,
        incident_id: int | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> int:
        """
        Create a new action gateway request.

        The request starts in:

            validation_status = PENDING
            execution_status = PENDING
        """

        if action_type not in self.SUPPORTED_ACTIONS:
            raise ActionGatewayError(
                f"Unsupported action type: {action_type}"
            )

        if not isinstance(request_payload, dict):
            raise ActionGatewayError(
                "request_payload must be a dictionary."
            )

        query = """
            INSERT INTO action_gateway_requests (
                action_type,
                requested_by_agent,
                patient_id,
                admission_id,
                incident_id,
                target_type,
                target_id,
                request_payload,
                validation_status,
                execution_status
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'PENDING',
                'PENDING'
            )
        """

        parameters = (
            action_type,
            requested_by_agent,
            patient_id,
            admission_id,
            incident_id,
            target_type,
            target_id,
            json.dumps(request_payload, default=str),
        )

        with get_db_connection() as connection:
            cursor = connection.cursor()

            cursor.execute(query, parameters)

            gateway_request_id = cursor.lastrowid

            connection.commit()

            cursor.close()

            return gateway_request_id

    # =========================================================
    # GET REQUEST
    # =========================================================

    def get_request(
        self,
        gateway_request_id: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve a gateway request by ID.
        """

        query = """
            SELECT
                gateway_request_id,
                action_type,
                requested_by_agent,
                patient_id,
                admission_id,
                incident_id,
                target_type,
                target_id,
                request_payload,
                validation_status,
                execution_status,
                result_payload,
                error_message,
                requested_at,
                validated_at,
                executed_at
            FROM action_gateway_requests
            WHERE gateway_request_id = %s
            LIMIT 1
        """

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                query,
                (gateway_request_id,),
            )

            request = cursor.fetchone()

            cursor.close()

            return request

    # =========================================================
    # VALIDATE REQUEST STRUCTURE
    # =========================================================

    def validate_request_structure(
        self,
        gateway_request_id: int,
    ) -> bool:
        """
        Validate the structure of a gateway request.

        This method does NOT perform hospital business-rule
        validation.

        Business-rule validation remains inside the MySQL
        stored procedures.
        """

        request = self.get_request(gateway_request_id)

        if request is None:
            raise ActionGatewayError(
                f"Gateway request {gateway_request_id} not found."
            )

        if request["validation_status"] != "PENDING":
            raise ActionGatewayError(
                "Only PENDING requests can be structurally validated."
            )

        validation_error = self._validate_action_fields(request)

        if validation_error is not None:

            query = """
                UPDATE action_gateway_requests
                SET
                    validation_status = 'REJECTED',
                    execution_status = 'FAILED',
                    error_message = %s,
                    validated_at = NOW(),
                    executed_at = NOW()
                WHERE gateway_request_id = %s
            """

            with get_db_connection() as connection:
                cursor = connection.cursor()

                cursor.execute(
                    query,
                    (
                        validation_error,
                        gateway_request_id,
                    ),
                )

                connection.commit()

                cursor.close()

            return False

        # -----------------------------------------------------
        # Structural validation successful
        # -----------------------------------------------------

        query = """
            UPDATE action_gateway_requests
            SET
                validation_status = 'VALIDATED',
                validated_at = NOW()
            WHERE gateway_request_id = %s
              AND validation_status = 'PENDING'
        """

        with get_db_connection() as connection:
            cursor = connection.cursor()

            cursor.execute(
                query,
                (gateway_request_id,),
            )

            connection.commit()

            cursor.close()

        return True

    # =========================================================
    # EXECUTE ACTION
    # =========================================================

    def execute_action(
        self,
        gateway_request_id: int,
    ) -> dict[str, Any]:
        """
        Execute a gateway action using the appropriate
        MySQL stored procedure.

        The stored procedure remains responsible for
        authoritative business-rule validation.
        """

        request = self.get_request(gateway_request_id)

        if request is None:
            raise ActionGatewayError(
                f"Gateway request {gateway_request_id} not found."
            )

        if request["validation_status"] != "PENDING":
            raise ActionGatewayError(
                "Only PENDING requests can be executed."
            )

        # -----------------------------------------------------
        # Python structural validation
        # -----------------------------------------------------

        structure_valid = self.validate_request_structure(
            gateway_request_id
        )

        if not structure_valid:
            result = self.get_request(gateway_request_id)

            return result

        # -----------------------------------------------------
        # Re-read after structural validation
        # -----------------------------------------------------

        request = self.get_request(gateway_request_id)

        if request is None:
            raise ActionGatewayError(
                "Gateway request disappeared after validation."
            )

        action_type = request["action_type"]

        # -----------------------------------------------------
        # RESERVE_BED
        # -----------------------------------------------------

        if action_type == "RESERVE_BED":

            if request["patient_id"] is None:
                raise ActionGatewayError(
                    "patient_id is required for RESERVE_BED."
                )

            if request["admission_id"] is None:
                raise ActionGatewayError(
                    "admission_id is required for RESERVE_BED."
                )

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for RESERVE_BED."
                )

            bed_id = int(request["target_id"])

            patient_id = request["patient_id"]

            admission_id = int(request["admission_id"])

            procedure = """
                CALL reserve_bed_v2(
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                bed_id,
                patient_id,
                admission_id,
            )

        # -----------------------------------------------------
        # ASSIGN_NURSE
        # -----------------------------------------------------

        elif action_type == "ASSIGN_NURSE":

            if request["admission_id"] is None:
                raise ActionGatewayError(
                    "admission_id is required for ASSIGN_NURSE."
                )

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for ASSIGN_NURSE."
                )

            admission_id = int(request["admission_id"])

            nurse_id = int(request["target_id"])

            procedure = """
                CALL assign_nurse_v1(
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                admission_id,
                nurse_id,
            )

        # -----------------------------------------------------
        # ASSIGN_DOCTOR
        # -----------------------------------------------------

        elif action_type == "ASSIGN_DOCTOR":

            if request["admission_id"] is None:
                raise ActionGatewayError(
                    "admission_id is required for ASSIGN_DOCTOR."
                )

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for ASSIGN_DOCTOR."
                )

            admission_id = int(request["admission_id"])

            doctor_id = int(request["target_id"])

            procedure = """
                CALL assign_doctor_v2(
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                admission_id,
                doctor_id,
            )

        # -----------------------------------------------------
        # REQUEST_TRANSPORT
        # -----------------------------------------------------

        elif action_type == "REQUEST_TRANSPORT":

            if request["incident_id"] is None:
                raise ActionGatewayError(
                    "incident_id is required for REQUEST_TRANSPORT."
                )

            incident_id = int(request["incident_id"])

            procedure = """
                CALL request_transport_v1(
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                incident_id,
            )

        # -----------------------------------------------------
        # DISPATCH_AMBULANCE
        # -----------------------------------------------------

        elif action_type == "DISPATCH_AMBULANCE":

            if request["incident_id"] is None:
                raise ActionGatewayError(
                    "incident_id is required for DISPATCH_AMBULANCE."
                )

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for DISPATCH_AMBULANCE."
                )

            incident_id = int(request["incident_id"])

            ambulance_id = int(request["target_id"])

            procedure = """
                CALL dispatch_ambulance_v1(
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                incident_id,
                ambulance_id,
            )

        # -----------------------------------------------------
        # UPDATE_LAB_ORDER
        # -----------------------------------------------------

        elif action_type == "UPDATE_LAB_ORDER":

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for UPDATE_LAB_ORDER."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError as exc:
                    raise ActionGatewayError(
                        "request_payload contains invalid JSON "
                        "for UPDATE_LAB_ORDER."
                    ) from exc

            lab_order_id = int(request["target_id"])

            new_status = request_payload.get("new_status")

            if not new_status:
                raise ActionGatewayError(
                    "new_status is required for UPDATE_LAB_ORDER."
                )

            procedure = """
                CALL update_lab_order_v1(
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                lab_order_id,
                new_status,
            )

        # -----------------------------------------------------
        # RECORD_LAB_RESULT
        # -----------------------------------------------------

        elif action_type == "RECORD_LAB_RESULT":

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for RECORD_LAB_RESULT."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError as exc:
                    raise ActionGatewayError(
                        "request_payload contains invalid JSON "
                        "for RECORD_LAB_RESULT."
                    ) from exc

            procedure = """
                CALL record_lab_result_v1(
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                int(request["target_id"]),
                request_payload["patient_id"],
                request_payload["test_name"],
                request_payload["result_value"],
                request_payload.get("numeric_value"),
                request_payload.get("unit"),
                request_payload.get("reference_range"),
                request_payload["result_status"],
                request_payload["performed_at"],
                request_payload.get("verified_by_doctor_id"),
                request_payload.get("interpretation"),
            )

        # -----------------------------------------------------
        # CLINICAL_ESCALATION
        # -----------------------------------------------------

        elif action_type == "CLINICAL_ESCALATION":

            if request["patient_id"] is None:
                raise ActionGatewayError(
                    "patient_id is required for CLINICAL_ESCALATION."
                )

            if request["target_type"] != "LAB_ORDER":
                raise ActionGatewayError(
                    "target_type must be LAB_ORDER "
                    "for CLINICAL_ESCALATION."
                )

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for CLINICAL_ESCALATION."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError as exc:
                    raise ActionGatewayError(
                        "request_payload contains invalid JSON "
                        "for CLINICAL_ESCALATION."
                    ) from exc

            procedure = """
                CALL clinical_escalation_v1(
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                request["patient_id"],
                int(request["target_id"]),
                request["admission_id"],
                request_payload.get("doctor_id"),
                request_payload.get("department_id"),
                request_payload.get("test_name"),
                request_payload.get("result_value"),
                request_payload.get("numeric_value"),
                request_payload.get("unit"),
                request_payload.get("reference_range"),
                request_payload.get("message"),
            )

        # -----------------------------------------------------
        # APPROVE_MEDICATION_REQUEST
        # -----------------------------------------------------

        elif action_type == "APPROVE_MEDICATION_REQUEST":

            if request["patient_id"] is None:
                raise ActionGatewayError(
                    "patient_id is required for "
                    "APPROVE_MEDICATION_REQUEST."
                )

            if request["target_type"] != "MEDICATION_REQUEST":
                raise ActionGatewayError(
                    "target_type must be MEDICATION_REQUEST "
                    "for APPROVE_MEDICATION_REQUEST."
                )

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for "
                    "APPROVE_MEDICATION_REQUEST."
                )

            try:
                medication_request_id = int(request["target_id"])
            except (TypeError, ValueError) as exc:
                raise ActionGatewayError(
                    "target_id must be a valid medication request ID "
                    "for APPROVE_MEDICATION_REQUEST."
                ) from exc

            procedure = """
                CALL approve_medication_request_v1(
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                medication_request_id,
            )

        # -----------------------------------------------------
        # DISPENSE_MEDICATION
        # -----------------------------------------------------

        elif action_type == "DISPENSE_MEDICATION":

            if request["patient_id"] is None:
                raise ActionGatewayError(
                    "patient_id is required for DISPENSE_MEDICATION."
                )

            if request["target_type"] != "MEDICATION_REQUEST":
                raise ActionGatewayError(
                    "target_type must be MEDICATION_REQUEST "
                    "for DISPENSE_MEDICATION."
                )

            if request["target_id"] is None:
                raise ActionGatewayError(
                    "target_id is required for DISPENSE_MEDICATION."
                )

            try:
                medication_request_id = int(request["target_id"])
            except (TypeError, ValueError) as exc:
                raise ActionGatewayError(
                    "target_id must be a valid medication request ID "
                    "for DISPENSE_MEDICATION."
                ) from exc

            procedure = """
                CALL dispense_medication_v1(
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                medication_request_id,
            )

        # -----------------------------------------------------
        # CREATE_ADMISSION
        # -----------------------------------------------------

        elif action_type == "CREATE_ADMISSION":

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError as exc:
                    raise ActionGatewayError(
                        "request_payload contains invalid JSON "
                        "for CREATE_ADMISSION."
                    ) from exc

            if not isinstance(request_payload, dict):
                raise ActionGatewayError(
                    "request_payload must be an object "
                    "for CREATE_ADMISSION."
                )

            procedure = """
                CALL create_admission_v1(
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                request_payload["patient_id"],
                request_payload["department_id"],
                request_payload["admission_type"],
                request_payload.get("encounter_id"),
                request_payload.get("expected_discharge_time"),
                request_payload.get("diagnosis"),
                request_payload.get("notes"),
            )

        # -----------------------------------------------------
        # UPDATE_ADMISSION_STATUS
        # -----------------------------------------------------

        elif action_type == "UPDATE_ADMISSION_STATUS":

            if request["admission_id"] is None:
                raise ActionGatewayError(
                    "admission_id is required for UPDATE_ADMISSION_STATUS."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError as exc:
                    raise ActionGatewayError(
                        "request_payload contains invalid JSON "
                        "for UPDATE_ADMISSION_STATUS."
                    ) from exc

            if not isinstance(request_payload, dict):
                raise ActionGatewayError(
                    "request_payload must be an object "
                    "for UPDATE_ADMISSION_STATUS."
                )

            procedure = """
                CALL update_admission_status_v1(
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                int(request["admission_id"]),
                request_payload["new_status"],
            )

        # -----------------------------------------------------
        # DISCHARGE_ADMISSION
        # -----------------------------------------------------

        elif action_type == "DISCHARGE_ADMISSION":

            if request["admission_id"] is None:
                raise ActionGatewayError(
                    "admission_id is required for DISCHARGE_ADMISSION."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError as exc:
                    raise ActionGatewayError(
                        "request_payload contains invalid JSON "
                        "for DISCHARGE_ADMISSION."
                    ) from exc

            if not isinstance(request_payload, dict):
                raise ActionGatewayError(
                    "request_payload must be an object "
                    "for DISCHARGE_ADMISSION."
                )

            procedure = """
                CALL discharge_admission_v1(
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                int(request["admission_id"]),
                request_payload.get("notes"),
            )

        # -----------------------------------------------------
        # CANCEL_ADMISSION
        # -----------------------------------------------------

        elif action_type == "CANCEL_ADMISSION":

            if request["admission_id"] is None:
                raise ActionGatewayError(
                    "admission_id is required for CANCEL_ADMISSION."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError as exc:
                    raise ActionGatewayError(
                        "request_payload contains invalid JSON "
                        "for CANCEL_ADMISSION."
                    ) from exc

            if not isinstance(request_payload, dict):
                raise ActionGatewayError(
                    "request_payload must be an object "
                    "for CANCEL_ADMISSION."
                )

            procedure = """
                CALL cancel_admission_v1(
                    %s,
                    %s,
                    %s
                )
            """

            parameters = (
                gateway_request_id,
                int(request["admission_id"]),
                request_payload.get("notes"),
            )

        # -----------------------------------------------------
        # UNKNOWN ACTION
        # -----------------------------------------------------

        else:
            raise ActionGatewayError(
                f"Unsupported action type: {action_type}"
            )

        # -----------------------------------------------------
        # Execute stored procedure
        # -----------------------------------------------------

        try:

            with get_db_connection() as connection:
                cursor = connection.cursor()

                cursor.execute(
                    procedure,
                    parameters,
                )

                # Consume current result set.
                if cursor.with_rows:
                    cursor.fetchall()

                # Consume every remaining result set.
                while cursor.nextset():
                    if cursor.with_rows:
                        cursor.fetchall()

                connection.commit()

                cursor.close()

        except Exception as exc:

            raise ActionGatewayError(
                f"Stored procedure execution failed: {exc}"
            ) from exc

        # -----------------------------------------------------
        # Read final gateway state
        # -----------------------------------------------------

        result = self.get_request(gateway_request_id)

        if result is None:
            raise ActionGatewayError(
                "Gateway request disappeared after execution."
            )

        return result

    # =========================================================
    # ACTION FIELD VALIDATION
    # =========================================================

    def _validate_action_fields(
        self,
        request: dict[str, Any],
    ) -> str | None:
        """
        Validate fields required to execute an action.

        This only checks request structure.

        It does NOT check hospital business rules.
        """

        action_type = request["action_type"]

        # -----------------------------------------------------
        # RESERVE_BED
        # -----------------------------------------------------

        if action_type == "RESERVE_BED":

            if request["patient_id"] is None:
                return (
                    "patient_id is required "
                    "for RESERVE_BED."
                )

            if request["admission_id"] is None:
                return (
                    "admission_id is required "
                    "for RESERVE_BED."
                )

            if request["target_type"] != "BED":
                return (
                    "target_type must be BED "
                    "for RESERVE_BED."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for RESERVE_BED."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "bed ID for RESERVE_BED."
                )

        # -----------------------------------------------------
        # ASSIGN_DOCTOR
        # -----------------------------------------------------

        elif action_type == "ASSIGN_DOCTOR":

            if request["admission_id"] is None:
                return (
                    "admission_id is required "
                    "for ASSIGN_DOCTOR."
                )

            if request["target_type"] != "DOCTOR":
                return (
                    "target_type must be DOCTOR "
                    "for ASSIGN_DOCTOR."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for ASSIGN_DOCTOR."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "doctor ID for ASSIGN_DOCTOR."
                )

        # -----------------------------------------------------
        # ASSIGN_NURSE
        # -----------------------------------------------------

        elif action_type == "ASSIGN_NURSE":

            if request["admission_id"] is None:
                return (
                    "admission_id is required "
                    "for ASSIGN_NURSE."
                )

            if request["target_type"] != "NURSE":
                return (
                    "target_type must be NURSE "
                    "for ASSIGN_NURSE."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for ASSIGN_NURSE."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "nurse ID for ASSIGN_NURSE."
                )

        # -----------------------------------------------------
        # REQUEST_TRANSPORT
        # -----------------------------------------------------

        elif action_type == "REQUEST_TRANSPORT":

            if request["incident_id"] is None:
                return (
                    "incident_id is required "
                    "for REQUEST_TRANSPORT."
                )

            if request["target_type"] != "INCIDENT":
                return (
                    "target_type must be INCIDENT "
                    "for REQUEST_TRANSPORT."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for REQUEST_TRANSPORT."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "incident ID for REQUEST_TRANSPORT."
                )

            if int(request["target_id"]) != int(
                request["incident_id"]
            ):
                return (
                    "target_id must match incident_id "
                    "for REQUEST_TRANSPORT."
                )

        # -----------------------------------------------------
        # DISPATCH_AMBULANCE
        # -----------------------------------------------------

        elif action_type == "DISPATCH_AMBULANCE":

            if request["incident_id"] is None:
                return (
                    "incident_id is required "
                    "for DISPATCH_AMBULANCE."
                )

            if request["target_type"] != "AMBULANCE":
                return (
                    "target_type must be AMBULANCE "
                    "for DISPATCH_AMBULANCE."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for DISPATCH_AMBULANCE."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "ambulance ID for DISPATCH_AMBULANCE."
                )

        # -----------------------------------------------------
        # UPDATE_LAB_ORDER
        # -----------------------------------------------------

        elif action_type == "UPDATE_LAB_ORDER":

            if request["target_type"] != "LAB_ORDER":
                return (
                    "target_type must be LAB_ORDER "
                    "for UPDATE_LAB_ORDER."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for UPDATE_LAB_ORDER."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "lab order ID for UPDATE_LAB_ORDER."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for UPDATE_LAB_ORDER."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for UPDATE_LAB_ORDER."
                )

            new_status = request_payload.get("new_status")

            if new_status is None:
                return (
                    "new_status is required "
                    "for UPDATE_LAB_ORDER."
                )

            if new_status not in {
                "ORDERED",
                "COLLECTED",
                "PROCESSING",
                "COMPLETED",
                "CANCELLED",
            }:
                return (
                    "new_status must be a valid lab order status "
                    "for UPDATE_LAB_ORDER."
                )

        # -----------------------------------------------------
        # RECORD_LAB_RESULT
        # -----------------------------------------------------

        elif action_type == "RECORD_LAB_RESULT":

            if request["target_type"] != "LAB_ORDER":
                return (
                    "target_type must be LAB_ORDER "
                    "for RECORD_LAB_RESULT."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for RECORD_LAB_RESULT."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "lab order ID for RECORD_LAB_RESULT."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for RECORD_LAB_RESULT."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for RECORD_LAB_RESULT."
                )

            required_fields = (
                "patient_id",
                "test_name",
                "result_value",
                "result_status",
                "performed_at",
            )

            for field in required_fields:
                if request_payload.get(field) is None:
                    return (
                        f"{field} is required "
                        "for RECORD_LAB_RESULT."
                    )

            if request_payload["result_status"] not in {
                "NORMAL",
                "ABNORMAL",
                "CRITICAL",
                "PENDING",
            }:
                return (
                    "result_status must be one of "
                    "NORMAL, ABNORMAL, CRITICAL, PENDING "
                    "for RECORD_LAB_RESULT."
                )

        # -----------------------------------------------------
        # CLINICAL_ESCALATION
        # -----------------------------------------------------

        elif action_type == "CLINICAL_ESCALATION":

            if request["patient_id"] is None:
                return (
                    "patient_id is required "
                    "for CLINICAL_ESCALATION."
                )

            if request["target_type"] != "LAB_ORDER":
                return (
                    "target_type must be LAB_ORDER "
                    "for CLINICAL_ESCALATION."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for CLINICAL_ESCALATION."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid "
                    "lab order ID for CLINICAL_ESCALATION."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for CLINICAL_ESCALATION."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for CLINICAL_ESCALATION."
                )

            required_fields = (
                "doctor_id",
                "department_id",
                "test_name",
            )

            for field in required_fields:
                if request_payload.get(field) is None:
                    return (
                        f"{field} is required "
                        "for CLINICAL_ESCALATION."
                    )

            try:
                int(request_payload["doctor_id"])
            except (TypeError, ValueError):
                return (
                    "doctor_id must be a valid integer "
                    "for CLINICAL_ESCALATION."
                )

            try:
                int(request_payload["department_id"])
            except (TypeError, ValueError):
                return (
                    "department_id must be a valid integer "
                    "for CLINICAL_ESCALATION."
                )

        # -----------------------------------------------------
        # APPROVE_MEDICATION_REQUEST
        # -----------------------------------------------------

        elif action_type == "APPROVE_MEDICATION_REQUEST":

            if request["patient_id"] is None:
                return (
                    "patient_id is required "
                    "for APPROVE_MEDICATION_REQUEST."
                )

            if request["target_type"] != "MEDICATION_REQUEST":
                return (
                    "target_type must be MEDICATION_REQUEST "
                    "for APPROVE_MEDICATION_REQUEST."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for APPROVE_MEDICATION_REQUEST."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid medication request ID "
                    "for APPROVE_MEDICATION_REQUEST."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for APPROVE_MEDICATION_REQUEST."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for APPROVE_MEDICATION_REQUEST."
                )

            if request_payload.get("request_id") is not None:
                try:
                    payload_request_id = int(
                        request_payload["request_id"]
                    )
                    target_request_id = int(request["target_id"])
                except (TypeError, ValueError):
                    return (
                        "request_id must be a valid medication request ID "
                        "for APPROVE_MEDICATION_REQUEST."
                    )

                if payload_request_id != target_request_id:
                    return (
                        "request_id must match target_id "
                        "for APPROVE_MEDICATION_REQUEST."
                    )

        # -----------------------------------------------------
        # DISPENSE_MEDICATION
        # -----------------------------------------------------

        elif action_type == "DISPENSE_MEDICATION":

            if request["patient_id"] is None:
                return (
                    "patient_id is required "
                    "for DISPENSE_MEDICATION."
                )

            if request["target_type"] != "MEDICATION_REQUEST":
                return (
                    "target_type must be MEDICATION_REQUEST "
                    "for DISPENSE_MEDICATION."
                )

            if request["target_id"] is None:
                return (
                    "target_id is required "
                    "for DISPENSE_MEDICATION."
                )

            try:
                int(request["target_id"])
            except (TypeError, ValueError):
                return (
                    "target_id must be a valid medication request ID "
                    "for DISPENSE_MEDICATION."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for DISPENSE_MEDICATION."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for DISPENSE_MEDICATION."
                )

            if request_payload.get("request_id") is not None:
                try:
                    payload_request_id = int(request_payload["request_id"])
                    target_request_id = int(request["target_id"])
                except (TypeError, ValueError):
                    return (
                        "request_id must be a valid medication request ID "
                        "for DISPENSE_MEDICATION."
                    )

                if payload_request_id != target_request_id:
                    return (
                        "request_id must match target_id "
                        "for DISPENSE_MEDICATION."
                    )

        # -----------------------------------------------------
        # CREATE_ADMISSION
        # -----------------------------------------------------

        elif action_type == "CREATE_ADMISSION":

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for CREATE_ADMISSION."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for CREATE_ADMISSION."
                )

            required_fields = (
                "patient_id",
                "department_id",
                "admission_type",
            )

            for field in required_fields:
                if request_payload.get(field) is None:
                    return (
                        f"{field} is required "
                        "for CREATE_ADMISSION."
                    )

            if request["patient_id"] is not None:
                if str(request_payload["patient_id"]) != str(request["patient_id"]):
                    return (
                        "patient_id must match the gateway patient_id "
                        "for CREATE_ADMISSION."
                    )

            try:
                int(request_payload["department_id"])
            except (TypeError, ValueError):
                return (
                    "department_id must be a valid integer "
                    "for CREATE_ADMISSION."
                )

            if request_payload["admission_type"] not in {
                "EMERGENCY",
                "ELECTIVE",
                "TRANSFER",
                "OBSERVATION",
            }:
                return (
                    "admission_type must be one of "
                    "EMERGENCY, ELECTIVE, TRANSFER, OBSERVATION "
                    "for CREATE_ADMISSION."
                )

            for field in ("bed_id", "doctor_id"):
                if request_payload.get(field) is not None:
                    try:
                        int(request_payload[field])
                    except (TypeError, ValueError):
                        return (
                            f"{field} must be a valid integer "
                            "for CREATE_ADMISSION."
                        )

        # -----------------------------------------------------
        # UPDATE_ADMISSION_STATUS
        # -----------------------------------------------------

        elif action_type == "UPDATE_ADMISSION_STATUS":

            if request["admission_id"] is None:
                return (
                    "admission_id is required "
                    "for UPDATE_ADMISSION_STATUS."
                )

            try:
                int(request["admission_id"])
            except (TypeError, ValueError):
                return (
                    "admission_id must be a valid integer "
                    "for UPDATE_ADMISSION_STATUS."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for UPDATE_ADMISSION_STATUS."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for UPDATE_ADMISSION_STATUS."
                )

            new_status = request_payload.get("new_status")

            if new_status is None:
                return (
                    "new_status is required "
                    "for UPDATE_ADMISSION_STATUS."
                )

            if new_status not in {
                "ADMITTED",
                "OBSERVATION",
                "DISCHARGED",
                "CANCELLED",
            }:
                return (
                    "new_status must be one of "
                    "ADMITTED, OBSERVATION, DISCHARGED, CANCELLED "
                    "for UPDATE_ADMISSION_STATUS."
                )

        # -----------------------------------------------------
        # DISCHARGE_ADMISSION
        # -----------------------------------------------------

        elif action_type == "DISCHARGE_ADMISSION":

            if request["admission_id"] is None:
                return (
                    "admission_id is required "
                    "for DISCHARGE_ADMISSION."
                )

            try:
                int(request["admission_id"])
            except (TypeError, ValueError):
                return (
                    "admission_id must be a valid integer "
                    "for DISCHARGE_ADMISSION."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for DISCHARGE_ADMISSION."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for DISCHARGE_ADMISSION."
                )

        # -----------------------------------------------------
        # CANCEL_ADMISSION
        # -----------------------------------------------------

        elif action_type == "CANCEL_ADMISSION":

            if request["admission_id"] is None:
                return (
                    "admission_id is required "
                    "for CANCEL_ADMISSION."
                )

            try:
                int(request["admission_id"])
            except (TypeError, ValueError):
                return (
                    "admission_id must be a valid integer "
                    "for CANCEL_ADMISSION."
                )

            request_payload = request["request_payload"]

            if isinstance(request_payload, str):
                try:
                    request_payload = json.loads(request_payload)
                except json.JSONDecodeError:
                    return (
                        "request_payload must contain valid JSON "
                        "for CANCEL_ADMISSION."
                    )

            if not isinstance(request_payload, dict):
                return (
                    "request_payload must be an object "
                    "for CANCEL_ADMISSION."
                )

        return None