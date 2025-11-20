import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Employers from "./pages/Employers";
import Workers from "./pages/Workers";
import PayrollRun from "./pages/PayrollRun";
import Payslip from "./pages/Payslip";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Employers />} />
        <Route path="/workers" element={<Workers />} />
        <Route path="/payroll" element={<PayrollRun />} />
        <Route path="/payslip/:workerId/:period" element={<Payslip />} />
      </Routes>
    </Layout>
  );
}