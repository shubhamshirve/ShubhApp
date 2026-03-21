import { useState, useEffect } from "react";
import { AdminLayout } from "../../components/Layout";
import { useAuth } from "../../App";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../../components/ui/dialog";
import { toast } from "sonner";
import { Package, Plus, Pencil, Trash2, RefreshCw, IndianRupee, FileText } from "lucide-react";

export default function AdminSaaSPlans() {
  const { authAxios } = useAuth();
  const [plans, setPlans] = useState([]);
  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [saving, setSaving] = useState(false);

  const emptyForm = {
    name: "",
    monthly_price: "",
    per_invoice_price: "10",
    included_addons: [],
  };
  const [formData, setFormData] = useState(emptyForm);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [plansRes, addonsRes] = await Promise.all([
        authAxios.get("/admin/saas-plans"),
        authAxios.get("/admin/addons"),
      ]);
      setPlans(plansRes.data || []);
      setAddons(addonsRes.data || []);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const openCreate = () => {
    setEditingPlan(null);
    setFormData(emptyForm);
    setShowDialog(true);
  };

  const openEdit = (plan) => {
    setEditingPlan(plan);
    setFormData({
      name: plan.name,
      monthly_price: String(plan.monthly_price ?? ""),
      per_invoice_price: String(plan.per_invoice_price ?? "10"),
      included_addons: plan.included_addons || [],
    });
    setShowDialog(true);
  };

  const toggleAddon = (code) => {
    setFormData((prev) => ({
      ...prev,
      included_addons: prev.included_addons.includes(code)
        ? prev.included_addons.filter((c) => c !== code)
        : [...prev.included_addons, code],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const monthlyPrice = parseFloat(formData.monthly_price);
    const perInvoicePrice = parseFloat(formData.per_invoice_price);
    if (!formData.name.trim()) { toast.error("Plan name is required"); return; }
    if (isNaN(monthlyPrice) || monthlyPrice < 0) { toast.error("Monthly price must be a valid number"); return; }
    if (isNaN(perInvoicePrice) || perInvoicePrice < 0) { toast.error("Per invoice price must be a valid number"); return; }

    setSaving(true);
    const payload = {
      name: formData.name.trim(),
      monthly_price: monthlyPrice,
      per_invoice_price: perInvoicePrice,
      included_addons: formData.included_addons,
    };
    try {
      if (editingPlan) {
        await authAxios.put(`/admin/saas-plans/${editingPlan.id}`, payload);
        toast.success("Plan updated successfully");
      } else {
        await authAxios.post("/admin/saas-plans", payload);
        toast.success("Plan created successfully");
      }
      setShowDialog(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save plan");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (plan) => {
    if (!window.confirm(`Delete plan "${plan.name}"? This cannot be undone.`)) return;
    try {
      await authAxios.delete(`/admin/saas-plans/${plan.id}`);
      toast.success("Plan deleted");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete plan");
    }
  };

  return (
    <AdminLayout title="SaaS Plans">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">SaaS Plans</h2>
            <p className="text-sm text-slate-500">All prices are exclusive of GST — 18% GST will be added at checkout</p>
          </div>
          <Button onClick={openCreate} className="bg-[#0066B2] hover:bg-[#004080] text-white" data-testid="create-plan-btn">
            <Plus className="w-4 h-4 mr-2" /> New Plan
          </Button>
        </div>

        {/* Plans Grid */}
        {loading ? (
          <div className="flex justify-center py-16">
            <RefreshCw className="w-7 h-7 animate-spin text-blue-600" />
          </div>
        ) : plans.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="py-16 text-center">
              <Package className="w-10 h-10 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500 font-medium">No plans created yet</p>
              <p className="text-slate-400 text-sm mt-1">Click "New Plan" to get started</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {plans.map((plan) => (
              <Card key={plan.id} className="relative hover:shadow-md transition-shadow" data-testid={`plan-card-${plan.id}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <Package className="w-5 h-5 text-[#0066B2]" />
                      <CardTitle className="text-base">{plan.name}</CardTitle>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(plan)} data-testid={`edit-plan-${plan.id}`}>
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(plan)} className="text-red-500 hover:text-red-700" data-testid={`delete-plan-${plan.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Pricing */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-blue-50 rounded-lg p-3 text-center">
                      <div className="flex items-center justify-center gap-1 mb-0.5">
                        <IndianRupee className="w-3 h-3 text-blue-600" />
                        <span className="text-xl font-bold text-blue-700">{plan.monthly_price?.toLocaleString("en-IN")}</span>
                      </div>
                      <p className="text-xs text-blue-600">Monthly Price</p>
                      <p className="text-[10px] text-blue-400">Excl. GST</p>
                    </div>
                    <div className="bg-amber-50 rounded-lg p-3 text-center">
                      <div className="flex items-center justify-center gap-1 mb-0.5">
                        <FileText className="w-3 h-3 text-amber-600" />
                        <span className="text-xl font-bold text-amber-700">₹{plan.per_invoice_price ?? 10}</span>
                      </div>
                      <p className="text-xs text-amber-600">Per Invoice</p>
                      <p className="text-[10px] text-amber-400">Wallet deduction</p>
                    </div>
                  </div>

                  {/* Addons */}
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1.5">Included Addons</p>
                    {(plan.included_addons || []).length === 0 ? (
                      <p className="text-xs text-slate-400 italic">None</p>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {(plan.included_addons || []).map((code) => (
                          <Badge key={code} variant="secondary" className="text-[10px]">{code.replace(/_/g, " ")}</Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Create / Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingPlan ? "Edit Plan" : "Create New Plan"}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-5 pt-2">
              {/* Plan Name */}
              <div className="space-y-1.5">
                <Label>Plan Name <span className="text-red-500">*</span></Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))}
                  placeholder="e.g., Starter, Business, Enterprise"
                  required
                  data-testid="plan-name-input"
                />
              </div>

              {/* Monthly Fixed Price */}
              <div className="space-y-1.5">
                <Label>Monthly Fixed Price (₹) <span className="text-red-500">*</span></Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">₹</span>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    className="pl-7"
                    value={formData.monthly_price}
                    onChange={(e) => setFormData((p) => ({ ...p, monthly_price: e.target.value }))}
                    placeholder="e.g., 999"
                    required
                    data-testid="plan-monthly-price-input"
                  />
                </div>
                <p className="text-xs text-slate-400">GST exclusive — 18% GST will be added at checkout. Charged monthly for account to remain active.</p>
              </div>

              {/* Per Invoice Price */}
              <div className="space-y-1.5">
                <Label>Per Invoice Price (₹) <span className="text-red-500">*</span></Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">₹</span>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    className="pl-7"
                    value={formData.per_invoice_price}
                    onChange={(e) => setFormData((p) => ({ ...p, per_invoice_price: e.target.value }))}
                    placeholder="e.g., 10"
                    required
                    data-testid="plan-per-invoice-input"
                  />
                </div>
                <p className="text-xs text-slate-400">Deducted from operator wallet each time an invoice is generated.</p>
              </div>

              {/* Addons */}
              {addons.length > 0 && (
                <div className="space-y-2">
                  <Label>Included Addons</Label>
                  <p className="text-xs text-slate-400">Operators on this plan will have these addons automatically active.</p>
                  <div className="border rounded-lg p-3 space-y-2 max-h-44 overflow-y-auto">
                    {addons.map((addon) => (
                      <div key={addon.code} className="flex items-center gap-2">
                        <Checkbox
                          id={`addon-${addon.code}`}
                          checked={formData.included_addons.includes(addon.code)}
                          onCheckedChange={() => toggleAddon(addon.code)}
                          data-testid={`addon-checkbox-${addon.code}`}
                        />
                        <label htmlFor={`addon-${addon.code}`} className="text-sm cursor-pointer flex-1">
                          <span className="font-medium">{addon.name}</span>
                          {addon.price > 0 && <span className="text-slate-400 text-xs ml-1">(₹{addon.price}/mo)</span>}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-1">
                <Button type="button" variant="outline" className="flex-1" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={saving} className="flex-1 bg-[#0066B2] hover:bg-[#004080] text-white" data-testid="save-plan-btn">
                  {saving ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : null}
                  {editingPlan ? "Update Plan" : "Create Plan"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
}
