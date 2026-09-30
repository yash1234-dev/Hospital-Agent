import { useEffect, useMemo, useState } from "react"
import NotificationButton from "../components/NotificationButton"
import Sidebar from "../components/Sidebar"
import Header from "../components/Header"

import {
  getAdmissions,
  getAdmission,
  getUnadmittedPatients,
  processAdmission,
  dischargeAdmission,
  cancelAdmission,
} from "../services/api"


function Admission() {

  // =========================================================
  // STATE
  // =========================================================

  const [patients, setPatients] = useState([])
  const [admissions, setAdmissions] = useState([])
  const [departments, setDepartments] = useState([])
  const [clinicalSummary, setClinicalSummary] = useState(null)
  const [clinicalLoading, setClinicalLoading] = useState(false)
  const [recommendationSource, setRecommendationSource] =
    useState("")

  const [selectedAdmission, setSelectedAdmission] = useState(null)

  const [patientId, setPatientId] = useState("")
  const [departmentId, setDepartmentId] = useState("")
  const [admissionType, setAdmissionType] =
    useState("")

  const [diagnosis, setDiagnosis] = useState("")
  const [notes, setNotes] = useState("")

  const [workflowResult, setWorkflowResult] = useState(null)

  const [loadingPatients, setLoadingPatients] =
    useState(false)

  const [loadingAdmissions, setLoadingAdmissions] =
    useState(false)

  const [runningAgent, setRunningAgent] =
    useState(false)

  const [error, setError] = useState("")

  const [searchTerm, setSearchTerm] = useState("")

  const [toast, setToast] = useState(null)


  // =========================================================
  // LOAD DATA
  // =========================================================

  const loadPatients = async () => {

    setLoadingPatients(true)

    try {

      const data = await getUnadmittedPatients()

      setPatients(data.patients || [])

    } catch (err) {

      setError(
        err.message ||
        "Failed to load unadmitted patients."
      )

    } finally {

      setLoadingPatients(false)

    }
  }


  const loadAdmissions = async () => {

    setLoadingAdmissions(true)

    try {

      const data = await getAdmissions({
        limit: 100,
        offset: 0,
      })

      const rows =
        Array.isArray(data)
          ? data
          : data.admissions || []

      setAdmissions(rows)

      if (
        selectedAdmission &&
        selectedAdmission.admission_id
      ) {

        const refreshed =
          rows.find(
            (item) =>
              Number(item.admission_id) ===
              Number(selectedAdmission.admission_id)
          )

        if (refreshed) {
          setSelectedAdmission(refreshed)
        }
      }

    } catch (err) {

      setError(
        err.message ||
        "Failed to load admissions."
      )

    } finally {

      setLoadingAdmissions(false)

    }
  }


  const loadDepartments = async () => {
    try {
      const response = await fetch(
       "https://hospital-agent-production-e949.up.railway.app/api/admissions/departments"
      )
      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to load departments."
        )
      }

      setDepartments(data.departments || [])
    } catch (err) {
      setError(
        err.message ||
        "Failed to load departments."
      )
    }
  }


  const loadClinicalSummary = async (id) => {
    if (!id) {
      setClinicalSummary(null)
      return
    }

    setClinicalLoading(true)

    try {
      const response = await fetch(
        `https://hospital-agent-production-e949.up.railway.app/api/admissions/patient/${id}/clinical-summary`
      )
      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Failed to load patient clinical information."
        )
      }

      setClinicalSummary(data)
    } catch (err) {
      setClinicalSummary(null)
      setError(
        err.message ||
        "Failed to load patient clinical information."
      )
    } finally {
      setClinicalLoading(false)
    }
  }


  useEffect(() => {

    loadPatients()
    loadAdmissions()
    loadDepartments()

  }, [])


  useEffect(() => {
    if (patientId) {
      loadClinicalSummary(patientId)
    } else {
      setClinicalSummary(null)
    }
  }, [patientId])


  const clinicalData =
    clinicalSummary?.clinical_summary || {}

  const conditions =
    clinicalData.conditions || []

  const encounters =
    clinicalData.recent_encounters || []

  const observations =
    clinicalData.recent_observations || []


  const suggestedDiagnosis =
    conditions[0]?.description ||
    encounters[0]?.reason_description ||
    encounters[0]?.description ||
    ""


  const suggestedAdmissionType = useMemo(() => {
    if (!clinicalSummary) return ""

    const text = [
      ...conditions.map(
        (item) => item.description || ""
      ),
      ...encounters.map(
        (item) =>
          `${item.description || ""} ${
            item.reason_description || ""
          }`
      ),
    ]
      .join(" ")
      .toLowerCase()

    const emergencyKeywords = [
      "emergency",
      "acute",
      "severe",
      "critical",
      "trauma",
      "accident",
      "stroke",
      "myocardial",
      "heart attack",
      "respiratory failure",
      "sepsis",
    ]

    const transferKeywords = [
      "transfer",
      "transferred",
      "referral",
    ]

    const electiveKeywords = [
      "elective",
      "scheduled",
      "planned",
      "procedure",
      "surgery",
    ]

    if (
      emergencyKeywords.some(
        (keyword) => text.includes(keyword)
      )
    ) {
      return "EMERGENCY"
    }

    if (
      transferKeywords.some(
        (keyword) => text.includes(keyword)
      )
    ) {
      return "TRANSFER"
    }

    if (
      electiveKeywords.some(
        (keyword) => text.includes(keyword)
      )
    ) {
      return "ELECTIVE"
    }

    if (
      conditions.length > 0 ||
      encounters.length > 0 ||
      observations.length > 0
    ) {
      return "OBSERVATION"
    }

    return ""
  }, [
    clinicalSummary,
    conditions,
    encounters,
    observations,
  ])


  const suggestedDepartment = useMemo(() => {
    if (!departments.length) return null

    const text = [
      ...conditions.map(
        (item) => item.description || ""
      ),
      ...encounters.map(
        (item) =>
          `${item.description || ""} ${
            item.reason_description || ""
          }`
      ),
    ]
      .join(" ")
      .toLowerCase()

    const rules = [
      [["cardiac", "cardiology", "coronary", "arrhythmia"], "cardiology"],
      [["neurolog", "seizure", "epilepsy", "stroke"], "neurology"],
      [["cancer", "tumor", "malignant", "oncolog"], "oncology"],
      [["fracture", "bone", "joint", "orthopedic"], "orthopedic"],
      [["respiratory", "lung", "pneumonia", "asthma", "copd"], "pulmon"],
      [["kidney", "renal", "nephro"], "nephro"],
      [["gastro", "stomach", "intestinal", "liver"], "gastro"],
      [["diabetes", "diabetic", "endocrine"], "endocrine"],
    ]

    for (const [keywords, departmentKeyword] of rules) {
      if (
        keywords.some((keyword) =>
          text.includes(keyword)
        )
      ) {
        const match = departments.find(
          (department) =>
            String(
              department.department_name || ""
            )
              .toLowerCase()
              .includes(departmentKeyword)
        )

        if (match) return match
      }
    }

    return (
      departments.find((department) =>
        String(
          department.department_name || ""
        )
          .toLowerCase()
          .includes("general medicine")
      ) || null
    )
  }, [departments, conditions, encounters])


  useEffect(() => {
    if (!clinicalSummary) return

    if (suggestedDepartment) {
      setDepartmentId(
        String(suggestedDepartment.department_id)
      )
    }

    if (suggestedDiagnosis) {
      setDiagnosis(suggestedDiagnosis)
    }

    if (suggestedAdmissionType) {
      setAdmissionType(suggestedAdmissionType)
      setRecommendationSource(
        "Based on the patient's available clinical record."
      )
    }
  }, [
    clinicalSummary,
    suggestedDepartment,
    suggestedDiagnosis,
    suggestedAdmissionType,
  ])


  // =========================================================
  // RUN AI ADMISSION WORKFLOW
  // =========================================================

  const handleRunWorkflow = async () => {

    if (!patientId) {
      setError("Please select a patient.")
      return
    }

    if (!departmentId) {
      setError("Please select a department.")
      return
    }

    setRunningAgent(true)
    setError("")
    setWorkflowResult(null)

    try {

      const result = await processAdmission({

        patientId,
        departmentId: Number(departmentId),
        admissionType,
        diagnosis:
          diagnosis.trim() || null,
        notes:
          notes.trim() || null,
      })

      setWorkflowResult(result)

      // Refresh both lists because
      // selected patient may now have an active admission.
      await Promise.all([
        loadPatients(),
        loadAdmissions(),
      ])

      // Clear form after successful workflow
      if (result.status === "SUCCESS") {
        setPatientId("")
        setDiagnosis("")
        setNotes("")
      }

    } catch (err) {

      setError(
        err.message ||
        "Admission AI workflow failed."
      )

    } finally {

      setRunningAgent(false)

    }
  }


  // =========================================================
  // SELECT ADMISSION
  // =========================================================

  const handleSelectAdmission = async (admission) => {

    try {

      const data = await getAdmission(
        admission.admission_id
      )

      setSelectedAdmission(
        data.admission || data
      )

    } catch (err) {

      setSelectedAdmission(admission)

      setError(
        err.message ||
        "Failed to load admission details."
      )
    }
  }


  // =========================================================
  // DISCHARGE
  // =========================================================

  const handleDischarge = async () => {

    if (!selectedAdmission) {
      return
    }

    const confirmed = window.confirm(
      `Discharge admission ${selectedAdmission.admission_id}?`
    )

    if (!confirmed) {
      return
    }

    try {

      setError("")

      await dischargeAdmission(
        selectedAdmission.admission_id,
        "Discharged from Admission Management."
      )

      await loadAdmissions()
      await loadPatients()

      const refreshed =
        await getAdmission(
          selectedAdmission.admission_id
        )

      setSelectedAdmission(
        refreshed.admission || refreshed
      )

      showToast(
        "success",
        "Admission Discharged",
        `Admission #${selectedAdmission.admission_id} has been discharged successfully.`
      )

    } catch (err) {

      setError(
        err.message ||
        "Failed to discharge admission."
      )

      showToast(
        "error",
        "Discharge Failed",
        err.message ||
        "Failed to discharge admission."
      )

    }
  }


  // =========================================================
  // CANCEL
  // =========================================================

  const handleCancel = async () => {

    if (!selectedAdmission) {
      return
    }

    const confirmed = window.confirm(
      `Cancel admission ${selectedAdmission.admission_id}?`
    )

    if (!confirmed) {
      return
    }

    try {

      setError("")

      await cancelAdmission(
        selectedAdmission.admission_id,
        "Cancelled from Admission Management."
      )

      await loadAdmissions()
      await loadPatients()

      const refreshed =
        await getAdmission(
          selectedAdmission.admission_id
        )

      setSelectedAdmission(
        refreshed.admission || refreshed
      )

      showToast(
        "success",
        "Admission Cancelled",
        `Admission #${selectedAdmission.admission_id} has been cancelled successfully.`
      )

    } catch (err) {

      setError(
        err.message ||
        "Failed to cancel admission."
      )

      showToast(
        "error",
        "Cancellation Failed",
        err.message ||
        "Failed to cancel admission."
      )

    }
  }


  // =========================================================
  // UI HELPERS
  // =========================================================

  const showToast = (type, title, message) => {
    setToast({
      type,
      title,
      message,
    })

    window.setTimeout(() => {
      setToast(null)
    }, 3500)
  }


  const getDepartmentName = (departmentId) => {
    return (
      departments.find(
        (department) =>
          Number(department.department_id) ===
          Number(departmentId)
      )?.department_name ||
      `Department ${departmentId ?? "N/A"}`
    )
  }


  const filteredAdmissions = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()

    if (!query) {
      return admissions
    }

    return admissions.filter((admission) => {
      const departmentName =
        getDepartmentName(admission.department_id)

      return [
        admission.admission_id,
        admission.patient_id,
        admission.admission_type,
        admission.status,
        admission.diagnosis,
        departmentName,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value)
            .toLowerCase()
            .includes(query)
        )
    })
  }, [admissions, departments, searchTerm])


  // =========================================================
  // KPI DATA
  // =========================================================

  const totalAdmissions =
    admissions.length

  const activeAdmissions =
    admissions.filter(
      (item) =>
        item.status === "ADMITTED"
    ).length

  const observationAdmissions =
    admissions.filter(
      (item) =>
        item.status === "OBSERVATION"
    ).length

  const dischargedAdmissions =
    admissions.filter(
      (item) =>
        item.status === "DISCHARGED"
    ).length


  // =========================================================
  // UI
  // =========================================================

  return (

    <div className="min-h-screen bg-slate-100 flex">

      <Sidebar />

      <div className="min-w-0 flex-1">

        <Header />

        {toast && (
          <Toast
            toast={toast}
            onClose={() => setToast(null)}
          />
        )}

        <main className="p-6 lg:p-8 space-y-6">


          {/* =================================================
              PAGE HEADER
          ================================================= */}

          <div>

            <div className="flex items-center gap-3">

              <div className="
                w-11 h-11
                rounded-xl
                bg-blue-100
                flex
                items-center
                justify-center
                text-xl
              ">
                🏥
              </div>

              <div>

                <h1 className="
                  text-2xl
                  font-bold
                  text-slate-800
                ">
                  Patient Admissions
                </h1>

                <p className="
                  text-sm
                  text-slate-500
                  mt-1
                ">
                  Manage admissions through
                  AI-powered hospital orchestration.
                </p>

              </div>

            </div>

          </div>


          {/* =================================================
              ERROR
          ================================================= */}

          {error && (

            <div className="
              p-4
              rounded-xl
              bg-red-50
              border
              border-red-200
              text-sm
              text-red-700
            ">

              {error}

            </div>

          )}


          {/* =================================================
              KPI
          ================================================= */}

          <div className="
            grid
            grid-cols-1
            sm:grid-cols-2
            lg:grid-cols-4
            gap-4
          ">

            <KpiCard
              label="Total Admissions"
              value={totalAdmissions}
              icon="🏥"
            />

            <KpiCard
              label="Active Admissions"
              value={activeAdmissions}
              icon="🟢"
            />

            <KpiCard
              label="Observation"
              value={observationAdmissions}
              icon="👁️"
            />

            <KpiCard
              label="Discharged"
              value={dischargedAdmissions}
              icon="✓"
            />

          </div>


          {/* =================================================
              AI ADMISSION AGENT
              NOW AT TOP
          ================================================= */}

          <section className="
            bg-white
            rounded-2xl
            border
            border-slate-200
            shadow-sm
            overflow-hidden
          ">

            {/* Agent Header */}

            <div className="
              px-6
              py-5
              border-b
              border-slate-200
              bg-slate-50
            ">

              <div className="
                flex
                items-center
                gap-4
              ">

                <div className="
                  w-12 h-12
                  rounded-xl
                  bg-blue-100
                  flex
                  items-center
                  justify-center
                  text-2xl
                ">
                  🤖
                </div>

                <div>

                  <h2 className="
                    text-xl
                    font-bold
                    text-slate-800
                  ">
                    AI Admission Agent
                  </h2>

                  <p className="
                    text-sm
                    text-slate-500
                    mt-1
                  ">
                    Admission orchestration
                  </p>

                </div>

              </div>

            </div>


            {/* Agent Form */}

            <div className="p-6">

              <div className="
                grid
                grid-cols-1
                lg:grid-cols-2
                gap-5
              ">


                {/* Patient */}

                <div className="lg:col-span-2">

                  <label className="
                    block
                    text-sm
                    font-medium
                    text-slate-700
                    mb-2
                  ">
                    Unadmitted Patient
                  </label>

                  <select
                    value={patientId}
                    onChange={(e) =>
                      setPatientId(e.target.value)
                    }
                    disabled={
                      loadingPatients ||
                      runningAgent
                    }
                    className="
                      w-full
                      px-4
                      py-3
                      rounded-lg
                      border
                      border-slate-300
                      bg-white
                      text-sm
                      outline-none
                      focus:ring-2
                      focus:ring-blue-500
                      disabled:bg-slate-100
                    "
                  >

                    <option value="">
                      {loadingPatients
                        ? "Loading unadmitted patients..."
                        : "Select an unadmitted patient"}
                    </option>

                    {patients.map((patient) => (

                      <option
                        key={patient.patient_id}
                        value={patient.patient_id}
                      >
                        {patient.patient_id}
                      </option>

                    ))}

                  </select>

                  <p className="
                    text-xs
                    text-slate-400
                    mt-2
                  ">
                    Only patients without an active
                    admission are shown.
                  </p>

                </div>


                {/* Department */}

                <div>

                  <label className="
                    block
                    text-sm
                    font-medium
                    text-slate-700
                    mb-2
                  ">
                    Department
                  </label>

                  <select
                    value={departmentId}
                    onChange={(e) =>
                      setDepartmentId(e.target.value)
                    }
                    disabled={runningAgent}
                    className="
                      w-full
                      px-4
                      py-3
                      rounded-lg
                      border
                      border-slate-300
                      bg-white
                      outline-none
                      focus:ring-2
                      focus:ring-blue-500
                    "
                  >
                    <option value="">
                      Select department
                    </option>

                    {departments.map((department) => (
                      <option
                        key={department.department_id}
                        value={department.department_id}
                      >
                        {department.department_name}
                      </option>
                    ))}
                  </select>

                </div>


                {/* Admission Type */}

                <div>

                  <label className="
                    block
                    text-sm
                    font-medium
                    text-slate-700
                    mb-2
                  ">
                    Admission Type
                  </label>

                  <select
                    value={admissionType}
                    onChange={(e) =>
                      setAdmissionType(e.target.value)
                    }
                    disabled={
                      runningAgent ||
                      !clinicalSummary
                    }
                    className="
                      w-full
                      px-4
                      py-3
                      rounded-lg
                      border
                      border-slate-300
                      bg-white
                      outline-none
                      focus:ring-2
                      focus:ring-blue-500
                    "
                  >
                    <option value="">
                      Select admission type
                    </option>
                    <option value="OBSERVATION">
                      Observation
                    </option>
                    <option value="EMERGENCY">
                      Emergency
                    </option>
                    <option value="ELECTIVE">
                      Elective
                    </option>
                    <option value="TRANSFER">
                      Transfer
                    </option>
                  </select>

                  {suggestedAdmissionType && (
                    <p className="
                      text-xs
                      text-blue-600
                      mt-2
                    ">
                      AI recommendation:{" "}
                      {suggestedAdmissionType}
                    </p>
                  )}

                </div>


                {/* Diagnosis */}

                <div className="lg:col-span-2">

                  <label className="
                    block
                    text-sm
                    font-medium
                    text-slate-700
                    mb-2
                  ">
                    Diagnosis
                  </label>

                  <input
                    type="text"
                    value={diagnosis}
                    onChange={(e) =>
                      setDiagnosis(e.target.value)
                    }
                    placeholder="Primary diagnosis"
                    disabled={runningAgent}
                    className="
                      w-full
                      px-4
                      py-3
                      rounded-lg
                      border
                      border-slate-300
                      outline-none
                      focus:ring-2
                      focus:ring-blue-500
                    "
                  />

                </div>


                {/* Notes */}

                <div className="lg:col-span-2">

                  <label className="
                    block
                    text-sm
                    font-medium
                    text-slate-700
                    mb-2
                  ">
                    Notes
                  </label>

                  <textarea
                    rows="3"
                    value={notes}
                    onChange={(e) =>
                      setNotes(e.target.value)
                    }
                    placeholder="Admission notes"
                    disabled={runningAgent}
                    className="
                      w-full
                      px-4
                      py-3
                      rounded-lg
                      border
                      border-slate-300
                      outline-none
                      focus:ring-2
                      focus:ring-blue-500
                      resize-none
                    "
                  />

                </div>


              </div>


              {patientId && (
                <section className="
                  mt-6
                  rounded-xl
                  border
                  border-slate-200
                  bg-slate-50
                  p-5
                ">
                  <div className="
                    flex
                    items-center
                    justify-between
                    gap-3
                  ">
                    <div>
                      <h3 className="
                        text-base
                        font-semibold
                        text-slate-800
                      ">
                        Patient Clinical Information
                      </h3>

                      <p className="
                        text-xs
                        text-slate-500
                        mt-1
                      ">
                        Read-only information retrieved
                        from the clinical database.
                      </p>
                    </div>

                    <span className="
                      px-2.5
                      py-1
                      rounded-full
                      bg-blue-100
                      text-blue-700
                      text-xs
                      font-semibold
                    ">
                      LIVE DATA
                    </span>
                  </div>

                  {clinicalLoading ? (
                    <p className="
                      text-sm
                      text-slate-500
                      mt-4
                    ">
                      Loading clinical information...
                    </p>
                  ) : clinicalSummary ? (
                    <>
                      <div className="
                        mt-4
                        rounded-lg
                        border
                        border-blue-200
                        bg-blue-50
                        p-4
                      ">
                        <p className="
                          text-xs
                          font-semibold
                          uppercase
                          tracking-wide
                          text-blue-700
                        ">
                          AI Admission Recommendation
                        </p>

                        <div className="
                          grid
                          grid-cols-1
                          md:grid-cols-3
                          gap-3
                          mt-3
                        ">
                          <RecommendationBox
                            label="Department"
                            value={
                              suggestedDepartment?.department_name ||
                              "No confident match"
                            }
                          />

                          <RecommendationBox
                            label="Admission Type"
                            value={
                              suggestedAdmissionType ||
                              "No confident recommendation"
                            }
                          />

                          <RecommendationBox
                            label="Clinical Reason"
                            value={
                              suggestedDiagnosis ||
                              "No confident diagnosis from available data"
                            }
                          />
                        </div>

                        <p className="
                          text-xs
                          text-blue-700
                          mt-3
                        ">
                          Review the recommendations before
                          running the admission workflow.
                        </p>
                      </div>

                      <div className="
                        grid
                        grid-cols-1
                        lg:grid-cols-3
                        gap-4
                        mt-4
                      ">
                      <ClinicalList
                        title="Recent Conditions"
                        items={conditions}
                        renderItem={(item) =>
                          item.description
                        }
                      />

                      <ClinicalList
                        title="Recent Encounters"
                        items={encounters}
                        renderItem={(item) =>
                          item.reason_description ||
                          item.description ||
                          item.encounter_class
                        }
                      />

                      <ClinicalList
                        title="Recent Observations"
                        items={observations.slice(0, 5)}
                        renderItem={(item) =>
                          `${item.description || "Observation"}: ${
                            item.value ?? "N/A"
                          } ${item.units || ""}`
                        }
                      />
                      </div>
                    </>
                  ) : null}
                </section>
              )}


              {/* Run Button */}

              <button
                onClick={handleRunWorkflow}
                disabled={
                  runningAgent ||
                  loadingPatients ||
                  patients.length === 0 ||
                  !patientId ||
                  !departmentId ||
                  !admissionType
                }
                className="
                  mt-6
                  w-full
                  py-3.5
                  rounded-lg
                  bg-violet-600
                  text-white
                  font-semibold
                  hover:bg-violet-700
                  disabled:bg-slate-400
                  disabled:cursor-not-allowed
                "
              >

                {runningAgent
                  ? "Processing Admission..."
                  : "Run AI Admission Workflow"}

              </button>

            </div>

          </section>


          {/* =================================================
              WORKFLOW RESULT
              IMMEDIATELY AFTER AGENT
          ================================================= */}

          {workflowResult && (

            <WorkflowResult
              result={workflowResult}
            />

          )}
          {/* Email Notification */}
{workflowResult?.status === "SUCCESS" && (
  <NotificationButton
    eventType="ADMISSION_CREATED"
    priority="NORMAL"
    patientId={
      workflowResult.context?.patient_id ||
      workflowResult.data?.patient_id ||
      null
    }
    admissionId={
      workflowResult.context?.admission_id ||
      workflowResult.data?.admission_id ||
      null
    }
    title="Admission Created"
    message={`A new hospital admission has been successfully created${
      workflowResult.context?.admission_id ||
      workflowResult.data?.admission_id
        ? ` for admission #${
            workflowResult.context?.admission_id ||
            workflowResult.data?.admission_id
          }`
        : ""
    }.`}
    sourceAgent="AdmissionAgent"
  />
)}


          {/* =================================================
              ADMISSION REGISTRY + DETAILS
          ================================================= */}

          <div className="
            grid
            grid-cols-1
            2xl:grid-cols-[minmax(0,1.7fr)_380px]
            gap-6
            items-start
          ">


            {/* =================================================
                REGISTRY
            ================================================= */}

            <section className="
              bg-white
              rounded-2xl
              border
              border-slate-200
              shadow-sm
              overflow-hidden
            ">

              <div className="
                px-6
                py-5
                border-b
                border-slate-200
              ">

                <div className="
                  flex
                  flex-col
                  xl:flex-row
                  xl:items-center
                  xl:justify-between
                  gap-4
                ">

                  <div>
                    <h2 className="
                      text-lg
                      font-semibold
                      text-slate-800
                    ">
                      Admission Registry
                    </h2>

                    <p className="
                      text-sm
                      text-slate-500
                      mt-1
                    ">
                      Search by admission, patient,
                      department, type, status or diagnosis.
                    </p>
                  </div>

                  <div className="
                    relative
                    w-full
                    xl:w-96
                  ">
                    <span className="
                      absolute
                      left-3
                      top-1/2
                      -translate-y-1/2
                      text-slate-400
                    ">
                      🔎
                    </span>

                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) =>
                        setSearchTerm(e.target.value)
                      }
                      placeholder="Search admissions..."
                      className="
                        w-full
                        pl-10
                        pr-10
                        py-2.5
                        rounded-xl
                        border
                        border-slate-200
                        bg-slate-50
                        text-sm
                        outline-none
                        focus:bg-white
                        focus:ring-2
                        focus:ring-blue-500
                      "
                    />

                    {searchTerm && (
                      <button
                        type="button"
                        onClick={() => setSearchTerm("")}
                        className="
                          absolute
                          right-3
                          top-1/2
                          -translate-y-1/2
                          text-slate-400
                          hover:text-slate-700
                        "
                      >
                        ×
                      </button>
                    )}
                  </div>

                </div>

                {searchTerm && (
                  <p className="
                    text-xs
                    text-slate-400
                    mt-3
                  ">
                    Showing {filteredAdmissions.length} of{" "}
                    {admissions.length} admissions.
                  </p>
                )}

              </div>


              {loadingAdmissions ? (

                <div className="
                  p-10
                  text-center
                  text-sm
                  text-slate-500
                ">
                  Loading admissions...
                </div>

              ) : filteredAdmissions.length === 0 ? (

                <div className="
                  p-10
                  text-center
                  text-sm
                  text-slate-500
                ">
                  {searchTerm
                    ? "No admissions match your search."
                    : "No admissions found."}
                </div>

              ) : (

                <div className="overflow-x-auto">

                  <table className="
                    w-full
                    text-sm
                  ">

                    <thead>

                      <tr className="
                        border-b
                        border-slate-200
                        bg-slate-50
                        text-left
                      ">

                        <th className="px-4 py-3">
                          Admission
                        </th>

                        <th className="px-4 py-3">
                          Patient
                        </th>

                        <th className="px-4 py-3">
                          Department
                        </th>

                        <th className="px-4 py-3">
                          Type
                        </th>

                        <th className="px-4 py-3">
                          Status
                        </th>

                      </tr>

                    </thead>

                    <tbody>

                      {filteredAdmissions.map((admission) => (

                        <tr
                          key={admission.admission_id}
                          onClick={() =>
                            handleSelectAdmission(
                              admission
                            )
                          }
                          className={`
                            border-b
                            border-slate-100
                            cursor-pointer
                            hover:bg-blue-50
                            ${
                              Number(
                                selectedAdmission?.admission_id
                              ) ===
                              Number(
                                admission.admission_id
                              )
                                ? "bg-blue-50"
                                : ""
                            }
                          `}
                        >

                          <td className="
                            px-4
                            py-4
                            font-semibold
                            text-slate-800
                          ">
                            #{admission.admission_id}
                          </td>

                          <td className="
                            px-4
                            py-4
                            text-slate-600
                          ">
                            <span className="block max-w-55 truncate">
                              {admission.patient_id}
                            </span>
                          </td>

                          <td className="
                            px-4
                            py-4
                            text-slate-600
                          ">
                            {getDepartmentName(
                              admission.department_id
                            )}
                          </td>

                          <td className="
                            px-4
                            py-4
                            text-slate-600
                          ">
                            {admission.admission_type}
                          </td>

                          <td className="px-4 py-4">

                            <StatusBadge
                              status={
                                admission.status
                              }
                            />

                          </td>

                        </tr>

                      ))}

                    </tbody>

                  </table>

                </div>

              )}
              
 
            </section>


            {/* =================================================
                SELECTED ADMISSION DETAILS
                NOW BESIDE REGISTRY
            ================================================= */}

            <AdmissionDetails
              admission={selectedAdmission}
              departments={departments}
              onDischarge={handleDischarge}
              onCancel={handleCancel}
            />

          </div>


        </main>

      </div>

    </div>

  )
}


function RecommendationBox({
  label,
  value,
}) {
  return (
    <div className="
      rounded-lg
      bg-white
      border
      border-blue-100
      p-3
    ">
      <p className="text-xs text-slate-500">
        {label}
      </p>

      <p className="
        text-sm
        font-semibold
        text-slate-800
        mt-1
      ">
        {value}
      </p>
    </div>
  )
}


function ClinicalList({
  title,
  items,
  renderItem,
}) {
  return (
    <div>
      <p className="
        text-xs
        font-semibold
        uppercase
        tracking-wide
        text-slate-500
      ">
        {title}
      </p>

      <div className="
        mt-2
        space-y-2
        max-h-32
        overflow-y-auto
      ">
        {items.length === 0 ? (
          <p className="
            text-xs
            text-slate-400
          ">
            No recent data found.
          </p>
        ) : (
          items.map((item, index) => (
            <div
              key={index}
              className="
                rounded-lg
                border
                border-slate-200
                bg-white
                px-3
                py-2
                text-xs
                text-slate-700
              "
            >
              {renderItem(item) || "N/A"}
            </div>
          ))
        )}
      </div>
    </div>
  )
}


// =============================================================
// KPI CARD
// =============================================================

function KpiCard({
  label,
  value,
  icon,
}) {

  return (

    <div className="
      bg-white
      rounded-xl
      border
      border-slate-200
      p-5
      shadow-sm
    ">

      <div className="
        flex
        items-center
        justify-between
      ">

        <div>

          <p className="
            text-xs
            font-medium
            uppercase
            tracking-wide
            text-slate-500
          ">
            {label}
          </p>

          <p className="
            text-2xl
            font-bold
            text-slate-800
            mt-2
          ">
            {value}
          </p>

        </div>

        <div className="
          text-xl
        ">
          {icon}
        </div>

      </div>

    </div>

  )
}


// =============================================================
// WORKFLOW RESULT
// =============================================================

function WorkflowResult({ result }) {

  const actions =
    result.actions ||
    result.context?.actions ||
    []

  const rawDecision =
    result.decision || ""

  const isBedPending =
    rawDecision === "NO_ACTION" &&
    String(result.reason || "")
      .toLowerCase()
      .includes("bed")

  const decisionLabel = isBedPending
    ? "BED ASSIGNMENT PENDING"
    : rawDecision === "NO_ACTION"
      ? "NO FURTHER ACTION"
      : rawDecision === "ASSIGN_BED"
        ? "BED ASSIGNMENT INITIATED"
        : rawDecision === "ASSIGN_DOCTOR"
          ? "DOCTOR ASSIGNMENT INITIATED"
          : rawDecision === "ASSIGN_NURSE"
            ? "NURSE ASSIGNMENT INITIATED"
            : rawDecision || "N/A"

  return (

    <section className="
      bg-white
      rounded-2xl
      border
      border-green-200
      shadow-sm
      p-6
    ">

      <div className="
        flex
        items-center
        justify-between
        gap-4
      ">

        <div>

          <h2 className="
            text-lg
            font-semibold
            text-slate-800
          ">
            AI Workflow Result
          </h2>

          <p className="
            text-sm
            text-slate-500
            mt-1
          ">
            AdmissionAgent orchestration result.
          </p>

        </div>

        <span className="
          px-3
          py-1.5
          rounded-full
          bg-green-100
          text-green-700
          text-xs
          font-semibold
        ">
          {result.status || "SUCCESS"}
        </span>

      </div>


      <div className="
        grid
        grid-cols-1
        md:grid-cols-3
        gap-4
        mt-6
      ">

        <InfoBox
          label="Decision"
          value={decisionLabel}
        />

        <InfoBox
          label="Patient"
          value={
            result.context?.patient_id ||
            result.data?.patient_id ||
            "N/A"
          }
        />

        <InfoBox
          label="Admission"
          value={
            result.context?.admission_id ||
            result.data?.admission_id ||
            "N/A"
          }
        />

      </div>


      <div className="
        mt-5
        p-4
        rounded-lg
        bg-slate-50
      ">

        <p className="
          text-xs
          uppercase
          tracking-wide
          text-slate-500
        ">
          Reason
        </p>

        <p className="
          text-sm
          text-slate-700
          mt-1
        ">
          {result.reason ||
            "No reason provided."}
        </p>

      </div>


      {actions.length > 0 && (

        <div className="mt-5">

          <h3 className="
            text-sm
            font-semibold
            text-slate-700
          ">
            Actions Performed
          </h3>

          <div className="
            mt-3
            space-y-2
          ">

            {actions.map(
              (action, index) => (

                <div
                  key={index}
                  className="
                    flex
                    items-center
                    justify-between
                    p-3
                    rounded-lg
                    border
                    border-slate-200
                  "
                >

                  <span className="
                    text-sm
                    font-medium
                    text-slate-700
                  ">
                    {action.action ||
                      "Action"}
                  </span>

                  <span className="
                    text-xs
                    font-semibold
                    text-green-600
                  ">
                    {action.status ||
                      "COMPLETED"}
                  </span>

                </div>

              )
            )}

          </div>

        </div>

      )}

    </section>

  )
}


// =============================================================
// ADMISSION DETAILS
// =============================================================

function AdmissionDetails({
  admission,
  departments,
  onDischarge,
  onCancel,
}) {

  if (!admission) {

    return (

      <section className="
        bg-white
        rounded-2xl
        border
        border-slate-200
        shadow-sm
        p-6
        2xl:sticky
        2xl:top-24
      ">

        <div className="
          text-center
          py-10
        ">

          <div className="text-3xl">
            🏥
          </div>

          <h3 className="
            mt-3
            font-semibold
            text-slate-700
          ">
            Admission Details
          </h3>

          <p className="
            text-sm
            text-slate-500
            mt-1
          ">
            Select an admission from the
            registry to view details.
          </p>

        </div>

      </section>

    )
  }


  const active =
    admission.status === "ADMITTED" ||
    admission.status === "OBSERVATION"


  return (

    <section className="
      bg-white
      rounded-2xl
      border
      border-slate-200
      shadow-sm
      p-6
      2xl:sticky
      2xl:top-24
    ">

      <div className="
        rounded-2xl
        bg-linear-to-br
        from-slate-900
        to-slate-700
        p-5
        text-white
      ">

        <div className="
          flex
          items-start
          justify-between
          gap-3
        ">

          <div>
            <p className="
              text-xs
              font-semibold
              uppercase
              tracking-wider
              text-slate-300
            ">
              Admission Record
            </p>

            <h2 className="
              text-2xl
              font-bold
              mt-1
            ">
              #{admission.admission_id}
            </h2>

            <p className="
              text-xs
              text-slate-300
              mt-1
            ">
              Patient admission details
            </p>
          </div>

          <StatusBadge
            status={admission.status}
          />

        </div>

      </div>


      <div className="
        mt-6
        space-y-4
      ">

        <DetailRow
          label="Patient ID"
          value={admission.patient_id}
        />

        <DetailRow
          label="Department"
          value={
            departments.find(
              (department) =>
                Number(department.department_id) ===
                Number(admission.department_id)
            )?.department_name ||
            `Department ${admission.department_id ?? "N/A"}`
          }
        />

        <DetailRow
          label="Admission Type"
          value={admission.admission_type}
        />

        <DetailRow
          label="Bed ID"
          value={
            admission.bed_id ??
            "Not assigned"
          }
        />

        <DetailRow
          label="Doctor ID"
          value={
            admission.doctor_id ??
            "Not assigned"
          }
        />

        <DetailRow
          label="Admission Time"
          value={
            admission.admission_time ||
            "N/A"
          }
        />

        <DetailRow
          label="Diagnosis"
          value={
            admission.diagnosis ||
            "N/A"
          }
        />

      </div>


      {active && (

        <div className="
          mt-6
          grid
          grid-cols-1
          gap-3
        ">

          {admission.bed_id == null && (
            <button
              type="button"
              onClick={() => {
                window.location.href = "/beds"
              }}
              className="
                w-full
                py-2.5
                rounded-xl
                bg-blue-50
                text-blue-700
                border
                border-blue-200
                text-sm
                font-semibold
                hover:bg-blue-100
                transition
              "
            >
              🛏️ Go to Bed Management
            </button>
          )}

          <button
            onClick={onDischarge}
            className="
              w-full
              py-2.5
              rounded-lg
              bg-green-600
              text-white
              text-sm
              font-semibold
              hover:bg-green-700
            "
          >
            Discharge Patient
          </button>

          <button
            onClick={onCancel}
            className="
              w-full
              py-2.5
              rounded-lg
              bg-red-50
              text-red-700
              border
              border-red-200
              text-sm
              font-semibold
              hover:bg-red-100
            "
          >
            Cancel Admission
          </button>

        </div>

      )}

    </section>

  )
}


function Toast({
  toast,
  onClose,
}) {
  const isSuccess = toast.type === "success"

  return (
    <div className="
      fixed
      top-5
      right-5
      z-100
      w-[min(420px,calc(100vw-2rem))]
      rounded-2xl
      border
      bg-white
      shadow-2xl
      p-4
      flex
      items-start
      gap-3
    "
      style={{
        borderColor: isSuccess
          ? "rgb(187 247 208)"
          : "rgb(254 202 202)",
      }}
    >

      <div className={`
        w-10
        h-10
        rounded-xl
        flex
        items-center
        justify-center
        text-lg
        ${isSuccess
          ? "bg-green-100 text-green-700"
          : "bg-red-100 text-red-700"}
      `}>
        {isSuccess ? "✓" : "!"}
      </div>

      <div className="flex-1 min-w-0">

        <p className="
          text-sm
          font-semibold
          text-slate-800
        ">
          {toast.title}
        </p>

        <p className="
          text-xs
          text-slate-500
          mt-1
        ">
          {toast.message}
        </p>

      </div>

      <button
        type="button"
        onClick={onClose}
        className="
          text-slate-400
          hover:text-slate-700
          text-lg
          leading-none
        "
      >
        ×
      </button>

    </div>
  )
}


// =============================================================
// INFO BOX
// =============================================================

function InfoBox({
  label,
  value,
}) {

  return (

    <div className="
      p-4
      rounded-lg
      bg-slate-50
      border
      border-slate-200
    ">

      <p className="
        text-xs
        uppercase
        tracking-wide
        text-slate-500
      ">
        {label}
      </p>

      <p className="
        text-sm
        font-semibold
        text-slate-800
        mt-2
        break-all
      ">
        {value}
      </p>

    </div>

  )
}


// =============================================================
// DETAIL ROW
// =============================================================

function DetailRow({
  label,
  value,
}) {

  return (

    <div className="
      rounded-xl
      border
      border-slate-100
      bg-slate-50/70
      px-4
      py-3
    ">

      <p className="
        text-[11px]
        font-semibold
        uppercase
        tracking-wider
        text-slate-400
      ">
        {label}
      </p>

      <p className="
        mt-1
        text-sm
        font-semibold
        text-slate-800
        break-all
      ">
        {value}
      </p>

    </div>

  )
}


// =============================================================
// STATUS BADGE
// =============================================================

function StatusBadge({
  status,
}) {

  const styles = {

    ADMITTED:
      "bg-green-100 text-green-700 border-green-200",

    OBSERVATION:
      "bg-blue-100 text-blue-700 border-blue-200",

    DISCHARGED:
      "bg-slate-100 text-slate-700 border-slate-200",

    CANCELLED:
      "bg-red-100 text-red-700 border-red-200",

  }

  return (

    <span className={`
      inline-flex
      px-2.5
      py-1
      rounded-full
      border
      text-xs
      font-semibold
      ${styles[status] ||
        "bg-slate-100 text-slate-700 border-slate-200"}
    `}>

      {status || "UNKNOWN"}

    </span>

  )
}


export default Admission