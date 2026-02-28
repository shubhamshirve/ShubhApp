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
import { Plus, Search, MoreVertical, Pencil, Trash2, Users, Phone } from "lucide-react";

const OperatorSubscribers = () => {
  const { authAxios } = useAuth();
  const [subscribers, setSubscribers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showDialog, setShowDialog] = useState(false);
  const [editingSubscriber, setEditingSubscriber] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    whatsapp_number: "",
    email: "",
    address: "",
    plan_id: "",
    billing_date: 1,
    discount: 0
  });

  useEffect(() => {
    fetchSubscribers();
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

  const fetchSubscribers = async () => {
    try {
      const response = await authAxios.get("/operator/subscribers");
      setSubscribers(response.data);
    } catch (error) {
      toast.error("Failed to load subscribers");
    } finally {
      setLoading(false);
    }
  };

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/operator/plans");
      setPlans(response.data);
    } catch (error) {
      console.error("Failed to load plans");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingSubscriber) {
        await authAxios.put(`/operator/subscribers/${editingSubscriber.id}`, formData);
        toast.success("Subscriber updated successfully");
      } else {
        await authAxios.post("/operator/subscribers", formData);
        toast.success("Subscriber created successfully");
      }
      setShowDialog(false);
      resetForm();
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save subscriber");
    }
  };

  const handleDelete = async (subscriberId) => {
    if (!confirm("Are you sure you want to delete this subscriber?")) return;
    try {
      await authAxios.delete(`/operator/subscribers/${subscriberId}`);
      toast.success("Subscriber deleted");
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete subscriber");
    }
  };

  const openEditDialog = (subscriber) => {
    setEditingSubscriber(subscriber);
    setFormData({
      name: subscriber.name,
      whatsapp_number: subscriber.whatsapp_number,
      email: subscriber.email || "",
      address: subscriber.address || "",
      plan_id: subscriber.plan_id,
      billing_date: subscriber.billing_date,
      discount: subscriber.discount
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingSubscriber(null);
    setFormData({
      name: "",
      whatsapp_number: "",
      email: "",
      address: "",
      plan_id: "",
      billing_date: 1,
      discount: 0
    });
  };

  const filteredSubscribers = subscribers.filter(sub =>
    sub.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sub.whatsapp_number.includes(searchTerm)
  );

  const getStatusBadge = (status) => {
    const badges = {
      active: "badge-active",
      inactive: "badge-suspended"
    };
    return <span className={badges[status] || "badge-pending"}>{status}</span>;
  };

  if (loading) {
    return (
      <OperatorLayout title="Subscribers">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const isReadOnly = dashboardStats?.is_read_only;

  return (
    <OperatorLayout title="Subscribers" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search subscribers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
              data-testid="search-subscribers"
            />
          </div>
          <Button 
            onClick={() => { resetForm(); setShowDialog(true); }}
            disabled={isReadOnly}
            data-testid="add-subscriber-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Subscriber
          </Button>
        </div>

        {/* Subscribers Table */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>WhatsApp</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Billing Date</TableHead>
                  <TableHead>Discount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSubscribers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                      <Users className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No subscribers found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredSubscribers.map((subscriber) => (
                    <TableRow key={subscriber.id} data-testid={`subscriber-row-${subscriber.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <span className="text-blue-600 font-medium text-sm">
                              {subscriber.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <span className="font-medium block">{subscriber.name}</span>
                            {subscriber.email && (
                              <span className="text-xs text-slate-500">{subscriber.email}</span>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Phone className="w-3 h-3 text-emerald-600" />
                          <span className="font-mono text-sm">{subscriber.whatsapp_number}</span>
                        </div>
                      </TableCell>
                      <TableCell>{subscriber.plan_name || "-"}</TableCell>
                      <TableCell>Day {subscriber.billing_date}</TableCell>
                      <TableCell>₹{subscriber.discount}</TableCell>
                      <TableCell>{getStatusBadge(subscriber.status)}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" disabled={isReadOnly}>
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => openEditDialog(subscriber)}>
                              <Pencil className="w-4 h-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => handleDelete(subscriber.id)}
                              className="text-red-600"
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

        {/* Create/Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingSubscriber ? "Edit Subscriber" : "Add New Subscriber"}</DialogTitle>
              <DialogDescription>
                {editingSubscriber ? "Update subscriber details" : "Add a new subscriber to your list"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 space-y-2">
                  <Label>Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Subscriber name"
                    required
                    data-testid="subscriber-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>WhatsApp Number *</Label>
                  <Input
                    value={formData.whatsapp_number}
                    onChange={(e) => setFormData(prev => ({ ...prev, whatsapp_number: e.target.value }))}
                    placeholder="9876543210"
                    required
                    data-testid="subscriber-phone-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="email@example.com"
                  />
                </div>

                <div className="col-span-2 space-y-2">
                  <Label>Address</Label>
                  <Input
                    value={formData.address}
                    onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                    placeholder="Full address"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Plan *</Label>
                  <Select 
                    value={formData.plan_id} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, plan_id: value }))}
                  >
                    <SelectTrigger data-testid="subscriber-plan-select">
                      <SelectValue placeholder="Select plan" />
                    </SelectTrigger>
                    <SelectContent>
                      {plans.map((plan) => (
                        <SelectItem key={plan.id} value={plan.id}>
                          {plan.name} - ₹{plan.price}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Billing Date (Day of Month) *</Label>
                  <Select 
                    value={formData.billing_date.toString()} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, billing_date: parseInt(value) }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select day" />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 28 }, (_, i) => i + 1).map((day) => (
                        <SelectItem key={day} value={day.toString()}>
                          Day {day}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Discount (₹)</Label>
                  <Input
                    type="number"
                    value={formData.discount}
                    onChange={(e) => setFormData(prev => ({ ...prev, discount: parseFloat(e.target.value) || 0 }))}
                    min="0"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-subscriber-btn">
                  {editingSubscriber ? "Update" : "Add Subscriber"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorSubscribers;
