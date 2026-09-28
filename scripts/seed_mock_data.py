"""
Hospital AI - Mock Operational Data Seeder

Purpose:
    Populate the hospital_ai operational database with a large,
    varied and relationally consistent mock dataset.

Important:
    - Does NOT delete existing data.
    - Does NOT modify the original Synthea patient data.
    - Reuses existing patients, departments, doctors, nurses,
      beds, ambulances and medication inventory.
    - Does NOT fabricate agent_actions, audit_logs or
      action_gateway_requests. Those should primarily be generated
      by actual agent/system execution.
    - Uses MOCK_DATA markers where practical.
    - Uses one database transaction for the seed operation.

Run from project root:

    python scripts/seed_mock_data.py
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, time, timedelta
from typing import Any

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from app.database.connection import get_db_connection


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 20260918

NUM_EMERGENCY_INCIDENTS = 450
NUM_ADMISSIONS = 450
NUM_APPOINTMENTS = 450
NUM_LAB_ORDERS = 450
NUM_MEDICATION_REQUESTS = 450
NUM_TRANSFERS = 150
NUM_HOSPITAL_EVENTS = 500
NUM_NOTIFICATIONS = 500

# Ambulance dispatches are limited by the existing ambulance
# fleet. We create historical/completed records, therefore
# multiple dispatches can use the same ambulance.
NUM_AMBULANCE_DISPATCHES = 100

# Number of patients to sample from the existing patient table.
PATIENT_POOL_SIZE = 2000

# Historical date range for mock records.
HISTORY_DAYS = 120


# ============================================================
# RANDOM GENERATOR
# ============================================================

rng = random.Random(RANDOM_SEED)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def weighted_choice(values: list[tuple[Any, int]]) -> Any:
    """Return one value according to integer weights."""

    items = [item[0] for item in values]
    weights = [item[1] for item in values]

    return rng.choices(items, weights=weights, k=1)[0]


def random_datetime(
    days_back: int = HISTORY_DAYS,
    max_days_forward: int = 0,
) -> datetime:
    """Generate a random datetime in the requested range."""

    now = datetime.now()

    earliest = now - timedelta(days=days_back)
    latest = now + timedelta(days=max_days_forward)

    total_seconds = int((latest - earliest).total_seconds())

    offset = rng.randint(0, total_seconds)

    return earliest + timedelta(seconds=offset)


def random_date(
    days_back: int = HISTORY_DAYS,
    max_days_forward: int = 0,
) -> date:
    return random_datetime(
        days_back=days_back,
        max_days_forward=max_days_forward,
    ).date()


def random_time(
    start_hour: int = 7,
    end_hour: int = 21,
) -> time:
    hour = rng.randint(start_hour, end_hour - 1)
    minute = rng.choice([0, 15, 30, 45])

    return time(
        hour=hour,
        minute=minute,
        second=0,
    )


def json_text(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        default=str,
    )


def mock_note(text: str) -> str:
    return f"MOCK_DATA | {text}"


# ============================================================
# DATABASE HELPERS
# ============================================================

def fetch_all(
    cursor,
    query: str,
    params: tuple = (),
) -> list[dict[str, Any]]:
    cursor.execute(query, params)
    return cursor.fetchall()


def fetch_one(
    cursor,
    query: str,
    params: tuple = (),
) -> dict[str, Any] | None:
    cursor.execute(query, params)
    return cursor.fetchone()


# ============================================================
# LOAD EXISTING HOSPITAL RESOURCES
# ============================================================

def load_reference_data(cursor) -> dict[str, list[dict[str, Any]]]:

    print("\nLoading existing hospital resources...")

    patients = fetch_all(
        cursor,
        """
        SELECT
            ID AS patient_id
        FROM patients
        WHERE DEATHDATE IS NULL
        LIMIT %s
        """,
        (PATIENT_POOL_SIZE,),
    )

    departments = fetch_all(
        cursor,
        """
        SELECT
            department_id,
            hospital_id,
            department_name
        FROM departments
        WHERE status = 'ACTIVE'
        ORDER BY department_id
        """,
    )

    doctors = fetch_all(
        cursor,
        """
        SELECT
            doctor_id,
            hospital_id,
            department_id,
            doctor_name,
            speciality
        FROM doctors
        WHERE employment_status = 'ACTIVE'
        ORDER BY doctor_id
        """,
    )

    nurses = fetch_all(
        cursor,
        """
        SELECT
            nurse_id,
            hospital_id,
            department_id,
            nurse_name
        FROM nurses
        WHERE employment_status = 'ACTIVE'
        ORDER BY nurse_id
        """,
    )

    beds = fetch_all(
        cursor,
        """
        SELECT
            bed_id,
            room_id,
            bed_number,
            bed_type,
            status,
            patient_id
        FROM beds
        ORDER BY bed_id
        """,
    )

    available_beds = fetch_all(
        cursor,
        """
        SELECT
            bed_id,
            room_id,
            bed_number,
            bed_type,
            status
        FROM beds
        WHERE status = 'AVAILABLE'
        ORDER BY bed_id
        """,
    )

    ambulances = fetch_all(
        cursor,
        """
        SELECT
            ambulance_id,
            hospital_id,
            ambulance_number,
            ambulance_type
        FROM ambulances
        ORDER BY ambulance_id
        """,
    )

    medications = fetch_all(
        cursor,
        """
        SELECT
            medication_inventory_id,
            medication_code,
            medication_name,
            category,
            unit,
            quantity_on_hand,
            reorder_level,
            status
        FROM medication_inventory
        ORDER BY medication_inventory_id
        """,
    )

    inventory = fetch_all(
        cursor,
        """
        SELECT
            inventory_id,
            hospital_id,
            item_code,
            item_name,
            category,
            quantity_on_hand,
            reorder_level,
            status
        FROM inventory
        ORDER BY inventory_id
        """,
    )

    rooms = fetch_all(
        cursor,
        """
        SELECT
            room_id,
            department_id,
            room_number,
            room_type
        FROM rooms
        ORDER BY room_id
        """,
    )

    encounters = fetch_all(
        cursor,
        """
        SELECT
            ID AS encounter_id,
            PATIENT AS patient_id
        FROM encounters
        LIMIT %s
        """,
        (PATIENT_POOL_SIZE,),
    )

    if not patients:
        raise RuntimeError(
            "No living patients were found."
        )

    if not departments:
        raise RuntimeError(
            "No active departments were found."
        )

    if not doctors:
        raise RuntimeError(
            "No active doctors were found."
        )

    if not nurses:
        raise RuntimeError(
            "No active nurses were found."
        )

    if not ambulances:
        raise RuntimeError(
            "No ambulances were found."
        )

    if not medications:
        raise RuntimeError(
            "No medication inventory records were found."
        )

    print(f"  Patients loaded       : {len(patients)}")
    print(f"  Departments loaded    : {len(departments)}")
    print(f"  Doctors loaded        : {len(doctors)}")
    print(f"  Nurses loaded         : {len(nurses)}")
    print(f"  Beds loaded           : {len(beds)}")
    print(f"  Available beds        : {len(available_beds)}")
    print(f"  Ambulances loaded     : {len(ambulances)}")
    print(f"  Medications loaded    : {len(medications)}")
    print(f"  Inventory loaded      : {len(inventory)}")
    print(f"  Rooms loaded          : {len(rooms)}")
    print(f"  Encounters loaded     : {len(encounters)}")

    return {
        "patients": patients,
        "departments": departments,
        "doctors": doctors,
        "nurses": nurses,
        "beds": beds,
        "available_beds": available_beds,
        "ambulances": ambulances,
        "medications": medications,
        "inventory": inventory,
        "rooms": rooms,
        "encounters": encounters,
    }


# ============================================================
# PATIENT / REFERENCE SELECTION
# ============================================================

def choose_patient(resources):
    return rng.choice(resources["patients"])


def choose_department(resources):
    return rng.choice(resources["departments"])


def choose_doctor_for_department(
    resources,
    department_id: int,
):
    matching = [
        doctor
        for doctor in resources["doctors"]
        if doctor["department_id"] == department_id
    ]

    if matching:
        return rng.choice(matching)

    return rng.choice(resources["doctors"])


def choose_nurse_for_department(
    resources,
    department_id: int,
):
    matching = [
        nurse
        for nurse in resources["nurses"]
        if nurse["department_id"] == department_id
    ]

    if matching:
        return rng.choice(matching)

    return rng.choice(resources["nurses"])


def choose_encounter(
    resources,
    patient_id: str | None = None,
):
    encounters = resources["encounters"]

    if patient_id is not None:
        matching = [
            encounter
            for encounter in encounters
            if encounter["patient_id"] == patient_id
        ]

        if matching:
            return rng.choice(matching)

    if encounters:
        return rng.choice(encounters)

    return None


# ============================================================
# EXISTING MOCK DATA DETECTION
# ============================================================

def existing_mock_count(
    cursor,
    table_name: str,
    column_name: str,
) -> int:
    query = f"""
        SELECT COUNT(*) AS count
        FROM {table_name}
        WHERE {column_name} LIKE 'MOCK_DATA%'
    """

    cursor.execute(query)
    row = cursor.fetchone()

    return int(row["count"])


# ============================================================
# 1. ADMISSIONS
# ============================================================

def seed_admissions(
    cursor,
    resources,
) -> list[int]:

    print("\n[1/10] Creating admissions...")

    admission_ids: list[int] = []

    admission_types = [
        ("EMERGENCY", 40),
        ("ELECTIVE", 25),
        ("TRANSFER", 20),
        ("OBSERVATION", 15),
    ]

    statuses = [
        ("DISCHARGED", 55),
        ("ADMITTED", 30),
        ("OBSERVATION", 10),
        ("CANCELLED", 5),
    ]

    for index in range(NUM_ADMISSIONS):

        patient = choose_patient(resources)
        patient_id = patient["patient_id"]

        department = choose_department(resources)
        department_id = department["department_id"]

        doctor = choose_doctor_for_department(
            resources,
            department_id,
        )

        admission_type = weighted_choice(
            admission_types
        )

        status = weighted_choice(
            statuses
        )

        admission_time = random_datetime(
            days_back=HISTORY_DAYS
        )

        expected_discharge = (
            admission_time
            + timedelta(
                days=rng.randint(1, 14)
            )
        )

        actual_discharge = None

        if status == "DISCHARGED":
            actual_discharge = expected_discharge

        # Historical discharged admissions do not need a
        # currently occupied bed.
        bed_id = None

        diagnosis = weighted_choice([
            ("Acute respiratory condition", 15),
            ("Cardiac evaluation", 10),
            ("Trauma observation", 10),
            ("Neurological evaluation", 10),
            ("Infection management", 15),
            ("Post-operative monitoring", 10),
            ("Routine medical management", 20),
            ("Emergency observation", 10),
        ])

        notes = mock_note(
            f"Admission scenario {index + 1}"
        )

        cursor.execute(
            """
            INSERT INTO admissions (
                patient_id,
                bed_id,
                doctor_id,
                department_id,
                encounter_id,
                admission_type,
                admission_time,
                expected_discharge_time,
                actual_discharge_time,
                status,
                diagnosis,
                notes
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                patient_id,
                bed_id,
                doctor["doctor_id"],
                department_id,
                (
                    choose_encounter(
                        resources,
                        patient_id,
                    ) or {}
                ).get("encounter_id"),
                admission_type,
                admission_time,
                expected_discharge,
                actual_discharge,
                status,
                diagnosis,
                notes,
            ),
        )

        admission_ids.append(
            cursor.lastrowid
        )

    print(
        f"  Created {len(admission_ids)} admissions."
    )

    return admission_ids


# ============================================================
# 2. EMERGENCY INCIDENTS
# ============================================================

def seed_emergency_incidents(
    cursor,
    resources,
    admission_ids,
) -> list[int]:

    print("\n[2/10] Creating emergency incidents...")

    incident_ids: list[int] = []

    incident_types = [
        "TRAUMA",
        "CARDIAC",
        "RESPIRATORY",
        "NEUROLOGICAL",
        "ACCIDENT",
        "MEDICAL",
        "OTHER",
    ]

    severities = [
        ("CRITICAL", 15),
        ("HIGH", 30),
        ("MEDIUM", 35),
        ("LOW", 20),
    ]

    sources = [
        ("AMBULANCE", 25),
        ("WALK_IN", 25),
        ("REFERRAL", 15),
        ("INTERNAL", 15),
        ("AI_DETECTED", 20),
    ]

    statuses = [
        ("REPORTED", 15),
        ("TRIAGED", 15),
        ("AWAITING_TRANSPORT", 10),
        ("IN_TRANSIT", 5),
        ("ARRIVED", 10),
        ("ADMITTED", 20),
        ("RESOLVED", 20),
        ("CANCELLED", 5),
    ]

    symptom_map = {
        "TRAUMA": [
            "Severe external injury",
            "Suspected fracture",
            "Bleeding after accident",
        ],
        "CARDIAC": [
            "Chest pain",
            "Shortness of breath",
            "Palpitations",
        ],
        "RESPIRATORY": [
            "Breathing difficulty",
            "Low oxygen saturation",
            "Persistent cough",
        ],
        "NEUROLOGICAL": [
            "Sudden weakness",
            "Confusion",
            "Severe headache",
        ],
        "ACCIDENT": [
            "Road accident injuries",
            "Fall injury",
            "Workplace injury",
        ],
        "MEDICAL": [
            "High fever",
            "Acute pain",
            "General medical emergency",
        ],
        "OTHER": [
            "Unspecified emergency symptoms",
            "Acute discomfort",
            "Urgent clinical complaint",
        ],
    }

    for index in range(NUM_EMERGENCY_INCIDENTS):

        patient = choose_patient(resources)
        patient_id = patient["patient_id"]

        department = choose_department(resources)
        department_id = department["department_id"]

        incident_type = rng.choice(
            incident_types
        )

        severity = weighted_choice(
            severities
        )

        source = weighted_choice(
            sources
        )

        status = weighted_choice(
            statuses
        )

        incident_time = random_datetime(
            days_back=HISTORY_DAYS
        )

        arrival_time = None
        triage_time = None

        if status in {
            "TRIAGED",
            "AWAITING_TRANSPORT",
            "IN_TRANSIT",
            "ARRIVED",
            "ADMITTED",
            "RESOLVED",
        }:
            arrival_time = incident_time + timedelta(
                minutes=rng.randint(5, 90)
            )

            triage_time = arrival_time + timedelta(
                minutes=rng.randint(2, 30)
            )

        symptoms = rng.choice(
            symptom_map[incident_type]
        )

        triage_notes = None

        if triage_time is not None:
            triage_notes = mock_note(
                f"{severity} severity emergency triage"
            )

        # Only some incidents are connected to an admission.
        admission_id = None

        if status in {
            "ARRIVED",
            "ADMITTED",
            "RESOLVED",
        }:
            admission_id = rng.choice(
                admission_ids
            )

        encounter = choose_encounter(
            resources,
            patient_id,
        )

        cursor.execute(
            """
            INSERT INTO emergency_incidents (
                patient_id,
                encounter_id,
                admission_id,
                department_id,
                incident_type,
                severity,
                incident_source,
                symptoms,
                incident_time,
                arrival_time,
                triage_time,
                triage_notes,
                status
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            """,
            (
                patient_id,
                (
                    encounter or {}
                ).get("encounter_id"),
                admission_id,
                department_id,
                incident_type,
                severity,
                source,
                symptoms,
                incident_time,
                arrival_time,
                triage_time,
                triage_notes,
                status,
            ),
        )

        incident_ids.append(
            cursor.lastrowid
        )

    print(
        f"  Created {len(incident_ids)} emergency incidents."
    )

    return incident_ids


# ============================================================
# 3. APPOINTMENTS
# ============================================================

def seed_appointments(
    cursor,
    resources,
):

    print("\n[3/10] Creating appointments...")

    appointment_types = [
        "CONSULTATION",
        "FOLLOW_UP",
        "EMERGENCY",
        "DIAGNOSTIC",
        "PROCEDURE",
        "ROUTINE_CHECKUP",
    ]

    statuses = [
        ("SCHEDULED", 35),
        ("CONFIRMED", 25),
        ("COMPLETED", 25),
        ("CANCELLED", 10),
        ("NO_SHOW", 5),
    ]

    for index in range(NUM_APPOINTMENTS):

        patient = choose_patient(resources)
        patient_id = patient["patient_id"]

        department = choose_department(resources)
        department_id = department["department_id"]

        doctor = choose_doctor_for_department(
            resources,
            department_id,
        )

        appointment_date = random_date(
            days_back=60,
            max_days_forward=30,
        )

        start_time = random_time()

        start_dt = datetime.combine(
            appointment_date,
            start_time,
        )

        end_dt = start_dt + timedelta(
            minutes=rng.choice(
                [30, 45, 60]
            )
        )

        status = weighted_choice(
            statuses
        )

        cursor.execute(
            """
            INSERT INTO appointments (
                patient_id,
                doctor_id,
                department_id,
                encounter_id,
                appointment_date,
                start_time,
                end_time,
                appointment_type,
                status,
                reason,
                notes
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                patient_id,
                doctor["doctor_id"],
                department_id,
                (
                    choose_encounter(
                        resources,
                        patient_id,
                    ) or {}
                ).get("encounter_id"),
                appointment_date,
                start_time,
                end_dt.time(),
                rng.choice(
                    appointment_types
                ),
                status,
                mock_note(
                    "Clinical appointment scenario"
                ),
                mock_note(
                    f"Appointment scenario {index + 1}"
                ),
            ),
        )

    print(
        f"  Created {NUM_APPOINTMENTS} appointments."
    )


# ============================================================
# 4. LAB ORDERS + RESULTS
# ============================================================

def seed_lab_orders_and_results(
    cursor,
    resources,
):

    print("\n[4/10] Creating lab orders and results...")

    tests = [
        (
            "CBC",
            "Complete Blood Count",
        ),
        (
            "BMP",
            "Basic Metabolic Panel",
        ),
        (
            "LFT",
            "Liver Function Test",
        ),
        (
            "RFT",
            "Renal Function Test",
        ),
        (
            "CRP",
            "C-Reactive Protein",
        ),
        (
            "TROPONIN",
            "Troponin Test",
        ),
        (
            "D_DIMER",
            "D-Dimer Test",
        ),
        (
            "GLUCOSE",
            "Blood Glucose",
        ),
        (
            "OXYGEN",
            "Oxygen Saturation",
        ),
        (
            "COVID",
            "COVID-19 Test",
        ),
    ]

    priorities = [
        ("ROUTINE", 55),
        ("URGENT", 30),
        ("STAT", 15),
    ]

    order_statuses = [
        ("ORDERED", 20),
        ("COLLECTED", 15),
        ("PROCESSING", 15),
        ("COMPLETED", 40),
        ("CANCELLED", 10),
    ]

    result_statuses = [
        ("NORMAL", 55),
        ("ABNORMAL", 25),
        ("CRITICAL", 10),
        ("PENDING", 10),
    ]

    lab_order_ids: list[int] = []

    for index in range(NUM_LAB_ORDERS):

        patient = choose_patient(resources)
        patient_id = patient["patient_id"]

        department = choose_department(resources)
        department_id = department["department_id"]

        doctor = choose_doctor_for_department(
            resources,
            department_id,
        )

        test_code, test_name = rng.choice(
            tests
        )

        priority = weighted_choice(
            priorities
        )

        order_status = weighted_choice(
            order_statuses
        )

        ordered_at = random_datetime(
            days_back=HISTORY_DAYS
        )

        collected_at = None
        completed_at = None

        if order_status in {
            "COLLECTED",
            "PROCESSING",
            "COMPLETED",
        }:
            collected_at = ordered_at + timedelta(
                minutes=rng.randint(10, 180)
            )

        if order_status == "COMPLETED":
            completed_at = collected_at + timedelta(
                minutes=rng.randint(30, 240)
            )

        cursor.execute(
            """
            INSERT INTO lab_orders (
                patient_id,
                doctor_id,
                department_id,
                encounter_id,
                test_code,
                test_name,
                priority,
                order_status,
                ordered_at,
                collected_at,
                completed_at,
                clinical_notes
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                patient_id,
                doctor["doctor_id"],
                department_id,
                (
                    choose_encounter(
                        resources,
                        patient_id,
                    ) or {}
                ).get("encounter_id"),
                test_code,
                test_name,
                priority,
                order_status,
                ordered_at,
                collected_at,
                completed_at,
                mock_note(
                    f"Diagnostic scenario {index + 1}"
                ),
            ),
        )

        lab_order_id = cursor.lastrowid

        lab_order_ids.append(
            lab_order_id
        )

        # Most completed orders receive results.
        # Some remain pending intentionally.
        should_create_result = (
            order_status != "CANCELLED"
            and (
                rng.random() < 0.92
            )
        )

        if not should_create_result:
            continue

        result_status = weighted_choice(
            result_statuses
        )

        numeric_value = None
        result_value = None
        unit = None
        reference_range = None
        interpretation = None

        if test_code == "GLUCOSE":
            numeric_value = rng.uniform(
                65,
                220,
            )
            unit = "mg/dL"
            reference_range = "70-100"
            result_value = f"{numeric_value:.1f}"

        elif test_code == "OXYGEN":
            numeric_value = rng.uniform(
                86,
                100,
            )
            unit = "%"
            reference_range = "95-100"
            result_value = f"{numeric_value:.1f}"

        elif test_code == "TROPONIN":
            numeric_value = rng.uniform(
                0.01,
                5.0,
            )
            unit = "ng/mL"
            reference_range = "<0.04"
            result_value = f"{numeric_value:.2f}"

        else:
            numeric_value = rng.uniform(
                1,
                100,
            )
            unit = "unit"
            reference_range = "Normal range"
            result_value = f"{numeric_value:.2f}"

        if result_status == "CRITICAL":
            interpretation = (
                "Critical result requires clinical review."
            )

        elif result_status == "ABNORMAL":
            interpretation = (
                "Abnormal result requires clinical assessment."
            )

        elif result_status == "NORMAL":
            interpretation = (
                "Result within expected range."
            )

        performed_at = None
        verified_at = None
        verified_by = None

        if order_status == "COMPLETED":
            performed_at = completed_at

            if result_status != "PENDING":
                verified_at = (
                    performed_at
                    + timedelta(
                        minutes=rng.randint(
                            10,
                            180,
                        )
                    )
                )

                verified_by = doctor["doctor_id"]

        cursor.execute(
            """
            INSERT INTO lab_results (
                lab_order_id,
                patient_id,
                test_name,
                result_value,
                numeric_value,
                unit,
                reference_range,
                result_status,
                performed_at,
                verified_at,
                verified_by_doctor_id,
                interpretation
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                lab_order_id,
                patient_id,
                test_name,
                result_value,
                numeric_value,
                unit,
                reference_range,
                result_status,
                performed_at,
                verified_at,
                verified_by,
                interpretation,
            ),
        )

    print(
        f"  Created {len(lab_order_ids)} lab orders."
    )

    print(
        "  Created linked lab results for most non-cancelled orders."
    )


# ============================================================
# 5. MEDICATION REQUESTS
# ============================================================

def seed_medication_requests(
    cursor,
    resources,
    admission_ids,
):

    print("\n[5/10] Creating medication requests...")

    priorities = [
        ("ROUTINE", 55),
        ("URGENT", 30),
        ("STAT", 15),
    ]

    request_types = [
        ("PRESCRIPTION", 45),
        ("ADMINISTRATION", 25),
        ("REFILL", 15),
        ("EMERGENCY", 15),
    ]

    statuses = [
        ("REQUESTED", 30),
        ("APPROVED", 20),
        ("DISPENSED", 20),
        ("ADMINISTERED", 15),
        ("REJECTED", 10),
        ("CANCELLED", 5),
    ]

    for index in range(NUM_MEDICATION_REQUESTS):

        patient = choose_patient(resources)
        patient_id = patient["patient_id"]

        department = choose_department(resources)
        department_id = department["department_id"]

        doctor = choose_doctor_for_department(
            resources,
            department_id,
        )

        medication = rng.choice(
            resources["medications"]
        )

        priority = weighted_choice(
            priorities
        )

        request_type = weighted_choice(
            request_types
        )

        status = weighted_choice(
            statuses
        )

        requested_at = random_datetime(
            days_back=HISTORY_DAYS
        )

        approved_at = None
        dispensed_at = None

        if status in {
            "APPROVED",
            "DISPENSED",
            "ADMINISTERED",
        }:
            approved_at = requested_at + timedelta(
                minutes=rng.randint(10, 180)
            )

        if status in {
            "DISPENSED",
            "ADMINISTERED",
        }:
            dispensed_at = approved_at + timedelta(
                minutes=rng.randint(10, 180)
            )

        admission_id = None

        if rng.random() < 0.65:
            admission_id = rng.choice(
                admission_ids
            )

        quantity = rng.randint(
            1,
            10,
        )

        cursor.execute(
            """
            INSERT INTO medication_requests (
                patient_id,
                doctor_id,
                admission_id,
                encounter_id,
                medication_inventory_id,
                requested_quantity,
                priority,
                request_type,
                status,
                requested_at,
                approved_at,
                dispensed_at,
                notes
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            """,
            (
                patient_id,
                doctor["doctor_id"],
                admission_id,
                (
                    choose_encounter(
                        resources,
                        patient_id,
                    ) or {}
                ).get("encounter_id"),
                medication[
                    "medication_inventory_id"
                ],
                quantity,
                priority,
                request_type,
                status,
                requested_at,
                approved_at,
                dispensed_at,
                mock_note(
                    f"Medication scenario {index + 1}"
                ),
            ),
        )

    print(
        f"  Created {NUM_MEDICATION_REQUESTS} medication requests."
    )


# ============================================================
# 6. PATIENT TRANSFERS
# ============================================================

def seed_patient_transfers(
    cursor,
    resources,
    admission_ids,
):

    print("\n[6/10] Creating patient transfers...")

    statuses = [
        ("REQUESTED", 30),
        ("APPROVED", 20),
        ("IN_PROGRESS", 15),
        ("COMPLETED", 25),
        ("CANCELLED", 10),
    ]

    for index in range(NUM_TRANSFERS):

        admission_id = rng.choice(
            admission_ids
        )

        admission = fetch_one(
            cursor,
            """
            SELECT
                admission_id,
                patient_id,
                department_id,
                bed_id,
                doctor_id
            FROM admissions
            WHERE admission_id = %s
            """,
            (admission_id,),
        )

        if not admission:
            continue

        patient_id = admission["patient_id"]
        from_department_id = admission["department_id"]

        possible_departments = [
            d
            for d in resources["departments"]
            if d["department_id"] != from_department_id
        ]

        if not possible_departments:
            continue

        to_department = rng.choice(
            possible_departments
        )

        status = weighted_choice(
            statuses
        )

        transfer_time = random_datetime(
            days_back=HISTORY_DAYS
        )

        cursor.execute(
            """
            INSERT INTO patient_transfers (
                admission_id,
                patient_id,
                from_department_id,
                to_department_id,
                from_bed_id,
                to_bed_id,
                requested_by_doctor_id,
                transfer_time,
                reason,
                status,
                notes
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                admission_id,
                patient_id,
                from_department_id,
                to_department["department_id"],
                admission["bed_id"],
                None,
                admission["doctor_id"],
                transfer_time,
                rng.choice([
                    "Higher level of care required",
                    "Specialist consultation",
                    "Department change",
                    "Bed availability",
                    "Clinical monitoring",
                ]),
                status,
                mock_note(
                    f"Transfer scenario {index + 1}"
                ),
            ),
        )

    print(
        f"  Created approximately {NUM_TRANSFERS} patient transfers."
    )


# ============================================================
# 7. AMBULANCE DISPATCHES
# ============================================================

def seed_ambulance_dispatches(
    cursor,
    resources,
    incident_ids,
):

    print("\n[7/10] Creating ambulance dispatches...")

    dispatch_statuses = [
        ("REQUESTED", 10),
        ("DISPATCHED", 10),
        ("EN_ROUTE", 10),
        ("AT_SCENE", 10),
        ("TRANSPORTING", 10),
        ("ARRIVED_HOSPITAL", 15),
        ("COMPLETED", 25),
        ("CANCELLED", 10),
    ]

    # Historical dispatches can reuse ambulances.
    # This avoids artificially modifying the current ambulance
    # availability state.

    created = 0

    for index in range(NUM_AMBULANCE_DISPATCHES):

        incident_id = rng.choice(
            incident_ids
        )

        ambulance = rng.choice(
            resources["ambulances"]
        )

        status = weighted_choice(
            dispatch_statuses
        )

        requested_at = random_datetime(
            days_back=HISTORY_DAYS
        )

        dispatched_at = None
        scene_arrival_at = None
        hospital_arrival_at = None
        completed_at = None

        if status != "REQUESTED":

            dispatched_at = requested_at + timedelta(
                minutes=rng.randint(2, 20)
            )

        if status in {
            "AT_SCENE",
            "TRANSPORTING",
            "ARRIVED_HOSPITAL",
            "COMPLETED",
        }:

            scene_arrival_at = (
                dispatched_at
                + timedelta(
                    minutes=rng.randint(
                        10,
                        45,
                    )
                )
            )

        if status in {
            "TRANSPORTING",
            "ARRIVED_HOSPITAL",
            "COMPLETED",
        }:

            hospital_arrival_at = (
                scene_arrival_at
                + timedelta(
                    minutes=rng.randint(
                        15,
                        90,
                    )
                )
            )

        if status == "COMPLETED":

            completed_at = (
                hospital_arrival_at
                + timedelta(
                    minutes=rng.randint(
                        10,
                        60,
                    )
                )
            )

        cursor.execute(
            """
            INSERT INTO ambulance_dispatches (
                ambulance_id,
                incident_id,
                dispatch_status,
                requested_at,
                dispatched_at,
                scene_arrival_at,
                hospital_arrival_at,
                completed_at,
                pickup_location,
                destination,
                estimated_arrival_minutes,
                actual_distance_km,
                notes
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            """,
            (
                ambulance["ambulance_id"],
                incident_id,
                status,
                requested_at,
                dispatched_at,
                scene_arrival_at,
                hospital_arrival_at,
                completed_at,
                rng.choice([
                    "City Center",
                    "Residential Area",
                    "Industrial Area",
                    "Highway",
                    "Railway Station",
                    "Airport",
                    "Nearby Clinic",
                ]),
                "Hospital Emergency Department",
                rng.randint(5, 45),
                round(
                    rng.uniform(
                        1.5,
                        35.0,
                    ),
                    2,
                ),
                mock_note(
                    f"Ambulance dispatch scenario {index + 1}"
                ),
            ),
        )

        created += 1

    print(
        f"  Created {created} ambulance dispatches."
    )


# ============================================================
# 8. HOSPITAL EVENTS
# ============================================================

def seed_hospital_events(
    cursor,
    resources,
    admission_ids,
    incident_ids,
):

    print("\n[8/10] Creating hospital events...")

    event_types = [
        ("PATIENT_ARRIVAL", 15),
        ("TRIAGE_REQUIRED", 15),
        ("BED_REQUIRED", 15),
        ("BED_RESERVED", 10),
        ("DOCTOR_REQUIRED", 10),
        ("LAB_RESULT_READY", 10),
        ("CRITICAL_LAB_RESULT", 5),
        ("MEDICATION_REQUESTED", 10),
        ("LOW_STOCK_ALERT", 5),
        ("EQUIPMENT_ALERT", 5),
    ]

    severities = [
        ("INFO", 40),
        ("LOW", 20),
        ("MEDIUM", 20),
        ("HIGH", 15),
        ("CRITICAL", 5),
    ]

    statuses = [
        ("NEW", 25),
        ("PROCESSING", 15),
        ("PROCESSED", 40),
        ("FAILED", 10),
        ("IGNORED", 10),
    ]

    for index in range(NUM_HOSPITAL_EVENTS):

        event_type = weighted_choice(
            event_types
        )

        severity = weighted_choice(
            severities
        )

        event_status = weighted_choice(
            statuses
        )

        patient = choose_patient(resources)
        patient_id = patient["patient_id"]

        admission_id = (
            rng.choice(admission_ids)
            if rng.random() < 0.65
            else None
        )

        incident_id = (
            rng.choice(incident_ids)
            if rng.random() < 0.45
            else None
        )

        department = choose_department(
            resources
        )

        created_at = random_datetime(
            days_back=HISTORY_DAYS
        )

        processed_at = None

        if event_status == "PROCESSED":
            processed_at = (
                created_at
                + timedelta(
                    minutes=rng.randint(
                        5,
                        240,
                    )
                )
            )

        event_data = {
            "mock": True,
            "scenario_number": index + 1,
            "event_category": event_type,
            "severity": severity,
        }

        cursor.execute(
            """
            INSERT INTO hospital_events (
                event_type,
                patient_id,
                admission_id,
                incident_id,
                department_id,
                severity,
                source,
                event_data,
                event_status,
                created_at,
                processed_at
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                event_type,
                patient_id,
                admission_id,
                incident_id,
                department["department_id"],
                severity,
                "MOCK_DATA_SEEDER",
                json_text(event_data),
                event_status,
                created_at,
                processed_at,
            ),
        )

    print(
        f"  Created {NUM_HOSPITAL_EVENTS} hospital events."
    )


# ============================================================
# 9. NOTIFICATIONS
# ============================================================

def seed_notifications(
    cursor,
    resources,
    admission_ids,
    incident_ids,
):

    print("\n[9/10] Creating notifications...")

    recipient_types = [
        "DOCTOR",
        "NURSE",
        "ADMIN",
        "PHARMACY",
        "LAB",
        "EMERGENCY_TEAM",
        "PATIENT",
        "SYSTEM",
    ]

    notification_types = [
        ("ALERT", 25),
        ("INFO", 25),
        ("WARNING", 20),
        ("REMINDER", 20),
        ("CRITICAL", 10),
    ]

    channels = [
        "EMAIL",
        "SMS",
        "PUSH",
        "WHATSAPP",
        "IN_APP",
    ]

    statuses = [
        ("PENDING", 25),
        ("SENT", 25),
        ("DELIVERED", 35),
        ("FAILED", 10),
        ("CANCELLED", 5),
    ]

    priorities = [
        ("LOW", 20),
        ("NORMAL", 45),
        ("HIGH", 25),
        ("URGENT", 10),
    ]

    titles = [
        "Emergency case requires attention",
        "Lab result available",
        "Medication request pending",
        "Low inventory alert",
        "Patient transfer requested",
        "Doctor assignment required",
        "Bed allocation required",
        "Critical clinical alert",
        "Appointment reminder",
        "System operational notification",
    ]

    for index in range(NUM_NOTIFICATIONS):

        patient = choose_patient(resources)
        patient_id = patient["patient_id"]

        admission_id = (
            rng.choice(admission_ids)
            if rng.random() < 0.60
            else None
        )

        incident_id = (
            rng.choice(incident_ids)
            if rng.random() < 0.45
            else None
        )

        recipient_type = rng.choice(
            recipient_types
        )

        notification_type = weighted_choice(
            notification_types
        )

        channel = rng.choice(
            channels
        )

        status = weighted_choice(
            statuses
        )

        priority = weighted_choice(
            priorities
        )

        created_at = random_datetime(
            days_back=HISTORY_DAYS
        )

        scheduled_at = (
            created_at
            + timedelta(
                minutes=rng.randint(
                    0,
                    1440,
                )
            )
        )

        sent_at = None

        if status in {
            "SENT",
            "DELIVERED",
        }:

            sent_at = scheduled_at + timedelta(
                minutes=rng.randint(
                    1,
                    120,
                )
            )

        cursor.execute(
            """
            INSERT INTO notifications (
                patient_id,
                admission_id,
                incident_id,
                recipient_type,
                recipient_id,
                notification_type,
                title,
                message,
                channel,
                status,
                priority,
                scheduled_at,
                sent_at
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            """,
            (
                patient_id,
                admission_id,
                incident_id,
                recipient_type,
                str(
                    rng.randint(
                        1,
                        100,
                    )
                ),
                notification_type,
                rng.choice(titles),
                mock_note(
                    f"Notification scenario {index + 1}"
                ),
                channel,
                status,
                priority,
                scheduled_at,
                sent_at,
            ),
        )

    print(
        f"  Created {NUM_NOTIFICATIONS} notifications."
    )


# ============================================================
# 10. RESOURCE / INVENTORY ENRICHMENT
# ============================================================

def enrich_inventory(
    cursor,
    resources,
):

    print("\n[10/10] Enriching inventory/resources...")

    # --------------------------------------------------------
    # General inventory
    # --------------------------------------------------------

    inventory_items = [
        ("PPE", "Nitrile Examination Gloves"),
        ("PPE", "Surgical Masks"),
        ("PPE", "N95 Respirators"),
        ("SURGICAL", "Surgical Sutures"),
        ("SURGICAL", "Sterile Surgical Drapes"),
        ("LAB", "Blood Collection Tubes"),
        ("LAB", "Urine Collection Containers"),
        ("NURSING", "IV Cannula"),
        ("NURSING", "IV Giving Set"),
        ("EMERGENCY", "Emergency Oxygen Mask"),
        ("EMERGENCY", "Trauma Dressing Kit"),
        ("CLEANING", "Disinfectant Solution"),
        ("OFFICE", "Patient Forms"),
        ("OTHER", "Disposable Bed Sheets"),
    ]

    hospital_id = 1

    existing_codes = {
        row["item_code"]
        for row in resources["inventory"]
    }

    added_inventory = 0

    for index, (category, item_name) in enumerate(
        inventory_items,
        start=1,
    ):

        item_code = f"MOCK-INV-{index:03d}"

        if item_code in existing_codes:
            continue

        quantity = rng.randint(
            0,
            500,
        )

        reorder_level = rng.choice(
            [10, 20, 30, 50]
        )

        if quantity == 0:
            status = "OUT_OF_STOCK"

        elif quantity <= reorder_level:
            status = "LOW_STOCK"

        else:
            status = "AVAILABLE"

        cursor.execute(
            """
            INSERT INTO inventory (
                hospital_id,
                item_code,
                item_name,
                category,
                unit,
                quantity_on_hand,
                reorder_level,
                reorder_quantity,
                unit_cost,
                storage_location,
                expiry_date,
                status
            )
            VALUES (
                %s, %s, %s, %s,
                'unit', %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                hospital_id,
                item_code,
                item_name,
                category,
                quantity,
                reorder_level,
                rng.randint(50, 300),
                round(
                    rng.uniform(
                        1,
                        500,
                    ),
                    2,
                ),
                f"Storage-{rng.randint(1, 10)}",
                (
                    date.today()
                    + timedelta(
                        days=rng.randint(
                            30,
                            720,
                        )
                    )
                ),
                status,
            ),
        )

        added_inventory += 1

    # --------------------------------------------------------
    # Medication inventory scenarios
    # --------------------------------------------------------

    # We intentionally modify only a subset of existing
    # medication inventory records so that different stock
    # states exist for PharmacyAgent testing.

    medication_rows = fetch_all(
        cursor,
        """
        SELECT
            medication_inventory_id,
            quantity_on_hand,
            reorder_level,
            status
        FROM medication_inventory
        ORDER BY medication_inventory_id
        """,
    )

    for index, medication in enumerate(
        medication_rows
    ):

        if index % 5 == 0:

            quantity = 0

            cursor.execute(
                """
                UPDATE medication_inventory
                SET
                    quantity_on_hand = %s,
                    status = 'OUT_OF_STOCK'
                WHERE medication_inventory_id = %s
                """,
                (
                    quantity,
                    medication[
                        "medication_inventory_id"
                    ],
                ),
            )

        elif index % 5 == 1:

            quantity = max(
                1,
                medication["reorder_level"] // 2,
            )

            cursor.execute(
                """
                UPDATE medication_inventory
                SET
                    quantity_on_hand = %s,
                    status = 'LOW_STOCK'
                WHERE medication_inventory_id = %s
                """,
                (
                    quantity,
                    medication[
                        "medication_inventory_id"
                    ],
                ),
            )

    print(
        f"  Added {added_inventory} inventory items."
    )

    print(
        "  Created varied medication stock states."
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_seed(
    cursor,
    before_counts: dict[str, int],
):

    print("\n==================================================")
    print("POST-SEED VALIDATION")
    print("==================================================")

    tables = [
        "admissions",
        "emergency_incidents",
        "appointments",
        "lab_orders",
        "lab_results",
        "medication_requests",
        "patient_transfers",
        "ambulance_dispatches",
        "hospital_events",
        "notifications",
    ]

    after_counts: dict[str, int] = {}

    for table in tables:

        cursor.execute(
            f"SELECT COUNT(*) AS count FROM {table}"
        )

        count = int(
            cursor.fetchone()["count"]
        )

        after_counts[table] = count

        before = before_counts.get(
            table,
            0,
        )

        print(
            f"{table:<25} "
            f"before={before:<6} "
            f"after={count:<6} "
            f"added={count - before}"
        )

    # --------------------------------------------------------
    # FK consistency checks
    # --------------------------------------------------------

    checks = {

        "orphan admissions": """
            SELECT COUNT(*) AS count
            FROM admissions a
            LEFT JOIN patients p
                ON p.ID = a.patient_id
            WHERE p.ID IS NULL
        """,

        "orphan emergency incidents": """
            SELECT COUNT(*) AS count
            FROM emergency_incidents e
            LEFT JOIN patients p
                ON p.ID = e.patient_id
            WHERE p.ID IS NULL
        """,

        "orphan lab orders": """
            SELECT COUNT(*) AS count
            FROM lab_orders l
            LEFT JOIN patients p
                ON p.ID = l.patient_id
            WHERE p.ID IS NULL
        """,

        "orphan lab results": """
            SELECT COUNT(*) AS count
            FROM lab_results r
            LEFT JOIN lab_orders l
                ON l.lab_order_id = r.lab_order_id
            WHERE l.lab_order_id IS NULL
        """,

        "orphan medication requests": """
            SELECT COUNT(*) AS count
            FROM medication_requests m
            LEFT JOIN medication_inventory mi
                ON mi.medication_inventory_id =
                   m.medication_inventory_id
            WHERE mi.medication_inventory_id IS NULL
        """,

        "orphan transfers": """
            SELECT COUNT(*) AS count
            FROM patient_transfers t
            LEFT JOIN admissions a
                ON a.admission_id = t.admission_id
            WHERE a.admission_id IS NULL
        """,

        "orphan dispatches": """
            SELECT COUNT(*) AS count
            FROM ambulance_dispatches d
            LEFT JOIN emergency_incidents e
                ON e.incident_id = d.incident_id
            WHERE e.incident_id IS NULL
        """,
    }

    print("\nForeign-key validation:")

    for name, query in checks.items():

        cursor.execute(query)

        count = int(
            cursor.fetchone()["count"]
        )

        if count == 0:
            print(
                f"  PASS  {name}"
            )
        else:
            print(
                f"  FAIL  {name}: {count}"
            )

    # --------------------------------------------------------
    # Useful scenario distributions
    # --------------------------------------------------------

    print("\nEmergency distribution:")

    cursor.execute(
        """
        SELECT
            severity,
            status,
            COUNT(*) AS count
        FROM emergency_incidents
        WHERE triage_notes LIKE 'MOCK_DATA%'
        GROUP BY severity, status
        ORDER BY severity, status
        """
    )

    for row in cursor.fetchall():

        print(
            f"  {row['severity']:<10} "
            f"{row['status']:<22} "
            f"{row['count']}"
        )

    print("\nLab result distribution:")

    cursor.execute(
        """
        SELECT
            result_status,
            COUNT(*) AS count
        FROM lab_results r
        INNER JOIN lab_orders l
            ON l.lab_order_id = r.lab_order_id
        WHERE l.clinical_notes LIKE 'MOCK_DATA%'
        GROUP BY result_status
        ORDER BY result_status
        """
    )

    for row in cursor.fetchall():

        print(
            f"  {row['result_status']:<12} "
            f"{row['count']}"
        )

    print("\nMedication request distribution:")

    cursor.execute(
        """
        SELECT
            status,
            priority,
            COUNT(*) AS count
        FROM medication_requests
        WHERE notes LIKE 'MOCK_DATA%'
        GROUP BY status, priority
        ORDER BY status, priority
        """
    )

    for row in cursor.fetchall():

        print(
            f"  {row['status']:<15} "
            f"{row['priority']:<10} "
            f"{row['count']}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("==================================================")
    print("HOSPITAL AI MOCK DATA SEEDER")
    print("==================================================")
    print(f"Random seed: {RANDOM_SEED}")

    try:

        # get_db_connection() is a context manager.
        # Keep the complete seed operation inside the context.
        with get_db_connection() as connection:

            cursor = connection.cursor(
                dictionary=True
            )

            try:

                # ----------------------------------------------------
                # Existing counts
                # ----------------------------------------------------

                tables = [
                    "admissions",
                    "emergency_incidents",
                    "appointments",
                    "lab_orders",
                    "lab_results",
                    "medication_requests",
                    "patient_transfers",
                    "ambulance_dispatches",
                    "hospital_events",
                    "notifications",
                ]

                before_counts: dict[str, int] = {}

                print("\nExisting row counts:")

                for table in tables:

                    cursor.execute(
                        f"SELECT COUNT(*) AS count FROM {table}"
                    )

                    count = int(
                        cursor.fetchone()["count"]
                    )

                    before_counts[table] = count

                    print(
                        f"  {table:<25} {count}"
                    )

                # ----------------------------------------------------
                # Load reference data
                # ----------------------------------------------------

                resources = load_reference_data(
                    cursor
                )

                # ----------------------------------------------------
                # Start transaction
                # ----------------------------------------------------

                print("\nUsing active database transaction...")

                # ----------------------------------------------------
                # Seed in FK-safe order
                # ----------------------------------------------------

                admission_ids = seed_admissions(
                    cursor,
                    resources,
                )

                incident_ids = seed_emergency_incidents(
                    cursor,
                    resources,
                    admission_ids,
                )

                seed_appointments(
                    cursor,
                    resources,
                )

                seed_lab_orders_and_results(
                    cursor,
                    resources,
                )

                seed_medication_requests(
                    cursor,
                    resources,
                    admission_ids,
                )

                seed_patient_transfers(
                    cursor,
                    resources,
                    admission_ids,
                )

                seed_ambulance_dispatches(
                    cursor,
                    resources,
                    incident_ids,
                )

                seed_hospital_events(
                    cursor,
                    resources,
                    admission_ids,
                    incident_ids,
                )

                seed_notifications(
                    cursor,
                    resources,
                    admission_ids,
                    incident_ids,
                )

                enrich_inventory(
                    cursor,
                    resources,
                )

                # ----------------------------------------------------
                # Validate before commit
                # ----------------------------------------------------

                validate_seed(
                    cursor,
                    before_counts,
                )

                # ----------------------------------------------------
                # Commit
                # ----------------------------------------------------

                connection.commit()

                print("\n==================================================")
                print("MOCK DATA SEED COMPLETED SUCCESSFULLY")
                print("==================================================")

                print(
                    "\nExisting agent history was NOT fabricated."
                )

                print(
                    "agent_actions, audit_logs and "
                    "action_gateway_requests remain available "
                    "for real agent execution history."
                )

            except Exception:

                try:
                    connection.rollback()
                    print("\nTransaction rolled back.")
                except Exception as rollback_error:
                    print(
                        f"\nRollback failed: {rollback_error}"
                    )

                raise

            finally:

                try:
                    cursor.close()
                except Exception:
                    pass

    except Exception as exc:

        print("\n==================================================")
        print("SEED FAILED")
        print("==================================================")

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise


if __name__ == "__main__":
    main()