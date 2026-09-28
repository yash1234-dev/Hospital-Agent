from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.tools.bed_tool import BedTool


router = APIRouter(
    prefix="/api/beds",
    tags=["Bed Management"],
)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class ReserveBedRequest(BaseModel):
    bed_id: int = Field(..., gt=0)
    patient_id: str = Field(..., min_length=1)
    admission_id: int = Field(..., gt=0)


# =========================================================
# GET AVAILABLE BEDS
# =========================================================

@router.get("/available")
def get_available_beds(
    bed_type: str | None = Query(default=None),
    room_type: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
):
    """
    Retrieve currently available hospital beds.

    Optional filters:
        bed_type
        room_type
        department_id
    """

    try:
        bed_tool = BedTool()

        beds = bed_tool.get_available_beds(
            bed_type=bed_type,
            room_type=room_type,
            department_id=department_id,
        )

        return {
            "status": "SUCCESS",
            "count": len(beds),
            "beds": beds,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load available beds: {str(e)}",
        )

# =========================================================
# GET ELIGIBLE ADMISSIONS
# =========================================================

@router.get("/eligible-admissions")
def get_eligible_admissions():
    """
    Retrieve active admissions that are eligible
    for hospital bed assignment.
    """

    try:
        bed_tool = BedTool()

        admissions = bed_tool.get_eligible_admissions()

        return {
            "status": "SUCCESS",
            "count": len(admissions),
            "admissions": admissions,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load eligible admissions: {str(e)}",
        )
# =========================================================
# RESERVE BED
# =========================================================

@router.post("/reserve")
def reserve_bed(request: ReserveBedRequest):
    """
    Reserve a hospital bed for a patient admission.

    The operation is executed through:

        BedTool
            ↓
        ActionGateway
            ↓
        reserve_bed_v2 stored procedure
    """

    try:
        bed_tool = BedTool()

        result = bed_tool.reserve_bed(
            bed_id=request.bed_id,
            patient_id=request.patient_id,
            admission_id=request.admission_id,
            requested_by_agent="BedManagementAPI",
        )

        validation_status = result.get("validation_status")
        execution_status = result.get("execution_status")

        if (
            validation_status == "VALIDATED"
            and execution_status == "COMPLETED"
        ):
            return {
                "status": "SUCCESS",
                "message": "Bed reserved successfully.",
                "gateway_request": result,
            }

        return {
            "status": "FAILED",
            "message": result.get(
                "error_message",
                "Bed reservation failed.",
            ),
            "gateway_request": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reserve bed: {str(e)}",
        )