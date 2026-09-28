from datetime import date

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.tools.staff_tool import StaffTool
from app.api.schemas.staff import (
    DoctorAssignmentRequest,
    NurseAssignmentRequest,
)


router = APIRouter(
    prefix="/api/staff",
    tags=["Staff Management"],
)


# =========================================================
# GET AVAILABLE DOCTORS
# =========================================================

@router.get("/doctors/available")
def get_available_doctors(
    schedule_date: date | None = Query(default=None),
    department_id: int | None = Query(default=None),
    speciality: str | None = Query(default=None),
    shift_type: str | None = Query(default=None),
):
    """
    Retrieve active doctors with available schedules.

    Optional filters:
        schedule_date
        department_id
        speciality
        shift_type
    """

    try:
        staff_tool = StaffTool()

        doctors = staff_tool.get_available_doctors(
            schedule_date=schedule_date,
            department_id=department_id,
            speciality=speciality,
            shift_type=shift_type,
        )

        return {
            "status": "SUCCESS",
            "count": len(doctors),
            "doctors": doctors,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to load available doctors: {str(e)}"
            ),
        )


# =========================================================
# GET AVAILABLE NURSES
# =========================================================

@router.get("/nurses/available")
def get_available_nurses(
    schedule_date: date | None = Query(default=None),
    department_id: int | None = Query(default=None),
    shift_type: str | None = Query(default=None),
):
    """
    Retrieve active nurses with available schedules.

    Optional filters:
        schedule_date
        department_id
        shift_type
    """

    try:
        staff_tool = StaffTool()

        nurses = staff_tool.get_available_nurses(
            schedule_date=schedule_date,
            department_id=department_id,
            shift_type=shift_type,
        )

        return {
            "status": "SUCCESS",
            "count": len(nurses),
            "nurses": nurses,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to load available nurses: {str(e)}"
            ),
        )


# =========================================================
# ASSIGN DOCTOR
# =========================================================

@router.post("/doctors/assign")
def assign_doctor(
    request: DoctorAssignmentRequest,
):
    """
    Assign a doctor to an admission.

    The StaffTool first verifies that the admission:

        1. Exists
        2. Is active
        3. Already has a bed assigned

    If no bed is assigned, the API returns HTTP 409
    with status BED_REQUIRED.
    """

    try:
        staff_tool = StaffTool()

        result = staff_tool.assign_doctor(
            admission_id=request.admission_id,
            doctor_id=request.doctor_id,
            requested_by_agent="StaffManagementAPI",
        )

        # -----------------------------------------------------
        # Bed is required before staff assignment
        # -----------------------------------------------------

        if result.get("status") == "BED_REQUIRED":
            return JSONResponse(
                status_code=409,
                content=result,
            )

        # -----------------------------------------------------
        # Admission does not exist
        # -----------------------------------------------------

        if result.get("status") == "ADMISSION_NOT_FOUND":
            return JSONResponse(
                status_code=404,
                content=result,
            )

        # -----------------------------------------------------
        # Admission is not active
        # -----------------------------------------------------

        if result.get("status") == "INVALID_ADMISSION_STATUS":
            return JSONResponse(
                status_code=409,
                content=result,
            )

        # -----------------------------------------------------
        # Normal gateway response
        # -----------------------------------------------------

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to assign doctor: {str(e)}"
            ),
        )


# =========================================================
# GET UNASSIGNED ADMISSIONS
# =========================================================

@router.get("/unassigned-admissions")
def get_unassigned_admissions():
    """
    Retrieve active admissions that require
    doctor assignment.
    """

    try:
        staff_tool = StaffTool()

        admissions = (
            staff_tool.get_unassigned_admissions()
        )

        return {
            "status": "SUCCESS",
            "count": len(admissions),
            "admissions": admissions,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load unassigned admissions: "
                f"{str(e)}"
            ),
        )
# =========================================================
# ASSIGN NURSE
# =========================================================

@router.post("/nurses/assign")
def assign_nurse(
    request: NurseAssignmentRequest,
):
    """
    Assign a nurse to an admission.

    The StaffTool first verifies that the admission:

        1. Exists
        2. Is active
        3. Already has a bed assigned

    If no bed is assigned, the API returns HTTP 409
    with status BED_REQUIRED.
    """

    try:
        staff_tool = StaffTool()

        result = staff_tool.assign_nurse(
            admission_id=request.admission_id,
            nurse_id=request.nurse_id,
            requested_by_agent="StaffManagementAPI",
        )

        # -----------------------------------------------------
        # Bed is required before staff assignment
        # -----------------------------------------------------

        if result.get("status") == "BED_REQUIRED":
            return JSONResponse(
                status_code=409,
                content=result,
            )

        # -----------------------------------------------------
        # Admission does not exist
        # -----------------------------------------------------

        if result.get("status") == "ADMISSION_NOT_FOUND":
            return JSONResponse(
                status_code=404,
                content=result,
            )

        # -----------------------------------------------------
        # Admission is not active
        # -----------------------------------------------------

        if result.get("status") == "INVALID_ADMISSION_STATUS":
            return JSONResponse(
                status_code=409,
                content=result,
            )

        # -----------------------------------------------------
        # Normal gateway response
        # -----------------------------------------------------

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to assign nurse: {str(e)}"
            ),
        )        