from app.database.connection import get_db_connection
from app.gateway.action_gateway import ActionGateway


def test_update_lab_order_gateway():
    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                lab_order_id,
                patient_id
            FROM lab_orders
            WHERE order_status = 'COLLECTED'
            ORDER BY lab_order_id
            LIMIT 1
        """)

        lab_order = cursor.fetchone()
        cursor.close()

    assert lab_order is not None, "No COLLECTED lab order available for testing."

    lab_order_id = lab_order["lab_order_id"]
    patient_id = lab_order["patient_id"]

    gateway = ActionGateway()

    gateway_request_id = gateway.create_request(
        action_type="UPDATE_LAB_ORDER",
        requested_by_agent="LabManagementTest",
        request_payload={
            "lab_order_id": lab_order_id,
            "new_status": "PROCESSING",
        },
        patient_id=patient_id,
        admission_id=None,
        incident_id=None,
        target_type="LAB_ORDER",
        target_id=str(lab_order_id),
    )

    result = gateway.execute_action(gateway_request_id)

    print("\nGateway Result:")
    print(result)

    assert result["action_type"] == "UPDATE_LAB_ORDER"
    assert result["target_id"] == str(lab_order_id)
    assert result["validation_status"] == "VALIDATED"
    assert result["execution_status"] == "COMPLETED"

    assert result["result_payload"] is not None