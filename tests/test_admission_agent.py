import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.admission_agent import AdmissionAgent
from app.models.agent_context import AgentContext


def main():
    print("=" * 70)
    print("ADMISSION AGENT - END-TO-END TEST")
    print("=" * 70)

    patient_id = "0001ae39-67c6-443c-81e4-e835ab4f6a9b"
    department_id = 3

    context = AgentContext(
        patient_id=patient_id,
        department_id=department_id,
        data={
            "admission_type": "EMERGENCY",
            "diagnosis": "Emergency admission test",
            "notes": "AdmissionAgent end-to-end test"
        }
    )

    agent = AdmissionAgent()

    print("\n[1] Running AdmissionAgent...")
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

    print("\n[6] CONTEXT")
    print("-" * 70)
    print("Admission ID:", context.admission_id)
    print("Patient ID  :", context.patient_id)
    print("Department  :", context.department_id)

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()