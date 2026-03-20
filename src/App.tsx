import { Route, Routes } from "react-router-dom";

import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import ConstantsDemo from "./components/ConstantsDemo";
import Dashboard from "./pages/Dashboard";
import Declarations from "./pages/Declarations";
import Employers from "./pages/Employers";
import Absences from "./pages/Absences";
import Contracts from "./pages/Contracts";
import HeuresSupplementairesPageHS from "./pages/HeuresSupplementairesPageHS";
import LeavePermissionManagement from "./pages/LeavePermissionManagement";
import Login from "./pages/Login";
import Organization from "./pages/Organization";
import PayrollRun from "./pages/PayrollRun";
import Payslip from "./pages/Payslip";
import PayslipsBulk from "./pages/PayslipsBulk";
import PrimesManagement from "./pages/PrimesManagement";
import Recruitment from "./pages/Recruitment";
import Reporting from "./pages/Reporting";
import Sst from "./pages/Sst";
import Talents from "./pages/Talents";
import Workers from "./pages/Workers";


function ProtectedApp() {
  return (
    <ProtectedRoute>
      <Layout>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/employers" element={<Employers />} />
            <Route path="/workers" element={<Workers />} />
            <Route path="/recruitment" element={<Recruitment />} />
            <Route path="/contracts" element={<Contracts />} />
            <Route path="/organization" element={<Organization />} />
            <Route path="/payroll" element={<PayrollRun />} />
            <Route path="/payslip/:workerId/:period" element={<Payslip />} />
            <Route path="/hs" element={<HeuresSupplementairesPageHS />} />
            <Route path="/absences" element={<Absences />} />
            <Route path="/payslip-bulk/:employerId/:period" element={<PayslipsBulk />} />
            <Route path="/employers/:employerId/primes" element={<PrimesManagement />} />
            <Route path="/leaves" element={<LeavePermissionManagement />} />
            <Route path="/declarations" element={<Declarations />} />
            <Route path="/talents" element={<Talents />} />
            <Route path="/sst" element={<Sst />} />
            <Route path="/reporting" element={<Reporting />} />
            <Route path="/constants-demo" element={<ConstantsDemo />} />
          </Routes>
        </ErrorBoundary>
      </Layout>
    </ProtectedRoute>
  );
}


export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<ProtectedApp />} />
    </Routes>
  );
}
