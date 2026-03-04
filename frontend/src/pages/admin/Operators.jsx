import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
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
  DialogFooter,
} from "../../components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../../components/ui/alert-dialog";
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
import { 
  Building2, 
  MoreVertical, 
  Eye, 
  Ban, 
  CheckCircle,
  Search,
  Package,
  LogIn,
  Plus,
  Calendar,
  Trash2
} from "lucide-react";

const AdminOperators = () => {
  const { authAxios, login } = useAuth();
  const navigate = useNavigate();
  const [operators, setOperators] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedOperator, setSelectedOperator] = useState(null);
  const [showAssignPlan, setShowAssignPlan] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("");
  
  // Create Operator Dialog
  const [showCreateOperator, setShowCreateOperator] = useState(false);
  const [createForm, setCreateForm] = useState({
    company_name: "",
    owner_name: "",
    email: "",
    phone: "",
    password: "",
    gst_number: "",
    charge_gst: false,
    bank_account_name: "",
    bank_account_number: "",
    bank_ifsc: "",
    bank_name: "",
    saas_plan_id: "",
    status: "active",
    subscription_months: 1
  });
  
  // Extend Subscription Dialog
  const [showExtendDialog, setShowExtendDialog] = useState(false);
  const [extendMonths, setExtendMonths] = useState("");
  const [customDate, setCustomDate] = useState("");
  
  // Delete Confirmation Dialog
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  useEffect(() => {
    fetchOperators();
    fetchPlans();
  }, []);

  const fetchOperators = async () => {
    try {
      const response = await authAxios.get("/admin/operators");
      setOperators(response.data);
    } catch (error) {
      toast.error("Failed to load operators");
    } finally {
      setLoading(false);
    }
  };

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/admin/saas-plans");
      setPlans(response.data);
    } catch (error) {
      console.error("Failed to load plans");
    }
  };

  const handleCreateOperator = async () => {
    if (!createForm.company_name || !createForm.owner_name || !createForm.email || 
        !createForm.phone || !createForm.password || !createForm.saas_plan_id) {
      toast.error("Please fill all required fields");
      return;
    }
    
    try {
      await authAxios.post("/admin/operators/create", createForm);
      toast.success("Operator created successfully");
      setShowCreateOperator(false);
      setCreateForm({
        company_name: "",
        owner_name: "",
        email: "",
        phone: "",
        password: "",
        gst_number: "",
        charge_gst: false,
        bank_account_name: "",
        bank_account_number: "",
        bank_ifsc: "",
        bank_name: "",
        saas_plan_id: "",
        status: "active",
        subscription_months: 1
      });
      fetchOperators();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create operator");
    }
  };

  const handleExtendSubscription = async () => {
    if (!extendMonths && !customDate) {
      toast.error("Please select months or custom date");
      return;
    }
    
    try {
      const payload = {};
      if (customDate) {
        payload.custom_date = new Date(customDate).toISOString();
      } else {
        payload.months = parseInt(extendMonths);
      }
      
      await authAxios.post(`/admin/operators/${selectedOperator.id}/extend-subscription`, payload);
      toast.success("Subscription extended successfully");
      setShowExtendDialog(false);
      setExtendMonths("");
      setCustomDate("");
      fetchOperators();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to extend subscription");
    }
  };

  const handleDeleteOperator = async () => {
    if (deleteConfirmText !== selectedOperator?.company_name) {
      toast.error("Company name doesn't match");
      return;
    }
    
    try {
      await authAxios.delete(`/admin/operators/${selectedOperator.id}`);
      toast.success("Operator deleted successfully");
      setShowDeleteDialog(false);
      setDeleteConfirmText("");
      setSelectedOperator(null);
      fetchOperators();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete operator");
    }
  };

  const handleSuspend = async (operatorId) => {
    try {
      await authAxios.post(`/admin/operators/${operatorId}/suspend`);
      toast.success("Operator suspended");
      fetchOperators();
    } catch (error) {
      toast.error("Failed to suspend operator");
    }
  };

  const handleAssignPlan = async () => {
    if (!selectedPlan || !selectedOperator) return;
    
    try {
      await authAxios.post(`/admin/operators/${selectedOperator.id}/assign-plan?plan_id=${selectedPlan}`);
      toast.success("Plan assigned successfully");
      setShowAssignPlan(false);
      setSelectedPlan("");
      fetchOperators();
    } catch (error) {
      toast.error("Failed to assign plan");
    }
  };

  const handleImpersonate = async (operator) => {
    try {
      const response = await authAxios.post(`/admin/operators/${operator.id}/impersonate`);
      const { access_token } = response.data;
      localStorage.setItem("token", access_token);
      localStorage.setItem("impersonating", "true");
      window.location.href = "/operator";
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to impersonate operator");
    }
  };

  const handleActivate = async (operatorId) => {
    try {
      await authAxios.post(`/admin/operators/${operatorId}/activate`);
      toast.success("Operator activated");
      fetchOperators();
    } catch (error) {
      toast.error("Failed to activate operator");
    }
  };

  const filteredOperators = operators.filter(op => 
    op.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    op.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusBadge = (status) => {
    const badges = {
      active: "badge-active",
      trial: "badge-trial",
      suspended: "badge-suspended",
      expired: "badge-overdue"
    };
    return <span className={badges[status] || "badge-pending"}>{status}</span>;
  };

  if (loading) {
    return (
      <AdminLayout title="Operators">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Operators">
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search operators..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
              data-testid="search-operators"
            />
          </div>
          <Button onClick={() => setShowCreateOperator(true)} data-testid="create-operator-btn">
            <Plus className="w-4 h-4 mr-2" />
            Create Operator
          </Button>
        </div>

        {/* Operators Table */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Company</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOperators.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                      No operators found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredOperators.map((operator) => (
                    <TableRow key={operator.id} data-testid={`operator-row-${operator.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
                            <Building2 className="w-4 h-4 text-slate-600" />
                          </div>
                          <span className="font-medium">{operator.company_name}</span>
                        </div>
                      </TableCell>
                      <TableCell>{operator.owner_name}</TableCell>
                      <TableCell className="font-mono text-sm">{operator.email}</TableCell>
                      <TableCell>{getStatusBadge(operator.status)}</TableCell>
                      <TableCell>{operator.saas_plan_name || "-"}</TableCell>
                      <TableCell className="text-sm text-slate-500">
                        {operator.subscription_ends_at 
                          ? new Date(operator.subscription_ends_at).toLocaleDateString()
                          : operator.trial_ends_at 
                            ? new Date(operator.trial_ends_at).toLocaleDateString()
                            : "-"}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" data-testid={`operator-menu-${operator.id}`}>
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem 
                              onClick={() => handleImpersonate(operator)}
                              data-testid={`impersonate-${operator.id}`}
                            >
                              <LogIn className="w-4 h-4 mr-2" />
                              Login as Operator
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                              setSelectedOperator(operator);
                              setShowExtendDialog(true);
                            }}>
                              <Calendar className="w-4 h-4 mr-2" />
                              Extend Subscription
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                              setSelectedOperator(operator);
                              setShowAssignPlan(true);
                            }}>
                              <Package className="w-4 h-4 mr-2" />
                              Assign Plan
                            </DropdownMenuItem>
                            {operator.status === "suspended" ? (
                              <DropdownMenuItem 
                                onClick={() => handleActivate(operator.id)}
                                className="text-emerald-600"
                                data-testid={`activate-${operator.id}`}
                              >
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Activate
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem 
                                onClick={() => handleSuspend(operator.id)}
                                className="text-amber-600"
                                data-testid={`suspend-${operator.id}`}
                              >
                                <Ban className="w-4 h-4 mr-2" />
                                Suspend
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem 
                              onClick={() => {
                                setSelectedOperator(operator);
                                setShowDeleteDialog(true);
                              }}
                              className="text-red-600"
                              data-testid={`delete-${operator.id}`}
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
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

        {/* Create Operator Dialog */}
        <Dialog open={showCreateOperator} onOpenChange={setShowCreateOperator}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create New Operator</DialogTitle>
              <DialogDescription>
                Manually create an operator with direct plan assignment
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {/* Basic Information */}
              <p className="text-sm font-medium text-slate-700">Basic Information</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Company Name *</Label>
                  <Input
                    value={createForm.company_name}
                    onChange={(e) => setCreateForm({...createForm, company_name: e.target.value})}
                    placeholder="Your Company Ltd."
                    data-testid="create-op-company"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Owner Name *</Label>
                  <Input
                    value={createForm.owner_name}
                    onChange={(e) => setCreateForm({...createForm, owner_name: e.target.value})}
                    placeholder="John Doe"
                    data-testid="create-op-owner"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Email *</Label>
                  <Input
                    type="email"
                    value={createForm.email}
                    onChange={(e) => setCreateForm({...createForm, email: e.target.value})}
                    placeholder="you@company.com"
                    data-testid="create-op-email"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone *</Label>
                  <Input
                    type="tel"
                    value={createForm.phone}
                    onChange={(e) => setCreateForm({...createForm, phone: e.target.value})}
                    placeholder="9876543210"
                    data-testid="create-op-phone"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Password *</Label>
                <Input
                  type="password"
                  value={createForm.password}
                  onChange={(e) => setCreateForm({...createForm, password: e.target.value})}
                  placeholder="Min. 6 characters"
                  data-testid="create-op-password"
                />
              </div>

              {/* GST Information */}
              <div className="border-t border-slate-200 pt-4">
                <p className="text-sm font-medium text-slate-700 mb-3">GST Information</p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>GST Number</Label>
                    <Input
                      value={createForm.gst_number}
                      onChange={(e) => setCreateForm({...createForm, gst_number: e.target.value})}
                      placeholder="22AAAAA0000A1Z5"
                    />
                  </div>
                  <div className="flex items-center gap-3 pt-6">
                    <Switch
                      checked={createForm.charge_gst}
                      onCheckedChange={(checked) => setCreateForm({...createForm, charge_gst: checked})}
                    />
                    <Label className="font-normal">Charge GST</Label>
                  </div>
                </div>
              </div>

              {/* Bank Details */}
              <div className="border-t border-slate-200 pt-4">
                <p className="text-sm font-medium text-slate-700 mb-3">Bank Details (Optional)</p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Account Holder Name</Label>
                    <Input
                      value={createForm.bank_account_name}
                      onChange={(e) => setCreateForm({...createForm, bank_account_name: e.target.value})}
                      placeholder="Account holder name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Bank Name</Label>
                    <Input
                      value={createForm.bank_name}
                      onChange={(e) => setCreateForm({...createForm, bank_name: e.target.value})}
                      placeholder="State Bank of India"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="space-y-2">
                    <Label>Account Number</Label>
                    <Input
                      value={createForm.bank_account_number}
                      onChange={(e) => setCreateForm({...createForm, bank_account_number: e.target.value})}
                      placeholder="1234567890"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>IFSC Code</Label>
                    <Input
                      value={createForm.bank_ifsc}
                      onChange={(e) => setCreateForm({...createForm, bank_ifsc: e.target.value})}
                      placeholder="SBIN0001234"
                    />
                  </div>
                </div>
              </div>

              {/* Plan & Subscription */}
              <div className="border-t border-slate-200 pt-4">
                <p className="text-sm font-medium text-slate-700 mb-3">Plan & Subscription</p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>SaaS Plan *</Label>
                    <Select value={createForm.saas_plan_id} onValueChange={(value) => setCreateForm({...createForm, saas_plan_id: value})}>
                      <SelectTrigger data-testid="create-op-plan">
                        <SelectValue placeholder="Choose a plan" />
                      </SelectTrigger>
                      <SelectContent>
                        {plans.map((plan) => (
                          <SelectItem key={plan.id} value={plan.id}>
                            {plan.name} - ₹{plan.monthly_price}/mo
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Subscription Months *</Label>
                    <Input
                      type="number"
                      min="1"
                      value={createForm.subscription_months}
                      onChange={(e) => setCreateForm({...createForm, subscription_months: parseInt(e.target.value) || 1})}
                      placeholder="1"
                    />
                  </div>
                </div>
                <div className="mt-4 space-y-2">
                  <Label>Status</Label>
                  <Select value={createForm.status} onValueChange={(value) => setCreateForm({...createForm, status: value})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="suspended">Suspended</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateOperator(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateOperator} data-testid="create-operator-submit">
                Create Operator
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Extend Subscription Dialog */}
        <Dialog open={showExtendDialog} onOpenChange={setShowExtendDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Extend Subscription</DialogTitle>
              <DialogDescription>
                Extend subscription for {selectedOperator?.company_name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Extend by Months</Label>
                <Select value={extendMonths} onValueChange={setExtendMonths}>
                  <SelectTrigger data-testid="extend-months-select">
                    <SelectValue placeholder="Select months" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 Month</SelectItem>
                    <SelectItem value="3">3 Months</SelectItem>
                    <SelectItem value="6">6 Months</SelectItem>
                    <SelectItem value="12">12 Months</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-white px-2 text-slate-500">Or</span>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Set Custom End Date</Label>
                <Input
                  type="date"
                  value={customDate}
                  onChange={(e) => setCustomDate(e.target.value)}
                  data-testid="custom-date-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowExtendDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleExtendSubscription} disabled={!extendMonths && !customDate} data-testid="extend-submit-btn">
                Extend Subscription
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Assign Plan Dialog */}
        <Dialog open={showAssignPlan} onOpenChange={setShowAssignPlan}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Assign SaaS Plan</DialogTitle>
              <DialogDescription>
                Assign a plan to {selectedOperator?.company_name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Select Plan</Label>
                <Select value={selectedPlan} onValueChange={setSelectedPlan}>
                  <SelectTrigger data-testid="select-plan">
                    <SelectValue placeholder="Choose a plan" />
                  </SelectTrigger>
                  <SelectContent>
                    {plans.filter(p => !p.trial_enabled).map((plan) => (
                      <SelectItem key={plan.id} value={plan.id}>
                        {plan.name} - ₹{plan.monthly_price}/mo
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setShowAssignPlan(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAssignPlan} disabled={!selectedPlan} data-testid="assign-plan-btn">
                  Assign Plan
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Operator</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete the operator
                and all associated data.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <div className="py-4">
              <Label>Type "{selectedOperator?.company_name}" to confirm</Label>
              <Input
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="Company name"
                className="mt-2"
                data-testid="delete-confirm-input"
              />
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => {
                setShowDeleteDialog(false);
                setDeleteConfirmText("");
              }}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteOperator}
                disabled={deleteConfirmText !== selectedOperator?.company_name}
                className="bg-red-600 hover:bg-red-700"
                data-testid="delete-confirm-btn"
              >
                Delete Operator
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AdminLayout>
  );
};

export default AdminOperators;
