import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.staff_agent import StaffAgent
from app.models.agent_context import AgentContext


def main():
    patient_id = "00034773-ca66-4191-8f43-56a9c20f8abf"
    admission_id = 132
    department_id = 2
    recipient_email = "yashkkalyani@gmail.com"

    context = AgentContext(
        patient_id=patient_id,
        admission_id=admission_id,
        department_id=department_id,
    )

    # StaffAgent requires its routing decision
    context.add_decision(
        {
            "decision": "ASSIGN_DOCTOR",
            "reason": "Assign an available doctor to the admission.",
        }
    )

    # Test recipient for n8n email notification
    context.add_data(
        "recipient_email",
        recipient_email,
    )

    context.add_data(
        "message",
        (
            f"Doctor assignment completed for patient {patient_id}. "
            f"Admission ID: {admission_id}."
        ),
    )

    print("=" * 60)
    print("STAFF AGENT DOCTOR ASSIGNMENT E2E TEST")
    print("=" * 60)

    print("\nInput Context:")
    print(f"Patient ID     : {patient_id}")
    print(f"Admission ID   : {admission_id}")
    print(f"Department ID  : {department_id}")
    print(f"Decision       : ASSIGN_DOCTOR")
    print(f"Recipient Email: {recipient_email}")

    print("\nRunning StaffAgent...\n")

    agent = StaffAgent()
    result = agent.process(context)

    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print(f"Status  : {result.status}")
    print(f"Decision: {result.decision}")
    print(f"Reason  : {result.reason}")

    print("\nData:")
    print(result.data)

    print("\nActions:")
    print(result.actions)

    notification = result.data.get("notification_result")

    print("\n" + "=" * 60)
    print("NOTIFICATION RESULT")
    print("=" * 60)
    print(notification)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()