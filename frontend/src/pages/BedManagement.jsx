import { useEffect, useState } from "react"

import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import NotificationButton from "../components/NotificationButton"
import {
  getAvailableBeds,
  getEligibleAdmissions,
  reserveBed,
} from "../services/api"


function BedManagement() {
  // =========================================================
  // STATE
  // =========================================================

  const [beds, setBeds] = useState([])
  const [admissions, setAdmissions] = useState([])

  const [selectedAdmission, setSelectedAdmission] = useState("")

  const [loadingBeds, setLoadingBeds] = useState(true)
  const [loadingAdmissions, setLoadingAdmissions] = useState(true)

  const [reservingBedId, setReservingBedId] = useState(null)

  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [notificationData, setNotificationData] = useState(null)

  const [bedType, setBedType] = useState("")
  const [roomType, setRoomType] = useState("")
  const [departmentId, setDepartmentId] = useState("")


  // =========================================================
  // LOAD AVAILABLE BEDS
  // =========================================================

  async function loadBeds(filters = {}) {
    try {
      setLoadingBeds(true)
      setError("")

      const data = await getAvailableBeds(filters)

      setBeds(data.beds || [])
    } catch (err) {
      setError(err.message || "Failed to load available beds.")
    } finally {
      setLoadingBeds(false)
    }
  }


  // =========================================================
  // LOAD ELIGIBLE ADMISSIONS
  // =========================================================

  async function loadAdmissions() {
    try {
      setLoadingAdmissions(true)

      const data = await getEligibleAdmissions()

      setAdmissions(data.admissions || [])
    } catch (err) {
      setError(
        err.message || "Failed to load eligible admissions."
      )
    } finally {
      setLoadingAdmissions(false)
    }
  }


  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {
    loadBeds()
    loadAdmissions()
  }, [])


  // =========================================================
  // FILTER
  // =========================================================

  function handleApplyFilters() {
    loadBeds({
      bedType,
      roomType,
      departmentId,
    })
  }


  function handleClearFilters() {
    setBedType("")
    setRoomType("")
    setDepartmentId("")

    loadBeds({
      bedType: "",
      roomType: "",
      departmentId: "",
    })
  }


  // =========================================================
  // RESERVE BED
  // =========================================================

  async function handleReserveBed(bed) {
    setError("")
    setSuccess("")

    if (!selectedAdmission) {
      setError(
        "Please select an eligible admission before reserving a bed."
      )
      return
    }

    const admission = admissions.find(
      (item) =>
        String(item.admission_id) === String(selectedAdmission)
    )

    if (!admission) {
      setError("Selected admission could not be found.")
      return
    }

    const confirmed = window.confirm(
      `Reserve Bed ${bed.bed_id} for Admission ${admission.admission_id}?`
    )

    if (!confirmed) {
      return
    }

    try {
      setReservingBedId(bed.bed_id)

      const result = await reserveBed({
        bedId: bed.bed_id,
        patientId: admission.patient_id,
        admissionId: admission.admission_id,
      })

      if (result.status !== "SUCCESS") {
        throw new Error(
          result.message || "Bed reservation failed."
        )
      }

      setSuccess(
        `Bed ${bed.bed_id} reserved successfully for Admission ${admission.admission_id}.`
      )
      setNotificationData({
  patientId: admission.patient_id,
  admissionId: admission.admission_id,
  bedId: bed.bed_id,
})

      // Refresh both lists because this reservation changes
      // the eligible-admission and available-bed state.
      await Promise.all([
        loadBeds({
          bedType,
          roomType,
          departmentId,
        }),
        loadAdmissions(),
      ])

      // Clear selected admission after successful reservation.
      setSelectedAdmission("")

    } catch (err) {
      setError(
        err.message || "Failed to reserve bed."
      )
    } finally {
      setReservingBedId(null)
    }
  }


  // =========================================================
  // COUNTS
  // =========================================================

  const availableBedsCount = beds.length

  const icuBedsCount = beds.filter(
    (bed) => bed.bed_type === "ICU"
  ).length

  const emergencyBedsCount = beds.filter(
    (bed) => bed.bed_type === "EMERGENCY"
  ).length


  // =========================================================
  // RENDER
  // =========================================================

  return (
    <div className="flex min-h-screen bg-slate-50">

      <Sidebar />

      <div className="min-w-0 flex-1">

        <Header />

        <main className="p-6">

          {/* =================================================
              PAGE HEADER
          ================================================= */}

          <div className="mb-6">

            <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
              Bed Management
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              Monitor available beds and reserve beds for
              eligible hospital admissions.
            </p>

          </div>


          {/* =================================================
              ALERTS
          ================================================= */}

          {error && (
            <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-5 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
              {success}
            </div>
          )}
          {notificationData && (
  <div className="mb-6">
    <NotificationButton
      eventType="BED_ASSIGNED"
      priority="NORMAL"
      patientId={notificationData.patientId}
      admissionId={notificationData.admissionId}
      title="Bed Assigned"
      message={`Bed #${notificationData.bedId} has been successfully assigned to Admission #${notificationData.admissionId}.`}
      sourceAgent="BedAgent"
    />
  </div>
)}


          {/* =================================================
              ADMISSION SELECTION
          ================================================= */}

          <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <div className="mb-3">

              <h2 className="text-lg font-semibold text-slate-800">
                Select Admission
              </h2>

              <p className="text-sm text-slate-500">
                Only admissions eligible for bed assignment
                are displayed.
              </p>

            </div>


            <select
              value={selectedAdmission}
              onChange={(e) =>
                setSelectedAdmission(e.target.value)
              }
              disabled={loadingAdmissions}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            >

              <option value="">
                {loadingAdmissions
                  ? "Loading eligible admissions..."
                  : "Select an admission"}
              </option>

              {admissions.map((admission) => (
                <option
                  key={admission.admission_id}
                  value={admission.admission_id}
                >
                  Admission #{admission.admission_id}
                  {" — "}
                  Patient {admission.patient_id}
                  {" — "}
                  {admission.department_name}
                </option>
              ))}

            </select>


            {selectedAdmission && (
              <div className="mt-3 rounded-lg bg-slate-50 p-3 text-sm">

                {(() => {

                  const admission = admissions.find(
                    (item) =>
                      String(item.admission_id) ===
                      String(selectedAdmission)
                  )

                  if (!admission) {
                    return null
                  }

                  return (
                    <div className="grid grid-cols-1 gap-2 md:grid-cols-4">

                      <div>
                        <span className="text-slate-500">
                          Admission
                        </span>

                        <p className="font-semibold text-slate-800">
                          #{admission.admission_id}
                        </p>
                      </div>


                      <div>
                        <span className="text-slate-500">
                          Patient
                        </span>

                        <p className="break-all font-semibold text-slate-800">
                          {admission.patient_id}
                        </p>
                      </div>


                      <div>
                        <span className="text-slate-500">
                          Department
                        </span>

                        <p className="font-semibold text-slate-800">
                          {admission.department_name}
                        </p>
                      </div>


                      <div>
                        <span className="text-slate-500">
                          Type
                        </span>

                        <p className="font-semibold text-slate-800">
                          {admission.admission_type}
                        </p>
                      </div>

                    </div>
                  )

                })()}

              </div>
            )}

          </div>


          {/* =================================================
              SUMMARY CARDS
          ================================================= */}

          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

              <p className="text-sm text-slate-500">
                Available Beds
              </p>

              <p className="mt-1 text-2xl font-bold text-slate-800">
                {availableBedsCount}
              </p>

            </div>


            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

              <p className="text-sm text-slate-500">
                Available ICU Beds
              </p>

              <p className="mt-1 text-2xl font-bold text-slate-800">
                {icuBedsCount}
              </p>

            </div>


            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

              <p className="text-sm text-slate-500">
                Emergency Beds
              </p>

              <p className="mt-1 text-2xl font-bold text-slate-800">
                {emergencyBedsCount}
              </p>

            </div>

          </div>


          {/* =================================================
              FILTERS
          ================================================= */}

          <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <h2 className="mb-4 text-lg font-semibold text-slate-800">
              Bed Filters
            </h2>


            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">

              {/* BED TYPE */}

              <div>

                <label className="mb-1 block text-sm font-medium text-slate-600">
                  Bed Type
                </label>

                <select
                  value={bedType}
                  onChange={(e) =>
                    setBedType(e.target.value)
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >

                  <option value="">
                    All Bed Types
                  </option>

                  <option value="STANDARD">
                    Standard
                  </option>

                  <option value="ICU">
                    ICU
                  </option>

                  <option value="EMERGENCY">
                    Emergency
                  </option>

                  <option value="PEDIATRIC">
                    Pediatric
                  </option>

                  <option value="MATERNITY">
                    Maternity
                  </option>

                </select>

              </div>


              {/* ROOM TYPE */}

              <div>

                <label className="mb-1 block text-sm font-medium text-slate-600">
                  Room Type
                </label>

                <select
                  value={roomType}
                  onChange={(e) =>
                    setRoomType(e.target.value)
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >

                  <option value="">
                    All Room Types
                  </option>

                  <option value="GENERAL">
                    General
                  </option>

                  <option value="ICU">
                    ICU
                  </option>

                  <option value="ISOLATION">
                    Isolation
                  </option>

                  <option value="EMERGENCY">
                    Emergency
                  </option>

                  <option value="OPERATING">
                    Operating
                  </option>

                  <option value="MATERNITY">
                    Maternity
                  </option>

                  <option value="PEDIATRIC">
                    Pediatric
                  </option>

                </select>

              </div>


              {/* DEPARTMENT */}

              <div>

                <label className="mb-1 block text-sm font-medium text-slate-600">
                  Department ID
                </label>

                <input
                  type="number"
                  min="1"
                  value={departmentId}
                  onChange={(e) =>
                    setDepartmentId(e.target.value)
                  }
                  placeholder="e.g. 3"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />

              </div>


              {/* BUTTONS */}

              <div className="flex items-end gap-2">

                <button
                  onClick={handleApplyFilters}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Apply
                </button>

                <button
                  onClick={handleClearFilters}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Clear
                </button>

              </div>

            </div>

          </div>


          {/* =================================================
              AVAILABLE BEDS TABLE
          ================================================= */}

          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">

            <div className="border-b border-slate-200 px-5 py-4">

              <h2 className="text-lg font-semibold text-slate-800">
                Available Beds
              </h2>

              <p className="text-sm text-slate-500">
                Select an admission above and reserve an
                available bed.
              </p>

            </div>


            {loadingBeds ? (

              <div className="p-8 text-center text-sm text-slate-500">
                Loading available beds...
              </div>

            ) : beds.length === 0 ? (

              <div className="p-8 text-center text-sm text-slate-500">
                No available beds found.
              </div>

            ) : (

              <div className="overflow-x-auto">

                <table className="w-full text-left text-sm">

                  <thead className="bg-slate-50 text-xs uppercase text-slate-500">

                    <tr>

                      <th className="px-5 py-3">
                        Bed
                      </th>

                      <th className="px-5 py-3">
                        Type
                      </th>

                      <th className="px-5 py-3">
                        Room
                      </th>

                      <th className="px-5 py-3">
                        Room Type
                      </th>

                      <th className="px-5 py-3">
                        Floor
                      </th>

                      <th className="px-5 py-3">
                        Department
                      </th>

                      <th className="px-5 py-3">
                        Status
                      </th>

                      <th className="px-5 py-3">
                        Action
                      </th>

                    </tr>

                  </thead>


                  <tbody className="divide-y divide-slate-100">

                    {beds.map((bed) => (

                      <tr
                        key={bed.bed_id}
                        className="hover:bg-slate-50"
                      >

                        <td className="px-5 py-4 font-semibold text-slate-800">
                          #{bed.bed_id}
                        </td>


                        <td className="px-5 py-4">
                          {bed.bed_type}
                        </td>


                        <td className="px-5 py-4">
                          {bed.room_number}
                        </td>


                        <td className="px-5 py-4">
                          {bed.room_type}
                        </td>


                        <td className="px-5 py-4">
                          {bed.floor_number}
                        </td>


                        <td className="px-5 py-4">

                          <div className="font-medium text-slate-700">
                            {bed.department_name}
                          </div>

                          <div className="text-xs text-slate-400">
                            {bed.department_code}
                          </div>

                        </td>


                        <td className="px-5 py-4">

                          <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
                            AVAILABLE
                          </span>

                        </td>


                        <td className="px-5 py-4">

                          <button
                            onClick={() =>
                              handleReserveBed(bed)
                            }
                            disabled={
                              !selectedAdmission ||
                              reservingBedId === bed.bed_id
                            }
                            className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                          >
                            {reservingBedId === bed.bed_id
                              ? "Reserving..."
                              : "Reserve"}
                          </button>

                        </td>

                      </tr>

                    ))}

                  </tbody>

                </table>

              </div>

            )}

          </div>

        </main>

      </div>

    </div>
  )
}


export default BedManagement