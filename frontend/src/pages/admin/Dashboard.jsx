import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
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
  Receipt,
  UserCheck,
  UserX,
  Wallet,
  Cpu,
  MemoryStick,
  HardDrive,
  Network,
  RefreshCw,
  Server,
  ArrowDown,
  ArrowUp,
} from "lucide-react";

// ── System Health sub-components (defined outside to avoid nested component warning) ─

const gaugeColor = (pct) => {
  if (pct == null) return "bg-slate-200";
  if (pct >= 85) return "bg-red-500";
  if (pct >= 65) return "bg-amber-400";
  return "bg-emerald-500";
};
const gaugeText = (pct) => {
  if (pct == null) return "text-slate-400";
  if (pct >= 85) return "text-red-600";
  if (pct >= 65) return "text-amber-600";
  return "text-emerald-600";
};

const GaugeBar = ({ label, icon: Icon, percent, sub, iconColor }) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className={`w-7 h-7 rounded-md flex items-center justify-center ${iconColor}`}>
          <Icon className="w-4 h-4" />
        </div>
        <span className="text-sm font-medium text-slate-700">{label}</span>
      </div>
      <span className={`text-sm font-bold tabular-nums ${gaugeText(percent)}`}>
        {percent != null ? `${percent}%` : "—"}
      </span>
    </div>
    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${gaugeColor(percent)}`}
        style={{ width: `${Math.min(percent ?? 0, 100)}%` }}
      />
    </div>
    {sub && <p className="text-xs text-slate-500">{sub}</p>}
  </div>
);

const StatPill = ({ icon: Icon, label, value, iconBg }) => (
  <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
    <div className={`w-8 h-8 rounded-md flex items-center justify-center shrink-0 ${iconBg}`}>
      <Icon className="w-4 h-4" />
    </div>
    <div className="min-w-0">
      <p className="text-xs text-slate-500 truncate">{label}</p>
      <p className="text-sm font-semibold text-slate-800 truncate">{value}</p>
    </div>
  </div>
);

// ────────────────────────────────────────────────────────────────────────────

const AdminDashboard = () => {
  const { authAxios } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sysHealth, setSysHealth] = useState(null);
  const [sysLoading, setSysLoading] = useState(false);
  const [sysLastUpdated, setSysLastUpdated] = useState(null);

  // Define fetch functions BEFORE useEffect hooks
  const fetchDashboard = useCallback(async () => {
    try {
      const response = await authAxios.get("/admin/dashboard");
      setStats(response.data);
    } catch (error) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [authAxios]);

  const fetchSysHealth = useCallback(async () => {
    setSysLoading(true);
    try {
      const res = await authAxios.get("/admin/system/health");
      setSysHealth(res.data);
      setSysLastUpdated(new Date());
    } catch {
      // silent — non-critical
    } finally {
      setSysLoading(false);
    }
  }, [authAxios]);

  useEffect(() => {
    fetchDashboard();
    fetchSysHealth();
  }, [fetchDashboard, fetchSysHealth]);

  // Auto-refresh system health every 30 seconds
  useEffect(() => {
    const id = setInterval(fetchSysHealth, 30_000);
    return () => clearInterval(id);
  }, [fetchSysHealth]);

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

  const subscriberCards = [
    { title: "Total Subscribers", value: stats?.total_subscribers || 0, icon: Users, color: "bg-slate-100 text-slate-700", testid: "sub-total" },
    { title: "Active Subscribers", value: stats?.active_subscribers || 0, icon: UserCheck, color: "bg-emerald-100 text-emerald-700", testid: "sub-active" },
    { title: "Suspended Subscribers", value: stats?.suspended_subscribers || 0, icon: UserX, color: "bg-red-100 text-red-700", testid: "sub-suspended" },
    { title: "Invoice Charges / mo", value: fmt(stats?.approx_monthly_revenue), icon: Wallet, color: "bg-indigo-100 text-indigo-700", testid: "sub-approx-revenue", hint: "Invoice charge × active subscribers across all operators" },
  ];

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

        {/* Subscriber Overview */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Subscriber Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {subscriberCards.map((card) => {
              const Icon = card.icon;
              return (
                <Card key={card.testid} className="kpi-card card-hover" data-testid={`kpi-${card.testid}`} title={card.hint || ""}>
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

        {/* System Health */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-heading font-semibold text-slate-900">System Health</h2>
            <div className="flex items-center gap-2">
              {sysLastUpdated && (
                <span className="text-xs text-slate-400">
                  Updated {sysLastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={fetchSysHealth}
                disabled={sysLoading}
                className="h-7 px-2 text-xs"
              >
                <RefreshCw className={`w-3 h-3 mr-1 ${sysLoading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>

          {!sysHealth ? (
            <Card className="p-6 flex items-center justify-center text-slate-400 text-sm">
              {sysLoading ? "Loading system metrics…" : "System metrics unavailable"}
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Gauges: CPU, RAM, Disk */}
              <Card>
                <CardHeader className="pb-3 pt-4 px-5">
                  <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                    <Server className="w-4 h-4 text-slate-500" /> Resource Usage
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-5 space-y-4">
                  <GaugeBar
                    label="CPU"
                    icon={Cpu}
                    percent={sysHealth.cpu?.percent}
                    sub={`${sysHealth.cpu?.cores_physical ?? "?"} cores${sysHealth.cpu?.frequency_mhz ? ` · ${(sysHealth.cpu.frequency_mhz / 1000).toFixed(1)} GHz` : ""}`}
                    iconColor="bg-blue-100 text-blue-600"
                  />
                  <GaugeBar
                    label="RAM"
                    icon={MemoryStick}
                    percent={sysHealth.memory?.percent}
                    sub={`${sysHealth.memory?.used_human} used of ${sysHealth.memory?.total_human}`}
                    iconColor="bg-violet-100 text-violet-600"
                  />
                  <GaugeBar
                    label="Disk"
                    icon={HardDrive}
                    percent={sysHealth.disk?.percent}
                    sub={`${sysHealth.disk?.used_human} used · ${sysHealth.disk?.free_human} free of ${sysHealth.disk?.total_human}`}
                    iconColor="bg-amber-100 text-amber-600"
                  />
                  {sysHealth.swap?.total_bytes > 0 && (
                    <GaugeBar
                      label="Swap"
                      icon={MemoryStick}
                      percent={sysHealth.swap?.percent}
                      sub={`${sysHealth.swap?.used_human} of ${sysHealth.swap?.total_human}`}
                      iconColor="bg-slate-100 text-slate-500"
                    />
                  )}
                </CardContent>
              </Card>

              {/* Network + Disk I/O + Uptime */}
              <div className="space-y-4">
                {/* Network traffic */}
                <Card>
                  <CardHeader className="pb-2 pt-4 px-5">
                    <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                      <Network className="w-4 h-4 text-slate-500" /> Network (cumulative since boot)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-5 pb-4 grid grid-cols-2 gap-3">
                    <StatPill
                      icon={ArrowDown}
                      label="Data Received"
                      value={sysHealth.network?.recv_human ?? "—"}
                      iconBg="bg-emerald-100 text-emerald-600"
                    />
                    <StatPill
                      icon={ArrowUp}
                      label="Data Sent"
                      value={sysHealth.network?.sent_human ?? "—"}
                      iconBg="bg-blue-100 text-blue-600"
                    />
                    <StatPill
                      icon={ArrowDown}
                      label="Packets In"
                      value={(sysHealth.network?.packets_recv ?? 0).toLocaleString()}
                      iconBg="bg-teal-100 text-teal-600"
                    />
                    <StatPill
                      icon={ArrowUp}
                      label="Packets Out"
                      value={(sysHealth.network?.packets_sent ?? 0).toLocaleString()}
                      iconBg="bg-indigo-100 text-indigo-600"
                    />
                  </CardContent>
                </Card>

                {/* Disk I/O + Uptime */}
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-2 pt-4 px-5">
                      <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <HardDrive className="w-4 h-4 text-slate-500" /> Disk I/O
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-5 pb-4 space-y-2">
                      <StatPill
                        icon={ArrowDown}
                        label="Total Read"
                        value={sysHealth.disk?.read_human ?? "—"}
                        iconBg="bg-orange-100 text-orange-600"
                      />
                      <StatPill
                        icon={ArrowUp}
                        label="Total Write"
                        value={sysHealth.disk?.write_human ?? "—"}
                        iconBg="bg-rose-100 text-rose-600"
                      />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2 pt-4 px-5">
                      <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Server className="w-4 h-4 text-slate-500" /> Server Info
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-5 pb-4 space-y-2">
                      <StatPill
                        icon={Clock}
                        label="Uptime"
                        value={sysHealth.uptime?.human ?? "—"}
                        iconBg="bg-sky-100 text-sky-600"
                      />
                      <StatPill
                        icon={Cpu}
                        label="CPU Cores"
                        value={`${sysHealth.cpu?.cores_physical ?? "?"} physical`}
                        iconBg="bg-blue-100 text-blue-600"
                      />
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>
          )}
        </section>

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
