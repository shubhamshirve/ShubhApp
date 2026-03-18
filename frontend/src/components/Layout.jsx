import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import {
  LayoutDashboard,
  Users,
  CreditCard,
  FileText,
  Settings,
  LogOut,
  Building2,
  Package,
  ClipboardList,
  UserCog,
  BarChart3,
  Menu,
  X,
  AlertTriangle,
  Bell,
  Database,
  Tag,
  MessageSquare,
  Banknote,
  Layout,
  Wallet
} from "lucide-react";
import { useState } from "react";
import { Button } from "./ui/button";

const AdminSidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const links = [
    { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
    { href: "/admin/operators", label: "Operators", icon: Building2 },
    { href: "/admin/saas-plans", label: "SaaS Plans", icon: Package },
    { href: "/admin/discount-codes", label: "Discount Codes", icon: Tag },
    { href: "/admin/reports", label: "Reports", icon: BarChart3 },
    { href: "/admin/settlements", label: "Settlements", icon: Banknote },
    { href: "/admin/wallets", label: "Wallets", icon: Wallet },
    { href: "/admin/landing-page", label: "Landing Page", icon: Layout },
    { href: "/admin/settings", label: "Settings", icon: Settings },
    { href: "/admin/error-logs", label: "Error Logs", icon: AlertTriangle },
    { href: "/admin/audit-logs", label: "Audit Logs", icon: ClipboardList },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-white border-r border-slate-200 
        transform transition-transform duration-200 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="h-16 flex items-center justify-between px-6 border-b border-slate-200">
            <Link to="/admin" className="flex items-center gap-2">
              <img src="/ebill-logo.svg" alt="E-Bill" className="w-8 h-8" />
              <span className="font-heading font-bold text-[#004080]">E-Bill</span>
            </Link>
            <button onClick={onClose} className="lg:hidden p-1 hover:bg-slate-100 rounded">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* User info */}
          <div className="px-4 py-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#0066B2] rounded-full flex items-center justify-center">
                <span className="text-white font-medium text-sm">
                  {user?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{user?.name}</p>
                <p className="text-xs text-slate-500">Super Admin</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {links.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.href;
              return (
                <Link
                  key={link.href}
                  to={link.href}
                  onClick={onClose}
                  className={`sidebar-link ${isActive ? 'active' : ''}`}
                  data-testid={`nav-${link.label.toLowerCase().replace(' ', '-')}`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Logout */}
          <div className="p-4 border-t border-slate-200">
            <button
              onClick={handleLogout}
              className="sidebar-link w-full text-red-600 hover:bg-red-50 hover:text-red-700"
              data-testid="logout-btn"
            >
              <LogOut className="w-5 h-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};

const OperatorSidebar = ({ isOpen, onClose, isReadOnly }) => {
  const location = useLocation();
  const { logout, user, features } = useAuth();
  const navigate = useNavigate();
  const isImpersonated = !!user?.impersonated_by;

  const allLinks = [
    { href: "/operator",              label: "Dashboard",    icon: LayoutDashboard, always: true },
    { href: "/operator/subscribers",  label: "Subscribers",  icon: Users,           always: true },
    { href: "/operator/plans",        label: "Plans",        icon: Package,         always: true },
    { href: "/operator/invoices",     label: "Invoices",     icon: FileText,        always: true },
    { href: "/operator/wallet",       label: "Wallet",       icon: Wallet,          always: true, operatorOnly: true },
    { href: "/operator/settlements",  label: "Settlements",  icon: Banknote,        always: true },
    { href: "/operator/announcements",label: "Announcements",icon: Bell,            feature: "announcement" },
    { href: "/operator/audit-logs",   label: "Audit Logs",   icon: ClipboardList,   feature: "audit_log" },
    { href: "/operator/staff",        label: "Staff",        icon: UserCog,         feature: "staff_management", operatorOnly: true },
    { href: "/operator/reports",      label: "Reports",      icon: BarChart3,       always: true },
    { href: "/operator/subscription", label: "Subscription", icon: CreditCard,      always: true },
    { href: "/operator/settings",     label: "Settings",     icon: Settings,        always: true, operatorOnly: true },
  ];

  const links = allLinks.filter(link => {
    if (link.feature && !features[link.feature]) return false;
    if (link.operatorOnly && user?.role === "staff") return false;
    return true;
  });

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-white border-r border-slate-200 
        transform transition-transform duration-200 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          <div className="h-16 flex items-center justify-between px-6 border-b border-slate-200">
            <Link to="/operator" className="flex items-center gap-2">
              <img src="/ebill-logo.svg" alt="E-Bill" className="w-8 h-8" />
              <span className="font-heading font-bold text-[#004080]">E-Bill</span>
            </Link>
            <button onClick={onClose} className="lg:hidden p-1 hover:bg-slate-100 rounded">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="px-4 py-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#0066B2] rounded-full flex items-center justify-center">
                <span className="text-white font-medium text-sm">
                  {user?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{user?.name}</p>
                <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
              </div>
            </div>
          </div>

          {isReadOnly && (
            <div className="mx-3 mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-center gap-2 text-amber-700">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-xs font-medium">Read-Only Mode</span>
              </div>
            </div>
          )}

          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {links.map((link) => {
              if (link.operatorOnly && user?.role !== "operator") return null;
              const Icon = link.icon;
              const isActive = location.pathname === link.href;
              return (
                <Link
                  key={link.href}
                  to={link.href}
                  onClick={onClose}
                  className={`sidebar-link ${isActive ? 'active' : ''}`}
                  data-testid={`nav-${link.label.toLowerCase()}`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-slate-200">
            <button
              onClick={handleLogout}
              className="sidebar-link w-full text-red-600 hover:bg-red-50 hover:text-red-700"
              data-testid="logout-btn"
            >
              <LogOut className="w-5 h-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};

export const AdminLayout = ({ children, title }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <AdminSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 lg:px-8 sticky top-0 z-30">
          <button 
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 hover:bg-slate-100 rounded-lg mr-4"
            data-testid="mobile-menu-btn"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-heading font-bold text-slate-900">{title}</h1>
        </header>
        <main className="flex-1 p-4 lg:p-8 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export const OperatorLayout = ({ children, title, isReadOnly = false }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, authAxios } = useAuth();
  const navigate = useNavigate();
  const isImpersonating = !!user?.impersonated_by;

  const handleReturnToAdmin = async () => {
    try {
      const res = await authAxios.post("/admin/return-from-impersonate");
      localStorage.setItem("token", res.data.access_token);
      window.location.href = "/admin/operators";
    } catch {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <OperatorSidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
        isReadOnly={isReadOnly}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {isImpersonating && (
          <div className="bg-indigo-600 text-white px-4 py-2 flex items-center justify-between text-sm sticky top-0 z-40" data-testid="impersonation-banner">
            <span>You are viewing this panel as <strong>{user.name}</strong> (impersonating)</span>
            <Button
              size="sm"
              variant="secondary"
              className="bg-white text-indigo-700 hover:bg-indigo-50 h-7 text-xs"
              onClick={handleReturnToAdmin}
              data-testid="return-to-admin-btn"
            >
              <LogOut className="w-3 h-3 mr-1" /> Return to Admin
            </Button>
          </div>
        )}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 lg:px-8 sticky top-0 z-30">
          <button 
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 hover:bg-slate-100 rounded-lg mr-4"
            data-testid="mobile-menu-btn"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-heading font-bold text-slate-900">{title}</h1>
        </header>
        <main className="flex-1 p-4 lg:p-8 overflow-auto">
          {isReadOnly && (
            <div className="read-only-banner mb-6 animate-fade-in">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                <div>
                  <p className="font-medium text-amber-800">Your account is in read-only mode</p>
                  <p className="text-sm text-amber-700">Please renew your subscription to continue using all features.</p>
                </div>
                <Button 
                  className="ml-auto bg-amber-600 hover:bg-amber-700" 
                  size="sm"
                  onClick={() => navigate("/operator/subscription")}
                  data-testid="renew-now-banner-btn"
                >
                  Renew Now
                </Button>
              </div>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
};
