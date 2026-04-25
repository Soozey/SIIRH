import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./contexts/useAuth";
import Login from "./pages/Login";
import { canAccessPath } from "./rbac";

const ChangePassword = lazy(() => import("./pages/ChangePassword"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const DataTransfer = lazy(() => import("./pages/DataTransfer"));
const Declarations = lazy(() => import("./pages/Declarations"));
const HelpCenter = lazy(() => import("./pages/HelpCenter"));
const Employee360 = lazy(() => import("./pages/Employee360"));
const EmployeePortal = lazy(() => import("./pages/EmployeePortal"));
const Employers = lazy(() => import("./pages/Employers"));
const InspectionCompliance = lazy(() => import("./pages/InspectionCompliance"));
const Messages = lazy(() => import("./pages/Messages"));
const Absences = lazy(() => import("./pages/Absences"));
const Contracts = lazy(() => import("./pages/Contracts"));
const HeuresSupplementairesPageHS = lazy(() => import("./pages/HeuresSupplementairesPageHS"));
const LeavePermissionManagement = lazy(() => import("./pages/LeavePermissionManagement"));
const Organization = lazy(() => import("./pages/Organization"));
const PayrollRun = lazy(() => import("./pages/PayrollRun"));
const Payslip = lazy(() => import("./pages/Payslip"));
const PayslipsBulk = lazy(() => import("./pages/PayslipsBulk"));
const PeopleOps = lazy(() => import("./pages/PeopleOps"));
const PrimesHub = lazy(() => import("./pages/PrimesHub"));
const PrimesManagement = lazy(() => import("./pages/PrimesManagement"));
const Recruitment = lazy(() => import("./pages/Recruitment"));
const RecruitmentSettings = lazy(() => import("./pages/RecruitmentSettings"));
const Reporting = lazy(() => import("./pages/Reporting"));
const Sst = lazy(() => import("./pages/Sst"));
const Talents = lazy(() => import("./pages/Talents"));
const Workers = lazy(() => import("./pages/Workers"));


function RouteLoader() {
  return (
    <div className="siirh-panel min-h-[32vh] p-8 text-sm text-slate-500">
      Chargement du module...
    </div>
  );
}

function RoleRoute({ path, children }: { path: string; children: React.ReactNode }) {
  const { session } = useAuth();
  if (!canAccessPath(session, path)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}


function ProtectedApp() {
  return (
    <ProtectedRoute>
      <Layout>
        <Suspense fallback={<RouteLoader />}>
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/employers" element={<RoleRoute path="/employers"><Employers /></RoleRoute>} />
              <Route path="/workers" element={<RoleRoute path="/workers"><Workers /></RoleRoute>} />
              <Route path="/recruitment" element={<RoleRoute path="/recruitment"><Recruitment /></RoleRoute>} />
              <Route path="/recruitment/settings" element={<RoleRoute path="/recruitment/settings"><RecruitmentSettings /></RoleRoute>} />
              <Route path="/contracts" element={<RoleRoute path="/contracts"><Contracts /></RoleRoute>} />
              <Route path="/organization" element={<RoleRoute path="/organization"><Organization /></RoleRoute>} />
              <Route path="/payroll" element={<RoleRoute path="/payroll"><PayrollRun /></RoleRoute>} />
              <Route path="/primes" element={<RoleRoute path="/primes"><PrimesHub /></RoleRoute>} />
              <Route path="/payslip/:workerId/:period" element={<RoleRoute path="/payslip"><Payslip /></RoleRoute>} />
              <Route path="/hs" element={<RoleRoute path="/hs"><HeuresSupplementairesPageHS /></RoleRoute>} />
              <Route path="/absences" element={<RoleRoute path="/absences"><Absences /></RoleRoute>} />
              <Route path="/payslip-bulk/:employerId/:period" element={<RoleRoute path="/payslip-bulk"><PayslipsBulk /></RoleRoute>} />
              <Route path="/employers/:employerId/primes" element={<RoleRoute path="/primes"><PrimesManagement /></RoleRoute>} />
              <Route path="/leaves" element={<RoleRoute path="/leaves"><LeavePermissionManagement /></RoleRoute>} />
              <Route path="/declarations" element={<RoleRoute path="/declarations"><Declarations /></RoleRoute>} />
              <Route path="/inspection" element={<RoleRoute path="/inspection"><InspectionCompliance /></RoleRoute>} />
              <Route path="/messages" element={<RoleRoute path="/messages"><Messages /></RoleRoute>} />
              <Route path="/employee-portal" element={<RoleRoute path="/employee-portal"><EmployeePortal /></RoleRoute>} />
              <Route path="/employee-360" element={<RoleRoute path="/employee-360"><Employee360 /></RoleRoute>} />
              <Route path="/people-ops" element={<RoleRoute path="/people-ops"><PeopleOps /></RoleRoute>} />
              <Route path="/talents" element={<RoleRoute path="/talents"><Talents /></RoleRoute>} />
              <Route path="/sst" element={<RoleRoute path="/sst"><Sst /></RoleRoute>} />
              <Route path="/reporting" element={<RoleRoute path="/reporting"><Reporting /></RoleRoute>} />
              <Route path="/data-transfer" element={<RoleRoute path="/data-transfer"><DataTransfer /></RoleRoute>} />
              <Route path="/help" element={<HelpCenter />} />
            </Routes>
          </ErrorBoundary>
        </Suspense>
      </Layout>
    </ProtectedRoute>
  );
}


export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/change-password" element={<ProtectedRoute><Suspense fallback={<RouteLoader />}><ChangePassword /></Suspense></ProtectedRoute>} />
      <Route path="/*" element={<ProtectedApp />} />
    </Routes>
  );
}
