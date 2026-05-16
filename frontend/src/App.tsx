import { Routes, Route, Navigate } from "react-router-dom";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Admissions from "@/pages/Admissions";
import Students from "@/pages/Students";
import StudentDetail from "@/pages/StudentDetail";
import Attendance from "@/pages/Attendance";
import MarksEntry from "@/pages/MarksEntry";
import MarksResults from "@/pages/MarksResults";
import Fees from "@/pages/Fees";
import Notices from "@/pages/Notices";
import Staff from "@/pages/Staff";
import Reports from "@/pages/Reports";
import MobileApps from "@/pages/MobileApps";
import Letterheads from "@/pages/Letterheads";
import SalarySlips from "@/pages/SalarySlips";
import Templates from "@/pages/Templates";
import TemplateDetail from "@/pages/TemplateDetail";
import DeletionRequests from "@/pages/DeletionRequests";
import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/admissions" element={<Admissions />} />
          <Route path="/students" element={<Students />} />
          <Route path="/students/:id" element={<StudentDetail />} />
          <Route path="/attendance" element={<Attendance />} />
          <Route path="/marks/entry" element={<MarksEntry />} />
          <Route path="/marks/results" element={<MarksResults />} />
          <Route path="/fees" element={<ProtectedRoute adminOnly><Fees /></ProtectedRoute>} />
          <Route path="/notices" element={<Notices />} />
          <Route path="/staff" element={<ProtectedRoute adminOnly><Staff /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute adminOnly><Reports /></ProtectedRoute>} />
          <Route path="/letterheads" element={<ProtectedRoute adminOnly><Letterheads /></ProtectedRoute>} />
          <Route path="/salary-slips" element={<ProtectedRoute adminOnly><SalarySlips /></ProtectedRoute>} />
          <Route path="/templates" element={<ProtectedRoute adminOnly><Templates /></ProtectedRoute>} />
          <Route path="/templates/:id" element={<ProtectedRoute adminOnly><TemplateDetail /></ProtectedRoute>} />
          <Route path="/mobile-apps" element={<MobileApps />} />
          <Route path="/deletion-requests" element={<ProtectedRoute superAdminOnly><DeletionRequests /></ProtectedRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
