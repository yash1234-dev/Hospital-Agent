import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"

import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import NotificationButton from "../components/NotificationButton"

import {
  getUnassignedAdmissions,
  getAvailableDoctors,
  getAvailableNurses,
  assignDoctor,
  assignNurse,
} from "../services/api"


function StaffManagement() {

  const navigate = useNavigate()

  // =========================================================
  // ADMISSIONS
  // =========================================================

  const [admissions, setAdmissions] = useState([])
  const [selectedAdmission, setSelectedAdmission] = useState(null)
  const [loadingAdmissions, setLoadingAdmissions] = useState(true)

  // =========================================================
  // STAFF
  // =========================================================

  const [staffType, setStaffType] = useState("DOCTORS")

  const [doctors, setDoctors] = useState([])
  const [nurses, setNurses] = useState([])

  const [loadingStaff, setLoadingStaff] = useState(false)

  // =========================================================
  // FILTERS
  // =========================================================

  const [speciality, setSpeciality] = useState("")
  const [searchText, setSearchText] = useState("")
  const [shiftType, setShiftType] = useState("")

  // =========================================================
  // UI STATE
  // =========================================================

  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [assigningId, setAssigningId] = useState(null)
  const [notificationData, setNotificationData] = useState(null)


  // =========================================================
  // LOAD UNASSIGNED ADMISSIONS
  // =========================================================

  async function loadAdmissions() {

    try {

      setLoadingAdmissions(true)
      setError("")

      const data = await getUnassignedAdmissions()

      setAdmissions(data.admissions || [])

    } catch (err) {

      setError(
        err.message ||
        "Failed to load unassigned admissions."
      )

    } finally {

      setLoadingAdmissions(false)

    }
  }


  // =========================================================
  // LOAD STAFF FOR SELECTED ADMISSION
  // =========================================================

  async function loadStaff() {

    if (!selectedAdmission) {
      return
    }

    try {

      setLoadingStaff(true)
      setError("")

      const departmentId =
        selectedAdmission.department_id

      if (staffType === "DOCTORS") {

        const data = await getAvailableDoctors({
          departmentId,
          speciality,
          shiftType,
        })

        setDoctors(data.doctors || [])

      } else {

        const data = await getAvailableNurses({
          departmentId,
          shiftType,
        })

        setNurses(data.nurses || [])

      }

    } catch (err) {

      setError(
        err.message ||
        "Failed to load available staff."
      )

    } finally {

      setLoadingStaff(false)

    }
  }


  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {

    loadAdmissions()

  }, [])


  // =========================================================
  // LOAD STAFF WHEN ADMISSION / TYPE / FILTER CHANGES
  // =========================================================

  useEffect(() => {

    if (!selectedAdmission) {
      return
    }

    loadStaff()

  }, [
    selectedAdmission,
    staffType,
    speciality,
    shiftType,
  ])


  // =========================================================
  // SELECT ADMISSION
  // =========================================================

  function handleSelectAdmission(admission) {

    setSelectedAdmission(admission)

    setSpeciality("")
    setSearchText("")
    setShiftType("")

    setSuccess("")
    setError("")
  }


  // =========================================================
  // SPECIALITIES
  // =========================================================

  const specialities = useMemo(() => {

    const values = doctors
      .map((doctor) => doctor.speciality)
      .filter(Boolean)

    return [...new Set(values)].sort()

  }, [doctors])


  // =========================================================
  // CLIENT-SIDE SEARCH
  // =========================================================

  const filteredDoctors = useMemo(() => {

    const query =
      searchText.trim().toLowerCase()

    if (!query) {
      return doctors
    }

    return doctors.filter((doctor) => {

      return (
        String(doctor.doctor_name || "")
          .toLowerCase()
          .includes(query)
        ||
        String(doctor.doctor_id || "")
          .includes(query)
        ||
        String(doctor.speciality || "")
          .toLowerCase()
          .includes(query)
      )

    })

  }, [doctors, searchText])


  const filteredNurses = useMemo(() => {

    const query =
      searchText.trim().toLowerCase()

    if (!query) {
      return nurses
    }

    return nurses.filter((nurse) => {

      return (
        String(nurse.nurse_name || "")
          .toLowerCase()
          .includes(query)
        ||
        String(nurse.nurse_id || "")
          .includes(query)
      )

    })

  }, [nurses, searchText])


  // =========================================================
  // ASSIGN DOCTOR
  // =========================================================

  async function handleAssignDoctor(doctor) {

    if (!selectedAdmission) {
      return
    }

    // Frontend protection
    if (!selectedAdmission.has_bed) {

      setError(
        "This patient has not been assigned a room/bed. Please assign a bed before assigning a doctor."
      )

      return
    }

    try {

      setAssigningId(`DOCTOR-${doctor.doctor_id}`)

      setError("")
      setSuccess("")

      const result = await assignDoctor(
        selectedAdmission.admission_id,
        doctor.doctor_id
      )

      if (result.execution_status === "COMPLETED") {

        setSuccess(
          `Doctor ${doctor.doctor_name} assigned successfully to Admission ${selectedAdmission.admission_id}.`
        )

        
        setNotificationData({
  type: "DOCTOR",
  patientId: selectedAdmission.patient_id,
  admissionId: selectedAdmission.admission_id,
  staffName: doctor.doctor_name,
  staffId: doctor.doctor_id,
})
await loadAdmissions()

        const updatedAdmission = {
          ...selectedAdmission,
          doctor_id: doctor.doctor_id,
          has_doctor: 1,
        }

        setSelectedAdmission(
          updatedAdmission
        )

      } else {

        setError(
          result.error_message ||
          "Doctor assignment was not completed."
        )

      }

    } catch (err) {

      // Backend bed prerequisite
      if (
        err.status === 409 &&
        err.data?.status === "BED_REQUIRED"
      ) {

        setError(
          err.data.message ||
          "Please assign a bed before assigning a doctor."
        )

        return
      }

      setError(
        err.data?.message ||
        err.message ||
        "Failed to assign doctor."
      )

    } finally {

      setAssigningId(null)

    }
  }


  // =========================================================
  // ASSIGN NURSE
  // =========================================================

  async function handleAssignNurse(nurse) {

    if (!selectedAdmission) {
      return
    }

    if (!selectedAdmission.has_bed) {

      setError(
        "This patient has not been assigned a room/bed. Please assign a bed before assigning a nurse."
      )

      return
    }

    try {

      setAssigningId(`NURSE-${nurse.nurse_id}`)

      setError("")
      setSuccess("")

      const result = await assignNurse(
        selectedAdmission.admission_id,
        nurse.nurse_id
      )

      if (result.execution_status === "COMPLETED") {

        setSuccess(
          `Nurse ${nurse.nurse_name} assigned successfully to Admission ${selectedAdmission.admission_id}.`
        )
        setNotificationData({
  type: "NURSE",
  patientId: selectedAdmission.patient_id,
  admissionId: selectedAdmission.admission_id,
  staffName: nurse.nurse_name,
  staffId: nurse.nurse_id,
})
        await loadAdmissions()

      } else {

        setError(
          result.error_message ||
          "Nurse assignment was not completed."
        )

      }

    } catch (err) {

      if (
        err.status === 409 &&
        err.data?.status === "BED_REQUIRED"
      ) {

        setError(
          err.data.message ||
          "Please assign a bed before assigning a nurse."
        )

        return
      }

      setError(
        err.data?.message ||
        err.message ||
        "Failed to assign nurse."
      )

    } finally {

      setAssigningId(null)

    }
  }


  // =========================================================
  // GO TO BED MANAGEMENT
  // =========================================================

  function handleGoToBedManagement() {

    if (!selectedAdmission) {
      return
    }

    navigate("/beds", {
      state: {
        admissionId:
          selectedAdmission.admission_id,
        patientId:
          selectedAdmission.patient_id,
        departmentId:
          selectedAdmission.department_id,
      },
    })
  }


  // =========================================================
  // FORMAT DATE
  // =========================================================

  function formatDate(value) {

    if (!value) {
      return "N/A"
    }

    return new Date(value).toLocaleString()

  }


  // =========================================================
  // RENDER
  // =========================================================

  return (

    <div className="min-h-screen bg-slate-100 flex">

      <Sidebar />

      <div className="min-w-0 flex-1">

        <Header />

        <main className="min-w-0 p-4 sm:p-6 lg:p-8">

          {/* ================================================= */}
          {/* PAGE HEADER */}
          {/* ================================================= */}

          <div className="mb-8">

            <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
              Doctor & Staff Management
            </h1>

            <p className="text-sm text-slate-500 mt-1">
              Assign available doctors and nurses to active
              hospital admissions.
            </p>

          </div>


          {/* ================================================= */}
          {/* GLOBAL ERROR */}
          {/* ================================================= */}

          {error && (

            <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200">

              <div className="flex items-start justify-between gap-4">

                <div>

                  <p className="font-medium text-red-700">
                    Operation Failed
                  </p>

                  <p className="text-sm text-red-600 mt-1">
                    {error}
                  </p>

                </div>

                {selectedAdmission &&
                  !selectedAdmission.has_bed && (

                  <button
                    onClick={handleGoToBedManagement}
                    className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700"
                  >
                    Go to Bed Management
                  </button>

                )}

              </div>

            </div>

          )}


          {/* ================================================= */}
          {/* SUCCESS */}
          {/* ================================================= */}

          {success && (

            <div className="mb-6 p-4 rounded-lg bg-green-50 border border-green-200">

              <p className="font-medium text-green-700">
                Assignment Successful
              </p>

              <p className="text-sm text-green-600 mt-1">
                {success}
              </p>

            </div>

          )}
          {notificationData && (
  <div className="mb-6">
    <NotificationButton
      eventType="STAFF_ASSIGNED"
      priority="NORMAL"
      patientId={notificationData.patientId}
      admissionId={notificationData.admissionId}
      title={`${notificationData.type === "DOCTOR" ? "Doctor" : "Nurse"} Assigned`}
      message={`${notificationData.type === "DOCTOR" ? "Doctor" : "Nurse"} ${notificationData.staffName} (ID: ${notificationData.staffId}) has been successfully assigned to Admission #${notificationData.admissionId}.`}
      sourceAgent="StaffAgent"
    />
  </div>
)}


          {/* ================================================= */}
          {/* ADMISSION SECTION */}
          {/* ================================================= */}

          <section className="bg-white rounded-xl border border-slate-200 p-6">

            <div className="flex items-center justify-between">

              <div>

                <h2 className="text-lg font-semibold text-slate-800">
                  Active Admissions Requiring Staff
                </h2>

                <p className="text-sm text-slate-500 mt-1">
                  Select an admission to view staff from its
                  department.
                </p>

              </div>

              <button
                onClick={loadAdmissions}
                className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Refresh
              </button>

            </div>


            {/* ADMISSIONS */}

            {loadingAdmissions ? (

              <div className="py-10 text-center text-slate-500">
                Loading admissions...
              </div>

            ) : admissions.length === 0 ? (

              <div className="py-10 text-center">

                <p className="font-medium text-slate-700">
                  No unassigned admissions found.
                </p>

                <p className="text-sm text-slate-500 mt-1">
                  All active admissions currently have
                  doctor assignments.
                </p>

              </div>

            ) : (

              <div className="mt-6 overflow-x-auto">

                <table className="w-full text-sm">

                  <thead>

                    <tr className="border-b border-slate-200 text-left">

                      <th className="pb-3 font-medium text-slate-500">
                        Admission
                      </th>

                      <th className="pb-3 font-medium text-slate-500">
                        Patient
                      </th>

                      <th className="pb-3 font-medium text-slate-500">
                        Department
                      </th>

                      <th className="pb-3 font-medium text-slate-500">
                        Bed
                      </th>

                      <th className="pb-3 font-medium text-slate-500">
                        Status
                      </th>

                      <th className="pb-3 font-medium text-slate-500">
                        Action
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {admissions.map((admission) => {

                      const selected =
                        selectedAdmission?.admission_id ===
                        admission.admission_id

                      return (

                        <tr
                          key={admission.admission_id}
                          className={`border-b border-slate-100 ${
                            selected
                              ? "bg-blue-50"
                              : ""
                          }`}
                        >

                          <td className="py-4 font-medium text-slate-800">
                            #{admission.admission_id}
                          </td>

                          <td className="py-4">

                            <p className="text-slate-700">
                              {admission.patient_id}
                            </p>

                          </td>

                          <td className="py-4">

                            <p className="font-medium text-slate-700">
                              {admission.department_name}
                            </p>

                            <p className="text-xs text-slate-500">
                              {admission.department_code}
                              {" · ID "}
                              {admission.department_id}
                            </p>

                          </td>

                          <td className="py-4">

                            {admission.has_bed ? (

                              <span className="px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                                Bed #{admission.bed_id}
                              </span>

                            ) : (

                              <span className="px-2 py-1 rounded-full bg-red-100 text-red-700 text-xs font-medium">
                                No Bed
                              </span>

                            )}

                          </td>

                          <td className="py-4 text-slate-600">
                            {admission.status}
                          </td>

                          <td className="py-4">

                            <button
                              onClick={() =>
                                handleSelectAdmission(
                                  admission
                                )
                              }
                              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                                selected
                                  ? "bg-blue-600 text-white"
                                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                              }`}
                            >
                              {selected
                                ? "Selected"
                                : "Select"}
                            </button>

                          </td>

                        </tr>

                      )

                    })}

                  </tbody>

                </table>

              </div>

            )}

          </section>


          {/* ================================================= */}
          {/* SELECTED ADMISSION */}
          {/* ================================================= */}

          {selectedAdmission && (

            <section className="mt-6 bg-white rounded-xl border border-slate-200 p-6">

              <div className="flex items-start justify-between">

                <div>

                  <h2 className="text-lg font-semibold text-slate-800">
                    Selected Admission #{selectedAdmission.admission_id}
                  </h2>

                  <p className="text-sm text-slate-500 mt-1">
                    Staff is automatically restricted to the
                    patient's admission department.
                  </p>

                </div>

                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    selectedAdmission.has_bed
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {selectedAdmission.has_bed
                    ? `Bed #${selectedAdmission.bed_id}`
                    : "BED REQUIRED"}
                </span>

              </div>


              {/* ADMISSION DETAILS */}

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">

                <InfoBox
                  label="Patient ID"
                  value={selectedAdmission.patient_id}
                />

                <InfoBox
                  label="Department"
                  value={
                    `${selectedAdmission.department_name} (${selectedAdmission.department_code})`
                  }
                />

                <InfoBox
                  label="Admission Type"
                  value={
                    selectedAdmission.admission_type
                  }
                />

                <InfoBox
                  label="Admission Time"
                  value={
                    formatDate(
                      selectedAdmission.admission_time
                    )
                  }
                />

              </div>


              {/* BED WARNING */}

              {!selectedAdmission.has_bed && (

                <div className="mt-6 p-5 rounded-lg bg-amber-50 border border-amber-200">

                  <p className="font-semibold text-amber-800">
                    Room/Bed assignment required
                  </p>

                  <p className="text-sm text-amber-700 mt-1">
                    This patient must be assigned a room and
                    bed before a doctor or nurse can be assigned.
                  </p>

                  <button
                    onClick={handleGoToBedManagement}
                    className="mt-4 px-4 py-2 rounded-lg bg-amber-600 text-white text-sm font-medium hover:bg-amber-700"
                  >
                    Go to Bed Management
                  </button>

                </div>

              )}

            </section>

          )}


          {/* ================================================= */}
          {/* STAFF SECTION */}
          {/* ================================================= */}

          {selectedAdmission &&
            selectedAdmission.has_bed && (

            <section className="mt-6 bg-white rounded-xl border border-slate-200 p-6">

              {/* STAFF TYPE */}

              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">

                <div>

                  <h2 className="text-lg font-semibold text-slate-800">
                    Available Staff
                  </h2>

                  <p className="text-sm text-slate-500 mt-1">
                    Department:
                    {" "}
                    <span className="font-medium">
                      {selectedAdmission.department_name}
                    </span>
                  </p>

                </div>


                <div className="flex rounded-lg bg-slate-100 p-1">

                  <button
                    onClick={() => {
                      setStaffType("DOCTORS")
                      setSearchText("")
                      setSpeciality("")
                    }}
                    className={`px-5 py-2 rounded-md text-sm font-medium ${
                      staffType === "DOCTORS"
                        ? "bg-white shadow text-blue-600"
                        : "text-slate-600"
                    }`}
                  >
                    Doctors
                  </button>

                  <button
                    onClick={() => {
                      setStaffType("NURSES")
                      setSearchText("")
                      setSpeciality("")
                    }}
                    className={`px-5 py-2 rounded-md text-sm font-medium ${
                      staffType === "NURSES"
                        ? "bg-white shadow text-blue-600"
                        : "text-slate-600"
                    }`}
                  >
                    Nurses
                  </button>

                </div>

              </div>


              {/* FILTERS */}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">

                {staffType === "DOCTORS" && (

                  <div>

                    <label className="block text-xs font-medium text-slate-500 mb-2">
                      Specialty
                    </label>

                    <select
                      value={speciality}
                      onChange={(e) =>
                        setSpeciality(e.target.value)
                      }
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    >

                      <option value="">
                        All Specialties
                      </option>

                      {specialities.map((value) => (

                        <option
                          key={value}
                          value={value}
                        >
                          {value}
                        </option>

                      ))}

                    </select>

                  </div>

                )}


                <div>

                  <label className="block text-xs font-medium text-slate-500 mb-2">
                    Search
                  </label>

                  <input
                    type="text"
                    value={searchText}
                    onChange={(e) =>
                      setSearchText(e.target.value)
                    }
                    placeholder={
                      staffType === "DOCTORS"
                        ? "Search doctor..."
                        : "Search nurse..."
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />

                </div>


                <div>

                  <label className="block text-xs font-medium text-slate-500 mb-2">
                    Shift
                  </label>

                  <select
                    value={shiftType}
                    onChange={(e) =>
                      setShiftType(e.target.value)
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >

                    <option value="">
                      All Shifts
                    </option>

                    <option value="MORNING">
                      Morning
                    </option>

                    <option value="AFTERNOON">
                      Afternoon
                    </option>

                    <option value="EVENING">
                      Evening
                    </option>

                    <option value="NIGHT">
                      Night
                    </option>

                  </select>

                </div>

              </div>


              {/* STAFF TABLE */}

              {loadingStaff ? (

                <div className="py-10 text-center text-slate-500">
                  Loading available staff...
                </div>

              ) : staffType === "DOCTORS" ? (

                <DoctorTable
                  doctors={filteredDoctors}
                  assigningId={assigningId}
                  onAssign={handleAssignDoctor}
                />

              ) : (

                <NurseTable
                  nurses={filteredNurses}
                  assigningId={assigningId}
                  onAssign={handleAssignNurse}
                />

              )}

            </section>

          )}

        </main>

      </div>

    </div>

  )
}


// =========================================================
// DOCTOR TABLE
// =========================================================

function DoctorTable({
  doctors,
  assigningId,
  onAssign,
}) {

  if (doctors.length === 0) {

    return (
      <div className="py-10 text-center text-slate-500">
        No available doctors match the selected filters.
      </div>
    )

  }

  return (

    <div className="mt-6 overflow-x-auto">

      <table className="w-full text-sm">

        <thead>

          <tr className="border-b border-slate-200 text-left">

            <th className="pb-3 font-medium text-slate-500">
              ID
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Doctor
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Specialty
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Department
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Shift
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Schedule
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Status
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Action
            </th>

          </tr>

        </thead>


        <tbody>

          {doctors.map((doctor) => {

            const assigning =
              assigningId ===
              `DOCTOR-${doctor.doctor_id}`

            return (

              <tr
                key={`${doctor.doctor_id}-${doctor.schedule_id}`}
                className="border-b border-slate-100"
              >

                <td className="py-4 font-medium">
                  {doctor.doctor_id}
                </td>

                <td className="py-4 font-medium text-slate-700">
                  {doctor.doctor_name}
                </td>

                <td className="py-4 text-slate-600">
                  {doctor.speciality}
                </td>

                <td className="py-4">

                  <p className="text-slate-700">
                    {doctor.department_name}
                  </p>

                  <p className="text-xs text-slate-500">
                    ID {doctor.department_id}
                  </p>

                </td>

                <td className="py-4 text-slate-600">
                  {doctor.shift_type}
                </td>

                <td className="py-4 text-slate-600">

                  <p>
                    {doctor.start_time}
                    {" - "}
                    {doctor.end_time}
                  </p>

                </td>

                <td className="py-4">

                  <span className="px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                    {doctor.schedule_status}
                  </span>

                </td>

                <td className="py-4">

                  <button
                    onClick={() =>
                      onAssign(doctor)
                    }
                    disabled={assigning}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    {assigning
                      ? "Assigning..."
                      : "Assign"}
                  </button>

                </td>

              </tr>

            )

          })}

        </tbody>

      </table>

    </div>

  )
}


// =========================================================
// NURSE TABLE
// =========================================================

function NurseTable({
  nurses,
  assigningId,
  onAssign,
}) {

  if (nurses.length === 0) {

    return (
      <div className="py-10 text-center text-slate-500">
        No available nurses match the selected filters.
      </div>
    )

  }

  return (

    <div className="mt-6 overflow-x-auto">

      <table className="w-full text-sm">

        <thead>

          <tr className="border-b border-slate-200 text-left">

            <th className="pb-3 font-medium text-slate-500">
              ID
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Nurse
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Department
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Shift
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Schedule
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Status
            </th>

            <th className="pb-3 font-medium text-slate-500">
              Action
            </th>

          </tr>

        </thead>


        <tbody>

          {nurses.map((nurse) => {

            const assigning =
              assigningId ===
              `NURSE-${nurse.nurse_id}`

            return (

              <tr
                key={`${nurse.nurse_id}-${nurse.schedule_id}`}
                className="border-b border-slate-100"
              >

                <td className="py-4 font-medium">
                  {nurse.nurse_id}
                </td>

                <td className="py-4 font-medium text-slate-700">
                  {nurse.nurse_name}
                </td>

                <td className="py-4">

                  <p className="text-slate-700">
                    {nurse.department_name}
                  </p>

                  <p className="text-xs text-slate-500">
                    ID {nurse.department_id}
                  </p>

                </td>

                <td className="py-4 text-slate-600">
                  {nurse.shift_type}
                </td>

                <td className="py-4 text-slate-600">
                  {nurse.start_time}
                  {" - "}
                  {nurse.end_time}
                </td>

                <td className="py-4">

                  <span className="px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                    {nurse.schedule_status}
                  </span>

                </td>

                <td className="py-4">

                  <button
                    onClick={() =>
                      onAssign(nurse)
                    }
                    disabled={assigning}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    {assigning
                      ? "Assigning..."
                      : "Assign"}
                  </button>

                </td>

              </tr>

            )

          })}

        </tbody>

      </table>

    </div>

  )
}


// =========================================================
// INFO BOX
// =========================================================

function InfoBox({
  label,
  value,
}) {

  return (

    <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">

      <p className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="text-sm font-semibold text-slate-800 mt-2 break-all">
        {value || "N/A"}
      </p>

    </div>

  )
}


export default StaffManagement  