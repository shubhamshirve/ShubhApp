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
import { sanitize } from "../../utils/sanitize";

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
  const [subFieldErrors, setSubFieldErrors] = useState({});
  const fileInputRef = useRef(null);
  const [formData, setFormData] = useState({
    name: "",
    whatsapp_number: "",
    email: "",
    address: "",
    plans: [{
      plan_id: "",
      billing_date: 1,
      discount: 0
    }]
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

  const validateSubField = (name, value) => {
    const v = typeof value === "string" ? value.trim() : value;
    if (name === "name") {
      if (!v || v.length < 2) return "Name must be at least 2 characters";
    } else if (name === "whatsapp_number") {
      const digits = (value || "").replace(/\D/g, "");
      if (!digits || digits.length < 10 || digits.length > 13) return "Enter a valid 10-digit WhatsApp number";
    } else if (name === "email") {
      if (v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return "Enter a valid email address";
    }
    return "";
  };

  const handleSubBlur = (e) => {
    const { name, value } = e.target;
    setSubFieldErrors((prev) => ({ ...prev, [name]: validateSubField(name, value) }));
  };

  const handleSubChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (subFieldErrors[field]) setSubFieldErrors((prev) => ({ ...prev, [field]: "" }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Validate all sub-fields
    const nameErr = validateSubField("name", formData.name);
    const phoneErr = validateSubField("whatsapp_number", formData.whatsapp_number);
    const emailErr = validateSubField("email", formData.email);
    if (nameErr || phoneErr || emailErr) {
      setSubFieldErrors({ name: nameErr, whatsapp_number: phoneErr, email: emailErr });
      toast.error("Please fix the errors before submitting");
      return;
    }

    const phoneDigits = formData.whatsapp_number.replace(/\D/g, "");
    
    if (formData.plans.length === 0) {
      toast.error("Please add at least one plan");
      return;
    }

    for (const p of formData.plans) {
      if (!p.plan_id) { toast.error("Please select a plan for all entries"); return; }
      if (p.discount < 0) { toast.error("Discount cannot be negative"); return; }
    }

    const payload = {
      ...formData,
      name: sanitize(formData.name),
      email: sanitize(formData.email),
      address: sanitize(formData.address),
      whatsapp_number: phoneDigits,
    };
    try {
      if (editingSubscriber) {
        await authAxios.put(`/operator/subscribers/${editingSubscriber.id}`, payload);
        toast.success("Subscriber updated successfully");
      } else {
        await authAxios.post("/operator/subscribers", payload);
        toast.success("Subscriber created successfully");
      }
      setShowDialog(false);
      resetForm();
      fetchSubscribers();
    } catch (error) {
      const detailRaw = error.response?.data?.detail;
      const detail = typeof detailRaw === "string" ? detailRaw
        : Array.isArray(detailRaw) ? detailRaw.map(e => e.msg || String(e)).join("; ")
        : "Failed to save subscriber";
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
      plans: subscriber.plans.map(p => ({
        plan_id: p.plan_id,
        billing_date: p.billing_date,
        discount: p.discount
      }))
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingSubscriber(null);
    setSubFieldErrors({});
    setFormData({
      name: "",
      whatsapp_number: "",
      email: "",
      address: "",
      plans: [{
        plan_id: "",
        billing_date: 1,
        discount: 0
      }]
    });
  };

  const addPlanRow = () => {
    setFormData(prev => ({
      ...prev,
      plans: [...prev.plans, { plan_id: "", billing_date: 1, discount: 0 }]
    }));
  };

  const removePlanRow = (index) => {
    setFormData(prev => ({
      ...prev,
      plans: prev.plans.filter((_, i) => i !== index)
    }));
  };

  const updatePlanRow = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      plans: prev.plans.map((p, i) => i === index ? { ...p, [field]: value } : p)
    }));
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

  const pollJobStatus = async (jobId) => {
    const maxAttempts = 300;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const res = await authAxios.get(`/operator/jobs/${jobId}`);
        const { status, result, error } = res.data;

        if (status === "completed") {
          setBulkResult(result);
          fetchSubscribers();
          fetchDashboard();
          if (result.created > 0) toast.success(`${result.created} subscriber(s) created`);
          return;
        } else if (status === "failed") {
          const detail = error || "Job failed";
          if (detail.toLowerCase().includes("upgrade") || detail.toLowerCase().includes("limit")) {
            setShowBulkDialog(false);
            setLimitError(detail);
          } else {
            toast.error(`Job failed: ${detail}`);
          }
          return;
        }
        await new Promise(resolve => setTimeout(resolve, 3000));
      } catch (e) {
        toast.error("Failed to check job status");
        return;
      }
    }
    toast.error("Job polling timed out");
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
      const { job_id } = res.data;
      toast.success("Job queued. Processing...");
      await pollJobStatus(job_id);
    } catch (e) {
      const detail = e.response?.data?.detail || "Upload failed";
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
                  <TableHead>Active Plans</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSubscribers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-slate-500">
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
                      <TableCell>
                        <div className="space-y-1">
                          {subscriber.plans?.map((p, idx) => (
                            <div key={idx} className="text-xs border-b border-slate-50 last:border-0 pb-1 last:pb-0">
                              <span className="font-medium text-slate-700">{p.plan_name}</span>
                              <div className="flex gap-2 text-slate-500 mt-0.5">
                                <span>Day {p.billing_date}</span>
                                {p.discount > 0 && <span>-₹{p.discount}</span>}
                              </div>
                            </div>
                          ))}
                          {(!subscriber.plans || subscriber.plans.length === 0) && (
                            <span className="text-slate-400">-</span>
                          )}
                        </div>
                      </TableCell>
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
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingSubscriber ? "Edit Subscriber" : "Add New Subscriber"}</DialogTitle>
              <DialogDescription>
                {editingSubscriber ? "Update subscriber details" : "Add a new subscriber to your list"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-slate-900 border-b pb-2">Basic Information</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2 space-y-2">
                    <Label>Name *</Label>
                    <Input
                      name="name"
                      value={formData.name}
                      onChange={(e) => handleSubChange("name", e.target.value)}
                      onBlur={handleSubBlur}
                      className={subFieldErrors.name ? "border-red-500" : ""}
                      placeholder="Subscriber name"
                      required
                      data-testid="subscriber-name-input"
                    />
                    {subFieldErrors.name && <p className="text-xs text-red-500 mt-1">{subFieldErrors.name}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label>WhatsApp Number *</Label>
                    <Input
                      name="whatsapp_number"
                      value={formData.whatsapp_number}
                      onChange={(e) => handleSubChange("whatsapp_number", e.target.value)}
                      onBlur={handleSubBlur}
                      className={subFieldErrors.whatsapp_number ? "border-red-500" : ""}
                      placeholder="9876543210"
                      required
                      data-testid="subscriber-phone-input"
                    />
                    {subFieldErrors.whatsapp_number && <p className="text-xs text-red-500 mt-1">{subFieldErrors.whatsapp_number}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleSubChange("email", e.target.value)}
                      onBlur={handleSubBlur}
                      className={subFieldErrors.email ? "border-red-500" : ""}
                      placeholder="email@example.com"
                    />
                    {subFieldErrors.email && <p className="text-xs text-red-500 mt-1">{subFieldErrors.email}</p>}
                  </div>

                  <div className="col-span-2 space-y-2">
                    <Label>Address</Label>
                    <Input
                      value={formData.address}
                      onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                      placeholder="Full address"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between border-b pb-2">
                  <h4 className="text-sm font-semibold text-slate-900">Active Plans</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addPlanRow}>
                    <Plus className="w-3 h-3 mr-1" /> Add Plan
                  </Button>
                </div>
                
                <div className="space-y-4">
                  {formData.plans.map((plan, index) => (
                    <div key={index} className="p-4 bg-slate-50 rounded-lg relative border border-slate-100">
                      {formData.plans.length > 1 && (
                        <Button 
                          type="button" 
                          variant="ghost" 
                          size="icon" 
                          className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-white border shadow-sm text-red-500"
                          onClick={() => removePlanRow(index)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                      
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label>Plan *</Label>
                          <Select 
                            value={plan.plan_id} 
                            onValueChange={(value) => updatePlanRow(index, "plan_id", value)}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select plan" />
                            </SelectTrigger>
                            <SelectContent>
                              {plans.map((p) => (
                                <SelectItem key={p.id} value={p.id}>
                                  {p.name} - ₹{p.price}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label>Billing Date *</Label>
                          <Select 
                            value={plan.billing_date.toString()} 
                            onValueChange={(value) => updatePlanRow(index, "billing_date", parseInt(value))}
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
                            value={plan.discount}
                            onChange={(e) => updatePlanRow(index, "discount", parseFloat(e.target.value) || 0)}
                            min="0"
                            placeholder="0"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-subscriber-btn">
                  {editingSubscriber ? "Update Subscriber" : "Create Subscriber"}
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
