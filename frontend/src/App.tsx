import { Routes, Route, Navigate } from "react-router-dom";
import Login from "@/pages/Login";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
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
import EditRequests from "@/pages/EditRequests";
import ClassSubjects from "@/pages/ClassSubjects";
import ClassSubjectDetail from "@/pages/ClassSubjectDetail";
import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";
import { useVersionCheck } from "@/lib/version";

export default function App() {
  // Auto-detect stale bundles after a deploy and hard-reload the user.
  // No-op in dev (BUILD_ID === "dev") or when version.json matches the bundle.
  useVersionCheck();
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard"     element={<ProtectedRoute menuKey="dashboard"><Dashboard /></ProtectedRoute>} />
          <Route path="/admissions"    element={<ProtectedRoute menuKey="admissions"><Admissions /></ProtectedRoute>} />
          <Route path="/students"      element={<ProtectedRoute menuKey="students"><Students /></ProtectedRoute>} />
          <Route path="/students/:id"  element={<ProtectedRoute menuKey="students"><StudentDetail /></ProtectedRoute>} />
          <Route path="/attendance"    element={<ProtectedRoute menuKey="attendance"><Attendance /></ProtectedRoute>} />
          <Route path="/marks/entry"   element={<ProtectedRoute menuKey="marks-entry"><MarksEntry /></ProtectedRoute>} />
          <Route path="/marks/results" element={<ProtectedRoute menuKey="marks-results"><MarksResults /></ProtectedRoute>} />
          <Route path="/fees"          element={<ProtectedRoute menuKey="fees"><Fees /></ProtectedRoute>} />
          <Route path="/notices"       element={<ProtectedRoute menuKey="notices"><Notices /></ProtectedRoute>} />
          <Route path="/staff"         element={<ProtectedRoute adminOnly><Staff /></ProtectedRoute>} />
          <Route path="/reports"       element={<ProtectedRoute menuKey="reports"><Reports /></ProtectedRoute>} />
          <Route path="/letterheads"   element={<ProtectedRoute menuKey="letterheads"><Letterheads /></ProtectedRoute>} />
          <Route path="/salary-slips"  element={<ProtectedRoute menuKey="salary-slips"><SalarySlips /></ProtectedRoute>} />
          <Route path="/templates"     element={<ProtectedRoute menuKey="templates"><Templates /></ProtectedRoute>} />
          <Route path="/templates/:id" element={<ProtectedRoute menuKey="templates"><TemplateDetail /></ProtectedRoute>} />
          <Route path="/mobile-apps"   element={<ProtectedRoute menuKey="mobile-apps"><MobileApps /></ProtectedRoute>} />
          <Route path="/deletion-requests" element={<ProtectedRoute superAdminOnly><DeletionRequests /></ProtectedRoute>} />
          <Route path="/edit-requests"     element={<ProtectedRoute superAdminOnly><EditRequests /></ProtectedRoute>} />
          <Route path="/class-subjects"     element={<ProtectedRoute superAdminOnly><ClassSubjects /></ProtectedRoute>} />
          <Route path="/class-subjects/:id" element={<ProtectedRoute superAdminOnly><ClassSubjectDetail /></ProtectedRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
