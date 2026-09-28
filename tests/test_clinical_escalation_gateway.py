from app.gateway.action_gateway import ActionGateway


def test_clinical_escalation_gateway():

    gateway = ActionGateway()

    patient_id = "99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"
    lab_order_id = 3

    request_payload = {
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
    }

    gateway_request_id = gateway.create_request(
        action_type="CLINICAL_ESCALATION",
        requested_by_agent="ClinicalEscalationAgent",
        request_payload=request_payload,
        patient_id=patient_id,
        admission_id=None,
        incident_id=None,
        target_type="LAB_ORDER",
        target_id=str(lab_order_id),
    )

    print(
        "\nGateway Request ID:",
        gateway_request_id
    )

    result = gateway.execute_action(
        gateway_request_id
    )

    print("\nFinal Gateway Result:")
    print(result)

    assert result is not None
    assert result["action_type"] == "CLINICAL_ESCALATION"
    assert result["validation_status"] == "VALIDATED"
    assert result["execution_status"] == "COMPLETED"