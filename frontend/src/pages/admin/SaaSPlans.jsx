import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { Plus, Pencil, Trash2, Package, IndianRupee } from "lucide-react";

const AdminSaaSPlans = () => {
  const { authAxios } = useAuth();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
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
    gst_applicable: true
  });

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/admin/saas-plans");
      setPlans(response.data);
    } catch (error) {
      toast.error("Failed to load plans");
    } finally {
      setLoading(false);
    }
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
      gst_applicable: plan.gst_applicable
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
      gst_applicable: true
    });
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
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex justify-between items-center">
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
                  <div className="flex items-center gap-2">
                    <span className={plan.notification_module ? "text-emerald-600" : "text-slate-400"}>
                      {plan.notification_module ? "✓" : "×"}
                    </span>
                    <span>Notification Module</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={plan.auto_reminder ? "text-emerald-600" : "text-slate-400"}>
                      {plan.auto_reminder ? "✓" : "×"}
                    </span>
                    <span>Auto Reminder</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={plan.audit_logs ? "text-emerald-600" : "text-slate-400"}>
                      {plan.audit_logs ? "✓" : "×"}
                    </span>
                    <span>Audit Logs</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={plan.payment_gateway_setup ? "text-emerald-600" : "text-slate-400"}>
                      {plan.payment_gateway_setup ? "✓" : "×"}
                    </span>
                    <span>Payment Gateway</span>
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="flex-1"
                    onClick={() => openEditDialog(plan)}
                  >
                    <Pencil className="w-3 h-3 mr-1" />
                    Edit
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    onClick={() => handleDelete(plan.id)}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Create/Edit Dialog */}
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
      </div>
    </AdminLayout>
  );
};

export default AdminSaaSPlans;
