import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
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
  Database, Plus, RefreshCw, Trash2, RotateCcw,
  CheckCircle, Clock, Shield, HardDrive, AlertTriangle, Download,
} from "lucide-react";

const DEFAULT_PLATFORM_SETTINGS = {
  cron_backup_time: "03:00",
};

const PAGE_SIZE = 10;

const AdminBackup = () => {
  const { authAxios } = useAuth();
  const [backups, setBackups] = useState([]);
  const [totalBackups, setTotalBackups] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [platformSettings, setPlatformSettings] = useState(DEFAULT_PLATFORM_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [password, setPassword] = useState("");
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    Promise.all([fetchBackups(1), fetchSettings()]).finally(() => setLoading(false));
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await authAxios.get("/admin/settings");
      setPlatformSettings({
        ...DEFAULT_PLATFORM_SETTINGS,
        ...res.data,
      });
    } catch {
      // keep defaults if settings cannot be loaded
    }
  };

  const fetchBackups = async (page = currentPage) => {
    try {
      const res = await authAxios.get("/admin/backup/list", { params: { page, per_page: PAGE_SIZE } });
      setBackups(res.data.backups || []);
      setTotalBackups(res.data.total || 0);
      setCurrentPage(res.data.page || page);
      setTotalPages(res.data.total_pages || 1);
    } catch {
      toast.error("Failed to load backups");
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      const res = await authAxios.post("/admin/backup/create");
      toast.success(`Backup created: ${res.data.backup.filename}`);
      fetchBackups(1);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Backup failed");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this backup permanently?")) return;
    try {
      await authAxios.delete(`/admin/backup/${id}`);
      toast.success("Backup deleted");
      fetchBackups(currentPage);
    } catch {
      toast.error("Failed to delete backup");
    }
  };

  const handleRestore = async () => {
    if (!restoreTarget || !password) return;
    setRestoring(true);
    try {
      const res = await authAxios.post(`/admin/backup/restore/${restoreTarget.id}`, { password });
      toast.success(`Restored successfully — ${res.data.records_restored} records across ${res.data.collections_restored.length} collections`);
      setRestoreTarget(null);
      setPassword("");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Restore failed");
    } finally {
      setRestoring(false);
    }
  };

  const formatSize = (kb) => {
    if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`;
    return `${kb} KB`;
  };

  const formatDate = (iso) => new Date(iso).toLocaleString();

  const handleDownload = async (backup) => {
    try {
      const res = await authAxios.get(`/admin/backup/download/${backup.id}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/gzip" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", backup.filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Download failed");
    }
  };

  if (loading) {
    return (
      <AdminLayout title="Backup & Restore">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Backup & Restore">
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <p className="text-slate-500">Manage database backups and restore points</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => fetchBackups(currentPage)}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={handleCreate} disabled={creating}>
              {creating ? (
                <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Creating...</>
              ) : (
                <><Plus className="w-4 h-4 mr-2" /> Create Backup</>
              )}
            </Button>
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="bg-blue-50 border-blue-100">
            <CardContent className="p-4 flex items-center gap-3">
              <Database className="w-8 h-8 text-blue-600" />
              <div>
                <p className="text-2xl font-bold text-blue-700">{totalBackups}</p>
                <p className="text-sm text-blue-600">Total Backups</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-emerald-50 border-emerald-100">
            <CardContent className="p-4 flex items-center gap-3">
              <Clock className="w-8 h-8 text-emerald-600" />
              <div>
                <p className="text-sm font-bold text-emerald-700">
                  {backups.filter(b => b.type === "auto").length} Auto
                </p>
                <p className="text-xs text-emerald-600">Daily at {platformSettings.cron_backup_time} IST</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-amber-50 border-amber-100">
            <CardContent className="p-4 flex items-center gap-3">
              <HardDrive className="w-8 h-8 text-amber-600" />
              <div>
                <p className="text-sm font-bold text-amber-700">
                  {formatSize(backups.reduce((s, b) => s + (b.size_kb || 0), 0))}
                </p>
                <p className="text-xs text-amber-600">Total Storage Used</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Backups Table */}
        <Card>
          <CardHeader className="pb-0">
            <CardTitle className="text-base">Available Backups</CardTitle>
          </CardHeader>
          <CardContent className="p-0 mt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Created At</TableHead>
                  <TableHead>Filename</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Records</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backups.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-10 text-slate-500">
                      <Database className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No backups yet. Click "Create Backup" to get started.
                    </TableCell>
                  </TableRow>
                ) : (
                  backups.map((b) => (
                    <TableRow key={b.id}>
                      <TableCell className="text-sm">{formatDate(b.created_at)}</TableCell>
                      <TableCell className="font-mono text-xs text-slate-600">{b.filename}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          b.type === "auto"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-slate-100 text-slate-700"
                        }`}>
                          {b.type === "auto" ? "Auto" : "Manual"}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">{formatSize(b.size_kb || 0)}</TableCell>
                      <TableCell className="text-sm">{(b.total_records || 0).toLocaleString()}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 border-blue-200"
                            onClick={() => handleDownload(b)}
                          >
                            <Download className="w-3.5 h-3.5 mr-1" />
                            Download
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-amber-600 hover:text-amber-700 hover:bg-amber-50 border-amber-200"
                            onClick={() => { setRestoreTarget(b); setPassword(""); }}
                          >
                            <RotateCcw className="w-3.5 h-3.5 mr-1" />
                            Restore
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => handleDelete(b.id)}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-slate-500">
              Showing {((currentPage - 1) * PAGE_SIZE) + 1}–{Math.min(currentPage * PAGE_SIZE, totalBackups)} of {totalBackups} backups
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => { const p = currentPage - 1; setCurrentPage(p); fetchBackups(p); }}
                disabled={currentPage <= 1}
              >
                Previous
              </Button>
              <span className="text-sm text-slate-600">Page {currentPage} of {totalPages}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => { const p = currentPage + 1; setCurrentPage(p); fetchBackups(p); }}
                disabled={currentPage >= totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Restore Password Dialog */}
      <Dialog open={!!restoreTarget} onOpenChange={() => { setRestoreTarget(null); setPassword(""); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-700">
              <AlertTriangle className="w-5 h-5" />
              Confirm Restore
            </DialogTitle>
            <DialogDescription>
              This will <strong>replace all current data</strong> with the backup from{" "}
              <span className="font-medium">{restoreTarget && formatDate(restoreTarget.created_at)}</span>.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700">
                All current operators, subscribers, invoices and settings will be replaced.
                Make sure to take a fresh backup before restoring.
              </p>
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Confirm Password
              </Label>
              <Input
                type="password"
                placeholder="Enter backup password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRestore()}
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => { setRestoreTarget(null); setPassword(""); }}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-amber-600 hover:bg-amber-700"
                onClick={handleRestore}
                disabled={restoring || !password}
              >
                {restoring ? (
                  <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Restoring...</>
                ) : (
                  <><RotateCcw className="w-4 h-4 mr-2" /> Restore Now</>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};

export default AdminBackup;
