from typing import Any

from app.database.connection import get_db_connection


def get_emergency_incident(
    incident_id: int,
) -> dict[str, Any] | None:
    """
    Retrieve a single emergency incident.

    Returns:
        A dictionary containing incident information,
        or None if the incident does not exist.
    """

    query = """
        SELECT
            ei.incident_id,
            ei.patient_id,
            ei.encounter_id,
            ei.admission_id,
            ei.department_id,
            ei.incident_type,
            ei.severity,
            ei.incident_source,
            ei.symptoms,
            ei.incident_time,
            ei.arrival_time,
            ei.triage_time,
            ei.triage_notes,
            ei.status,

            d.department_name,
            d.department_code

        FROM emergency_incidents ei

        LEFT JOIN departments d
            ON ei.department_id = d.department_id

        WHERE ei.incident_id = %s

        LIMIT 1
    """

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, (incident_id,))

        incident = cursor.fetchone()

        cursor.close()

        return incident


def get_available_ambulances(
    ambulance_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve ambulances that are currently available.

    Optional filter:
        ambulance_type:
            BASIC_LIFE_SUPPORT
            ADVANCED_LIFE_SUPPORT
            PATIENT_TRANSPORT

    Returns:
        A list of available ambulances.
    """

    query = """
        SELECT
            ambulance_id,
            hospital_id,
            ambulance_number,
            ambulance_type,
            status,
            current_location,
            latitude,
            longitude,
            driver_name,
            paramedic_name,
            last_maintenance_date

        FROM ambulances

        WHERE status = 'AVAILABLE'
    """

    parameters: list[Any] = []

    # ---------------------------------------------------------
    # Optional ambulance type filter
    # ---------------------------------------------------------

    if ambulance_type is not None:
        query += " AND ambulance_type = %s"
        parameters.append(ambulance_type)

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    query += """
        ORDER BY ambulance_id
    """

    # ---------------------------------------------------------
    # Execute query
    # ---------------------------------------------------------

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, tuple(parameters))

        ambulances = cursor.fetchall()

        cursor.close()

        return ambulances


def get_ambulance_dispatch(
    dispatch_id: int,
) -> dict[str, Any] | None:
    """
    Retrieve details of a specific ambulance dispatch.

    Returns:
        A dictionary containing dispatch and ambulance information,
        or None if the dispatch does not exist.
    """

    query = """
        SELECT
            ad.dispatch_id,
            ad.incident_id,
            ad.ambulance_id,
            ad.dispatch_status,
            ad.requested_at,
            ad.dispatched_at,
            ad.scene_arrival_at,
            ad.hospital_arrival_at,
            ad.completed_at,
            ad.pickup_location,
            ad.destination,
            ad.estimated_arrival_minutes,
            ad.actual_distance_km,
            ad.notes,

            a.ambulance_number,
            a.ambulance_type,
            a.status AS ambulance_status,
            a.current_location,
            a.driver_name,
            a.paramedic_name

        FROM ambulance_dispatches ad

        INNER JOIN ambulances a
            ON ad.ambulance_id = a.ambulance_id

        WHERE ad.dispatch_id = %s

        LIMIT 1
    """

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, (dispatch_id,))

        dispatch = cursor.fetchone()

        cursor.close()

        return dispatch