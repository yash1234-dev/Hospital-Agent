import { useState } from "react"
import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import { runEmergencyTriage } from "../services/api"
import NotificationButton from "../components/NotificationButton"
function Emergency() {
  const [incidentId, setIncidentId] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState("")

  const handleRunTriage = async () => {
    if (!incidentId) {
      setError("Please enter an Incident ID.")
      return
    }

    setLoading(true)
    setError("")
    setResult(null)

    try {
      const data = await runEmergencyTriage(incidentId)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex">

      <Sidebar />

      <div className="min-w-0 flex-1">

        <Header />

        <main className="min-w-0 p-4 sm:p-6 lg:p-8">

          {/* Page Header */}
          <div className="mb-8">

            <div className="flex items-center gap-3">

              <div className="w-11 h-11 rounded-lg bg-red-100 flex items-center justify-center text-xl">
                🚨
              </div>

              <div>
                <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
                  Emergency Operations
                </h1>

                <p className="text-sm text-slate-500 mt-1">
                  Run AI-powered emergency triage and patient allocation.
                </p>
              </div>

            </div>

          </div>

          {/* Incident Input */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">

            <h2 className="text-lg font-semibold text-slate-800">
              Start Emergency Workflow
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Enter an emergency incident ID to start the AI workflow.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 mt-6 max-w-xl">

              <input
                type="number"
                min="1"
                value={incidentId}
                onChange={(e) => setIncidentId(e.target.value)}
                placeholder="Enter Incident ID"
                className="flex-1 px-4 py-3 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
              />

              <button
                onClick={handleRunTriage}
                disabled={loading}
                className="px-6 py-3 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 disabled:bg-slate-400 disabled:cursor-not-allowed"
              >
                {loading ? "Processing..." : "Run AI Triage"}
              </button>

            </div>

            {error && (
              <div className="mt-4 p-4 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
                {error}
              </div>
            )}

          </div>

          {/* Loading */}
          {loading && (
            <div className="mt-6 bg-white rounded-xl border border-slate-200 p-8 text-center">

              <div className="text-3xl mb-3">
                ⚙️
              </div>

              <p className="font-medium text-slate-700">
                AI agents are processing the emergency...
              </p>

              <p className="text-sm text-slate-500 mt-1">
                Triage → Transport → Bed → Staff
              </p>

            </div>
          )}

          {/* Result */}
          {result && !loading && (
            <div className="mt-6 space-y-6">

              {/* Final Status */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">

                <div className="flex items-center justify-between">

                  <div>
                    <h2 className="text-lg font-semibold text-slate-800">
                      Workflow Result
                    </h2>

                    <p className="text-sm text-slate-500 mt-1">
                      Emergency workflow execution completed.
                    </p>
                  </div>

                  <span className="px-4 py-2 rounded-full bg-green-100 text-green-700 text-sm font-semibold">
                    {result.status}
                  </span>

                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">

                   <InfoBox
                     label="Workflow Status"
                     value={result.status || "N/A"}
                   />

                   <InfoBox
                     label="Final Agent Decision"
                     value={result.decision || "N/A"}
                   />

                  <InfoBox
                    label="Patient ID"
                    value={result.context?.patient_id || "N/A"}
                  />

                  <InfoBox
                    label="Admission ID"
                    value={result.context?.admission_id || "N/A"}
                  />

                </div>

                <div className="mt-5 p-4 rounded-lg bg-slate-50">
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Reason
                  </p>

                  <p className="text-sm text-slate-700 mt-1">
                    {result.reason || "No reason provided."}
                  </p>
                </div>

              </div>

              {/* Agent Execution */}
              <AgentExecution result={result} />

              {/* Actions */}
              <ActionPanel result={result} />

              {/* Context */}
              <ContextPanel result={result} />
              {/* Email Notification */}
{result.status === "SUCCESS" && (
  <NotificationButton
    eventType="EMERGENCY_ALERT"
    priority="HIGH"
    patientId={result.context?.patient_id || null}
    admissionId={result.context?.admission_id || null}
    incidentId={incidentId ? Number(incidentId) : null}
    title="Emergency Alert"
    message={`Emergency workflow for ${
      result.context?.patient_id
        ? `patient ${result.context.patient_id}`
        : "the patient"
    } has been successfully processed. The emergency response workflow has completed.`}
    sourceAgent="EmergencyAgent"
  />
)}

            </div>
          )}

        </main>

      </div>

    </div>
  )
}


/* -------------------------------- */
/* Information Box                  */
/* -------------------------------- */

function InfoBox({ label, value }) {
  return (
    <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">

      <p className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="text-sm font-semibold text-slate-800 mt-2 break-all">
        {value}
      </p>

    </div>
  )
}


/* -------------------------------- */
/* Agent Execution                  */
/* -------------------------------- */

function AgentExecution({ result }) {

  const decisions = result.context?.decisions || []
  const completedAgents =
    result.execution_state?.completed_agents || []

  const failedAgents =
    result.execution_state?.failed_agents || []

  const agents = [
    "TriageAgent",
    "EmergencyAgent",
    "BedAgent",
    "StaffAgent",
  ]

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">

      <h2 className="text-lg font-semibold text-slate-800">
        Agent Execution
      </h2>

      <p className="text-sm text-slate-500 mt-1">
        Agents involved in this emergency workflow.
      </p>

      <div className="mt-6 space-y-4">

        {agents.map((agent) => {

          const completed = completedAgents.includes(agent)
          const failed = failedAgents.includes(agent)

          const decision =
            decisions.find(
              (item) => item.agent === agent
            )

          return (
            <div
              key={agent}
              className="flex items-start gap-4 p-4 rounded-lg border border-slate-200"
            >

              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center ${
                  failed
                    ? "bg-red-100 text-red-600"
                    : completed
                    ? "bg-green-100 text-green-600"
                    : "bg-slate-100 text-slate-400"
                }`}
              >
                {failed ? "✕" : completed ? "✓" : "○"}
              </div>

              <div className="min-w-0 flex-1">

                <div className="flex items-center justify-between">

                  <h3 className="font-semibold text-slate-800">
                    {agent}
                  </h3>

                  <span
                    className={`text-xs font-medium ${
                      failed
                        ? "text-red-600"
                        : completed
                        ? "text-green-600"
                        : "text-slate-400"
                    }`}
                  >
                    {failed
                      ? "Failed"
                      : completed
                      ? "Completed"
                      : "Not Executed"}
                  </span>

                </div>

                {decision && (
                  <div className="mt-2">

                    <p className="text-xs text-slate-500">
                      Decision
                    </p>

                    <p className="text-sm font-medium text-blue-600">
                      {decision.decision}
                    </p>

                    {decision.reason && (
                      <p className="text-xs text-slate-500 mt-1">
                        {decision.reason}
                      </p>
                    )}

                  </div>
                )}

              </div>

            </div>
          )
        })}

      </div>

    </div>
  )
}


/* -------------------------------- */
/* Actions                          */
/* -------------------------------- */

function ActionPanel({ result }) {

  const actions = result.context?.actions || []

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">

      <h2 className="text-lg font-semibold text-slate-800">
        Actions Performed
      </h2>

      <p className="text-sm text-slate-500 mt-1">
        Actions executed through the Action Gateway.
      </p>

      {actions.length === 0 ? (

        <p className="text-sm text-slate-500 mt-6">
          No actions were performed.
        </p>

      ) : (

        <div className="mt-6 overflow-x-auto">

          <table className="w-full text-sm">

            <thead>
              <tr className="border-b border-slate-200 text-left">

                <th className="pb-3 font-medium text-slate-500">
                  Agent
                </th>

                <th className="pb-3 font-medium text-slate-500">
                  Action
                </th>

                <th className="pb-3 font-medium text-slate-500">
                  Status
                </th>

                <th className="pb-3 font-medium text-slate-500">
                  Details
                </th>

              </tr>
            </thead>

            <tbody>

              {actions.map((action, index) => (

                <tr
                  key={index}
                  className="border-b border-slate-100"
                >

                  <td className="py-4 font-medium text-slate-700">
                    {action.agent || "N/A"}
                  </td>

                  <td className="py-4 text-slate-600">
                    {action.action || "N/A"}
                  </td>

                  <td className="py-4">

                    <span className="px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                      {action.status || "N/A"}
                    </span>

                  </td>

                  <td className="py-4 text-slate-500">

                    {action.bed_id && (
                      <span>
                        Bed: {action.bed_id}
                      </span>
                    )}

                    {action.doctor_id && (
                      <span>
                        Doctor: {action.doctor_id}
                      </span>
                    )}

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      )}

    </div>
  )
}


/* -------------------------------- */
/* Context                          */
/* -------------------------------- */

function ContextPanel({ result }) {

  const context = result.context || {}

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">

      <h2 className="text-lg font-semibold text-slate-800">
        Patient & Admission State
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">

        <InfoBox
          label="Incident"
          value={context.incident_id || "N/A"}
        />

        <InfoBox
          label="Patient"
          value={context.patient_id || "N/A"}
        />

        <InfoBox
          label="Admission"
          value={context.admission_id || "N/A"}
        />

        <InfoBox
          label="Department"
          value={context.department_id || "N/A"}
        />

      </div>

    </div>
  )
}

export default Emergency