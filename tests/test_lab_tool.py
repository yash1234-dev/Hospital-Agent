from datetime import datetime

from app.tools.lab_tool import LabTool


def test_get_lab_orders():

    tool = LabTool()

    orders = tool.get_lab_orders(limit=5)

    print("\nLAB ORDERS:")
    print(orders)

    assert isinstance(orders, list)

    if orders:
        assert "lab_order_id" in orders[0]
        assert "patient_id" in orders[0]
        assert "test_name" in orders[0]
        assert "order_status" in orders[0]


def test_get_lab_order():

    tool = LabTool()

    orders = tool.get_lab_orders(limit=1)

    assert orders

    lab_order_id = orders[0]["lab_order_id"]

    order = tool.get_lab_order(lab_order_id)

    print("\nLAB ORDER:")
    print(order)

    assert order is not None
    assert order["lab_order_id"] == lab_order_id


def test_get_lab_results():

    tool = LabTool()

    results = tool.get_lab_results(limit=5)

    print("\nLAB RESULTS:")
    print(results)

    assert isinstance(results, list)

    if results:
        assert "lab_result_id" in results[0]
        assert "lab_order_id" in results[0]
        assert "patient_id" in results[0]
        assert "result_status" in results[0]


def test_get_lab_results_for_order():

    tool = LabTool()

    orders = tool.get_lab_orders(limit=1)

    assert orders

    lab_order_id = orders[0]["lab_order_id"]

    results = tool.get_lab_results(
        lab_order_id=lab_order_id,
        limit=10,
    )

    print(f"\nRESULTS FOR ORDER {lab_order_id}:")
    print(results)

    assert isinstance(results, list)

    for result in results:
        assert result["lab_order_id"] == lab_order_id


def test_update_lab_order_gateway():

    tool = LabTool()

    orders = tool.get_lab_orders(
        order_status="COLLECTED",
        limit=1,
    )

    assert orders, "No COLLECTED lab order available for test."

    lab_order_id = orders[0]["lab_order_id"]

    result = tool.update_lab_order(
        lab_order_id=lab_order_id,
        new_status="PROCESSING",
        requested_by_agent="LabToolTest",
    )

    print("\nUPDATE LAB ORDER RESULT:")
    print(result)

    assert result["action_type"] == "UPDATE_LAB_ORDER"
    assert result["validation_status"] == "VALIDATED"
    assert result["execution_status"] == "COMPLETED"


def test_record_lab_result_gateway():

    tool = LabTool()

    orders = tool.get_lab_orders(limit=1)

    assert orders

    order = orders[0]

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
        interpretation="LabTool integration test.",
        requested_by_agent="LabToolTest",
    )

    print("\nRECORD LAB RESULT:")
    print(result)

    assert result["action_type"] == "RECORD_LAB_RESULT"
    assert result["validation_status"] == "VALIDATED"
    assert result["execution_status"] == "COMPLETED"