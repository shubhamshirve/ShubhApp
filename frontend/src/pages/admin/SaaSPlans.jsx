import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Checkbox } from "../../components/ui/checkbox";
import { Textarea } from "../../components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Package, Puzzle } from "lucide-react";

const AdminSaaSPlans = () => {
  const { authAxios } = useAuth();
  const [plans, setPlans] = useState([]);
  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  // Addon dialog state
  const [showAddonDialog, setShowAddonDialog] = useState(false);
  const [editingAddon, setEditingAddon] = useState(null);
  const [addonForm, setAddonForm] = useState({ name: "", code: "", price: 0, description: "" });
  const [formData, setFormData] = useState({
    name: "",
    monthly_price: 0,
    max_subscribers: 100,
    max_staff: 3,
    trial_enabled: false,
    trial_days: 0,
    notification_module: false,
    auto_reminder: false,
    audit_logs: false,
    payment_gateway_setup: false,
    gst_applicable: true,
    included_addons: []
  });

  useEffect(() => {
    Promise.all([fetchPlans(), fetchAddons()])
      .finally(() => setLoading(false));
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/admin/saas-plans");
      setPlans(response.data);
    } catch (error) {
      toast.error("Failed to load plans");
    }
  };

  const fetchAddons = async () => {
    try {
      const response = await authAxios.get("/admin/addons");
      setAddons(response.data);
    } catch { /* ignore */ }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingPlan) {
        await authAxios.put(`/admin/saas-plans/${editingPlan.id}`, formData);
        toast.success("Plan updated successfully");
      } else {
        await authAxios.post("/admin/saas-plans", formData);
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
      await authAxios.delete(`/admin/saas-plans/${planId}`);
      toast.success("Plan deleted");
      fetchPlans();
    } catch (error) {
      toast.error("Failed to delete plan");
    }
  };

  const openEditDialog = (plan) => {
    setEditingPlan(plan);
    setFormData({
      name: plan.name,
      monthly_price: plan.monthly_price,
      max_subscribers: plan.max_subscribers,
      max_staff: plan.max_staff,
      trial_enabled: plan.trial_enabled,
      trial_days: plan.trial_days,
      notification_module: plan.notification_module,
      auto_reminder: plan.auto_reminder,
      audit_logs: plan.audit_logs,
      payment_gateway_setup: plan.payment_gateway_setup,
      gst_applicable: plan.gst_applicable,
      included_addons: plan.included_addons || []
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingPlan(null);
    setFormData({
      name: "",
      monthly_price: 0,
      max_subscribers: 100,
      max_staff: 3,
      trial_enabled: false,
      trial_days: 0,
      notification_module: false,
      auto_reminder: false,
      audit_logs: false,
      payment_gateway_setup: false,
      gst_applicable: true,
      included_addons: []
    });
  };

  const toggleAddon = (addonCode) => {
    setFormData(prev => {
      const current = prev.included_addons || [];
      const updated = current.includes(addonCode)
        ? current.filter(c => c !== addonCode)
        : [...current, addonCode];
      return { ...prev, included_addons: updated };
    });
  };

  // ── Addon CRUD ──────────────────────────────────────────────────────────
  const openAddonCreate = () => {
    setEditingAddon(null);
    setAddonForm({ name: "", code: "", price: 0, description: "" });
    setShowAddonDialog(true);
  };

  const openAddonEdit = (addon) => {
    setEditingAddon(addon);
    setAddonForm({ name: addon.name, code: addon.code, price: addon.price, description: addon.description || "" });
    setShowAddonDialog(true);
  };

  const handleAddonSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingAddon) {
        await authAxios.put(`/admin/addons/${editingAddon.id}`, addonForm);
        toast.success("Add-on updated");
      } else {
        await authAxios.post("/admin/addons", addonForm);
        toast.success("Add-on created");
      }
      setShowAddonDialog(false);
      fetchAddons();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save add-on");
    }
  };

  const handleAddonDelete = async (id) => {
    if (!confirm("Delete this add-on?")) return;
    try {
      await authAxios.delete(`/admin/addons/${id}`);
      toast.success("Add-on deleted");
      fetchAddons();
    } catch {
      toast.error("Failed to delete add-on");
    }
  };

  if (loading) {
    return (
      <AdminLayout title="SaaS Plans">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="SaaS Plans">
      <div className="space-y-8 animate-fade-in">
        {/* ── SaaS Plans Section ── */}
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-slate-500">Manage subscription plans for operators</p>
            <Button onClick={() => { resetForm(); setShowDialog(true); }} data-testid="create-plan-btn">
              <Plus className="w-4 h-4 mr-2" />
              Create Plan
            </Button>
          </div>

          {/* Plans Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans.map((plan) => (
              <Card key={plan.id} className="relative card-hover" data-testid={`plan-card-${plan.id}`}>
                {plan.trial_enabled && (
                  <div className="absolute top-3 right-3 badge-trial">Trial</div>
                )}
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Package className="w-5 h-5 text-blue-600" />
                    {plan.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-slate-900">
                      ₹{plan.monthly_price.toLocaleString('en-IN')}
                    </span>
                    <span className="text-slate-500">/month</span>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Max Subscribers</span>
                      <span className="font-medium">{plan.max_subscribers}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Max Staff</span>
                      <span className="font-medium">{plan.max_staff}</span>
                    </div>
                  </div>

                  <div className="border-t pt-3 space-y-1.5 text-xs">
                    {[
                      { key: "notification_module", label: "Notification Module" },
                      { key: "auto_reminder", label: "Auto Reminder" },
                      { key: "audit_logs", label: "Audit Logs" },
                      { key: "payment_gateway_setup", label: "Payment Gateway" },
                    ].map(f => (
                      <div key={f.key} className="flex items-center gap-2">
                        <span className={plan[f.key] ? "text-emerald-600" : "text-slate-400"}>
                          {plan[f.key] ? "✓" : "×"}
                        </span>
                        <span>{f.label}</span>
                      </div>
                    ))}
                  </div>

                  {/* Included Addons */}
                  {plan.included_addons && plan.included_addons.length > 0 && (
                    <div className="border-t pt-3">
                      <p className="text-xs font-medium text-slate-500 mb-1.5 flex items-center gap-1">
                        <Puzzle className="w-3 h-3" /> Included Add-ons
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {plan.included_addons.map(code => {
                          const addon = addons.find(a => a.code === code);
                          return (
                            <span key={code} className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-medium">
                              {addon?.name || code}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => openEditDialog(plan)}
                      data-testid={`edit-plan-${plan.id}`}
                    >
                      <Pencil className="w-3 h-3 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => handleDelete(plan.id)}
                      data-testid={`delete-plan-${plan.id}`}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* ── Add-ons Section ── */}
        <div>
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <Puzzle className="w-5 h-5 text-indigo-600" />
                Add-ons Management
              </h2>
              <p className="text-slate-500 text-sm mt-0.5">Create add-ons that can be bundled with plans or purchased individually</p>
            </div>
            <Button variant="outline" onClick={openAddonCreate}>
              <Plus className="w-4 h-4 mr-2" />
              New Add-on
            </Button>
          </div>

          {addons.length === 0 ? (
            <Card>
              <CardContent className="text-center py-10 text-slate-500">
                <Puzzle className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                No add-ons created yet. Add some to bundle with your plans.
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {addons.map((addon) => (
                <Card key={addon.id} className="card-hover">
                  <CardContent className="pt-4 space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-semibold text-slate-900">{addon.name}</p>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">{addon.code}</p>
                      </div>
                      <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
                        ₹{addon.price}/mo
                      </span>
                    </div>
                    {addon.description && (
                      <p className="text-xs text-slate-500 line-clamp-2">{addon.description}</p>
                    )}
                    <div className="flex gap-2 pt-1">
                      <Button variant="outline" size="sm" className="flex-1" onClick={() => openAddonEdit(addon)}>
                        <Pencil className="w-3 h-3 mr-1" /> Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-600 hover:bg-red-50"
                        onClick={() => handleAddonDelete(addon.id)}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Create/Edit Plan Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingPlan ? "Edit Plan" : "Create New Plan"}</DialogTitle>
              <DialogDescription>
                {editingPlan ? "Update plan details" : "Create a new SaaS subscription plan"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 space-y-2">
                  <Label>Plan Name</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Professional"
                    required
                    data-testid="plan-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Monthly Price (₹)</Label>
                  <Input
                    type="number"
                    value={formData.monthly_price}
                    onChange={(e) => setFormData(prev => ({ ...prev, monthly_price: parseFloat(e.target.value) }))}
                    min="0"
                    required
                    data-testid="plan-price-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Max Subscribers</Label>
                  <Input
                    type="number"
                    value={formData.max_subscribers}
                    onChange={(e) => setFormData(prev => ({ ...prev, max_subscribers: parseInt(e.target.value) }))}
                    min="1"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label>Max Staff</Label>
                  <Input
                    type="number"
                    value={formData.max_staff}
                    onChange={(e) => setFormData(prev => ({ ...prev, max_staff: parseInt(e.target.value) }))}
                    min="1"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label>Trial Days</Label>
                  <Input
                    type="number"
                    value={formData.trial_days}
                    onChange={(e) => setFormData(prev => ({ ...prev, trial_days: parseInt(e.target.value) }))}
                    min="0"
                  />
                </div>
              </div>

              <div className="border-t pt-4 space-y-3">
                <p className="text-sm font-medium text-slate-700">Plan Features</p>
                <div className="space-y-3">
                  {[
                    { key: "trial_enabled", label: "Enable Trial" },
                    { key: "notification_module", label: "Notification Module" },
                    { key: "auto_reminder", label: "Auto Reminder" },
                    { key: "audit_logs", label: "Audit Logs" },
                    { key: "payment_gateway_setup", label: "Payment Gateway Setup" },
                    { key: "gst_applicable", label: "GST Applicable" }
                  ].map((feature) => (
                    <div key={feature.key} className="flex items-center justify-between">
                      <Label className="font-normal">{feature.label}</Label>
                      <Switch
                        checked={formData[feature.key]}
                        onCheckedChange={(checked) =>
                          setFormData(prev => ({ ...prev, [feature.key]: checked }))
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Included Add-ons */}
              {addons.length > 0 && (
                <div className="border-t pt-4 space-y-3">
                  <p className="text-sm font-medium text-slate-700 flex items-center gap-2">
                    <Puzzle className="w-4 h-4" /> Included Add-ons
                  </p>
                  <p className="text-xs text-slate-500">Select add-ons bundled with this plan at no extra cost</p>
                  <div className="space-y-2">
                    {addons.map((addon) => (
                      <div key={addon.code} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors">
                        <Checkbox
                          id={`addon-${addon.code}`}
                          checked={(formData.included_addons || []).includes(addon.code)}
                          onCheckedChange={() => toggleAddon(addon.code)}
                          data-testid={`addon-check-${addon.code}`}
                        />
                        <div className="flex-1">
                          <label htmlFor={`addon-${addon.code}`} className="text-sm font-medium cursor-pointer">
                            {addon.name}
                          </label>
                          <p className="text-xs text-slate-500">{addon.description || addon.code} — ₹{addon.price}/mo standalone</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-plan-btn">
                  {editingPlan ? "Update Plan" : "Create Plan"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Create/Edit Add-on Dialog */}
        <Dialog open={showAddonDialog} onOpenChange={setShowAddonDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Puzzle className="w-5 h-5" />
                {editingAddon ? "Edit Add-on" : "Create Add-on"}
              </DialogTitle>
              <DialogDescription>
                {editingAddon ? "Update add-on details" : "Create a new purchasable add-on"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddonSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={addonForm.name}
                  onChange={(e) => setAddonForm(p => ({ ...p, name: e.target.value }))}
                  placeholder="e.g., WhatsApp Notifications"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Code <span className="text-xs text-slate-400">(unique identifier)</span></Label>
                <Input
                  value={addonForm.code}
                  onChange={(e) => setAddonForm(p => ({ ...p, code: e.target.value.toLowerCase().replace(/\s+/g, "_") }))}
                  placeholder="e.g., notifications"
                  required
                  disabled={!!editingAddon}
                />
              </div>
              <div className="space-y-2">
                <Label>Monthly Price (₹)</Label>
                <Input
                  type="number"
                  min="0"
                  value={addonForm.price}
                  onChange={(e) => setAddonForm(p => ({ ...p, price: parseFloat(e.target.value) }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  value={addonForm.description}
                  onChange={(e) => setAddonForm(p => ({ ...p, description: e.target.value }))}
                  placeholder="Short description..."
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setShowAddonDialog(false)}>Cancel</Button>
                <Button type="submit">{editingAddon ? "Update" : "Create"} Add-on</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
};

export default AdminSaaSPlans;
