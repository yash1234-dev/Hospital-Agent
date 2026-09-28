from fastapi import APIRouter, HTTPException

from app.models.agent_context import AgentContext
from app.agents.triage_agent import TriageAgent
from app.agents.emergency_agent import EmergencyAgent
from app.agents.bed_agent import BedAgent
from app.agents.staff_agent import StaffAgent

from app.tools.emergency_tool import EmergencyTool
from app.tools.bed_tool import BedTool
from app.tools.staff_tool import StaffTool

from app.orchestration.orchestrator import Orchestrator
from app.orchestration.router import AgentRouter

from app.api.schemas.emergency import EmergencyTriageRequest


router = APIRouter(
    prefix="/api/emergency",
    tags=["Emergency"],
)


def build_emergency_orchestrator() -> Orchestrator:
    """
    Build the emergency workflow using the existing agents.
    """

    emergency_tool = EmergencyTool()
    bed_tool = BedTool()
    staff_tool = StaffTool()

    triage_agent = TriageAgent(
        emergency_tool=emergency_tool
    )

    emergency_agent = EmergencyAgent(
        emergency_tool=emergency_tool
    )

    bed_agent = BedAgent(
        bed_tool=bed_tool
    )

    staff_agent = StaffAgent(
        staff_tool=staff_tool
    )

    router = AgentRouter(
        routes={
            "REQUEST_TRANSPORT": "EmergencyAgent",
            "ASSIGN_BED": "BedAgent",
            "ASSIGN_DOCTOR": "StaffAgent",
            "ASSIGN_NURSE": "StaffAgent",
            "NO_ACTION": None,
        }
    )

    orchestrator = Orchestrator(
        workflow_name="emergency_triage_workflow"
    )

    orchestrator.register_agent(triage_agent)
    orchestrator.register_agent(emergency_agent)
    orchestrator.register_agent(bed_agent)
    orchestrator.register_agent(staff_agent)

    return orchestrator, router


@router.post("/triage")
def run_emergency_triage(request: EmergencyTriageRequest):
    """
    Execute the complete emergency agent workflow.
    """

    try:
        orchestrator, router = build_emergency_orchestrator()

        context = AgentContext(
            incident_id=request.incident_id
        )

        result = orchestrator.run_dynamic(
            context=context,
            initial_agent="TriageAgent",
            router=router,
            max_steps=5,
        )

        return {
            "status": result.status,
            "decision": result.decision,
            "reason": result.reason,
            "data": result.data,
            "actions": result.actions,
            "errors": result.errors,
            "context": {
                "incident_id": context.incident_id,
                "patient_id": context.patient_id,
                "admission_id": context.admission_id,
                "department_id": context.department_id,
                "data": context.data,
                "decisions": context.decisions,
                "actions": context.actions,
                "errors": context.errors,
            },
            "execution_state": orchestrator.get_state_dict(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )