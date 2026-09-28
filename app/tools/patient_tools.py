from typing import Any

from app.database.connection import get_db_connection


def get_patient_by_id(patient_id: str) -> dict[str, Any] | None:
    """
    Retrieve a patient from the patients table using the
    patient's identifier.

    Returns:
        A dictionary containing patient information if found.
        None if the patient does not exist.
    """

    query = """
        SELECT
            Id,
            BIRTHDATE,
            DEATHDATE,
            PREFIX,
            FIRST,
            LAST,
            SUFFIX,
            MARITAL,
            RACE,
            ETHNICITY,
            GENDER,
            BIRTHPLACE,
            ADDRESS,
            CITY,
            STATE,
            COUNTY,
            ZIP,
            LAT,
            LON,
            HEALTHCARE_EXPENSES,
            HEALTHCARE_COVERAGE
        FROM patients
        WHERE Id = %s
        LIMIT 1
    """

    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, (patient_id,))

        patient = cursor.fetchone()

        cursor.close()

        return patient