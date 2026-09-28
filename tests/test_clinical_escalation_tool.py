from app.tools.clinical_escalation_tool import ClinicalEscalationTool


def test_clinical_escalation_tool():

    tool = ClinicalEscalationTool()

    patient_id = "99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"
    lab_order_id = 3

    result = tool.escalate_critical_lab(
        patient_id=patient_id,
        lab_order_id=lab_order_id,
        doctor_id=81,
        department_id=3,
        test_name="Blood Glucose",
        result_value="350",
        numeric_value=350,
        unit="mg/dL",
        reference_range="70-140",
        message=(
            "Critical blood glucose result requires "
            "immediate clinical review."
        ),
    )

    print("\nClinical Escalation Tool Result:")
    print(result)

    assert result is not None
    assert result["action_type"] == "CLINICAL_ESCALATION"
    assert result["validation_status"] == "VALIDATED"
    assert result["execution_status"] == "COMPLETED"
    