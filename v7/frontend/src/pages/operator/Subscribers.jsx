import { useState, useEffect, useRef } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { toast } from "sonner";
import { Plus, Search, MoreVertical, Pencil, Trash2, Users, Phone, MessageCircle, Upload, Download, FileSpreadsheet, CheckCircle, XCircle, AlertCircle, Ban } from "lucide-react";

const OperatorSubscribers = () => {
  const { authAxios, user } = useAuth();
  const isStaff = user?.role === "staff";
  const isAdminImpersonating = !!user?.impersonated_by; // admin logged in as operator
  const [subscribers, setSubscribers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showDialog, setShowDialog] = useState(false);
  const [editingSubscriber, setEditingSubscriber] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [limitError, setLimitError] = useState(null); // for plan limit exceeded errors
  const fileInputRef = useRef(null);
  const [formData, setFormData] = useState({
    name: "",
    whatsapp_number: "",
    email: "",
    address: "",
    plan_id: "",
    billing_date: 1,
    discount: 0
  });

  useEffect(() => {
    fetchSubscribers();
    fetchPlans();
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await authAxios.get("/operator/dashboard");
      setDashboardStats(response.data);
    } catch (error) {
      console.error("Failed to load dashboard");
    }
  };

  const fetchSubscribers = async () => {
    try {
      const response = await authAxios.get("/operator/subscribers");
      setSubscribers(response.data);
    } catch (error) {
      toast.error("Failed to load subscribers");
    } finally {
      setLoading(false);
    }
  };

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/operator/plans");
      setPlans(response.data);
    } catch (error) {
      console.error("Failed to load plans");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingSubscriber) {
        await authAxios.put(`/operator/subscribers/${editingSubscriber.id}`, formData);
        toast.success("Subscriber updated successfully");
      } else {
        await authAxios.post("/operator/subscribers", formData);
        toast.success("Subscriber created successfully");
      }
      setShowDialog(false);
      resetForm();
      fetchSubscribers();
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to save subscriber";
      if (!editingSubscriber && (detail.toLowerCase().includes("upgrade") || detail.toLowerCase().includes("limit"))) {
        setShowDialog(false);
        setLimitError(detail);
      } else {
        toast.error(detail);
      }
    }
  };

  const handleDelete = async (subscriberId) => {
    if (!confirm("Are you sure you want to delete this subscriber? This action cannot be undone.")) return;
    try {
      await authAxios.delete(`/operator/subscribers/${subscriberId}`);
      toast.success("Subscriber deleted");
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete subscriber");
    }
  };

  const handleSuspend = async (subscriberId) => {
    try {
      await authAxios.post(`/operator/subscribers/${subscriberId}/suspend`);
      toast.success("Subscriber suspended");
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to suspend subscriber");
    }
  };

  const handleActivate = async (subscriberId) => {
    try {
      await authAxios.post(`/operator/subscribers/${subscriberId}/activate`);
      toast.success("Subscriber activated");
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to activate subscriber");
    }
  };

  const openEditDialog = (subscriber) => {
    setEditingSubscriber(subscriber);
    setFormData({
      name: subscriber.name,
      whatsapp_number: subscriber.whatsapp_number,
      email: subscriber.email || "",
      address: subscriber.address || "",
      plan_id: subscriber.plan_id,
      billing_date: subscriber.billing_date,
      discount: subscriber.discount
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingSubscriber(null);
    setFormData({
      name: "",
      whatsapp_number: "",
      email: "",
      address: "",
      plan_id: "",
      billing_date: 1,
      discount: 0
    });
  };

  const filteredSubscribers = subscribers.filter(sub =>
    sub.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sub.whatsapp_number.includes(searchTerm)
  );

  // ── Bulk Upload ───────────────────────────────────────────────────────────
  const handleDownloadSample = async () => {
    try {
      const res = await authAxios.get("/operator/subscribers/sample-csv", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = "subscribers_sample.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error("Failed to download sample"); }
  };

  const handleBulkUpload = async () => {
    if (!bulkFile) return;
    setBulkUploading(true);
    setBulkResult(null);
    setLimitError(null);
    try {
      const form = new FormData();
      form.append("file", bulkFile);
      const res = await authAxios.post("/operator/subscribers/bulk-upload", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setBulkResult(res.data);
      fetchSubscribers();
      fetchDashboard();
      if (res.data.created > 0) toast.success(`${res.data.created} subscriber(s) created`);
    } catch (e) {
      const detail = e.response?.data?.detail || "Upload failed";
      // If it's a plan limit error, show prominent dialog; otherwise show toast
      if (detail.toLowerCase().includes("upgrade") || detail.toLowerCase().includes("limit")) {
        setShowBulkDialog(false);
        setLimitError(detail);
      } else {
        toast.error(detail);
      }
    } finally {
      setBulkUploading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      active: "badge-active",
      inactive: "badge-suspended"
    };
    return <span className={badges[status] || "badge-pending"}>{status}</span>;
  };

  if (loading) {
    return (
      <OperatorLayout title="Subscribers">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const isReadOnly = dashboardStats?.is_read_only;

  return (
    <>
    <OperatorLayout title="Subscribers" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search subscribers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
              data-testid="search-subscribers"
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => { setShowBulkDialog(true); setBulkFile(null); setBulkResult(null); }}
              disabled={isReadOnly || isStaff}
            >
              <Upload className="w-4 h-4 mr-2" />
              Bulk Upload
            </Button>
            <Button 
              onClick={() => { resetForm(); setShowDialog(true); }}
              disabled={isReadOnly}
              data-testid="add-subscriber-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Subscriber
            </Button>
          </div>
        </div>

        {/* Subscriber usage bar */}
        {dashboardStats?.max_subscribers != null && (
          <div className="flex items-center gap-3 px-1">
            <span className="text-sm text-slate-500 whitespace-nowrap">
              Subscribers:
              <span className={`ml-1 font-semibold ${
                dashboardStats.total_subscribers >= dashboardStats.max_subscribers
                  ? "text-red-600"
                  : dashboardStats.total_subscribers >= dashboardStats.max_subscribers * 0.8
                  ? "text-amber-600"
                  : "text-slate-700"
              }`}>
                {dashboardStats.total_subscribers} / {dashboardStats.max_subscribers}
              </span>
            </span>
            <div className="flex-1 max-w-[200px] h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  dashboardStats.total_subscribers >= dashboardStats.max_subscribers
                    ? "bg-red-500"
                    : dashboardStats.total_subscribers >= dashboardStats.max_subscribers * 0.8
                    ? "bg-amber-400"
                    : "bg-emerald-500"
                }`}
                style={{ width: `${Math.min(100, (dashboardStats.total_subscribers / dashboardStats.max_subscribers) * 100)}%` }}
              />
            </div>
            {dashboardStats.total_subscribers >= dashboardStats.max_subscribers && (
              <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                Limit reached
              </span>
            )}
          </div>
        )}

        {/* Subscribers Table */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>WhatsApp</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Billing Date</TableHead>
                  <TableHead>Discount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSubscribers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                      <Users className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No subscribers found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredSubscribers.map((subscriber) => (
                    <TableRow key={subscriber.id} data-testid={`subscriber-row-${subscriber.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <span className="text-blue-600 font-medium text-sm">
                              {subscriber.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <span className="font-medium block">{subscriber.name}</span>
                            {subscriber.email && (
                              <span className="text-xs text-slate-500">{subscriber.email}</span>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Phone className="w-3 h-3 text-emerald-600" />
                          <span className="font-mono text-sm">{subscriber.whatsapp_number}</span>
                        </div>
                      </TableCell>
                      <TableCell>{subscriber.plan_name || "-"}</TableCell>
                      <TableCell>Day {subscriber.billing_date}</TableCell>
                      <TableCell>₹{subscriber.discount}</TableCell>
                      <TableCell>{getStatusBadge(subscriber.status)}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" disabled={isReadOnly}>
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => openEditDialog(subscriber)}>
                              <Pencil className="w-4 h-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => {
                                let phone = (subscriber.whatsapp_number || "").replace(/[^0-9]/g, '');
                                if (phone.length === 10) phone = "91" + phone;
                                if (!phone) { return; }
                                window.open(`https://wa.me/${phone}`, '_blank');
                              }}
                              data-testid={`wa-subscriber-${subscriber.id}`}
                            >
                              <MessageCircle className="w-4 h-4 mr-2 text-emerald-600" />
                              WhatsApp
                            </DropdownMenuItem>
                            {!isStaff && (
                              subscriber.status === "active" ? (
                                <DropdownMenuItem
                                  onClick={() => handleSuspend(subscriber.id)}
                                  className="text-amber-600"
                                  data-testid={`suspend-subscriber-${subscriber.id}`}
                                >
                                  <Ban className="w-4 h-4 mr-2" />
                                  Suspend
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem
                                  onClick={() => handleActivate(subscriber.id)}
                                  className="text-emerald-600"
                                  data-testid={`activate-subscriber-${subscriber.id}`}
                                >
                                  <CheckCircle className="w-4 h-4 mr-2" />
                                  Activate
                                </DropdownMenuItem>
                              )
                            )}
                            {isAdminImpersonating && (
                              <DropdownMenuItem
                                onClick={() => handleDelete(subscriber.id)}
                                className="text-red-600"
                                data-testid={`delete-subscriber-${subscriber.id}`}
                              >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Create/Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingSubscriber ? "Edit Subscriber" : "Add New Subscriber"}</DialogTitle>
              <DialogDescription>
                {editingSubscriber ? "Update subscriber details" : "Add a new subscriber to your list"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 space-y-2">
                  <Label>Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Subscriber name"
                    required
                    data-testid="subscriber-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>WhatsApp Number *</Label>
                  <Input
                    value={formData.whatsapp_number}
                    onChange={(e) => setFormData(prev => ({ ...prev, whatsapp_number: e.target.value }))}
                    placeholder="9876543210"
                    required
                    data-testid="subscriber-phone-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="email@example.com"
                  />
                </div>

                <div className="col-span-2 space-y-2">
                  <Label>Address</Label>
                  <Input
                    value={formData.address}
                    onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                    placeholder="Full address"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Plan *</Label>
                  <Select 
                    value={formData.plan_id} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, plan_id: value }))}
                  >
                    <SelectTrigger data-testid="subscriber-plan-select">
                      <SelectValue placeholder="Select plan" />
                    </SelectTrigger>
                    <SelectContent>
                      {plans.map((plan) => (
                        <SelectItem key={plan.id} value={plan.id}>
                          {plan.name} - ₹{plan.price}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Billing Date (Day of Month) *</Label>
                  <Select 
                    value={formData.billing_date.toString()} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, billing_date: parseInt(value) }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select day" />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 28 }, (_, i) => i + 1).map((day) => (
                        <SelectItem key={day} value={day.toString()}>
                          Day {day}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Discount (₹)</Label>
                  <Input
                    type="number"
                    value={formData.discount}
                    onChange={(e) => setFormData(prev => ({ ...prev, discount: parseFloat(e.target.value) || 0 }))}
                    min="0"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-subscriber-btn">
                  {editingSubscriber ? "Update" : "Add Subscriber"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Bulk Upload Dialog */}
        <Dialog open={showBulkDialog} onOpenChange={(o) => { setShowBulkDialog(o); if (!o) { setBulkFile(null); setBulkResult(null); } }}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                Bulk Upload Subscribers
              </DialogTitle>
              <DialogDescription>Upload a CSV or XLSX file to add multiple subscribers at once.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {/* Sample Download */}
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-800">Download Sample File</p>
                  <p className="text-xs text-blue-600 mt-0.5">Columns: name, whatsapp_number, email, address, plan_name, billing_date, discount</p>
                </div>
                <Button variant="outline" size="sm" className="shrink-0 border-blue-200 text-blue-700" onClick={handleDownloadSample}>
                  <Download className="w-3.5 h-3.5 mr-1" /> Sample CSV
                </Button>
              </div>

              {/* File Picker */}
              <div
                className="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center cursor-pointer hover:border-slate-400 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  onChange={(e) => { setBulkFile(e.target.files[0]); setBulkResult(null); }}
                />
                <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                {bulkFile ? (
                  <p className="text-sm font-medium text-slate-700">{bulkFile.name}</p>
                ) : (
                  <p className="text-sm text-slate-500">Click to select CSV or XLSX file</p>
                )}
              </div>

              {/* Result */}
              {bulkResult && (
                <div className="bg-slate-50 rounded-lg p-3 space-y-2">
                  <div className="flex gap-4 text-sm">
                    <span className="flex items-center gap-1 text-emerald-700"><CheckCircle className="w-4 h-4" /> {bulkResult.created} created</span>
                    <span className="flex items-center gap-1 text-amber-600"><AlertCircle className="w-4 h-4" /> {bulkResult.skipped} skipped</span>
                    <span className="flex items-center gap-1 text-red-600"><XCircle className="w-4 h-4" /> {bulkResult.errors?.length || 0} errors</span>
                  </div>
                  {bulkResult.errors?.length > 0 && (
                    <div className="text-xs text-red-600 space-y-0.5 max-h-24 overflow-y-auto">
                      {bulkResult.errors.map((e, i) => <div key={i}>Row {e.row}{e.name ? ` (${e.name})` : ""}: {e.reason}</div>)}
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setShowBulkDialog(false)}>Close</Button>
                <Button className="flex-1" onClick={handleBulkUpload} disabled={!bulkFile || bulkUploading}>
                  {bulkUploading ? "Uploading..." : "Upload File"}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>

    {/* Plan Limit Exceeded Dialog */}
    <Dialog open={!!limitError} onOpenChange={() => setLimitError(null)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertCircle className="w-5 h-5" />
            Subscriber Limit Reached
          </DialogTitle>
        </DialogHeader>
        <div className="py-3 space-y-4">
          <p className="text-slate-700 text-sm leading-relaxed">{limitError}</p>
          {dashboardStats?.max_subscribers != null && (
            <div className="p-3 bg-slate-50 rounded-lg space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Current subscribers</span>
                <span className="font-semibold">{dashboardStats.total_subscribers}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Plan limit</span>
                <span className="font-semibold">{dashboardStats.max_subscribers}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Available slots</span>
                <span className="font-semibold text-amber-600">{Math.max(0, dashboardStats.max_subscribers - dashboardStats.total_subscribers)}</span>
              </div>
            </div>
          )}
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => setLimitError(null)}>Close</Button>
          <Button
            onClick={() => { setLimitError(null); window.location.href = "/operator/subscription"; }}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Upgrade Plan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
};

export default OperatorSubscribers;
