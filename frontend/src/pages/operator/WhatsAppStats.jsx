import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
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
import { toast } from "sonner";
import {
  MessageSquare,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Calendar,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Send,
  Filter,
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
  cron: "Scheduled",
  cron_reminder: "Payment Reminders",
  cron_wallet: "Wallet Alerts",
  cron_expiry: "Expiry Notifications",
  cron_report: "Daily Reports",
  manual: "Manual",
  auto_invoice: "Auto Invoice (Cron)",
  auto_invoice_create: "Auto Invoice (Create)",
  first_invoice: "First Invoice",
  manual_announcement: "Announcement",
  payment_confirmation: "Payment Confirmed",
};

function StatCard({ title, value, subtitle, icon: Icon, color = "blue" }) {
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
                <div className="w-full bg-red-300 rounded-t-sm" style={{ height: `${(failedH / totalH) * 100}%` }} />
              )}
              <div className="w-full bg-green-400 rounded-b-sm" style={{ height: `${(sentH / totalH) * 100}%` }} />
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

export default function OperatorWhatsAppStats() {
  const { authAxios } = useAuth();

  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [logs, setLogs] = useState([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsPage, setLogsPage] = useState(1);
  const [logsTotalPages, setLogsTotalPages] = useState(1);
  const [logsLoading, setLogsLoading] = useState(false);

  const [filterStatus, setFilterStatus] = useState("all");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterSearch, setFilterSearch] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const res = await authAxios.get("/operator/whatsapp-stats");
      setStats(res.data);
    } catch {
      toast.error("Failed to load WhatsApp stats");
    } finally {
      setStatsLoading(false);
    }
  }, [authAxios]);

  const fetchLogs = useCallback(async (page = 1) => {
    setLogsLoading(true);
    try {
      const params = { page, per_page: 20 };
      if (filterStatus && filterStatus !== "all") params.status = filterStatus;
      if (filterCategory && filterCategory !== "all") params.template_category = filterCategory;
      if (filterSearch) params.search = filterSearch;
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo) params.date_to = filterDateTo;

      const res = await authAxios.get("/operator/whatsapp-message-logs", { params });
      setLogs(res.data.logs || []);
      setLogsTotal(res.data.total || 0);
      setLogsTotalPages(res.data.total_pages || 1);
      setLogsPage(res.data.page || page);
    } catch {
      toast.error("Failed to load message logs");
    } finally {
      setLogsLoading(false);
    }
  }, [authAxios, filterStatus, filterCategory, filterSearch, filterDateFrom, filterDateTo]);

  useEffect(() => { fetchStats(); }, [fetchStats]);
  useEffect(() => { fetchLogs(1); }, [fetchLogs]);

  const handlePageChange = (newPage) => {
    setLogsPage(newPage);
    fetchLogs(newPage);
  };

  if (statsLoading) {
    return (
      <OperatorLayout title="WhatsApp Stats">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      </OperatorLayout>
    );
  }

  return (
    <OperatorLayout title="WhatsApp Stats">
      <div className="space-y-6 animate-fade-in">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <p className="text-slate-500">WhatsApp messages sent to your subscribers</p>
          <Button variant="outline" size="sm" onClick={() => { fetchStats(); fetchLogs(1); }}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard title="Total Messages" value={stats?.total ?? 0} icon={MessageSquare} color="blue" />
          <StatCard title="Today" value={stats?.today ?? 0} icon={Calendar} color="purple" />
          <StatCard title="This Month" value={stats?.this_month ?? 0} icon={TrendingUp} color="amber" />
          <StatCard
            title="Success Rate"
            value={`${stats?.success_rate ?? 0}%`}
            subtitle={`${stats?.sent ?? 0} sent, ${stats?.failed ?? 0} failed`}
            icon={stats?.success_rate >= 90 ? CheckCircle2 : XCircle}
            color={stats?.success_rate >= 90 ? "green" : "red"}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 7-day chart */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Last 7 Days</CardTitle>
            </CardHeader>
            <CardContent>
              <MiniBarChart data={stats?.recent_7_days || []} />
              <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm bg-green-400 inline-block" /> Sent
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm bg-red-300 inline-block" /> Failed
                </span>
              </div>
            </CardContent>
          </Card>

          {/* By Category */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">By Category</CardTitle>
            </CardHeader>
            <CardContent>
              {stats?.by_category && Object.keys(stats.by_category).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(stats.by_category)
                    .sort(([, a], [, b]) => b - a)
                    .map(([cat, count]) => (
                      <div key={cat} className="flex items-center justify-between">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[cat] || "bg-slate-100 text-slate-700"}`}>
                          {CATEGORY_LABELS[cat] || cat}
                        </span>
                        <span className="text-sm font-semibold text-slate-700">{count}</span>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="text-center text-sm text-slate-400 py-6">No data yet</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Message Logs */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Send className="w-4 h-4" />
                Message Logs
                {logsTotal > 0 && (
                  <span className="ml-1 text-xs font-normal text-slate-400">({logsTotal} total)</span>
                )}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {/* Filters */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search phone / template…"
                  className="pl-9 h-9 text-sm"
                  value={filterSearch}
                  onChange={e => setFilterSearch(e.target.value)}
                />
              </div>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterCategory} onValueChange={setFilterCategory}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex gap-2 col-span-2 md:col-span-1">
                <Input
                  type="date"
                  className="h-9 text-sm flex-1"
                  value={filterDateFrom}
                  onChange={e => setFilterDateFrom(e.target.value)}
                  title="From date"
                />
                <Input
                  type="date"
                  className="h-9 text-sm flex-1"
                  value={filterDateTo}
                  onChange={e => setFilterDateTo(e.target.value)}
                  title="To date"
                />
              </div>
            </div>

            {/* Table */}
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Template</TableHead>
                    <TableHead>Trigger</TableHead>
                    <TableHead>Invoice</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logsLoading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto text-slate-400" />
                      </TableCell>
                    </TableRow>
                  ) : logs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-10 text-slate-500">
                        <MessageSquare className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                        No messages found
                      </TableCell>
                    </TableRow>
                  ) : (
                    logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                          {new Date(log.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="font-mono text-xs">{log.recipient_phone}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[log.template_category] || "bg-slate-100 text-slate-700"}`}>
                            {CATEGORY_LABELS[log.template_category] || log.template_category}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-slate-600 max-w-[120px] truncate" title={log.template_name}>
                          {log.template_name}
                        </TableCell>
                        <TableCell className="text-xs">
                          {TRIGGER_LABELS[log.trigger] || log.trigger || "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-blue-600">
                          {log.invoice_number || "—"}
                        </TableCell>
                        <TableCell>
                          {log.status === "sent" ? (
                            <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full border border-green-200">
                              <CheckCircle2 className="w-3 h-3" /> Sent
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-red-700 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">
                              <XCircle className="w-3 h-3" /> Failed
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {logsTotalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-slate-500">
                  Page {logsPage} of {logsTotalPages} · {logsTotal} total
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePageChange(1)}
                    disabled={logsPage <= 1}
                  >
                    «
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePageChange(logsPage - 1)}
                    disabled={logsPage <= 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-sm text-slate-600 px-2">{logsPage}</span>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePageChange(logsPage + 1)}
                    disabled={logsPage >= logsTotalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handlePageChange(logsTotalPages)}
                    disabled={logsPage >= logsTotalPages}
                  >
                    »
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </OperatorLayout>
  );
}
