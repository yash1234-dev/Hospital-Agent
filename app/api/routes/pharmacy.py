from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.agents.pharmacy_agent import PharmacyAgent
from app.models.agent_context import AgentContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.router import AgentRouter
from app.tools.pharmacy_tool import PharmacyTool


router = APIRouter(
    prefix="/api/pharmacy",
    tags=["Pharmacy Management"],
)


# =========================================================
# GET MEDICATIONS
# =========================================================

@router.get("/medications")
def get_medications(
    medication_name: str | None = None,
    medication_code: str | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Search medication inventory.
    """

    try:
        pharmacy_tool = PharmacyTool()

        medications = pharmacy_tool.search_medications(
            medication_name=medication_name,
            medication_code=medication_code,
            status=status,
            category=category,
            limit=limit,
        )

        return {
            "status": "SUCCESS",
            "count": len(medications),
            "medications": medications,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load medication inventory: {str(exc)}",
        )


# =========================================================
# GET ONE MEDICATION
# =========================================================

@router.get("/medications/{medication_inventory_id}")
def get_medication(
    medication_inventory_id: int,
):
    """
    Retrieve one medication inventory record.
    """

    try:
        pharmacy_tool = PharmacyTool()

        medication = pharmacy_tool.get_medication(
            medication_inventory_id=medication_inventory_id,
        )

        if medication is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Medication inventory record "
                    f"{medication_inventory_id} was not found."
                ),
            )

        return {
            "status": "SUCCESS",
            "medication": medication,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load medication: {str(exc)}",
        )


# =========================================================
# GET MEDICATION REQUESTS
# =========================================================

@router.get("/requests")
def get_medication_requests(
    priority: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Retrieve pending medication requests.

    When no priority is supplied, STAT requests are returned first,
    followed by URGENT and ROUTINE requests according to PharmacyTool.
    """

    try:
        pharmacy_tool = PharmacyTool()

        requests = pharmacy_tool.get_pending_requests(
            priority=priority,
            limit=limit,
        )

        return {
            "status": "SUCCESS",
            "count": len(requests),
            "requests": requests,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load medication requests: {str(exc)}",
        )


# =========================================================
# GET ONE MEDICATION REQUEST
# =========================================================

@router.get("/requests/{request_id}")
def get_medication_request(
    request_id: int,
):
    """
    Retrieve one medication request with its inventory information.
    """

    try:
        pharmacy_tool = PharmacyTool()

        medication_request = pharmacy_tool.get_medication_request(
            request_id=request_id,
        )

        if medication_request is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Medication request {request_id} was not found."
                ),
            )

        return {
            "status": "SUCCESS",
            "request": medication_request,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load medication request: {str(exc)}",
        )


# =========================================================
# RUN PHARMACY AGENT
# =========================================================

@router.post("/requests/{request_id}/process")
def process_medication_request(
    request_id: int,
):
    """
    Run the complete PharmacyAgent workflow for a medication request.

    The API does not modify pharmacy state directly.
    The workflow is:

        API -> Orchestrator -> PharmacyAgent -> PharmacyTool
            -> ActionGateway -> Stored Procedures -> MySQL

    A request with sufficient stock is approved and then dispensed.
    Requests that cannot currently be fulfilled return a successful
    REVIEW_STOCK decision without mutating the request.
    """

    if request_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="request_id must be a positive integer.",
        )

    try:
        pharmacy_tool = PharmacyTool()

        medication_request = pharmacy_tool.get_medication_request(
            request_id=request_id,
        )

        if medication_request is None:
            raise HTTPException(
                status_code=404,
                detail=f"Medication request {request_id} was not found.",
            )

        context = AgentContext(
            patient_id=medication_request.get("patient_id"),
            admission_id=medication_request.get("admission_id"),
            data={
                "request_id": request_id,
            },
        )

        agent = PharmacyAgent(
            pharmacy_tool=pharmacy_tool,
        )

        router_for_workflow = AgentRouter(
            routes={
                "PHARMACY_COMPLETED": None,
                "REVIEW_STOCK": None,
                "NO_ACTION": None,
            }
        )

        orchestrator = Orchestrator(
            workflow_name="pharmacy_request_workflow",
        )

        orchestrator.register_agent(agent)

        result = orchestrator.run_dynamic(
            context=context,
            initial_agent="PharmacyAgent",
            router=router_for_workflow,
            max_steps=1,
        )

        response: dict[str, Any] = {
            "status": result.status,
            "decision": result.decision,
            "reason": result.reason,
            "data": result.data,
            "actions": result.actions,
            "errors": result.errors,
            "context": {
                "patient_id": context.patient_id,
                "admission_id": context.admission_id,
                "data": context.data,
                "actions": context.actions,
                "decisions": context.decisions,
            },
            "execution_state": orchestrator.get_state_dict(),
        }

        if result.status != "SUCCESS":
            raise HTTPException(
                status_code=409,
                detail=response,
            )

        return response

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pharmacy workflow failed: {str(exc)}",
        )
