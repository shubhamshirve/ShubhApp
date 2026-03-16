import { useState, useEffect } from "react";
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
} from "../../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Checkbox } from "../../components/ui/checkbox";
import { toast } from "sonner";
import { Plus, Trash2, UserCog, Shield } from "lucide-react";

const PERMISSIONS = [
  { id: "view_subscribers", label: "View Subscribers" },
  { id: "manage_subscribers", label: "Manage Subscribers" },
  { id: "view_invoices", label: "View Invoices" },
  { id: "manage_invoices", label: "Manage Invoices" },
  { id: "view_plans", label: "View Plans" },
  { id: "manage_plans", label: "Manage Plans" },
  { id: "view_reports", label: "View Reports" }
];

const OperatorStaff = () => {
  const { authAxios } = useAuth();
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    phone: "",
    permissions: []
  });

  useEffect(() => {
    fetchStaff();
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

  const fetchStaff = async () => {
    try {
      const response = await authAxios.get("/operator/staff");
      setStaff(response.data);
    } catch (error) {
      toast.error("Failed to load staff");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await authAxios.post("/operator/staff", formData);
      toast.success("Staff member added successfully");
      setShowDialog(false);
      resetForm();
      fetchStaff();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to add staff");
    }
  };

  const handleDelete = async (staffId) => {
    if (!confirm("Are you sure you want to remove this staff member?")) return;
    try {
      await authAxios.delete(`/operator/staff/${staffId}`);
      toast.success("Staff member removed");
      fetchStaff();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to remove staff");
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      email: "",
      password: "",
      phone: "",
      permissions: []
    });
  };

  const togglePermission = (permissionId) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permissionId)
        ? prev.permissions.filter(p => p !== permissionId)
        : [...prev.permissions, permissionId]
    }));
  };

  if (loading) {
    return (
      <OperatorLayout title="Staff Management">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const isReadOnly = dashboardStats?.is_read_only;

  return (
    <OperatorLayout title="Staff Management" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex justify-between items-center">
          <p className="text-slate-500">Manage staff members and their permissions</p>
          <Button 
            onClick={() => { resetForm(); setShowDialog(true); }}
            disabled={isReadOnly}
            data-testid="add-staff-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Staff
          </Button>
        </div>

        {/* Staff Table */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Permissions</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {staff.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-slate-500">
                      <UserCog className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No staff members yet
                    </TableCell>
                  </TableRow>
                ) : (
                  staff.map((member) => (
                    <TableRow key={member.id} data-testid={`staff-row-${member.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                            <span className="text-purple-600 font-medium text-sm">
                              {member.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <span className="font-medium">{member.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{member.email}</TableCell>
                      <TableCell>{member.phone || "-"}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {member.permissions?.length > 0 ? (
                            member.permissions.slice(0, 2).map(p => (
                              <span key={p} className="text-xs bg-slate-100 px-2 py-1 rounded">
                                {PERMISSIONS.find(perm => perm.id === p)?.label || p}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-slate-400">No permissions</span>
                          )}
                          {member.permissions?.length > 2 && (
                            <span className="text-xs text-slate-500">
                              +{member.permissions.length - 2} more
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="badge-active">{member.status}</span>
                      </TableCell>
                      <TableCell>
                        <Button 
                          variant="ghost" 
                          size="icon"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => handleDelete(member.id)}
                          disabled={isReadOnly}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Add Staff Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Add Staff Member</DialogTitle>
              <DialogDescription>Add a new team member with specific permissions</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Staff name"
                    required
                    data-testid="staff-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    placeholder="9876543210"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="staff@company.com"
                  required
                  data-testid="staff-email-input"
                />
              </div>

              <div className="space-y-2">
                <Label>Password *</Label>
                <Input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Min. 6 characters"
                  required
                  data-testid="staff-password-input"
                />
              </div>

              <div className="space-y-3 border-t pt-4">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-slate-600" />
                  <Label className="text-sm font-medium">Permissions</Label>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {PERMISSIONS.map((permission) => (
                    <div key={permission.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={permission.id}
                        checked={formData.permissions.includes(permission.id)}
                        onCheckedChange={() => togglePermission(permission.id)}
                      />
                      <label
                        htmlFor={permission.id}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {permission.label}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-staff-btn">
                  Add Staff
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorStaff;
