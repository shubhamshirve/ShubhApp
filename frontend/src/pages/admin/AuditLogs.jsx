import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
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
import { ClipboardList, User, Eye, ChevronRight, ChevronDown } from "lucide-react";

const AdminAuditLogs = () => {
  const { authAxios } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await authAxios.get("/admin/audit-logs?limit=100");
      setLogs(response.data);
    } catch (error) {
      toast.error("Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  const getActionBadge = (action) => {
    const colors = {
      create: "bg-emerald-100 text-emerald-700",
      update: "bg-blue-100 text-blue-700",
      delete: "bg-red-100 text-red-700",
      login: "bg-purple-100 text-purple-700",
      payment: "bg-amber-100 text-amber-700",
      trigger: "bg-indigo-100 text-indigo-700",
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[action] || "bg-slate-100 text-slate-700"}`}>
        {action}
      </span>
    );
  };

  const hasDetails = (log) => {
    return (log.old_value && Object.keys(log.old_value).length > 0) ||
           (log.new_value && Object.keys(log.new_value).length > 0);
  };

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

  if (loading) {
    return (
      <AdminLayout title="Audit Logs">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Audit Logs">
      <div className="space-y-6 animate-fade-in">
        <p className="text-slate-500">View all system activity and changes</p>

        <Card>
          <CardContent className="p-0">
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
                    <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                      <ClipboardList className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No audit logs found
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log) => (
                    <TableRow key={log.id} data-testid={`audit-row-${log.id}`}>
                      <TableCell className="font-mono text-xs text-slate-500">
                        {new Date(log.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-slate-100 rounded-full flex items-center justify-center">
                            <User className="w-3 h-3 text-slate-600" />
                          </div>
                          <span className="text-sm">{log.user_name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm capitalize">{log.role}</TableCell>
                      <TableCell>{getActionBadge(log.action)}</TableCell>
                      <TableCell className="text-sm">{log.module}</TableCell>
                      <TableCell className="font-mono text-xs text-slate-500">
                        {log.ip_address || "-"}
                      </TableCell>
                      <TableCell className="text-center">
                        {hasDetails(log) ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                            onClick={() => setSelectedLog(log)}
                          >
                            <Eye className="w-3.5 h-3.5 mr-1" />
                            Details
                          </Button>
                        ) : (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
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
              {/* Summary row */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "User", value: selectedLog.user_name },
                  { label: "Role", value: selectedLog.role },
                  { label: "Action", value: selectedLog.action },
                  { label: "Module", value: selectedLog.module },
                  { label: "IP Address", value: selectedLog.ip_address || "—" },
                  { label: "Timestamp", value: new Date(selectedLog.created_at).toLocaleString() },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-slate-50 rounded-lg p-3">
                    <p className="text-xs text-slate-500 mb-1">{label}</p>
                    <p className="text-sm font-medium text-slate-800 break-all">{value}</p>
                  </div>
                ))}
              </div>

              {/* Changes */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedLog.old_value && Object.keys(selectedLog.old_value).length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-red-400"></div>
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
                      <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
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
