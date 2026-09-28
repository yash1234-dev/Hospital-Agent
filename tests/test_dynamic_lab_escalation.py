from app.agents.lab_agent import LabAgent
from app.agents.clinical_escalation_agent import ClinicalEscalationAgent
from app.models.agent_context import AgentContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.router import AgentRouter


def test_dynamic_lab_clinical_escalation():

    patient_id = "99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"
    lab_order_id = 3

    # =========================================================
    # CONTEXT
    # =========================================================

    context = AgentContext(
        patient_id=patient_id,
        admission_id=None,
        incident_id=None,
    )

    context.add_data(
        "lab_order_id",
        lab_order_id,
    )

    # =========================================================
    # AGENTS
    # =========================================================

    lab_agent = LabAgent()

    clinical_escalation_agent = (
        ClinicalEscalationAgent()
    )

    # =========================================================
    # ORCHESTRATOR
    # =========================================================

    orchestrator = Orchestrator(
        workflow_name="Critical Lab Escalation"
    )

    orchestrator.register_agent(
        lab_agent
    )

    orchestrator.register_agent(
        clinical_escalation_agent
    )

    print("\nRegistered Agents:")
    print(
        orchestrator.list_agents()
    )

    # =========================================================
    # ROUTER
    # =========================================================

    router = AgentRouter()

    print("\nRouter Routes:")
    print(
        router.get_routes()
    )

    # =========================================================
    # DYNAMIC WORKFLOW
    # =========================================================

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="LabAgent",
        router=router,
        max_steps=5,
    )

    # =========================================================
    # OUTPUT
    # =========================================================

    print("\n========================================")
    print("DYNAMIC WORKFLOW RESULT")
    print("========================================")

    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", result.actions)
    print("Errors:", result.errors)

    print("\n========================================")
    print("EXECUTION STATE")
    print("========================================")

    print(
        orchestrator.get_state_dict()
    )

    # =========================================================
    # ASSERTIONS
    # =========================================================

    assert result.status == "SUCCESS"

    assert (
        result.decision
        == "ESCALATION_COMPLETED"
    )

    assert (
        "CLINICAL_ESCALATION"
        in result.actions
    )

    gateway_result = (
        result.data[
            "gateway_result"
        ]
    )

    assert (
        gateway_result[
            "execution_status"
        ]
        == "COMPLETED"
    )