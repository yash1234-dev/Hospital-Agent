import sys
from pathlib import Path


# ---------------------------------------------------------
# Make project root importable
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.agents.emergency_agent import EmergencyAgent
from app.models.agent_context import AgentContext


# =========================================================
# TEST 1 — None context
# =========================================================

def test_none_context():

    agent = EmergencyAgent()

    result = agent.process(None)

    print("\n" + "=" * 70)
    print("TEST 1 — NONE CONTEXT")
    print("=" * 70)

    print("Status :", result.status)
    print("Reason :", result.reason)

    assert result.status == "FAILED"
    assert "AgentContext cannot be None" in result.reason

    print("PASS")


# =========================================================
# TEST 2 — Missing incident ID
# =========================================================

def test_missing_incident_id():

    agent = EmergencyAgent()

    context = AgentContext()

    result = agent.process(context)

    print("\n" + "=" * 70)
    print("TEST 2 — MISSING INCIDENT ID")
    print("=" * 70)

    print("Status :", result.status)
    print("Reason :", result.reason)

    assert result.status == "FAILED"
    assert "Incident ID is required" in result.reason

    print("PASS")


# =========================================================
# TEST 3 — Missing decision
# =========================================================

def test_missing_decision():

    agent = EmergencyAgent()

    context = AgentContext(
        incident_id=6
    )

    result = agent.process(context)

    print("\n" + "=" * 70)
    print("TEST 3 — MISSING DECISION")
    print("=" * 70)

    print("Status :", result.status)
    print("Reason :", result.reason)

    assert result.status == "FAILED"
    assert "requires a decision" in result.reason

    print("PASS")


# =========================================================
# TEST 4 — Unsupported decision
# =========================================================

def test_unsupported_decision():

    agent = EmergencyAgent()

    context = AgentContext(
        incident_id=6
    )

    context.add_decision(
        {
            "decision": "INVALID_ACTION"
        }
    )

    result = agent.process(context)

    print("\n" + "=" * 70)
    print("TEST 4 — UNSUPPORTED DECISION")
    print("=" * 70)

    print("Status :", result.status)
    print("Decision :", result.decision)
    print("Reason :", result.reason)

    assert result.status == "FAILED"
    assert "does not support decision" in result.reason

    print("PASS")


# =========================================================
# TEST 5 — REAL END-TO-END EMERGENCY TEST
# =========================================================

def test_real_emergency_notification():

    agent = EmergencyAgent()

    context = AgentContext(
    patient_id="04bb18cd-a4b9-49bc-bc0f-d3fb3cf2407b",
    incident_id=21,
)

    # -----------------------------------------------------
    # EmergencyAgent decision
    # -----------------------------------------------------

    context.add_decision(
        {
            "decision": "REQUEST_TRANSPORT"
        }
    )

    # -----------------------------------------------------
    # Test email recipient
    # -----------------------------------------------------

    context.add_data(
        "recipient_email",
        "yashkkalyani@gmail.com"
    )

    # -----------------------------------------------------
    # Notification message
    # -----------------------------------------------------

    context.add_data(
        "message",
        (
            "Critical trauma emergency requires transport. "
            "Emergency transport has been requested."
        )
    )

    # -----------------------------------------------------
    # Execute actual agent
    # -----------------------------------------------------

    result = agent.process(context)

    print("\n" + "=" * 70)
    print("TEST 5 — REAL EMERGENCY END-TO-END TEST")
    print("=" * 70)

    print("\nAgent Status:")
    print(result.status)

    print("\nDecision:")
    print(result.decision)

    print("\nReason:")
    print(result.reason)

    print("\nData:")
    print(result.data)

    print("\nActions:")
    print(result.actions)

    print("\nErrors:")
    print(result.errors)

    print("\nContext Actions:")
    print(context.actions)

    print("\n" + "=" * 70)

    # -----------------------------------------------------
    # Assertions
    # -----------------------------------------------------

    assert result.status == "SUCCESS"

    assert result.decision == "ASSIGN_BED"

    assert result.data is not None

    gateway_result = result.data.get(
        "gateway_result"
    )

    notification_result = result.data.get(
        "notification_result"
    )

    assert gateway_result is not None

    assert gateway_result.get(
        "execution_status"
    ) == "COMPLETED"

    assert notification_result is not None

    assert notification_result.get(
        "success"
    ) is True

    assert notification_result.get(
        "status"
    ) == "SENT"

    print("\nREAL END-TO-END TEST: PASS")


# =========================================================
# RUN ALL TESTS
# =========================================================

if __name__ == "__main__":
    test_real_emergency_notification()
    
    print("\n")
    print("=" * 70)
    print("ALL EMERGENCY AGENT TESTS PASSED")
    print("=" * 70)