import { useEffect, useState } from "react"
import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import StatCard from "../components/StatCard"
import { getDashboardMetrics,getSystemHealth,getActiveEmergencyCases } from "../services/api"

function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [systemHealth, setSystemHealth] = useState(null)
const [systemLoading, setSystemLoading] = useState(true)
const [systemError, setSystemError] = useState("")
const [emergencyCases, setEmergencyCases] = useState([])
const [casesLoading, setCasesLoading] = useState(true)
const [casesError, setCasesError] = useState("")

  useEffect(() => {
    loadDashboardMetrics()
    loadSystemHealth()
    loadEmergencyCases()
  }, [])

  async function loadDashboardMetrics() {
    try {
      setLoading(true)
      setError("")

      const data = await getDashboardMetrics()

      setMetrics(data.metrics)
    } catch (err) {
      setError(err.message || "Failed to load dashboard metrics.")
    } finally {
      setLoading(false)
    }
  }
  async function loadSystemHealth() {
  try {
    setSystemLoading(true)
    setSystemError("")

    const data = await getSystemHealth()

    setSystemHealth(data.services)
  } catch (err) {
    setSystemError(
      err.message || "Failed to load system health."
    )
  } finally {
    setSystemLoading(false)
  }
}
async function loadEmergencyCases() {
  try {
    setCasesLoading(true)
    setCasesError("")

    const data = await getActiveEmergencyCases()

    setEmergencyCases(data.cases || [])
  } catch (err) {
    setCasesError(
      err.message || "Failed to load emergency cases."
    )
  } finally {
    setCasesLoading(false)
  }
}
  return (
    <div className="min-h-screen bg-slate-100 flex">

      <Sidebar />

      <div className="min-w-0 flex-1">

        <Header />

        <main className="min-w-0 p-4 sm:p-6 lg:p-8">

          {/* Page Title */}
          <div className="mb-8">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
              Overview
            </h1>

            <p className="text-sm text-slate-500 mt-1">
              Monitor hospital operations and AI-driven workflows.
            </p>
          </div>
           {error && (
  <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
    <p className="text-sm text-red-700">
      Dashboard API Error: {error}
    </p>
  </div>
)}
          {/* Statistics */}
         <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">

  <StatCard
    title="Available Beds"
    value={loading ? "..." : metrics?.available_beds ?? 0}
    description="Currently available"
    icon="🛏️"
  />

  <StatCard
    title="ICU Beds"
    value={loading ? "..." : metrics?.icu_beds ?? 0}
    description="Currently available"
    icon="🏥"
  />

  <StatCard
    title="Available Doctors"
    value={loading ? "..." : metrics?.available_doctors ?? 0}
    description="Scheduled today"
    icon="👨‍⚕️"
  />

  <StatCard
    title="Available Ambulances"
    value={loading ? "..." : metrics?.available_ambulances ?? 0}
    description="Ready for dispatch"
    icon="🚑"
  />

</div>

          {/* Main Dashboard Sections */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-8">

            {/* Emergency Operations */}
            <div className="xl:col-span-2 bg-white rounded-xl border border-slate-200 p-6">

              <div className="flex items-center justify-between mb-5">

                <div>
                  <h2 className="text-lg font-semibold text-slate-800">
                    Emergency Operations
                  </h2>

                  <p className="text-sm text-slate-500">
                    AI-managed emergency workflow
                  </p>
                </div>

                <a
                  href="/emergency"
                  className="text-sm font-medium text-blue-600 hover:text-blue-800"
                >
                  Open Emergency →
                </a>

              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                <div className="rounded-lg bg-red-50 p-4">
                  <p className="text-sm text-red-600">
                    Critical
                  </p>

                  <p className="text-2xl font-bold text-red-700 mt-1">
                     {loading ? "..." : metrics?.critical_cases ?? 0}
                  </p>
                </div>

                <div className="rounded-lg bg-orange-50 p-4">
                  <p className="text-sm text-orange-600">
                    High Priority
                  </p>

                  <p className="text-2xl font-bold text-orange-700 mt-1">
                    {loading ? "..." : metrics?.high_priority_cases ?? 0}
                  </p>
                </div>

                <div className="rounded-lg bg-blue-50 p-4">
                  <p className="text-sm text-blue-600">
                    Active Cases
                  </p>

                  <p className="text-2xl font-bold text-blue-700 mt-1">
                     {loading ? "..." : metrics?.active_cases ?? 0}
                  </p>
                </div>

              </div>

            </div>

            {/* AI System Status */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">

              <h2 className="text-lg font-semibold text-slate-800">
                AI System Status
              </h2>

              <p className="text-sm text-slate-500 mt-1">
                Agentic workflow services
              </p>

              <div className="mt-6 space-y-4">

  {systemError && (
    <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
      <p className="text-xs text-red-700">
        {systemError}
      </p>
    </div>
  )}

  <div className="flex items-center justify-between">
    <span className="text-sm text-slate-600">
      FastAPI
    </span>

    <span
      className={`text-xs font-medium ${
        systemHealth?.fastapi?.status === "ONLINE"
          ? "text-green-600"
          : "text-red-600"
      }`}
    >
      ●{" "}
      {systemLoading
        ? "Checking..."
        : systemHealth?.fastapi?.status || "Unknown"}
    </span>
  </div>


  <div className="flex items-center justify-between">
    <span className="text-sm text-slate-600">
      MySQL
    </span>

    <span
      className={`text-xs font-medium ${
        systemHealth?.mysql?.status === "ONLINE"
          ? "text-green-600"
          : "text-red-600"
      }`}
    >
      ●{" "}
      {systemLoading
        ? "Checking..."
        : systemHealth?.mysql?.status || "Unknown"}
    </span>
  </div>


  <div className="flex items-center justify-between">
    <span className="text-sm text-slate-600">
      Agent Orchestrator
    </span>

    <span
      className={`text-xs font-medium ${
        systemHealth?.orchestrator?.status === "READY"
          ? "text-green-600"
          : "text-red-600"
      }`}
    >
      ●{" "}
      {systemLoading
        ? "Checking..."
        : systemHealth?.orchestrator?.status || "Unknown"}
    </span>
  </div>


  <div className="flex items-center justify-between">
    <span className="text-sm text-slate-600">
      Action Gateway
    </span>

    <span
      className={`text-xs font-medium ${
        systemHealth?.action_gateway?.status === "READY"
          ? "text-green-600"
          : "text-red-600"
      }`}
    >
      ●{" "}
      {systemLoading
        ? "Checking..."
        : systemHealth?.action_gateway?.status || "Unknown"}
    </span>
  </div>

</div>

            </div>

          </div>
          {/* Active Emergency Cases */}

<div className="bg-white rounded-xl border border-slate-200 p-6 mt-6">

  <div className="flex items-center justify-between mb-5">

    <div>
      <h2 className="text-lg font-semibold text-slate-800">
        Active Emergency Cases
      </h2>

      <p className="text-sm text-slate-500 mt-1">
        Current emergency incidents requiring attention
      </p>
    </div>

    <a
      href="/emergency"
      className="text-sm font-medium text-blue-600 hover:text-blue-800"
    >
      Open Emergency →
    </a>

  </div>


  {casesError && (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 mb-4">
      <p className="text-sm text-red-700">
        {casesError}
      </p>
    </div>
  )}


  {casesLoading ? (

    <div className="py-8 text-center">
      <p className="text-sm text-slate-500">
        Loading emergency cases...
      </p>
    </div>

  ) : emergencyCases.length === 0 ? (

    <div className="py-8 text-center">
      <p className="text-sm text-slate-500">
        No active emergency cases.
      </p>
    </div>

  ) : (

    <div className="overflow-x-auto">

      <table className="w-full text-sm">

        <thead>
          <tr className="border-b border-slate-200 text-left">

            <th className="py-3 px-3 font-medium text-slate-500">
              Incident
            </th>

            <th className="py-3 px-3 font-medium text-slate-500">
              Type
            </th>

            <th className="py-3 px-3 font-medium text-slate-500">
              Severity
            </th>

            <th className="py-3 px-3 font-medium text-slate-500">
              Department
            </th>

            <th className="py-3 px-3 font-medium text-slate-500">
              Status
            </th>

            <th className="py-3 px-3 font-medium text-slate-500">
              Incident Time
            </th>

          </tr>
        </thead>


        <tbody>

          {emergencyCases.map((incident) => (

            <tr
              key={incident.incident_id}
              className="border-b border-slate-100 last:border-0"
            >

              <td className="py-3 px-3 font-medium text-slate-700">
                #{incident.incident_id}
              </td>


              <td className="py-3 px-3 text-slate-600">
                {incident.incident_type || "N/A"}
              </td>


              <td className="py-3 px-3">

                <span
                  className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                    incident.severity === "CRITICAL"
                      ? "bg-red-100 text-red-700"
                      : incident.severity === "HIGH"
                      ? "bg-orange-100 text-orange-700"
                      : incident.severity === "MEDIUM"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-blue-100 text-blue-700"
                  }`}
                >
                  {incident.severity || "N/A"}
                </span>

              </td>


              <td className="py-3 px-3 text-slate-600">
                {incident.department_name || "N/A"}
              </td>


              <td className="py-3 px-3">

                <span className="inline-flex rounded-full bg-slate-100 text-slate-700 px-2.5 py-1 text-xs font-medium">
                  {incident.status || "N/A"}
                </span>

              </td>


              <td className="py-3 px-3 text-slate-500">
                {incident.incident_time
                  ? new Date(
                      incident.incident_time
                    ).toLocaleString()
                  : "N/A"}
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

export default Dashboard