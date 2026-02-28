import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

// Pages
import Login from "./pages/Login";
import Register from "./pages/Register";
import AdminDashboard from "./pages/admin/Dashboard";
import AdminOperators from "./pages/admin/Operators";
import AdminSaaSPlans from "./pages/admin/SaaSPlans";
import AdminAuditLogs from "./pages/admin/AuditLogs";
import OperatorDashboard from "./pages/operator/Dashboard";
import OperatorSubscribers from "./pages/operator/Subscribers";
import OperatorPlans from "./pages/operator/Plans";
import OperatorInvoices from "./pages/operator/Invoices";
import OperatorStaff from "./pages/operator/Staff";
import OperatorReports from "./pages/operator/Reports";
import OperatorSettings from "./pages/operator/Settings";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem("token"));

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem("token");
      if (storedToken) {
        try {
          const response = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${storedToken}` }
          });
          setUser(response.data);
          setToken(storedToken);
        } catch (error) {
          localStorage.removeItem("token");
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, user: userData } = response.data;
    localStorage.setItem("token", access_token);
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const register = async (data) => {
    const response = await axios.post(`${API}/auth/register`, data);
    const { access_token, user: userData } = response.data;
    localStorage.setItem("token", access_token);
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const authAxios = axios.create({
    baseURL: API,
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, authAxios }}>
      {children}
    </AuthContext.Provider>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    if (user.role === "admin") {
      return <Navigate to="/admin" replace />;
    }
    return <Navigate to="/operator" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" richColors closeButton />
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Admin Routes */}
          <Route path="/admin" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminDashboard />
            </ProtectedRoute>
          } />
          <Route path="/admin/operators" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminOperators />
            </ProtectedRoute>
          } />
          <Route path="/admin/saas-plans" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminSaaSPlans />
            </ProtectedRoute>
          } />
          <Route path="/admin/audit-logs" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminAuditLogs />
            </ProtectedRoute>
          } />

          {/* Operator Routes */}
          <Route path="/operator" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorDashboard />
            </ProtectedRoute>
          } />
          <Route path="/operator/subscribers" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorSubscribers />
            </ProtectedRoute>
          } />
          <Route path="/operator/plans" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorPlans />
            </ProtectedRoute>
          } />
          <Route path="/operator/invoices" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorInvoices />
            </ProtectedRoute>
          } />
          <Route path="/operator/staff" element={
            <ProtectedRoute allowedRoles={["operator"]}>
              <OperatorStaff />
            </ProtectedRoute>
          } />
          <Route path="/operator/reports" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorReports />
            </ProtectedRoute>
          } />
          <Route path="/operator/settings" element={
            <ProtectedRoute allowedRoles={["operator"]}>
              <OperatorSettings />
            </ProtectedRoute>
          } />

          {/* Default Route */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
