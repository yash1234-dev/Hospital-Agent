import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from app.agents.pharmacy_agent import PharmacyAgent
from app.models.agent_context import AgentContext


def main():
    print("=" * 70)
    print("PHARMACY AGENT - END-TO-END TEST")
    print("=" * 70)

    request_id = 55

    context = AgentContext(
        patient_id="8c571e80-3471-4d42-9396-77b29cd3762a",
        data={
    "request_id": request_id,
    "recipient_email": "yashkkalyani@gmail.com",
    "message": "Medication request has been approved and dispensed."
}
    )

    agent = PharmacyAgent()

    print("\n[1] Running PharmacyAgent...")
    result = agent.run(context)

    print("\n[2] RESULT")
    print("-" * 70)
    print("Status  :", result.status)
    print("Decision:", result.decision)
    print("Reason  :", result.reason)

    print("\n[3] DATA")
    print("-" * 70)
    print(result.data)

    print("\n[4] ACTIONS")
    print("-" * 70)

    for action in result.actions:
        print(action)

    print("\n[5] ERRORS")
    print("-" * 70)

    for error in result.errors:
        print(error)

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()