from datetime import date
from typing import Any

from app.database.connection import get_db_connection


def get_available_doctors(
    schedule_date: date | None = None,
    department_id: int | None = None,
    speciality: str | None = None,
    shift_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve active doctors who have an available schedule.

    The schedule date is optional. When omitted, availability is not
    restricted to today; any schedule row with status AVAILABLE may be
    returned. If a schedule_date is supplied, results are restricted to
    that date.

    Optional filters:
        schedule_date:
            Optional date on which the doctor should be available.

        department_id:
            Restrict results to a specific department.

        speciality:
            Restrict results to a doctor's speciality.

        shift_type:
            MORNING, AFTERNOON, EVENING, or NIGHT.

    Returns:
        A list of doctors with their department and schedule details.
    """

    query = """
        SELECT
            d.doctor_id,
            d.doctor_name,
            d.speciality,
            d.gender,
            d.employment_status,

            dept.department_id,
            dept.department_name,
            dept.department_code,

            ds.schedule_id,
            ds.schedule_date,
            ds.shift_type,
            ds.start_time,
            ds.end_time,
            ds.status AS schedule_status,
            ds.max_appointments

        FROM doctors d

        INNER JOIN doctor_schedules ds
            ON d.doctor_id = ds.doctor_id

        LEFT JOIN departments dept
            ON d.department_id = dept.department_id

        WHERE d.employment_status = 'ACTIVE'
          AND ds.status = 'AVAILABLE'
    """

    parameters: list[Any] = []

    if schedule_date is not None:
        query += " AND ds.schedule_date = %s"
        parameters.append(schedule_date)

    # ---------------------------------------------------------
    # Optional department filter
    # ---------------------------------------------------------

    if department_id is not None:
        query += " AND d.department_id = %s"
        parameters.append(department_id)

    # ---------------------------------------------------------
    # Optional speciality filter
    # ---------------------------------------------------------

    if speciality is not None:
        query += " AND d.speciality = %s"
        parameters.append(speciality)

    # ---------------------------------------------------------
    # Optional shift filter
    # ---------------------------------------------------------

    if shift_type is not None:
        query += " AND ds.shift_type = %s"
        parameters.append(shift_type)

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    query += """
        ORDER BY
            ds.start_time,
            d.doctor_id
    """

    # ---------------------------------------------------------
    # Execute query
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, tuple(parameters))

        doctors = cursor.fetchall()

        cursor.close()

        return doctors


def get_available_nurses(
    schedule_date: date | None = None,
    department_id: int | None = None,
    shift_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve active nurses who have an available schedule.

    The schedule date is optional. When omitted, availability is not
    restricted to today; any schedule row with status AVAILABLE may be
    returned. If a schedule_date is supplied, results are restricted to
    that date.

    Optional filters:
        schedule_date:
            Optional date on which the nurse should be available.

        department_id:
            Restrict results to a specific department.

        shift_type:
            MORNING, AFTERNOON, EVENING, or NIGHT.

    Returns:
        A list of nurses with their department and schedule details.
    """

    query = """
        SELECT
            n.nurse_id,
            n.nurse_name,
            n.gender,
            n.employment_status,
            n.shift_preference,

            dept.department_id,
            dept.department_name,
            dept.department_code,

            ns.schedule_id,
            ns.schedule_date,
            ns.shift_type,
            ns.start_time,
            ns.end_time,
            ns.status AS schedule_status

        FROM nurses n

        INNER JOIN nurse_schedules ns
            ON n.nurse_id = ns.nurse_id

        LEFT JOIN departments dept
            ON n.department_id = dept.department_id

        WHERE n.employment_status = 'ACTIVE'
          AND ns.status = 'AVAILABLE'
    """

    parameters: list[Any] = []

    if schedule_date is not None:
        query += " AND ns.schedule_date = %s"
        parameters.append(schedule_date)

    # ---------------------------------------------------------
    # Optional department filter
    # ---------------------------------------------------------

    if department_id is not None:
        query += " AND n.department_id = %s"
        parameters.append(department_id)

    # ---------------------------------------------------------
    # Optional shift filter
    # ---------------------------------------------------------

    if shift_type is not None:
        query += " AND ns.shift_type = %s"
        parameters.append(shift_type)

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    query += """
        ORDER BY
            ns.start_time,
            n.nurse_id
    """

    # ---------------------------------------------------------
    # Execute query
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, tuple(parameters))

        nurses = cursor.fetchall()

        cursor.close()

        return nurses
    
def get_unassigned_admissions() -> list[dict[str, Any]]:
    """
    Retrieve active admissions that still require staff assignment.

    An admission is included when:
        - admission is active
        - patient is alive
        - doctor is not assigned OR nurse is not assigned

    Bed information is included so the frontend can determine
    whether staff assignment is allowed.
    """

    query = """
        SELECT
            a.admission_id,
            a.patient_id,
            a.department_id,
            d.department_name,
            d.department_code,

            a.admission_type,
            a.admission_time,
            a.status,

            a.bed_id,
            a.doctor_id,

            CASE
                WHEN a.bed_id IS NULL THEN 0
                ELSE 1
            END AS has_bed,

            CASE
                WHEN a.doctor_id IS NULL THEN 0
                ELSE 1
            END AS has_doctor

        FROM admissions a

        INNER JOIN departments d
            ON a.department_id = d.department_id

        INNER JOIN patients p
            ON a.patient_id = p.ID

        WHERE a.status IN ('ADMITTED', 'OBSERVATION')
          AND p.DEATHDATE IS NULL
          AND (
              a.doctor_id IS NULL
          )

        ORDER BY
            a.admission_time DESC,
            a.admission_id DESC
    """

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query)

        admissions = cursor.fetchall()

        cursor.close()

        return admissions    