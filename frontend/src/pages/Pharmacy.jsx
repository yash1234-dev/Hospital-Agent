import { useEffect, useMemo, useState } from "react"
import NotificationButton from "../components/NotificationButton"
import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import {
  getMedications,
  getMedicationRequests,
  processMedicationRequest,
} from "../services/api"

function Pharmacy() {
  const [medications, setMedications] = useState([])
  const [requests, setRequests] = useState([])

  const [medicationSearch, setMedicationSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("ALL")
  const [priorityFilter, setPriorityFilter] = useState("ALL")

  const [loading, setLoading] = useState(true)
  const [processingRequestId, setProcessingRequestId] = useState(null)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [workflowResult, setWorkflowResult] = useState(null)
  const [selectedRequestId, setSelectedRequestId] = useState(null)

  const loadPharmacyData = async () => {
    setLoading(true)
    setError("")

    try {
      const [medicationData, requestData] = await Promise.all([
        getMedications({ limit: 100 }),
        getMedicationRequests({ limit: 100 }),
      ])

      setMedications(
        medicationData.medications || medicationData.results || []
      )
      setRequests(requestData.requests || requestData.results || [])
    } catch (err) {
      setError(err.message || "Failed to load pharmacy data.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPharmacyData()
  }, [])

  const filteredMedications = useMemo(() => {
    const search = medicationSearch.trim().toLowerCase()

    return medications.filter((medication) => {
      const matchesSearch =
        !search ||
        String(medication.medication_name || "")
          .toLowerCase()
          .includes(search) ||
        String(medication.medication_code || "")
          .toLowerCase()
          .includes(search)

      const matchesStatus =
        statusFilter === "ALL" || medication.status === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [medications, medicationSearch, statusFilter])

  const filteredRequests = useMemo(() => {
    return requests.filter(
      (request) =>
        priorityFilter === "ALL" || request.priority === priorityFilter
    )
  }, [requests, priorityFilter])

  const stats = useMemo(() => {
    return {
      totalMedications: medications.length,
      lowStock: medications.filter(
        (item) => item.status === "LOW_STOCK"
      ).length,
      outOfStock: medications.filter(
        (item) => item.status === "OUT_OF_STOCK"
      ).length,
      pendingRequests: requests.filter(
        (item) => item.status === "REQUESTED"
      ).length,
    }
  }, [medications, requests])

  const selectedRequest = useMemo(() => {
    return requests.find(
      (request) => request.request_id === selectedRequestId
    )
  }, [requests, selectedRequestId])

  const handleProcessRequest = async (requestId) => {
    setSelectedRequestId(requestId)
    setProcessingRequestId(requestId)
    setError("")
    setSuccess("")
    setWorkflowResult(null)

    try {
      const result = await processMedicationRequest(requestId)

      setWorkflowResult(result)
      setSuccess(`Medication request #${requestId} was processed successfully.`)

      await loadPharmacyData()
    } catch (err) {
      setError(
        err.message || `Failed to process medication request #${requestId}.`
      )
    } finally {
      setProcessingRequestId(null)
    }
  }

  const getStatusClass = (status) => {
    switch (status) {
      case "AVAILABLE":
        return "bg-emerald-50 text-emerald-700 border-emerald-200"
      case "LOW_STOCK":
        return "bg-amber-50 text-amber-700 border-amber-200"
      case "OUT_OF_STOCK":
      case "EXPIRED":
        return "bg-red-50 text-red-700 border-red-200"
      case "DISCONTINUED":
        return "bg-slate-100 text-slate-600 border-slate-200"
      default:
        return "bg-slate-100 text-slate-700 border-slate-200"
    }
  }

  const getPriorityClass = (priority) => {
    switch (priority) {
      case "STAT":
        return "bg-red-50 text-red-700 border-red-200"
      case "URGENT":
        return "bg-orange-50 text-orange-700 border-orange-200"
      case "ROUTINE":
        return "bg-blue-50 text-blue-700 border-blue-200"
      default:
        return "bg-slate-100 text-slate-700 border-slate-200"
    }
  }

  const getRequestStatusClass = (status) => {
    switch (status) {
      case "REQUESTED":
        return "bg-amber-50 text-amber-700 border-amber-200"
      case "APPROVED":
        return "bg-blue-50 text-blue-700 border-blue-200"
      case "DISPENSED":
      case "ADMINISTERED":
        return "bg-emerald-50 text-emerald-700 border-emerald-200"
      case "REJECTED":
        return "bg-red-50 text-red-700 border-red-200"
      case "CANCELLED":
        return "bg-slate-100 text-slate-600 border-slate-200"
      default:
        return "bg-slate-100 text-slate-700 border-slate-200"
    }
  }

  return (
    <div className="min-h-screen bg-[#f6f8fb] flex text-slate-800">
      <Sidebar />

      <div className="flex-1 min-w-0">
        <Header />

        <main className="p-4 sm:p-6 xl:p-8 space-y-6 max-w-[1800px] mx-auto">
          {/* =====================================================
              PAGE HEADER
          ====================================================== */}
          <section className="relative overflow-hidden rounded-2xl bg-slate-950 text-white shadow-sm">
            <div className="absolute inset-0 bg-linear-to-br from-indigo-950 via-slate-950 to-emerald-950 opacity-90" />

            <div className="relative px-6 py-7 lg:px-8 lg:py-8">
              <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-6">
                <div>
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-11 h-11 rounded-xl bg-white/10 border border-white/10 flex items-center justify-center text-xl">
                      💊
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-emerald-300 font-semibold">
                        Hospital Pharmacy
                      </p>
                      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
                        Pharmacy Management
                      </h1>
                    </div>
                  </div>

                  <p className="text-sm sm:text-base text-slate-300 max-w-2xl">
                    Monitor medication inventory and process medication
                    requests through the Pharmacy AI Agent and Action Gateway.
                  </p>
                </div>

                <button
                  onClick={loadPharmacyData}
                  disabled={loading}
                  className="self-start xl:self-center px-4 py-2.5 rounded-xl bg-white/10 border border-white/15 text-sm font-semibold text-white hover:bg-white/15 transition disabled:opacity-50"
                >
                  {loading ? "Refreshing..." : "↻ Refresh Data"}
                </button>
              </div>
            </div>
          </section>

          {/* =====================================================
              ALERTS
          ====================================================== */}
          {error && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
              <span className="text-base">!</span>
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-700">
              <span className="text-base">✓</span>
              <span>{success}</span>
            </div>
          )}

          {/* =====================================================
              KPI STRIP
          ====================================================== */}
          <section className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard
              title="Medications"
              value={stats.totalMedications}
              description="Inventory items"
              icon="💊"
              accent="indigo"
            />

            <StatCard
              title="Low Stock"
              value={stats.lowStock}
              description="Needs monitoring"
              icon="⚠"
              accent="amber"
            />

            <StatCard
              title="Out of Stock"
              value={stats.outOfStock}
              description="Currently unavailable"
              icon="!"
              accent="red"
            />

            <StatCard
              title="Pending Requests"
              value={stats.pendingRequests}
              description="Awaiting AI processing"
              icon="⌁"
              accent="emerald"
            />
          </section>

          {/* =====================================================
              PRIMARY WORKSPACE
              Requests + AI panel are intentionally together.
          ====================================================== */}
          <section className="grid grid-cols-1 2xl:grid-cols-[minmax(0,1.65fr)_minmax(380px,0.9fr)] gap-6 items-start">
            {/* REQUEST QUEUE */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-5 border-b border-slate-200">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-bold text-slate-900">
                        Medication Request Queue
                      </h2>

                      <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold">
                        {filteredRequests.length}
                      </span>
                    </div>

                    <p className="text-sm text-slate-500 mt-1">
                      Select a pending request and run the AI pharmacy workflow.
                    </p>
                  </div>

                  <select
                    value={priorityFilter}
                    onChange={(event) =>
                      setPriorityFilter(event.target.value)
                    }
                    className="w-full sm:w-44 px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="ALL">All Priorities</option>
                    <option value="STAT">STAT</option>
                    <option value="URGENT">URGENT</option>
                    <option value="ROUTINE">ROUTINE</option>
                  </select>
                </div>
              </div>

              {loading ? (
                <LoadingState text="Loading medication requests..." />
              ) : filteredRequests.length === 0 ? (
                <EmptyState text="No medication requests found." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50/80">
                      <tr className="border-b border-slate-200 text-left">
                        <th className="px-5 py-3 font-semibold text-slate-500">
                          Request
                        </th>
                        <th className="px-5 py-3 font-semibold text-slate-500">
                          Patient
                        </th>
                        <th className="px-5 py-3 font-semibold text-slate-500">
                          Medication
                        </th>
                        <th className="px-5 py-3 font-semibold text-slate-500">
                          Qty
                        </th>
                        <th className="px-5 py-3 font-semibold text-slate-500">
                          Priority
                        </th>
                        <th className="px-5 py-3 font-semibold text-slate-500">
                          Status
                        </th>
                        <th className="px-5 py-3 text-right font-semibold text-slate-500">
                          Action
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {filteredRequests.map((request) => {
                        const canProcess = request.status === "REQUESTED"
                        const isProcessing =
                          processingRequestId === request.request_id
                        const isSelected =
                          selectedRequestId === request.request_id

                        return (
                          <tr
                            key={request.request_id}
                            className={`border-b border-slate-100 transition ${
                              isSelected
                                ? "bg-indigo-50/60"
                                : "hover:bg-slate-50/70"
                            }`}
                          >
                            <td className="px-5 py-4">
                              <div className="flex items-center gap-2">
                                {isSelected && (
                                  <span className="w-1.5 h-7 rounded-full bg-indigo-600" />
                                )}
                                <div>
                                  <p className="font-bold text-slate-900">
                                    #{request.request_id}
                                  </p>
                                  <p className="text-[11px] text-slate-400 mt-0.5">
                                    Doctor #{request.doctor_id ?? "N/A"}
                                  </p>
                                </div>
                              </div>
                            </td>

                            <td className="px-5 py-4">
                              <p
                                className="font-medium text-slate-700 max-w-45 truncate"
                                title={request.patient_id || "N/A"}
                              >
                                {request.patient_id || "N/A"}
                              </p>
                            </td>

                            <td className="px-5 py-4">
                              <p className="font-medium text-slate-800">
                                {request.medication_name ||
                                  `Inventory #${request.medication_inventory_id}`}
                              </p>
                              <p className="text-xs text-slate-400 mt-0.5">
                                Inventory #{request.medication_inventory_id}
                              </p>
                            </td>

                            <td className="px-5 py-4 font-bold text-slate-800">
                              {request.requested_quantity ?? 0}
                            </td>

                            <td className="px-5 py-4">
                              <span
                                className={`inline-flex px-2.5 py-1 rounded-full border text-[11px] font-bold ${getPriorityClass(
                                  request.priority
                                )}`}
                              >
                                {request.priority || "N/A"}
                              </span>
                            </td>

                            <td className="px-5 py-4">
                              <span
                                className={`inline-flex px-2.5 py-1 rounded-full border text-[11px] font-bold ${getRequestStatusClass(
                                  request.status
                                )}`}
                              >
                                {request.status || "N/A"}
                              </span>
                            </td>

                            <td className="px-5 py-4 text-right">
                              {canProcess ? (
                                <button
                                  onClick={() =>
                                    handleProcessRequest(request.request_id)
                                  }
                                  disabled={isProcessing}
                                  className="inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-950 text-white text-xs font-bold hover:bg-indigo-700 transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                  <span>{isProcessing ? "◌" : "✦"}</span>
                                  {isProcessing
                                    ? "Processing..."
                                    : "Process with AI"}
                                </button>
                              ) : (
                                <span className="text-xs text-slate-400">
                                  No action
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* AI CONTROL / RESULT PANEL */}
            <div className="2xl:sticky 2xl:top-6 space-y-4">
              <div className="rounded-2xl overflow-hidden bg-slate-950 text-white shadow-lg">
                <div className="px-5 py-5 bg-linear-to-br from-indigo-950 via-slate-950 to-emerald-950">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="text-xs uppercase tracking-[0.16em] text-emerald-300 font-bold">
                          AI Pharmacy Agent
                        </span>
                      </div>

                      <h2 className="text-xl font-bold">
                        {workflowResult
                          ? "Workflow Completed"
                          : "Ready to Process"}
                      </h2>

                      <p className="text-sm text-slate-300 mt-1">
                        {workflowResult
                          ? "Execution summary and actions performed."
                          : "Choose a medication request from the queue."}
                      </p>
                    </div>

                    <div className="w-10 h-10 rounded-xl bg-white/10 border border-white/10 flex items-center justify-center text-lg">
                      ✦
                    </div>
                  </div>
                </div>

                <div className="p-5">
                  {workflowResult ? (
                    <WorkflowResult
                      workflowResult={workflowResult}
                      selectedRequest={selectedRequest}
                      getRequestStatusClass={getRequestStatusClass}
                    />
                  ) : (
                    <EmptyWorkflowState />
                  )}
                </div>
              </div>

              {/* Workflow pipeline */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      AI Workflow
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      State-changing operations use the Action Gateway.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <WorkflowStep
                    number="01"
                    title="Validate"
                    description="Check request state, patient and medication stock."
                    active={workflowResult}
                  />
                  <WorkflowStep
                    number="02"
                    title="Approve"
                    description="Create and execute the approval gateway action."
                    active={workflowResult}
                  />
                  <WorkflowStep
                    number="03"
                    title="Dispense"
                    description="Deduct inventory and complete the request."
                    active={workflowResult}
                  />
                </div>
              </div>
            </div>
             {/* Email Notification */}
              {workflowResult?.status === "SUCCESS" && (
  <NotificationButton
    eventType="MEDICATION_DISPENSED"
    priority="NORMAL"
    patientId={workflowResult.context?.patient_id || null}
    admissionId={workflowResult.context?.admission_id || null}
    title="Medication Dispensed"
    message={`Medication request ${
      workflowResult.context?.request_id
        ? `#${workflowResult.context.request_id}`
        : ""
    } has been successfully processed and the medication has been dispensed.`}
    sourceAgent="PharmacyAgent"
  />
)}
          </section>

          {/* =====================================================
              INVENTORY
          ====================================================== */}
          <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-5 border-b border-slate-200">
              <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-900">
                      Medication Inventory
                    </h2>

                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold">
                      {filteredMedications.length}
                    </span>
                  </div>

                  <p className="text-sm text-slate-500 mt-1">
                    Current stock, reorder thresholds and medication status.
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                      ⌕
                    </span>
                    <input
                      type="text"
                      value={medicationSearch}
                      onChange={(event) =>
                        setMedicationSearch(event.target.value)
                      }
                      placeholder="Search medication or code..."
                      className="w-full sm:w-72 pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
                    />
                  </div>

                  <select
                    value={statusFilter}
                    onChange={(event) => setStatusFilter(event.target.value)}
                    className="px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="ALL">All Status</option>
                    <option value="AVAILABLE">Available</option>
                    <option value="LOW_STOCK">Low Stock</option>
                    <option value="OUT_OF_STOCK">Out of Stock</option>
                    <option value="EXPIRED">Expired</option>
                    <option value="DISCONTINUED">Discontinued</option>
                  </select>
                </div>
              </div>
            </div>

            {loading ? (
              <LoadingState text="Loading medication inventory..." />
            ) : filteredMedications.length === 0 ? (
              <EmptyState text="No medications match the selected filters." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50/80">
                    <tr className="border-b border-slate-200 text-left">
                      <th className="px-5 py-3 font-semibold text-slate-500">
                        Code
                      </th>
                      <th className="px-5 py-3 font-semibold text-slate-500">
                        Medication
                      </th>
                      <th className="px-5 py-3 font-semibold text-slate-500">
                        Category
                      </th>
                      <th className="px-5 py-3 font-semibold text-slate-500">
                        Stock
                      </th>
                      <th className="px-5 py-3 font-semibold text-slate-500">
                        Reorder Level
                      </th>
                      <th className="px-5 py-3 font-semibold text-slate-500">
                        Status
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredMedications.map((medication) => (
                      <tr
                        key={medication.medication_inventory_id}
                        className="border-b border-slate-100 hover:bg-slate-50/70 transition"
                      >
                        <td className="px-5 py-4 font-mono text-xs text-slate-500">
                          {medication.medication_code || "N/A"}
                        </td>

                        <td className="px-5 py-4">
                          <p className="font-semibold text-slate-800">
                            {medication.medication_name || "N/A"}
                          </p>
                        </td>

                        <td className="px-5 py-4 text-slate-600">
                          {medication.category || "N/A"}
                        </td>

                        <td className="px-5 py-4">
                          <span className="font-bold text-slate-800">
                            {medication.quantity_on_hand ?? 0}
                          </span>
                          <span className="text-slate-400 ml-1">
                            {medication.unit || ""}
                          </span>
                        </td>

                        <td className="px-5 py-4 text-slate-600">
                          {medication.reorder_level ?? "N/A"}
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={`inline-flex px-2.5 py-1 rounded-full border text-[11px] font-bold ${getStatusClass(
                              medication.status
                            )}`}
                          >
                            {medication.status || "UNKNOWN"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  )
}

function WorkflowResult({
  workflowResult,
  selectedRequest,
  getRequestStatusClass,
}) {
  const actions =
    workflowResult.actions || workflowResult.context?.actions || []

  const patientId =
    workflowResult.context?.patient_id ||
    workflowResult.data?.medication_request?.patient_id ||
    selectedRequest?.patient_id ||
    "N/A"

  const admissionId =
    workflowResult.context?.admission_id ||
    workflowResult.data?.medication_request?.admission_id ||
    selectedRequest?.admission_id ||
    "N/A"

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3">
        <ResultMetric
          label="Decision"
          value={workflowResult.decision || "N/A"}
          highlight
        />

        <ResultMetric
          label="Request"
          value={
            selectedRequest?.request_id
              ? `#${selectedRequest.request_id}`
              : "N/A"
          }
        />

        <ResultMetric
          label="Patient"
          value={patientId}
        />

        <ResultMetric
          label="Admission"
          value={admissionId}
        />
      </div>

      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
        <p className="text-[10px] uppercase tracking-[0.16em] text-slate-400 font-bold">
          Result
        </p>

        <div className="flex items-center justify-between gap-3 mt-2">
          <span className="text-sm font-semibold text-white">
            {workflowResult.reason || "Workflow completed."}
          </span>

          <span className="shrink-0 px-2.5 py-1 rounded-full bg-emerald-400/10 text-emerald-300 border border-emerald-400/20 text-[10px] font-bold">
            {workflowResult.status || "SUCCESS"}
          </span>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-white">
            Actions Performed
          </h3>

          <span className="text-xs text-slate-400">
            {actions.length} action{actions.length === 1 ? "" : "s"}
          </span>
        </div>

        <div className="space-y-2">
          {actions.length > 0 ? (
            actions.map((action, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
              >
                <div className="w-7 h-7 rounded-lg bg-emerald-400/10 text-emerald-300 flex items-center justify-center text-xs font-bold">
                  ✓
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-slate-200 truncate">
                    {action.action || "Action"}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    PharmacyAgent
                  </p>
                </div>

                <span className="text-[10px] font-bold text-emerald-300">
                  {action.status || "COMPLETED"}
                </span>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400">
              No state-changing actions were performed.
            </p>
          )}
        </div>
      </div>

      {selectedRequest?.status && (
        <div className="pt-1 flex items-center justify-between">
          <span className="text-xs text-slate-400">Current request state</span>
          <span
            className={`px-2.5 py-1 rounded-full border text-[10px] font-bold ${getRequestStatusClass(
              selectedRequest.status
            )}`}
          >
            {selectedRequest.status}
          </span>
        </div>
      )}
    </div>
  )
}

function EmptyWorkflowState() {
  return (
    <div className="py-5">
      <div className="w-14 h-14 rounded-2xl bg-white/10 border border-white/10 flex items-center justify-center text-2xl mb-5">
        ✦
      </div>

      <h3 className="text-base font-bold text-white">
        No request selected
      </h3>

      <p className="text-sm text-slate-400 mt-2 leading-6">
        Choose a request from the queue and click{" "}
        <span className="text-slate-200 font-semibold">Process with AI</span>.
        The execution result will appear here without requiring you to scroll
        through the page.
      </p>

      <div className="mt-5 p-3.5 rounded-xl bg-white/5 border border-white/10">
        <p className="text-[11px] text-slate-400 leading-5">
          The workflow validates the request, approves the medication and
          dispenses it through the Action Gateway.
        </p>
      </div>
    </div>
  )
}

function StatCard({ title, value, description, icon, accent }) {
  const accents = {
    indigo: "bg-indigo-50 text-indigo-600 border-indigo-100",
    amber: "bg-amber-50 text-amber-600 border-amber-100",
    red: "bg-red-50 text-red-600 border-red-100",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-100",
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide font-semibold text-slate-400">
            {title}
          </p>

          <p className="text-2xl font-bold text-slate-900 mt-2">
            {value}
          </p>

          <p className="text-xs text-slate-500 mt-1">
            {description}
          </p>
        </div>

        <div
          className={`w-10 h-10 rounded-xl border flex items-center justify-center text-sm font-bold ${
            accents[accent] || accents.indigo
          }`}
        >
          {icon}
        </div>
      </div>
    </div>
  )
}

function ResultMetric({ label, value, highlight = false }) {
  return (
    <div
      className={`rounded-xl border p-3.5 ${
        highlight
          ? "bg-indigo-500/10 border-indigo-400/20"
          : "bg-white/5 border-white/10"
      }`}
    >
      <p className="text-[9px] uppercase tracking-[0.14em] text-slate-400 font-bold">
        {label}
      </p>

      <p
        className={`text-xs font-bold mt-1.5 break-all ${
          highlight ? "text-indigo-200" : "text-slate-200"
        }`}
      >
        {value}
      </p>
    </div>
  )
}

function WorkflowStep({ number, title, description, active }) {
  return (
    <div className="flex items-start gap-3">
      <div
        className={`w-8 h-8 shrink-0 rounded-lg flex items-center justify-center text-[10px] font-bold ${
          active
            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
            : "bg-slate-100 text-slate-500 border border-slate-200"
        }`}
      >
        {active ? "✓" : number}
      </div>

      <div className="min-w-0">
        <p className="text-xs font-bold text-slate-800">{title}</p>
        <p className="text-[11px] text-slate-500 leading-5 mt-0.5">
          {description}
        </p>
      </div>
    </div>
  )
}

function LoadingState({ text }) {
  return (
    <div className="py-14 text-center">
      <div className="w-10 h-10 mx-auto rounded-xl bg-slate-100 flex items-center justify-center mb-3 animate-pulse">
        ⚙
      </div>
      <p className="text-sm text-slate-500">{text}</p>
    </div>
  )
}

function EmptyState({ text }) {
  return (
    <div className="py-14 text-center">
      <div className="text-2xl mb-2">⌁</div>
      <p className="text-sm text-slate-500">{text}</p>
    </div>
  )
}

export default Pharmacy
