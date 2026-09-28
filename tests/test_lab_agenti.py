import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.lab_agent import LabAgent
from app.agents.base_agent import AgentContext


def main():
    print("\n========== LAB AGENT TEST ==========\n")

    context = AgentContext(
        patient_id="ab3323a2-3c89-4bb0-af51-50d68dcc89d9",
        department_id=3,
        data={
            "lab_order_id": 20
        }
    )

    agent = LabAgent()

    result = agent.process(context)

    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("\nData:")
    print(result.data)

    print("\nActions:")
    print(context.actions)

    print("\nErrors:")
    print(context.errors)


if __name__ == "__main__":
    main()