import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from datetime import datetime

from app.agents.lab_agent import LabAgent
from app.models.agent_context import AgentContext


def main():
    print("\n========== LAB AGENT RESULT TEST ==========\n")

    context = AgentContext(
        patient_id="ab3323a2-3c89-4bb0-af51-50d68dcc89d9",
        department_id=3,
        data={
            "lab_order_id": 20,
            "lab_result": {
                "patient_id": "ab3323a2-3c89-4bb0-af51-50d68dcc89d9",
                "test_name": "Comprehensive Metabolic Panel",
                "result_value": "118",
                "numeric_value": 118.0,
                "unit": "mg/dL",
                "reference_range": "70-140",
                "result_status": "NORMAL",
                "performed_at": datetime.now(),
                "verified_by_doctor_id": 72,
                "interpretation": "Within normal reference range."
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