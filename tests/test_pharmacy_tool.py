from typing import Any

import pytest

from app.tools.pharmacy_tool import PharmacyTool


@pytest.fixture
def pharmacy_tool():
    return PharmacyTool()


def test_get_medication_out_of_stock(pharmacy_tool):
    medication = pharmacy_tool.get_medication(1)

    assert medication is not None
    assert medication["medication_inventory_id"] == 1
    assert medication["status"] == "OUT_OF_STOCK"
    assert medication["quantity_on_hand"] == 0


def test_get_medication_low_stock(pharmacy_tool):
    medication = pharmacy_tool.get_medication(2)

    assert medication is not None
    assert medication["medication_inventory_id"] == 2
    assert medication["status"] == "LOW_STOCK"
    assert medication["quantity_on_hand"] == 15


def test_get_medication_available(pharmacy_tool):
    medication = pharmacy_tool.get_medication(3)

    assert medication is not None
    assert medication["medication_inventory_id"] == 3
    assert medication["status"] == "AVAILABLE"
    assert medication["quantity_on_hand"] == 371


def test_check_stock_out_of_stock(pharmacy_tool):
    result = pharmacy_tool.check_stock(
        medication_inventory_id=1,
        requested_quantity=1,
    )

    assert result["found"] is True
    assert result["available"] is False
    assert result["status"] == "OUT_OF_STOCK"


def test_check_stock_low_stock(pharmacy_tool):
    result = pharmacy_tool.check_stock(
        medication_inventory_id=2,
        requested_quantity=5,
    )

    assert result["found"] is True
    assert result["available"] is True
    assert result["status"] == "LOW_STOCK"
    assert result["quantity_on_hand"] == 15
    assert result["requested_quantity"] == 5
    assert result["remaining_quantity"] == 10


def test_check_stock_insufficient_quantity(pharmacy_tool):
    result = pharmacy_tool.check_stock(
        medication_inventory_id=2,
        requested_quantity=20,
    )

    assert result["found"] is True
    assert result["available"] is False
    assert result["quantity_on_hand"] == 15
    assert result["requested_quantity"] == 20


def test_check_stock_available(pharmacy_tool):
    result = pharmacy_tool.check_stock(
        medication_inventory_id=3,
        requested_quantity=100,
    )

    assert result["found"] is True
    assert result["available"] is True
    assert result["status"] == "AVAILABLE"
    assert result["remaining_quantity"] == 271


def test_get_medication_request(pharmacy_tool):
    request = pharmacy_tool.get_medication_request(1)

    assert request is not None
    assert request["request_id"] == 1
    assert request["medication_inventory_id"] == 7
    assert request["status"] == "DISPENSED"
    assert request["medication_name"] is not None


def test_get_pending_requests(pharmacy_tool):
    requests = pharmacy_tool.get_pending_requests()

    assert isinstance(requests, list)

    for request in requests:
        assert request["status"] == "REQUESTED"
        assert request["medication_name"] is not None


def test_get_pending_stat_requests(pharmacy_tool):
    requests = pharmacy_tool.get_pending_requests(
        priority="STAT"
    )

    assert isinstance(requests, list)

    for request in requests:
        assert request["status"] == "REQUESTED"
        assert request["priority"] == "STAT"


def test_search_medications(pharmacy_tool):
    medications = pharmacy_tool.search_medications(
        status="AVAILABLE",
        limit=10,
    )

    assert isinstance(medications, list)

    for medication in medications:
        assert medication["status"] == "AVAILABLE"


def test_invalid_medication_id(pharmacy_tool):
    with pytest.raises(ValueError):
        pharmacy_tool.get_medication(0)


def test_invalid_requested_quantity(pharmacy_tool):
    with pytest.raises(ValueError):
        pharmacy_tool.check_stock(
            medication_inventory_id=3,
            requested_quantity=0,
        )


def test_invalid_status(pharmacy_tool):
    with pytest.raises(ValueError):
        pharmacy_tool.search_medications(
            status="INVALID_STATUS"
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
        """

        # -----------------------------------------------------
        # GET MEDICATION
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # SEARCH MEDICATIONS
        # -----------------------------------------------------

        if operation == "search_medications":

            return self.search_medications(
                medication_name=kwargs.get("medication_name"),
                medication_code=kwargs.get("medication_code"),
                status=kwargs.get("status"),
                category=kwargs.get("category"),
                limit=int(kwargs.get("limit", 50)),
            )

        # -----------------------------------------------------
        # CHECK STOCK
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # GET MEDICATION REQUEST
        # -----------------------------------------------------

        if operation == "get_medication_request":

            if "request_id" not in kwargs:
                raise ValueError(
                    "request_id is required for "
                    "get_medication_request."
                )

            return self.get_medication_request(
                request_id=int(kwargs["request_id"])
            )

        # -----------------------------------------------------
        # GET PENDING REQUESTS
        # -----------------------------------------------------

        if operation == "get_pending_requests":

            return self.get_pending_requests(
                priority=kwargs.get("priority"),
                limit=int(kwargs.get("limit", 50)),
            )

        # -----------------------------------------------------
        # INVALID OPERATION
        # -----------------------------------------------------

        raise ValueError(
            f"Unsupported PharmacyTool operation: {operation}"
        )
        
# ============================================================
# PHARMACY AGENT TESTS
# ============================================================

def test_pharmacy_agent_import():
    from app.agents.pharmacy_agent import PharmacyAgent

    agent = PharmacyAgent()

    assert agent.agent_name == "PharmacyAgent"

    print("\nPHARMACY AGENT IMPORT TEST PASSED")


def test_pharmacy_agent_missing_request_id():
    from app.agents.pharmacy_agent import PharmacyAgent
    from app.models.agent_context import AgentContext

    agent = PharmacyAgent()

    context = AgentContext()

    result = agent.run(context)

    print("\n===== PHARMACY AGENT MISSING REQUEST TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "FAILED"
    assert result.decision == "NO_ACTION"

    assert (
        "request_id is required"
        in result.reason
    )

    print("PHARMACY AGENT MISSING REQUEST TEST PASSED")


def test_pharmacy_agent_invalid_request_id():
    from app.agents.pharmacy_agent import PharmacyAgent
    from app.models.agent_context import AgentContext

    agent = PharmacyAgent()

    context = AgentContext(
        data={
            "request_id": "invalid"
        }
    )

    result = agent.run(context)

    print("\n===== PHARMACY AGENT INVALID REQUEST TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "FAILED"
    assert result.decision == "NO_ACTION"

    assert (
        "request_id must be a valid integer"
        in result.reason
    )

    print("PHARMACY AGENT INVALID REQUEST TEST PASSED")


def test_pharmacy_agent_request_not_found():
    from app.agents.pharmacy_agent import PharmacyAgent
    from app.models.agent_context import AgentContext

    agent = PharmacyAgent()

    context = AgentContext(
        data={
            "request_id": 999999999
        }
    )

    result = agent.run(context)

    print("\n===== PHARMACY AGENT REQUEST NOT FOUND TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "FAILED"
    assert result.decision == "NO_ACTION"

    assert (
        "was not found"
        in result.reason
    )

    print("PHARMACY AGENT REQUEST NOT FOUND TEST PASSED")
def test_pharmacy_approve_medication_request_gateway():
    from app.gateway.action_gateway import ActionGateway
    from app.database.connection import get_db_connection

    gateway = ActionGateway()

    # ---------------------------------------------------------
    # STEP 1: Find a fresh REQUESTED medication request
    #         with sufficient stock
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                mr.request_id,
                mr.patient_id,
                mr.doctor_id,
                mr.medication_inventory_id,
                mr.requested_quantity,
                mr.priority,
                mr.status,
                mi.medication_name,
                mi.quantity_on_hand,
                mi.status AS inventory_status
            FROM medication_requests mr
            INNER JOIN medication_inventory mi
                ON mi.medication_inventory_id =
                   mr.medication_inventory_id
            WHERE mr.status = 'REQUESTED'
              AND mr.requested_quantity > 0
              AND mi.quantity_on_hand >= mr.requested_quantity
              AND mi.status IN ('AVAILABLE', 'LOW_STOCK')
            ORDER BY
                CASE mr.priority
                    WHEN 'STAT' THEN 1
                    WHEN 'URGENT' THEN 2
                    WHEN 'ROUTINE' THEN 3
                    ELSE 4
                END,
                mr.requested_at ASC
            LIMIT 1
            """
        )

        medication_request = cursor.fetchone()
        cursor.close()

    # A suitable request must exist
    assert medication_request is not None

    request_id = medication_request["request_id"]
    patient_id = medication_request["patient_id"]

    assert medication_request["status"] == "REQUESTED"

    quantity_before = medication_request["quantity_on_hand"]
    requested_quantity = medication_request["requested_quantity"]

    assert requested_quantity > 0
    assert quantity_before >= requested_quantity

    assert medication_request["inventory_status"] in (
        "AVAILABLE",
        "LOW_STOCK",
    )

    # ---------------------------------------------------------
    # STEP 2: Create APPROVE_MEDICATION_REQUEST gateway request
    # ---------------------------------------------------------

    gateway_request_id = gateway.create_request(
        action_type="APPROVE_MEDICATION_REQUEST",
        requested_by_agent="PharmacyAgent",
        patient_id=patient_id,
        target_type="MEDICATION_REQUEST",
        target_id=str(request_id),
        request_payload={
            "request_id": request_id,
            "patient_id": patient_id,
        },
    )

    assert gateway_request_id is not None
    assert gateway_request_id > 0

    # ---------------------------------------------------------
    # STEP 3: Execute through ActionGateway
    # ---------------------------------------------------------

    result = gateway.execute_action(
        gateway_request_id
    )

    assert result is not None

    assert (
        result["action_type"]
        == "APPROVE_MEDICATION_REQUEST"
    )

    assert (
        result["validation_status"]
        == "VALIDATED"
    )

    assert (
        result["execution_status"]
        == "COMPLETED"
    )

    # ---------------------------------------------------------
    # STEP 4: Verify medication request became APPROVED
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                request_id,
                status,
                approved_at
            FROM medication_requests
            WHERE request_id = %s
            """,
            (request_id,),
        )

        updated_request = cursor.fetchone()
        cursor.close()

    assert updated_request is not None

    assert (
        updated_request["request_id"]
        == request_id
    )

    assert (
        updated_request["status"]
        == "APPROVED"
    )

    assert (
        updated_request["approved_at"]
        is not None
    )

    # ---------------------------------------------------------
    # STEP 5: Verify approval did NOT deduct inventory
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                medication_inventory_id,
                quantity_on_hand,
                status
            FROM medication_inventory
            WHERE medication_inventory_id = %s
            """,
            (
                medication_request[
                    "medication_inventory_id"
                ],
            ),
        )

        inventory_after = cursor.fetchone()
        cursor.close()

    assert inventory_after is not None

    assert (
        inventory_after["quantity_on_hand"]
        == quantity_before
    )

    # ---------------------------------------------------------
    # TEST OUTPUT
    # ---------------------------------------------------------

    print(
        "\n===== PHARMACY APPROVAL GATEWAY TEST ====="
    )

    print(
        "Request ID:",
        request_id
    )

    print(
        "Gateway Request ID:",
        gateway_request_id
    )

    print(
        "Medication:",
        medication_request["medication_name"]
    )

    print(
        "Previous Status: REQUESTED"
    )

    print(
        "New Status:",
        updated_request["status"]
    )

    print(
        "Stock Before:",
        quantity_before
    )

    print(
        "Stock After:",
        inventory_after["quantity_on_hand"]
    )

    print(
        "Gateway Status:",
        result["execution_status"]
    )

    print(
        "PHARMACY APPROVAL GATEWAY PASSED"
    )  
def test_pharmacy_dispense_medication_gateway():
    from app.gateway.action_gateway import ActionGateway
    from app.database.connection import get_db_connection

    gateway = ActionGateway()

    # ---------------------------------------------------------
    # STEP 1: Find a fresh APPROVED medication request
    #         with sufficient stock
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                mr.request_id,
                mr.patient_id,
                mr.doctor_id,
                mr.medication_inventory_id,
                mr.requested_quantity,
                mr.priority,
                mr.status,
                mi.medication_name,
                mi.quantity_on_hand,
                mi.status AS inventory_status
            FROM medication_requests mr
            INNER JOIN medication_inventory mi
                ON mi.medication_inventory_id =
                   mr.medication_inventory_id
            WHERE mr.status = 'APPROVED'
              AND mr.requested_quantity > 0
              AND mi.quantity_on_hand >= mr.requested_quantity
              AND mi.status IN ('AVAILABLE', 'LOW_STOCK')
            ORDER BY
                CASE mr.priority
                    WHEN 'STAT' THEN 1
                    WHEN 'URGENT' THEN 2
                    WHEN 'ROUTINE' THEN 3
                    ELSE 4
                END,
                mr.approved_at ASC
            LIMIT 1
            """
        )

        medication_request = cursor.fetchone()
        cursor.close()

    # A suitable approved request must exist
    assert medication_request is not None

    request_id = medication_request["request_id"]
    patient_id = medication_request["patient_id"]

    assert medication_request["status"] == "APPROVED"

    medication_inventory_id = (
        medication_request[
            "medication_inventory_id"
        ]
    )

    requested_quantity = (
        medication_request[
            "requested_quantity"
        ]
    )

    quantity_before = (
        medication_request[
            "quantity_on_hand"
        ]
    )

    assert requested_quantity > 0
    assert quantity_before >= requested_quantity

    assert medication_request["inventory_status"] in (
        "AVAILABLE",
        "LOW_STOCK",
    )

    # ---------------------------------------------------------
    # STEP 2: Create DISPENSE_MEDICATION gateway request
    # ---------------------------------------------------------

    gateway_request_id = gateway.create_request(
        action_type="DISPENSE_MEDICATION",
        requested_by_agent="PharmacyAgent",
        patient_id=patient_id,
        target_type="MEDICATION_REQUEST",
        target_id=str(request_id),
        request_payload={
            "request_id": request_id,
            "patient_id": patient_id,
        },
    )

    assert gateway_request_id is not None
    assert gateway_request_id > 0

    # ---------------------------------------------------------
    # STEP 3: Execute through ActionGateway
    # ---------------------------------------------------------

    result = gateway.execute_action(
        gateway_request_id
    )

    assert result is not None

    assert (
        result["action_type"]
        == "DISPENSE_MEDICATION"
    )

    assert (
        result["validation_status"]
        == "VALIDATED"
    )

    assert (
        result["execution_status"]
        == "COMPLETED"
    )

    # ---------------------------------------------------------
    # STEP 4: Verify request became DISPENSED
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                request_id,
                status,
                approved_at,
                dispensed_at
            FROM medication_requests
            WHERE request_id = %s
            """,
            (request_id,),
        )

        updated_request = cursor.fetchone()
        cursor.close()

    assert updated_request is not None

    assert (
        updated_request["request_id"]
        == request_id
    )

    assert (
        updated_request["status"]
        == "DISPENSED"
    )

    assert (
        updated_request["approved_at"]
        is not None
    )

    assert (
        updated_request["dispensed_at"]
        is not None
    )

    # ---------------------------------------------------------
    # STEP 5: Verify inventory quantity was deducted
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                medication_inventory_id,
                quantity_on_hand,
                reorder_level,
                status
            FROM medication_inventory
            WHERE medication_inventory_id = %s
            """,
            (medication_inventory_id,),
        )

        inventory_after = cursor.fetchone()
        cursor.close()

    assert inventory_after is not None

    expected_quantity = (
        quantity_before
        - requested_quantity
    )

    assert (
        inventory_after["quantity_on_hand"]
        == expected_quantity
    )

    # ---------------------------------------------------------
    # STEP 6: Verify inventory status
    # ---------------------------------------------------------

    remaining_quantity = (
        inventory_after["quantity_on_hand"]
    )

    reorder_level = (
        inventory_after["reorder_level"]
    )

    if remaining_quantity <= 0:

        assert (
            inventory_after["status"]
            == "OUT_OF_STOCK"
        )

    elif remaining_quantity <= reorder_level:

        assert (
            inventory_after["status"]
            == "LOW_STOCK"
        )

    else:

        assert (
            inventory_after["status"]
            == "AVAILABLE"
        )

    # ---------------------------------------------------------
    # TEST OUTPUT
    # ---------------------------------------------------------

    print(
        "\n===== PHARMACY DISPENSING GATEWAY TEST ====="
    )

    print(
        "Request ID:",
        request_id
    )

    print(
        "Gateway Request ID:",
        gateway_request_id
    )

    print(
        "Medication:",
        medication_request["medication_name"]
    )

    print(
        "Previous Status: APPROVED"
    )

    print(
        "New Status:",
        updated_request["status"]
    )

    print(
        "Quantity Before:",
        quantity_before
    )

    print(
        "Dispensed Quantity:",
        requested_quantity
    )

    print(
        "Quantity After:",
        inventory_after["quantity_on_hand"]
    )

    print(
        "Reorder Level:",
        reorder_level
    )

    print(
        "Inventory Status:",
        inventory_after["status"]
    )

    print(
        "Gateway Status:",
        result["execution_status"]
    )

    print(
        "PHARMACY DISPENSING GATEWAY PASSED"
    )
def test_pharmacy_agent_approval_and_dispensing_workflow():
    from app.agents.pharmacy_agent import PharmacyAgent
    from app.models.agent_context import AgentContext
    from app.database.connection import get_db_connection

    # ---------------------------------------------------------
    # STEP 1: Find a fresh REQUESTED medication request
    # with sufficient stock.
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                mr.request_id,
                mr.patient_id,
                mr.medication_inventory_id,
                mr.requested_quantity,
                mr.priority,
                mr.status,
                mi.quantity_on_hand,
                mi.status AS inventory_status,
                mi.medication_name
            FROM medication_requests mr
            INNER JOIN medication_inventory mi
                ON mi.medication_inventory_id =
                   mr.medication_inventory_id
            WHERE mr.status = 'REQUESTED'
              AND mr.requested_quantity > 0
              AND mi.status IN ('AVAILABLE', 'LOW_STOCK')
              AND mi.quantity_on_hand >= mr.requested_quantity
            ORDER BY mr.request_id DESC
            LIMIT 1
            """
        )

        medication_request = cursor.fetchone()
        cursor.close()

    assert medication_request is not None

    request_id = medication_request["request_id"]
    patient_id = medication_request["patient_id"]
    quantity_before = medication_request["quantity_on_hand"]
    requested_quantity = medication_request["requested_quantity"]

    # ---------------------------------------------------------
    # STEP 2: Run PharmacyAgent.
    # ---------------------------------------------------------

    agent = PharmacyAgent()

    context = AgentContext(
        patient_id=patient_id,
        data={
            "request_id": request_id,
        },
    )

    result = agent.run(context)

    # ---------------------------------------------------------
    # STEP 3: Verify final agent result.
    # ---------------------------------------------------------

    print("\n===== PHARMACY AGENT STATE-CHANGING WORKFLOW =====")
    print("Request ID:", request_id)
    print("Patient ID:", patient_id)
    print("Medication:", medication_request["medication_name"])
    print("Priority:", medication_request["priority"])
    print("Quantity Before:", quantity_before)
    print("Requested Quantity:", requested_quantity)
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Context Actions:", context.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "PHARMACY_COMPLETED"

    # ---------------------------------------------------------
    # STEP 4: Verify both state-changing actions were recorded.
    # ---------------------------------------------------------

    assert len(context.actions) == 2

    assert context.actions[0]["agent"] == "PharmacyAgent"
    assert context.actions[0]["action"] == (
        "APPROVE_MEDICATION_REQUEST"
    )
    assert context.actions[0]["status"] == "COMPLETED"

    assert context.actions[1]["agent"] == "PharmacyAgent"
    assert context.actions[1]["action"] == "DISPENSE_MEDICATION"
    assert context.actions[1]["status"] == "COMPLETED"

    # ---------------------------------------------------------
    # STEP 5: Verify final database state.
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                request_id,
                patient_id,
                status,
                approved_at,
                dispensed_at
            FROM medication_requests
            WHERE request_id = %s
            """,
            (request_id,),
        )

        updated_request = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                medication_inventory_id,
                medication_name,
                quantity_on_hand,
                status
            FROM medication_inventory
            WHERE medication_inventory_id = %s
            """,
            (medication_request["medication_inventory_id"],),
        )

        inventory_after = cursor.fetchone()
        cursor.close()

    assert updated_request is not None
    assert updated_request["patient_id"] == patient_id
    assert updated_request["status"] == "DISPENSED"
    assert updated_request["approved_at"] is not None
    assert updated_request["dispensed_at"] is not None

    assert inventory_after is not None

    expected_quantity = (
        quantity_before - requested_quantity
    )

    assert (
        inventory_after["quantity_on_hand"]
        == expected_quantity
    )

    print("Final Request Status:", updated_request["status"])
    print(
        "Quantity After:",
        inventory_after["quantity_on_hand"],
    )
    print("PHARMACY AGENT WORKFLOW PASSED")
# ============================================================
# PHARMACY API TESTS
# Add these tests to the existing tests/test_pharmacy_tool.py
# ============================================================


def test_pharmacy_api_get_medication_inventory():
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)

    response = client.get(
        "/api/pharmacy/medications",
        params={"limit": 5},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "SUCCESS"
    assert isinstance(data["medications"], list)
    assert data["count"] == len(data["medications"])

    print("\nPHARMACY API MEDICATION LIST PASSED")


def test_pharmacy_api_get_medication_request():
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.database.connection import get_db_connection

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT request_id
            FROM medication_requests
            ORDER BY request_id DESC
            LIMIT 1
            """
        )
        request_row = cursor.fetchone()
        cursor.close()

    assert request_row is not None

    request_id = request_row["request_id"]

    client = TestClient(app)

    response = client.get(
        f"/api/pharmacy/requests/{request_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "SUCCESS"
    assert data["request"]["request_id"] == request_id

    print("\nPHARMACY API REQUEST LOOKUP PASSED")


def test_pharmacy_api_process_medication_request():
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.database.connection import get_db_connection

    # ---------------------------------------------------------
    # STEP 1: Find a fresh REQUESTED request with sufficient stock
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                mr.request_id,
                mr.patient_id,
                mr.requested_quantity,
                mr.status,
                mi.quantity_on_hand,
                mi.status AS inventory_status
            FROM medication_requests mr
            INNER JOIN medication_inventory mi
                ON mi.medication_inventory_id =
                   mr.medication_inventory_id
            WHERE mr.status = 'REQUESTED'
              AND mi.quantity_on_hand >= mr.requested_quantity
              AND mi.status IN ('AVAILABLE', 'LOW_STOCK')
            ORDER BY
                CASE mr.priority
                    WHEN 'STAT' THEN 1
                    WHEN 'URGENT' THEN 2
                    WHEN 'ROUTINE' THEN 3
                END,
                mr.requested_at ASC
            LIMIT 1
            """
        )

        request_row = cursor.fetchone()
        cursor.close()

    assert request_row is not None

    request_id = request_row["request_id"]

    # ---------------------------------------------------------
    # STEP 2: Call API
    # ---------------------------------------------------------

    client = TestClient(app)

    response = client.post(
        f"/api/pharmacy/requests/{request_id}/process"
    )

    assert response.status_code == 200

    data = response.json()

    # ---------------------------------------------------------
    # STEP 3: Verify workflow result
    # ---------------------------------------------------------

    assert data["status"] == "SUCCESS"
    assert data["decision"] == "PHARMACY_COMPLETED"
    assert data["errors"] == []

    assert len(data["actions"]) == 2

    action_names = [
        action["action"]
        for action in data["actions"]
    ]

    assert action_names == [
        "APPROVE_MEDICATION_REQUEST",
        "DISPENSE_MEDICATION",
    ]

    # ---------------------------------------------------------
    # STEP 4: Verify actual MySQL state
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                request_id,
                status,
                approved_at,
                dispensed_at
            FROM medication_requests
            WHERE request_id = %s
            """,
            (request_id,),
        )

        updated_request = cursor.fetchone()
        cursor.close()

    assert updated_request is not None
    assert updated_request["status"] == "DISPENSED"
    assert updated_request["approved_at"] is not None
    assert updated_request["dispensed_at"] is not None

    print("\n===== PHARMACY API WORKFLOW TEST =====")
    print("Request ID:", request_id)
    print("API Status:", response.status_code)
    print("Workflow Status:", data["status"])
    print("Decision:", data["decision"])
    print("Final DB Status:", updated_request["status"])
    print("Actions:", action_names)
    print("PHARMACY API WORKFLOW PASSED")
    
# ============================================================
# PHARMACY API NEGATIVE / ERROR TESTS
# ============================================================


def test_pharmacy_api_get_medication_not_found():
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)

    response = client.get(
        "/api/pharmacy/medications/999999999"
    )

    assert response.status_code == 404

    data = response.json()

    assert "detail" in data
    assert (
        "was not found"
        in data["detail"]
    )

    print(
        "\nPHARMACY API MEDICATION NOT FOUND PASSED"
    )


def test_pharmacy_api_get_medication_invalid_id():
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)

    response = client.get(
        "/api/pharmacy/medications/0"
    )

    assert response.status_code == 400

    data = response.json()

    assert "detail" in data

    print(
        "\nPHARMACY API INVALID MEDICATION ID PASSED"
    )


def test_pharmacy_api_get_medication_request_not_found():
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)

    response = client.get(
        "/api/pharmacy/requests/999999999"
    )

    assert response.status_code == 404

    data = response.json()

    assert "detail" in data

    assert (
        "was not found"
        in data["detail"]
    )

    print(
        "\nPHARMACY API REQUEST NOT FOUND PASSED"
    )


def test_pharmacy_api_process_invalid_request_id():
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/pharmacy/requests/0/process"
    )

    assert response.status_code == 400

    data = response.json()

    assert "detail" in data

    assert (
        "positive integer"
        in data["detail"]
    )

    print(
        "\nPHARMACY API INVALID PROCESS REQUEST ID PASSED"
    )


def test_pharmacy_api_process_request_not_found():
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/pharmacy/requests/999999999/process"
    )

    assert response.status_code == 404

    data = response.json()

    assert "detail" in data

    assert (
        "was not found"
        in data["detail"]
    )

    print(
        "\nPHARMACY API PROCESS REQUEST NOT FOUND PASSED"
    )    