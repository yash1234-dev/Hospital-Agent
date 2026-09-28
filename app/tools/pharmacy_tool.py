from typing import Any

from app.tools.base_tool import BaseTool
from app.database.connection import get_db_connection
from app.gateway.action_gateway import ActionGateway


class PharmacyTool(BaseTool):
    """
    Agent-facing tool for pharmacy operations.

    Current version provides:
        - Retrieve medication inventory
        - Retrieve a medication by ID/code
        - Retrieve medication requests
        - Retrieve pending medication requests
        - Check medication stock
        - Approve medication requests through ActionGateway
        - Dispense medication through ActionGateway

    State-changing pharmacy operations are executed only through
    ActionGateway -> MySQL stored procedures.
    """

    def __init__(self) -> None:
        super().__init__(
            tool_name="pharmacy_tool",
            description=(
                "Retrieve medication inventory, medication requests, "
                "pharmacy stock information, and execute controlled "
                "pharmacy actions through ActionGateway."
            ),
        )

        self.action_gateway = ActionGateway()

    # =========================================================
    # MEDICATION INVENTORY
    # =========================================================

    def get_medication(
        self,
        medication_inventory_id: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve one medication inventory record.
        """

        if medication_inventory_id <= 0:
            raise ValueError(
                "medication_inventory_id must be a positive integer."
            )

        with get_db_connection() as connection:

            cursor = connection.cursor(dictionary=True)

            try:
                cursor.execute(
                    """
                    SELECT
                        medication_inventory_id,
                        medication_code,
                        medication_name,
                        category,
                        unit,
                        quantity_on_hand,
                        reorder_level,
                        reorder_quantity,
                        unit_cost,
                        expiry_date,
                        storage_location,
                        status,
                        created_at,
                        updated_at
                    FROM medication_inventory
                    WHERE medication_inventory_id = %s
                    """,
                    (medication_inventory_id,),
                )

                return cursor.fetchone()

            finally:
                cursor.close()

    # =========================================================
    # SEARCH MEDICATIONS
    # =========================================================

    def search_medications(
        self,
        medication_name: str | None = None,
        medication_code: str | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Search medication inventory using optional filters.
        """

        if limit <= 0:
            raise ValueError(
                "limit must be a positive integer."
            )

        if limit > 200:
            raise ValueError(
                "limit cannot exceed 200."
            )

        allowed_statuses = {
            "AVAILABLE",
            "LOW_STOCK",
            "OUT_OF_STOCK",
            "EXPIRED",
            "DISCONTINUED",
        }

        if status is not None and status not in allowed_statuses:
            raise ValueError(
                f"Invalid medication status: {status}"
            )

        query = """
            SELECT
                medication_inventory_id,
                medication_code,
                medication_name,
                category,
                unit,
                quantity_on_hand,
                reorder_level,
                reorder_quantity,
                unit_cost,
                expiry_date,
                storage_location,
                status,
                created_at,
                updated_at
            FROM medication_inventory
            WHERE 1 = 1
        """

        params: list[Any] = []

        if medication_name:
            query += """
                AND medication_name LIKE %s
            """
            params.append(
                f"%{medication_name}%"
            )

        if medication_code:
            query += """
                AND medication_code = %s
            """
            params.append(
                medication_code
            )

        if status:
            query += """
                AND status = %s
            """
            params.append(status)

        if category:
            query += """
                AND category = %s
            """
            params.append(category)

        query += """
            ORDER BY medication_name
            LIMIT %s
        """

        params.append(limit)

        with get_db_connection() as connection:

            cursor = connection.cursor(dictionary=True)

            try:
                cursor.execute(
                    query,
                    tuple(params),
                )

                return cursor.fetchall()

            finally:
                cursor.close()

    # =========================================================
    # STOCK CHECK
    # =========================================================

    def check_stock(
        self,
        medication_inventory_id: int,
        requested_quantity: int,
    ) -> dict[str, Any]:
        """
        Check whether sufficient medication stock exists.

        This operation is read-only.

        It does NOT reserve or dispense medication.
        """

        if medication_inventory_id <= 0:
            raise ValueError(
                "medication_inventory_id must be a positive integer."
            )

        if requested_quantity <= 0:
            raise ValueError(
                "requested_quantity must be a positive integer."
            )

        medication = self.get_medication(
            medication_inventory_id
        )

        if medication is None:
            return {
                "found": False,
                "available": False,
                "reason": (
                    "Medication inventory record was not found."
                ),
            }

        quantity_on_hand = int(
            medication["quantity_on_hand"]
        )

        reorder_level = int(
            medication["reorder_level"]
        )

        status = medication["status"]

        sufficient_stock = (
            quantity_on_hand >= requested_quantity
        )

        usable_status = status in {
            "AVAILABLE",
            "LOW_STOCK",
        }

        can_fulfill = (
            sufficient_stock
            and usable_status
        )

        return {
            "found": True,
            "available": can_fulfill,
            "medication_inventory_id": (
                medication["medication_inventory_id"]
            ),
            "medication_name": (
                medication["medication_name"]
            ),
            "quantity_on_hand": quantity_on_hand,
            "requested_quantity": requested_quantity,
            "remaining_quantity": (
                quantity_on_hand - requested_quantity
                if sufficient_stock
                else quantity_on_hand
            ),
            "reorder_level": reorder_level,
            "status": status,
            "reason": self._build_stock_reason(
                status=status,
                quantity_on_hand=quantity_on_hand,
                requested_quantity=requested_quantity,
            ),
        }

    # =========================================================
    # STOCK REASON
    # =========================================================

    @staticmethod
    def _build_stock_reason(
        status: str,
        quantity_on_hand: int,
        requested_quantity: int,
    ) -> str:

        if status == "OUT_OF_STOCK":
            return "Medication is currently out of stock."

        if status == "EXPIRED":
            return (
                "Medication has expired and cannot be dispensed."
            )

        if status == "DISCONTINUED":
            return "Medication has been discontinued."

        if quantity_on_hand < requested_quantity:
            return (
                "Available stock is lower than the requested quantity."
            )

        if status == "LOW_STOCK":
            return (
                "Requested quantity is available, "
                "but remaining stock is low."
            )

        return "Sufficient medication stock is available."

    # =========================================================
    # MEDICATION REQUEST
    # =========================================================

    def get_medication_request(
        self,
        request_id: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve one medication request with its medication
        inventory information.
        """

        if request_id <= 0:
            raise ValueError(
                "request_id must be a positive integer."
            )

        with get_db_connection() as connection:

            cursor = connection.cursor(dictionary=True)

            try:
                cursor.execute(
                    """
                    SELECT
                        mr.request_id,
                        mr.patient_id,
                        mr.doctor_id,
                        mr.admission_id,
                        mr.encounter_id,
                        mr.medication_inventory_id,
                        mr.requested_quantity,
                        mr.priority,
                        mr.request_type,
                        mr.status,
                        mr.requested_at,
                        mr.approved_at,
                        mr.dispensed_at,
                        mr.notes,

                        mi.medication_code,
                        mi.medication_name,
                        mi.category,
                        mi.unit,
                        mi.quantity_on_hand,
                        mi.reorder_level,
                        mi.status AS medication_status,
                        mi.expiry_date,
                        mi.storage_location

                    FROM medication_requests mr

                    INNER JOIN medication_inventory mi
                        ON mi.medication_inventory_id =
                           mr.medication_inventory_id

                    WHERE mr.request_id = %s
                    """,
                    (request_id,),
                )

                return cursor.fetchone()

            finally:
                cursor.close()

    # =========================================================
    # PENDING REQUESTS
    # =========================================================

    def get_pending_requests(
        self,
        priority: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Retrieve medication requests that still require
        pharmacy processing.

        Current pending state:
            REQUESTED
        """

        if limit <= 0:
            raise ValueError(
                "limit must be a positive integer."
            )

        if limit > 200:
            raise ValueError(
                "limit cannot exceed 200."
            )

        allowed_priorities = {
            "ROUTINE",
            "URGENT",
            "STAT",
        }

        if (
            priority is not None
            and priority not in allowed_priorities
        ):
            raise ValueError(
                f"Invalid priority: {priority}"
            )

        query = """
            SELECT
                mr.request_id,
                mr.patient_id,
                mr.doctor_id,
                mr.admission_id,
                mr.encounter_id,
                mr.medication_inventory_id,
                mr.requested_quantity,
                mr.priority,
                mr.request_type,
                mr.status,
                mr.requested_at,
                mr.notes,

                mi.medication_code,
                mi.medication_name,
                mi.category,
                mi.unit,
                mi.quantity_on_hand,
                mi.reorder_level,
                mi.status AS medication_status,
                mi.expiry_date,
                mi.storage_location

            FROM medication_requests mr

            INNER JOIN medication_inventory mi
                ON mi.medication_inventory_id =
                   mr.medication_inventory_id

            WHERE mr.status = 'REQUESTED'
        """

        params: list[Any] = []

        if priority:
            query += """
                AND mr.priority = %s
            """
            params.append(priority)

        query += """
            ORDER BY
                CASE mr.priority
                    WHEN 'STAT' THEN 1
                    WHEN 'URGENT' THEN 2
                    WHEN 'ROUTINE' THEN 3
                END,
                mr.requested_at ASC
            LIMIT %s
        """

        params.append(limit)

        with get_db_connection() as connection:

            cursor = connection.cursor(dictionary=True)

            try:
                cursor.execute(
                    query,
                    tuple(params),
                )

                return cursor.fetchall()

            finally:
                cursor.close()

    # =========================================================
    # APPROVE MEDICATION REQUEST
    # =========================================================

    def approve_medication_request(
        self,
        request_id: int,
        requested_by_agent: str = "PharmacyAgent",
    ) -> dict[str, Any]:
        """
        Approve a medication request through ActionGateway.

        The ActionGateway executes approve_medication_request_v1,
        which performs the authoritative business-rule validation
        and database state change.
        """

        if request_id <= 0:
            raise ValueError(
                "request_id must be a positive integer."
            )

        if not requested_by_agent:
            raise ValueError(
                "requested_by_agent is required."
            )

        medication_request = self.get_medication_request(
            request_id=request_id
        )

        if medication_request is None:
            raise ValueError(
                f"Medication request {request_id} was not found."
            )

        patient_id = medication_request.get("patient_id")

        if not patient_id:
            raise ValueError(
                f"Medication request {request_id} does not contain "
                "a patient_id."
            )

        if medication_request.get("status") != "REQUESTED":
            raise ValueError(
                f"Medication request {request_id} cannot be approved "
                f"because its current status is "
                f"{medication_request.get('status')}."
            )

        gateway_request_id = self.action_gateway.create_request(
            action_type="APPROVE_MEDICATION_REQUEST",
            requested_by_agent=requested_by_agent,
            patient_id=patient_id,
            target_type="MEDICATION_REQUEST",
            target_id=str(request_id),
            request_payload={
                "request_id": request_id,
                "patient_id": patient_id,
            },
        )

        return self.action_gateway.execute_action(
            gateway_request_id
        )

    # =========================================================
    # DISPENSE MEDICATION
    # =========================================================

    def dispense_medication(
        self,
        request_id: int,
        requested_by_agent: str = "PharmacyAgent",
    ) -> dict[str, Any]:
        """
        Dispense an approved medication request through
        ActionGateway.

        The ActionGateway executes dispense_medication_v1,
        which performs the authoritative business-rule validation,
        inventory deduction, and request status update.
        """

        if request_id <= 0:
            raise ValueError(
                "request_id must be a positive integer."
            )

        if not requested_by_agent:
            raise ValueError(
                "requested_by_agent is required."
            )

        medication_request = self.get_medication_request(
            request_id=request_id
        )

        if medication_request is None:
            raise ValueError(
                f"Medication request {request_id} was not found."
            )

        patient_id = medication_request.get("patient_id")

        if not patient_id:
            raise ValueError(
                f"Medication request {request_id} does not contain "
                "a patient_id."
            )

        if medication_request.get("status") != "APPROVED":
            raise ValueError(
                f"Medication request {request_id} cannot be dispensed "
                f"because its current status is "
                f"{medication_request.get('status')}."
            )

        gateway_request_id = self.action_gateway.create_request(
            action_type="DISPENSE_MEDICATION",
            requested_by_agent=requested_by_agent,
            patient_id=patient_id,
            target_type="MEDICATION_REQUEST",
            target_id=str(request_id),
            request_payload={
                "request_id": request_id,
                "patient_id": patient_id,
            },
        )

        return self.action_gateway.execute_action(
            gateway_request_id
        )

    # =========================================================
    # BASE TOOL EXECUTION INTERFACE
    # =========================================================

    def execute(
        self,
        operation: str,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a supported PharmacyTool operation.

        Supported operations:
            get_medication
            search_medications
            check_stock
            get_medication_request
            get_pending_requests
            approve_medication_request
            dispense_medication
        """

        if operation == "get_medication":

            if "medication_inventory_id" not in kwargs:
                raise ValueError(
                    "medication_inventory_id is required for "
                    "get_medication."
                )

            return self.get_medication(
                medication_inventory_id=int(
                    kwargs["medication_inventory_id"]
                )
            )

        if operation == "search_medications":

            return self.search_medications(
                medication_name=kwargs.get(
                    "medication_name"
                ),
                medication_code=kwargs.get(
                    "medication_code"
                ),
                status=kwargs.get("status"),
                category=kwargs.get("category"),
                limit=int(
                    kwargs.get("limit", 50)
                ),
            )

        if operation == "check_stock":

            if "medication_inventory_id" not in kwargs:
                raise ValueError(
                    "medication_inventory_id is required for "
                    "check_stock."
                )

            if "requested_quantity" not in kwargs:
                raise ValueError(
                    "requested_quantity is required for "
                    "check_stock."
                )

            return self.check_stock(
                medication_inventory_id=int(
                    kwargs["medication_inventory_id"]
                ),
                requested_quantity=int(
                    kwargs["requested_quantity"]
                ),
            )

        if operation == "get_medication_request":

            if "request_id" not in kwargs:
                raise ValueError(
                    "request_id is required for "
                    "get_medication_request."
                )

            return self.get_medication_request(
                request_id=int(
                    kwargs["request_id"]
                )
            )

        if operation == "get_pending_requests":

            return self.get_pending_requests(
                priority=kwargs.get("priority"),
                limit=int(
                    kwargs.get("limit", 50)
                ),
            )

        if operation == "approve_medication_request":

            if "request_id" not in kwargs:
                raise ValueError(
                    "request_id is required for "
                    "approve_medication_request."
                )

            return self.approve_medication_request(
                request_id=int(kwargs["request_id"]),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "PharmacyAgent",
                ),
            )

        if operation == "dispense_medication":

            if "request_id" not in kwargs:
                raise ValueError(
                    "request_id is required for "
                    "dispense_medication."
                )

            return self.dispense_medication(
                request_id=int(kwargs["request_id"]),
                requested_by_agent=kwargs.get(
                    "requested_by_agent",
                    "PharmacyAgent",
                ),
            )

        raise ValueError(
            f"Unsupported PharmacyTool operation: {operation}"
        )