import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Badge } from "../../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { toast } from "sonner";
import {
  MessageSquare,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Calendar,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Search,
  ChevronLeft,
  ChevronRight,
  BarChart2,
  Clock,
  Send,
  Filter,
  Eye,
} from "lucide-react";

const CATEGORY_COLORS = {
  invoice_notification: "bg-blue-100 text-blue-800",
  payment_reminder: "bg-amber-100 text-amber-800",
  payment_due_reminder: "bg-red-100 text-red-800",
  payment_confirmation: "bg-green-100 text-green-800",
  announcement: "bg-purple-100 text-purple-800",
  reminder: "bg-amber-100 text-amber-800",
  custom: "bg-slate-100 text-slate-800",
};

const CATEGORY_LABELS = {
  invoice_notification: "Invoice",
  payment_reminder: "Reminder",
  payment_due_reminder: "Payment Due",
  payment_confirmation: "Confirmation",
  announcement: "Announcement",
  reminder: "Reminder",
  custom: "Custom",
};

const TRIGGER_LABELS = {
  cron: "Scheduled (Legacy)",
  cron_reminder: "Payment Reminders",
  cron_wallet: "Wallet Alerts",
  cron_expiry: "Expiry Notifications",
  cron_report: "Daily Reports",
  manual: "Manual (Operator)",
  auto_invoice: "Auto Invoice (Cron)",
  auto_invoice_create: "Auto Invoice (Create)",
  first_invoice: "First Invoice",
  manual_announcement: "Announcement",
  payment_confirmation: "Payment Confirmed",
};

const TRIGGER_COLORS = {
  cron: "bg-slate-100 text-slate-700",
  cron_reminder: "bg-amber-100 text-amber-700",
  cron_wallet: "bg-orange-100 text-orange-700",
  cron_expiry: "bg-red-100 text-red-700",
  cron_report: "bg-indigo-100 text-indigo-700",
  manual: "bg-slate-100 text-slate-600",
  auto_invoice: "bg-blue-100 text-blue-700",
  auto_invoice_create: "bg-blue-100 text-blue-700",
  first_invoice: "bg-teal-100 text-teal-700",
  manual_announcement: "bg-purple-100 text-purple-700",
  payment_confirmation: "bg-green-100 text-green-700",
};

const DELIVERY_STATUS_LABELS = {
  sent: "Sent",
  delivered: "Delivered",
  read: "Read",
  failed: "Failed",
};

function DeliveryStatusBadge({ status }) {
  const base = "inline-flex items-center gap-1 text-xs font-medium px-1.5 py-0.5 rounded-full";
  if (status === "read") {
    return (
      <span className={`${base} bg-blue-50 text-blue-700`} title="Read by recipient">
        <span className="font-bold tracking-tighter">✓✓</span> Read
      </span>
    );
  }
  if (status === "delivered") {
    return (
      <span className={`${base} bg-slate-100 text-slate-600`} title="Delivered to device">
        <span className="font-bold tracking-tighter">✓✓</span> Delivered
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className={`${base} bg-red-50 text-red-600`}>
        <XCircle className="w-3 h-3" /> Failed
      </span>
    );
  }
  // sent (or undefined) — single tick
  return (
    <span className={`${base} bg-slate-50 text-slate-500`} title="Sent — awaiting delivery confirmation">
      <span className="font-bold">✓</span> Sent
    </span>
  );
}

function StatCard({ title, value, subtitle, icon: Icon, color = "blue", trend = null }) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    red: "bg-red-50 text-red-600",
    amber: "bg-amber-50 text-amber-600",
    purple: "bg-purple-50 text-purple-600",
    slate: "bg-slate-50 text-slate-600",
  };
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-slate-500">{title}</p>
            <p className="text-3xl font-bold text-slate-800 mt-1">{value}</p>
            {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
          </div>
          <div className={`p-2.5 rounded-lg ${colors[color]}`}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
        {trend !== null && (
          <div className="mt-3 flex items-center gap-1 text-xs">
            <TrendingUp className={`w-3 h-3 ${trend >= 0 ? "text-green-500" : "text-red-500"}`} />
            <span className={trend >= 0 ? "text-green-600" : "text-red-600"}>
              {trend >= 0 ? "+" : ""}{trend}% success rate
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MiniBarChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-slate-400 text-sm">
        No data available
      </div>
    );
  }
  const maxVal = Math.max(...data.map(d => d.sent + d.failed), 1);
  return (
    <div className="flex items-end gap-1.5 h-24 px-1">
      {data.map((d, i) => {
        const totalH = ((d.sent + d.failed) / maxVal) * 100;
        const sentH = (d.sent / (d.sent + d.failed || 1)) * totalH;
        const failedH = totalH - sentH;
        return (
          <div key={d.date || `bar-${i}`} className="flex-1 flex flex-col items-center gap-0.5 group relative">
            <div
              className="w-full rounded-t flex flex-col-reverse"
              style={{ height: `${Math.max(totalH, 2)}%` }}
              title={`${d.date}\nSent: ${d.sent}\nFailed: ${d.failed}`}
            >
              {failedH > 0 && (
                <div
                  className="w-full bg-red-300 rounded-t-sm"
                  style={{ height: `${(failedH / totalH) * 100}%` }}
                />
              )}
              <div
                className="w-full bg-green-400 rounded-b-sm"
                style={{ height: `${(sentH / totalH) * 100}%` }}
              />
            </div>
            <span className="text-[9px] text-slate-400 hidden group-hover:block absolute -bottom-4 whitespace-nowrap">
              {d.date?.slice(5)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function WhatsAppStats() {
  const { authAxios } = useAuth();

  // Stats
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Message logs
  const [logs, setLogs] = useState([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsPage, setLogsPage] = useState(1);
  const [logsTotalPages, setLogsTotalPages] = useState(1);
  const [logsLoading, setLogsLoading] = useState(false);

  // Message logs filters
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterDeliveryStatus, setFilterDeliveryStatus] = useState("all");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterSearch, setFilterSearch] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  // Error logs
  const [errorLogs, setErrorLogs] = useState([]);
  const [errorLogsLoading, setErrorLogsLoading] = useState(false);
  const [clearingLogs, setClearingLogs] = useState(false);
  const [selectedError, setSelectedError] = useState(null);
  // Message status detail
  const [selectedLog, setSelectedLog] = useState(null);
  const [logRefreshing, setLogRefreshing] = useState(false);

  // Tab
  const [activeTab, setActiveTab] = useState("message-logs");

  // Webhook events
  const [webhookEvents, setWebhookEvents] = useState([]);
  const [webhookEventsTotal, setWebhookEventsTotal] = useState(0);
  const [webhookEventsPage, setWebhookEventsPage] = useState(1);
  const [webhookEventsTotalPages, setWebhookEventsTotalPages] = useState(1);
  const [webhookEventsLoading, setWebhookEventsLoading] = useState(false);
  const [webhookEventFilter, setWebhookEventFilter] = useState("all");
  const [expandedEventId, setExpandedEventId] = useState(null);
  const [clearingWebhookEvents, setClearingWebhookEvents] = useState(false);

  // Diagnostics
  const [diagRunning, setDiagRunning] = useState(false);
  const [diagResult, setDiagResult] = useState(null);

  const fetchStats = useCallback(async () => {
    try {
      setStatsLoading(true);
      const res = await authAxios.get("/admin/whatsapp-stats");
      setStats(res.data);
    } catch {
      toast.error("Failed to load WhatsApp stats");
    } finally {
      setStatsLoading(false);
    }
  }, [authAxios]);

  const fetchLogs = useCallback(async (page = 1) => {
    try {
      setLogsLoading(true);
      const params = new URLSearchParams({ page, per_page: 20 });
      if (filterStatus && filterStatus !== "all") params.append("status", filterStatus);
      if (filterDeliveryStatus && filterDeliveryStatus !== "all") params.append("delivery_status", filterDeliveryStatus);
      if (filterCategory && filterCategory !== "all") params.append("template_category", filterCategory);
      if (filterSearch) params.append("search", filterSearch);
      if (filterDateFrom) params.append("date_from", filterDateFrom);
      if (filterDateTo) params.append("date_to", filterDateTo);

      const res = await authAxios.get(`/admin/whatsapp-message-logs?${params.toString()}`);
      setLogs(res.data.logs || []);
      setLogsTotal(res.data.total || 0);
      setLogsTotalPages(res.data.total_pages || 1);
      setLogsPage(page);
    } catch {
      toast.error("Failed to load message logs");
    } finally {
      setLogsLoading(false);
    }
  }, [authAxios, filterStatus, filterDeliveryStatus, filterCategory, filterSearch, filterDateFrom, filterDateTo]);

  const fetchErrorLogs = useCallback(async () => {
    try {
      setErrorLogsLoading(true);
      const res = await authAxios.get("/admin/error-logs?per_page=20&module=whatsapp");
      setErrorLogs(res.data.logs || []);
    } catch {
      toast.error("Failed to load WhatsApp error logs");
    } finally {
      setErrorLogsLoading(false);
    }
  }, [authAxios]);

  const fetchWebhookEvents = useCallback(async (page = 1, filter = webhookEventFilter) => {
    try {
      setWebhookEventsLoading(true);
      const params = new URLSearchParams({ page, per_page: 20 });
      if (filter && filter !== "all") params.append("event_type", filter);
      const res = await authAxios.get(`/admin/webhook-events?${params.toString()}`);
      setWebhookEvents(res.data.events || []);
      setWebhookEventsTotal(res.data.total || 0);
      setWebhookEventsPage(res.data.page || 1);
      setWebhookEventsTotalPages(res.data.total_pages || 1);
    } catch {
      toast.error("Failed to load webhook events");
    } finally {
      setWebhookEventsLoading(false);
    }
  }, [authAxios, webhookEventFilter]);

  const runDiagnostics = useCallback(async () => {
    try {
      setDiagRunning(true);
      setDiagResult(null);
      const res = await authAxios.post("/admin/webhook-self-test");
      setDiagResult(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Diagnostics failed");
    } finally {
      setDiagRunning(false);
    }
  }, [authAxios]);

  useEffect(() => {
    fetchStats();
    fetchErrorLogs();
  }, [fetchStats, fetchErrorLogs]);

  useEffect(() => {
    fetchLogs(1);
  }, [fetchLogs]);

  useEffect(() => {
    if (activeTab === "webhook-events") {
      fetchWebhookEvents(1);
    }
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClearMessageLogs = async () => {
    if (!window.confirm("Clear all WhatsApp message logs? This cannot be undone.")) return;
    try {
      setClearingLogs(true);
      const res = await authAxios.delete("/admin/whatsapp-message-logs");
      toast.success(res.data.message);
      fetchStats();
      fetchLogs(1);
    } catch {
      toast.error("Failed to clear logs");
    } finally {
      setClearingLogs(false);
    }
  };

  const handleClearWebhookEvents = async () => {
    if (!window.confirm("Clear all webhook event logs? This cannot be undone.")) return;
    try {
      setClearingWebhookEvents(true);
      const res = await authAxios.delete("/admin/webhook-events");
      toast.success(res.data.message);
      fetchWebhookEvents(1);
    } catch {
      toast.error("Failed to clear webhook events");
    } finally {
      setClearingWebhookEvents(false);
    }
  };

  const handleApplyFilters = () => {
    fetchLogs(1);
  };

  const handleResetFilters = () => {
    setFilterStatus("all");
    setFilterDeliveryStatus("all");
    setFilterCategory("all");
    setFilterSearch("");
    setFilterDateFrom("");
    setFilterDateTo("");
  };

  const handleOpenLog = useCallback((log) => {
    setSelectedLog(log);
    setLogRefreshing(false);
  }, []);

  const refreshSelectedLog = useCallback(async () => {
    if (!selectedLog?.id) return;
    try {
      setLogRefreshing(true);
      const res = await authAxios.get(`/admin/whatsapp-message-logs/${selectedLog.id}`);
      setSelectedLog(res.data);
    } catch {
      toast.error("Failed to refresh message status");
    } finally {
      setLogRefreshing(false);
    }
  }, [authAxios, selectedLog]);

  const sortedCategories = useMemo(() =>
    stats?.by_category
      ? Object.entries(stats.by_category).sort((a, b) => b[1] - a[1])
      : [],
    [stats]
  );

  const formatDate = (isoStr) => {
    if (!isoStr) return "—";
    try {
      return new Date(isoStr).toLocaleString("en-IN", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: true,
      });
    } catch { return isoStr; }
  };

  return (
    <AdminLayout title="WhatsApp Stats">
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">WhatsApp API Stats & Reports</h2>
            <p className="text-sm text-slate-500 mt-1">
              Track WhatsApp message delivery, API stats, and error logs.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                fetchStats();
                fetchLogs(logsPage);
                fetchErrorLogs();
                if (activeTab === "webhook-events") fetchWebhookEvents(webhookEventsPage);
              }}
              className="gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
            <Button
              variant="outline"
              onClick={handleClearMessageLogs}
              disabled={clearingLogs}
              className="gap-2 text-red-600 border-red-200 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4" />
              {clearingLogs ? "Clearing..." : "Clear Logs"}
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        {statsLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Card key={`skeleton-${i}`}>
                <CardContent className="p-5">
                  <div className="animate-pulse space-y-2">
                    <div className="h-3 bg-slate-200 rounded w-24" />
                    <div className="h-8 bg-slate-200 rounded w-16" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : stats ? (
          <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Total Messages"
              value={stats.total?.toLocaleString() || "0"}
              subtitle="All time"
              icon={MessageSquare}
              color="blue"
            />
            <StatCard
              title="Sent Today"
              value={stats.today?.toLocaleString() || "0"}
              subtitle="Messages today"
              icon={Send}
              color="green"
            />
            <StatCard
              title="This Month"
              value={stats.this_month?.toLocaleString() || "0"}
              subtitle="Messages this month"
              icon={Calendar}
              color="purple"
            />
            <StatCard
              title="Success Rate"
              value={`${stats.success_rate || 0}%`}
              subtitle={`${stats.sent || 0} sent · ${stats.failed || 0} failed`}
              icon={TrendingUp}
              color={stats.success_rate >= 90 ? "green" : stats.success_rate >= 70 ? "amber" : "red"}
              trend={stats.success_rate}
            />
          </div>
          {/* Automated vs Manual Breakdown */}
          {stats.by_trigger && Object.keys(stats.by_trigger).length > 0 && (() => {
            const manualCount = stats.by_trigger["manual"] || 0;
            const automated = Object.entries(stats.by_trigger)
              .filter(([t]) => t !== "manual")
              .reduce((s, [, c]) => s + c, 0);
            return (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Card className="border-indigo-100 bg-indigo-50/30">
                  <CardContent className="p-4">
                    <p className="text-xs font-medium text-indigo-600 mb-1">Automated (All)</p>
                    <p className="text-2xl font-bold text-indigo-800">{automated.toLocaleString()}</p>
                    <p className="text-[11px] text-indigo-400 mt-0.5">By software / cron jobs</p>
                  </CardContent>
                </Card>
                <Card className="border-slate-100 bg-slate-50/30">
                  <CardContent className="p-4">
                    <p className="text-xs font-medium text-slate-600 mb-1">Manual (Operator)</p>
                    <p className="text-2xl font-bold text-slate-800">{manualCount.toLocaleString()}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">Triggered by operator</p>
                  </CardContent>
                </Card>
                {Object.entries(stats.by_trigger)
                  .filter(([t]) => t !== "manual" && t !== "cron")
                  .sort((a, b) => b[1] - a[1])
                  .map(([trigger, count]) => (
                    <Card key={trigger} className="border-slate-100">
                      <CardContent className="p-4">
                        <p className="text-xs font-medium text-slate-600 mb-1">{TRIGGER_LABELS[trigger] || trigger}</p>
                        <p className="text-2xl font-bold text-slate-800">{count.toLocaleString()}</p>
                        <p className="text-[11px] text-slate-400 mt-0.5">Auto triggered</p>
                      </CardContent>
                    </Card>
                  ))
                }
              </div>
            );
          })()}
          </>
        ) : null}

        {/* Activity Chart + Breakdown */}
        {stats && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* 7-day activity */}
            <Card className="lg:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-slate-400" />
                  Last 7 Days Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                {stats.recent_7_days && stats.recent_7_days.length > 0 ? (
                  <div>
                    <MiniBarChart data={stats.recent_7_days} />
                    <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-2 bg-green-400 rounded-sm inline-block" /> Sent
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-2 bg-red-300 rounded-sm inline-block" /> Failed
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-7 gap-1">
                      {stats.recent_7_days.map((d, i) => (
                        <div key={d.date || `day-${i}`} className="text-center">
                          <p className="text-[10px] text-slate-400">{d.date?.slice(5)}</p>
                          <p className="text-xs font-medium text-green-600">{d.sent}</p>
                          {d.failed > 0 && <p className="text-xs text-red-500">-{d.failed}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-24 text-slate-400 text-sm">
                    <div className="text-center">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      <p>No message data for last 7 days</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Breakdown */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-slate-700">By Category</CardTitle>
              </CardHeader>
              <CardContent>
                {stats.by_category && Object.keys(stats.by_category).length > 0 ? (
                  <div className="space-y-2">
                    {sortedCategories.map(([cat, count]) => (
                      <div key={cat} className="flex items-center justify-between">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[cat] || "bg-slate-100 text-slate-700"}`}>
                          {CATEGORY_LABELS[cat] || cat}
                        </span>
                        <span className="text-sm font-semibold text-slate-700">{count.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 text-center py-4">No data</p>
                )}

                {stats.by_trigger && Object.keys(stats.by_trigger).length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <p className="text-xs text-slate-500 font-medium mb-2">By Trigger Source</p>
                    <div className="space-y-1.5">
                      {Object.entries(stats.by_trigger).sort((a, b) => b[1] - a[1]).map(([trigger, count]) => (
                        <div key={trigger} className="flex items-center justify-between text-xs">
                          <span className={`px-2 py-0.5 rounded-full font-medium ${TRIGGER_COLORS[trigger] || "bg-slate-100 text-slate-600"}`}>
                            {TRIGGER_LABELS[trigger] || trigger}
                          </span>
                          <span className="font-semibold text-slate-700">{count.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* ── Tab Navigation ─────────────────────────────────────────────── */}
        <div className="border-b border-slate-200">
          <nav className="-mb-px flex gap-0 overflow-x-auto">
            {[
              { id: "message-logs", label: "Message Logs", count: logsTotal },
              { id: "webhook-events", label: "Webhook Events", count: webhookEventsTotal },
              { id: "error-logs", label: "Error Logs", count: errorLogs.length },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? "border-green-600 text-green-700"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                }`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${
                    activeTab === tab.id ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
                  }`}>
                    {tab.count.toLocaleString()}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* ── Tab: Message Logs ──────────────────────────────────────────── */}
        {activeTab === "message-logs" && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquare className="w-4 h-4 text-green-600" />
                Message Logs
                <span className="text-xs font-normal text-slate-400 ml-1">({logsTotal.toLocaleString()} total)</span>
              </CardTitle>
            </div>

            {/* Filters */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-2 mt-3">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                <Input
                  placeholder="Search phone, invoice..."
                  value={filterSearch}
                  onChange={(e) => setFilterSearch(e.target.value)}
                  className="pl-7 h-8 text-xs"
                  onKeyDown={(e) => e.key === "Enter" && handleApplyFilters()}
                  data-testid="whatsapp-logs-filter-search"
                />
              </div>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="h-8 text-xs" data-testid="whatsapp-logs-filter-status"><SelectValue placeholder="Send Status" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Send Status</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterDeliveryStatus} onValueChange={setFilterDeliveryStatus}>
                <SelectTrigger className="h-8 text-xs" data-testid="whatsapp-logs-filter-delivery"><SelectValue placeholder="Delivery" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Delivery</SelectItem>
                  <SelectItem value="sent">Sent (no receipt)</SelectItem>
                  <SelectItem value="delivered">Delivered</SelectItem>
                  <SelectItem value="read">Read</SelectItem>
                  <SelectItem value="failed">Failed at delivery</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterCategory} onValueChange={setFilterCategory}>
                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Category" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  <SelectItem value="invoice_notification">Invoice Notification</SelectItem>
                  <SelectItem value="payment_reminder">Payment Reminder</SelectItem>
                  <SelectItem value="payment_due_reminder">Payment Due Reminder</SelectItem>
                  <SelectItem value="payment_confirmation">Payment Confirmation</SelectItem>
                  <SelectItem value="announcement">Announcement</SelectItem>
                </SelectContent>
              </Select>
              <Input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="h-8 text-xs"
                placeholder="From date"
              />
              <Input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                className="h-8 text-xs"
                placeholder="To date"
              />
              <div className="flex gap-1">
                <Button size="sm" onClick={handleApplyFilters} className="h-8 px-3 gap-1 flex-1" data-testid="whatsapp-logs-filter-apply">
                  <Filter className="w-3 h-3" />
                  Apply
                </Button>
                <Button size="sm" variant="outline" onClick={handleResetFilters} className="h-8 px-2">
                  ×
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {logsLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
              </div>
            ) : logs.length === 0 ? (
              <div className="text-center py-12">
                <MessageSquare className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500 font-medium">No message logs found</p>
                <p className="text-slate-400 text-sm mt-1">
                  WhatsApp messages sent will appear here
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead>Date & Time</TableHead>
                      <TableHead>Recipient</TableHead>
                      <TableHead>Template</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Invoice</TableHead>
                      <TableHead>Trigger</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-20 text-center">View</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id} className="hover:bg-slate-50">
                        <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                          {formatDate(log.created_at)}
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="text-sm font-mono text-slate-700">{log.recipient_phone || "—"}</p>
                            {log.wa_id && log.wa_id !== log.recipient_phone && (
                              <p className="text-xs text-slate-400 font-mono">{log.wa_id}</p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <code className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded text-xs font-mono">
                            {log.template_name || "—"}
                          </code>
                        </TableCell>
                        <TableCell>
                          {log.template_category ? (
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[log.template_category] || "bg-slate-100 text-slate-700"}`}>
                              {CATEGORY_LABELS[log.template_category] || log.template_category}
                            </span>
                          ) : "—"}
                        </TableCell>
                        <TableCell>
                          {log.invoice_number ? (
                            <span className="text-xs text-slate-600 font-medium">{log.invoice_number}</span>
                          ) : "—"}
                        </TableCell>
                        <TableCell>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TRIGGER_COLORS[log.trigger] || "bg-slate-100 text-slate-600"}`}>
                            {TRIGGER_LABELS[log.trigger] || log.trigger || "—"}
                          </span>
                        </TableCell>
                        <TableCell>
                          {log.status === "failed" ? (
                            <span className="flex items-center gap-1 text-red-600 text-xs font-medium">
                              <XCircle className="w-3.5 h-3.5" />
                              Failed
                            </span>
                          ) : (
                            <DeliveryStatusBadge status={log.delivery_status || "sent"} />
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenLog(log)}
                            className="h-7 w-7 p-0 text-slate-400 hover:text-blue-600"
                            title="View message status"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Pagination — always visible */}
            {!logsLoading && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
                <p className="text-xs text-slate-500">
                  Page {logsPage} of {logsTotalPages} · {logsTotal.toLocaleString()} total
                </p>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchLogs(1)}
                    disabled={logsPage <= 1 || logsLoading}
                    className="h-7 px-2 text-xs"
                  >
                    «
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchLogs(logsPage - 1)}
                    disabled={logsPage <= 1 || logsLoading}
                    className="h-7 px-2"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </Button>
                  {/* Page number pills */}
                  {Array.from({ length: Math.min(5, logsTotalPages) }, (_, i) => {
                    const start = Math.max(1, Math.min(logsPage - 2, logsTotalPages - 4));
                    const p = start + i;
                    return p <= logsTotalPages ? (
                      <Button
                        key={p}
                        variant={p === logsPage ? "default" : "outline"}
                        size="sm"
                        onClick={() => fetchLogs(p)}
                        disabled={logsLoading}
                        className="h-7 w-7 p-0 text-xs"
                      >
                        {p}
                      </Button>
                    ) : null;
                  })}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchLogs(logsPage + 1)}
                    disabled={logsPage >= logsTotalPages || logsLoading}
                    className="h-7 px-2"
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchLogs(logsTotalPages)}
                    disabled={logsPage >= logsTotalPages || logsLoading}
                    className="h-7 px-2 text-xs"
                  >
                    »
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
        )} {/* end message-logs tab */}

        {/* ── Tab: Webhook Events ────────────────────────────────────────── */}
        {activeTab === "webhook-events" && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="text-green-600 font-mono text-xs bg-green-50 px-2 py-1 rounded border border-green-200">POST /api/webhooks/whatsapp</span>
                Webhook Events
                <span className="text-xs font-normal text-slate-400 ml-1">({webhookEventsTotal.toLocaleString()} received)</span>
              </CardTitle>
              <div className="flex items-center gap-2">
                <select
                  value={webhookEventFilter}
                  onChange={(e) => {
                    setWebhookEventFilter(e.target.value);
                    fetchWebhookEvents(1, e.target.value);
                  }}
                  className="text-xs border border-slate-200 rounded-md px-2 py-1.5 bg-white text-slate-600 focus:outline-none focus:ring-1 focus:ring-green-500"
                >
                  <option value="all">All Events</option>
                  <option value="status_update">Status Updates</option>
                  <option value="incoming_message">Incoming Messages</option>
                  <option value="other">Other</option>
                </select>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fetchWebhookEvents(webhookEventsPage)}
                  disabled={webhookEventsLoading}
                  className="gap-1 h-8 text-xs"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${webhookEventsLoading ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearWebhookEvents}
                  disabled={clearingWebhookEvents}
                  className="gap-1 h-8 text-xs text-red-600 border-red-200 hover:bg-red-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  {clearingWebhookEvents ? "Clearing..." : "Clear"}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {webhookEventsLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
              </div>
            ) : webhookEvents.length === 0 ? (
              <div className="p-6 space-y-6">
                {/* ── Diagnostic Panel ───────────────────────────────── */}
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl mt-0.5">🔍</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-amber-800 text-sm">No webhook events received yet</p>
                      <p className="text-amber-700 text-xs mt-1">
                        Run the self-test below to identify what's misconfigured, then follow the step-by-step Meta setup guide.
                      </p>
                    </div>
                    <Button
                      onClick={runDiagnostics}
                      disabled={diagRunning}
                      size="sm"
                      className="shrink-0 bg-amber-600 hover:bg-amber-700 text-white gap-1.5 h-8 text-xs"
                    >
                      {diagRunning ? (
                        <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Running…</>
                      ) : (
                        <><span>🧪</span> Run Self-Test</>
                      )}
                    </Button>
                  </div>

                  {/* Diagnostic Results */}
                  {diagResult && (
                    <div className="mt-4 space-y-2">
                      <p className={`text-xs font-semibold ${diagResult.all_pass ? "text-green-700" : "text-red-700"}`}>
                        {diagResult.all_pass ? "✅ All checks passed — webhook is correctly configured." : "⚠️ Some checks failed — see details below."}
                      </p>
                      {diagResult.results.map((r, i) => (
                        <div key={i} className={`rounded-lg border px-3 py-2.5 text-xs ${r.pass ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
                          <div className="flex items-start gap-2">
                            <span className="mt-0.5 shrink-0">{r.pass ? "✅" : "❌"}</span>
                            <div className="min-w-0">
                              <p className={`font-medium ${r.pass ? "text-green-800" : "text-red-800"}`}>{r.check}</p>
                              <p className={`mt-0.5 leading-relaxed ${r.pass ? "text-green-700" : "text-red-700"}`}>{r.detail}</p>
                              {r.fix_steps && r.fix_steps.length > 0 && (
                                <ul className="mt-1.5 space-y-1 list-disc list-inside text-red-700">
                                  {r.fix_steps.map((s, j) => <li key={j}>{s}</li>)}
                                </ul>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Webhook URL copy box */}
                      {diagResult.public_webhook_url && (
                        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
                          <p className="text-xs font-semibold text-slate-700 mb-1">📋 Callback URL to paste in Meta:</p>
                          <div className="flex items-center gap-2">
                            <code className="flex-1 text-[11px] bg-slate-50 border border-slate-200 rounded px-2 py-1.5 break-all text-slate-800 select-all font-mono">
                              {diagResult.public_webhook_url}
                            </code>
                            <button
                              onClick={() => { navigator.clipboard?.writeText(diagResult.public_webhook_url); toast.success("URL copied!"); }}
                              className="shrink-0 text-xs text-blue-600 hover:underline font-medium"
                            >
                              Copy
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* ── Step-by-Step Meta Setup Guide ──────────────────── */}
                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <p className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
                    <span>📘</span> Step-by-Step Meta Webhook Setup Guide
                  </p>
                  <ol className="space-y-3">
                    {[
                      {
                        step: "1",
                        title: "Set the Webhook Verify Token in this app",
                        body: "Go to Admin → Settings → WhatsApp Configuration. Set a Webhook Verify Token (any secret string, e.g. my-secret-123). Save the configuration.",
                        icon: "⚙️",
                      },
                      {
                        step: "2",
                        title: "Open Meta for Developers",
                        body: "Go to https://developers.facebook.com → Your App → WhatsApp → Configuration.",
                        icon: "🌐",
                        link: "https://developers.facebook.com",
                        linkLabel: "Open Meta Developers →",
                      },
                      {
                        step: "3",
                        title: "Set the Callback URL",
                        body: "Paste your app's webhook URL into the Callback URL field. Click 'Run Self-Test' above to see the exact URL. It looks like: https://your-domain.com/api/webhooks/whatsapp",
                        icon: "🔗",
                      },
                      {
                        step: "4",
                        title: "Set the Verify Token",
                        body: "Enter the SAME verify token you saved in Step 1. Click 'Verify and Save'. Meta will call your webhook URL with a GET request — if the token matches, verification succeeds.",
                        icon: "🔑",
                      },
                      {
                        step: "5",
                        title: "Subscribe to the 'messages' field",
                        body: "After verification, click 'Manage' next to the webhook. Enable (subscribe) the 'messages' field. This tells Meta to send delivery status callbacks (sent → delivered → read) to your webhook.",
                        icon: "✉️",
                      },
                      {
                        step: "6",
                        title: "Verify App Mode — must be LIVE",
                        body: "In Meta for Developers, ensure your app is set to LIVE mode (not Development). In Development mode, webhooks only fire for test phone numbers. Switch to Live mode from the top bar of your app dashboard.",
                        icon: "🚀",
                      },
                      {
                        step: "7",
                        title: "Send a test message and check here",
                        body: "Send a WhatsApp invoice message from the Invoices page. Come back here and click Refresh — you should see a new 'Status Update' event appear within a few seconds.",
                        icon: "✅",
                      },
                    ].map((item) => (
                      <li key={item.step} className="flex gap-3">
                        <div className="shrink-0 w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-sm font-bold text-slate-600">
                          {item.step}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
                            <span>{item.icon}</span> {item.title}
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">{item.body}</p>
                          {item.link && (
                            <a href={item.link} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline mt-0.5 inline-block">
                              {item.linkLabel}
                            </a>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            ) : (
              <div>
                {/* Compact diagnostics bar when events present */}
                <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-4 flex-wrap">
                    <p className="text-xs text-slate-500">
                      {diagResult ? (
                        diagResult.all_pass
                          ? <span className="text-green-700 font-medium">✅ Self-test passed — webhook correctly configured</span>
                          : <span className="text-red-700 font-medium">⚠️ Self-test found issues — click Diagnose</span>
                      ) : (
                        "Run a self-test to verify webhook configuration"
                      )}
                    </p>
                    {/* orphan summary across all loaded events */}
                    {(() => {
                      const totalOrphans = webhookEvents.reduce((acc, e) => acc + (e.orphan_count || 0), 0);
                      const totalMatched = webhookEvents.reduce((acc, e) => acc + (e.matched_count || 0), 0);
                      if (totalOrphans > 0) return (
                        <span className="text-xs font-medium text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                          ⚠ {totalOrphans} orphan{totalOrphans > 1 ? "s" : ""} — status NOT applied
                        </span>
                      );
                      if (totalMatched > 0) return (
                        <span className="text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">
                          ✓ {totalMatched} status{totalMatched > 1 ? "es" : ""} applied
                        </span>
                      );
                      return null;
                    })()}
                  </div>
                  <Button
                    onClick={runDiagnostics}
                    disabled={diagRunning}
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs gap-1.5"
                  >
                    {diagRunning ? <RefreshCw className="w-3 h-3 animate-spin" /> : <span>🧪</span>}
                    {diagRunning ? "Running…" : "Diagnose"}
                  </Button>
                </div>

                {/* Orphan explanation banner */}
                {webhookEvents.some(e => (e.orphan_count || 0) > 0) && (
                  <div className="mx-4 mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800 space-y-1.5">
                    <p className="font-semibold flex items-center gap-1.5">⚠️ Orphan Events Detected — Status Updates Not Being Applied</p>
                    <p>Webhook events are being <strong>received</strong> but the <code className="bg-red-100 px-1 rounded">message_id</code> in these events does not match any record in the Message Logs.</p>
                    <p className="font-medium mt-1">Most likely causes:</p>
                    <ol className="list-decimal list-inside space-y-0.5 text-red-700">
                      <li>Messages were sent from a <strong>different phone number / WABA</strong> than the one sending the webhooks. Verify that the Phone Number ID in Settings matches the number used to send messages.</li>
                      <li>The message was sent <strong>before logging was implemented</strong> in the current app version.</li>
                      <li>The <code className="bg-red-100 px-1 rounded">log_whatsapp_message()</code> call failed silently when the message was sent — check backend error logs.</li>
                    </ol>
                    <p className="mt-1 text-red-600">→ To confirm: Compare the <code className="bg-red-100 px-1 rounded">msg_id</code> shown in the orphan event with the message_id in Message Logs for the same recipient.</p>
                  </div>
                )}

                {/* Show diagnostic results inline if issues found */}
                {diagResult && !diagResult.all_pass && (
                  <div className="px-4 py-3 bg-red-50 border-b border-red-100 space-y-2">
                    {diagResult.results.filter(r => !r.pass).map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <span>❌</span>
                        <div>
                          <span className="font-medium text-red-800">{r.check}: </span>
                          <span className="text-red-700">{r.detail}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50">
                        <TableHead className="w-36">Received At</TableHead>
                        <TableHead className="w-32">Event Type</TableHead>
                        <TableHead className="w-24 text-center">Events</TableHead>
                        <TableHead>Status Details</TableHead>
                        <TableHead className="w-16 text-center">Payload</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {webhookEvents.map((evt) => (
                        <>
                          <TableRow key={evt.id} className="hover:bg-slate-50">
                            <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                              {formatDate(evt.received_at)}
                            </TableCell>
                            <TableCell>
                              {evt.event_type === "status_update" ? (
                                <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-green-50 text-green-700">
                                  <span className="font-bold tracking-tighter">✓✓</span> Status Update
                                </span>
                              ) : evt.event_type === "incoming_message" ? (
                                <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700">
                                  💬 Incoming Msg
                                </span>
                              ) : (
                                <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600">
                                  Other
                                </span>
                              )}
                            </TableCell>
                            <TableCell className="text-center">
                              {evt.status_count > 0 ? (
                                <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                                  {evt.status_count}
                                </span>
                              ) : evt.incoming_message_count > 0 ? (
                                <span className="text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
                                  {evt.incoming_message_count} msg
                                </span>
                              ) : (
                                <span className="text-xs text-slate-400">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {evt.statuses && evt.statuses.length > 0 ? (
                                <div className="space-y-1">
                                  {evt.statuses.slice(0, 3).map((s, i) => (
                                    <div key={i} className="flex items-center gap-2 flex-wrap">
                                      <DeliveryStatusBadge status={s.status} />
                                      <code className="text-[10px] text-slate-400 font-mono truncate max-w-[120px]" title={s.msg_id}>
                                        {s.msg_id ? s.msg_id.slice(0, 26) + "…" : "—"}
                                      </code>
                                      {s.recipient_id && (
                                        <span className="text-[10px] text-slate-400">{s.recipient_id}</span>
                                      )}
                                      {/* ✓ matched vs ⚠ orphan indicator */}
                                      {s.matched === true ? (
                                        <span className="text-[10px] font-semibold text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded" title="Log found and delivery_status updated">✓ matched</span>
                                      ) : s.matched === false ? (
                                        <span className="text-[10px] font-semibold text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded" title="No message log found for this ID — status was NOT applied">⚠ orphan</span>
                                      ) : null}
                                    </div>
                                  ))}
                                  {evt.statuses.length > 3 && (
                                    <p className="text-[10px] text-slate-400">+{evt.statuses.length - 3} more</p>
                                  )}
                                </div>
                              ) : (
                                <span className="text-xs text-slate-400">No status data</span>
                              )}
                            </TableCell>
                            <TableCell className="text-center">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setExpandedEventId(expandedEventId === evt.id ? null : evt.id)}
                                className="h-7 w-7 p-0 text-slate-400 hover:text-blue-600"
                                title="View raw payload"
                              >
                                <Eye className={`w-4 h-4 ${expandedEventId === evt.id ? "text-blue-600" : ""}`} />
                              </Button>
                            </TableCell>
                          </TableRow>
                          {expandedEventId === evt.id && (
                            <TableRow key={`${evt.id}-expanded`}>
                              <TableCell colSpan={5} className="bg-slate-50 p-0">
                                <div className="p-4 space-y-3">
                                  <div className="flex items-center justify-between">
                                    <p className="text-xs font-semibold text-slate-600">Raw Webhook Payload</p>
                                    <button
                                      onClick={() => {
                                        navigator.clipboard?.writeText(JSON.stringify(evt.raw_payload, null, 2));
                                        toast.success("Payload copied to clipboard");
                                      }}
                                      className="text-xs text-blue-600 hover:underline"
                                    >
                                      Copy JSON
                                    </button>
                                  </div>
                                  <pre className="bg-slate-900 text-green-300 text-[11px] rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-72 overflow-y-auto leading-relaxed font-mono">
                                    {JSON.stringify(evt.raw_payload, null, 2)}
                                  </pre>
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                        </>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                {webhookEventsTotalPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
                    <p className="text-xs text-slate-500">
                      Page {webhookEventsPage} of {webhookEventsTotalPages} · {webhookEventsTotal.toLocaleString()} total
                    </p>
                    <div className="flex items-center gap-1">
                      <Button variant="outline" size="sm" onClick={() => fetchWebhookEvents(webhookEventsPage - 1)} disabled={webhookEventsPage <= 1} className="h-7 px-2">
                        <ChevronLeft className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => fetchWebhookEvents(webhookEventsPage + 1)} disabled={webhookEventsPage >= webhookEventsTotalPages} className="h-7 px-2">
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        )} {/* end webhook-events tab */}

        {/* ── Tab: Error Logs ────────────────────────────────────────────── */}
        {activeTab === "error-logs" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              WhatsApp Error Logs
              <span className="text-xs font-normal text-slate-400 ml-1">Recent API errors</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {errorLogsLoading ? (
              <div className="flex items-center justify-center h-24">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-slate-900" />
              </div>
            ) : errorLogs.length === 0 ? (
              <div className="text-center py-10">
                <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <p className="text-slate-500 text-sm">No WhatsApp errors found</p>
                <p className="text-slate-400 text-xs mt-1">Great — no API errors logged</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead>Date</TableHead>
                      <TableHead>Error Type</TableHead>
                      <TableHead>Module</TableHead>
                      <TableHead>Message</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead className="w-16 text-center">View</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {errorLogs.map((err) => (
                      <TableRow key={err.id} className="hover:bg-slate-50">
                        <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                          {formatDate(err.created_at)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="destructive" className="text-xs">
                            {err.error_type || "error"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <code className="text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                            {err.module || "—"}
                          </code>
                        </TableCell>
                        <TableCell>
                          <p className="text-xs text-slate-700 max-w-xs truncate">
                            {err.message || "—"}
                          </p>
                        </TableCell>
                        <TableCell>
                          <span className="text-xs text-slate-500">{err.user_name || "System"}</span>
                        </TableCell>
                        <TableCell className="text-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedError(err)}
                            className="h-7 w-7 p-0 text-slate-400 hover:text-blue-600"
                            title="View full error"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
        )} {/* end error-logs tab */}
      </div>

      {/* ── Message Status Detail Dialog ────────────────────────────────── */}
      <Dialog open={!!selectedLog} onOpenChange={(v) => !v && setSelectedLog(null)}>
        <DialogContent className="max-w-lg w-full max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <MessageSquare className="w-4 h-4 text-green-600" />
              Message Status
              <Button
                variant="ghost"
                size="sm"
                onClick={refreshSelectedLog}
                disabled={logRefreshing}
                className="ml-auto h-7 w-7 p-0 text-slate-400 hover:text-blue-600"
                title="Refresh status from server"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${logRefreshing ? "animate-spin" : ""}`} />
              </Button>
            </DialogTitle>
          </DialogHeader>

          {selectedLog && (
            <div className="space-y-4 text-sm">
              {/* Status banner */}
              {selectedLog.status === "sent" ? (
                <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                  <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />
                  <div>
                    <p className="font-semibold text-green-800">
                      {selectedLog.message_id ? "Sent & API Accepted" : "Sent (No Receipt)"}
                    </p>
                    <p className="text-xs text-green-600 mt-0.5">
                      {selectedLog.message_id
                        ? "WhatsApp API accepted the message and issued a message ID."
                        : "Message was sent but no message ID was returned by the API."}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                  <XCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-red-800">Failed to Send</p>
                    {selectedLog.error_message && (
                      <p className="text-xs text-red-600 mt-1 whitespace-pre-wrap break-words">
                        {selectedLog.error_message}
                      </p>
                    )}
                    {(selectedLog.error_code !== undefined && selectedLog.error_code !== null) && (
                      <p className="text-[11px] text-red-500 mt-1 font-mono">
                        Meta error code: {selectedLog.error_code}
                        {selectedLog.error_title ? ` — ${selectedLog.error_title}` : ""}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Delivery Timeline */}
              {selectedLog.status === "sent" && (
                <div className="bg-white border border-slate-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-slate-600 mb-3 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" /> Delivery Timeline
                  </p>
                  {(() => {
                    const ds = selectedLog.delivery_status || "sent";
                    const failed = ds === "failed";
                    const timeline = [
                      { key: "sent", label: "Sent", at: selectedLog.created_at, reached: true },
                      { key: "delivered", label: "Delivered", at: selectedLog.delivered_at, reached: ["delivered", "read"].includes(ds) },
                      { key: "read", label: "Read", at: selectedLog.read_at, reached: ds === "read" },
                    ];
                    return (
                      <div className="space-y-2">
                        {timeline.map((step) => (
                          <div key={step.key} className="flex items-center gap-3">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                              step.reached
                                ? (step.key === "read" ? "bg-blue-500 text-white" : "bg-green-500 text-white")
                                : "bg-slate-200 text-slate-400"
                            }`}>
                              {step.key === "sent" ? "✓" : "✓✓"}
                            </div>
                            <div className="flex-1">
                              <p className={`text-xs font-medium ${step.reached ? "text-slate-700" : "text-slate-400"}`}>
                                {step.label}
                              </p>
                              <p className="text-[11px] text-slate-400">
                                {step.reached ? formatDate(step.at) : "Pending"}
                              </p>
                            </div>
                          </div>
                        ))}
                        {failed && (
                          <div className="flex items-start gap-3 pt-2 border-t border-slate-100">
                            <div className="w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center shrink-0">
                              <XCircle className="w-3.5 h-3.5" />
                            </div>
                            <div className="flex-1">
                              <p className="text-xs font-medium text-red-700">Failed at delivery</p>
                              <p className="text-[11px] text-red-500">{formatDate(selectedLog.failed_at)}</p>
                              {(selectedLog.error_code !== undefined && selectedLog.error_code !== null) && (
                                <p className="text-[11px] text-red-500 mt-0.5 font-mono">
                                  Meta error code: {selectedLog.error_code}
                                  {selectedLog.error_title ? ` — ${selectedLog.error_title}` : ""}
                                </p>
                              )}
                              {selectedLog.error_message && !selectedLog.error_title && (
                                <p className="text-[11px] text-red-500 mt-0.5 whitespace-pre-wrap break-words">
                                  {selectedLog.error_message}
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                        {!failed && ds === "sent" && (
                          <p className="text-[11px] text-slate-400 italic pt-1">
                            Awaiting delivery confirmation from WhatsApp.{" "}
                            {!selectedLog.delivered_at && "If delivery webhooks are not configured, only Sent will appear here."}
                          </p>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Details grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Sent At</p>
                  <p className="font-medium text-slate-700 text-xs">{formatDate(selectedLog.created_at)}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Trigger</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TRIGGER_COLORS[selectedLog.trigger] || "bg-slate-100 text-slate-600"}`}>
                    {TRIGGER_LABELS[selectedLog.trigger] || selectedLog.trigger || "—"}
                  </span>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Recipient Phone</p>
                  <p className="font-mono text-slate-700 text-xs break-all">{selectedLog.recipient_phone || "—"}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">WA ID (Resolved)</p>
                  <p className="font-mono text-slate-700 text-xs break-all">{selectedLog.wa_id || "—"}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Template</p>
                  <code className="bg-white border border-slate-200 text-slate-700 px-1.5 py-0.5 rounded text-xs font-mono break-all">
                    {selectedLog.template_name || "—"}
                  </code>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Category</p>
                  {selectedLog.template_category ? (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[selectedLog.template_category] || "bg-slate-100 text-slate-700"}`}>
                      {CATEGORY_LABELS[selectedLog.template_category] || selectedLog.template_category}
                    </span>
                  ) : <span className="text-slate-400 text-xs">—</span>}
                </div>
                {selectedLog.invoice_number && (
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                    <p className="text-xs text-slate-400 mb-0.5">Invoice #</p>
                    <p className="font-semibold text-slate-700 text-xs">{selectedLog.invoice_number}</p>
                  </div>
                )}
                {selectedLog.operator_id && (
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                    <p className="text-xs text-slate-400 mb-0.5">Operator ID</p>
                    <p className="font-mono text-slate-500 text-[10px] break-all">{selectedLog.operator_id}</p>
                  </div>
                )}
              </div>

              {/* Message ID — full width */}
              {selectedLog.message_id && (
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-1">WhatsApp Message ID</p>
                  <code className="text-xs text-slate-600 font-mono break-all">{selectedLog.message_id}</code>
                  <p className="text-[10px] text-slate-400 mt-1">
                    This ID confirms the message was accepted by the WhatsApp API. Delivery to device depends on the recipient's connection.
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between pt-1 border-t border-slate-100">
                <p className="text-[11px] text-slate-400 italic">
                  {logRefreshing ? "Refreshing..." : "Click ↺ to get the latest delivery status"}
                </p>
                <Button variant="outline" size="sm" onClick={() => setSelectedLog(null)}>Close</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ── Error Detail Dialog ─────────────────────────────────────────── */}
      <Dialog open={!!selectedError} onOpenChange={(v) => !v && setSelectedError(null)}>
        <DialogContent className="max-w-2xl w-full max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              Error Log Detail
            </DialogTitle>
          </DialogHeader>

          {selectedError && (
            <div className="space-y-4 mt-1 text-sm">
              {/* Meta row */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Date & Time</p>
                  <p className="font-medium text-slate-700">{formatDate(selectedError.created_at)}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Reported By</p>
                  <p className="font-medium text-slate-700">{selectedError.user_name || "System"}</p>
                  {selectedError.user_role && (
                    <p className="text-xs text-slate-400">{selectedError.user_role}</p>
                  )}
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Error Type</p>
                  <Badge variant="destructive" className="text-xs mt-0.5">
                    {selectedError.error_type || "error"}
                  </Badge>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-0.5">Module</p>
                  <code className="text-xs bg-white border border-slate-200 text-slate-700 px-1.5 py-0.5 rounded break-all">
                    {selectedError.module || "—"}
                  </code>
                </div>
              </div>

              {/* Endpoint */}
              {(selectedError.endpoint || selectedError.request_path) && (
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-1">Endpoint</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {selectedError.request_method && (
                      <span className="text-xs font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                        {selectedError.request_method}
                      </span>
                    )}
                    <code className="text-xs text-slate-600 break-all">
                      {selectedError.endpoint || selectedError.request_path}
                    </code>
                    {selectedError.status_code && (
                      <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                        selectedError.status_code >= 500 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                      }`}>
                        {selectedError.status_code}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Error message */}
              <div className="bg-red-50 rounded-lg p-3 border border-red-100">
                <p className="text-xs text-red-400 mb-1 font-medium">Error Message</p>
                <p className="text-sm text-red-800 whitespace-pre-wrap break-words leading-relaxed">
                  {selectedError.message || "—"}
                </p>
              </div>

              {/* Stack trace / extra data */}
              {selectedError.stack_trace && (
                <div>
                  <p className="text-xs text-slate-500 font-medium mb-1">Stack Trace</p>
                  <pre className="bg-slate-900 text-slate-200 text-xs rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-64 overflow-y-auto leading-relaxed">
                    {selectedError.stack_trace}
                  </pre>
                </div>
              )}

              {selectedError.extra_data && Object.keys(selectedError.extra_data).length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 font-medium mb-1">Extra Data</p>
                  <pre className="bg-slate-900 text-slate-200 text-xs rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-48 overflow-y-auto leading-relaxed">
                    {JSON.stringify(selectedError.extra_data, null, 2)}
                  </pre>
                </div>
              )}

              <div className="flex justify-end pt-2 border-t">
                <Button variant="outline" onClick={() => setSelectedError(null)}>Close</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
