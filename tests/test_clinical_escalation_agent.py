from app.agents.clinical_escalation_agent import ClinicalEscalationAgent
from app.models.agent_context import AgentContext


def test_clinical_escalation_agent():

    patient_id = "99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"

    context = AgentContext(
        patient_id=patient_id,
        admission_id=None,
        incident_id=None,
    )

    context.data.update({
        "lab_order_id": 3,
        "doctor_id": 81,
        "department_id": 3,
        "test_name": "Blood Glucose",
        "result_value": "350",
        "numeric_value": 350,
        "unit": "mg/dL",
        "reference_range": "70-140",
        "message": (
            "Critical blood glucose result requires "
            "immediate clinical review."
        ),
    })

    agent = ClinicalEscalationAgent()

    result = agent.run(context)

    print("\nClinical Escalation Agent Result:")
    print(result)
    print("\nClinical Escalation Agent Result:")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)
    print("Data:", result.data)
    print("Errors:", result.errors)

    assert result.status == "SUCCESS"
    assert result.decision == "ESCALATION_COMPLETED"

    assert "CLINICAL_ESCALATION" in result.actions

    assert result.data["gateway_result"]["execution_status"] == "COMPLETED"