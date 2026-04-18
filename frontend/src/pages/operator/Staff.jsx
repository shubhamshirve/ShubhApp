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
import { Plus, Pencil, Trash2, UserCog, Shield } from "lucide-react";

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
  const [editingStaff, setEditingStaff] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    phone: "",
    permissions: [],
    status: "active"
  });

  useEffect(() => {
    fetchStaff();
    fetchDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // Validation
    if (!formData.name.trim() || formData.name.trim().length < 2) {
      toast.error("Name must be at least 2 characters"); return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      toast.error("Please enter a valid email address"); return;
    }
    const phoneDigits = (formData.phone || "").replace(/\D/g, "");
    if (!phoneDigits || phoneDigits.length !== 10) {
      toast.error("Phone number must be exactly 10 digits"); return;
    }
    // Password is required only when creating new staff
    if (!editingStaff && (!formData.password || formData.password.length < 6)) {
      toast.error("Password must be at least 6 characters"); return;
    }
    try {
      if (editingStaff) {
        // Update existing staff
        await authAxios.put(`/operator/staff/${editingStaff.id}`, formData);
        toast.success("Staff member updated successfully");
      } else {
        // Create new staff
        await authAxios.post("/operator/staff", formData);
        toast.success("Staff member added successfully");
      }
      setShowDialog(false);
      resetForm();
      fetchStaff();
    } catch (error) {
      toast.error(error.response?.data?.detail || (editingStaff ? "Failed to update staff" : "Failed to add staff"));
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

  const openEditDialog = (member) => {
    setEditingStaff(member);
    setFormData({
      name: member.name,
      email: member.email,
      password: "",
      phone: member.phone || "",
      permissions: member.permissions || [],
      status: member.status || "active"
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingStaff(null);
    setFormData({
      name: "",
      email: "",
      password: "",
      phone: "",
      permissions: [],
      status: "active"
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
            Add Staff Member
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
                        <span className={`badge-active ${member.status !== 'active' ? 'bg-red-50 text-red-700 border-red-200' : ''}`}>{member.status}</span>
                      </TableCell>
                      <TableCell className="flex gap-1 justify-center">
                        <Button 
                          variant="ghost" 
                          size="icon"
                          className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                          onClick={() => openEditDialog(member)}
                          disabled={isReadOnly}
                          data-testid={`edit-staff-${member.id}`}
                          title="Edit staff"
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => handleDelete(member.id)}
                          disabled={isReadOnly}
                          title="Delete staff"
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
              <DialogTitle>{editingStaff ? "Edit Staff Member" : "Add Staff Member"}</DialogTitle>
              <DialogDescription>
                {editingStaff ? "Update team member details and permissions" : "Add a new team member with specific permissions"}
              </DialogDescription>
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
                <Label>Password {!editingStaff && "*"}</Label>
                <Input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  placeholder={editingStaff ? "Leave empty to keep current password" : "Min. 6 characters"}
                  required={!editingStaff}
                  data-testid="staff-password-input"
                />
                {editingStaff && <p className="text-xs text-slate-500">Leave blank to keep current password</p>}
              </div>

              {editingStaff && (
                <div className="space-y-2">
                  <Label>Account Status</Label>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    value={formData.status}
                    onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value }))}
                    data-testid="staff-status-select"
                  >
                    <option value="active">Active</option>
                    <option value="suspended">Suspended</option>
                  </select>
                </div>
              )}

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
                <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-staff-btn">
                  {editingStaff ? "Update Staff" : "Add Staff"}
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
