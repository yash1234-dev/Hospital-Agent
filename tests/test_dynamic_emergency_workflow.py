from app.agents.triage_agent import TriageAgent
from app.agents.emergency_agent import EmergencyAgent
from app.agents.bed_agent import BedAgent
from app.agents.staff_agent import StaffAgent

from app.tools.emergency_tool import EmergencyTool
from app.tools.bed_tool import BedTool
from app.tools.staff_tool import StaffTool

from app.models.agent_context import AgentContext
from app.orchestration.router import AgentRouter
from app.orchestration.orchestrator import Orchestrator

from app.database.connection import get_db_connection


def test_dynamic_emergency_workflow():

    # =========================================================
    # STEP 1: Select a patient without an assigned bed
    # =========================================================

    with get_db_connection() as connection:

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT p.ID AS patient_id
            FROM patients p
            WHERE p.DEATHDATE IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM beds b
                  WHERE b.patient_id = p.ID
              )
            LIMIT 1
            """
        )

        patient = cursor.fetchone()

        cursor.close()

    assert patient is not None

    patient_id = patient["patient_id"]

    # =========================================================
    # STEP 2: Select department
    # =========================================================

    department_id = 3

    # =========================================================
    # STEP 3: Create fresh admission
    # =========================================================

    with get_db_connection() as connection:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO admissions (
                patient_id,
                department_id,
                admission_type,
                admission_time,
                status,
                doctor_id
            )
            VALUES (
                %s,
                %s,
                'EMERGENCY',
                NOW(),
                'ADMITTED',
                NULL
            )
            """,
            (
                patient_id,
                department_id,
            ),
        )

        admission_id = cursor.lastrowid

        connection.commit()

        cursor.close()

    assert admission_id is not None
    assert admission_id > 0

    # =========================================================
    # STEP 4: Create fresh emergency incident
    # =========================================================

    with get_db_connection() as connection:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO emergency_incidents (
                patient_id,
                encounter_id,
                admission_id,
                department_id,
                incident_type,
                severity,
                incident_source,
                symptoms,
                incident_time,
                triage_time,
                triage_notes,
                status
            )
            VALUES (
                %s,
                NULL,
                %s,
                %s,
                'RESPIRATORY',
                'HIGH',
                'AI_DETECTED',
                'Severe respiratory distress',
                NOW(),
                NOW(),
                'High severity emergency requiring transport.',
                'TRIAGED'
            )
            """,
            (
                patient_id,
                admission_id,
                department_id,
            ),
        )

        incident_id = cursor.lastrowid

        connection.commit()

        cursor.close()

    assert incident_id is not None
    assert incident_id > 0

    print("\n==============================================")
    print(" DYNAMIC EMERGENCY WORKFLOW")
    print("==============================================")
    print("Patient ID:", patient_id)
    print("Admission ID:", admission_id)
    print("Incident ID:", incident_id)
    print("Department ID:", department_id)

    # =========================================================
    # STEP 5: Create real tools
    # =========================================================

    emergency_tool = EmergencyTool()
    bed_tool = BedTool()
    staff_tool = StaffTool()

    # =========================================================
    # STEP 6: Create real agents
    # =========================================================

    triage_agent = TriageAgent(
        emergency_tool=emergency_tool
    )

    emergency_agent = EmergencyAgent(
        emergency_tool=emergency_tool
    )

    bed_agent = BedAgent(
        bed_tool=bed_tool
    )

    staff_agent = StaffAgent(
        staff_tool=staff_tool
    )

    # =========================================================
    # STEP 7: Router
    # =========================================================

    router = AgentRouter(
        routes={
            "REQUEST_TRANSPORT": "EmergencyAgent",
            "ASSIGN_BED": "BedAgent",
            "ASSIGN_DOCTOR": "StaffAgent",
            "ASSIGN_NURSE": "StaffAgent",
            "NO_ACTION": None,
        }
    )

    # =========================================================
    # STEP 8: Orchestrator
    # =========================================================

    orchestrator = Orchestrator(
        workflow_name="Dynamic Emergency Workflow"
    )

    orchestrator.register_agent(
        triage_agent
    )

    orchestrator.register_agent(
        emergency_agent
    )

    orchestrator.register_agent(
        bed_agent
    )

    orchestrator.register_agent(
        staff_agent
    )

    # =========================================================
    # STEP 9: Shared context
    # =========================================================

    context = AgentContext(
        incident_id=incident_id,
        patient_id=patient_id,
        admission_id=admission_id,
        department_id=department_id,
    )

    # =========================================================
    # STEP 10: Dynamic workflow
    # =========================================================

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="TriageAgent",
        router=router,
        max_steps=5,
    )

    # =========================================================
    # STEP 11: Output
    # =========================================================

    print("\n==============================================")
    print(" WORKFLOW RESULT")
    print("==============================================")

    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", result.actions)
    print("Errors:", result.errors)

    print("\n==============================================")
    print(" CONTEXT")
    print("==============================================")

    print("Patient:", context.patient_id)
    print("Admission:", context.admission_id)
    print("Incident:", context.incident_id)
    print("Department:", context.department_id)

    print("\nDecisions:")
    print(context.decisions)

    print("\nActions:")
    print(context.actions)

    print("\n==============================================")
    print(" EXECUTION STATE")
    print("==============================================")

    print(
        orchestrator.get_state_dict()
    )

    # =========================================================
    # STEP 12: Assertions
    # =========================================================

    assert result.status == "SUCCESS", (
        f"Workflow failed: "
        f"{result.reason} | "
        f"{result.errors}"
    )

    assert result.decision == "NO_ACTION"

    assert orchestrator.state.status == "COMPLETED"

    assert orchestrator.state.completed_agents == [
        "TriageAgent",
        "EmergencyAgent",
        "BedAgent",
        "StaffAgent",
    ]

    assert len(
        orchestrator.state.failed_agents
    ) == 0

    assert len(context.decisions) == 4

    assert context.decisions[0]["decision"] == (
        "REQUEST_TRANSPORT"
    )

    assert context.decisions[1]["decision"] == (
        "ASSIGN_BED"
    )

    assert context.decisions[2]["decision"] == (
        "ASSIGN_DOCTOR"
    )

    assert context.decisions[3]["decision"] == (
        "NO_ACTION"
    )

    assert len(context.actions) >= 3

    print("\n==============================================")
    print(" DYNAMIC EMERGENCY WORKFLOW PASSED")
    print("==============================================")