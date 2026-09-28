import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.bed_agent import BedAgent
from app.agents.base_agent import AgentContext


def main():
    patient_id = "04741a86-157c-496b-ab59-cfd4e8e4eaf1"
    admission_id = 196
    department_id = 1
    recipient_email = "yashkkalyani@gmail.com"

    context = AgentContext(
        patient_id=patient_id,
        admission_id=admission_id,
        department_id=department_id,
    )

    context.add_data("recipient_email", recipient_email)
    context.add_data(
        "message",
        f"Bed assignment completed for patient {patient_id}. "
        f"Admission ID: {admission_id}."
    )

    print("=" * 60)
    print("BED AGENT NOTIFICATION E2E TEST")
    print("=" * 60)

    print("\nInput Context:")
    print(f"Patient ID     : {patient_id}")
    print(f"Admission ID   : {admission_id}")
    print(f"Department ID  : {department_id}")
    print(f"Recipient Email: {recipient_email}")

    print("\nRunning BedAgent...\n")

    agent = BedAgent()
    result = agent.process(context)

    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print(f"Status  : {result.status}")
    print(f"Decision: {result.decision}")
    print(f"Reason  : {result.reason}")
    print(f"\nData   : {result.data}")
    print(f"\nActions: {result.actions}")

    if result.data:
        notification = result.data.get("notification_result")

        print("\n" + "=" * 60)
        print("NOTIFICATION RESULT")
        print("=" * 60)
        print(notification)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()