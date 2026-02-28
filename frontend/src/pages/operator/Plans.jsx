import { useState, useEffect } from "react";
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
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Package, IndianRupee } from "lucide-react";

const OperatorPlans = () => {
  const { authAxios } = useAuth();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    price: 0,
    validity: "monthly",
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
      tax_percentage: 0,
      tax_type: "none",
      description: ""
    });
  };

  const getValidityLabel = (validity) => {
    const labels = {
      monthly: "Monthly",
      quarterly: "Quarterly",
      half_yearly: "Half Yearly",
      yearly: "Yearly"
    };
    return labels[validity] || validity;
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
        <div className="flex justify-between items-center">
          <p className="text-slate-500">Define service plans for your subscribers</p>
          <Button 
            onClick={() => { resetForm(); setShowDialog(true); }}
            disabled={isReadOnly}
            data-testid="create-plan-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create Plan
          </Button>
        </div>

        {/* Plans Grid */}
        {plans.length === 0 ? (
          <Card className="p-8 text-center">
            <Package className="w-12 h-12 mx-auto mb-4 text-slate-300" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">No plans yet</h3>
            <p className="text-slate-500 mb-4">Create your first service plan to start adding subscribers</p>
            <Button onClick={() => setShowDialog(true)} disabled={isReadOnly}>
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Plan
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plans.map((plan) => (
              <Card key={plan.id} className="card-hover" data-testid={`plan-card-${plan.id}`}>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Package className="w-5 h-5 text-blue-600" />
                    {plan.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-slate-900">
                      ₹{plan.price.toLocaleString('en-IN')}
                    </span>
                    <span className="text-slate-500">/{getValidityLabel(plan.validity).toLowerCase()}</span>
                  </div>

                  {plan.description && (
                    <p className="text-sm text-slate-500">{plan.description}</p>
                  )}

                  <div className="space-y-2 text-sm border-t pt-3">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Validity</span>
                      <span className="font-medium">{getValidityLabel(plan.validity)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Tax</span>
                      <span className="font-medium">
                        {plan.tax_type === "none" ? "No Tax" : `${plan.tax_percentage}% (${plan.tax_type})`}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Status</span>
                      <span className="badge-active">{plan.status}</span>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="flex-1"
                      onClick={() => openEditDialog(plan)}
                      disabled={isReadOnly}
                    >
                      <Pencil className="w-3 h-3 mr-1" />
                      Edit
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => handleDelete(plan.id)}
                      disabled={isReadOnly}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
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
                    onChange={(e) => setFormData(prev => ({ ...prev, price: parseFloat(e.target.value) }))}
                    min="0"
                    required
                    data-testid="plan-price-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Validity *</Label>
                  <Select 
                    value={formData.validity} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, validity: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="monthly">Monthly</SelectItem>
                      <SelectItem value="quarterly">Quarterly</SelectItem>
                      <SelectItem value="half_yearly">Half Yearly</SelectItem>
                      <SelectItem value="yearly">Yearly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Tax Percentage (%)</Label>
                  <Input
                    type="number"
                    value={formData.tax_percentage}
                    onChange={(e) => setFormData(prev => ({ ...prev, tax_percentage: parseFloat(e.target.value) || 0 }))}
                    min="0"
                    max="100"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Tax Type</Label>
                  <Select 
                    value={formData.tax_type} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, tax_type: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
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
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Plan description (optional)"
                  rows={3}
                />
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
    </OperatorLayout>
  );
};

export default OperatorPlans;
