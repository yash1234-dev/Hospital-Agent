from fastapi import APIRouter, HTTPException

from app.database.connection import get_db_connection


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("/metrics")
def get_dashboard_metrics():
    """
    Return real-time hospital operational metrics
    for the frontend dashboard.
    """

    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            # ---------------------------------------------------------
            # 1. Available Beds
            # ---------------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM beds
                WHERE status = 'AVAILABLE'
            """)

            available_beds = cursor.fetchone()["count"]

            # ---------------------------------------------------------
            # 2. Available ICU Beds
            # ---------------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM beds
                WHERE status = 'AVAILABLE'
                  AND bed_type = 'ICU'
            """)

            icu_beds = cursor.fetchone()["count"]

            # ---------------------------------------------------------
            # 3. Available Doctors Scheduled Today
            # ---------------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM doctor_schedules
                WHERE schedule_date = CURDATE()
                  AND status = 'AVAILABLE'
            """)

            available_doctors = cursor.fetchone()["count"]

            # ---------------------------------------------------------
            # 4. Available Ambulances
            # ---------------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM ambulances
                WHERE status = 'AVAILABLE'
            """)

            available_ambulances = cursor.fetchone()["count"]

            # ---------------------------------------------------------
            # 5. Critical Emergency Cases
            # ---------------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM emergency_incidents
                WHERE severity = 'CRITICAL'
                  AND status NOT IN ('RESOLVED', 'ADMITTED')
            """)

            critical_cases = cursor.fetchone()["count"]

            # ---------------------------------------------------------
            # 6. High Priority Emergency Cases
            # ---------------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM emergency_incidents
                WHERE severity = 'HIGH'
                  AND status NOT IN ('RESOLVED', 'ADMITTED')
            """)

            high_priority_cases = cursor.fetchone()["count"]

            # ---------------------------------------------------------
            # 7. Active Emergency Cases
            # ---------------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM emergency_incidents
                WHERE status NOT IN ('RESOLVED', 'ADMITTED')
            """)

            active_cases = cursor.fetchone()["count"]

            cursor.close()

            return {
                "status": "SUCCESS",
                "metrics": {
                    "available_beds": available_beds,
                    "icu_beds": icu_beds,
                    "available_doctors": available_doctors,
                    "available_ambulances": available_ambulances,
                    "critical_cases": critical_cases,
                    "high_priority_cases": high_priority_cases,
                    "active_cases": active_cases
                }
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load dashboard metrics: {str(e)}"
        )
@router.get("/emergency-cases")
def get_active_emergency_cases():
    """
    Return currently active emergency cases for the dashboard.
    """

    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    ei.incident_id,
                    ei.patient_id,
                    ei.admission_id,
                    ei.department_id,
                    ei.incident_type,
                    ei.severity,
                    ei.incident_source,
                    ei.symptoms,
                    ei.incident_time,
                    ei.arrival_time,
                    ei.triage_time,
                    ei.status,

                    d.department_name,
                    d.department_code

                FROM emergency_incidents ei

                LEFT JOIN departments d
                    ON ei.department_id = d.department_id

                WHERE ei.status NOT IN (
                    'RESOLVED',
                    'ADMITTED'
                )

                ORDER BY
                    CASE ei.severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                        ELSE 5
                    END,
                    ei.incident_time DESC

                LIMIT 20
            """)

            cases = cursor.fetchall()

            cursor.close()

            return {
                "status": "SUCCESS",
                "cases": cases,
                "count": len(cases),
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load emergency cases: {str(e)}"
        )        