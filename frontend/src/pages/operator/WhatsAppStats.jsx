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
  Search,
  ChevronLeft,
  ChevronRight,
  Send,
  Eye,
  Clock,
} from "lucide-react";

// ─── Constants ────────────────────────────────────────────────────────────────

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

// ─── Delivery status badge (mirrors admin WhatsAppStats) ─────────────────────

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
  // sent / undefined — single tick
  return (
    <span className={`${base} bg-slate-50 text-slate-500`} title="Sent — awaiting delivery confirmation">
      <span className="font-bold">✓</span> Sent
    </span>
  );
}

// ─── Delivery timeline modal ──────────────────────────────────────────────────

function DeliveryTimelineModal({ log, onClose }) {
  if (!log) return null;
  const ds = log.delivery_status || "sent";
  const formatDate = (iso) => iso ? new Date(iso).toLocaleString() : null;

  const steps = [
    { key: "sent",      label: "Sent",      at: log.created_at,     reached: true },
    { key: "delivered", label: "Delivered", at: log.delivered_at,   reached: ["delivered", "read"].includes(ds) },
    { key: "read",      label: "Read",      at: log.read_at,        reached: ds === "read" },
  ];

  const statusColor = {
    read:      "text-blue-700 bg-blue-50 border-blue-200",
    delivered: "text-slate-700 bg-slate-50 border-slate-200",
    failed:    "text-red-700 bg-red-50 border-red-200",
    sent:      "text-slate-600 bg-slate-50 border-slate-200",
  }[ds] || "text-slate-600 bg-slate-50 border-slate-200";

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Send className="w-4 h-4" />
            Message Status
          </DialogTitle>
        </DialogHeader>

        {/* Status banner */}
        <div className={`rounded-lg border px-4 py-3 flex items-center gap-3 ${statusColor}`}>
          <DeliveryStatusBadge status={ds} />
          <div className="text-sm font-medium">
            {ds === "read"      && "Message read by recipient"}
            {ds === "delivered" && "Delivered to recipient's device"}
            {ds === "failed"    && "Delivery failed"}
            {ds === "sent"      && "Sent & accepted by WhatsApp API"}
          </div>
        </div>

        {/* Delivery timeline */}
        <div className="space-y-3 mt-1">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Delivery Timeline</p>
          <div className="relative pl-6 space-y-4">
            {/* Vertical line */}
            <div className="absolute left-2.5 top-1 bottom-1 w-0.5 bg-slate-200" />

            {steps.map((step) => (
              <div key={step.key} className="relative flex items-start gap-3">
                <div className={`absolute -left-4 mt-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center z-10
                  ${step.reached
                    ? "bg-green-500 border-green-500"
                    : "bg-white border-slate-300"}`}
                >
                  {step.reached && (
                    <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 12 12" fill="none">
                      <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-medium ${step.reached ? "text-slate-800" : "text-slate-400"}`}>
                    {step.label}
                  </p>
                  {step.at && step.reached ? (
                    <p className="text-xs text-slate-500 mt-0.5">{formatDate(step.at)}</p>
                  ) : (
                    <p className="text-xs text-slate-400 mt-0.5 italic">
                      {step.reached ? "" : "Not yet reached"}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Failed details */}
          {ds === "failed" && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 mt-2 space-y-1">
              <p className="text-xs font-semibold text-red-700">Failure Details</p>
              {log.failed_at && <p className="text-xs text-red-600">Failed at: {formatDate(log.failed_at)}</p>}
              {log.error_code && <p className="text-xs text-red-600">Code: {log.error_code}</p>}
              {log.error_title && <p className="text-xs text-red-600">{log.error_title}</p>}
            </div>
          )}
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs border-t pt-3 mt-1">
          {[
            ["Subscriber",  log.subscriber_name || "—"],
            ["Recipient",   log.recipient_phone],
            ["Category",    CATEGORY_LABELS[log.template_category] || log.template_category],
            ["Template",    log.template_name],
            ["Trigger",     TRIGGER_LABELS[log.trigger] || log.trigger || "—"],
            ["Invoice #",   log.invoice_number || "—"],
            ["Sent At",     formatDate(log.created_at)],
          ].map(([label, val]) => (
            <div key={label}>
              <p className="text-slate-400">{label}</p>
              <p className="text-slate-700 font-medium truncate" title={val}>{val || "—"}</p>
            </div>
          ))}
        </div>

        {!log.delivered_at && ds !== "failed" && (
          <p className="text-xs text-slate-400 mt-2 border-t pt-2">
            Delivery confirmations require WhatsApp webhook to be configured by admin.
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── Stat card ───────────────────────────────────────────────────────────────

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

// ─── Mini bar chart ───────────────────────────────────────────────────────────

function MiniBarChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-slate-400 text-sm">No data available</div>
    );
  }
  const maxVal = Math.max(...data.map(d => d.sent + d.failed), 1);
  return (
    <div className="flex items-end gap-1.5 h-24 px-1">
      {data.map((d, i) => {
        const totalH = ((d.sent + d.failed) / maxVal) * 100;
        const sentH  = (d.sent / (d.sent + d.failed || 1)) * totalH;
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

// ─── Main page ────────────────────────────────────────────────────────────────

export default function OperatorWhatsAppStats() {
  const { authAxios } = useAuth();

  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [logs, setLogs] = useState([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsPage, setLogsPage] = useState(1);
  const [logsTotalPages, setLogsTotalPages] = useState(1);
  const [logsLoading, setLogsLoading] = useState(false);

  // Filters
  const [filterStatus,         setFilterStatus]         = useState("all");
  const [filterDeliveryStatus, setFilterDeliveryStatus] = useState("all");
  const [filterCategory,       setFilterCategory]       = useState("all");
  const [filterSearch,         setFilterSearch]         = useState("");
  const [filterDateFrom,       setFilterDateFrom]       = useState("");
  const [filterDateTo,         setFilterDateTo]         = useState("");

  // Detail modal
  const [selectedLog, setSelectedLog] = useState(null);

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
      if (filterStatus         !== "all") params.status          = filterStatus;
      if (filterDeliveryStatus !== "all") params.delivery_status = filterDeliveryStatus;
      if (filterCategory       !== "all") params.template_category = filterCategory;
      if (filterSearch)  params.search   = filterSearch;
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo)   params.date_to   = filterDateTo;

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
  }, [authAxios, filterStatus, filterDeliveryStatus, filterCategory, filterSearch, filterDateFrom, filterDateTo]);

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
            subtitle={`${stats?.sent ?? 0} sent · ${stats?.failed ?? 0} failed`}
            icon={stats?.success_rate >= 90 ? CheckCircle2 : XCircle}
            color={stats?.success_rate >= 90 ? "green" : "red"}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Last 7 Days</CardTitle>
            </CardHeader>
            <CardContent>
              <MiniBarChart data={stats?.recent_7_days || []} />
              <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-green-400 inline-block" /> Sent</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-red-300 inline-block" /> Failed</span>
              </div>
            </CardContent>
          </Card>

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
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
              {/* Search */}
              <div className="relative col-span-2 md:col-span-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Phone / template / invoice…"
                  className="pl-9 h-9 text-sm"
                  value={filterSearch}
                  onChange={e => setFilterSearch(e.target.value)}
                />
              </div>

              {/* Send status */}
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Send Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Send Status</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>

              {/* Delivery status */}
              <Select value={filterDeliveryStatus} onValueChange={setFilterDeliveryStatus}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Delivery" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Delivery</SelectItem>
                  <SelectItem value="sent">Sent (API accepted)</SelectItem>
                  <SelectItem value="delivered">Delivered</SelectItem>
                  <SelectItem value="read">Read</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>

              {/* Category */}
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

              {/* Date range */}
              <div className="flex gap-2 col-span-2 md:col-span-1 lg:col-span-1">
                <Input type="date" className="h-9 text-sm flex-1" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)} title="From" />
                <Input type="date" className="h-9 text-sm flex-1" value={filterDateTo}   onChange={e => setFilterDateTo(e.target.value)}   title="To" />
              </div>
            </div>

            {/* Table */}
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Subscriber</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Trigger</TableHead>
                    <TableHead>Invoice</TableHead>
                    <TableHead>Delivery</TableHead>
                    <TableHead className="text-right">Detail</TableHead>
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
                      <TableRow key={log.id} className="hover:bg-slate-50">
                        <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                          {new Date(log.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div>
                            {log.subscriber_name && (
                              <p className="text-sm font-medium text-slate-800 leading-tight">{log.subscriber_name}</p>
                            )}
                            <p className="font-mono text-xs text-slate-500">{log.recipient_phone}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[log.template_category] || "bg-slate-100 text-slate-700"}`}>
                            {CATEGORY_LABELS[log.template_category] || log.template_category}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-slate-600">
                          {TRIGGER_LABELS[log.trigger] || log.trigger || "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-blue-600">
                          {log.invoice_number || "—"}
                        </TableCell>
                        <TableCell>
                          <DeliveryStatusBadge status={log.delivery_status || "sent"} />
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => setSelectedLog(log)}
                            title="View delivery details"
                          >
                            <Eye className="w-4 h-4 text-slate-500" />
                          </Button>
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
                  <Button variant="outline" size="icon" className="h-8 w-8"
                    onClick={() => handlePageChange(1)} disabled={logsPage <= 1}>«</Button>
                  <Button variant="outline" size="icon" className="h-8 w-8"
                    onClick={() => handlePageChange(logsPage - 1)} disabled={logsPage <= 1}>
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-sm text-slate-600 px-2">{logsPage}</span>
                  <Button variant="outline" size="icon" className="h-8 w-8"
                    onClick={() => handlePageChange(logsPage + 1)} disabled={logsPage >= logsTotalPages}>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                  <Button variant="outline" size="icon" className="h-8 w-8"
                    onClick={() => handlePageChange(logsTotalPages)} disabled={logsPage >= logsTotalPages}>»</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Delivery detail modal */}
      {selectedLog && (
        <DeliveryTimelineModal log={selectedLog} onClose={() => setSelectedLog(null)} />
      )}
    </OperatorLayout>
  );
}
