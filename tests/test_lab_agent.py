from datetime import datetime

from app.agents.lab_agent import LabAgent
from app.models.agent_context import AgentContext


class FakeLabTool:

    def __init__(
        self,
        result_status="NORMAL",
        update_status="COMPLETED",
        record_status="COMPLETED",
    ):
        self.result_status = result_status
        self.update_status = update_status
        self.record_status = record_status

    def get_lab_order(self, lab_order_id):

        return {
            "lab_order_id": lab_order_id,
            "patient_id": "test-patient",
            "doctor_id": 81,
            "department_id": 3,
            "test_name": "Blood Glucose",
            "priority": "ROUTINE",
            "order_status": "PROCESSING",
        }

    def get_lab_results(
        self,
        lab_order_id=None,
        patient_id=None,
        result_status=None,
        limit=50,
    ):

        return [
            {
                "lab_result_id": 1,
                "lab_order_id": lab_order_id,
                "patient_id": "test-patient",
                "test_name": "Blood Glucose",
                "result_value": "120",
                "numeric_value": 120,
                "unit": "mg/dL",
                "reference_range": "70-140",
                "result_status": self.result_status,
                "performed_at": datetime.now(),
            }
        ]

    def update_lab_order(
        self,
        lab_order_id,
        new_status,
        requested_by_agent,
    ):

        return {
            "gateway_request_id": 100,
            "action_type": "UPDATE_LAB_ORDER",
            "validation_status": "VALIDATED",
            "execution_status": self.update_status,
            "error_message": None,
        }

    def record_lab_result(
        self,
        **kwargs,
    ):

        return {
            "gateway_request_id": 101,
            "action_type": "RECORD_LAB_RESULT",
            "validation_status": "VALIDATED",
            "execution_status": self.record_status,
            "error_message": None,
        }


def test_lab_agent_normal_result():

    agent = LabAgent(
        lab_tool=FakeLabTool(
            result_status="NORMAL"
        )
    )

    context = AgentContext()

    context.add_data(
        "lab_order_id",
        3
    )

    result = agent.run(context)

    print("\nNORMAL RESULT")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Reason:", result.reason)

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"


def test_lab_agent_abnormal_result():

    agent = LabAgent(
        lab_tool=FakeLabTool(
            result_status="ABNORMAL"
        )
    )

    context = AgentContext()

    context.add_data(
        "lab_order_id",
        3
    )

    result = agent.run(context)

    print("\nABNORMAL RESULT")
    print("Status:", result.status)
    print("Decision:", result.decision)

    assert result.status == "SUCCESS"
    assert result.decision == "REVIEW_ABNORMAL_LAB"


def test_lab_agent_critical_result():

    agent = LabAgent(
        lab_tool=FakeLabTool(
            result_status="CRITICAL"
        )
    )

    context = AgentContext()

    context.add_data(
        "lab_order_id",
        3
    )

    result = agent.run(context)

    print("\nCRITICAL RESULT")
    print("Status:", result.status)
    print("Decision:", result.decision)

    assert result.status == "SUCCESS"
    assert result.decision == "ESCALATE_CRITICAL_LAB"


def test_lab_agent_update_order():

    agent = LabAgent(
        lab_tool=FakeLabTool()
    )

    context = AgentContext()

    context.add_data(
        "lab_order_id",
        3
    )

    context.add_data(
        "requested_status",
        "COMPLETED"
    )

    result = agent.run(context)

    print("\nUPDATE ORDER")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Actions:", result.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "LAB_ORDER_UPDATED"
    assert len(result.actions) == 1


def test_lab_agent_record_normal_result():

    agent = LabAgent(
        lab_tool=FakeLabTool()
    )

    context = AgentContext()

    context.add_data(
        "lab_order_id",
        3
    )

    context.add_data(
        "lab_result",
        {
            "patient_id": "test-patient",
            "test_name": "Blood Glucose",
            "result_value": "120",
            "numeric_value": 120,
            "unit": "mg/dL",
            "reference_range": "70-140",
            "result_status": "NORMAL",
            "performed_at": datetime.now(),
            "verified_by_doctor_id": 81,
            "interpretation": "Within reference range.",
        }
    )

    result = agent.run(context)

    print("\nRECORD NORMAL RESULT")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Actions:", result.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "NO_ACTION"
    assert len(result.actions) == 1


def test_lab_agent_record_critical_result():

    agent = LabAgent(
        lab_tool=FakeLabTool()
    )

    context = AgentContext()

    context.add_data(
        "lab_order_id",
        3
    )

    context.add_data(
        "lab_result",
        {
            "patient_id": "test-patient",
            "test_name": "Blood Glucose",
            "result_value": "500",
            "numeric_value": 500,
            "unit": "mg/dL",
            "reference_range": "70-140",
            "result_status": "CRITICAL",
            "performed_at": datetime.now(),
            "verified_by_doctor_id": 81,
            "interpretation": "Critical value detected.",
        }
    )

    result = agent.run(context)

    print("\nRECORD CRITICAL RESULT")
    print("Status:", result.status)
    print("Decision:", result.decision)
    print("Actions:", result.actions)

    assert result.status == "SUCCESS"
    assert result.decision == "ESCALATE_CRITICAL_LAB"
    assert len(result.actions) == 1