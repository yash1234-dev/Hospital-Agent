import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime

from app.agents.lab_agent import LabAgent
from app.models.agent_context import AgentContext


def main():
    print("\n========== LAB AGENT CRITICAL RESULT TEST ==========\n")

    context = AgentContext(
        patient_id="b45e91bd-cd7c-4041-a5dc-56ba69481668",
        department_id=3,
        data={
            "lab_order_id": 32,
            "lab_result": {
                "patient_id": "b45e91bd-cd7c-4041-a5dc-56ba69481668",
                "test_name": "Comprehensive Metabolic Panel",
                "result_value": "450",
                "numeric_value": 450.0,
                "unit": "mg/dL",
                "reference_range": "70-140",
                "result_status": "CRITICAL",
                "performed_at": datetime.now(),
                "verified_by_doctor_id": 64,
                "interpretation": "Critically elevated result requiring immediate clinical review."
            }
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

    print("\nDecisions:")
    print(context.decisions)

    print("\nErrors:")
    print(context.errors)


if __name__ == "__main__":
    main()