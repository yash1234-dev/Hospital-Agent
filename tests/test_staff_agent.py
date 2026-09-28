import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.staff_agent import StaffAgent
from app.agents.base_agent import AgentContext

context = AgentContext(
    patient_id="000f8952-7e76-40e6-9edc-2775f70568d8",
    admission_id=169,
    department_id=3,
    data={
        "recipient_email": "yashkkalyani@gmail.com",
        "message": "Doctor has been assigned to the emergency admission."
    }
)

context.add_decision({
    "agent": "BedAgent",
    "decision": "ASSIGN_DOCTOR",
    "reason": "Bed has been successfully assigned."
})

agent = StaffAgent()
result = agent.process(context)

print("\n========== STAFF AGENT TEST ==========")
print("Status:", result.status)
print("Decision:", result.decision)
print("Reason:", result.reason)
print("Data:", result.data)
print("Actions:", result.actions)
print("Errors:", result.errors)