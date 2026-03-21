import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
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
import { toast } from "sonner";
import {
  Settings, CreditCard, Trash2, Plus, Info,
  Database, RefreshCw, RotateCcw, HardDrive, Clock, AlertTriangle, Shield, MessageCircle, Eye, EyeOff, Download, Lock, CheckCircle2, ExternalLink
} from "lucide-react";

const AdminSettings = () => {
  const { authAxios } = useAuth();
  const navigate = useNavigate();
  const [settings, setSettings] = useState(null);
  const [gateways, setGateways] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGatewayDialog, setShowGatewayDialog] = useState(false);
  const [gatewayForm, setGatewayForm] = useState({
    gateway_type: "razorpay", api_key: "", api_secret: "", webhook_secret: "", is_active: true
  });

  // Backup state
  const [backups, setBackups] = useState([]);
  const [creating, setCreating] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [restorePassword, setRestorePassword] = useState("");
  const [restoring, setRestoring] = useState(false);

  // Change-password state
  const [pwForm, setPwForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [pwLoading, setPwLoading] = useState(false);
  const [showPw, setShowPw] = useState({ current: false, new: false, confirm: false });

  // WhatsApp config state
  const [waConfig, setWaConfig] = useState({
    phone_number_id: "",
    access_token: "",
    business_account_id: "",
    access_token_preview: "",
    is_configured: false,
  });
  const [waLoading, setWaLoading] = useState(false);
  const [showToken, setShowToken] = useState(false);

  // WhatsApp template settings state
  const [templateSettings, setTemplateSettings] = useState({
    invoice_template: "",
    reminder_template: "",
    payment_confirmation_template: "",
    announcement_template: "",
  });
  const [templateSettingsLoading, setTemplateSettingsLoading] = useState(false);
  const [availableTemplates, setAvailableTemplates] = useState([]);

  // WhatsApp test message state
  const [testPhone, setTestPhone] = useState("");
  const [testSending, setTestSending] = useState(false);

  useEffect(() => {
    Promise.all([fetchSettings(), fetchGateways(), fetchBackups(), fetchWaConfig(), fetchTemplateSettings(), fetchTemplates()])
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

  const fetchBackups = async () => {
    try {
      const res = await authAxios.get("/admin/backup/list");
      setBackups(res.data);
    } catch { /* ignore */ }
  };

  const fetchWaConfig = async () => {
    try {
      const res = await authAxios.get("/admin/whatsapp-config");
      setWaConfig(prev => ({
        ...prev,
        phone_number_id: res.data.phone_number_id || "",
        business_account_id: res.data.business_account_id || "",
        access_token_preview: res.data.access_token_preview || "",
        is_configured: res.data.is_configured || false,
      }));
    } catch { /* ignore */ }
  };

  const fetchTemplateSettings = async () => {
    try {
      const res = await authAxios.get("/admin/whatsapp-template-settings");
      setTemplateSettings({
        invoice_template: res.data.invoice_template || "",
        reminder_template: res.data.reminder_template || "",
        payment_confirmation_template: res.data.payment_confirmation_template || "",
        announcement_template: res.data.announcement_template || "",
      });
    } catch { /* ignore */ }
  };

  const fetchTemplates = async () => {
    try {
      const res = await authAxios.get("/admin/whatsapp-templates");
      setAvailableTemplates(res.data.filter(t => t.is_active));
    } catch { /* ignore */ }
  };

  const handleUpdateWhatsApp = async (e) => {
    e.preventDefault();
    if (!waConfig.phone_number_id || !waConfig.access_token) {
      toast.error("Phone Number ID and Access Token are required");
      return;
    }
    setWaLoading(true);
    try {
      await authAxios.put("/admin/whatsapp-config", waConfig);
      toast.success("WhatsApp configuration updated");
      setWaConfig(prev => ({ ...prev, access_token: "" })); // clear for security
      fetchWaConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update WhatsApp config");
    } finally {
      setWaLoading(false);
    }
  };

  const handleSaveTemplateSettings = async () => {
    setTemplateSettingsLoading(true);
    try {
      await authAxios.put("/admin/whatsapp-template-settings", templateSettings);
      toast.success("Template settings saved successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save template settings");
    } finally {
      setTemplateSettingsLoading(false);
    }
  };

  const handleSendTestMessage = async () => {
    if (!testPhone.trim()) {
      toast.error("Please enter a phone number");
      return;
    }
    setTestSending(true);
    try {
      const res = await authAxios.post("/admin/whatsapp-test", { phone_number: testPhone.trim() });
      toast.success(res.data.message || "Test message sent!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send test message");
    } finally {
      setTestSending(false);
    }
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
    if (!gatewayForm.api_key?.trim() || !gatewayForm.api_secret?.trim()) {
      toast.error("API Key and API Secret are required"); return;
    }
    if (gatewayForm.api_key.trim().length < 10) {
      toast.error("Please enter a valid API Key"); return;
    }
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
    } catch {
      toast.error("Failed to remove gateway");
    }
  };

  // Backup handlers
  const handleCreateBackup = async () => {
    setCreating(true);
    try {
      const res = await authAxios.post("/admin/backup/create");
      toast.success(`Backup created: ${res.data.backup.filename}`);
      fetchBackups();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Backup failed");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteBackup = async (id) => {
    if (!confirm("Delete this backup permanently?")) return;
    try {
      await authAxios.delete(`/admin/backup/${id}`);
      toast.success("Backup deleted");
      fetchBackups();
    } catch {
      toast.error("Failed to delete backup");
    }
  };

  const handleRestore = async () => {
    if (!restoreTarget || !restorePassword) return;
    setRestoring(true);
    try {
      const res = await authAxios.post(`/admin/backup/restore/${restoreTarget.id}`, { password: restorePassword });
      toast.success(`Restored — ${res.data.records_restored} records across ${res.data.collections_restored.length} collections`);
      setRestoreTarget(null);
      setRestorePassword("");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Restore failed");
    } finally {
      setRestoring(false);
    }
  };

  const formatSize = (kb) => kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
  const formatDate = (iso) => new Date(iso).toLocaleString();

  const handleDownload = async (backup) => {
    try {
      const res = await authAxios.get(`/admin/backup/download/${backup.id}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/gzip" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", backup.filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Download failed");
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (pwForm.new_password !== pwForm.confirm_password) {
      toast.error("New passwords do not match");
      return;
    }
    if (pwForm.new_password.length < 6) {
      toast.error("New password must be at least 6 characters");
      return;
    }
    setPwLoading(true);
    try {
      await authAxios.put("/auth/change-password", {
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      });
      toast.success("Password changed successfully");
      setPwForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to change password");
    } finally {
      setPwLoading(false);
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
          <TabsList>
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="gateways">Payment Gateways</TabsTrigger>
            <TabsTrigger value="whatsapp" data-testid="tab-whatsapp">WhatsApp</TabsTrigger>
            <TabsTrigger value="backup">Backup & Restore</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
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
                      <SelectTrigger><SelectValue /></SelectTrigger>
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
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>GST Rate (%)</Label>
                    <Input
                      type="number"
                      value={settings?.gst_rate || 18}
                      onChange={(e) => setSettings(s => ({ ...s, gst_rate: parseFloat(e.target.value) }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Late Fee Percentage (%)</Label>
                    <Input
                      type="number"
                      value={settings?.late_fee_percentage || 0}
                      onChange={(e) => setSettings(s => ({ ...s, late_fee_percentage: parseFloat(e.target.value) }))}
                    />
                  </div>
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-amber-900">Maintenance Mode</p>
                      <p className="text-sm text-amber-700">
                        When enabled, automation stops and operator/staff users are forced into read-only mode.
                      </p>
                    </div>
                    <Switch
                      checked={!!settings?.maintenance_mode}
                      onCheckedChange={(checked) => setSettings(s => ({ ...s, maintenance_mode: checked }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Maintenance Message</Label>
                    <Textarea
                      value={settings?.maintenance_message || ""}
                      onChange={(e) => setSettings(s => ({ ...s, maintenance_message: e.target.value }))}
                      placeholder="The app is under maintenance. Updates and automation are temporarily paused."
                      rows={3}
                    />
                  </div>
                </div>
                <Button onClick={handleUpdateSettings}>Save Settings</Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Payment Gateways Tab */}
          <TabsContent value="gateways" className="mt-6 space-y-4">
            <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
              <Info className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
              <p className="text-sm text-blue-800">
                These credentials process <strong>Operator SaaS subscription & add-on payments</strong>.
              </p>
            </div>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5" />
                  SaaS Payment Gateway
                </CardTitle>
                <Button size="sm" onClick={() => setShowGatewayDialog(true)}>
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
                          No payment gateways configured.
                        </TableCell>
                      </TableRow>
                    ) : gateways.map((gw) => (
                      <TableRow key={gw.id}>
                        <TableCell className="font-medium capitalize">{gw.gateway_type}</TableCell>
                        <TableCell className="font-mono text-sm text-slate-700">
                          {gw.api_key
                            ? <span className="bg-slate-100 px-2 py-0.5 rounded text-xs">{gw.api_key}</span>
                            : <span className="text-slate-400">••••••••</span>}
                        </TableCell>
                        <TableCell>
                          <span className="text-xs bg-slate-100 px-2 py-1 rounded">
                            {gw.is_platform_gateway ? "SaaS Payments" : `Operator: ${gw.operator_id?.slice(0, 8)}`}
                          </span>
                        </TableCell>
                        <TableCell>
                          {gw.is_active
                            ? <span className="badge-active">Active</span>
                            : <span className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded">Inactive</span>}
                        </TableCell>
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

          {/* WhatsApp Tab */}
          <TabsContent value="whatsapp" className="mt-6 space-y-6">
            {/* API Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageCircle className="w-5 h-5 text-green-600" />
                  Platform WhatsApp API Configuration
                </CardTitle>
                <p className="text-sm text-slate-500">
                  Configure the global WhatsApp Business API credentials used for all operators.
                </p>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdateWhatsApp} className="space-y-4 max-w-lg">
                  {waConfig.is_configured && (
                    <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-emerald-800">WhatsApp is configured</p>
                        {waConfig.access_token_preview && (
                          <p className="text-xs text-emerald-600 font-mono mt-0.5">
                            Token: {waConfig.access_token_preview}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label>Phone Number ID</Label>
                    <Input
                      value={waConfig.phone_number_id}
                      onChange={(e) => setWaConfig(prev => ({ ...prev, phone_number_id: e.target.value }))}
                      placeholder="e.g., 123456789012345"
                      data-testid="wa-phone-number-id"
                    />
                    <p className="text-xs text-slate-400">Found in Meta Business Suite → WhatsApp → API Setup</p>
                  </div>

                  <div className="space-y-2">
                    <Label>Business Account ID</Label>
                    <Input
                      value={waConfig.business_account_id}
                      onChange={(e) => setWaConfig(prev => ({ ...prev, business_account_id: e.target.value }))}
                      placeholder="e.g., 987654321098765"
                      data-testid="wa-business-account-id"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Access Token</Label>
                    <div className="relative">
                      <Input
                        type={showToken ? "text" : "password"}
                        value={waConfig.access_token}
                        onChange={(e) => setWaConfig(prev => ({ ...prev, access_token: e.target.value }))}
                        placeholder="Enter new access token to update"
                        className="pr-10"
                        data-testid="wa-access-token"
                      />
                      <button
                        type="button"
                        onClick={() => setShowToken(v => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <p className="text-xs text-slate-400">Leave blank to keep the existing token unchanged.</p>
                  </div>

                  <div className="pt-2 flex items-center gap-3">
                    <Button type="submit" disabled={waLoading} data-testid="save-wa-config-btn">
                      {waLoading ? "Saving..." : "Save WhatsApp Config"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* Template Assignment */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-blue-600" />
                  Template Assignment
                </CardTitle>
                <p className="text-sm text-slate-500">
                  Assign which WhatsApp template to use for each type of notification. Templates must be created in the <span className="font-medium">WA Templates</span> section first.
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-5 max-w-lg">
                  {[
                    { key: "invoice_template", label: "Invoice Sending", desc: "Template used when sending new invoices to subscribers" },
                    { key: "reminder_template", label: "Payment Reminders", desc: "Template used for overdue payment reminders" },
                    { key: "payment_confirmation_template", label: "Payment Confirmation", desc: "Template used when a payment is confirmed" },
                    { key: "announcement_template", label: "Announcements", desc: "Template used for sending announcements" },
                  ].map(({ key, label, desc }) => (
                    <div key={key} className="space-y-1.5">
                      <Label className="text-sm font-medium">{label}</Label>
                      <Select
                        value={templateSettings[key] || "_none_"}
                        onValueChange={(v) => setTemplateSettings(prev => ({ ...prev, [key]: v === "_none_" ? "" : v }))}
                      >
                        <SelectTrigger data-testid={`tpl-${key}`}>
                          <SelectValue placeholder="Select a template..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="_none_">— Not Assigned —</SelectItem>
                          {availableTemplates.map(t => (
                            <SelectItem key={t.id} value={t.template_name}>
                              {t.display_name} ({t.template_name})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-slate-400">{desc}</p>
                    </div>
                  ))}

                  <div className="pt-3 flex items-center gap-3">
                    <Button onClick={handleSaveTemplateSettings} disabled={templateSettingsLoading} data-testid="save-template-settings-btn">
                      {templateSettingsLoading ? "Saving..." : "Save Template Settings"}
                    </Button>
                    <Button variant="outline" onClick={() => navigate("/admin/whatsapp-templates")} data-testid="manage-templates-btn">
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Manage Templates
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Test Message */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageCircle className="w-5 h-5 text-amber-600" />
                  Send Test Message
                </CardTitle>
                <p className="text-sm text-slate-500">
                  Send a test WhatsApp message using the pre-approved <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">hello_world</code> template to verify your configuration.
                </p>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-3 max-w-lg">
                  <div className="flex-1 space-y-1.5">
                    <Label>Phone Number</Label>
                    <Input
                      value={testPhone}
                      onChange={(e) => setTestPhone(e.target.value)}
                      placeholder="e.g., 919876543210"
                      data-testid="wa-test-phone"
                    />
                    <p className="text-xs text-slate-400">Enter number with country code (e.g., 91 for India)</p>
                  </div>
                  <Button
                    onClick={handleSendTestMessage}
                    disabled={testSending || !waConfig.is_configured}
                    variant="outline"
                    className="border-green-300 text-green-700 hover:bg-green-50"
                    data-testid="send-test-btn"
                  >
                    {testSending ? "Sending..." : "Send Test"}
                  </Button>
                </div>
                {!waConfig.is_configured && (
                  <p className="text-xs text-amber-600 mt-2">
                    <Info className="w-3 h-3 inline mr-1" />
                    Save your WhatsApp API config above before sending test messages.
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Backup & Restore Tab */}
          <TabsContent value="backup" className="mt-6 space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card className="bg-blue-50 border-blue-100">
                <CardContent className="p-4 flex items-center gap-3">
                  <Database className="w-8 h-8 text-blue-600" />
                  <div>
                    <p className="text-2xl font-bold text-blue-700">{backups.length}</p>
                    <p className="text-sm text-blue-600">Total Backups</p>
                  </div>
                </CardContent>
              </Card>
              <Card className="bg-emerald-50 border-emerald-100">
                <CardContent className="p-4 flex items-center gap-3">
                  <Clock className="w-8 h-8 text-emerald-600" />
                  <div>
                    <p className="text-sm font-bold text-emerald-700">{backups.filter(b => b.type === "auto").length} Auto</p>
                    <p className="text-xs text-emerald-600">Daily at 02:00 UTC</p>
                  </div>
                </CardContent>
              </Card>
              <Card className="bg-amber-50 border-amber-100">
                <CardContent className="p-4 flex items-center gap-3">
                  <HardDrive className="w-8 h-8 text-amber-600" />
                  <div>
                    <p className="text-sm font-bold text-amber-700">
                      {formatSize(backups.reduce((s, b) => s + (b.size_kb || 0), 0))}
                    </p>
                    <p className="text-xs text-amber-600">Total Storage</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Database className="w-5 h-5" /> Available Backups
                </CardTitle>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={fetchBackups}>
                    <RefreshCw className="w-4 h-4 mr-1" /> Refresh
                  </Button>
                  <Button size="sm" onClick={handleCreateBackup} disabled={creating}>
                    {creating ? <><RefreshCw className="w-4 h-4 mr-1 animate-spin" /> Creating...</> : <><Plus className="w-4 h-4 mr-1" /> Create Backup</>}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Created At</TableHead>
                      <TableHead>Filename</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Records</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backups.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-10 text-slate-500">
                          <Database className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                          No backups yet. Click "Create Backup" to start.
                        </TableCell>
                      </TableRow>
                    ) : backups.map((b) => (
                      <TableRow key={b.id}>
                        <TableCell className="text-sm">{formatDate(b.created_at)}</TableCell>
                        <TableCell className="font-mono text-xs text-slate-600">{b.filename}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            b.type === "auto" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-700"
                          }`}>{b.type === "auto" ? "Auto" : "Manual"}</span>
                        </TableCell>
                        <TableCell className="text-sm">{formatSize(b.size_kb || 0)}</TableCell>
                        <TableCell className="text-sm">{(b.total_records || 0).toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button variant="outline" size="sm"
                              className="text-blue-600 hover:bg-blue-50 border-blue-200"
                              onClick={() => handleDownload(b)}
                            >
                              <Download className="w-3.5 h-3.5 mr-1" /> Download
                            </Button>
                            <Button variant="outline" size="sm"
                              className="text-amber-600 hover:bg-amber-50 border-amber-200"
                              onClick={() => { setRestoreTarget(b); setRestorePassword(""); }}
                            >
                              <RotateCcw className="w-3.5 h-3.5 mr-1" /> Restore
                            </Button>
                            <Button variant="outline" size="sm"
                              className="text-red-600 hover:bg-red-50"
                              onClick={() => handleDeleteBackup(b.id)}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security" className="mt-6">
            <Card className="max-w-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lock className="w-5 h-5" /> Change Password
                </CardTitle>
                <p className="text-sm text-slate-500">Update your admin account password.</p>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleChangePassword} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="current_password">Current Password</Label>
                    <div className="relative">
                      <Input
                        id="current_password"
                        type={showPw.current ? "text" : "password"}
                        value={pwForm.current_password}
                        onChange={(e) => setPwForm(f => ({ ...f, current_password: e.target.value }))}
                        required
                        placeholder="Enter current password"
                      />
                      <button type="button" tabIndex={-1}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        onClick={() => setShowPw(s => ({ ...s, current: !s.current }))}>
                        {showPw.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new_password">New Password</Label>
                    <div className="relative">
                      <Input
                        id="new_password"
                        type={showPw.new ? "text" : "password"}
                        value={pwForm.new_password}
                        onChange={(e) => setPwForm(f => ({ ...f, new_password: e.target.value }))}
                        required
                        placeholder="At least 6 characters"
                      />
                      <button type="button" tabIndex={-1}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        onClick={() => setShowPw(s => ({ ...s, new: !s.new }))}>
                        {showPw.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm_password">Confirm New Password</Label>
                    <div className="relative">
                      <Input
                        id="confirm_password"
                        type={showPw.confirm ? "text" : "password"}
                        value={pwForm.confirm_password}
                        onChange={(e) => setPwForm(f => ({ ...f, confirm_password: e.target.value }))}
                        required
                        placeholder="Repeat new password"
                      />
                      <button type="button" tabIndex={-1}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        onClick={() => setShowPw(s => ({ ...s, confirm: !s.confirm }))}>
                        {showPw.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  {pwForm.new_password && pwForm.confirm_password && (
                    <p className={`text-sm flex items-center gap-1 ${pwForm.new_password === pwForm.confirm_password ? "text-green-600" : "text-red-500"}`}>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {pwForm.new_password === pwForm.confirm_password ? "Passwords match" : "Passwords do not match"}
                    </p>
                  )}
                  <Button type="submit" disabled={pwLoading} className="w-full">
                    {pwLoading ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Changing...</> : <><Shield className="w-4 h-4 mr-2" /> Change Password</>}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Add Gateway Dialog */}
        <Dialog open={showGatewayDialog} onOpenChange={setShowGatewayDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Payment Gateway</DialogTitle>
              <DialogDescription>Configure a payment gateway for SaaS subscription collections.</DialogDescription>
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
                <Input value={gatewayForm.api_key} onChange={(e) => setGatewayForm(f => ({ ...f, api_key: e.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>API Secret</Label>
                <Input type="password" value={gatewayForm.api_secret} onChange={(e) => setGatewayForm(f => ({ ...f, api_secret: e.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>Webhook Secret (optional)</Label>
                <Input value={gatewayForm.webhook_secret} onChange={(e) => setGatewayForm(f => ({ ...f, webhook_secret: e.target.value }))} />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" type="button" onClick={() => setShowGatewayDialog(false)}>Cancel</Button>
                <Button type="submit">Save Gateway</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Restore Password Dialog */}
        <Dialog open={!!restoreTarget} onOpenChange={() => { setRestoreTarget(null); setRestorePassword(""); }}>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-amber-700">
                <AlertTriangle className="w-5 h-5" /> Confirm Restore
              </DialogTitle>
              <DialogDescription>
                This will <strong>replace ALL current data</strong> with the backup from{" "}
                <span className="font-medium">{restoreTarget && formatDate(restoreTarget.created_at)}</span>.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-2">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <p className="text-xs text-amber-700">
                  <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />
                  All current data will be replaced. This cannot be undone.
                </p>
              </div>
              <div className="space-y-2">
                <Label className="flex items-center gap-2"><Shield className="w-4 h-4" /> Confirm Password</Label>
                <Input type="password" placeholder="Enter backup password" value={restorePassword}
                  onChange={(e) => setRestorePassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRestore()}
                />
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setRestoreTarget(null)}>Cancel</Button>
                <Button className="flex-1 bg-amber-600 hover:bg-amber-700" onClick={handleRestore}
                  disabled={restoring || !restorePassword}
                >
                  {restoring ? <><RefreshCw className="w-4 h-4 mr-1 animate-spin" /> Restoring...</> : <><RotateCcw className="w-4 h-4 mr-1" /> Restore Now</>}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
};

export default AdminSettings;
