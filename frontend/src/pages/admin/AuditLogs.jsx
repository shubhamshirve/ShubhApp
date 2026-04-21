import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent } from "../../components/ui/card";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
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
  ClipboardList, User, Eye, Search, X, ChevronLeft, ChevronRight,
  Filter, RefreshCw,
} from "lucide-react";

const PAGE_SIZE = 20;

const ACTION_OPTIONS = ["create", "update", "delete", "login", "payment", "trigger", "cron_executed"];
const ROLE_OPTIONS   = ["admin", "operator", "staff"];
const MODULE_OPTIONS = [
  "auth", "operators", "saas_plans", "subscribers", "invoices",
  "payment_gateways", "whatsapp_config", "settings", "addons",
  "staff", "announcements", "discount_codes", "cron_jobs", "backup",
];

const AdminAuditLogs = () => {
  const { authAxios } = useAuth();
  const [logs, setLogs]     = useState([]);
  const [total, setTotal]   = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage]     = useState(0);           // 0-indexed

  const [selectedLog, setSelectedLog] = useState(null);

  // Filter state
  const [search, setSearch]       = useState("");
  const [action, setAction]       = useState("all");
  const [role,   setRole]         = useState("all");
  const [module, setModule]       = useState("all");
  const [dateFrom, setDateFrom]   = useState("");
  const [dateTo,   setDateTo]     = useState("");

  // Build query string from current filters + page
  const buildQuery = useCallback((pg = page) => {
    const params = new URLSearchParams();
    params.set("skip",  String(pg * PAGE_SIZE));
    params.set("limit", String(PAGE_SIZE));
    if (search)            params.set("search",    search);
    if (action !== "all")  params.set("action",    action);
    if (role   !== "all")  params.set("role",      role);
    if (module !== "all")  params.set("module",    module);
    if (dateFrom)          params.set("date_from", dateFrom);
    if (dateTo)            params.set("date_to",   dateTo);
    return params.toString();
  }, [page, search, action, role, module, dateFrom, dateTo]);

  const fetchLogs = useCallback(async (pg = page) => {
    setLoading(true);
    try {
      const res = await authAxios.get(`/admin/audit-logs?${buildQuery(pg)}`);
      setLogs(res.data.logs || []);
      setTotal(res.data.total || 0);
    } catch {
      toast.error("Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [authAxios, buildQuery, page]);

  useEffect(() => {
    fetchLogs(page);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleApplyFilters = () => {
    setPage(0);
    fetchLogs(0);
  };

  const handleReset = () => {
    setSearch("");
    setAction("all");
    setRole("all");
    setModule("all");
    setDateFrom("");
    setDateTo("");
    setPage(0);
    // Fetch with cleared filters immediately
    setLoading(true);
    authAxios.get(`/admin/audit-logs?skip=0&limit=${PAGE_SIZE}`)
      .then(res => { setLogs(res.data.logs || []); setTotal(res.data.total || 0); })
      .catch(() => toast.error("Failed to load audit logs"))
      .finally(() => setLoading(false));
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ── helpers ──────────────────────────────────────────────────────────────

  const getActionBadge = (act) => {
    const colors = {
      create:  "bg-emerald-100 text-emerald-700",
      update:  "bg-blue-100 text-blue-700",
      delete:  "bg-red-100 text-red-700",
      login:   "bg-purple-100 text-purple-700",
      payment: "bg-amber-100 text-amber-700",
      trigger: "bg-indigo-100 text-indigo-700",
      cron_executed: "bg-teal-100 text-teal-700",
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[act] || "bg-slate-100 text-slate-700"}`}>
        {act}
      </span>
    );
  };

  const hasDetails = (log) =>
    (log.old_value && Object.keys(log.old_value).length > 0) ||
    (log.new_value && Object.keys(log.new_value).length > 0);

  const renderValue = (val) => {
    if (!val || typeof val !== "object" || Object.keys(val).length === 0) return null;
    return (
      <div className="space-y-1">
        {Object.entries(val).map(([k, v]) => (
          <div key={k} className="flex gap-2 text-xs">
            <span className="font-medium text-slate-600 min-w-[120px] shrink-0">{k}:</span>
            <span className="text-slate-800 break-all">
              {typeof v === "object" ? JSON.stringify(v) : String(v ?? "")}
            </span>
          </div>
        ))}
      </div>
    );
  };

  const activeFilterCount = [
    search, action !== "all" && action, role !== "all" && role,
    module !== "all" && module, dateFrom, dateTo,
  ].filter(Boolean).length;

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <AdminLayout title="Audit Logs">
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center justify-between">
          <p className="text-slate-500 text-sm">View all system activity and changes</p>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-full">
            {total.toLocaleString()} total records
          </span>
        </div>

        {/* ── Filter bar ─────────────────────────────────────────────────── */}
        <Card>
          <CardContent className="p-4">
            <div className="space-y-3">
              {/* Row 1: search + action + role + module */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="lg:col-span-1 relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <Input
                    placeholder="Search user, module, IP…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleApplyFilters()}
                    className="pl-9"
                  />
                </div>

                <Select value={action} onValueChange={setAction}>
                  <SelectTrigger>
                    <SelectValue placeholder="All Actions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Actions</SelectItem>
                    {ACTION_OPTIONS.map(a => (
                      <SelectItem key={a} value={a} className="capitalize">{a}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={role} onValueChange={setRole}>
                  <SelectTrigger>
                    <SelectValue placeholder="All Roles" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Roles</SelectItem>
                    {ROLE_OPTIONS.map(r => (
                      <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={module} onValueChange={setModule}>
                  <SelectTrigger>
                    <SelectValue placeholder="All Modules" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Modules</SelectItem>
                    {MODULE_OPTIONS.map(m => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Row 2: date range + buttons */}
              <div className="flex flex-wrap items-end gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-slate-500">From</Label>
                  <Input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="w-40 text-sm"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-slate-500">To</Label>
                  <Input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="w-40 text-sm"
                  />
                </div>

                <div className="flex gap-2 ml-auto">
                  {activeFilterCount > 0 && (
                    <Button variant="outline" size="sm" onClick={handleReset}>
                      <X className="w-3.5 h-3.5 mr-1" />
                      Clear
                      <span className="ml-1 bg-slate-200 text-slate-700 text-xs rounded-full px-1.5">
                        {activeFilterCount}
                      </span>
                    </Button>
                  )}
                  <Button size="sm" onClick={handleApplyFilters}>
                    <Filter className="w-3.5 h-3.5 mr-1" />
                    Apply Filters
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => fetchLogs(page)}>
                    <RefreshCw className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ── Table ──────────────────────────────────────────────────────── */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center h-48">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Module</TableHead>
                    <TableHead>IP Address</TableHead>
                    <TableHead className="text-center">Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-12 text-slate-500">
                        <ClipboardList className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                        No audit logs match your filters
                      </TableCell>
                    </TableRow>
                  ) : logs.map((log) => (
                    <TableRow key={log.id} className="hover:bg-slate-50">
                      <TableCell className="font-mono text-xs text-slate-500 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-slate-100 rounded-full flex items-center justify-center shrink-0">
                            <User className="w-3 h-3 text-slate-600" />
                          </div>
                          <span className="text-sm">{log.user_name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm capitalize">{log.role}</TableCell>
                      <TableCell>{getActionBadge(log.action)}</TableCell>
                      <TableCell className="text-sm">{log.module}</TableCell>
                      <TableCell className="font-mono text-xs text-slate-500">
                        {log.ip_address || "—"}
                      </TableCell>
                      <TableCell className="text-center">
                        {hasDetails(log) ? (
                          <Button
                            variant="ghost" size="sm"
                            className="h-7 px-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                            onClick={() => setSelectedLog(log)}
                          >
                            <Eye className="w-3.5 h-3.5 mr-1" /> Details
                          </Button>
                        ) : (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <p className="text-sm text-slate-500">
                Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total.toLocaleString()}
              </p>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline" size="sm"
                  disabled={page === 0}
                  onClick={() => setPage(p => p - 1)}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                {/* Page number pills — show up to 5 around current */}
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                  const start = Math.max(0, Math.min(page - 2, totalPages - 5));
                  const pg = start + i;
                  return (
                    <Button
                      key={pg}
                      variant={pg === page ? "default" : "outline"}
                      size="sm"
                      className="w-8 h-8 p-0"
                      onClick={() => setPage(pg)}
                    >
                      {pg + 1}
                    </Button>
                  );
                })}
                <Button
                  variant="outline" size="sm"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage(p => p + 1)}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Details Modal */}
      <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ClipboardList className="w-5 h-5" />
              Audit Log Details
            </DialogTitle>
            <DialogDescription>
              {selectedLog && (
                <span>
                  {new Date(selectedLog.created_at).toLocaleString()} · {selectedLog.user_name} · {selectedLog.module} · {selectedLog.action}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          {selectedLog && (
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "User",       value: selectedLog.user_name },
                  { label: "Role",       value: selectedLog.role },
                  { label: "Action",     value: selectedLog.action },
                  { label: "Module",     value: selectedLog.module },
                  { label: "IP Address", value: selectedLog.ip_address || "—" },
                  { label: "Timestamp",  value: new Date(selectedLog.created_at).toLocaleString() },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-slate-50 rounded-lg p-3">
                    <p className="text-xs text-slate-500 mb-1">{label}</p>
                    <p className="text-sm font-medium text-slate-800 break-all">{value}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedLog.old_value && Object.keys(selectedLog.old_value).length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-red-400" />
                      <p className="text-sm font-semibold text-slate-700">Before (Old Value)</p>
                    </div>
                    <div className="bg-red-50 border border-red-100 rounded-lg p-3">
                      {renderValue(selectedLog.old_value)}
                    </div>
                  </div>
                )}
                {selectedLog.new_value && Object.keys(selectedLog.new_value).length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-400" />
                      <p className="text-sm font-semibold text-slate-700">After (New Value)</p>
                    </div>
                    <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                      {renderValue(selectedLog.new_value)}
                    </div>
                  </div>
                )}
              </div>

              {!selectedLog.old_value && !selectedLog.new_value && (
                <p className="text-sm text-slate-500 text-center py-4">No change details recorded.</p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};

export default AdminAuditLogs;
