import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
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
} from "../../components/ui/dialog";
import { toast } from "sonner";
import { Settings, CreditCard, Package, Trash2, Plus } from "lucide-react";

const AdminSettings = () => {
  const { authAxios } = useAuth();
  const [settings, setSettings] = useState(null);
  const [gateways, setGateways] = useState([]);
  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGatewayDialog, setShowGatewayDialog] = useState(false);
  const [showAddonDialog, setShowAddonDialog] = useState(false);
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

  const handleAddAddon = async (e) => {
    e.preventDefault();
    try {
      await authAxios.post("/admin/addons", addonForm);
      toast.success("Add-on created");
      setShowAddonDialog(false);
      setAddonForm({ name: "", code: "", price: 0, description: "" });
      fetchAddons();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create add-on");
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

          <TabsContent value="gateways" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5" />
                  Payment Gateway Configurations
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
                      <TableHead>Scope</TableHead>
                      <TableHead>Active</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {gateways.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                          No payment gateways configured
                        </TableCell>
                      </TableRow>
                    ) : gateways.map((gw) => (
                      <TableRow key={gw.id} data-testid={`gateway-row-${gw.id}`}>
                        <TableCell className="font-medium capitalize">{gw.gateway_type}</TableCell>
                        <TableCell className="font-mono text-sm">{gw.api_key}</TableCell>
                        <TableCell>{gw.is_platform_gateway ? "Platform Default" : `Operator: ${gw.operator_id?.slice(0, 8)}`}</TableCell>
                        <TableCell>{gw.is_active ? <span className="badge-active">Active</span> : <span className="badge-suspended">Inactive</span>}</TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteGateway(gw.id)}>
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

          <TabsContent value="addons" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  SaaS Add-ons
                </CardTitle>
                <Button size="sm" onClick={() => setShowAddonDialog(true)} data-testid="add-addon-btn">
                  <Plus className="w-4 h-4 mr-1" /> Create Add-on
                </Button>
              </CardHeader>
              <CardContent>
                {addons.length === 0 ? (
                  <p className="text-center py-8 text-slate-500">No add-ons created yet</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {addons.map((addon) => (
                      <Card key={addon.id} data-testid={`addon-card-${addon.id}`}>
                        <CardContent className="pt-6">
                          <h3 className="font-semibold text-lg">{addon.name}</h3>
                          <p className="text-sm text-slate-500 mt-1">{addon.description || "No description"}</p>
                          <div className="mt-3 flex items-center justify-between">
                            <span className="text-2xl font-bold">₹{addon.price}</span>
                            <span className="text-xs font-mono bg-slate-100 px-2 py-1 rounded">{addon.code}</span>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
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

        {/* Add Addon Dialog */}
        <Dialog open={showAddonDialog} onOpenChange={setShowAddonDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Add-on</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleAddAddon} className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={addonForm.name} onChange={(e) => setAddonForm(f => ({ ...f, name: e.target.value }))} required data-testid="addon-name" />
              </div>
              <div className="space-y-2">
                <Label>Code</Label>
                <Select value={addonForm.code} onValueChange={(v) => setAddonForm(f => ({ ...f, code: v }))}>
                  <SelectTrigger data-testid="addon-code"><SelectValue placeholder="Select code" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="notifications">notifications</SelectItem>
                    <SelectItem value="custom_gateway">custom_gateway</SelectItem>
                    <SelectItem value="subscriber_upgrade_100">subscriber_upgrade_100</SelectItem>
                    <SelectItem value="audit_logs">audit_logs</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Price (₹)</Label>
                <Input type="number" value={addonForm.price} onChange={(e) => setAddonForm(f => ({ ...f, price: parseFloat(e.target.value) }))} required data-testid="addon-price" />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input value={addonForm.description} onChange={(e) => setAddonForm(f => ({ ...f, description: e.target.value }))} data-testid="addon-description" />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" type="button" onClick={() => setShowAddonDialog(false)}>Cancel</Button>
                <Button type="submit" data-testid="save-addon-btn">Create Add-on</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
};

export default AdminSettings;
