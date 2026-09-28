from datetime import datetime

from app.database.connection import get_db_connection
from app.tools.lab_tool import LabTool


def test_record_lab_result_gateway():

    with get_db_connection() as connection:

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                lab_order_id,
                patient_id,
                test_name
            FROM lab_orders
            ORDER BY lab_order_id
            LIMIT 1
        """)

        order = cursor.fetchone()

        cursor.close()

    assert order is not None

    tool = LabTool()

    result = tool.record_lab_result(
        lab_order_id=order["lab_order_id"],
        patient_id=order["patient_id"],
        test_name=order["test_name"],
        result_value="118",
        numeric_value=118,
        unit="mg/dL",
        reference_range="70-140",
        result_status="NORMAL",
        performed_at=datetime.now(),
        verified_by_doctor_id=81,
        interpretation="Automated gateway test.",
    )

    print(result)

    assert result["action_type"] == "RECORD_LAB_RESULT"
    assert result["validation_status"] == "VALIDATED"
    assert result["execution_status"] == "COMPLETED"