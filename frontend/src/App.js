import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { createContext, useContext, useState, useEffect, useMemo } from "react";
import axios from "axios";

// Pages
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import AdminDashboard from "./pages/admin/Dashboard";
import AdminOperators from "./pages/admin/Operators";
import AdminSaaSPlans from "./pages/admin/SaaSPlans";
import AdminAuditLogs from "./pages/admin/AuditLogs";
import AdminSettings from "./pages/admin/Settings";
import AdminReports from "./pages/admin/Reports";
import OperatorDashboard from "./pages/operator/Dashboard";
import OperatorSubscribers from "./pages/operator/Subscribers";
import OperatorPlans from "./pages/operator/Plans";
import OperatorInvoices from "./pages/operator/Invoices";
import OperatorStaff from "./pages/operator/Staff";
import OperatorReports from "./pages/operator/Reports";
import OperatorSettings from "./pages/operator/Settings";
import OperatorSubscription from "./pages/operator/Subscription";
import OperatorAnnouncements from "./pages/operator/Announcements";
import SubscriberLedgerPage from "./pages/operator/SubscriberLedgerPage";
import AdminBackup from "./pages/admin/Backup";
import OperatorAuditLogs from "./pages/operator/AuditLogs";
import AdminDiscountCodes from "./pages/admin/DiscountCodes";
import AdminWhatsAppTemplates from "./pages/admin/WhatsAppTemplates";
import AdminWhatsAppStats from "./pages/admin/WhatsAppStats";
import AdminErrorLogs from "./pages/admin/ErrorLogs";
import AdminLandingPage from "./pages/admin/LandingPage";
import AdminWallets from "./pages/admin/Wallets";
import AdminSupport from "./pages/admin/Support";
import OperatorWallet from "./pages/operator/Wallet";
import OperatorSupport from "./pages/operator/Support";
import OperatorWhatsAppStats from "./pages/operator/WhatsAppStats";
import PublicInvoice from "./pages/PublicInvoice";

// Theme Context
import { ThemeProvider } from "./contexts/ThemeContext";
import { clearBrowserCache } from "./lib/browserCache";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
export const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [features, setFeatures] = useState({});

  const refreshCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true  // Send cookies with request
      });
      setUser(response.data);
      await loadFeatures(response.data.role);
      return response.data;
    } catch (error) {
      setUser(null);
      return null;
    }
  };

  const loadFeatures = async (role) => {
    if (role === "operator" || role === "staff") {
      try {
        const res = await axios.get(`${API}/operator/features`, {
          withCredentials: true
        });
        setFeatures(res.data);
      } catch { setFeatures({}); }
    } else {
      setFeatures({});
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      try {
        await refreshCurrentUser();
      } catch (error) {
        // No valid session
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  useEffect(() => {
    if (!user) return undefined;

    const verifySession = async () => {
      try {
        await refreshCurrentUser();
      } catch (error) {
        if (error.response?.status === 401) {
          toast.error("Session expired. Please log in again.");
          logout();
        }
      }
    };

    const intervalId = window.setInterval(verifySession, 60000);
    const handleFocus = () => verifySession();
    window.addEventListener("focus", handleFocus);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleFocus);
    };
  }, [user]);

  const login = async (email, password) => {
    const response = await axios.post(
      `${API}/auth/login`, 
      { email, password },
      { withCredentials: true }  // Allow cookies to be set
    );
    const { user: userData } = response.data;
    await clearBrowserCache();
    setUser(userData);
    await loadFeatures(userData.role);
    return userData;
  };

  const register = async (data) => {
    const response = await axios.post(
      `${API}/auth/register`, 
      data,
      { withCredentials: true }
    );
    const { user: userData } = response.data;
    await clearBrowserCache();
    setUser(userData);
    await loadFeatures(userData.role);
    return userData;
  };

  const logout = async () => {
    try {
      await axios.post(
        `${API}/auth/logout`,
        {},
        { withCredentials: true }
      );
    } catch (error) {
      // Ignore errors on logout
    }
    setUser(null);
    setFeatures({});
  };

  // Create axios instance with credentials
  const authAxios = useMemo(() => {
    const instance = axios.create({
      baseURL: API,
      withCredentials: true  // Always send cookies
    });

    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401 && user) {
          toast.error("Session expired. Please log in again.");
          logout();
        }
        return Promise.reject(error);
      }
    );

    return instance;
  }, [user]);

  const contextValue = useMemo(
    () => ({ 
      user, 
      loading, 
      login, 
      register, 
      logout, 
      authAxios, 
      features, 
      refreshCurrentUser, 
      clearBrowserCache 
    }),
    [user, loading, features, authAxios]
  );

  return (
    <AuthContext.Provider value={contextValue}>
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
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/invoice/:invoiceRef" element={<PublicInvoice />} />

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
          <Route path="/admin/settings" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminSettings />
            </ProtectedRoute>
          } />
          <Route path="/admin/reports" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminReports />
            </ProtectedRoute>
          } />
          <Route path="/admin/backup" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminBackup />
            </ProtectedRoute>
          } />
          <Route path="/admin/discount-codes" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminDiscountCodes />
            </ProtectedRoute>
          } />
          <Route path="/admin/whatsapp-templates" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminWhatsAppTemplates />
            </ProtectedRoute>
          } />
          <Route path="/admin/whatsapp-stats" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminWhatsAppStats />
            </ProtectedRoute>
          } />
          <Route path="/admin/error-logs" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminErrorLogs />
            </ProtectedRoute>
          } />
          <Route path="/admin/wallets" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminWallets />
            </ProtectedRoute>
          } />
          <Route path="/admin/support" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminSupport />
            </ProtectedRoute>
          } />
          <Route path="/admin/landing-page" element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminLandingPage />
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
          <Route path="/operator/subscribers/:subscriberId/ledger" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <SubscriberLedgerPage />
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
          <Route path="/operator/subscription" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorSubscription />
            </ProtectedRoute>
          } />
          <Route path="/operator/announcements" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorAnnouncements />
            </ProtectedRoute>
          } />
          <Route path="/operator/audit-logs" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorAuditLogs />
            </ProtectedRoute>
          } />
          <Route path="/operator/wallet" element={
            <ProtectedRoute allowedRoles={["operator"]}>
              <OperatorWallet />
            </ProtectedRoute>
          } />
          <Route path="/operator/support" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorSupport />
            </ProtectedRoute>
          } />
          <Route path="/operator/whatsapp-stats" element={
            <ProtectedRoute allowedRoles={["operator", "staff"]}>
              <OperatorWhatsAppStats />
            </ProtectedRoute>
          } />
          {/* Default Route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
