import pytest

from app.database.connection import get_db_connection
from app.tools.admission_tool import AdmissionTool


def _fetch_one(query, params=()):
    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        row = cursor.fetchone()
        cursor.close()
        return row


def _fetch_all(query, params=()):
    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows


def _execute(query, params=()):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        cursor.close()


def _find_test_patient():
    """
    Find a patient who:
    - exists
    - currently has no active admission

    This keeps the test independent of hard-coded patient IDs.
    """
    return _fetch_one(
        """
        SELECT p.Id AS patient_id
        FROM patients p
        WHERE NOT EXISTS (
            SELECT 1
            FROM admissions a
            WHERE a.patient_id = p.Id
              AND a.status IN ('ADMITTED', 'OBSERVATION')
        )
        LIMIT 1
        """
    )


def _find_test_department():
    return _fetch_one(
        """
        SELECT department_id
        FROM departments
        ORDER BY department_id
        LIMIT 1
        """
    )


def test_admission_tool_read_existing_admission():
    """
    Verify AdmissionTool can read an existing admission.
    """
    admission = _fetch_one(
        """
        SELECT admission_id
        FROM admissions
        ORDER BY admission_id DESC
        LIMIT 1
        """
    )

    if admission is None:
        pytest.skip("No admission exists in the database.")

    tool = AdmissionTool()

    result = tool.get_admission(
        int(admission["admission_id"])
    )

    assert result is not None
    assert result["admission_id"] == admission["admission_id"]


def test_admission_tool_create_and_cancel_admission():
    """
    End-to-end AdmissionTool test:

        AdmissionTool
            ↓
        ActionGateway
            ↓
        create_admission_v1
            ↓
        admissions
            ↓
        ActionGateway
            ↓
        cancel_admission_v1

    The admission is cancelled at the end so the test does not
    leave an active admission behind.
    """
    patient = _find_test_patient()

    if patient is None:
        pytest.skip(
            "No patient without an active admission is available."
        )

    department = _find_test_department()

    if department is None:
        pytest.skip("No department is available.")

    patient_id = patient["patient_id"]
    department_id = int(department["department_id"])

    tool = AdmissionTool()

    result = tool.create_admission(
        patient_id=patient_id,
        department_id=department_id,
        admission_type="OBSERVATION",
        diagnosis="AdmissionTool integration test",
        notes="Temporary automated test admission",
        requested_by_agent="AdmissionToolTest",
    )

    assert result is not None
    assert result["action_type"] == "CREATE_ADMISSION"
    assert result["validation_status"] == "VALIDATED"
    assert result["execution_status"] == "COMPLETED"

    created = _fetch_one(
        """
        SELECT
            admission_id,
            patient_id,
            department_id,
            admission_type,
            status
        FROM admissions
        WHERE patient_id = %s
        ORDER BY admission_id DESC
        LIMIT 1
        """,
        (patient_id,),
    )

    assert created is not None
    assert created["patient_id"] == patient_id
    assert created["department_id"] == department_id
    assert created["admission_type"] == "OBSERVATION"
    assert created["status"] == "OBSERVATION"

    admission_id = int(created["admission_id"])

    try:
        cancel_result = tool.cancel_admission(
            admission_id=admission_id,
            notes="Cleanup after AdmissionTool integration test",
            requested_by_agent="AdmissionToolTest",
        )

        assert cancel_result is not None
        assert cancel_result["action_type"] == "CANCEL_ADMISSION"
        assert cancel_result["validation_status"] == "VALIDATED"
        assert cancel_result["execution_status"] == "COMPLETED"

        final_state = _fetch_one(
            """
            SELECT
                admission_id,
                patient_id,
                status
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        assert final_state is not None
        assert final_state["patient_id"] == patient_id
        assert final_state["status"] == "CANCELLED"

    except Exception:
        # Best-effort cleanup if the assertion after creation fails.
        _execute(
            """
            UPDATE admissions
            SET
                status = 'CANCELLED',
                updated_at = NOW()
            WHERE admission_id = %s
              AND status IN ('ADMITTED', 'OBSERVATION')
            """,
            (admission_id,),
        )
        raise


def test_admission_tool_update_status_and_discharge():
    """
    Verify:

        create → update status → discharge

    using the real Gateway and MySQL procedures.
    """
    patient = _find_test_patient()

    if patient is None:
        pytest.skip(
            "No patient without an active admission is available."
        )

    department = _find_test_department()

    if department is None:
        pytest.skip("No department is available.")

    patient_id = patient["patient_id"]
    department_id = int(department["department_id"])

    tool = AdmissionTool()

    create_result = tool.create_admission(
        patient_id=patient_id,
        department_id=department_id,
        admission_type="ELECTIVE",
        diagnosis="Admission status integration test",
        notes="Temporary automated test admission",
        requested_by_agent="AdmissionToolTest",
    )

    assert create_result["validation_status"] == "VALIDATED"
    assert create_result["execution_status"] == "COMPLETED"

    created = _fetch_one(
        """
        SELECT admission_id, status
        FROM admissions
        WHERE patient_id = %s
        ORDER BY admission_id DESC
        LIMIT 1
        """,
        (patient_id,),
    )

    assert created is not None

    admission_id = int(created["admission_id"])

    try:
        status_result = tool.update_admission_status(
            admission_id=admission_id,
            new_status="ADMITTED",
            requested_by_agent="AdmissionToolTest",
        )

        assert status_result["action_type"] == "UPDATE_ADMISSION_STATUS"
        assert status_result["validation_status"] == "VALIDATED"
        assert status_result["execution_status"] == "COMPLETED"

        current = _fetch_one(
            """
            SELECT status
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        assert current["status"] == "ADMITTED"

        discharge_result = tool.discharge_admission(
            admission_id=admission_id,
            notes="Discharged by AdmissionTool integration test",
            requested_by_agent="AdmissionToolTest",
        )

        assert discharge_result["action_type"] == "DISCHARGE_ADMISSION"
        assert discharge_result["validation_status"] == "VALIDATED"
        assert discharge_result["execution_status"] == "COMPLETED"

        final_state = _fetch_one(
            """
            SELECT status, actual_discharge_time
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        assert final_state["status"] == "DISCHARGED"
        assert final_state["actual_discharge_time"] is not None

    except Exception:
        _execute(
            """
            UPDATE admissions
            SET
                status = 'CANCELLED',
                updated_at = NOW()
            WHERE admission_id = %s
              AND status IN ('ADMITTED', 'OBSERVATION')
            """,
            (admission_id,),
        )
        raise


def test_admission_tool_invalid_inputs():
    """
    Verify local tool-level validation without touching MySQL.
    """
    tool = AdmissionTool()

    with pytest.raises(ValueError):
        tool.get_admission(0)

    with pytest.raises(ValueError):
        tool.get_active_admission("")

    with pytest.raises(ValueError):
        tool.list_admissions(limit=0)

    with pytest.raises(ValueError):
        tool.list_admissions(status="INVALID")

    with pytest.raises(ValueError):
        tool.create_admission(
            patient_id="",
            department_id=1,
            admission_type="EMERGENCY",
        )

    with pytest.raises(ValueError):
        tool.create_admission(
            patient_id="test",
            department_id=1,
            admission_type="INVALID",
        )

    with pytest.raises(ValueError):
        tool.update_admission_status(
            admission_id=1,
            new_status="INVALID",
        )

    with pytest.raises(ValueError):
        tool.discharge_admission(0)

    with pytest.raises(ValueError):
        tool.cancel_admission(0)


# =========================================================
# AdmissionAgent tests
# =========================================================

from app.agents.admission_agent import AdmissionAgent
from app.models.agent_context import AgentContext


def test_admission_agent_creates_admission_and_routes_to_bed():
    """
    Real AdmissionAgent workflow:

        AdmissionAgent
            ↓
        AdmissionTool
            ↓
        ActionGateway
            ↓
        create_admission_v1
            ↓
        admissions

    The created admission is cancelled during cleanup.
    """
    patient = _find_test_patient()

    if patient is None:
        pytest.skip(
            "No patient without an active admission is available."
        )

    department = _find_test_department()

    if department is None:
        pytest.skip("No department is available.")

    patient_id = patient["patient_id"]
    department_id = int(department["department_id"])

    context = AgentContext(
        patient_id=patient_id,
        department_id=department_id,
        data={
            "admission_type": "OBSERVATION",
            "diagnosis": "AdmissionAgent integration test",
            "notes": "Temporary automated AdmissionAgent test",
        },
    )

    agent = AdmissionAgent()

    result = agent.run(context)

    print("\n===== ADMISSION AGENT CREATE TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Admission ID:", context.admission_id)
    print("Context Data:", context.data)
    print("Context Actions:", context.actions)
    print("Context Decisions:", context.decisions)

    assert result.status == "SUCCESS"
    assert result.decision == "ASSIGN_BED"
    assert context.admission_id is not None
    assert context.admission_id > 0

    admission = _fetch_one(
        """
        SELECT
            admission_id,
            patient_id,
            department_id,
            admission_type,
            status
        FROM admissions
        WHERE admission_id = %s
        """,
        (context.admission_id,),
    )

    assert admission is not None
    assert admission["patient_id"] == patient_id
    assert admission["department_id"] == department_id
    assert admission["admission_type"] == "OBSERVATION"
    assert admission["status"] == "OBSERVATION"

    assert any(
        action.get("action") == "CREATE_ADMISSION"
        and action.get("status") == "COMPLETED"
        for action in context.actions
    )

    assert context.decisions[-1]["agent"] == "AdmissionAgent"
    assert context.decisions[-1]["decision"] == "ASSIGN_BED"

    try:
        _execute(
            """
            UPDATE admissions
            SET
                status = 'CANCELLED',
                updated_at = NOW()
            WHERE admission_id = %s
              AND status IN ('ADMITTED', 'OBSERVATION')
            """,
            (context.admission_id,),
        )
    except Exception:
        raise


def test_admission_agent_uses_existing_active_admission():
    """
    Verify that AdmissionAgent does not create a duplicate
    admission when an active admission already exists.
    """
    patient = _find_test_patient()

    if patient is None:
        pytest.skip(
            "No patient without an active admission is available."
        )

    department = _find_test_department()

    if department is None:
        pytest.skip("No department is available.")

    patient_id = patient["patient_id"]
    department_id = int(department["department_id"])

    tool = AdmissionTool()

    create_result = tool.create_admission(
        patient_id=patient_id,
        department_id=department_id,
        admission_type="OBSERVATION",
        diagnosis="Existing admission test",
        notes="Temporary automated test admission",
        requested_by_agent="AdmissionAgentTest",
    )

    assert create_result["execution_status"] == "COMPLETED"

    active = tool.get_active_admission(patient_id)

    assert active is not None

    admission_id = int(active["admission_id"])

    try:
        context = AgentContext(
            patient_id=patient_id,
            department_id=department_id,
            data={
                "admission_type": "OBSERVATION",
            },
        )

        agent = AdmissionAgent()

        result = agent.run(context)

        print("\n===== ADMISSION AGENT EXISTING ADMISSION TEST =====")
        print("Status:", result.status)
        print("Decision:", result.decision)
        print("Reason:", result.reason)
        print("Admission ID:", context.admission_id)

        assert result.status == "SUCCESS"
        assert result.decision == "ASSIGN_BED"
        assert context.admission_id == admission_id

        count = _fetch_one(
            """
            SELECT COUNT(*) AS active_count
            FROM admissions
            WHERE patient_id = %s
              AND status IN ('ADMITTED', 'OBSERVATION')
            """,
            (patient_id,),
        )

        assert int(count["active_count"]) == 1

    finally:
        _execute(
            """
            UPDATE admissions
            SET
                status = 'CANCELLED',
                updated_at = NOW()
            WHERE admission_id = %s
              AND status IN ('ADMITTED', 'OBSERVATION')
            """,
            (admission_id,),
        )


def test_admission_agent_existing_context_admission():
    """
    Verify that AdmissionAgent can continue from an admission
    already placed into AgentContext.
    """
    patient = _find_test_patient()

    if patient is None:
        pytest.skip(
            "No patient without an active admission is available."
        )

    department = _find_test_department()

    if department is None:
        pytest.skip("No department is available.")

    patient_id = patient["patient_id"]
    department_id = int(department["department_id"])

    tool = AdmissionTool()

    create_result = tool.create_admission(
        patient_id=patient_id,
        department_id=department_id,
        admission_type="OBSERVATION",
        diagnosis="Context admission test",
        notes="Temporary automated test admission",
        requested_by_agent="AdmissionAgentTest",
    )

    assert create_result["execution_status"] == "COMPLETED"

    active = tool.get_active_admission(patient_id)
    assert active is not None

    admission_id = int(active["admission_id"])

    try:
        context = AgentContext(
            patient_id=patient_id,
            admission_id=admission_id,
            department_id=department_id,
            data={
                "admission_type": "OBSERVATION",
            },
        )

        result = AdmissionAgent().run(context)

        assert result.status == "SUCCESS"
        assert result.decision == "ASSIGN_BED"
        assert context.admission_id == admission_id
        assert "admission" in context.data

        assert context.actions == []

    finally:
        _execute(
            """
            UPDATE admissions
            SET
                status = 'CANCELLED',
                updated_at = NOW()
            WHERE admission_id = %s
              AND status IN ('ADMITTED', 'OBSERVATION')
            """,
            (admission_id,),
        )


def test_admission_agent_invalid_context():
    """
    Verify AdmissionAgent rejects incomplete workflow context
    without touching the database.
    """
    agent = AdmissionAgent()

    result = agent.run(
        AgentContext(
            department_id=1,
            data={
                "admission_type": "OBSERVATION",
            },
        )
    )

    assert result.status == "FAILED"
    assert result.decision == "NO_ACTION"
    assert "Patient ID is required" in result.reason


def test_admission_agent_missing_admission_type():
    """
    Verify admission_type is required before creating an admission.
    """
    agent = AdmissionAgent()

    result = agent.run(
        AgentContext(
            patient_id="test-patient",
            department_id=1,
            data={},
        )
    )

    assert result.status == "FAILED"
    assert result.decision == "NO_ACTION"
    assert "admission_type is required" in result.reason


def test_admission_agent_invalid_admission_type():
    """
    Verify invalid admission types are rejected locally.
    """
    agent = AdmissionAgent()

    result = agent.run(
        AgentContext(
            patient_id="test-patient",
            department_id=1,
            data={
                "admission_type": "INVALID",
            },
        )
    )

    assert result.status == "FAILED"
    assert result.decision == "NO_ACTION"
    assert "Invalid admission_type" in result.reason
# =========================================================
# Admission API tests
# =========================================================

from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


# =========================================================
# API TEST HELPERS
# =========================================================


def _api_find_test_patient():
    """
    Find a patient who currently has no active admission.
    """
    return _fetch_one(
        """
        SELECT p.Id AS patient_id
        FROM patients p
        WHERE NOT EXISTS (
            SELECT 1
            FROM admissions a
            WHERE a.patient_id = p.Id
              AND a.status IN ('ADMITTED', 'OBSERVATION')
        )
        LIMIT 1
        """
    )


def _api_find_department():
    return _fetch_one(
        """
        SELECT department_id
        FROM departments
        ORDER BY department_id
        LIMIT 1
        """
    )


# =========================================================
# GET ALL ADMISSIONS
# =========================================================


def test_admission_api_get_all_admissions():

    response = client.get(
        "/api/admissions"
    )

    print(
        "\n===== GET ALL ADMISSIONS API ====="
    )
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "SUCCESS"
    assert "count" in data
    assert "admissions" in data
    assert isinstance(data["admissions"], list)


# =========================================================
# GET SINGLE ADMISSION
# =========================================================


def test_admission_api_get_single_admission():

    admission = _fetch_one(
        """
        SELECT admission_id
        FROM admissions
        ORDER BY admission_id DESC
        LIMIT 1
        """
    )

    if admission is None:
        pytest.skip(
            "No admission exists in the database."
        )

    admission_id = int(
        admission["admission_id"]
    )

    response = client.get(
        f"/api/admissions/{admission_id}"
    )

    print(
        "\n===== GET SINGLE ADMISSION API ====="
    )
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "SUCCESS"
    assert "admission" in data
    assert (
        data["admission"]["admission_id"]
        == admission_id
    )


# =========================================================
# GET ACTIVE PATIENT ADMISSION
# =========================================================


def test_admission_api_get_active_patient_admission():

    admission = _fetch_one(
        """
        SELECT
            admission_id,
            patient_id
        FROM admissions
        WHERE status IN ('ADMITTED', 'OBSERVATION')
        ORDER BY admission_id DESC
        LIMIT 1
        """
    )

    if admission is None:
        pytest.skip(
            "No active admission exists."
        )

    patient_id = admission["patient_id"]

    response = client.get(
        f"/api/admissions/patient/{patient_id}/active"
    )

    print(
        "\n===== GET ACTIVE PATIENT ADMISSION API ====="
    )
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "SUCCESS"
    assert data["found"] is True
    assert data["admission"] is not None


# =========================================================
# CREATE ADMISSION API
# =========================================================


def test_admission_api_create_and_cancel():

    patient = _api_find_test_patient()
    department = _api_find_department()

    if patient is None:
        pytest.skip(
            "No patient without active admission available."
        )

    if department is None:
        pytest.skip(
            "No department available."
        )

    patient_id = patient["patient_id"]
    department_id = int(
        department["department_id"]
    )

    admission_id = None

    try:

        response = client.post(
            "/api/admissions",
            json={
                "patient_id": patient_id,
                "department_id": department_id,
                "admission_type": "OBSERVATION",
                "diagnosis": "Admission API integration test",
                "notes": "Temporary API test admission",
            },
        )

        print(
            "\n===== CREATE ADMISSION API ====="
        )
        print(
            "Status Code:",
            response.status_code,
        )
        print(
            "Response:",
            response.json(),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "SUCCESS"
        assert (
            data["message"]
            == "Admission created successfully."
        )

        admission = data["admission"]

        assert (
            admission["action_type"]
            == "CREATE_ADMISSION"
        )
        assert (
            admission["execution_status"]
            == "COMPLETED"
        )

        created = _fetch_one(
            """
            SELECT
                admission_id,
                patient_id,
                department_id,
                admission_type,
                status
            FROM admissions
            WHERE patient_id = %s
            ORDER BY admission_id DESC
            LIMIT 1
            """,
            (patient_id,),
        )

        assert created is not None

        admission_id = int(
            created["admission_id"]
        )

        assert (
            created["patient_id"]
            == patient_id
        )

        assert (
            created["department_id"]
            == department_id
        )

        assert (
            created["admission_type"]
            == "OBSERVATION"
        )

        assert (
            created["status"]
            == "OBSERVATION"
        )

    finally:

        if admission_id is not None:

            _execute(
                """
                UPDATE admissions
                SET
                    status = 'CANCELLED',
                    updated_at = NOW()
                WHERE admission_id = %s
                  AND status IN (
                      'ADMITTED',
                      'OBSERVATION'
                  )
                """,
                (admission_id,),
            )


# =========================================================
# UPDATE STATUS + DISCHARGE API
# =========================================================


def test_admission_api_update_status_and_discharge():

    patient = _api_find_test_patient()
    department = _api_find_department()

    if patient is None:
        pytest.skip(
            "No patient without active admission available."
        )

    if department is None:
        pytest.skip(
            "No department available."
        )

    patient_id = patient["patient_id"]
    department_id = int(
        department["department_id"]
    )

    admission_id = None

    try:

        create_response = client.post(
            "/api/admissions",
            json={
                "patient_id": patient_id,
                "department_id": department_id,
                "admission_type": "ELECTIVE",
                "diagnosis": "Status API test",
                "notes": "Temporary API test admission",
            },
        )

        assert create_response.status_code == 200

        created = _fetch_one(
            """
            SELECT admission_id
            FROM admissions
            WHERE patient_id = %s
            ORDER BY admission_id DESC
            LIMIT 1
            """,
            (patient_id,),
        )

        assert created is not None

        admission_id = int(
            created["admission_id"]
        )

        # -------------------------------------------------
        # UPDATE STATUS
        # -------------------------------------------------

        status_response = client.put(
            f"/api/admissions/{admission_id}/status",
            json={
                "new_status": "ADMITTED"
            },
        )

        print(
            "\n===== UPDATE ADMISSION STATUS API ====="
        )
        print(
            "Status Code:",
            status_response.status_code,
        )
        print(
            "Response:",
            status_response.json(),
        )

        assert status_response.status_code == 200

        status_data = status_response.json()

        assert status_data["status"] == "SUCCESS"
        assert (
            status_data["admission"]["action_type"]
            == "UPDATE_ADMISSION_STATUS"
        )
        assert (
            status_data["admission"]["execution_status"]
            == "COMPLETED"
        )

        db_state = _fetch_one(
            """
            SELECT status
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        assert db_state["status"] == "ADMITTED"

        # -------------------------------------------------
        # DISCHARGE
        # -------------------------------------------------

        discharge_response = client.post(
            f"/api/admissions/{admission_id}/discharge",
            json={
                "notes": "API discharge integration test"
            },
        )

        print(
            "\n===== DISCHARGE ADMISSION API ====="
        )
        print(
            "Status Code:",
            discharge_response.status_code,
        )
        print(
            "Response:",
            discharge_response.json(),
        )

        assert discharge_response.status_code == 200

        discharge_data = (
            discharge_response.json()
        )

        assert (
            discharge_data["status"]
            == "SUCCESS"
        )

        assert (
            discharge_data["admission"]["action_type"]
            == "DISCHARGE_ADMISSION"
        )

        assert (
            discharge_data["admission"]
            ["execution_status"]
            == "COMPLETED"
        )

        final_state = _fetch_one(
            """
            SELECT
                status,
                actual_discharge_time
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        assert (
            final_state["status"]
            == "DISCHARGED"
        )

        assert (
            final_state[
                "actual_discharge_time"
            ]
            is not None
        )

    finally:

        if admission_id is not None:

            _execute(
                """
                UPDATE admissions
                SET
                    status = 'CANCELLED',
                    updated_at = NOW()
                WHERE admission_id = %s
                  AND status IN (
                      'ADMITTED',
                      'OBSERVATION'
                  )
                """,
                (admission_id,),
            )


# =========================================================
# CANCEL ADMISSION API
# =========================================================


def test_admission_api_cancel():

    patient = _api_find_test_patient()
    department = _api_find_department()

    if patient is None:
        pytest.skip(
            "No patient without active admission available."
        )

    if department is None:
        pytest.skip(
            "No department available."
        )

    patient_id = patient["patient_id"]
    department_id = int(
        department["department_id"]
    )

    admission_id = None

    try:

        create_response = client.post(
            "/api/admissions",
            json={
                "patient_id": patient_id,
                "department_id": department_id,
                "admission_type": "OBSERVATION",
                "diagnosis": "Cancel API test",
                "notes": "Temporary cancellation test",
            },
        )

        assert create_response.status_code == 200

        created = _fetch_one(
            """
            SELECT admission_id
            FROM admissions
            WHERE patient_id = %s
            ORDER BY admission_id DESC
            LIMIT 1
            """,
            (patient_id,),
        )

        assert created is not None

        admission_id = int(
            created["admission_id"]
        )

        response = client.post(
            f"/api/admissions/{admission_id}/cancel",
            json={
                "notes": "API cancellation test"
            },
        )

        print(
            "\n===== CANCEL ADMISSION API ====="
        )
        print(
            "Status Code:",
            response.status_code,
        )
        print(
            "Response:",
            response.json(),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "SUCCESS"

        assert (
            data["admission"]["action_type"]
            == "CANCEL_ADMISSION"
        )

        assert (
            data["admission"]["execution_status"]
            == "COMPLETED"
        )

        db_state = _fetch_one(
            """
            SELECT status
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        assert (
            db_state["status"]
            == "CANCELLED"
        )

    finally:

        if admission_id is not None:

            _execute(
                """
                UPDATE admissions
                SET
                    status = 'CANCELLED',
                    updated_at = NOW()
                WHERE admission_id = %s
                  AND status IN (
                      'ADMITTED',
                      'OBSERVATION'
                  )
                """,
                (admission_id,),
            )


# =========================================================
# NON-EXISTENT ADMISSION
# =========================================================


def test_admission_api_nonexistent_admission():

    response = client.get(
        "/api/admissions/999999999"
    )

    print(
        "\n===== NON-EXISTENT ADMISSION API ====="
    )
    print(
        "Status Code:",
        response.status_code,
    )
    print(
        "Response:",
        response.json(),
    )

    assert response.status_code == 404

    assert (
        "not found"
        in response.json()["detail"].lower()
    )


# =========================================================
# INVALID ADMISSION ID
# =========================================================


def test_admission_api_invalid_admission_id():

    response = client.get(
        "/api/admissions/0"
    )

    assert response.status_code == 400

    assert (
        "positive integer"
        in response.json()["detail"]
    )


# =========================================================
# INVALID CREATE REQUEST
# =========================================================


def test_admission_api_invalid_create_request():

    response = client.post(
        "/api/admissions",
        json={
            "patient_id": "",
            "department_id": 1,
            "admission_type": "INVALID",
        },
    )

    print(
        "\n===== INVALID CREATE ADMISSION API ====="
    )
    print(
        "Status Code:",
        response.status_code,
    )
    print(
        "Response:",
        response.json(),
    )

    # Request reaches AdmissionTool validation.
    assert response.status_code == 400

    assert (
        "patient_id"
        in response.json()["detail"]
    )


# =========================================================
# INVALID STATUS
# =========================================================


def test_admission_api_invalid_status():

    admission = _fetch_one(
        """
        SELECT admission_id
        FROM admissions
        WHERE status IN ('ADMITTED', 'OBSERVATION')
        ORDER BY admission_id DESC
        LIMIT 1
        """
    )

    if admission is None:
        pytest.skip(
            "No active admission available."
        )

    admission_id = int(
        admission["admission_id"]
    )

    response = client.put(
        f"/api/admissions/{admission_id}/status",
        json={
            "new_status": "INVALID_STATUS"
        },
    )

    print(
        "\n===== INVALID ADMISSION STATUS API ====="
    )
    print(
        "Status Code:",
        response.status_code,
    )
    print(
        "Response:",
        response.json(),
    )

    assert response.status_code == 400

    assert (
        "invalid"
        in response.json()["detail"].lower()
    )