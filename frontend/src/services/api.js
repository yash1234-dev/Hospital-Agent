const API_BASE_URL = "http://127.0.0.1:8000"

export async function runEmergencyTriage(incidentId) {
  const response = await fetch(
    `${API_BASE_URL}/api/emergency/triage`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        incident_id: Number(incidentId),
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Emergency workflow failed."
    )
  }

  return data
}


export async function getDashboardMetrics() {
  const response = await fetch(
    `${API_BASE_URL}/api/dashboard/metrics`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load dashboard metrics."
    )
  }

  return data
}


export async function getSystemHealth() {
  const response = await fetch(
    `${API_BASE_URL}/api/health/system`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load system health."
    )
  }

  return data
}


export async function getActiveEmergencyCases() {
  const response = await fetch(
    `${API_BASE_URL}/api/dashboard/emergency-cases`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load emergency cases."
    )
  }

  return data
}


// =========================================================
// BED MANAGEMENT - AVAILABLE BEDS
// =========================================================

export const getAvailableBeds = async ({
  bedType = "",
  roomType = "",
  departmentId = "",
} = {}) => {

  const params = new URLSearchParams()

  if (bedType) {
    params.append("bed_type", bedType)
  }

  if (roomType) {
    params.append("room_type", roomType)
  }

  if (departmentId) {
    params.append("department_id", departmentId)
  }

  const queryString = params.toString()

  const response = await fetch(
    `${API_BASE_URL}/api/beds/available${
      queryString ? `?${queryString}` : ""
    }`
  )

  if (!response.ok) {
    throw new Error("Failed to fetch available beds")
  }

  return response.json()
}


// =========================================================
// BED MANAGEMENT - ELIGIBLE ADMISSIONS
// =========================================================

export async function getEligibleAdmissions() {

  const response = await fetch(
    `${API_BASE_URL}/api/beds/eligible-admissions`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load eligible admissions."
    )
  }

  return data
}


// =========================================================
// BED MANAGEMENT - RESERVE BED
// =========================================================

export async function reserveBed({
  bedId,
  patientId,
  admissionId,
}) {

  const response = await fetch(
    `${API_BASE_URL}/api/beds/reserve`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        bed_id: Number(bedId),
        patient_id: patientId,
        admission_id: Number(admissionId),
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to reserve bed."
    )
  }

  return data
}


// =========================================================
// STAFF MANAGEMENT - AVAILABLE DOCTORS
// =========================================================

export async function getAvailableDoctors({
  scheduleDate = "",
  departmentId = "",
  speciality = "",
  shiftType = "",
} = {}) {

  const params = new URLSearchParams()

  if (scheduleDate) {
    params.append("schedule_date", scheduleDate)
  }

  if (departmentId) {
    params.append("department_id", departmentId)
  }

  if (speciality) {
    params.append("speciality", speciality)
  }

  if (shiftType) {
    params.append("shift_type", shiftType)
  }

  const queryString = params.toString()

  const response = await fetch(
    `${API_BASE_URL}/api/staff/doctors/available${
      queryString ? `?${queryString}` : ""
    }`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load available doctors."
    )
  }

  return data
}


// =========================================================
// STAFF MANAGEMENT - AVAILABLE NURSES
// =========================================================

export async function getAvailableNurses({
  scheduleDate = "",
  departmentId = "",
  shiftType = "",
} = {}) {

  const params = new URLSearchParams()

  if (scheduleDate) {
    params.append("schedule_date", scheduleDate)
  }

  if (departmentId) {
    params.append("department_id", departmentId)
  }

  if (shiftType) {
    params.append("shift_type", shiftType)
  }

  const queryString = params.toString()

  const response = await fetch(
    `${API_BASE_URL}/api/staff/nurses/available${
      queryString ? `?${queryString}` : ""
    }`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load available nurses."
    )
  }

  return data
}


// =========================================================
// STAFF MANAGEMENT - UNASSIGNED ADMISSIONS
// =========================================================

export async function getUnassignedAdmissions() {

  const response = await fetch(
    `${API_BASE_URL}/api/staff/unassigned-admissions`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load unassigned admissions."
    )
  }

  return data
}


// =========================================================
// STAFF MANAGEMENT - ASSIGN DOCTOR
// =========================================================

export async function assignDoctor(
  admissionId,
  doctorId
) {

  const response = await fetch(
    `${API_BASE_URL}/api/staff/doctors/assign`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        admission_id: Number(admissionId),
        doctor_id: Number(doctorId),
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {

    const error = new Error(
      data.detail ||
      data.message ||
      "Failed to assign doctor."
    )

    error.status = response.status
    error.data = data

    throw error
  }

  return data
}


// =========================================================
// STAFF MANAGEMENT - ASSIGN NURSE
// =========================================================

export async function assignNurse(
  admissionId,
  nurseId
) {

  const response = await fetch(
    `${API_BASE_URL}/api/staff/nurses/assign`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        admission_id: Number(admissionId),
        nurse_id: Number(nurseId),
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {

    const error = new Error(
      data.detail ||
      data.message ||
      "Failed to assign nurse."
    )

    error.status = response.status
    error.data = data

    throw error
  }

  return data
}


// =========================================================
// LAB / DIAGNOSTICS - GET LAB ORDER
// =========================================================

export async function getLabOrder(labOrderId) {

  const response = await fetch(
    `${API_BASE_URL}/api/labs/orders/${Number(labOrderId)}`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load lab order."
    )
  }

  /*
   * Backend returns:
   *
   * {
   *   status: "SUCCESS",
   *   lab_order: {
   *      lab_order_id: 3,
   *      patient_id: "...",
   *      doctor_id: 81,
   *      department_id: 3,
   *      ...
   *   }
   * }
   *
   * Diagnostics page needs the actual lab_order object.
   */

  return data.lab_order || data
}


// =========================================================
// LAB / DIAGNOSTICS - GET LAB RESULTS
// =========================================================

export async function getLabResults(labOrderId) {

  const response = await fetch(
    `${API_BASE_URL}/api/labs/orders/${Number(labOrderId)}/results`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load laboratory results."
    )
  }

  return data
}


// =========================================================
// LAB / DIAGNOSTICS - RUN LAB AGENT
// =========================================================

export async function runLabAgent({
  labOrderId,
  patientId = null,
  admissionId = null,
  departmentId = null,
}) {

  const response = await fetch(
    `${API_BASE_URL}/api/labs/orders/${Number(labOrderId)}/run`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,

        admission_id:
          admissionId === null || admissionId === ""
            ? null
            : Number(admissionId),

        department_id:
          departmentId === null || departmentId === ""
            ? null
            : Number(departmentId),
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Lab agent workflow failed."
    )
  }

  return data
}


// =========================================================
// LAB / DIAGNOSTICS - UPDATE LAB ORDER STATUS
// =========================================================

export async function updateLabOrderStatus({
  labOrderId,
  newStatus,
}) {

  const response = await fetch(
    `${API_BASE_URL}/api/labs/orders/${Number(labOrderId)}/status`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        new_status: newStatus,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to update lab order status."
    )
  }

  return data
}


// =========================================================
// LAB / DIAGNOSTICS - RECORD LAB RESULT
// =========================================================

export async function recordLabResult({
  labOrderId,
  patientId,
  testName,
  resultValue = null,
  numericValue = null,
  unit = null,
  referenceRange = null,
  resultStatus,
  performedAt = null,
  verifiedByDoctorId = null,
  interpretation = null,
}) {

  const response = await fetch(
    `${API_BASE_URL}/api/labs/orders/${Number(labOrderId)}/result`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,

        test_name: testName,

        result_value: resultValue,

        numeric_value:
          numericValue === null || numericValue === ""
            ? null
            : Number(numericValue),

        unit,

        reference_range: referenceRange,

        result_status: resultStatus,

        performed_at: performedAt,

        verified_by_doctor_id:
          verifiedByDoctorId === null ||
          verifiedByDoctorId === ""
            ? null
            : Number(verifiedByDoctorId),

        interpretation,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to record laboratory result."
    )
  }

  return data
}

// =========================================================
// PHARMACY - MEDICATION INVENTORY
// =========================================================

export async function getMedications({
  medicationName = "",
  medicationCode = "",
  status = "",
  category = "",
  limit = 50,
} = {}) {
  const params = new URLSearchParams()

  if (medicationName) {
    params.append("medication_name", medicationName)
  }

  if (medicationCode) {
    params.append("medication_code", medicationCode)
  }

  if (status) {
    params.append("status", status)
  }

  if (category) {
    params.append("category", category)
  }

  params.append("limit", Number(limit))

  const response = await fetch(
    `${API_BASE_URL}/api/pharmacy/medications?${params.toString()}`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load medication inventory."
    )
  }

  return data
}


// =========================================================
// PHARMACY - SINGLE MEDICATION
// =========================================================

export async function getMedication(medicationInventoryId) {
  const response = await fetch(
    `${API_BASE_URL}/api/pharmacy/medications/${Number(
      medicationInventoryId
    )}`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load medication."
    )
  }

  return data
}


// =========================================================
// PHARMACY - PENDING REQUESTS
// =========================================================

export async function getMedicationRequests({
  priority = "",
  limit = 50,
} = {}) {
  const params = new URLSearchParams()

  if (priority) {
    params.append("priority", priority)
  }

  params.append("limit", Number(limit))

  const response = await fetch(
    `${API_BASE_URL}/api/pharmacy/requests?${params.toString()}`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load medication requests."
    )
  }

  return data
}


// =========================================================
// PHARMACY - SINGLE REQUEST
// =========================================================

export async function getMedicationRequest(requestId) {
  const response = await fetch(
    `${API_BASE_URL}/api/pharmacy/requests/${Number(requestId)}`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load medication request."
    )
  }

  return data
}


// =========================================================
// PHARMACY - PROCESS REQUEST WITH AI AGENT
// =========================================================

export async function processMedicationRequest(requestId) {
  const response = await fetch(
    `${API_BASE_URL}/api/pharmacy/requests/${Number(
      requestId
    )}/process`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  )

  const data = await response.json()

  if (!response.ok) {
    const error = new Error(
      data.detail ||
      data.message ||
      "Failed to process medication request."
    )

    error.status = response.status
    error.data = data

    throw error
  }

  return data
}
// =========================================================
// ADMISSION MANAGEMENT
// =========================================================

export async function getAdmissions({
  limit = 100,
  offset = 0,
  status = "",
  patientId = "",
} = {}) {
  const params = new URLSearchParams()

  params.append("limit", Number(limit))
  params.append("offset", Number(offset))

  if (status) {
    params.append("status", status)
  }

  if (patientId) {
    params.append("patient_id", patientId)
  }

  const response = await fetch(
    `${API_BASE_URL}/api/admissions?${params.toString()}`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load admissions."
    )
  }

  return data
}

export async function getAdmission(admissionId) {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions/${Number(admissionId)}`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load admission."
    )
  }

  return data
}

export async function getActivePatientAdmission(patientId) {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions/patient/${patientId}/active`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load active admission."
    )
  }

  return data
}

export async function createAdmission({
  patientId,
  departmentId,
  admissionType,
  encounterId = null,
  expectedDischargeTime = null,
  diagnosis = "",
  notes = "",
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,
        department_id: Number(departmentId),
        admission_type: admissionType,
        encounter_id: encounterId,
        expected_discharge_time: expectedDischargeTime,
        diagnosis,
        notes,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to create admission."
    )
  }

  return data
}

export async function processAdmission({
  patientId,
  departmentId,
  admissionType,
  admissionId = null,
  encounterId = null,
  expectedDischargeTime = null,
  diagnosis = "",
  notes = "",
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions/process`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,
        department_id: Number(departmentId),
        admission_type: admissionType,
        admission_id: admissionId
          ? Number(admissionId)
          : null,
        encounter_id: encounterId,
        expected_discharge_time: expectedDischargeTime,
        diagnosis,
        notes,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Admission AI workflow failed."
    )
  }

  return data
}

export async function updateAdmissionStatus(
  admissionId,
  newStatus
) {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions/${Number(admissionId)}/status`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        new_status: newStatus,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to update admission status."
    )
  }

  return data
}

export async function dischargeAdmission(
  admissionId,
  notes = ""
) {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions/${Number(admissionId)}/discharge`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        notes,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to discharge admission."
    )
  }

  return data
}

export async function cancelAdmission(
  admissionId,
  notes = ""
) {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions/${Number(admissionId)}/cancel`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        notes,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to cancel admission."
    )
  }

  return data
}
export async function getUnadmittedPatients() {
  const response = await fetch(
    `${API_BASE_URL}/api/admissions/unadmitted-patients`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail || "Failed to load unadmitted patients."
    )
  }

  return data
}
// =========================================================
// NOTIFICATIONS - SEND EMAIL
// =========================================================

export async function sendNotification({
  eventType,
  priority = "NORMAL",
  patientId = null,
  admissionId = null,
  incidentId = null,
  title,
  message,
  recipientEmail,
  sourceAgent,
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/notifications/send`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        event_type: eventType,
        priority,
        patient_id: patientId,
        admission_id:
          admissionId === null || admissionId === ""
            ? null
            : Number(admissionId),
        incident_id:
          incidentId === null || incidentId === ""
            ? null
            : Number(incidentId),
        title,
        message,
        recipient_email: recipientEmail,
        source_agent: sourceAgent,
      }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail?.error ||
      data.detail ||
      "Failed to send notification email."
    )
  }

  return data
}