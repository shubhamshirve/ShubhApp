import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
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
  LogIn
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
                            <DropdownMenuItem onClick={() => {
                              setSelectedOperator(operator);
                              setShowAssignPlan(true);
                            }}>
                              <Package className="w-4 h-4 mr-2" />
                              Assign Plan
                            </DropdownMenuItem>
                            {operator.status !== "suspended" && (
                              <DropdownMenuItem 
                                onClick={() => handleSuspend(operator.id)}
                                className="text-red-600"
                              >
                                <Ban className="w-4 h-4 mr-2" />
                                Suspend
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
      </div>
    </AdminLayout>
  );
};

export default AdminOperators;
