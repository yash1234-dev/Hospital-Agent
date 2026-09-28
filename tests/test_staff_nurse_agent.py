import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.staff_agent import StaffAgent
from app.agents.base_agent import AgentContext


def main():

    print("\n========== STAFF AGENT NURSE TEST ==========\n")

    context = AgentContext(
        patient_id="00051dc6-38dc-4781-a6db-b69479990236",
        admission_id=136,
        department_id=3,
        data={
            "recipient_email": "yashkkalyani@gmail.com",
            "message": "Nurse has been successfully assigned to the admission."
        }
    )

    context.add_decision({
        "agent": "BedAgent",
        "decision": "ASSIGN_NURSE",
        "reason": "Bed has been successfully assigned."
    })

    agent = StaffAgent()

    result = agent.process(context)

    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Actions:", context.actions)
    print("Errors:", context.errors)


if __name__ == "__main__":
    main()