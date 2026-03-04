import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
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
import { toast } from "sonner";
import { Settings, CreditCard, Package, Trash2, Plus, Pencil, Info } from "lucide-react";

const AdminSettings = () => {
  const { authAxios } = useAuth();
  const [settings, setSettings] = useState(null);
  const [gateways, setGateways] = useState([]);
  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGatewayDialog, setShowGatewayDialog] = useState(false);
  const [showAddonDialog, setShowAddonDialog] = useState(false);
  const [editingAddon, setEditingAddon] = useState(null);
  const [deleteAddonId, setDeleteAddonId] = useState(null);
  const [gatewayForm, setGatewayForm] = useState({
    gateway_type: "razorpay", api_key: "", api_secret: "", webhook_secret: "", is_active: true
  });
  const [addonForm, setAddonForm] = useState({
    name: "", code: "", price: 0, description: ""
  });

  useEffect(() => {
    Promise.all([fetchSettings(), fetchGateways(), fetchAddons()])
      .finally(() => setLoading(false));
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await authAxios.get("/admin/settings");
      setSettings(res.data);
    } catch { /* ignore */ }
  };

  const fetchGateways = async () => {
    try {
      const res = await authAxios.get("/admin/payment-gateways");
      setGateways(res.data);
    } catch { /* ignore */ }
  };

  const fetchAddons = async () => {
    try {
      const res = await authAxios.get("/admin/addons");
      setAddons(res.data);
    } catch { /* ignore */ }
  };

  const handleUpdateSettings = async () => {
    try {
      await authAxios.put("/admin/settings", settings);
      toast.success("Settings updated");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update settings");
    }
  };

  const handleAddGateway = async (e) => {
    e.preventDefault();
    try {
      await authAxios.post("/admin/payment-gateways", gatewayForm);
      toast.success("Gateway configured");
      setShowGatewayDialog(false);
      setGatewayForm({ gateway_type: "razorpay", api_key: "", api_secret: "", webhook_secret: "", is_active: true });
      fetchGateways();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to add gateway");
    }
  };

  const handleDeleteGateway = async (id) => {
    try {
      await authAxios.delete(`/admin/payment-gateways/${id}`);
      toast.success("Gateway removed");
      fetchGateways();
    } catch (error) {
      toast.error("Failed to remove gateway");
    }
  };

  const openAddonDialog = (addon = null) => {
    if (addon) {
      setEditingAddon(addon);
      setAddonForm({ name: addon.name, code: addon.code, price: addon.price, description: addon.description || "" });
    } else {
      setEditingAddon(null);
      setAddonForm({ name: "", code: "", price: 0, description: "" });
    }
    setShowAddonDialog(true);
  };

  const handleSaveAddon = async (e) => {
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
      setEditingAddon(null);
      setAddonForm({ name: "", code: "", price: 0, description: "" });
      fetchAddons();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save add-on");
    }
  };

  const handleDeleteAddon = async () => {
    if (!deleteAddonId) return;
    try {
      await authAxios.delete(`/admin/addons/${deleteAddonId}`);
      toast.success("Add-on deleted");
      setDeleteAddonId(null);
      fetchAddons();
    } catch (error) {
      toast.error("Failed to delete add-on");
    }
  };

  if (loading) {
    return (
      <AdminLayout title="Settings">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Platform Settings">
      <div className="space-y-6 animate-fade-in">
        <Tabs defaultValue="general">
          <TabsList data-testid="settings-tabs">
            <TabsTrigger value="general" data-testid="tab-general">General</TabsTrigger>
            <TabsTrigger value="gateways" data-testid="tab-gateways">Payment Gateways</TabsTrigger>
            <TabsTrigger value="addons" data-testid="tab-addons">Add-ons</TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  Platform Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Active Payment Gateway</Label>
                    <Select
                      value={settings?.active_payment_gateway || "razorpay"}
                      onValueChange={(v) => setSettings(s => ({ ...s, active_payment_gateway: v }))}
                    >
                      <SelectTrigger data-testid="gateway-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="razorpay">Razorpay</SelectItem>
                        <SelectItem value="cashfree">Cashfree</SelectItem>
                        <SelectItem value="phonepe">PhonePe</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Auto Invoice Days Before</Label>
                    <Input
                      type="number"
                      value={settings?.auto_invoice_days_before || 3}
                      onChange={(e) => setSettings(s => ({ ...s, auto_invoice_days_before: parseInt(e.target.value) }))}
                      data-testid="auto-invoice-days"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>GST Rate (%)</Label>
                    <Input
                      type="number"
                      value={settings?.gst_rate || 18}
                      onChange={(e) => setSettings(s => ({ ...s, gst_rate: parseFloat(e.target.value) }))}
                      data-testid="gst-rate"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Late Fee Percentage (%)</Label>
                    <Input
                      type="number"
                      value={settings?.late_fee_percentage || 0}
                      onChange={(e) => setSettings(s => ({ ...s, late_fee_percentage: parseFloat(e.target.value) }))}
                      data-testid="late-fee"
                    />
                  </div>
                </div>
                <Button onClick={handleUpdateSettings} data-testid="save-settings-btn">
                  Save Settings
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Payment Gateways Tab */}
          <TabsContent value="gateways" className="mt-6 space-y-4">
            <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
              <Info className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
              <p className="text-sm text-blue-800">
                These payment gateway credentials are used for <strong>Operator-to-Admin SaaS subscription payments</strong>. 
                When operators pay for their subscription or add-ons, the configured gateway will process those payments.
              </p>
            </div>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5" />
                  SaaS Payment Gateway Config
                </CardTitle>
                <Button size="sm" onClick={() => setShowGatewayDialog(true)} data-testid="add-gateway-btn">
                  <Plus className="w-4 h-4 mr-1" /> Add Gateway
                </Button>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>API Key</TableHead>
                      <TableHead>Purpose</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {gateways.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                          No payment gateways configured. Add one to accept SaaS subscription payments.
                        </TableCell>
                      </TableRow>
                    ) : gateways.map((gw) => (
                      <TableRow key={gw.id} data-testid={`gateway-row-${gw.id}`}>
                        <TableCell className="font-medium capitalize">{gw.gateway_type}</TableCell>
                        <TableCell className="font-mono text-sm">{gw.api_key?.slice(0, 16)}...</TableCell>
                        <TableCell>
                          <span className="text-xs bg-slate-100 px-2 py-1 rounded font-medium">
                            {gw.is_platform_gateway ? "SaaS Subscription Payments" : `Operator: ${gw.operator_id?.slice(0, 8)}`}
                          </span>
                        </TableCell>
                        <TableCell>
                          {gw.is_active 
                            ? <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-1 rounded font-medium">Active</span> 
                            : <span className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded font-medium">Inactive</span>}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteGateway(gw.id)} data-testid={`delete-gw-${gw.id}`}>
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Add-ons Tab */}
          <TabsContent value="addons" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  SaaS Add-ons
                </CardTitle>
                <Button size="sm" onClick={() => openAddonDialog()} data-testid="add-addon-btn">
                  <Plus className="w-4 h-4 mr-1" /> Create Add-on
                </Button>
              </CardHeader>
              <CardContent>
                {addons.length === 0 ? (
                  <p className="text-center py-8 text-slate-500">No add-ons created yet</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Code</TableHead>
                        <TableHead>Price</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="w-[100px] text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {addons.map((addon) => (
                        <TableRow key={addon.id} data-testid={`addon-row-${addon.id}`}>
                          <TableCell className="font-medium">{addon.name}</TableCell>
                          <TableCell>
                            <span className="text-xs font-mono bg-slate-100 px-2 py-1 rounded">{addon.code}</span>
                          </TableCell>
                          <TableCell className="font-semibold">₹{addon.price}</TableCell>
                          <TableCell className="text-sm text-slate-500 max-w-[200px] truncate">{addon.description || "-"}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button variant="ghost" size="icon" onClick={() => openAddonDialog(addon)} data-testid={`edit-addon-${addon.id}`}>
                                <Pencil className="w-4 h-4 text-slate-600" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={() => setDeleteAddonId(addon.id)} data-testid={`delete-addon-${addon.id}`}>
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Add Gateway Dialog */}
        <Dialog open={showGatewayDialog} onOpenChange={setShowGatewayDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Payment Gateway</DialogTitle>
              <DialogDescription>
                Configure a payment gateway for SaaS subscription collections from operators.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddGateway} className="space-y-4">
              <div className="space-y-2">
                <Label>Gateway Type</Label>
                <Select value={gatewayForm.gateway_type} onValueChange={(v) => setGatewayForm(f => ({ ...f, gateway_type: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="razorpay">Razorpay</SelectItem>
                    <SelectItem value="cashfree">Cashfree</SelectItem>
                    <SelectItem value="phonepe">PhonePe</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>API Key</Label>
                <Input value={gatewayForm.api_key} onChange={(e) => setGatewayForm(f => ({ ...f, api_key: e.target.value }))} required data-testid="gw-api-key" />
              </div>
              <div className="space-y-2">
                <Label>API Secret</Label>
                <Input type="password" value={gatewayForm.api_secret} onChange={(e) => setGatewayForm(f => ({ ...f, api_secret: e.target.value }))} required data-testid="gw-api-secret" />
              </div>
              <div className="space-y-2">
                <Label>Webhook Secret (optional)</Label>
                <Input value={gatewayForm.webhook_secret} onChange={(e) => setGatewayForm(f => ({ ...f, webhook_secret: e.target.value }))} data-testid="gw-webhook-secret" />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" type="button" onClick={() => setShowGatewayDialog(false)}>Cancel</Button>
                <Button type="submit" data-testid="save-gateway-btn">Save Gateway</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Add/Edit Addon Dialog */}
        <Dialog open={showAddonDialog} onOpenChange={setShowAddonDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingAddon ? "Edit Add-on" : "Create Add-on"}</DialogTitle>
              <DialogDescription>
                {editingAddon ? "Update the add-on details." : "Create a new purchasable add-on for operators."}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSaveAddon} className="space-y-4">
              <div className="space-y-2">
                <Label>Name *</Label>
                <Input value={addonForm.name} onChange={(e) => setAddonForm(f => ({ ...f, name: e.target.value }))} required data-testid="addon-name" placeholder="e.g., WhatsApp Notifications" />
              </div>
              <div className="space-y-2">
                <Label>Code *</Label>
                {editingAddon ? (
                  <Input value={addonForm.code} disabled className="bg-slate-50" />
                ) : (
                  <Input value={addonForm.code} onChange={(e) => setAddonForm(f => ({ ...f, code: e.target.value.toLowerCase().replace(/\s+/g, '_') }))} required data-testid="addon-code" placeholder="e.g., notifications" />
                )}
                <p className="text-xs text-slate-500">Unique identifier. Use lowercase with underscores.</p>
              </div>
              <div className="space-y-2">
                <Label>Price (₹/month) *</Label>
                <Input type="number" min="0" value={addonForm.price} onChange={(e) => setAddonForm(f => ({ ...f, price: parseFloat(e.target.value) || 0 }))} required data-testid="addon-price" />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea value={addonForm.description} onChange={(e) => setAddonForm(f => ({ ...f, description: e.target.value }))} data-testid="addon-description" placeholder="Describe what this add-on provides" rows={3} />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" type="button" onClick={() => setShowAddonDialog(false)}>Cancel</Button>
                <Button type="submit" data-testid="save-addon-btn">
                  {editingAddon ? "Update Add-on" : "Create Add-on"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Addon Confirmation */}
        <AlertDialog open={!!deleteAddonId} onOpenChange={(open) => !open && setDeleteAddonId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Add-on</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete this add-on? Operators who have purchased it will lose access.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDeleteAddon} className="bg-red-600 hover:bg-red-700" data-testid="confirm-delete-addon">
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AdminLayout>
  );
};

export default AdminSettings;
