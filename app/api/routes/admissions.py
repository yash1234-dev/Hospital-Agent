from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.admission_agent import AdmissionAgent
from app.models.agent_context import AgentContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.router import AgentRouter
from app.tools.admission_tool import AdmissionTool, AdmissionToolError
from app.database.connection import get_db_connection


router = APIRouter(
    prefix="/api/admissions",
    tags=["Admission Management"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================


class AdmissionCreateRequest(BaseModel):
    patient_id: str
    department_id: int = Field(gt=0)
    admission_type: str
    encounter_id: str | None = None
    expected_discharge_time: Any = None
    diagnosis: str | None = None
    notes: str | None = None


class AdmissionProcessRequest(BaseModel):
    patient_id: str
    department_id: int = Field(gt=0)
    admission_type: str
    encounter_id: str | None = None
    expected_discharge_time: Any = None
    diagnosis: str | None = None
    notes: str | None = None
    admission_id: int | None = Field(
        default=None,
        gt=0,
    )


class AdmissionStatusRequest(BaseModel):
    new_status: str


class AdmissionNotesRequest(BaseModel):
    notes: str | None = None


# =========================================================
# GET ALL ADMISSIONS
# =========================================================


@router.get("")
def get_admissions(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    status: str | None = Query(
        default=None,
    ),
    patient_id: str | None = Query(
        default=None,
    ),
):
    """
    Retrieve hospital admissions with optional filters.
    """

    try:
        tool = AdmissionTool()

        admissions = tool.list_admissions(
            limit=limit,
            offset=offset,
            status=status,
            patient_id=patient_id,
        )

        return {
            "status": "SUCCESS",
            "count": len(admissions),
            "admissions": admissions,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load admissions: {str(exc)}",
        )


# =========================================================
# GET UNADMITTED PATIENTS
# IMPORTANT:
# This route MUST appear before /{admission_id}
# =========================================================


@router.get("/unadmitted-patients")
def get_unadmitted_patients():
    """
    Retrieve living patients who currently do not have
    an active admission.

    Active admission statuses:
        ADMITTED
        OBSERVATION
    """

    try:
        with get_db_connection() as connection:

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    p.ID AS patient_id
                FROM patients p
                WHERE p.DEATHDATE IS NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM admissions a
                      WHERE a.patient_id = p.ID
                        AND a.status IN (
                            'ADMITTED',
                            'OBSERVATION'
                        )
                  )
                ORDER BY p.ID
                LIMIT 100
                """
            )

            patients = cursor.fetchall()

            cursor.close()

        return {
            "status": "SUCCESS",
            "count": len(patients),
            "patients": patients,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load unadmitted patients: "
                f"{str(exc)}"
            ),
        )


# =========================================================
# GET PATIENT CLINICAL SUMMARY
# IMPORTANT:
# This is READ-ONLY.
#
# It does NOT create an admission.
# It does NOT modify database state.
# =========================================================


@router.get("/patient/{patient_id}/clinical-summary")
def get_patient_clinical_summary(
    patient_id: str,
):
    """
    Retrieve existing clinical information for a patient.

    Data sources:
        patients
        encounters
        conditions
        observations

    This information will later be used by the
    Admission Intelligence layer to suggest:
        - department
        - admission reason / diagnosis
        - relevant clinical context
    """

    if not patient_id or not patient_id.strip():
        raise HTTPException(
            status_code=400,
            detail="patient_id is required.",
        )

    patient_id = patient_id.strip()

    try:
        with get_db_connection() as connection:

            cursor = connection.cursor(
                dictionary=True
            )

            # -------------------------------------------------
            # PATIENT
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    ID AS patient_id,
                    BIRTHDATE AS birth_date,
                    GENDER AS gender,
                    RACE AS race,
                    ETHNICITY AS ethnicity
                FROM patients
                WHERE ID = %s
                LIMIT 1
                """,
                (patient_id,),
            )

            patient = cursor.fetchone()

            if patient is None:
                cursor.close()

                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Patient {patient_id} "
                        "not found."
                    ),
                )

            # -------------------------------------------------
            # RECENT ENCOUNTERS
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    ID AS encounter_id,
                    START AS start_time,
                    STOP AS stop_time,
                    ENCOUNTERCLASS AS encounter_class,
                    CODE AS encounter_code,
                    DESCRIPTION AS description,
                    REASONCODE AS reason_code,
                    REASONDESCRIPTION AS reason_description
                FROM encounters
                WHERE PATIENT = %s
                ORDER BY START DESC
                LIMIT 10
                """,
                (patient_id,),
            )

            encounters = cursor.fetchall()

            # -------------------------------------------------
            # CONDITIONS
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    START AS start_date,
                    STOP AS stop_date,
                    ENCOUNTER AS encounter_id,
                    CODE AS condition_code,
                    DESCRIPTION AS description
                FROM conditions
                WHERE PATIENT = %s
                ORDER BY START DESC
                LIMIT 10
                """,
                (patient_id,),
            )

            conditions = cursor.fetchall()

            # -------------------------------------------------
            # OBSERVATIONS
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    DATE AS observation_date,
                    ENCOUNTER AS encounter_id,
                    CODE AS observation_code,
                    DESCRIPTION AS description,
                    VALUE AS value,
                    UNITS AS units,
                    TYPE AS observation_type
                FROM observations
                WHERE PATIENT = %s
                ORDER BY DATE DESC
                LIMIT 15
                """,
                (patient_id,),
            )

            observations = cursor.fetchall()

            cursor.close()

        return {
            "status": "SUCCESS",
            "patient": patient,
            "clinical_summary": {
                "recent_encounters": encounters,
                "conditions": conditions,
                "recent_observations": observations,
            },
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load patient "
                f"clinical summary: {str(exc)}"
            ),
        )


# =========================================================
# GET ACTIVE ADMISSION FOR PATIENT
# IMPORTANT:
# This route MUST appear before /{admission_id}
# =========================================================


@router.get("/patient/{patient_id}/active")
def get_active_patient_admission(
    patient_id: str,
):
    """
    Retrieve the latest active admission for a patient.
    """

    if not patient_id or not patient_id.strip():
        raise HTTPException(
            status_code=400,
            detail="patient_id is required.",
        )

    try:
        tool = AdmissionTool()

        admission = tool.get_active_admission(
            patient_id=patient_id,
        )

        return {
            "status": "SUCCESS",
            "found": admission is not None,
            "admission": admission,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load active admission: "
                f"{str(exc)}"
            ),
        )


# =========================================================
# CREATE ADMISSION
# =========================================================


@router.post("")
def create_admission(
    request: AdmissionCreateRequest,
):
    """
    Create a new patient admission.

    State-changing operation flow:

        API
          ↓
        AdmissionTool
          ↓
        ActionGateway
          ↓
        create_admission_v1
          ↓
        MySQL
    """

    try:
        tool = AdmissionTool()

        result = tool.create_admission(
            patient_id=request.patient_id,
            department_id=request.department_id,
            admission_type=request.admission_type.upper(),
            encounter_id=request.encounter_id,
            expected_discharge_time=(
                request.expected_discharge_time
            ),
            diagnosis=request.diagnosis,
            notes=request.notes,
            requested_by_agent="AdmissionAPI",
        )

        if result.get("execution_status") != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=(
                    result.get("error_message")
                    or "Admission creation failed."
                ),
            )

        return {
            "status": "SUCCESS",
            "message": (
                "Admission created successfully."
            ),
            "admission": result,
        }

    except HTTPException:
        raise

    except (
        ValueError,
        AdmissionToolError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to create admission: "
                f"{str(exc)}"
            ),
        )


# =========================================================
# PROCESS ADMISSION THROUGH AGENT
# =========================================================


@router.post("/process")
def process_admission(
    request: AdmissionProcessRequest,
):
    """
    Process an admission request through the
    agentic admission workflow.

    Workflow:

        API
          ↓
        AdmissionAgent
          ↓
        BedAgent
          ↓
        StaffAgent
          ↓
        ActionGateway
          ↓
        MySQL
    """

    try:
        context = AgentContext(
            patient_id=request.patient_id,
            admission_id=request.admission_id,
            department_id=request.department_id,
            data={
                "admission_type": (
                    request.admission_type.upper()
                ),
                "encounter_id": request.encounter_id,
                "expected_discharge_time": (
                    request.expected_discharge_time
                ),
                "diagnosis": request.diagnosis,
                "notes": request.notes,
            },
        )

        admission_agent = AdmissionAgent()

        # -------------------------------------------------
        # ROUTER
        # -------------------------------------------------

        router = AgentRouter(
            routes={
                "ASSIGN_BED": "BedAgent",
                "ASSIGN_DOCTOR": "StaffAgent",
                "ASSIGN_NURSE": "StaffAgent",
                "NO_ACTION": None,
            }
        )

        # -------------------------------------------------
        # ORCHESTRATOR
        # -------------------------------------------------

        orchestrator = Orchestrator(
            workflow_name=(
                "admission_request_workflow"
            )
        )

        orchestrator.register_agent(
            admission_agent
        )

        # -------------------------------------------------
        # BED AGENT
        # -------------------------------------------------

        from app.agents.bed_agent import BedAgent

        orchestrator.register_agent(
            BedAgent()
        )

        # -------------------------------------------------
        # STAFF AGENT
        # -------------------------------------------------

        from app.agents.staff_agent import StaffAgent

        orchestrator.register_agent(
            StaffAgent()
        )

        # -------------------------------------------------
        # RUN DYNAMIC WORKFLOW
        # -------------------------------------------------

        result = orchestrator.run_dynamic(
            context=context,
            initial_agent="AdmissionAgent",
            router=router,
            max_steps=5,
        )

        state = orchestrator.get_state_dict()

        return {
            "status": result.status,
            "decision": result.decision,
            "reason": result.reason,
            "data": result.data,
            "actions": result.actions,
            "errors": result.errors,
            "context": {
                "patient_id": (
                    context.patient_id
                ),
                "admission_id": (
                    context.admission_id
                ),
                "department_id": (
                    context.department_id
                ),
                "data": context.data,
                "actions": context.actions,
                "decisions": context.decisions,
            },
            "execution_state": state,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Admission agent processing failed: "
                f"{str(exc)}"
            ),
        )


# =========================================================
# GET ACTIVE HOSPITAL DEPARTMENTS
# =========================================================


@router.get("/departments")
def get_departments():
    """
    Retrieve active hospital departments for the admission UI.
    Read-only operation.
    """

    query = """
        SELECT
            department_id,
            department_name,
            department_code
        FROM departments
        WHERE status = 'ACTIVE'
        ORDER BY department_name
    """

    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query)
            departments = cursor.fetchall()

            cursor.close()

        return {
            "status": "SUCCESS",
            "count": len(departments),
            "departments": departments,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load departments: {str(exc)}",
        )



# =========================================================
# GET SINGLE ADMISSION
# IMPORTANT:
# Keep this AFTER all static/dynamic named routes above.
# =========================================================


@router.get("/{admission_id}")
def get_admission(
    admission_id: int,
):
    """
    Retrieve one admission by admission ID.
    """

    if admission_id <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "admission_id must be "
                "a positive integer."
            ),
        )

    try:
        tool = AdmissionTool()

        admission = tool.get_admission(
            admission_id=admission_id,
        )

        if admission is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Admission {admission_id} "
                    "not found."
                ),
            )

        return {
            "status": "SUCCESS",
            "admission": admission,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load admission: "
                f"{str(exc)}"
            ),
        )


# =========================================================
# UPDATE ADMISSION STATUS
# =========================================================


@router.put("/{admission_id}/status")
def update_admission_status(
    admission_id: int,
    request: AdmissionStatusRequest,
):
    """
    Update an admission status through ActionGateway.
    """

    if admission_id <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "admission_id must be "
                "a positive integer."
            ),
        )

    try:
        tool = AdmissionTool()

        result = tool.update_admission_status(
            admission_id=admission_id,
            new_status=request.new_status.upper(),
            requested_by_agent="AdmissionAPI",
        )

        if result.get("execution_status") != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=(
                    result.get("error_message")
                    or "Admission status "
                    "update failed."
                ),
            )

        return {
            "status": "SUCCESS",
            "message": (
                "Admission status updated "
                "successfully."
            ),
            "admission": result,
        }

    except HTTPException:
        raise

    except (
        ValueError,
        AdmissionToolError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to update admission "
                f"status: {str(exc)}"
            ),
        )


# =========================================================
# DISCHARGE ADMISSION
# =========================================================


@router.post("/{admission_id}/discharge")
def discharge_admission(
    admission_id: int,
    request: AdmissionNotesRequest,
):
    """
    Discharge a patient from an active admission.
    """

    if admission_id <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "admission_id must be "
                "a positive integer."
            ),
        )

    try:
        tool = AdmissionTool()

        result = tool.discharge_admission(
            admission_id=admission_id,
            notes=request.notes,
            requested_by_agent="AdmissionAPI",
        )

        if result.get("execution_status") != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=(
                    result.get("error_message")
                    or "Admission discharge failed."
                ),
            )

        return {
            "status": "SUCCESS",
            "message": (
                "Admission discharged "
                "successfully."
            ),
            "admission": result,
        }

    except HTTPException:
        raise

    except (
        ValueError,
        AdmissionToolError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to discharge admission: "
                f"{str(exc)}"
            ),
        )


# =========================================================
# CANCEL ADMISSION
# =========================================================


@router.post("/{admission_id}/cancel")
def cancel_admission(
    admission_id: int,
    request: AdmissionNotesRequest,
):
    """
    Cancel an active admission.
    """

    if admission_id <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "admission_id must be "
                "a positive integer."
            ),
        )

    try:
        tool = AdmissionTool()

        result = tool.cancel_admission(
            admission_id=admission_id,
            notes=request.notes,
            requested_by_agent="AdmissionAPI",
        )

        if result.get("execution_status") != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=(
                    result.get("error_message")
                    or "Admission cancellation failed."
                ),
            )

        return {
            "status": "SUCCESS",
            "message": (
                "Admission cancelled "
                "successfully."
            ),
            "admission": result,
        }

    except HTTPException:
        raise

    except (
        ValueError,
        AdmissionToolError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to cancel admission: "
                f"{str(exc)}"
            ),
        )