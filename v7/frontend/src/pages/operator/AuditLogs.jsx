import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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
import { ClipboardList, Eye, RefreshCw } from "lucide-react";

const OperatorAuditLogs = () => {
  const { authAxios } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await authAxios.get("/operator/audit-logs?limit=100");
      setLogs(res.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error("Audit Logs add-on is not enabled for your plan.");
      } else {
        toast.error("Failed to load audit logs");
      }
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (iso) => new Date(iso).toLocaleString("en-IN");

  const getActionBadge = (action) => {
    const colors = {
      create: "bg-emerald-100 text-emerald-700",
      update: "bg-blue-100 text-blue-700",
      delete: "bg-red-100 text-red-700",
      payment: "bg-purple-100 text-purple-700",
    };
    const cls = colors[action?.toLowerCase()] || "bg-slate-100 text-slate-700";
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${cls}`}>
        {action}
      </span>
    );
  };

  if (loading) {
    return (
      <OperatorLayout title="Audit Logs">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  return (
    <OperatorLayout title="Audit Logs">
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <p className="text-slate-500 text-sm">Track all changes made in your operator account</p>
          <Button variant="outline" size="sm" onClick={fetchLogs} data-testid="refresh-logs-btn">
            <RefreshCw className="w-4 h-4 mr-1" /> Refresh
          </Button>
        </div>

        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Module</TableHead>
                  <TableHead className="w-[80px]">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-10 text-slate-500">
                      <ClipboardList className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No audit logs found
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log) => (
                    <TableRow key={log.id} data-testid={`audit-row-${log.id}`}>
                      <TableCell className="text-sm text-slate-500">{formatDate(log.created_at)}</TableCell>
                      <TableCell>
                        <div>
                          <span className="font-medium text-sm">{log.user_name}</span>
                          <span className="text-xs text-slate-400 block capitalize">{log.role}</span>
                        </div>
                      </TableCell>
                      <TableCell>{getActionBadge(log.action)}</TableCell>
                      <TableCell className="text-sm capitalize">{log.module?.replace(/_/g, " ")}</TableCell>
                      <TableCell>
                        {(log.old_value || log.new_value) && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setSelectedLog(log)}
                            data-testid={`view-log-${log.id}`}
                          >
                            <Eye className="w-4 h-4 text-slate-500" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Detail Dialog */}
        <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
          <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ClipboardList className="w-5 h-5" />
                Audit Log Details
              </DialogTitle>
            </DialogHeader>
            {selectedLog && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-slate-500">Action:</span> <span className="font-medium capitalize">{selectedLog.action}</span></div>
                  <div><span className="text-slate-500">Module:</span> <span className="font-medium capitalize">{selectedLog.module?.replace(/_/g, " ")}</span></div>
                  <div><span className="text-slate-500">User:</span> <span className="font-medium">{selectedLog.user_name}</span></div>
                  <div><span className="text-slate-500">Time:</span> <span className="font-medium">{formatDate(selectedLog.created_at)}</span></div>
                </div>
                {selectedLog.old_value && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 mb-1">Before</p>
                    <pre className="bg-red-50 border border-red-100 rounded p-3 text-xs overflow-auto max-h-40">
                      {JSON.stringify(selectedLog.old_value, null, 2)}
                    </pre>
                  </div>
                )}
                {selectedLog.new_value && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 mb-1">After</p>
                    <pre className="bg-emerald-50 border border-emerald-100 rounded p-3 text-xs overflow-auto max-h-40">
                      {JSON.stringify(selectedLog.new_value, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorAuditLogs;
