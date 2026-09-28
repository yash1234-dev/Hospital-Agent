from app.agents.lab_agent import LabAgent
from app.agents.clinical_escalation_agent import ClinicalEscalationAgent
from app.models.agent_context import AgentContext
from app.orchestration.router import AgentRouter


def test_lab_to_clinical_escalation_orchestration():

    patient_id = "99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"
    lab_order_id = 3

    # ---------------------------------------------------------
    # Create workflow context
    # ---------------------------------------------------------

    context = AgentContext(
        patient_id=patient_id,
        admission_id=None,
        incident_id=None,
    )

    context.add_data(
        "lab_order_id",
        lab_order_id,
    )

    # ---------------------------------------------------------
    # Create agents
    # ---------------------------------------------------------

    lab_agent = LabAgent()
    clinical_escalation_agent = ClinicalEscalationAgent()

    agents = {
        "LabAgent": lab_agent,
        "ClinicalEscalationAgent": clinical_escalation_agent,
    }

    # ---------------------------------------------------------
    # Create router
    # ---------------------------------------------------------

    router = AgentRouter()

    # ---------------------------------------------------------
    # Step 1: LabAgent
    # ---------------------------------------------------------

    lab_result = lab_agent.run(context)

    print("\n========================================")
    print("LAB AGENT RESULT")
    print("========================================")
    print("Status:", lab_result.status)
    print("Decision:", lab_result.decision)
    print("Reason:", lab_result.reason)
    print("Data:", lab_result.data)
    print("Actions:", lab_result.actions)
    print("Errors:", lab_result.errors)

    assert lab_result.status == "SUCCESS"

    # Lab order 3 should contain a critical result
    assert lab_result.decision == "ESCALATE_CRITICAL_LAB"

    # ---------------------------------------------------------
    # Step 2: Router
    # ---------------------------------------------------------

    next_agent_name = router.get_next_agent(
        lab_result
    )

    print("\n========================================")
    print("ROUTER")
    print("========================================")
    print("Decision:", lab_result.decision)
    print("Next Agent:", next_agent_name)

    assert (
        next_agent_name
        == "ClinicalEscalationAgent"
    )

    # ---------------------------------------------------------
    # Step 3: ClinicalEscalationAgent
    # ---------------------------------------------------------

    next_agent = agents.get(
        next_agent_name
    )

    assert next_agent is not None

    escalation_result = next_agent.run(
        context
    )

    print("\n========================================")
    print("CLINICAL ESCALATION AGENT RESULT")
    print("========================================")
    print("Status:", escalation_result.status)
    print("Decision:", escalation_result.decision)
    print("Reason:", escalation_result.reason)
    print("Data:", escalation_result.data)
    print("Actions:", escalation_result.actions)
    print("Errors:", escalation_result.errors)

    assert escalation_result.status == "SUCCESS"

    assert (
        escalation_result.decision
        == "ESCALATION_COMPLETED"
    )

    assert (
        "CLINICAL_ESCALATION"
        in escalation_result.actions
    )

    gateway_result = (
        escalation_result.data[
            "gateway_result"
        ]
    )

    assert (
        gateway_result["execution_status"]
        == "COMPLETED"
    )

    print("\n========================================")
    print("WORKFLOW COMPLETED")
    print("========================================")