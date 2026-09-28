import { BrowserRouter, Routes, Route } from "react-router-dom"

import Dashboard from "./pages/Dashboard"
import Emergency from "./pages/Emergency"
import BedManagement from "./pages/BedManagement"
import StaffManagement from "./pages/StaffManagement"
import Diagnostics from "./pages/Diagnostics"
import Pharmacy from "./pages/Pharmacy"
import Admission from "./pages/Admission"

function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route
          path="/"
          element={<Dashboard />}
        />

        <Route
          path="/emergency"
          element={<Emergency />}
        />

        <Route
          path="/beds"
          element={<BedManagement />}
        />

        <Route
          path="/staff"
          element={<StaffManagement />}
        />

        <Route
          path="/diagnostics"
          element={<Diagnostics />}
        />

        <Route
          path="/pharmacy"
          element={<Pharmacy />}
        />

        <Route
          path="/admissions"
          element={<Admission />}
        />

      </Routes>
    </BrowserRouter>
  )
}

export default App