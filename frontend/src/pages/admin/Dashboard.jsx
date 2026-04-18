import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { toast } from "sonner";
import WelcomeModal from "../../components/WelcomeModal";
import {
  Building2,
  Users,
  Clock,
  AlertTriangle,
  Ban,
  Eye,
  IndianRupee,
  TrendingUp,
  Puzzle,
  Receipt
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
    { title: "Total Operators", value: stats?.total_operators || 0, icon: Building2, color: "bg-slate-100 text-slate-700" },
    { title: "Active Operators", value: stats?.active_operators || 0, icon: Users, color: "bg-emerald-100 text-emerald-700" },
    { title: "Trial Operators", value: stats?.trial_operators || 0, icon: Clock, color: "bg-blue-100 text-blue-700" },
    { title: "Suspended", value: stats?.suspended_operators || 0, icon: Ban, color: "bg-red-100 text-red-700" },
    { title: "Read-Only Mode", value: stats?.read_only_operators || 0, icon: Eye, color: "bg-amber-100 text-amber-700" },
    { title: "Expiring Soon", value: stats?.expiring_operators || 0, icon: AlertTriangle, color: "bg-orange-100 text-orange-700" }
  ];

  const fmt = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

  return (
    <AdminLayout title="Dashboard">
      <WelcomeModal />
      <div className="space-y-8 animate-fade-in">

        {/* Operator Overview */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Operator Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {kpiCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <Card key={index} className="kpi-card card-hover" data-testid={`kpi-${card.title.toLowerCase().replace(/\s+/g, "-")}`}>
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

        {/* Platform Revenue */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Platform Revenue</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* All-Time Revenue Hero */}
            <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white col-span-1 md:col-span-2" data-testid="total-platform-revenue">
              <CardContent className="p-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <p className="text-slate-300 text-sm mb-1">All-Time Platform Revenue</p>
                    <p className="text-4xl font-bold font-heading">
                      {fmt(stats?.total_saas_revenue + stats?.total_addon_revenue)}
                    </p>
                    <p className="text-slate-400 text-xs mt-1">
                      Subscriptions: {fmt(stats?.total_saas_revenue)} &nbsp;|&nbsp;
                      Add-ons: {fmt(stats?.total_addon_revenue)} &nbsp;|&nbsp;
                      GST: {fmt(stats?.total_gst_collected)}
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <div className="text-center">
                      <p className="text-2xl font-bold">{fmt(stats?.saas_revenue_this_month + stats?.addon_revenue_this_month)}</p>
                      <p className="text-slate-400 text-xs">This Month</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="kpi-card card-hover" data-testid="revenue-subscriptions">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <IndianRupee className="w-6 h-6" />
                </div>
                <div>
                  <p className="kpi-value">{fmt(stats?.saas_revenue_this_month)}</p>
                  <p className="kpi-label">Subscription Revenue (Month)</p>
                </div>
              </div>
            </Card>

            <Card className="kpi-card card-hover" data-testid="revenue-addons">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center">
                  <Puzzle className="w-6 h-6" />
                </div>
                <div>
                  <p className="kpi-value">{fmt(stats?.addon_revenue_this_month)}</p>
                  <p className="kpi-label">Add-on Revenue (Month)</p>
                </div>
              </div>
            </Card>

            <Card className="kpi-card card-hover" data-testid="revenue-gst">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
                  <TrendingUp className="w-6 h-6" />
                </div>
                <div>
                  <p className="kpi-value">{fmt(stats?.gst_collected_this_month)}</p>
                  <p className="kpi-label">GST Collected (Month)</p>
                </div>
              </div>
            </Card>
          </div>
        </section>

        {/* Recent SaaS Payments */}
        {stats?.recent_payments?.length > 0 && (
          <section>
            <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Recent Payments</h2>
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Operator</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Type</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Base</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">GST</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Total</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recent_payments.map((p, i) => (
                        <tr key={i} className="border-b border-slate-50 hover:bg-slate-50 transition-colors" data-testid={`payment-row-${i}`}>
                          <td className="px-4 py-3 font-medium text-slate-900">{p.operator_name}</td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                              p.item_type === "subscription"
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-purple-100 text-purple-700"
                            }`}>
                              {p.item_type === "subscription" ? "Subscription" : `Add-on: ${p.item_code}`}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-slate-700">₹{p.base_amount?.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-right text-slate-500">₹{p.gst_amount?.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-right font-semibold text-slate-900">₹{p.total_amount?.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-slate-500">
                            {p.created_at ? new Date(p.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </section>
        )}

        {/* Quick Actions */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => window.location.href = "/admin/operators"}>
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

            <Card className="p-4 hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => window.location.href = "/admin/saas-plans"}>
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

            <Card className="p-4 hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => window.location.href = "/admin/reports"}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Receipt className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Reports</p>
                  <p className="text-sm text-slate-500">Revenue & analytics</p>
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
