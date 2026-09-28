import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.lab_agent import LabAgent
from app.agents.clinical_escalation_agent import ClinicalEscalationAgent
from app.models.agent_context import AgentContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.router import AgentRouter


def main():
    print("\n========== LAB CRITICAL E2E WORKFLOW TEST ==========\n")

    # ---------------------------------------------------------
    # Shared workflow context
    # ---------------------------------------------------------

    context = AgentContext(
        patient_id="b45e91bd-cd7c-4041-a5dc-56ba69481668",
        department_id=3,
        data={
            "lab_order_id": 32,

            # Used by ClinicalEscalationAgent for notification
            "recipient_email": "yashkkalyani@gmail.com",

            "message": (
                "Critical Comprehensive Metabolic Panel result "
                "requires immediate clinical review."
            ),
        }
    )

    # ---------------------------------------------------------
    # Create orchestrator
    # ---------------------------------------------------------

    orchestrator = Orchestrator(
        workflow_name="Critical Lab Escalation Workflow"
    )

    # ---------------------------------------------------------
    # Register required agents
    # ---------------------------------------------------------

    lab_agent = LabAgent()
    clinical_escalation_agent = ClinicalEscalationAgent()

    orchestrator.register_agent(lab_agent)
    orchestrator.register_agent(clinical_escalation_agent)

    # ---------------------------------------------------------
    # Router
    # ---------------------------------------------------------

    router = AgentRouter()

    # ---------------------------------------------------------
    # Run dynamic workflow
    # ---------------------------------------------------------

    result = orchestrator.run_dynamic(
        context=context,
        initial_agent="LabAgent",
        router=router,
        max_steps=5
    )

    # ---------------------------------------------------------
    # Final result
    # ---------------------------------------------------------

    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    print("\nFinal Data:")
    print(result.data)

    print("\nAgent Actions:")
    for action in context.actions:
        print(action)

    print("\nAgent Decisions:")
    for decision in context.decisions:
        print(decision)

    print("\nErrors:")
    print(context.errors)

    print("\nExecution State:")
    print(orchestrator.get_state_dict())


if __name__ == "__main__":
    main()