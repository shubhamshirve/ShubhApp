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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Badge } from "../../components/ui/badge";
import { Plus, Pencil, Trash2, Package, Puzzle, Users, UserCog, IndianRupee } from "lucide-react";

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
  // Tier pricing (must match backend models.py)
  const SUBSCRIBER_TIERS = {250: 500, 500: 1000, 750: 1500, 1000: 2000, 1500: 3000, 2000: 4000, 3000: 5500};
  const STAFF_TIERS = {0: 0, 5: 100, 10: 200, 20: 300};

  const normalizeTier = (value, tierMap) => {
    const keys = Object.keys(tierMap).map(Number);
    if (keys.includes(value)) return value;
    return keys.reduce((prev, curr) =>
      Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
    );
  };

  const calcPrice = (maxSubs, maxStaff, selectedAddons) => {
    const base = SUBSCRIBER_TIERS[maxSubs] || 0;
    const staff = STAFF_TIERS[maxStaff] || 0;
    const addonTotal = selectedAddons.reduce((sum, code) => {
      const addon = addons.find(a => a.code === code);
      return sum + (addon?.price || 0);
    }, 0);
    return base + staff + addonTotal;
  };

  const [formData, setFormData] = useState({
    name: "",
    max_subscribers: 250,
    max_staff: 0,
    trial_enabled: false,
    trial_days: 0,
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
      max_subscribers: normalizeTier(plan.max_subscribers, SUBSCRIBER_TIERS),
      max_staff: normalizeTier(plan.max_staff, STAFF_TIERS),
      trial_enabled: plan.trial_enabled,
      trial_days: plan.trial_days,
      gst_applicable: plan.gst_applicable,
      included_addons: plan.included_addons || []
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingPlan(null);
    setFormData({
      name: "",
      max_subscribers: 250,
      max_staff: 0,
      trial_enabled: false,
      trial_days: 0,
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
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 flex items-center gap-1"><Users className="w-3.5 h-3.5" /> Subscribers</span>
                      <span className="font-medium">{plan.max_subscribers.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 flex items-center gap-1"><UserCog className="w-3.5 h-3.5" /> Staff</span>
                      <span className="font-medium">{plan.max_staff === 0 ? "No staff" : plan.max_staff}</span>
                    </div>
                    {plan.trial_enabled && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Trial</span>
                        <span className="font-medium text-amber-600">{plan.trial_days} days</span>
                      </div>
                    )}
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
              <div className="space-y-2">
                <Label>Plan Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Professional"
                  required
                  data-testid="plan-name-input"
                />
              </div>

              {/* Tier Selectors */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> Subscriber Count</Label>
                  <Select
                    value={String(formData.max_subscribers)}
                    onValueChange={(v) => setFormData(prev => ({ ...prev, max_subscribers: parseInt(v) }))}
                  >
                    <SelectTrigger data-testid="subscribers-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(SUBSCRIBER_TIERS).map(([count, price]) => (
                        <SelectItem key={count} value={count}>
                          {parseInt(count).toLocaleString()} users — ₹{price}/mo
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-1"><UserCog className="w-3.5 h-3.5" /> Staff Count</Label>
                  <Select
                    value={String(formData.max_staff)}
                    onValueChange={(v) => setFormData(prev => ({ ...prev, max_staff: parseInt(v) }))}
                  >
                    <SelectTrigger data-testid="staff-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(STAFF_TIERS).map(([count, price]) => (
                        <SelectItem key={count} value={count}>
                          {parseInt(count) === 0 ? "No staff" : `${count} staff`} — {price === 0 ? "Free" : `+₹${price}/mo`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Live Price Preview */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-xs font-medium text-slate-500 mb-1.5 flex items-center gap-1">
                  <IndianRupee className="w-3 h-3" /> Price Breakdown
                </p>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between text-slate-600">
                    <span>Subscribers ({formData.max_subscribers})</span>
                    <span>₹{(SUBSCRIBER_TIERS[formData.max_subscribers] || 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-slate-600">
                    <span>Staff ({formData.max_staff === 0 ? "None" : formData.max_staff})</span>
                    <span>+₹{(STAFF_TIERS[formData.max_staff] || 0).toLocaleString()}</span>
                  </div>
                  {formData.included_addons.length > 0 && (
                    <div className="flex justify-between text-slate-600">
                      <span>Add-ons ({formData.included_addons.length})</span>
                      <span>+₹{formData.included_addons.reduce((s, c) => s + (addons.find(a => a.code === c)?.price || 0), 0).toLocaleString()}</span>
                    </div>
                  )}
                  <div className="flex justify-between font-semibold text-slate-900 border-t pt-1 mt-1">
                    <span>Total / month</span>
                    <span className="text-blue-700">₹{calcPrice(formData.max_subscribers, formData.max_staff, formData.included_addons).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Trial Days</Label>
                  <Input
                    type="number"
                    value={formData.trial_days}
                    onChange={(e) => setFormData(prev => ({ ...prev, trial_days: parseInt(e.target.value) || 0 }))}
                    min="0"
                  />
                </div>
              </div>

              <div className="border-t pt-4 space-y-3">
                <p className="text-sm font-medium text-slate-700">Plan Options</p>
                <div className="space-y-3">
                  {[
                    { key: "trial_enabled", label: "Enable Trial Period" },
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
