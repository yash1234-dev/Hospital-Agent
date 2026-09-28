import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agents.base_agent import BaseAgent
from app.models.agent_result import AgentResult
from app.orchestration.router import AgentRouter
from app.orchestration.orchestrator import Orchestrator
from app.agents.bed_agent import BedAgent
from app.models.agent_context import AgentContext


class FakeBedTool:

    def __init__(self, reservation_status="COMPLETED"):
        self.reservation_status = reservation_status
        self.calls = []

    def run(self, operation, **kwargs):

        self.calls.append({
            "operation": operation,
            "kwargs": kwargs,
        })

        if operation == "get_available_beds":
            return [
                {
                    "bed_id": 128,
                    "bed_number": "ER-4-C",
                    "bed_type": "EMERGENCY",
                    "room_type": "Emergency",
                    "department_id": 1,
                }
            ]

        if operation == "reserve_bed":

            if self.reservation_status == "COMPLETED":
                return {
                    "execution_status": "COMPLETED",
                    "validation_status": "VALIDATED",
                    "result_payload": {
                        "action": "RESERVE_BED",
                        "bed_id": kwargs["bed_id"],
                        "patient_id": kwargs["patient_id"],
                        "status": "RESERVED",
                    },
                }

            return {
                "execution_status": "FAILED",
                "validation_status": "REJECTED",
                "error_message": "Bed reservation failed.",
            }

        raise ValueError(f"Unsupported fake operation: {operation}")


def test_bed_agent_success():

    fake_tool = FakeBedTool()

    agent = BedAgent(bed_tool=fake_tool)

    context = AgentContext(
        patient_id="test-patient-001",
        admission_id=1,
        department_id=1,
    )

    result = agent.run(context)

    print("\n===== TEST 1: SUCCESS =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", result.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "ASSIGN_DOCTOR"

    assert len(result.actions) == 1
    assert result.actions[0]["action"] == "RESERVE_BED"
    assert result.actions[0]["status"] == "COMPLETED"

    assert len(context.actions) == 1

    assert fake_tool.calls[0]["operation"] == "get_available_beds"
    assert fake_tool.calls[1]["operation"] == "reserve_bed"

    print("TEST 1 PASSED")


def test_bed_agent_no_available_bed():

    class NoBedTool:

        def run(self, operation, **kwargs):

            if operation == "get_available_beds":
                return []

            raise AssertionError(
                "reserve_bed should not be called when no bed exists."
            )

    agent = BedAgent(bed_tool=NoBedTool())

    context = AgentContext(
        patient_id="test-patient-002",
        admission_id=2,
        department_id=1,
    )

    result = agent.run(context)

    print("\n===== TEST 2: NO BED =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"
    assert len(result.actions) == 0

    print("TEST 2 PASSED")


def test_bed_agent_missing_patient():

    fake_tool = FakeBedTool()

    agent = BedAgent(bed_tool=fake_tool)

    context = AgentContext(
        patient_id=None,
        department_id=1,
    )

    result = agent.run(context)

    print("\n===== TEST 3: MISSING PATIENT =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "FAILED"

    print("TEST 3 PASSED")


def test_bed_agent_reservation_failure():

    fake_tool = FakeBedTool(
        reservation_status="FAILED"
    )

    agent = BedAgent(bed_tool=fake_tool)

    context = AgentContext(
        patient_id="test-patient-004",
        department_id=1,
    )

    result = agent.run(context)

    print("\n===== TEST 4: RESERVATION FAILURE =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "FAILED"
    assert len(context.actions) == 0

    print("TEST 4 PASSED")
    


    from app.tools.bed_tool import BedTool

    patient_id = "99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"

    bed_tool = BedTool()

    agent = BedAgent(
        bed_tool=bed_tool
    )

    context = AgentContext(
        patient_id=patient_id,
    )

    result = agent.run(context)

    print("\n===== REAL DATABASE BED TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", result.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert len(result.actions) == 1

    action = result.actions[0]

    assert action["agent"] == "BedAgent"
    assert action["action"] == "RESERVE_BED"
    assert action["status"] == "COMPLETED"

    reserved_bed_id = action["bed_id"]

    print("\nReserved Bed ID:", reserved_bed_id)

    assert reserved_bed_id > 0

    print("\nREAL DATABASE BED TEST PASSED")    
def test_bed_agent_real_database():

    from app.tools.bed_tool import BedTool
    from app.database.connection import get_db_connection

    # ---------------------------------------------------------
# STEP 1: Select a clean patient with no currently assigned bed
# ---------------------------------------------------------
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
                   AND b.status IN ('OCCUPIED', 'RESERVED')
            )
            LIMIT 1
            """
        )

        patient = cursor.fetchone()
        cursor.close()

    assert patient is not None, "No patient without an assigned bed was found."

    patient_id = patient["patient_id"]

    department_id = 3

    # ---------------------------------------------------------
    # STEP 1: Create a fresh controlled admission
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # STEP 2: Create real BedAgent
    # ---------------------------------------------------------

    bed_tool = BedTool()

    agent = BedAgent(
        bed_tool=bed_tool
    )

    context = AgentContext(
        patient_id=patient_id,
        admission_id=admission_id,
        department_id=department_id,
    )

    # ---------------------------------------------------------
    # STEP 3: Run BedAgent
    # ---------------------------------------------------------

    result = agent.run(context)

    print("\n===== REAL DATABASE BED TEST =====")
    print("Admission ID:", admission_id)
    print("Patient ID:", patient_id)
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", result.actions)

    # ---------------------------------------------------------
    # STEP 4: Verify AgentResult
    # ---------------------------------------------------------

    assert result.status == "SUCCESS"
    assert result.decision == "ASSIGN_DOCTOR"

    assert len(result.actions) == 1

    action = result.actions[0]

    assert action["agent"] == "BedAgent"
    assert action["action"] == "RESERVE_BED"
    assert action["status"] == "COMPLETED"

    reserved_bed_id = action["bed_id"]

    print("\nReserved Bed ID:", reserved_bed_id)

    assert reserved_bed_id > 0

    # ---------------------------------------------------------
    # STEP 5: Verify actual database mutation
    # ---------------------------------------------------------

    with get_db_connection() as connection:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                admission_id,
                patient_id,
                department_id,
                bed_id,
                status
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        admission = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                bed_id,
                status,
                patient_id
            FROM beds
            WHERE bed_id = %s
            """,
            (reserved_bed_id,),
        )

        bed = cursor.fetchone()

        cursor.close()

    print("\n--- DATABASE VERIFICATION ---")
    print("Admission:", admission)
    print("Bed:", bed)

    assert admission is not None
    assert admission["admission_id"] == admission_id
    assert admission["patient_id"] == patient_id
    assert admission["department_id"] == department_id
    assert admission["bed_id"] == reserved_bed_id
    assert admission["status"] == "ADMITTED"

    assert bed is not None
    assert bed["bed_id"] == reserved_bed_id
    assert bed["status"] == "RESERVED"
    assert bed["patient_id"] == patient_id

    print("\nREAL DATABASE BED TEST PASSED")  
from app.agents.staff_agent import StaffAgent


class FakeStaffTool:

    def __init__(self, assignment_status="COMPLETED"):
        self.assignment_status = assignment_status
        self.calls = []

    def run(self, operation, **kwargs):

        self.calls.append({
            "operation": operation,
            "kwargs": kwargs,
        })

        if operation == "get_available_doctors":
            return [
                {
                    "doctor_id": 20,
                    "doctor_name": "Test Doctor",
                    "department_id": 3,
                }
            ]

        if operation == "get_available_nurses":
            return [
                {
                    "nurse_id": 4,
                    "nurse_name": "Test Nurse",
                    "department_id": 3,
                }
            ]

        if operation == "assign_doctor":

            if self.assignment_status == "COMPLETED":
                return {
                    "execution_status": "COMPLETED",
                    "validation_status": "VALIDATED",
                    "result_payload": {
                        "action": "ASSIGN_DOCTOR",
                        "admission_id": kwargs["admission_id"],
                        "doctor_id": kwargs["doctor_id"],
                        "status": "ASSIGNED",
                    },
                }

            return {
                "execution_status": "FAILED",
                "validation_status": "REJECTED",
                "error_message": "Doctor assignment failed.",
            }

        if operation == "assign_nurse":

            if self.assignment_status == "COMPLETED":
                return {
                    "execution_status": "COMPLETED",
                    "validation_status": "VALIDATED",
                    "result_payload": {
                        "action": "ASSIGN_NURSE",
                        "admission_id": kwargs["admission_id"],
                        "nurse_id": kwargs["nurse_id"],
                        "status": "ASSIGNED",
                    },
                }

            return {
                "execution_status": "FAILED",
                "validation_status": "REJECTED",
                "error_message": "Nurse assignment failed.",
            }

        raise ValueError(
            f"Unsupported fake operation: {operation}"
        )


def test_staff_agent_assign_doctor():

    fake_tool = FakeStaffTool()

    agent = StaffAgent(
        staff_tool=fake_tool
    )

    context = AgentContext(
        admission_id=136,
        department_id=3,
    )

    context.add_decision({
        "agent": "TestAgent",
        "decision": "ASSIGN_DOCTOR",
        "reason": "Admission requires a doctor.",
    })

    result = agent.run(context)

    print("\n===== STAFF TEST 1: DOCTOR =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Actions:", result.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert len(result.actions) == 1

    assert result.actions[0]["agent"] == "StaffAgent"
    assert result.actions[0]["action"] == "ASSIGN_DOCTOR"
    assert result.actions[0]["status"] == "COMPLETED"

    assert fake_tool.calls[0]["operation"] == "get_available_doctors"
    assert fake_tool.calls[1]["operation"] == "assign_doctor"

    print("STAFF TEST 1 PASSED")


def test_staff_agent_assign_nurse():

    fake_tool = FakeStaffTool()

    agent = StaffAgent(
        staff_tool=fake_tool
    )

    context = AgentContext(
        admission_id=136,
        department_id=3,
    )

    context.add_decision({
        "agent": "TestAgent",
        "decision": "ASSIGN_NURSE",
        "reason": "Admission requires a nurse.",
    })

    result = agent.run(context)

    print("\n===== STAFF TEST 2: NURSE =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Actions:", result.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert len(result.actions) == 1

    assert result.actions[0]["agent"] == "StaffAgent"
    assert result.actions[0]["action"] == "ASSIGN_NURSE"
    assert result.actions[0]["status"] == "COMPLETED"

    assert fake_tool.calls[0]["operation"] == "get_available_nurses"
    assert fake_tool.calls[1]["operation"] == "assign_nurse"

    print("STAFF TEST 2 PASSED")


def test_staff_agent_missing_admission():

    fake_tool = FakeStaffTool()

    agent = StaffAgent(
        staff_tool=fake_tool
    )

    context = AgentContext(
        department_id=3,
    )

    context.add_decision({
        "agent": "TestAgent",
        "decision": "ASSIGN_DOCTOR",
        "reason": "Test.",
    })

    result = agent.run(context)

    print("\n===== STAFF TEST 3: MISSING ADMISSION =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "FAILED"

    print("STAFF TEST 3 PASSED")


def test_staff_agent_missing_decision():

    fake_tool = FakeStaffTool()

    agent = StaffAgent(
        staff_tool=fake_tool
    )

    context = AgentContext(
        admission_id=136,
        department_id=3,
    )

    result = agent.run(context)

    print("\n===== STAFF TEST 4: MISSING DECISION =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "FAILED"

    print("STAFF TEST 4 PASSED")  
def test_staff_agent_real_doctor_assignment():
    from app.tools.staff_tool import StaffTool

    admission_id = 148

    staff_tool = StaffTool()
    agent = StaffAgent(staff_tool=staff_tool)

    context = AgentContext(
        admission_id=admission_id,
        department_id=3
    )

    context.add_decision({
        "agent": "TestAgent",
        "decision": "ASSIGN_DOCTOR",
        "reason": "Admission requires doctor assignment."
    })

    result = agent.run(context)

    print("\n--- REAL STAFF AGENT DOCTOR TEST ---")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Actions:", result.actions)
    print("Errors:", result.errors)
    
    print("\nFULL RESULT OBJECT:")
    print(result)
    print("\nRESULT DICT:")
    print(vars(result))

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert len(result.actions) == 1

    action = result.actions[0]

    assert action["agent"] == "StaffAgent"
    assert action["action"] == "ASSIGN_DOCTOR"
    assert action["status"] == "COMPLETED"
    assert action["admission_id"] == admission_id
    assert action["doctor_id"] > 0     
    
def test_staff_tool_real_doctor_assignment():
    from app.tools.staff_tool import StaffTool

    staff_tool = StaffTool()

    result = staff_tool.assign_doctor(
        admission_id=148,
        doctor_id=4,
        requested_by_agent="StaffAgent"
    )

    print("\n--- DIRECT STAFF TOOL DOCTOR TEST ---")
    print("Result:", result)
    print("Result type:", type(result))

    if result is not None:
        print("Result dict:", vars(result) if hasattr(result, "__dict__") else result)
        
def test_staff_tool_real_doctor_availability_today():
    from app.tools.staff_tool import StaffTool
    from datetime import date

    staff_tool = StaffTool()

    doctors = staff_tool.get_available_doctors(
        department_id=3
    )

    print("\n--- REAL STAFF TOOL DOCTOR AVAILABILITY ---")
    print("Today:", date.today())
    print("Doctors returned:", len(doctors))

    for doctor in doctors[:10]:
        print(
            doctor["doctor_id"],
            doctor["doctor_name"],
            doctor["department_id"],
            doctor["schedule_date"],
            doctor["shift_type"],
            doctor["schedule_status"],
        )

    assert len(doctors) > 0

    for doctor in doctors:
        assert doctor["department_id"] == 3
        assert doctor["schedule_date"] == date.today()
        assert doctor["schedule_status"] == "AVAILABLE"
        assert doctor["employment_status"] == "ACTIVE"    
        
        
def test_staff_agent_real_doctor_selection_today():
    from app.tools.staff_tool import StaffTool
    from datetime import date

    staff_tool = StaffTool()
    agent = StaffAgent(staff_tool=staff_tool)

    context = AgentContext(
        admission_id=148,
        department_id=3
    )

    context.add_decision({
        "agent": "TestAgent",
        "decision": "ASSIGN_DOCTOR",
        "reason": "Verify doctor selection uses today's schedule."
    })

    # Directly test StaffAgent's processing logic.
    # This will NOT perform the assignment because we only
    # inspect the doctor-selection portion through the tool.
    doctors = staff_tool.get_available_doctors(
        department_id=3
    )

    print("\n--- STAFF AGENT DOCTOR SELECTION DATA ---")
    print("Today:", date.today())
    print("Available doctors:", len(doctors))

    assert len(doctors) > 0

    selected_doctor = doctors[0]

    print("Selected doctor:")
    print(selected_doctor)

    assert selected_doctor["department_id"] == 3
    assert selected_doctor["schedule_date"] == date.today()
    assert selected_doctor["schedule_status"] == "AVAILABLE"
    assert selected_doctor["employment_status"] == "ACTIVE"  
    
class FakeAdmissionAgent(BaseAgent):

    def __init__(self):
        super().__init__(agent_name="AdmissionAgent")

    def process(self, context):
        return AgentResult(
            status="SUCCESS",
            decision="ASSIGN_DOCTOR",
            reason="Admission requires doctor assignment."
        )
        
def test_orchestrator_routes_to_staff_agent():

    admission_agent = FakeAdmissionAgent()

    class FakeStaffAgent(BaseAgent):

        def __init__(self):
            super().__init__(agent_name="StaffAgent")

        def process(self, context):
            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason="Staff assignment completed."
            )

    staff_agent = FakeStaffAgent()

    router = AgentRouter(
        routes={
            "ASSIGN_DOCTOR": "StaffAgent",
            "ASSIGN_NURSE": "StaffAgent",
            "NO_ACTION": None,
        }
    )

    orchestrator = Orchestrator(
        workflow_name="staff_routing_test"
    )

    orchestrator.register_agent(admission_agent)
    orchestrator.register_agent(staff_agent)

    context = AgentContext(
        admission_id=999,
        department_id=3
    )

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="AdmissionAgent",
        router=router,
        max_steps=5
    )

    print("\n===== DYNAMIC STAFF ROUTING TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Execution State:")
    print(orchestrator.get_state_dict())

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    state = orchestrator.get_state_dict()

    assert "AdmissionAgent" in state["completed_agents"]
    assert "StaffAgent" in state["completed_agents"]

    assert state["status"] == "COMPLETED"

    print("DYNAMIC STAFF ROUTING TEST PASSED")    
    
    
def test_real_dynamic_staff_agent_doctor_assignment():

    from app.agents.staff_agent import StaffAgent
    from app.tools.staff_tool import StaffTool
    from app.database.connection import get_db_connection

    patient_id = "99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"
    department_id = 3

    # ---------------------------------------------------------
    # STEP 1: Create a fresh controlled admission
    # ---------------------------------------------------------

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

    print("\n===== REAL DYNAMIC STAFF WORKFLOW =====")
    print("Created Admission ID:", admission_id)
    print("Department ID:", department_id)

    assert admission_id is not None
    assert admission_id > 0

    # ---------------------------------------------------------
    # STEP 2: Create real StaffAgent
    # ---------------------------------------------------------

    staff_tool = StaffTool()

    staff_agent = StaffAgent(
        staff_tool=staff_tool
    )

    # ---------------------------------------------------------
    # STEP 3: Create router
    # ---------------------------------------------------------

    router = AgentRouter(
        routes={
            "ASSIGN_DOCTOR": "StaffAgent",
            "ASSIGN_NURSE": "StaffAgent",
            "NO_ACTION": None,
        }
    )

    # ---------------------------------------------------------
    # STEP 4: Create orchestrator
    # ---------------------------------------------------------

    orchestrator = Orchestrator(
        workflow_name="real_staff_assignment"
    )

    # Register the existing FakeAdmissionAgent
    admission_agent = FakeAdmissionAgent()

    orchestrator.register_agent(
        admission_agent
    )

    orchestrator.register_agent(
        staff_agent
    )

    # ---------------------------------------------------------
    # STEP 5: Create shared context
    # ---------------------------------------------------------

    context = AgentContext(
        patient_id=patient_id,
        admission_id=admission_id,
        department_id=department_id,
    )

    # ---------------------------------------------------------
    # STEP 6: Run REAL dynamic workflow
    # ---------------------------------------------------------

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="AdmissionAgent",
        router=router,
        max_steps=5,
    )

    # ---------------------------------------------------------
    # STEP 7: Print orchestration result
    # ---------------------------------------------------------

    print("\n--- ORCHESTRATOR RESULT ---")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Actions:", result.actions)
    print("Errors:", result.errors)

    print("\n--- EXECUTION STATE ---")
    print(orchestrator.get_state_dict())

    # ---------------------------------------------------------
    # STEP 8: Verify orchestration
    # ---------------------------------------------------------

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert len(result.actions) == 1

    action = result.actions[0]

    assert action["agent"] == "StaffAgent"
    assert action["action"] == "ASSIGN_DOCTOR"
    assert action["status"] == "COMPLETED"
    assert action["admission_id"] == admission_id
    assert action["doctor_id"] > 0

    state = orchestrator.get_state_dict()

    assert state["status"] == "COMPLETED"

    assert "AdmissionAgent" in state["completed_agents"]
    assert "StaffAgent" in state["completed_agents"]

    # ---------------------------------------------------------
    # STEP 9: Verify actual MySQL mutation
    # ---------------------------------------------------------

    with get_db_connection() as connection:

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                admission_id,
                patient_id,
                department_id,
                doctor_id,
                status
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        admission = cursor.fetchone()

        cursor.close()

    print("\n--- DATABASE VERIFICATION ---")
    print("Admission:", admission)

    assert admission is not None

    assert admission["admission_id"] == admission_id
    assert admission["patient_id"] == patient_id
    assert admission["department_id"] == department_id
    assert admission["status"] == "ADMITTED"

    assert admission["doctor_id"] == action["doctor_id"]
    assert admission["doctor_id"] > 0

    print("\nREAL DYNAMIC STAFF WORKFLOW PASSED")
    print("Admission ID:", admission_id)
    print("Assigned Doctor ID:", admission["doctor_id"])
    
def test_emergency_agent_routes_to_bed_after_transport():
    from app.agents.emergency_agent import EmergencyAgent

    class FakeEmergencyTool:
        def __init__(self):
            self.calls = []

        def run(self, operation, **kwargs):
            self.calls.append({
                "operation": operation,
                **kwargs,
            })

            if operation == "request_transport":
                return {
                    "gateway_request_id": 999,
                    "validation_status": "VALIDATED",
                    "execution_status": "COMPLETED",
                    "result_payload": {
                        "action": "REQUEST_TRANSPORT",
                        "status": "REQUESTED",
                    },
                    "error_message": None,
                }

            return {
                "gateway_request_id": None,
                "validation_status": "REJECTED",
                "execution_status": "FAILED",
                "result_payload": None,
                "error_message": f"Unsupported operation: {operation}",
            }

    context = AgentContext(
        patient_id="test-patient",
        incident_id=12,
        department_id=3,
    )

    context.add_decision({
        "decision": "REQUEST_TRANSPORT",
        "reason": "Emergency transport required.",
    })

    fake_tool = FakeEmergencyTool()
    agent = EmergencyAgent(emergency_tool=fake_tool)

    result = agent.run(context)

    print("\n===== EMERGENCY AGENT ROUTING TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Actions:", context.actions)
    print("Errors:", context.errors)
    print("Tool Calls:", fake_tool.calls)

    assert result.status == "SUCCESS"
    assert result.decision == "ASSIGN_BED"

    assert len(fake_tool.calls) == 1
    assert fake_tool.calls[0]["operation"] == "request_transport"
    assert fake_tool.calls[0]["incident_id"] == 12

    print("EMERGENCY AGENT ROUTING TEST PASSED")  
    
    
def test_orchestrator_routes_bed_agent_to_staff_agent():
    from app.agents.base_agent import BaseAgent
    from app.agents.bed_agent import BedAgent
    from app.agents.staff_agent import StaffAgent
    from app.models.agent_result import AgentResult
    from app.orchestration.router import AgentRouter
    from app.orchestration.orchestrator import Orchestrator

    class FakeBedTool:
        def run(self, operation, **kwargs):
            if operation == "get_available_beds":
                return [
                    {
                        "bed_id": 101,
                        "bed_number": "TEST-101",
                        "bed_type": "EMERGENCY",
                        "room_type": "Emergency",
                        "department_id": 1,
                    }
                ]

            if operation == "reserve_bed":
                return {
                    "gateway_request_id": 1001,
                    "validation_status": "VALIDATED",
                    "execution_status": "COMPLETED",
                    "result_payload": {
                        "action": "RESERVE_BED",
                        "bed_id": kwargs["bed_id"],
                        "patient_id": kwargs["patient_id"],
                        "status": "RESERVED",
                    },
                    "error_message": None,
                }

            raise ValueError(f"Unsupported operation: {operation}")

    class FakeStaffTool:
        def run(self, operation, **kwargs):
            if operation == "get_available_doctors":
                return [
                    {
                        "doctor_id": 1,
                        "doctor_name": "Test Doctor",
                        "department_id": 1,
                        "employment_status": "ACTIVE",
                    }
                ]

            if operation == "assign_doctor":
                return {
                    "gateway_request_id": 1002,
                    "validation_status": "VALIDATED",
                    "execution_status": "COMPLETED",
                    "result_payload": {
                        "action": "ASSIGN_DOCTOR",
                        "admission_id": kwargs["admission_id"],
                        "doctor_id": kwargs["doctor_id"],
                        "status": "ASSIGNED",
                    },
                    "error_message": None,
                }

            raise ValueError(f"Unsupported operation: {operation}")

    class FakeAdmissionAgent(BaseAgent):
        def __init__(self):
            super().__init__(agent_name="AdmissionAgent")

        def process(self, context):
            return AgentResult(
                status="SUCCESS",
                decision="ASSIGN_BED",
                reason="Admission requires bed assignment.",
            )

    class FakeStaffAgent(StaffAgent):
        def process(self, context):
            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason="Doctor assignment completed.",
            )

    context = AgentContext(
        patient_id="test-patient-002",
        admission_id=999,
        department_id=1,
    )

    bed_agent = BedAgent(
        bed_tool=FakeBedTool()
    )

    staff_agent = FakeStaffAgent(
        staff_tool=FakeStaffTool()
    )

    admission_agent = FakeAdmissionAgent()

    router = AgentRouter(
        routes={
            "ASSIGN_BED": "BedAgent",
            "ASSIGN_DOCTOR": "StaffAgent",
            "NO_ACTION": None,
        }
    )

    orchestrator = Orchestrator(
        workflow_name="bed_to_staff_routing_test"
    )

    orchestrator.register_agent(admission_agent)
    orchestrator.register_agent(bed_agent)
    orchestrator.register_agent(staff_agent)

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="AdmissionAgent",
        router=router,
    )

    print("\n===== BED → STAFF DYNAMIC ROUTING TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Actions:", result.actions)
    print("Errors:", result.errors)

    print("\n===== EXECUTION STATE =====")
    print(orchestrator.state.to_dict())

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert orchestrator.state.status == "COMPLETED"

    assert orchestrator.state.completed_agents == [
        "AdmissionAgent",
        "BedAgent",
        "StaffAgent",
    ]

    assert len(orchestrator.state.failed_agents) == 0

    assert orchestrator.state.execution_history == [
        {
            "agent": "AdmissionAgent",
            "status": "SUCCESS",
        },
        {
            "agent": "BedAgent",
            "status": "SUCCESS",
        },
        {
            "agent": "StaffAgent",
            "status": "SUCCESS",
        },
    ]

    print("BED → STAFF DYNAMIC ROUTING TEST PASSED")    
    
    
    
def test_dynamic_workflow_preserves_agent_decisions():
    from app.agents.base_agent import BaseAgent
    from app.models.agent_result import AgentResult
    from app.orchestration.router import AgentRouter
    from app.orchestration.orchestrator import Orchestrator

    class FirstAgent(BaseAgent):
        def __init__(self):
            super().__init__(agent_name="FirstAgent")

        def process(self, context):
            return AgentResult(
                status="SUCCESS",
                decision="NEXT_AGENT",
                reason="First agent completed.",
            )

    class SecondAgent(BaseAgent):
        def __init__(self):
            super().__init__(agent_name="SecondAgent")

        def process(self, context):
            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason="Second agent completed.",
            )

    context = AgentContext(
        patient_id="test-patient",
    )

    router = AgentRouter(
        routes={
            "NEXT_AGENT": "SecondAgent",
            "NO_ACTION": None,
        }
    )

    orchestrator = Orchestrator(
        workflow_name="decision_propagation_test"
    )

    orchestrator.register_agent(FirstAgent())
    orchestrator.register_agent(SecondAgent())

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="FirstAgent",
        router=router,
    )

    print("\n===== DECISION PROPAGATION TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Context decisions:", context.decisions)

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert len(context.decisions) == 2
    assert context.decisions[0]["decision"] == "NEXT_AGENT"
    assert context.decisions[1]["decision"] == "NO_ACTION"

    print("DECISION PROPAGATION TEST PASSED")     
    
def test_dynamic_bed_to_staff_workflow():
    from app.agents.base_agent import BaseAgent
    from app.models.agent_result import AgentResult
    from app.orchestration.router import AgentRouter
    from app.orchestration.orchestrator import Orchestrator

    class FakeStaffAgent(BaseAgent):
        def __init__(self):
            super().__init__(agent_name="StaffAgent")

        def process(self, context):
            # Verify that BedAgent actually stored the reserved bed.
            assert "reserved_bed" in context.data
            assert context.data["reserved_bed"]["bed_id"] == 128

            # Verify that BedAgent recorded its action.
            assert len(context.actions) == 1
            assert context.actions[0]["action"] == "RESERVE_BED"
            assert context.actions[0]["status"] == "COMPLETED"

            action = {
                "agent": "StaffAgent",
                "action": "ASSIGN_DOCTOR",
                "status": "COMPLETED",
                "admission_id": context.admission_id,
                "doctor_id": 20,
            }

            context.add_action(action)
            context.add_data(
                "assigned_doctor",
                {
                    "doctor_id": 20,
                    "doctor_name": "Test Doctor",
         },
            )

            return AgentResult(
                status="SUCCESS",
                decision="NO_ACTION",
                reason="Doctor successfully assigned after bed reservation.",
                data={
                    "assigned_doctor": {
                        "doctor_id": 20,
                        "doctor_name": "Test Doctor",
                    }
                },
                actions=[action],
            )

    # ---------------------------------------------------------
    # BedAgent uses the existing fake BedTool.
    # No real database mutation occurs.
    # ---------------------------------------------------------
    bed_agent = BedAgent(
        bed_tool=FakeBedTool()
    )

    staff_agent = FakeStaffAgent()

    # ---------------------------------------------------------
    # Router
    # ---------------------------------------------------------
    router = AgentRouter(
        routes={
            "ASSIGN_DOCTOR": "StaffAgent",
            "ASSIGN_NURSE": "StaffAgent",
            "NO_ACTION": None,
        }
    )

    # ---------------------------------------------------------
    # Register agents
    # ---------------------------------------------------------
    orchestrator = Orchestrator(
        workflow_name="bed_to_staff_routing_test"
    )

    orchestrator.register_agent(bed_agent)
    orchestrator.register_agent(staff_agent)

    # ---------------------------------------------------------
    # Shared context
    # ---------------------------------------------------------
    context = AgentContext(
        patient_id="test-patient-bed-staff",
        admission_id=999,
        department_id=1,
    )

    # ---------------------------------------------------------
    # Run dynamic workflow
    # ---------------------------------------------------------
    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="BedAgent",
        router=router,
    )

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------
    print("\n===== BED TO STAFF DYNAMIC WORKFLOW =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Context Data:", context.data)
    print("Context Actions:", context.actions)
    print("Execution State:", orchestrator.state.to_dict())

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------
    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert len(context.actions) == 2

    assert context.actions[0]["agent"] == "BedAgent"
    assert context.actions[0]["action"] == "RESERVE_BED"
    assert context.actions[0]["status"] == "COMPLETED"

    assert context.actions[1]["agent"] == "StaffAgent"
    assert context.actions[1]["action"] == "ASSIGN_DOCTOR"
    assert context.actions[1]["status"] == "COMPLETED"

    assert "reserved_bed" in context.data
    assert context.data["reserved_bed"]["bed_id"] == 128

    assert context.data["assigned_doctor"]["doctor_id"] == 20

    # Both agents must have executed exactly once.
    assert orchestrator.state.completed_agents == [
        "BedAgent",
        "StaffAgent",
    ]

    print("BED TO STAFF DYNAMIC WORKFLOW PASSED")    
    
    
def test_real_dynamic_bed_to_staff_workflow():

    from app.tools.bed_tool import BedTool
    from app.tools.staff_tool import StaffTool
    from app.database.connection import get_db_connection

    patient_id = None
    department_id = 3

# ---------------------------------------------------------
# STEP 1: Select a clean patient with no assigned bed
# ---------------------------------------------------------
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
              AND b.status IN ('OCCUPIED', 'RESERVED')
        )
        LIMIT 1
        """
    )

    patient = cursor.fetchone()
    cursor.close()

    assert patient is not None, "No patient without an assigned bed was found."

    patient_id = patient["patient_id"]

    # ---------------------------------------------------------
    # STEP 1: Create a fresh controlled admission
    # ---------------------------------------------------------

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

    print("\n===== REAL BED → STAFF WORKFLOW =====")
    print("Created Admission ID:", admission_id)
    print("Department ID:", department_id)

    assert admission_id is not None
    assert admission_id > 0

    # ---------------------------------------------------------
    # STEP 2: Create real agents
    # ---------------------------------------------------------

    bed_agent = BedAgent(
        bed_tool=BedTool()
    )

    staff_agent = StaffAgent(
        staff_tool=StaffTool()
    )

    # ---------------------------------------------------------
    # STEP 3: AdmissionAgent
    # ---------------------------------------------------------

    class RealWorkflowAdmissionAgent(BaseAgent):

        def __init__(self):
            super().__init__(
                agent_name="AdmissionAgent"
            )

        def process(self, context):

            return AgentResult(
                status="SUCCESS",
                decision="ASSIGN_BED",
                reason="Admission requires bed assignment.",
            )

    admission_agent = RealWorkflowAdmissionAgent()

    # ---------------------------------------------------------
    # STEP 4: Router
    # ---------------------------------------------------------

    router = AgentRouter(
        routes={
            "ASSIGN_BED": "BedAgent",
            "ASSIGN_DOCTOR": "StaffAgent",
            "ASSIGN_NURSE": "StaffAgent",
            "NO_ACTION": None,
        }
    )

    # ---------------------------------------------------------
    # STEP 5: Orchestrator
    # ---------------------------------------------------------

    orchestrator = Orchestrator(
        workflow_name="real_bed_to_staff_workflow"
    )

    orchestrator.register_agent(
        admission_agent
    )

    orchestrator.register_agent(
        bed_agent
    )

    orchestrator.register_agent(
        staff_agent
    )

    # ---------------------------------------------------------
    # STEP 6: Shared context
    # ---------------------------------------------------------

    context = AgentContext(
        patient_id=patient_id,
        admission_id=admission_id,
        department_id=department_id,
    )

    # ---------------------------------------------------------
    # STEP 7: Run complete dynamic workflow
    # ---------------------------------------------------------

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="AdmissionAgent",
        router=router,
        max_steps=5,
    )

    # ---------------------------------------------------------
    # STEP 8: Print result
    # ---------------------------------------------------------

    print("\n--- ORCHESTRATOR RESULT ---")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", result.actions)
    print("Errors:", result.errors)

    print("\n--- CONTEXT DATA ---")
    print(context.data)

    print("\n--- CONTEXT ACTIONS ---")
    print(context.actions)

    print("\n--- CONTEXT DECISIONS ---")
    print(context.decisions)

    print("\n--- EXECUTION STATE ---")
    print(orchestrator.get_state_dict())

    # ---------------------------------------------------------
    # STEP 9: Verify overall workflow
    # ---------------------------------------------------------

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    assert orchestrator.state.status == "COMPLETED"

    assert orchestrator.state.completed_agents == [
        "AdmissionAgent",
        "BedAgent",
        "StaffAgent",
    ]

    assert len(orchestrator.state.failed_agents) == 0

    # ---------------------------------------------------------
    # STEP 10: Verify BedAgent action
    # ---------------------------------------------------------

    bed_actions = [
        action
        for action in context.actions
        if action["agent"] == "BedAgent"
    ]

    assert len(bed_actions) == 1

    bed_action = bed_actions[0]

    assert bed_action["action"] == "RESERVE_BED"
    assert bed_action["status"] == "COMPLETED"
    assert bed_action["bed_id"] > 0

    assert "reserved_bed" in context.data

    reserved_bed = context.data["reserved_bed"]

    assert reserved_bed["bed_id"] == bed_action["bed_id"]

    print("\nReserved Bed ID:", bed_action["bed_id"])

    # ---------------------------------------------------------
    # STEP 11: Verify StaffAgent action
    # ---------------------------------------------------------

    staff_actions = [
        action
        for action in context.actions
        if action["agent"] == "StaffAgent"
    ]

    assert len(staff_actions) == 1

    staff_action = staff_actions[0]

    assert staff_action["action"] == "ASSIGN_DOCTOR"
    assert staff_action["status"] == "COMPLETED"
    assert staff_action["admission_id"] == admission_id
    assert staff_action["doctor_id"] > 0

    print("Assigned Doctor ID:", staff_action["doctor_id"])

    # ---------------------------------------------------------
    # STEP 12: Verify decision chain
    # ---------------------------------------------------------

    assert context.decisions[0]["decision"] == "ASSIGN_BED"
    assert context.decisions[1]["decision"] == "ASSIGN_DOCTOR"
    assert context.decisions[2]["decision"] == "NO_ACTION"

    # ---------------------------------------------------------
    # STEP 13: Verify actual MySQL admission mutation
    # ---------------------------------------------------------

    with get_db_connection() as connection:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                admission_id,
                patient_id,
                department_id,
                bed_id,
                doctor_id,
                status
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        admission = cursor.fetchone()

        cursor.close()

    print("\n--- DATABASE VERIFICATION ---")
    print("Admission:", admission)

    assert admission is not None

    assert admission["admission_id"] == admission_id
    assert admission["patient_id"] == patient_id
    assert admission["department_id"] == department_id
    assert admission["status"] == "ADMITTED"

    # Doctor must have been assigned by StaffAgent.
    assert admission["doctor_id"] == staff_action["doctor_id"]
    assert admission["doctor_id"] > 0

    # Bed reservation should be reflected in the admission.
    assert admission["bed_id"] == bed_action["bed_id"]

    print("\nREAL BED → STAFF WORKFLOW PASSED")
    print("Admission ID:", admission_id)
    print("Reserved Bed ID:", admission["bed_id"])
    print("Assigned Doctor ID:", admission["doctor_id"])
    
    
def test_triage_agent_populates_shared_context():
    from app.agents.triage_agent import TriageAgent
    from app.models.agent_context import AgentContext

    class FakeEmergencyTool:
        def run(self, operation, **kwargs):
            assert operation == "get_emergency_incident"
            assert kwargs["incident_id"] == 100

            return {
                "incident_id": 100,
                "patient_id": "test-patient-100",
                "admission_id": 200,
                "department_id": 3,
                "incident_type": "RESPIRATORY",
                "severity": "HIGH",
                "status": "TRIAGED",
            }

    # ---------------------------------------------------------
    # Create shared context
    # ---------------------------------------------------------

    context = AgentContext(
        incident_id=100,
    )

    # ---------------------------------------------------------
    # Create TriageAgent with fake tool
    # ---------------------------------------------------------

    fake_tool = FakeEmergencyTool()

    agent = TriageAgent(
        emergency_tool=fake_tool
    )

    # ---------------------------------------------------------
    # Run agent
    # ---------------------------------------------------------

    result = agent.run(context)

    # ---------------------------------------------------------
    # Print result
    # ---------------------------------------------------------

    print("\n===== TRIAGE CONTEXT HANDOFF TEST =====")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    print("\n--- SHARED CONTEXT ---")
    print("Incident ID:", context.incident_id)
    print("Patient ID:", context.patient_id)
    print("Admission ID:", context.admission_id)
    print("Department ID:", context.department_id)

    print("\n--- CONTEXT DATA ---")
    print(context.data)

    # ---------------------------------------------------------
    # Verify agent result
    # ---------------------------------------------------------

    assert result.status == "SUCCESS"
    assert result.decision == "REQUEST_TRANSPORT"

    # ---------------------------------------------------------
    # Verify shared core identifiers
    # ---------------------------------------------------------

    assert context.incident_id == 100
    assert context.patient_id == "test-patient-100"
    assert context.admission_id == 200
    assert context.department_id == 3

    # ---------------------------------------------------------
    # Verify shared data
    # ---------------------------------------------------------

    assert context.data["patient_id"] == "test-patient-100"
    assert context.data["admission_id"] == 200
    assert context.data["department_id"] == 3

    # ---------------------------------------------------------
    # Verify decision
    # ---------------------------------------------------------

    
    assert result.decision == "REQUEST_TRANSPORT"
    assert len(context.decisions) == 0
    
    

    print("\nTRIAGE CONTEXT HANDOFF TEST PASSED")                                
    
    
def test_real_full_triage_to_staff_workflow():

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

    # =========================================================
    # STEP 1: Fresh clean patient
    # =========================================================

    department_id = 3

# =========================================================
# STEP 1: Select a clean patient with no assigned bed
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
              AND b.status IN ('OCCUPIED', 'RESERVED')
        )
        LIMIT 1
        """
    )

    patient = cursor.fetchone()
    cursor.close()

    assert patient is not None, "No patient without an assigned bed was found."

    patient_id = patient["patient_id"]

    # =========================================================
    # STEP 2: Create fresh admission
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

    print("\n==============================================")
    print(" REAL TRIAGE → EMERGENCY → BED → STAFF WORKFLOW")
    print("==============================================")

    print("Patient ID:", patient_id)
    print("Admission ID:", admission_id)
    print("Department ID:", department_id)

    assert admission_id is not None
    assert admission_id > 0

    # =========================================================
    # STEP 3: Create fresh emergency incident
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

    print("Incident ID:", incident_id)

    assert incident_id is not None
    assert incident_id > 0

    # =========================================================
    # STEP 4: Create real agents
    # =========================================================

    emergency_tool = EmergencyTool()
    bed_tool = BedTool()
    staff_tool = StaffTool()

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
    # STEP 5: Create router
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
    # STEP 6: Create orchestrator
    # =========================================================

    orchestrator = Orchestrator(
        workflow_name="real_triage_to_staff_workflow"
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
    # STEP 7: Shared context
    # =========================================================

    context = AgentContext(
        incident_id=incident_id
    )

    # =========================================================
    # STEP 8: Run complete dynamic workflow
    # =========================================================

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="TriageAgent",
        router=router,
        max_steps=5,
    )

    # =========================================================
    # STEP 9: Print orchestration result
    # =========================================================

    print("\n--- ORCHESTRATOR RESULT ---")

    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", result.actions)
    print("Errors:", result.errors)

    print("\n--- CONTEXT CORE IDENTIFIERS ---")

    print("Incident ID:", context.incident_id)
    print("Patient ID:", context.patient_id)
    print("Admission ID:", context.admission_id)
    print("Department ID:", context.department_id)

    print("\n--- CONTEXT DATA ---")
    print(context.data)

    print("\n--- CONTEXT DECISIONS ---")
    print(context.decisions)

    print("\n--- CONTEXT ACTIONS ---")
    print(context.actions)

    print("\n--- EXECUTION STATE ---")
    print(orchestrator.get_state_dict())

    # =========================================================
    # STEP 10: Verify workflow result
    # =========================================================

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"

    # =========================================================
    # STEP 11: Verify context identifiers
    # =========================================================

    assert context.incident_id == incident_id
    assert context.patient_id == patient_id
    assert context.admission_id == admission_id
    assert context.department_id == department_id

    # =========================================================
    # STEP 12: Verify decisions
    # =========================================================

    decisions = context.decisions

    assert any(
        d["agent"] == "TriageAgent"
        and d["decision"] == "REQUEST_TRANSPORT"
        for d in decisions
    )

    assert any(
        d["agent"] == "EmergencyAgent"
        and d["decision"] == "ASSIGN_BED"
        for d in decisions
    )

    assert any(
        d["agent"] == "BedAgent"
        and d["decision"] == "ASSIGN_DOCTOR"
        for d in decisions
    )

    assert any(
        d["agent"] == "StaffAgent"
        and d["decision"] == "NO_ACTION"
        for d in decisions
    )

    # =========================================================
    # STEP 13: Verify actions
    # =========================================================

    actions = context.actions

    assert any(
        action["agent"] == "EmergencyAgent"
        and action["action"] == "REQUEST_TRANSPORT"
        and action["status"] == "COMPLETED"
        for action in actions
    )

    assert any(
        action["agent"] == "BedAgent"
        and action["action"] == "RESERVE_BED"
        and action["status"] == "COMPLETED"
        for action in actions
    )

    assert any(
        action["agent"] == "StaffAgent"
        and action["action"] == "ASSIGN_DOCTOR"
        and action["status"] == "COMPLETED"
        for action in actions
    )

    # =========================================================
    # STEP 14: Verify execution order
    # =========================================================

    state = orchestrator.get_state_dict()

    assert state["status"] == "COMPLETED"

    assert state["completed_agents"] == [
        "TriageAgent",
        "EmergencyAgent",
        "BedAgent",
        "StaffAgent",
    ]

    assert state["failed_agents"] == []

    # =========================================================
    # STEP 15: Verify database mutation
    # =========================================================

    with get_db_connection() as connection:

        cursor = connection.cursor(
            dictionary=True
        )

        # -----------------------------------------------------
        # Verify admission
        # -----------------------------------------------------

        cursor.execute(
            """
            SELECT
                admission_id,
                patient_id,
                department_id,
                bed_id,
                doctor_id,
                status
            FROM admissions
            WHERE admission_id = %s
            """,
            (
                admission_id,
            ),
        )

        admission = cursor.fetchone()

        # -----------------------------------------------------
        # Verify emergency incident
        # -----------------------------------------------------

        cursor.execute(
            """
            SELECT
                incident_id,
                patient_id,
                admission_id,
                department_id,
                severity,
                status
            FROM emergency_incidents
            WHERE incident_id = %s
            """,
            (
                incident_id,
            ),
        )

        incident = cursor.fetchone()

        cursor.close()

    print("\n--- DATABASE VERIFICATION ---")

    print("Admission:", admission)
    print("Incident:", incident)

    # ---------------------------------------------------------
    # Admission assertions
    # ---------------------------------------------------------

    assert admission is not None

    assert admission["admission_id"] == admission_id
    assert admission["patient_id"] == patient_id
    assert admission["department_id"] == department_id
    assert admission["status"] == "ADMITTED"

    assert admission["bed_id"] is not None
    assert admission["bed_id"] > 0

    assert admission["doctor_id"] is not None
    assert admission["doctor_id"] > 0

    # ---------------------------------------------------------
    # Incident assertions
    # ---------------------------------------------------------

    assert incident is not None

    assert incident["incident_id"] == incident_id
    assert incident["patient_id"] == patient_id
    assert incident["admission_id"] == admission_id
    assert incident["department_id"] == department_id

    # REQUEST_TRANSPORT should have moved the incident
    # away from TRIAGED.
    assert incident["status"] == "AWAITING_TRANSPORT"

    print("\n==============================================")
    print(" FULL TRIAGE → EMERGENCY → BED → STAFF PASSED")
    print("==============================================")
    

    
    
def test_orchestrator_records_triage_decision_once():
    from app.agents.triage_agent import TriageAgent
    from app.models.agent_context import AgentContext
    from app.orchestration.orchestrator import Orchestrator
    from app.orchestration.router import AgentRouter

    class FakeEmergencyTool:
        def run(self, operation, incident_id):
            return {
                "incident_id": incident_id,
                "patient_id": "test-patient",
                "admission_id": 999,
                "department_id": 3,
                "incident_type": "RESPIRATORY",
                "severity": "HIGH",
                "status": "TRIAGED",
            }

    context = AgentContext(
        incident_id=123
    )

    triage_agent = TriageAgent(
        emergency_tool=FakeEmergencyTool()
    )

    orchestrator = Orchestrator(
        workflow_name="test_triage_decision"
    )

    orchestrator.register_agent(triage_agent)

    router = AgentRouter(
        {
            "REQUEST_TRANSPORT": None,
            "NO_ACTION": None,
        }
    )

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="TriageAgent",
        router=router,
    )

    assert result.is_success()
    assert result.decision == "REQUEST_TRANSPORT"

    assert len(context.decisions) == 1

    assert context.decisions[0]["agent"] == "TriageAgent"
    assert context.decisions[0]["decision"] == "REQUEST_TRANSPORT"
    assert context.decisions[0]["reason"] == result.reason
    
    
def test_bed_agent_records_reserved_bed_state():
    from app.agents.bed_agent import BedAgent
    from app.models.agent_context import AgentContext

    class FakeBedTool:
        def run(self, operation, **kwargs):

            if operation == "get_available_beds":
                return [
                    {
                        "bed_id": 177,
                        "bed_number": "MED-3-D",
                        "bed_type": "STANDARD",
                        "bed_status": "AVAILABLE",
                        "room_id": 10,
                        "room_number": "MED-3",
                        "room_type": "GENERAL",
                        "floor_number": 2,
                        "department_id": 3,
                        "department_name": "General Medicine",
                        "department_code": "MED",
                    }
                ]

            if operation == "reserve_bed":
                return {
                    "gateway_request_id": 999,
                    "action_type": "RESERVE_BED",
                    "execution_status": "COMPLETED",
                    "validation_status": "VALIDATED",
                    "result_payload": (
                        '{"action":"RESERVE_BED",'
                        '"status":"RESERVED",'
                        '"bed_id":177,'
                        '"admission_id":500}'
                    ),
                    "error_message": None,
                }

            raise ValueError(
                f"Unsupported operation: {operation}"
            )

    context = AgentContext(
        patient_id="test-patient",
        admission_id=500,
        department_id=3,
    )

    agent = BedAgent(
        bed_tool=FakeBedTool()
    )

    result = agent.run(context)

    assert result.is_success()
    assert result.decision == "ASSIGN_DOCTOR"

    reserved_bed = context.data["reserved_bed"]

    assert reserved_bed["bed_id"] == 177
    assert reserved_bed["bed_status"] == "RESERVED"
    assert reserved_bed["patient_id"] == "test-patient"
    assert reserved_bed["admission_id"] == 500

    assert len(context.actions) == 1

    assert context.actions[0]["action"] == "RESERVE_BED"
    assert context.actions[0]["admission_id"] == 500    