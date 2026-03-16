import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
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
import { Badge } from "../../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { toast } from "sonner";
import {
  AlertTriangle,
  AlertCircle,
  AlertOctagon,
  RefreshCw,
  Trash2,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  Server,
  User,
  ShieldAlert,
  Filter,
  X,
} from "lucide-react";

const ERROR_TYPES = [
  { value: "all", label: "All Types" },
  { value: "server_error", label: "Server Error (5xx)" },
  { value: "client_error", label: "Client Error (4xx)" },
  { value: "validation_error", label: "Validation Error" },
  { value: "unhandled_exception", label: "Unhandled Exception" },
  { value: "whatsapp_error", label: "WhatsApp Error" },
];

const TYPE_BADGE = {
  server_error: { color: "bg-red-100 text-red-800 border-red-200", icon: AlertOctagon },
  client_error: { color: "bg-amber-100 text-amber-800 border-amber-200", icon: AlertTriangle },
  validation_error: { color: "bg-blue-100 text-blue-800 border-blue-200", icon: AlertCircle },
  unhandled_exception: { color: "bg-purple-100 text-purple-800 border-purple-200", icon: ShieldAlert },
  whatsapp_error: { color: "bg-green-100 text-green-800 border-green-200", icon: Server },
};

const STATUS_COLOR = (code) => {
  if (code >= 500) return "bg-red-100 text-red-700";
  if (code >= 400) return "bg-amber-100 text-amber-700";
  if (code >= 300) return "bg-blue-100 text-blue-700";
  return "bg-slate-100 text-slate-700";
};

export default function ErrorLogs() {
  const { authAxios } = useAuth();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Filters
  const [errorType, setErrorType] = useState("all");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [statusCode, setStatusCode] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Detail dialog
  const [selectedLog, setSelectedLog] = useState(null);

  // Clear confirm
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [page, errorType, search, statusCode, dateFrom, dateTo]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("page", page);
      params.set("per_page", 50);
      if (errorType !== "all") params.set("error_type", errorType);
      if (search) params.set("search", search);
      if (statusCode) params.set("status_code", statusCode);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);

      const res = await authAxios.get(`/admin/error-logs?${params.toString()}`);
      setLogs(res.data.logs || []);
      setTotalPages(res.data.total_pages || 1);
      setTotal(res.data.total || 0);
    } catch (e) {
      toast.error("Failed to load error logs");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await authAxios.get("/admin/error-logs/stats");
      setStats(res.data);
    } catch { /* ignore */ }
  };

  const handleClearLogs = async () => {
    try {
      await authAxios.delete("/admin/error-logs");
      toast.success("All error logs cleared");
      setShowClearConfirm(false);
      setPage(1);
      fetchLogs();
      fetchStats();
    } catch (e) {
      toast.error("Failed to clear logs");
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const clearFilters = () => {
    setErrorType("all");
    setSearch("");
    setSearchInput("");
    setStatusCode("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const hasActiveFilters = errorType !== "all" || search || statusCode || dateFrom || dateTo;

  const formatDate = (iso) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("en-IN", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
    } catch { return iso; }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Error Logs</h1>
            <p className="text-slate-500 mt-1">
              Monitor and diagnose application errors across all modules.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => { fetchLogs(); fetchStats(); }}>
              <RefreshCw className="w-4 h-4 mr-1" /> Refresh
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setShowClearConfirm(true)}>
              <Trash2 className="w-4 h-4 mr-1" /> Clear All
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: "Total Errors", value: stats.total, color: "text-slate-800", bg: "bg-slate-50" },
              { label: "Today", value: stats.today, color: "text-blue-700", bg: "bg-blue-50" },
              { label: "Server (5xx)", value: stats.by_type?.server_error || 0, color: "text-red-700", bg: "bg-red-50" },
              { label: "Client (4xx)", value: stats.by_type?.client_error || 0, color: "text-amber-700", bg: "bg-amber-50" },
              { label: "Unhandled", value: stats.by_type?.unhandled_exception || 0, color: "text-purple-700", bg: "bg-purple-50" },
            ].map((s) => (
              <Card key={s.label} className={`${s.bg} border-0`}>
                <CardContent className="p-4">
                  <p className="text-xs text-slate-500 font-medium">{s.label}</p>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Filters */}
        <Card>
          <CardContent className="py-4 px-5">
            <div className="flex flex-wrap items-end gap-3">
              <form onSubmit={handleSearchSubmit} className="flex gap-2 flex-1 min-w-[200px]">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    placeholder="Search errors..."
                    className="pl-9"
                    data-testid="error-search"
                  />
                </div>
                <Button type="submit" variant="outline" size="icon">
                  <Search className="w-4 h-4" />
                </Button>
              </form>

              <div className="w-[180px]">
                <Select value={errorType} onValueChange={(v) => { setErrorType(v); setPage(1); }}>
                  <SelectTrigger data-testid="error-type-filter">
                    <SelectValue placeholder="Error Type" />
                  </SelectTrigger>
                  <SelectContent>
                    {ERROR_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="w-[100px]">
                <Input
                  value={statusCode}
                  onChange={(e) => { setStatusCode(e.target.value.replace(/\D/g, "")); setPage(1); }}
                  placeholder="Status"
                  data-testid="status-code-filter"
                />
              </div>

              <div>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                  className="w-[140px]"
                  data-testid="date-from-filter"
                />
              </div>
              <span className="text-sm text-slate-400 pb-2">to</span>
              <div>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                  className="w-[140px]"
                  data-testid="date-to-filter"
                />
              </div>

              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters} className="text-slate-500">
                  <X className="w-4 h-4 mr-1" /> Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card>
          <CardHeader className="py-3 px-5">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Filter className="w-4 h-4" />
                {total} error{total !== 1 ? "s" : ""} found
              </CardTitle>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                Page {page} of {totalPages}
                <Button variant="outline" size="icon" className="h-7 w-7" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="icon" className="h-7 w-7" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : logs.length === 0 ? (
              <div className="text-center py-12">
                <AlertTriangle className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500 font-medium">No error logs found</p>
                <p className="text-slate-400 text-sm mt-1">
                  {hasActiveFilters ? "Try adjusting your filters" : "Great! No errors have been recorded yet."}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[150px]">Timestamp</TableHead>
                      <TableHead className="w-[130px]">Type</TableHead>
                      <TableHead className="w-[60px]">Status</TableHead>
                      <TableHead className="w-[100px]">Method</TableHead>
                      <TableHead>Endpoint / Message</TableHead>
                      <TableHead className="w-[120px]">User</TableHead>
                      <TableHead className="w-[60px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => {
                      const typeInfo = TYPE_BADGE[log.error_type] || TYPE_BADGE.client_error;
                      const TypeIcon = typeInfo.icon;
                      return (
                        <TableRow key={log.id} className="hover:bg-slate-50/50 cursor-pointer" onClick={() => setSelectedLog(log)}>
                          <TableCell className="text-xs text-slate-500 font-mono whitespace-nowrap">
                            {formatDate(log.created_at)}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className={`text-xs ${typeInfo.color} border`}>
                              <TypeIcon className="w-3 h-3 mr-1" />
                              {log.error_type?.replace(/_/g, " ")}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${STATUS_COLOR(log.status_code)}`}>
                              {log.status_code}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="text-xs font-mono font-medium text-slate-600">
                              {log.request_method}
                            </span>
                          </TableCell>
                          <TableCell>
                            <div className="max-w-[400px]">
                              <p className="text-xs text-slate-600 font-mono truncate">{log.request_path || log.endpoint}</p>
                              <p className="text-xs text-slate-400 truncate mt-0.5">{log.message}</p>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1 text-xs text-slate-500">
                              <User className="w-3 h-3" />
                              <span className="truncate max-w-[80px]">{log.user_name || "System"}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={(e) => { e.stopPropagation(); setSelectedLog(log); }}>
                              <Eye className="w-4 h-4 text-slate-400" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pagination bottom */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft className="w-4 h-4 mr-1" /> Previous
            </Button>
            <span className="text-sm text-slate-500">Page {page} of {totalPages}</span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
              Next <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        )}

        {/* Detail Dialog */}
        <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                Error Details
              </DialogTitle>
            </DialogHeader>
            {selectedLog && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Error Type", value: selectedLog.error_type?.replace(/_/g, " ") },
                    { label: "Status Code", value: selectedLog.status_code },
                    { label: "Method", value: selectedLog.request_method },
                    { label: "Endpoint", value: selectedLog.request_path || selectedLog.endpoint },
                    { label: "User", value: `${selectedLog.user_name || "System"} (${selectedLog.user_role || "system"})` },
                    { label: "IP Address", value: selectedLog.ip_address || "N/A" },
                    { label: "Module", value: selectedLog.module || "N/A" },
                    { label: "Timestamp", value: formatDate(selectedLog.created_at) },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <p className="text-xs text-slate-400 font-medium">{label}</p>
                      <p className="text-sm text-slate-800 font-mono break-all">{value}</p>
                    </div>
                  ))}
                </div>

                <div>
                  <p className="text-xs text-slate-400 font-medium mb-1">Error Message</p>
                  <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-800 font-mono break-all whitespace-pre-wrap">
                    {selectedLog.message}
                  </div>
                </div>

                {selectedLog.stack_trace && (
                  <div>
                    <p className="text-xs text-slate-400 font-medium mb-1">Stack Trace</p>
                    <div className="bg-red-50 rounded-lg p-3 text-xs text-red-800 font-mono break-all whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                      {selectedLog.stack_trace}
                    </div>
                  </div>
                )}

                {selectedLog.extra_data && Object.keys(selectedLog.extra_data).length > 0 && (
                  <div>
                    <p className="text-xs text-slate-400 font-medium mb-1">Additional Data</p>
                    <div className="bg-blue-50 rounded-lg p-3 text-xs text-blue-800 font-mono break-all whitespace-pre-wrap">
                      {JSON.stringify(selectedLog.extra_data, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Clear Confirm Dialog */}
        <Dialog open={showClearConfirm} onOpenChange={setShowClearConfirm}>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle>Clear All Error Logs?</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-slate-500">
              This will permanently delete all error logs. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setShowClearConfirm(false)}>Cancel</Button>
              <Button variant="destructive" onClick={handleClearLogs}>Delete All</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
}
