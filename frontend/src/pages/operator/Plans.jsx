import { useState, useEffect, useRef } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
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
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Package, Upload, Download, FileSpreadsheet, CheckCircle, XCircle, AlertCircle, Search } from "lucide-react";
import { Checkbox } from "../../components/ui/checkbox";

const VALIDITY_OPTIONS = [
  { value: "monthly",    label: "Monthly" },
  { value: "quarterly",  label: "Quarterly" },
  { value: "half_yearly",label: "Half-Yearly" },
  { value: "yearly",     label: "Yearly" },
];
const VALIDITY_MONTHS = { monthly: 1, quarterly: 3, half_yearly: 6, yearly: 12 };

/** Scale base plan price to a target tenure */
const priceForTenure = (basePrice, baseValidity, targetValidity) => {
  const bm = VALIDITY_MONTHS[baseValidity] || 1;
  const tm = VALIDITY_MONTHS[targetValidity] || bm;
  return Math.round((basePrice / bm * tm) * 100) / 100;
};

const OperatorPlans = () => {
  const { authAxios, user } = useAuth();
  const isStaff = user?.role === "staff";
  const [plans, setPlans] = useState([]);
  const [filteredPlans, setFilteredPlans] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const fileInputRef = useRef(null);
  const [formData, setFormData] = useState({
    name: "",
    price: 0,
    validity: "monthly",
    available_validities: ["monthly"],
    tax_percentage: 0,
    tax_type: "none",
    description: ""
  });

  useEffect(() => {
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

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/operator/plans");
      setPlans(response.data);
      setFilteredPlans(response.data);
    } catch (error) {
      toast.error("Failed to load plans");
    } finally {
      setLoading(false);
    }
  };

  // Filter plans based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredPlans(plans);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = plans.filter(plan => 
        plan.name.toLowerCase().includes(query) ||
        plan.description?.toLowerCase().includes(query) ||
        plan.price.toString().includes(query)
      );
      setFilteredPlans(filtered);
    }
  }, [searchQuery, plans]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Validation
    if (!formData.name.trim() || formData.name.trim().length < 2) {
      toast.error("Plan name must be at least 2 characters"); return;
    }
    if (formData.price < 0) { toast.error("Price cannot be negative"); return; }
    if (formData.tax_percentage < 0 || formData.tax_percentage > 100) {
      toast.error("Tax percentage must be between 0 and 100"); return;
    }
    if (!formData.validity) { toast.error("Please select a base validity period"); return; }
    if (!formData.available_validities?.length) { toast.error("Please enable at least one tenure"); return; }
    try {
      if (editingPlan) {
        await authAxios.put(`/operator/plans/${editingPlan.id}`, formData);
        toast.success("Plan updated successfully");
      } else {
        await authAxios.post("/operator/plans", formData);
        toast.success("Plan created successfully");
      }
      setShowDialog(false);
      resetForm();
      fetchPlans();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save plan");
    }
  };

  const handleDelete = async (planId) => {
    if (!confirm("Are you sure you want to delete this plan?")) return;
    try {
      await authAxios.delete(`/operator/plans/${planId}`);
      toast.success("Plan deleted");
      fetchPlans();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete plan");
    }
  };

  const openEditDialog = (plan) => {
    setEditingPlan(plan);
    setFormData({
      name: plan.name,
      price: plan.price,
      validity: plan.validity,
      available_validities: plan.available_validities?.length ? plan.available_validities : [plan.validity],
      tax_percentage: plan.tax_percentage,
      tax_type: plan.tax_type,
      description: plan.description || ""
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingPlan(null);
    setFormData({
      name: "",
      price: 0,
      validity: "monthly",
      available_validities: ["monthly"],
      tax_percentage: 0,
      tax_type: "none",
      description: ""
    });
  };

  const toggleTenure = (val) => {
    setFormData(prev => {
      const cur = prev.available_validities || [];
      // base validity cannot be unchecked
      if (val === prev.validity) return prev;
      const next = cur.includes(val) ? cur.filter(v => v !== val) : [...cur, val];
      // ensure base is always present
      if (!next.includes(prev.validity)) next.unshift(prev.validity);
      return { ...prev, available_validities: next };
    });
  };

  const getValidityLabel = (validity) => {
    const opt = VALIDITY_OPTIONS.find(o => o.value === validity);
    return opt ? opt.label : validity;
  };

  // ── Bulk Upload ───────────────────────────────────────────────────────────
  const handleDownloadSample = async () => {
    try {
      const res = await authAxios.get("/operator/plans/sample-csv", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = "plans_sample.csv";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch { toast.error("Failed to download sample"); }
  };

  const pollJobStatusInBackground = async (jobId) => {
    const maxAttempts = 300; // 15 minutes max with 3-second intervals
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const res = await authAxios.get(`/operator/jobs/${jobId}`);
        const { status, result, error } = res.data;

        if (status === "completed") {
          fetchPlans();
          return;
        } else if (status === "failed") {
          return;
        }
        // Still pending or processing, wait and retry
        await new Promise(resolve => setTimeout(resolve, 3000));
      } catch (e) {
        return;
      }
    }
  };

  const handleBulkUpload = async () => {
    if (!bulkFile) return;
    setBulkUploading(true);
    setBulkResult(null);
    try {
      const form = new FormData();
      form.append("file", bulkFile);
      const res = await authAxios.post("/operator/plans/bulk-upload", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      const { job_id } = res.data;
      toast.success("File uploaded successfully. Processing in background...");
      // Close dialog immediately
      setShowBulkDialog(false);
      setBulkUploading(false);
      // Start background polling without awaiting
      pollJobStatusInBackground(job_id);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Upload failed");
      setBulkUploading(false);
    }
  };

  if (loading) {
    return (
      <OperatorLayout title="Plans">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const isReadOnly = dashboardStats?.is_read_only;

  return (
    <OperatorLayout title="Plans" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <p className="text-slate-500">Define service plans for your subscribers</p>
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Search plans..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
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
              data-testid="create-plan-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Plan
            </Button>
          </div>
        </div>

        {/* Plans Grid */}
        {filteredPlans.length === 0 ? (
          <Card className="p-8 text-center">
            <Package className="w-12 h-12 mx-auto mb-4 text-slate-300" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">
              {searchQuery ? "No plans found" : "No plans yet"}
            </h3>
            <p className="text-slate-500 mb-4">
              {searchQuery 
                ? "Try adjusting your search criteria" 
                : "Create your first service plan to start adding subscribers"}
            </p>
            {!searchQuery && (
              <div className="flex justify-center gap-3">
                <Button variant="outline" onClick={() => setShowBulkDialog(true)} disabled={isReadOnly}>
                  <Upload className="w-4 h-4 mr-2" /> Bulk Upload
                </Button>
                <Button onClick={() => setShowDialog(true)} disabled={isReadOnly}>
                  <Plus className="w-4 h-4 mr-2" /> Create Your First Plan
                </Button>
              </div>
            )}
          </Card>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Plan Name</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Base Validity</TableHead>
                    <TableHead>Available Tenures</TableHead>
                    <TableHead>Tax</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[100px] text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPlans.map((plan) => {
                    const tenures = plan.available_validities?.length ? plan.available_validities : [plan.validity];
                    return (
                    <TableRow key={plan.id} data-testid={`plan-row-${plan.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-2 font-medium">
                          <Package className="w-4 h-4 text-blue-600" />
                          {plan.name}
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">
                        ₹{plan.price.toLocaleString('en-IN')}
                        <span className="text-xs text-slate-400 ml-1">/ {getValidityLabel(plan.validity)}</span>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                          {getValidityLabel(plan.validity)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {VALIDITY_OPTIONS.map(opt => (
                            tenures.includes(opt.value) ? (
                              <span key={opt.value} className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded font-medium">
                                {opt.label}
                              </span>
                            ) : (
                              <span key={opt.value} className="text-xs bg-slate-50 text-slate-300 border border-slate-100 px-1.5 py-0.5 rounded">
                                {opt.label}
                              </span>
                            )
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        {plan.tax_type === "none" ? "No Tax" : `${plan.tax_percentage}% (${plan.tax_type})`}
                      </TableCell>
                      <TableCell>
                        <span className="badge-active">{plan.status}</span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button 
                            variant="ghost" size="icon"
                            className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                            onClick={() => openEditDialog(plan)}
                            disabled={isReadOnly} title="Edit plan"
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          {!isStaff && (
                            <Button
                              variant="ghost" size="icon"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleDelete(plan.id)}
                              disabled={isReadOnly}
                              data-testid={`delete-plan-${plan.id}`}
                              title="Delete plan"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );})}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingPlan ? "Edit Plan" : "Create New Plan"}</DialogTitle>
              <DialogDescription>
                {editingPlan ? "Update plan details" : "Create a service plan for your subscribers"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Plan Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Monthly Premium"
                  required
                  data-testid="plan-name-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Price (₹) *</Label>
                  <Input
                    type="number"
                    value={formData.price}
                    onChange={(e) => setFormData(prev => ({ ...prev, price: parseFloat(e.target.value) || 0 }))}
                    min="0" required
                    data-testid="plan-price-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Base Validity (price reference) *</Label>
                  <Select
                    value={formData.validity}
                    onValueChange={(v) => setFormData(p => ({
                      ...p,
                      validity: v,
                      // keep base validity in available_validities
                      available_validities: Array.from(new Set([v, ...(p.available_validities || [])]))
                    }))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {VALIDITY_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <p className="text-[11px] text-slate-400">The price above is for this period.</p>
                </div>
              </div>

              {/* Available Tenures */}
              <div className="space-y-2">
                <Label>Available Tenures</Label>
                <p className="text-xs text-slate-500">Choose which tenures operators can assign to subscribers.</p>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  {VALIDITY_OPTIONS.map(opt => {
                    const isBase = opt.value === formData.validity;
                    const checked = (formData.available_validities || []).includes(opt.value);
                    const calcPrice = priceForTenure(formData.price || 0, formData.validity, opt.value);
                    return (
                      <label
                        key={opt.value}
                        className={`flex items-center gap-2 border rounded-lg px-3 py-2 cursor-pointer transition-colors ${
                          checked ? "bg-blue-50 border-blue-300" : "bg-slate-50 border-slate-200 opacity-60"
                        } ${isBase ? "ring-1 ring-blue-400" : ""}`}
                      >
                        <Checkbox
                          checked={checked}
                          disabled={isBase}
                          onCheckedChange={() => toggleTenure(opt.value)}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-800 flex items-center gap-1">
                            {opt.label}
                            {isBase && <span className="text-[10px] bg-blue-200 text-blue-700 px-1 rounded">base</span>}
                          </p>
                          <p className="text-xs text-slate-500">
                            {formData.price > 0 ? `₹${calcPrice.toLocaleString('en-IN')}` : "—"}
                          </p>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Tax %</Label>
                  <Input type="number" value={formData.tax_percentage}
                    onChange={(e) => setFormData(p => ({ ...p, tax_percentage: parseFloat(e.target.value) || 0 }))}
                    min="0" max="100" />
                </div>
                <div className="space-y-2">
                  <Label>Tax Type</Label>
                  <Select value={formData.tax_type} onValueChange={(v) => setFormData(p => ({ ...p, tax_type: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      <SelectItem value="inclusive">Inclusive</SelectItem>
                      <SelectItem value="exclusive">Exclusive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData(p => ({ ...p, description: e.target.value }))}
                  placeholder="Plan description (optional)" rows={3}
                />
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>Cancel</Button>
                <Button type="submit" data-testid="save-plan-btn">{editingPlan ? "Update Plan" : "Create Plan"}</Button>
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
                Bulk Upload Plans
              </DialogTitle>
              <DialogDescription>Upload a CSV or XLSX file to create multiple plans at once.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {/* Sample Download */}
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-800">Download Sample File</p>
                  <p className="text-xs text-blue-600 mt-0.5">Required columns: name, price, validity, tax_percentage, tax_type, description</p>
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
                    <span className="flex items-center gap-1 text-emerald-700">
                      <CheckCircle className="w-4 h-4" /> {bulkResult.created} created
                    </span>
                    <span className="flex items-center gap-1 text-amber-600">
                      <AlertCircle className="w-4 h-4" /> {bulkResult.skipped} skipped
                    </span>
                    <span className="flex items-center gap-1 text-red-600">
                      <XCircle className="w-4 h-4" /> {bulkResult.errors?.length || 0} errors
                    </span>
                  </div>
                  {bulkResult.errors?.length > 0 && (
                    <div className="text-xs text-red-600 space-y-0.5 max-h-24 overflow-y-auto">
                      {bulkResult.errors.map((e, i) => (
                        <div key={`plan-err-${e.row}-${i}`}>Row {e.row}: {e.reason}</div>
                      ))}
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
  );
};

export default OperatorPlans;
