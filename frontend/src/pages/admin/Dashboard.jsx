import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { toast } from "sonner";
import {
  Building2,
  Users,
  Clock,
  AlertTriangle,
  Ban,
  Eye,
  IndianRupee,
  TrendingUp
} from "lucide-react";

const AdminDashboard = () => {
  const { authAxios } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await authAxios.get("/admin/dashboard");
      setStats(response.data);
    } catch (error) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </AdminLayout>
    );
  }

  const kpiCards = [
    {
      title: "Total Operators",
      value: stats?.total_operators || 0,
      icon: Building2,
      color: "bg-slate-100 text-slate-700"
    },
    {
      title: "Active Operators",
      value: stats?.active_operators || 0,
      icon: Users,
      color: "bg-emerald-100 text-emerald-700"
    },
    {
      title: "Trial Operators",
      value: stats?.trial_operators || 0,
      icon: Clock,
      color: "bg-blue-100 text-blue-700"
    },
    {
      title: "Suspended",
      value: stats?.suspended_operators || 0,
      icon: Ban,
      color: "bg-red-100 text-red-700"
    },
    {
      title: "Read-Only Mode",
      value: stats?.read_only_operators || 0,
      icon: Eye,
      color: "bg-amber-100 text-amber-700"
    },
    {
      title: "Expiring Soon",
      value: stats?.expiring_operators || 0,
      icon: AlertTriangle,
      color: "bg-orange-100 text-orange-700"
    }
  ];

  const revenueCards = [
    {
      title: "SaaS Revenue (This Month)",
      value: `₹${(stats?.saas_revenue_this_month || 0).toLocaleString('en-IN')}`,
      icon: IndianRupee,
      color: "bg-emerald-100 text-emerald-700"
    },
    {
      title: "GST Collected",
      value: `₹${(stats?.gst_collected || 0).toLocaleString('en-IN')}`,
      icon: TrendingUp,
      color: "bg-blue-100 text-blue-700"
    },
    {
      title: "Add-on Revenue",
      value: `₹${(stats?.addon_revenue || 0).toLocaleString('en-IN')}`,
      icon: TrendingUp,
      color: "bg-purple-100 text-purple-700"
    }
  ];

  return (
    <AdminLayout title="Dashboard">
      <div className="space-y-8 animate-fade-in">
        {/* KPI Section */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Operator Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {kpiCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <Card key={index} className="kpi-card card-hover" data-testid={`kpi-${card.title.toLowerCase().replace(/\s+/g, '-')}`}>
                  <div className={`w-10 h-10 rounded-lg ${card.color} flex items-center justify-center mb-3`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <p className="kpi-value">{card.value}</p>
                  <p className="kpi-label">{card.title}</p>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Revenue Section */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Revenue</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {revenueCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <Card key={index} className="kpi-card card-hover" data-testid={`revenue-${index}`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-lg ${card.color} flex items-center justify-center`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="kpi-value">{card.value}</p>
                      <p className="kpi-label">{card.title}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Quick Actions */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => window.location.href = '/admin/operators'}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Manage Operators</p>
                  <p className="text-sm text-slate-500">View and manage all operators</p>
                </div>
              </div>
            </Card>
            
            <Card className="p-4 hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => window.location.href = '/admin/saas-plans'}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">SaaS Plans</p>
                  <p className="text-sm text-slate-500">Create and manage plans</p>
                </div>
              </div>
            </Card>
            
            <Card className="p-4 hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => window.location.href = '/admin/audit-logs'}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Eye className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Audit Logs</p>
                  <p className="text-sm text-slate-500">View system activity</p>
                </div>
              </div>
            </Card>
            
            <Card className="p-4 bg-amber-50 border-amber-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="font-medium text-amber-900">{stats?.expiring_operators || 0} Expiring</p>
                  <p className="text-sm text-amber-700">Operators expiring in 7 days</p>
                </div>
              </div>
            </Card>
          </div>
        </section>
      </div>
    </AdminLayout>
  );
};

export default AdminDashboard;
