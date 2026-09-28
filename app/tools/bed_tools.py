from typing import Any

from app.database.connection import get_db_connection


def get_available_beds(
    bed_type: str | None = None,
    room_type: str | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve currently available beds.

    Optional filters:
        bed_type:
            STANDARD, ICU, EMERGENCY, PEDIATRIC, MATERNITY

        room_type:
            GENERAL, ICU, ISOLATION, EMERGENCY,
            OPERATING, MATERNITY, PEDIATRIC

        department_id:
            Restrict results to a specific department.

    Returns:
        A list of available beds with room and department details.
    """

    query = """
        SELECT
            b.bed_id,
            b.bed_number,
            b.bed_type,
            b.status AS bed_status,

            r.room_id,
            r.room_number,
            r.room_type,
            r.floor_number,

            d.department_id,
            d.department_name,
            d.department_code

        FROM beds b

        INNER JOIN rooms r
            ON b.room_id = r.room_id

        INNER JOIN departments d
            ON r.department_id = d.department_id

        WHERE b.status = 'AVAILABLE'
          AND r.status = 'AVAILABLE'
          AND d.status = 'ACTIVE'
    """

    parameters: list[Any] = []

    # ---------------------------------------------------------
    # Optional bed type filter
    # ---------------------------------------------------------

    if bed_type is not None:
        query += " AND b.bed_type = %s"
        parameters.append(bed_type)

    # ---------------------------------------------------------
    # Optional room type filter
    # ---------------------------------------------------------

    if room_type is not None:
        query += " AND r.room_type = %s"
        parameters.append(room_type)

    # ---------------------------------------------------------
    # Optional department filter
    # ---------------------------------------------------------

    if department_id is not None:
        query += " AND d.department_id = %s"
        parameters.append(department_id)

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    query += """
        ORDER BY
            d.department_id,
            r.room_id,
            b.bed_id
    """

    # ---------------------------------------------------------
    # Execute query
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, tuple(parameters))

        beds = cursor.fetchall()

        cursor.close()

        return beds
    
def get_eligible_admissions() -> list[dict[str, Any]]:
    """
    Retrieve active admissions that are eligible for bed assignment.

    Eligibility:
        - Admission is ADMITTED or OBSERVATION
        - Admission currently has no bed
        - Patient does not already have an OCCUPIED or RESERVED bed
    """

    query = """
        SELECT
            a.admission_id,
            a.patient_id,
            a.department_id,
            a.admission_type,
            a.admission_time,
            a.diagnosis,
            a.status AS admission_status,

            d.department_name,
            d.department_code

        FROM admissions a

        INNER JOIN departments d
            ON a.department_id = d.department_id

        WHERE a.status IN ('ADMITTED', 'OBSERVATION')
          AND a.bed_id IS NULL
          AND d.status = 'ACTIVE'

          AND NOT EXISTS (
              SELECT 1
              FROM beds b
              WHERE b.patient_id = a.patient_id
                AND b.status IN ('OCCUPIED', 'RESERVED')
          )

        ORDER BY
            a.admission_time ASC,
            a.admission_id ASC
    """

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query)

        admissions = cursor.fetchall()

        cursor.close()

        return admissions    