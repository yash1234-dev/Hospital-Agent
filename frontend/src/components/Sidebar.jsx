import { useState } from "react"
import { NavLink } from "react-router-dom"

function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)

  const navClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-3 rounded-lg transition ${
      isActive
        ? "bg-slate-800 text-white"
        : "text-slate-300 hover:bg-slate-800 hover:text-white"
    }`

  const handleNavigate = () => setIsOpen(false)

  return (
    <>
      {/* Mobile menu button */}
      <button
        type="button"
        aria-label="Open navigation menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(true)}
        className="fixed left-3 top-3 z-60 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white shadow-lg ring-1 ring-white/10 md:hidden"
      >
        <span className="text-xl leading-none">☰</span>
      </button>

      {/* Mobile backdrop */}
      {isOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/50 md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 max-w-[86vw] flex-col bg-slate-900 text-white shadow-2xl transition-transform duration-200 md:static md:z-auto md:w-64 md:max-w-none md:shrink-0 md:translate-x-0 md:shadow-none ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="flex items-start justify-between border-b border-slate-700 px-5 py-5 md:px-6">
          <div>
            <h1 className="text-xl font-bold">Hospital AI</h1>
            <p className="mt-1 text-xs text-slate-400">
              Operations Intelligence
            </p>
          </div>

          <button
            type="button"
            aria-label="Close navigation menu"
            onClick={() => setIsOpen(false)}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white md:hidden"
          >
            ✕
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-2 overflow-y-auto px-4 py-5">
          <NavLink to="/" className={navClass} onClick={handleNavigate}>
            <span>📊</span>
            <span>Dashboard</span>
          </NavLink>

          <NavLink to="/emergency" className={navClass} onClick={handleNavigate}>
            <span>🚨</span>
            <span>Emergency</span>
          </NavLink>

          <NavLink to="/admissions" className={navClass} onClick={handleNavigate}>
            <span>🏥</span>
            <span>Admissions</span>
          </NavLink>

          <NavLink to="/beds" className={navClass} onClick={handleNavigate}>
            <span>🛏️</span>
            <span>Bed Management</span>
          </NavLink>

          <NavLink to="/staff" className={navClass} onClick={handleNavigate}>
            <span>👨‍⚕️</span>
            <span>Staff Management</span>
          </NavLink>

          <NavLink to="/diagnostics" className={navClass} onClick={handleNavigate}>
            <span>🧪</span>
            <span>Diagnostics</span>
          </NavLink>

          <NavLink to="/pharmacy" className={navClass} onClick={handleNavigate}>
            <span>💊</span>
            <span>Pharmacy</span>
          </NavLink>
        </nav>

        {/* Footer */}
        <div className="border-t border-slate-700 px-5 py-4 md:px-6">
          <p className="text-xs text-slate-500">AI Hospital System</p>
          <p className="text-xs text-slate-500">v1.0.0</p>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
