import { useMemo, useState } from "react"
import NotificationButton from "../components/NotificationButton"
import Sidebar from "../components/Sidebar"
import {
  getLabOrder,
  getLabResults,
  runLabAgent,
} from "../services/api"

function Diagnostics() {
  const [labOrderId, setLabOrderId] = useState("")
  const [labOrder, setLabOrder] = useState(null)
  const [labResults, setLabResults] = useState([])
  const [workflowResult, setWorkflowResult] = useState(null)

  const [resultFilter, setResultFilter] = useState("ALL")
  const [testFilter, setTestFilter] = useState("ALL")

  const [loading, setLoading] = useState(false)
  const [runningAgent, setRunningAgent] = useState(false)
  const [error, setError] = useState("")

  // =========================================================
  // LOAD LAB ORDER + RESULTS
  // =========================================================

  const handleSearch = async () => {
    if (!labOrderId) {
      setError("Enter a laboratory order number to continue.")
      return
    }

    setLoading(true)
    setError("")
    setWorkflowResult(null)
    setResultFilter("ALL")
    setTestFilter("ALL")

    try {
      const [orderData, resultsData] = await Promise.all([
        getLabOrder(labOrderId),
        getLabResults(labOrderId),
      ])

      // The API wraps the order inside { status, lab_order }.
      // Keep the page state focused on the actual laboratory order object.
      const order = orderData?.lab_order || orderData

      setLabOrder(order)
      setLabResults(resultsData.results || [])
    } catch (err) {
      setLabOrder(null)
      setLabResults([])
      setError(err.message || "Could not load laboratory information.")
    } finally {
      setLoading(false)
    }
  }

  const handleQuickOpen = (orderId) => {
    setLabOrderId(String(orderId))
  }

  // =========================================================
  // RUN LAB AGENT
  // =========================================================

  const handleRunAgent = async () => {
    if (!labOrderId) {
      setError("Load a laboratory order before running the AI review.")
      return
    }

    setRunningAgent(true)
    setError("")
    setWorkflowResult(null)

    try {
      const result = await runLabAgent({
        labOrderId: Number(labOrderId),
        patientId: labOrder?.patient_id || null,
        admissionId: null,
        departmentId: labOrder?.department_id || null,
      })

      setWorkflowResult(result)

      const resultsData = await getLabResults(labOrderId)
      setLabResults(resultsData.results || [])
    } catch (err) {
      setError(err.message || "Laboratory AI workflow failed.")
    } finally {
      setRunningAgent(false)
    }
  }

  // =========================================================
  // HELPERS
  // =========================================================

  const getLatestResult = () => {
    if (!labResults.length) return null
    return labResults[0]
  }

  const latestResult = getLatestResult()

  const testOptions = useMemo(() => {
    const names = [...new Set(
      labResults
        .map((result) => result.test_name)
        .filter(Boolean)
    )]

    return names.sort()
  }, [labResults])

  const filteredResults = useMemo(() => {
    return labResults.filter((result) => {
      const statusMatch =
        resultFilter === "ALL" ||
        result.result_status === resultFilter

      const testMatch =
        testFilter === "ALL" ||
        result.test_name === testFilter

      return statusMatch && testMatch
    })
  }, [labResults, resultFilter, testFilter])

  const formatResultValue = (result) => {
    if (result?.result_value === null || result?.result_value === undefined) {
      return "N/A"
    }

    const value = String(result.result_value).trim()
    const unit = String(result.unit || "").trim()

    if (!unit) return value

    // Some stored results already contain their unit.
    // Prevent UI output such as "83 mg/dL mg/dL".
    const escapedUnit = unit.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    const unitAtEnd = new RegExp(`\\s*${escapedUnit}\\s*$`, "i")

    return unitAtEnd.test(value) ? value : `${value} ${unit}`
  }

  const getFriendlyDecision = (decision) => {
    switch (decision) {
      case "ESCALATE_CRITICAL_LAB":
        return "Critical result requires escalation"
      case "ESCALATION_COMPLETED":
        return "Clinical escalation completed"
      case "REVIEW_ABNORMAL_LAB":
        return "Result needs clinical review"
      case "NO_ACTION":
        return "No immediate action required"
      case "WAIT_FOR_RESULT":
        return "Waiting for laboratory result"
      default:
        return decision || "Not available"
    }
  }

  const getStatusText = (status) => {
    if (status === "SUCCESS" || status === "COMPLETED") return "Completed successfully"
    if (status === "FAILED" || status === "ERROR") return "Workflow failed"
    return status || "Unknown"
  }

  const getStatusClass = (status) => {
    switch (status) {
      case "CRITICAL":
        return "bg-red-100 text-red-700 border-red-200"
      case "ABNORMAL":
        return "bg-orange-100 text-orange-700 border-orange-200"
      case "NORMAL":
        return "bg-green-100 text-green-700 border-green-200"
      case "PENDING":
        return "bg-yellow-100 text-yellow-700 border-yellow-200"
      default:
        return "bg-slate-100 text-slate-700 border-slate-200"
    }
  }

  const getFriendlyStatus = (status) => {
    switch (status) {
      case "CRITICAL":
        return "Needs urgent review"
      case "ABNORMAL":
        return "Outside normal range"
      case "NORMAL":
        return "Within normal range"
      case "PENDING":
        return "Awaiting result"
      default:
        return status || "Unknown"
    }
  }

  const getOrderStatusClass = (status) => {
    switch (status) {
      case "COMPLETED":
        return "bg-green-100 text-green-700 border-green-200"
      case "PROCESSING":
        return "bg-blue-100 text-blue-700 border-blue-200"
      case "COLLECTED":
        return "bg-purple-100 text-purple-700 border-purple-200"
      case "ORDERED":
        return "bg-yellow-100 text-yellow-700 border-yellow-200"
      case "CANCELLED":
        return "bg-slate-100 text-slate-600 border-slate-200"
      default:
        return "bg-slate-100 text-slate-700 border-slate-200"
    }
  }

  const statusCounts = useMemo(() => {
    return labResults.reduce(
      (counts, result) => {
        const status = result.result_status || "OTHER"
        counts[status] = (counts[status] || 0) + 1
        return counts
      },
      {}
    )
  }, [labResults])

  // =========================================================
  // UI
  // =========================================================

  return (
    <div className="min-h-screen bg-slate-100 flex">
      <Sidebar />

      <div className="flex-1 min-w-0">
        <main className="p-6 lg:p-8 space-y-6 bg-slate-50 min-h-screen">

      {/* =====================================================
          PAGE HEADER
      ===================================================== */}

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">

          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl">
              🧪
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
                  Diagnostics & Laboratory
                </h1>

                <span className="px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold border border-blue-100">
                  Clinical Monitoring
                </span>
              </div>

              <p className="text-sm text-slate-500 mt-2 max-w-3xl">
                Review laboratory tests, understand patient results, identify
                results that need attention, and use the AI workflow to
                escalate critical findings to the responsible doctor.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:min-w-0">
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-3">
              <p className="text-xs text-slate-500">Purpose</p>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                Test & Result Review
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 border border-slate-200 p-3">
              <p className="text-xs text-slate-500">AI Support</p>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                Critical Result Escalation
              </p>
            </div>
          </div>

        </div>
      </div>

      {/* =====================================================
          WHAT THIS PAGE DOES
      ===================================================== */}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="text-xl mb-3">🔎</div>
          <h3 className="font-semibold text-slate-800">
            Review Test Results
          </h3>
          <p className="text-sm text-slate-500 mt-1 leading-6">
            Open a laboratory order and review the patient's test values,
            reference ranges, status, and clinical interpretation.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="text-xl mb-3">📊</div>
          <h3 className="font-semibold text-slate-800">
            Understand Result Status
          </h3>
          <p className="text-sm text-slate-500 mt-1 leading-6">
            Quickly distinguish normal results from abnormal, pending, and
            critical findings that require attention.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="text-xl mb-3">🤖</div>
          <h3 className="font-semibold text-slate-800">
            AI Clinical Escalation
          </h3>
          <p className="text-sm text-slate-500 mt-1 leading-6">
            When a result is critical, the AI workflow can identify it and
            create an escalation for the responsible clinical team.
          </p>
        </div>

      </div>

      {/* =====================================================
          FIND LABORATORY ORDER
      ===================================================== */}

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">

        <div className="flex items-start gap-3 mb-5">
          <div className="text-xl">📋</div>

          <div>
            <h2 className="text-lg font-semibold text-slate-800">
              Find a Laboratory Order
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Enter the laboratory order number from the hospital system to
              view its complete test history.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-4">

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Laboratory Order Number
            </label>

            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                #
              </span>

              <input
                type="number"
                min="1"
                value={labOrderId}
                onChange={(e) => setLabOrderId(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch()
                }}
                placeholder="e.g. 3"
                className="w-full border border-slate-300 rounded-xl pl-8 pr-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <p className="text-xs text-slate-400 mt-2">
              This number identifies a specific laboratory test order. It is
              not the patient's ID.
            </p>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleSearch}
              disabled={loading}
              className="w-full lg:w-auto px-7 py-3 rounded-xl bg-slate-900 text-white font-semibold hover:bg-slate-800 disabled:opacity-50"
            >
              {loading ? "Loading..." : "View Test Details"}
            </button>
          </div>

        </div>

        <div className="mt-5 rounded-xl bg-blue-50 border border-blue-100 p-4">
          <div className="flex gap-3">
            <span className="text-lg">💡</span>
            <div>
              <p className="text-sm font-semibold text-blue-900">
                What happens after you open an order?
              </p>
              <p className="text-sm text-blue-800 mt-1 leading-6">
                The system shows the test, patient, ordering doctor, current
                status, latest result, reference range, previous results, and
                any clinical interpretation available for that order.
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

      </div>

      {/* =====================================================
          LAB ORDER DETAILS
      ===================================================== */}

      {labOrder && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-bold text-slate-800">
                  {labOrder.test_name || "Laboratory Test"}
                </h2>

                <span className="text-xs font-medium text-slate-500 bg-slate-100 border border-slate-200 rounded-full px-3 py-1">
                  Order #{labOrder.lab_order_id}
                </span>
              </div>

              <p className="text-sm text-slate-500 mt-2">
                Laboratory order details and current testing status
              </p>
            </div>

            <span
              className={`px-3 py-1.5 rounded-full border text-xs font-bold ${getOrderStatusClass(
                labOrder.order_status
              )}`}
            >
              {labOrder.order_status || "UNKNOWN"}
            </span>

          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">

            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
              <p className="text-xs text-slate-500">Patient</p>
              <p className="font-semibold text-slate-800 mt-1 break-all">
                {labOrder.patient_id || "Not available"}
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
              <p className="text-xs text-slate-500">Ordering Doctor</p>
              <p className="font-semibold text-slate-800 mt-1">
                Doctor {labOrder.doctor_id ?? "Not available"}
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
              <p className="text-xs text-slate-500">Department</p>
              <p className="font-semibold text-slate-800 mt-1">
                Department {labOrder.department_id ?? "Not available"}
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
              <p className="text-xs text-slate-500">Priority</p>
              <p className="font-semibold text-slate-800 mt-1">
                {labOrder.priority || "Not specified"}
              </p>
            </div>

          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">

            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500">Test Code</p>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {labOrder.test_code || "Not available"}
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500">Ordered On</p>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {labOrder.ordered_at
                  ? new Date(labOrder.ordered_at).toLocaleString()
                  : "Not available"}
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500">Testing Stage</p>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {labOrder.order_status || "Not available"}
              </p>
            </div>

          </div>

          {labOrder.clinical_notes && (
            <div className="mt-4 rounded-xl bg-slate-50 border border-slate-200 p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Clinical Notes
              </p>
              <p className="text-sm text-slate-700 mt-2 leading-6">
                {labOrder.clinical_notes}
              </p>
            </div>
          )}

        </div>
      )}

      {/* =====================================================
          RESULT SUMMARY
      ===================================================== */}

      {labOrder && labResults.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs text-slate-500">Total Results</p>
            <p className="text-2xl font-bold text-slate-800 mt-1">
              {labResults.length}
            </p>
          </div>

          <div className="bg-white border border-green-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs text-green-600">Normal</p>
            <p className="text-2xl font-bold text-green-700 mt-1">
              {statusCounts.NORMAL || 0}
            </p>
          </div>

          <div className="bg-white border border-orange-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs text-orange-600">Abnormal</p>
            <p className="text-2xl font-bold text-orange-700 mt-1">
              {statusCounts.ABNORMAL || 0}
            </p>
          </div>

          <div className="bg-white border border-red-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs text-red-600">Critical</p>
            <p className="text-2xl font-bold text-red-700 mt-1">
              {statusCounts.CRITICAL || 0}
            </p>
          </div>

        </div>
      )}

      {/* =====================================================
          LATEST RESULT
      ===================================================== */}

      {latestResult && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">📈</span>
                <h2 className="text-xl font-bold text-slate-800">
                  Latest Test Result
                </h2>
              </div>

              <p className="text-sm text-slate-500 mt-1">
                Most recent laboratory finding available for this order.
              </p>
            </div>

            <span
              className={`px-3 py-1.5 rounded-full border text-xs font-bold ${getStatusClass(
                latestResult.result_status
              )}`}
            >
              {getFriendlyStatus(latestResult.result_status)}
            </span>

          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">

            <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
              <p className="text-xs text-slate-500">Test</p>
              <p className="font-semibold text-slate-800 mt-1">
                {latestResult.test_name || "Not available"}
              </p>
            </div>

            <div
              className={`rounded-xl p-5 border ${
                latestResult.result_status === "CRITICAL"
                  ? "bg-red-50 border-red-200"
                  : "bg-slate-50 border-slate-100"
              }`}
            >
              <p className="text-xs text-slate-500">Measured Value</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">
                {formatResultValue(latestResult)}
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
              <p className="text-xs text-slate-500">Expected Range</p>
              <p className="font-semibold text-slate-800 mt-1">
                {latestResult.reference_range || "Not available"}
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
              <p className="text-xs text-slate-500">Verified By</p>
              <p className="font-semibold text-slate-800 mt-1">
                {latestResult.verified_by_doctor_id
                  ? `Doctor ${latestResult.verified_by_doctor_id}`
                  : "Not verified"}
              </p>
            </div>

          </div>

          {latestResult.interpretation && (
            <div className="mt-5 rounded-xl bg-slate-50 border border-slate-200 p-5">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                What the Result Means
              </p>
              <p className="text-sm text-slate-700 mt-2 leading-6">
                {latestResult.interpretation}
              </p>
            </div>
          )}

          {latestResult.performed_at && (
            <p className="text-xs text-slate-400 mt-4">
              Test performed:{" "}
              {new Date(latestResult.performed_at).toLocaleString()}
            </p>
          )}

          {/* Critical warning */}

          {latestResult.result_status === "CRITICAL" && (
            <div className="mt-6 rounded-2xl border border-red-300 bg-red-50 overflow-hidden">

              <div className="p-5 border-b border-red-200">
                <div className="flex items-start gap-4">
                  <div className="h-11 w-11 rounded-full bg-red-100 flex items-center justify-center text-xl shrink-0">
                    🚨
                  </div>

                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-red-900 text-lg">
                        Critical Result — Clinical Review Required
                      </h3>
                      <span className="px-2.5 py-1 rounded-full bg-red-600 text-white text-xs font-bold">
                        URGENT
                      </span>
                    </div>

                    <p className="text-sm text-red-800 mt-2 leading-6">
                      This laboratory result has been marked critical. The AI
                      workflow can review the finding, create a controlled
                      clinical escalation, and send a notification to the
                      responsible doctor.
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-5 bg-white/60">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="rounded-xl bg-white border border-red-100 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      Step 1
                    </p>
                    <p className="font-semibold text-slate-800 mt-1">
                      AI reviews the finding
                    </p>
                    <p className="text-xs text-slate-500 mt-1 leading-5">
                      The LabAgent checks the latest result and its clinical status.
                    </p>
                  </div>

                  <div className="rounded-xl bg-white border border-red-100 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      Step 2
                    </p>
                    <p className="font-semibold text-slate-800 mt-1">
                      Escalation is recorded
                    </p>
                    <p className="text-xs text-slate-500 mt-1 leading-5">
                      The Clinical Escalation Agent sends the action through the Action Gateway.
                    </p>
                  </div>

                  <div className="rounded-xl bg-white border border-red-100 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      Step 3
                    </p>
                    <p className="font-semibold text-slate-800 mt-1">
                      Doctor is notified
                    </p>
                    <p className="text-xs text-slate-500 mt-1 leading-5">
                      The escalation workflow creates the required clinical notification.
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">
                      Ready to start the clinical review?
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      No manual database action is required from this screen.
                    </p>
                  </div>

                  <button
                    onClick={handleRunAgent}
                    disabled={runningAgent}
                    className="px-6 py-3 rounded-xl bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                  >
                    {runningAgent
                      ? "Processing Clinical Escalation..."
                      : "Start Clinical Escalation"}
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      )}

      {/* =====================================================
          RESULTS HISTORY + FILTERS
      ===================================================== */}

      {labResults.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">

          <div className="p-6 border-b border-slate-200">

            <div className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-4">

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl">🧾</span>
                  <h2 className="text-xl font-bold text-slate-800">
                    Test History
                  </h2>
                </div>

                <p className="text-sm text-slate-500 mt-1">
                  Review all recorded results for this laboratory order.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">

                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">
                    Filter by test
                  </label>

                  <select
                    value={testFilter}
                    onChange={(e) => setTestFilter(e.target.value)}
                    className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="ALL">All tests</option>
                    {testOptions.map((test) => (
                      <option key={test} value={test}>
                        {test}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">
                    Filter by status
                  </label>

                  <select
                    value={resultFilter}
                    onChange={(e) => setResultFilter(e.target.value)}
                    className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="ALL">All statuses</option>
                    <option value="NORMAL">Normal</option>
                    <option value="ABNORMAL">Abnormal</option>
                    <option value="CRITICAL">Critical</option>
                    <option value="PENDING">Pending</option>
                  </select>
                </div>

              </div>

            </div>

          </div>

          <div className="overflow-x-auto">

            <table className="w-full text-sm">

              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">
                    Result
                  </th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">
                    Test
                  </th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">
                    Measured Value
                  </th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">
                    Expected Range
                  </th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">
                    Status
                  </th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">
                    Verified By
                  </th>
                </tr>
              </thead>

              <tbody>
                {filteredResults.map((result) => (
                  <tr
                    key={result.lab_result_id}
                    className="border-t border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-5 py-4 text-slate-600">
                      #{result.lab_result_id}
                    </td>

                    <td className="px-5 py-4 font-medium text-slate-800">
                      {result.test_name || "N/A"}
                    </td>

                    <td className="px-5 py-4 font-semibold text-slate-800">
                      {formatResultValue(result)}
                    </td>

                    <td className="px-5 py-4 text-slate-600">
                      {result.reference_range || "N/A"}
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={`px-2.5 py-1 rounded-full border text-xs font-semibold ${getStatusClass(
                          result.result_status
                        )}`}
                      >
                        {getFriendlyStatus(result.result_status)}
                      </span>
                    </td>

                    <td className="px-5 py-4 text-slate-600">
                      {result.verified_by_doctor_id
                        ? `Doctor ${result.verified_by_doctor_id}`
                        : "Not verified"}
                    </td>
                  </tr>
                ))}

                {filteredResults.length === 0 && (
                  <tr>
                    <td
                      colSpan="6"
                      className="px-5 py-8 text-center text-sm text-slate-500"
                    >
                      No results match the selected filters.
                    </td>
                  </tr>
                )}

              </tbody>

            </table>

          </div>

          <div className="px-6 py-4 border-t border-slate-100 bg-slate-50">
            <p className="text-xs text-slate-500">
              Showing {filteredResults.length} of {labResults.length} recorded
              result(s).
            </p>
          </div>

        </div>
      )}

      {/* =====================================================
          AI WORKFLOW RESULT
      ===================================================== */}

      {workflowResult && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">

          <div className="p-6 border-b border-slate-200">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl">🤖</span>
                  <h2 className="text-xl font-bold text-slate-800">
                    Clinical Escalation Result
                  </h2>
                </div>
                <p className="text-sm text-slate-500 mt-1">
                  A clear record of what the AI workflow detected and what actions were completed.
                </p>
              </div>

              <span className={`px-3 py-1.5 rounded-full text-xs font-bold border ${
                workflowResult.status === "SUCCESS"
                  ? "bg-green-100 text-green-700 border-green-200"
                  : "bg-red-100 text-red-700 border-red-200"
              }`}>
                {getStatusText(workflowResult.status)}
              </span>
            </div>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs text-slate-500">AI Outcome</p>
                <p className="font-bold text-slate-800 mt-1">
                  {getFriendlyDecision(workflowResult.decision)}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Workflow</p>
                <p className="font-bold text-slate-800 mt-1">
                  {workflowResult.workflow?.state || "Completed"}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Gateway Request</p>
                <p className="font-bold text-slate-800 mt-1">
                  #{workflowResult.data?.gateway_result?.gateway_request_id || "N/A"}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Responsible Doctor</p>
                <p className="font-bold text-slate-800 mt-1">
                  {workflowResult.data?.doctor_id
                    ? `Doctor ${workflowResult.data.doctor_id}`
                    : labOrder?.doctor_id
                      ? `Doctor ${labOrder.doctor_id}`
                      : "Not available"}
                </p>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-green-200 bg-green-50 p-5">
              <div className="flex items-start gap-3">
                <div className="h-9 w-9 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                  ✓
                </div>
                <div>
                  <p className="font-semibold text-green-900">
                    {workflowResult.status === "SUCCESS"
                      ? "Clinical escalation completed"
                      : "Clinical workflow needs attention"}
                  </p>
                  <p className="text-sm text-green-800 mt-1 leading-6">
                    {workflowResult.reason ||
                      "The clinical workflow has finished processing this laboratory finding."}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                Escalation Activity
              </p>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                {(workflowResult.workflow?.completed_agents || []).map((agent, index, agents) => (
                  <div key={agent} className="relative rounded-xl border border-slate-200 bg-white p-4">
                    <div className="flex items-center gap-2">
                      <span className="h-7 w-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">
                        {index + 1}
                      </span>
                      <span className="font-semibold text-slate-800 text-sm">
                        {agent.replace("Agent", " Agent")}
                      </span>
                    </div>
                    {index < agents.length - 1 && (
                      <div className="hidden md:block absolute top-1/2 -right-3 w-3 border-t border-slate-300" />
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Hospital Event</p>
                <p className="font-semibold text-slate-800 mt-1">
                  {workflowResult.data?.gateway_result?.event_id
                    ? `#${workflowResult.data.gateway_result.event_id}`
                    : "Recorded by workflow"}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Doctor Notification</p>
                <p className="font-semibold text-slate-800 mt-1">
                  {workflowResult.data?.gateway_result?.notification_id
                    ? `#${workflowResult.data.gateway_result.notification_id}`
                    : "Created by workflow"}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs text-slate-500">Laboratory Order</p>
                <p className="font-semibold text-slate-800 mt-1">
                  #{workflowResult.data?.lab_order_id || labOrder?.lab_order_id || labOrderId}
                </p>
              </div>
            </div>

            <div className="mt-5 rounded-xl bg-slate-50 border border-slate-200 p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Technical Decision
              </p>
              <p className="text-sm text-slate-700 mt-1 font-mono">
                {workflowResult.decision || "N/A"}
              </p>
            </div>
             {/* =====================================================
    EMAIL NOTIFICATION
===================================================== */}

{(String(workflowResult?.status || "").toUpperCase() === "SUCCESS" ||
  String(workflowResult?.status || "").toUpperCase() === "COMPLETED") &&
  latestResult?.result_status === "CRITICAL" && (
    <div className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 p-5">
      <div className="flex flex-col gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">✉️</span>
            <h3 className="font-bold text-slate-800 text-lg">
              Email Notification
            </h3>
          </div>

          <p className="text-sm text-slate-600 mt-2 leading-6">
            The critical laboratory result has been processed successfully.
            You can send the result notification to a real test recipient
            email address.
          </p>
        </div>

        <NotificationButton
          eventType="CRITICAL_LAB_RESULT"
          priority="HIGH"
          patientId={
            workflowResult?.context?.patient_id ||
            labOrder?.patient_id ||
            null
          }
          admissionId={null}
          title="Critical Laboratory Result"
          message={`A critical laboratory result requires immediate clinical review. Test: ${
            latestResult?.test_name || "Laboratory Test"
          }. Result: ${
            latestResult?.result_value ?? "N/A"
          }${
            latestResult?.unit
              ? ` ${latestResult.unit}`
              : ""
          }.`}
          sourceAgent="ClinicalEscalationAgent"
        />
      </div>
    </div>
  )}
          </div>
          </div>
        
      )}

      {/* =====================================================
          WORKFLOW EXPLANATION
      ===================================================== */}

      <div className="bg-slate-900 rounded-2xl p-6 text-white">

        <div className="flex items-center gap-2 mb-5">
          <span className="text-xl">⚙️</span>
          <h2 className="text-lg font-semibold">
            How the Diagnostics AI Workflow Works
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

          <div className="rounded-xl bg-white/10 border border-white/10 p-4">
            <p className="text-xs text-slate-300">01</p>
            <p className="font-semibold mt-1">Load Test Data</p>
            <p className="text-xs text-slate-300 mt-2 leading-5">
              The system retrieves the selected laboratory order and results.
            </p>
          </div>

          <div className="rounded-xl bg-white/10 border border-white/10 p-4">
            <p className="text-xs text-slate-300">02</p>
            <p className="font-semibold mt-1">AI Reviews Result</p>
            <p className="text-xs text-slate-300 mt-2 leading-5">
              LabAgent evaluates the latest recorded result and its status.
            </p>
          </div>

          <div className="rounded-xl bg-white/10 border border-white/10 p-4">
            <p className="text-xs text-slate-300">03</p>
            <p className="font-semibold mt-1">Escalate if Critical</p>
            <p className="text-xs text-slate-300 mt-2 leading-5">
              Critical findings are passed to the clinical escalation agent.
            </p>
          </div>

          <div className="rounded-xl bg-white/10 border border-white/10 p-4">
            <p className="text-xs text-slate-300">04</p>
            <p className="font-semibold mt-1">Record & Notify</p>
            <p className="text-xs text-slate-300 mt-2 leading-5">
              The Action Gateway records the action and creates the required
              clinical notification.
            </p>
          </div>

        </div>

      </div>
        </main>
      </div>
    </div>
  )
}

export default Diagnostics
