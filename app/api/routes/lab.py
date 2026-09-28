from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.lab_agent import LabAgent
from app.models.agent_context import AgentContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.router import AgentRouter


router = APIRouter(
    prefix="/api/labs",
    tags=["Lab Management"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================


class LabRunRequest(BaseModel):
    patient_id: str | None = None
    admission_id: int | None = None
    department_id: int | None = None


class LabStatusUpdateRequest(BaseModel):
    new_status: str = Field(
        ...,
        description="New lab order status.",
    )


class LabResultRequest(BaseModel):
    patient_id: str
    test_name: str
    result_value: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    reference_range: str | None = None
    result_status: str
    performed_at: str
    verified_by_doctor_id: int | None = None
    interpretation: str | None = None

    admission_id: int | None = None
    department_id: int | None = None


# =========================================================
# GET LAB ORDER
# =========================================================


@router.get("/orders/{lab_order_id}")
def get_lab_order(
    lab_order_id: int,
):
    """
    Retrieve a single lab order.
    """

    try:
        from app.tools.lab_tool import LabTool

        lab_tool = LabTool()

        lab_order = lab_tool.get_lab_order(
            lab_order_id
        )

        if lab_order is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Lab order {lab_order_id} "
                    "was not found."
                ),
            )

        return {
            "status": "SUCCESS",
            "lab_order": lab_order,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load lab order: "
                f"{str(e)}"
            ),
        )


# =========================================================
# GET LAB RESULTS
# =========================================================


@router.get("/orders/{lab_order_id}/results")
def get_lab_results(
    lab_order_id: int,
):
    """
    Retrieve results associated with a lab order.
    """

    try:
        from app.tools.lab_tool import LabTool

        lab_tool = LabTool()

        lab_order = lab_tool.get_lab_order(
            lab_order_id
        )

        if lab_order is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Lab order {lab_order_id} "
                    "was not found."
                ),
            )

        results = lab_tool.get_lab_results(
            lab_order_id=lab_order_id,
            limit=50,
        )

        return {
            "status": "SUCCESS",
            "lab_order_id": lab_order_id,
            "count": len(results),
            "results": results,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load lab results: "
                f"{str(e)}"
            ),
        )


# =========================================================
# RUN LAB AGENT
# =========================================================


@router.post("/orders/{lab_order_id}/run")
def run_lab_agent(
    lab_order_id: int,
    request: LabRunRequest | None = None,
):
    """
    Execute the LabAgent workflow for a lab order.

    The agent may:
        - inspect the lab order
        - inspect existing results
        - detect critical results
        - route to ClinicalEscalationAgent
        - complete the clinical escalation workflow
    """

    try:
        request = request or LabRunRequest()

        lab_tool_context = AgentContext(
            patient_id=request.patient_id,
            admission_id=request.admission_id,
            department_id=request.department_id,
            data={
                "lab_order_id": lab_order_id,
            },
        )

        # -------------------------------------------------
        # Register agents
        # -------------------------------------------------

        lab_agent = LabAgent()

        try:
            from app.agents.clinical_escalation_agent import (
                ClinicalEscalationAgent,
            )

            clinical_escalation_agent = (
                ClinicalEscalationAgent()
            )

        except ImportError:
            clinical_escalation_agent = None

        orchestrator = Orchestrator(
            workflow_name="Lab Workflow"
        )

        orchestrator.register_agent(
            lab_agent
        )

        if clinical_escalation_agent is not None:
            orchestrator.register_agent(
                clinical_escalation_agent
            )

        # -------------------------------------------------
        # Routing
        # -------------------------------------------------

        routes: dict[str, str | None] = {
            "WAIT_FOR_RESULT": None,
            "NO_ACTION": None,
            "LAB_ORDER_UPDATED": "LabAgent",
            "REVIEW_ABNORMAL_LAB": None,
            "ESCALATE_CRITICAL_LAB": (
                "ClinicalEscalationAgent"
            ),
            "ESCALATION_COMPLETED": None,
        }

        router = AgentRouter(
            routes=routes
        )

        # -------------------------------------------------
        # Execute dynamic workflow
        # -------------------------------------------------

        result = orchestrator.run_dynamic(
            context=lab_tool_context,
            initial_agent="LabAgent",
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
            "workflow": {
                "name": "Lab Workflow",
                "state": orchestrator.state.status,
                "completed_agents": (
                    orchestrator.state.completed_agents
                ),
                "failed_agents": (
                    orchestrator.state.failed_agents
                ),
            },
            "context": {
                "patient_id": lab_tool_context.patient_id,
                "admission_id": lab_tool_context.admission_id,
                "department_id": lab_tool_context.department_id,
                "decisions": lab_tool_context.decisions,
                "actions": lab_tool_context.actions,
                "errors": lab_tool_context.errors,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Lab workflow execution failed: "
                f"{str(e)}"
            ),
        )


# =========================================================
# UPDATE LAB ORDER STATUS
# =========================================================


@router.post("/orders/{lab_order_id}/status")
def update_lab_order_status(
    lab_order_id: int,
    request: LabStatusUpdateRequest,
):
    """
    Update a lab order through LabAgent and
    ActionGateway.
    """

    try:
        context = AgentContext(
            data={
                "lab_order_id": lab_order_id,
                "requested_status": (
                    request.new_status
                ),
            }
        )

        lab_agent = LabAgent()

        result = lab_agent.run(
            context
        )

        return {
            "status": result.status,
            "decision": result.decision,
            "reason": result.reason,
            "data": result.data,
            "actions": result.actions,
            "errors": result.errors,
            "context": {
                "decisions": context.decisions,
                "actions": context.actions,
                "errors": context.errors,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to update lab order: "
                f"{str(e)}"
            ),
        )


# =========================================================
# RECORD LAB RESULT
# =========================================================


@router.post("/orders/{lab_order_id}/result")
def record_lab_result(
    lab_order_id: int,
    request: LabResultRequest,
):
    """
    Record a new laboratory result through LabAgent.

    If the result is CRITICAL, LabAgent produces:

        ESCALATE_CRITICAL_LAB

    and the dynamic workflow can continue to:

        ClinicalEscalationAgent
    """

    try:
        context = AgentContext(
            patient_id=request.patient_id,
            admission_id=request.admission_id,
            department_id=request.department_id,
            data={
                "lab_order_id": lab_order_id,
                "lab_result": {
                    "patient_id": request.patient_id,
                    "test_name": request.test_name,
                    "result_value": request.result_value,
                    "numeric_value": request.numeric_value,
                    "unit": request.unit,
                    "reference_range": (
                        request.reference_range
                    ),
                    "result_status": (
                        request.result_status
                    ),
                    "performed_at": (
                        request.performed_at
                    ),
                    "verified_by_doctor_id": (
                        request.verified_by_doctor_id
                    ),
                    "interpretation": (
                        request.interpretation
                    ),
                },
            },
        )

        lab_agent = LabAgent()

        result = lab_agent.run(
            context
        )

        return {
            "status": result.status,
            "decision": result.decision,
            "reason": result.reason,
            "data": result.data,
            "actions": result.actions,
            "errors": result.errors,
            "context": {
                "patient_id": context.patient_id,
                "admission_id": context.admission_id,
                "department_id": context.department_id,
                "decisions": context.decisions,
                "actions": context.actions,
                "errors": context.errors,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to record lab result: "
                f"{str(e)}"
            ),
        )