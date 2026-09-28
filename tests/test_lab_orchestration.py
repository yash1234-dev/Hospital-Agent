from app.agents.lab_agent import LabAgent
from app.models.agent_context import AgentContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.router import AgentRouter


# =========================================================
# Fake LabTool
# =========================================================

class FakeLabTool:

    def __init__(self, result_status="NORMAL"):
        self.result_status = result_status

    def get_lab_order(self, lab_order_id):
        return {
            "lab_order_id": lab_order_id,
            "patient_id": "patient-001",
            "doctor_id": 81,
            "department_id": 3,
            "test_name": "Blood Glucose",
            "order_status": "COMPLETED",
        }

    def get_lab_results(self, lab_order_id, limit=1):
        return [
            {
                "lab_result_id": 1,
                "lab_order_id": lab_order_id,
                "patient_id": "patient-001",
                "test_name": "Blood Glucose",
                "result_value": "120",
                "numeric_value": 120,
                "unit": "mg/dL",
                "reference_range": "70-140",
                "result_status": self.result_status,
            }
        ]


# =========================================================
# Router Configuration
# =========================================================

def build_lab_router():

    return AgentRouter(
        routes={
            # Existing hospital workflow
            "REQUEST_TRANSPORT": "EmergencyAgent",
            "ASSIGN_BED": "BedAgent",
            "ASSIGN_DOCTOR": "StaffAgent",
            "ASSIGN_NURSE": "StaffAgent",

            # Lab workflow
            "LAB_ORDER_UPDATED": None,
            "WAIT_FOR_RESULT": None,
            "REVIEW_ABNORMAL_LAB": None,
            "ESCALATE_CRITICAL_LAB": None,
            "NO_ACTION": None,
        }
    )


# =========================================================
# Helper: Run Lab Dynamic Workflow
# =========================================================

def run_lab_workflow(result_status):

    # Create LabAgent
    lab_agent = LabAgent()

    # Replace real LabTool with fake tool
    lab_agent.lab_tool = FakeLabTool(result_status)

    # Create orchestrator with workflow name
    orchestrator = Orchestrator(
        workflow_name="LabWorkflowTest"
    )

    # Register LabAgent
    orchestrator.register_agent(lab_agent)

    # Create shared context
    context = AgentContext(
        patient_id="patient-001",
        data={
            "lab_order_id": 3
        }
    )

    # Create router
    router = build_lab_router()

    # Run dynamic workflow
    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="LabAgent",
        router=router
    )

    return result


# =========================================================
# Test 1: NORMAL
# =========================================================

def test_lab_normal_result():

    result = run_lab_workflow("NORMAL")

    print("\n================ NORMAL RESULT ================")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.is_success()
    assert result.decision == "NO_ACTION"


# =========================================================
# Test 2: ABNORMAL
# =========================================================

def test_lab_abnormal_result():

    result = run_lab_workflow("ABNORMAL")

    print("\n================ ABNORMAL RESULT ================")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.is_success()
    assert result.decision == "REVIEW_ABNORMAL_LAB"


# =========================================================
# Test 3: CRITICAL
# =========================================================

def test_lab_critical_result():

    result = run_lab_workflow("CRITICAL")

    print("\n================ CRITICAL RESULT ================")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.is_success()
    assert result.decision == "ESCALATE_CRITICAL_LAB"