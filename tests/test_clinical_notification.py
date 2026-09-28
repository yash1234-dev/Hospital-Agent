import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



from app.agents.clinical_escalation_agent import ClinicalEscalationAgent
from app.models.agent_context import AgentContext


# ---------------------------------------------------------
# Create Agent Context
# ---------------------------------------------------------

context = AgentContext(
    patient_id="99a7fc1a-ba4f-4637-b83e-6cbffa96d2e6"
)

# ---------------------------------------------------------
# Provide Clinical Escalation Data
# ---------------------------------------------------------

context.add_data(
    "lab_order_id",
    1
)

context.add_data(
    "doctor_id",
    81
)

context.add_data(
    "department_id",
    3
)

context.add_data(
    "test_name",
    "Comprehensive Metabolic Panel"
)

context.add_data(
    "result_value",
    "Critical"
)

context.add_data(
    "numeric_value",
    450.0
)

context.add_data(
    "unit",
    "mg/dL"
)

context.add_data(
    "reference_range",
    "70-110 mg/dL"
)

context.add_data(
    "message",
    "Critical laboratory result detected. Immediate clinical review required."
)

# ---------------------------------------------------------
# Test Email Recipient
# ---------------------------------------------------------

context.add_data(
    "recipient_email",
    "yashkkalyani@gmail.com"
)

# ---------------------------------------------------------
# Run Clinical Escalation Agent
# ---------------------------------------------------------

agent = ClinicalEscalationAgent()

result = agent.process(context)

# ---------------------------------------------------------
# Print Results
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("CLINICAL ESCALATION END-TO-END TEST")
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