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

const DEFAULT_SETTINGS = {
  active_payment_gateway: "razorpay",
  auto_invoice_days_before: 3,
  gst_rate: 18,
  late_fee_percentage: 0,
  referral_discount_percent: 10,
  referral_discount_max_amount: 500,
  referral_reward_percent: 5,
  referral_reward_valid_days: 90,
  maintenance_mode: false,
  maintenance_message: "The app is under maintenance. Updates and automation are temporarily paused.",
  session_timeout_hours: 24,
  cron_backup_time: "03:00",
  cron_expiry_time: "00:05",
  cron_invoice_time: "08:00",
  cron_wallet_time: "09:00",
  cron_reminder_time: "10:00",
  cron_daily_report_time: "09:30",
  welcome_modal_enabled: false,
  welcome_modal_title: "Welcome to E-Bill",
  welcome_modal_content: "",
  welcome_modal_show_for: "all",
  welcome_modal_version: 1,
};

const DEFAULT_EMAIL_CONFIG = {
  resend_api_key: "",
  resend_from_email: "",
  resend_api_key_preview: "",
  is_configured: false,
  smtp_host: "",
  smtp_port: 587,
  smtp_username: "",
  smtp_password: "",
  smtp_from_email: "",
  smtp_use_tls: true,
  is_smtp_configured: false,
};

const CRON_FIELDS = [
  { key: "cron_backup_time", label: "Auto Backup Time", help: "Creates the daily system backup." },
  { key: "cron_expiry_time", label: "Expiry Check Time", help: "Checks expired and read-only operators." },
  { key: "cron_invoice_time", label: "Invoice Generation Time", help: "Creates upcoming invoices automatically." },
  { key: "cron_wallet_time", label: "Wallet Check Time", help: "Checks operator balances and applies suspension rules." },
  { key: "cron_reminder_time", label: "Reminder Processing Time", help: "Sends scheduled WhatsApp payment reminders." },
  { key: "cron_daily_report_time", label: "Daily Operator Report Time", help: "Sends daily billing summary WhatsApp to each operator." },
];

const AdminSettings = () => {
  const { authAxios, user, refreshCurrentUser, clearBrowserCache } = useAuth();
  const navigate = useNavigate();
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [gateways, setGateways] = useState([]);
  const [operators, setOperators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGatewayDialog, setShowGatewayDialog] = useState(false);
  const [gatewayForm, setGatewayForm] = useState({
    gateway_type: "razorpay", api_key: "", api_secret: "", webhook_secret: "", is_active: true, for_operator_id: "platform"
  });

  // Backup state
  const [backups, setBackups] = useState([]);
  const [creating, setCreating] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [restorePassword, setRestorePassword] = useState("");
  const [restoring, setRestoring] = useState(false);

  // ── Danger Zone (System Reset) ──
  const [resetOtpSent, setResetOtpSent] = useState(false);
  const [resetOtpInput, setResetOtpInput] = useState("");
  const [resetOtpLoading, setResetOtpLoading] = useState(false);
  const [resetExecuteLoading, setResetExecuteLoading] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetResult, setResetResult] = useState(null);

  // Change-password state
  const [adminProfileForm, setAdminProfileForm] = useState({ name: "" });
  const [profileSaving, setProfileSaving] = useState(false);
  const [pwForm, setPwForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [pwLoading, setPwLoading] = useState(false);
  const [showPw, setShowPw] = useState({ current: false, new: false, confirm: false });
  const [cacheClearing, setCacheClearing] = useState(false);

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
    payment_due_reminder_template: "",
  });
  const [templateSettingsLoading, setTemplateSettingsLoading] = useState(false);
  const [availableTemplates, setAvailableTemplates] = useState([]);

  // WhatsApp test message state
  const [testPhone, setTestPhone] = useState("");
  const [testSending, setTestSending] = useState(false);

  // WhatsApp diagnostics state
  const [diagnostics, setDiagnostics] = useState(null);
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);

  // Global Reminder settings state
  const [reminderSettings, setReminderSettings] = useState({
    enabled: true,
    remind_before_due: [7, 5, 3, 2, 1],
    remind_on_due: true,
    remind_after_due: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    max_reminders_per_invoice: 20,
  });
  const [reminderSaving, setReminderSaving] = useState(false);

  // Email config state
  const [emailConfig, setEmailConfig] = useState(DEFAULT_EMAIL_CONFIG);
  const [emailSaving, setEmailSaving] = useState(false);
  const [showEmailKey, setShowEmailKey] = useState(false);
  const [testEmail, setTestEmail] = useState("");
  const [emailTestSending, setEmailTestSending] = useState({ resend: false, smtp: false });

  // Security settings state
  const [securitySettings, setSecuritySettings] = useState({
    jwt_secret: "",
    backup_password: "",
    jwt_secret_preview: "",
    backup_password_preview: "",
    is_configured: false,
  });
  const [securitySaving, setSecuritySaving] = useState(false);
  const [showSecurityKeys, setShowSecurityKeys] = useState({ jwt: false, backup: false });

  useEffect(() => {
    setAdminProfileForm({ name: user?.name || "" });
    setTestEmail((prev) => prev || user?.email || "");
  }, [user]);

  useEffect(() => {
    Promise.all([
      fetchSettings(), fetchGateways(), fetchOperators(), fetchBackups(),
      fetchWaConfig(), fetchTemplateSettings(), fetchTemplates(),
      fetchReminderSettings(), fetchEmailConfig(), fetchSecuritySettings()
    ]).finally(() => setLoading(false));
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await authAxios.get("/admin/settings");
      setSettings({ ...DEFAULT_SETTINGS, ...res.data });
    } catch { /* ignore */ }
  };

  const fetchReminderSettings = async () => {
    try {
      const res = await authAxios.get("/admin/reminder-settings");
      setReminderSettings({
        enabled: res.data.enabled ?? true,
        remind_before_due: res.data.remind_before_due || [7, 5, 3, 2, 1],
        remind_on_due: res.data.remind_on_due ?? true,
        remind_after_due: res.data.remind_after_due || [1,2,3,4,5,6,7,8,9,10],
        max_reminders_per_invoice: res.data.max_reminders_per_invoice || 20,
      });
    } catch { /* ignore */ }
  };

  const fetchEmailConfig = async () => {
    try {
      const res = await authAxios.get("/admin/email-settings");
      setEmailConfig({ ...DEFAULT_EMAIL_CONFIG, ...res.data });
    } catch { /* ignore */ }
  };

  const fetchSecuritySettings = async () => {
    try {
      const res = await authAxios.get("/admin/security-settings");
      setSecuritySettings(prev => ({ ...prev, ...res.data }));
    } catch { /* ignore */ }
  };

  const handleSaveSecuritySettings = async (e) => {
    e.preventDefault();
    setSecuritySaving(true);
    try {
      const payload = {};
      ["jwt_secret", "backup_password"].forEach(k => {
        if (securitySettings[k]) payload[k] = securitySettings[k];
      });

      if (Object.keys(payload).length === 0) {
        toast.info("No changes to save");
        setSecuritySaving(false);
        return;
      }

      await authAxios.put("/admin/security-settings", payload);
      toast.success("Security settings updated successfully");
      const cleared = {};
      ["jwt_secret", "backup_password"].forEach(k => cleared[k] = "");
      setSecuritySettings(prev => ({ ...prev, ...cleared }));
      await fetchSecuritySettings();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save security settings");
    } finally {
      setSecuritySaving(false);
    }
  };

  const handleSaveEmailConfig = async (e) => {
    e.preventDefault();
    const hasResend = Boolean(emailConfig.resend_api_key || emailConfig.is_configured || emailConfig.resend_api_key_preview);
    const hasSmtp = Boolean(emailConfig.smtp_host?.trim());

    if (!hasResend && !hasSmtp) {
      toast.error("Configure either Resend or SMTP to save email settings");
      return;
    }
    if (emailConfig.resend_api_key && !emailConfig.resend_from_email?.trim()) {
      toast.error("Resend from email is required when using Resend");
      return;
    }
    if (emailConfig.smtp_host?.trim() && !((emailConfig.smtp_from_email || emailConfig.resend_from_email || "").trim())) {
      toast.error("SMTP from email is required when SMTP is configured");
      return;
    }
    setEmailSaving(true);
    try {
      await authAxios.put("/admin/email-settings", {
        resend_api_key: emailConfig.resend_api_key,
        resend_from_email: emailConfig.resend_from_email,
        smtp_host: emailConfig.smtp_host,
        smtp_port: Number(emailConfig.smtp_port) || 587,
        smtp_username: emailConfig.smtp_username,
        smtp_password: emailConfig.smtp_password,
        smtp_from_email: emailConfig.smtp_from_email,
        smtp_use_tls: emailConfig.smtp_use_tls,
      });
      await fetchEmailConfig();
      toast.success("Email settings updated successfully");
      setEmailConfig(prev => ({ ...prev, resend_api_key: "", smtp_password: "" }));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save email settings");
    } finally {
      setEmailSaving(false);
    }
  };

  const fetchGateways = async () => {
    try {
      const res = await authAxios.get("/admin/payment-gateways");
      setGateways(res.data);
    } catch { /* ignore */ }
  };

  const fetchOperators = async () => {
    try {
      const res = await authAxios.get("/admin/operators");
      setOperators(res.data || []);
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
        payment_due_reminder_template: res.data.payment_due_reminder_template || "",
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

  const fetchDiagnostics = async () => {
    setDiagnosticsLoading(true);
    setDiagnostics(null);
    try {
      const res = await authAxios.get("/admin/whatsapp-diagnostics");
      setDiagnostics(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to fetch diagnostics");
    } finally {
      setDiagnosticsLoading(false);
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
      await fetchSettings();
      toast.success("Settings updated");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update settings");
    }
  };

  const VALID_BEFORE = [1, 2, 3, 5, 7];
  const VALID_AFTER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  const toggleReminderBeforeDay = (day) =>
    setReminderSettings(prev => ({
      ...prev,
      remind_before_due: prev.remind_before_due.includes(day)
        ? prev.remind_before_due.filter(d => d !== day)
        : [...prev.remind_before_due, day],
    }));

  const toggleReminderAfterDay = (day) =>
    setReminderSettings(prev => ({
      ...prev,
      remind_after_due: prev.remind_after_due.includes(day)
        ? prev.remind_after_due.filter(d => d !== day)
        : [...prev.remind_after_due, day],
    }));

  const handleSaveReminderSettings = async () => {
    setReminderSaving(true);
    try {
      await authAxios.put("/admin/reminder-settings", reminderSettings);
      toast.success("Global reminder settings saved");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save reminder settings");
    } finally {
      setReminderSaving(false);
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
      await authAxios.post("/admin/payment-gateways", {
        ...gatewayForm,
        for_operator_id: gatewayForm.for_operator_id === "platform" ? null : gatewayForm.for_operator_id,
      });
      toast.success("Gateway configured");
      setShowGatewayDialog(false);
      setGatewayForm({ gateway_type: "razorpay", api_key: "", api_secret: "", webhook_secret: "", is_active: true, for_operator_id: "platform" });
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

  const handleUpdateAdminProfile = async (e) => {
    e.preventDefault();
    if (!adminProfileForm.name.trim() || adminProfileForm.name.trim().length < 2) {
      toast.error("Admin name must be at least 2 characters");
      return;
    }
    setProfileSaving(true);
    try {
      await authAxios.put("/auth/profile", {
        name: adminProfileForm.name.trim(),
      });
      await refreshCurrentUser();
      toast.success("Admin name updated successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update admin name");
    } finally {
      setProfileSaving(false);
    }
  };

  const handleClearBrowserCache = async () => {
    setCacheClearing(true);
    try {
      await clearBrowserCache();
      toast.success("Browser cache cleared. Reloading fresh data...");
      window.setTimeout(() => window.location.reload(), 200);
    } catch (error) {
      toast.error("Failed to clear browser cache");
    } finally {
      setCacheClearing(false);
    }
  };

  const handleSendEmailTest = async (provider) => {
    const normalizedEmail = testEmail.trim();
    if (!normalizedEmail) {
      toast.error("Enter a test email address first");
      return;
    }

    setEmailTestSending((prev) => ({ ...prev, [provider]: true }));
    try {
      const endpoint = provider === "resend" ? "/admin/email-settings/test-resend" : "/admin/email-settings/test-smtp";
      const res = await authAxios.post(endpoint, { email: normalizedEmail });
      toast.success(res.data.message || "Test email sent successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send test email");
    } finally {
      setEmailTestSending((prev) => ({ ...prev, [provider]: false }));
    }
  };

  // ── Danger Zone handlers ────────────────────────────────────────────────
  const handleRequestResetOTP = async () => {
    setResetOtpLoading(true);
    try {
      const res = await authAxios.post("/admin/reset/request-otp");
      toast.success(res.data.message);
      setResetOtpSent(true);
      setResetOtpInput("");
      setResetResult(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send OTP");
    } finally {
      setResetOtpLoading(false);
    }
  };

  const handleExecuteReset = async () => {
    if (!resetOtpInput.trim()) { toast.error("Enter the OTP first"); return; }
    setResetExecuteLoading(true);
    try {
      const res = await authAxios.post("/admin/reset/execute", { otp: resetOtpInput.trim() });
      setResetResult({ success: true, message: res.data.message, summary: res.data.summary });
      toast.success("System reset complete");
      setShowResetConfirm(false);
      setResetOtpSent(false);
      setResetOtpInput("");
    } catch (err) {
      setResetResult({ success: false, message: err.response?.data?.detail || "Reset failed" });
      toast.error(err.response?.data?.detail || "Reset failed");
    } finally {
      setResetExecuteLoading(false);
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
            <TabsTrigger value="reminders">Reminders</TabsTrigger>
            <TabsTrigger value="gateways">Payment Gateways</TabsTrigger>
            <TabsTrigger value="whatsapp" data-testid="tab-whatsapp">WhatsApp</TabsTrigger>
            <TabsTrigger value="backup">Backup & Restore</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="email">Email API</TabsTrigger>
            <TabsTrigger value="danger" className="text-red-600 data-[state=active]:text-red-700">Danger Zone</TabsTrigger>
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
                  <div className="space-y-2">
                    <Label>Session/Idle Timeout (Hours)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      min="0.1"
                      value={settings?.session_timeout_hours || 24}
                      onChange={(e) => setSettings(s => ({ ...s, session_timeout_hours: parseFloat(e.target.value) || 24 }))}
                    />
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-4">
                  <div>
                    <p className="font-medium text-slate-900">Cron Schedule Times</p>
                    <p className="text-sm text-slate-600">
                      All scheduled jobs use Asia/Kolkata time and update immediately after saving.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {CRON_FIELDS.map((field) => (
                      <div key={field.key} className="space-y-2">
                        <Label>{field.label}</Label>
                        <Input
                          type="time"
                          value={settings?.[field.key] || ""}
                          onChange={(e) => setSettings((s) => ({ ...s, [field.key]: e.target.value }))}
                        />
                        <p className="text-xs text-slate-500">{field.help}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 space-y-4">
                  <div>
                    <p className="font-medium text-slate-900">Referral Benefits</p>
                    <p className="text-sm text-slate-600">
                      Control the referral discount for new operators and the wallet reward given to referrers.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Referral Discount (%)</Label>
                      <Input
                        type="number"
                        min="0"
                        value={settings?.referral_discount_percent ?? 10}
                        onChange={(e) => setSettings(s => ({ ...s, referral_discount_percent: parseFloat(e.target.value) || 0 }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Referral Discount Max (INR)</Label>
                      <Input
                        type="number"
                        min="0"
                        value={settings?.referral_discount_max_amount ?? 500}
                        onChange={(e) => setSettings(s => ({ ...s, referral_discount_max_amount: parseFloat(e.target.value) || 0 }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Referral Reward (%)</Label>
                      <Input
                        type="number"
                        min="0"
                        value={settings?.referral_reward_percent ?? 5}
                        onChange={(e) => setSettings(s => ({ ...s, referral_reward_percent: parseFloat(e.target.value) || 0 }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Referral Reward Validity (Days)</Label>
                      <Input
                        type="number"
                        min="1"
                        value={settings?.referral_reward_valid_days ?? 90}
                        onChange={(e) => setSettings(s => ({ ...s, referral_reward_valid_days: parseInt(e.target.value) || 90 }))}
                      />
                    </div>
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
                <div className="rounded-lg border border-indigo-200 bg-indigo-50/50 p-4 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-indigo-900">Welcome Modal</p>
                      <p className="text-sm text-indigo-700">
                        Show an announcement popup to users when they log in for the first time (or when version changes).
                      </p>
                    </div>
                    <Switch
                      checked={!!settings?.welcome_modal_enabled}
                      onCheckedChange={(checked) => setSettings(s => ({ ...s, welcome_modal_enabled: checked }))}
                    />
                  </div>
                  {settings?.welcome_modal_enabled && (
                    <div className="space-y-3">
                      <div className="space-y-2">
                        <Label>Modal Title</Label>
                        <Input
                          value={settings?.welcome_modal_title || ""}
                          onChange={(e) => setSettings(s => ({ ...s, welcome_modal_title: e.target.value }))}
                          placeholder="Welcome to E-Bill"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Modal Content</Label>
                        <Textarea
                          value={settings?.welcome_modal_content || ""}
                          onChange={(e) => setSettings(s => ({ ...s, welcome_modal_content: e.target.value }))}
                          placeholder="Write your announcement or welcome message here. Supports plain text."
                          rows={4}
                        />
                        <p className="text-xs text-slate-500">Tip: Increment Version below to force all users to see the modal again.</p>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Show For</Label>
                          <Select
                            value={settings?.welcome_modal_show_for || "all"}
                            onValueChange={(v) => setSettings(s => ({ ...s, welcome_modal_show_for: v }))}
                          >
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="all">All Users</SelectItem>
                              <SelectItem value="operators">Operators &amp; Staff Only</SelectItem>
                              <SelectItem value="admins">Admins Only</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Version (increment to re-show to all users)</Label>
                          <Input
                            type="number"
                            min="1"
                            value={settings?.welcome_modal_version || 1}
                            onChange={(e) => setSettings(s => ({ ...s, welcome_modal_version: parseInt(e.target.value) || 1 }))}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                <Button onClick={handleUpdateSettings}>Save Settings</Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reminders Tab */}
          <TabsContent value="reminders" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Global WhatsApp Reminder Schedule
                </CardTitle>
                <p className="text-sm text-slate-500">
                  Configure when reminders are sent for all operators with the WhatsApp Notifications add-on.
                </p>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Enable/Disable */}
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div>
                    <p className="font-medium text-sm">Enable Automated Reminders</p>
                    <p className="text-xs text-slate-500">When disabled, no reminders are sent to any subscriber</p>
                  </div>
                  <Switch
                    checked={reminderSettings.enabled}
                    onCheckedChange={(v) => setReminderSettings(s => ({ ...s, enabled: v }))}
                  />
                </div>

                {/* Before Due */}
                <div className="space-y-2">
                  <Label>Remind Days BEFORE Due Date</Label>
                  <div className="flex flex-wrap gap-2">
                    {VALID_BEFORE.map(d => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => toggleReminderBeforeDay(d)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                          reminderSettings.remind_before_due.includes(d)
                            ? "bg-slate-900 text-white border-slate-900"
                            : "bg-white text-slate-700 border-slate-200 hover:border-slate-400"
                        }`}
                      >
                        {d}d
                      </button>
                    ))}
                  </div>
                </div>

                {/* On Due Date */}
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div>
                    <p className="font-medium text-sm">Remind on Due Date</p>
                    <p className="text-xs text-slate-500">Send a reminder on the day the payment is due</p>
                  </div>
                  <Switch
                    checked={reminderSettings.remind_on_due}
                    onCheckedChange={(v) => setReminderSettings(s => ({ ...s, remind_on_due: v }))}
                  />
                </div>

                {/* After Due */}
                <div className="space-y-2">
                  <Label>Remind Days AFTER Due Date</Label>
                  <div className="flex flex-wrap gap-2">
                    {VALID_AFTER.map(d => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => toggleReminderAfterDay(d)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                          reminderSettings.remind_after_due.includes(d)
                            ? "bg-red-600 text-white border-red-600"
                            : "bg-white text-slate-700 border-slate-200 hover:border-red-300"
                        }`}
                      >
                        {d}d
                      </button>
                    ))}
                  </div>
                </div>

                {/* Max Reminders */}
                <div className="space-y-2">
                  <Label>Max Reminders per Invoice</Label>
                  <Input
                    type="number"
                    min={1}
                    max={20}
                    value={reminderSettings.max_reminders_per_invoice}
                    onChange={(e) => setReminderSettings(s => ({ ...s, max_reminders_per_invoice: parseInt(e.target.value) || 1 }))}
                    className="w-28"
                  />
                  <p className="text-xs text-slate-500">Maximum 20 reminders per invoice</p>
                </div>

                <Button onClick={handleSaveReminderSettings} disabled={reminderSaving}>
                  {reminderSaving ? "Saving..." : "Save Reminder Settings"}
                </Button>
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
                      <TableHead>Assigned To</TableHead>
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
                            {gw.is_platform_gateway ? "Platform / SaaS Payments" : gw.operator_name || "Assigned Operator"}
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

            {/* Account Diagnostics */}
            <Card className="border-amber-200">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <span className="text-amber-600">🔍</span>
                    Account Diagnostics
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchDiagnostics}
                    disabled={diagnosticsLoading || !waConfig.is_configured}
                    className="border-amber-300 text-amber-700 hover:bg-amber-50 gap-1.5"
                  >
                    {diagnosticsLoading ? "Checking..." : "Run Diagnostics"}
                  </Button>
                </div>
                <p className="text-sm text-slate-500">
                  Check your WhatsApp Business account status — whether it's in <strong>Live</strong> or <strong>Development (test)</strong> mode. In development mode, messages are only delivered to test numbers.
                </p>
              </CardHeader>
              {diagnostics && (
                <CardContent>
                  <div className="space-y-3">
                    {/* Mode badge */}
                    <div className={`flex items-center gap-3 p-3 rounded-lg border ${
                      diagnostics.mode === "LIVE"
                        ? "bg-green-50 border-green-200"
                        : diagnostics.mode === "DEVELOPMENT"
                        ? "bg-red-50 border-red-200"
                        : "bg-yellow-50 border-yellow-200"
                    }`}>
                      <span className="text-2xl">
                        {diagnostics.mode === "LIVE" ? "✅" : diagnostics.mode === "DEVELOPMENT" ? "⚠️" : "❓"}
                      </span>
                      <div>
                        <p className={`font-bold text-sm ${
                          diagnostics.mode === "LIVE" ? "text-green-800" : diagnostics.mode === "DEVELOPMENT" ? "text-red-800" : "text-yellow-800"
                        }`}>
                          Account Mode: {diagnostics.mode}
                          {diagnostics.throughput_level && (
                            <span className="ml-2 text-xs font-normal opacity-75">(throughput: {diagnostics.throughput_level})</span>
                          )}
                        </p>
                        {diagnostics.mode === "DEVELOPMENT" && (
                          <p className="text-xs text-red-700 mt-0.5">
                            Messages only delivered to pre-approved test numbers in Meta. All others get 200 OK but are silently dropped.
                          </p>
                        )}
                        {diagnostics.mode === "LIVE" && (
                          <p className="text-xs text-green-700 mt-0.5">Messages can be sent to all WhatsApp numbers.</p>
                        )}
                      </div>
                    </div>

                    {/* Warning message */}
                    {diagnostics.warning && (
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 space-y-2">
                        <p><strong>⚠ {diagnostics.is_test_number ? "Test Number Detected" : "Action Required"}:</strong> {diagnostics.warning}</p>
                        {diagnostics.fix_steps?.length > 0 && (
                          <div>
                            <p className="font-semibold mb-1">How to fix:</p>
                            <ul className="space-y-1.5">
                              {diagnostics.fix_steps.map((step, i) => (
                                <li key={i} className="flex gap-1.5">
                                  <span className="font-bold shrink-0">{i + 1}.</span>
                                  <span>{step}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <p className="border-t border-amber-200 pt-2">
                          👉 <a href="https://developers.facebook.com/apps/" target="_blank" rel="noreferrer" className="underline font-medium">Open Meta for Developers Portal</a>
                        </p>
                      </div>
                    )}

                    {/* Phone number details */}
                    {diagnostics.phone_number && !diagnostics.phone_number.error && (
                      <div className="bg-slate-50 rounded-lg p-3 text-xs space-y-1">
                        <p className="font-medium text-slate-700">Phone Number Details</p>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-600">
                          {diagnostics.phone_number.verified_name && <><span className="text-slate-400">Name:</span><span>{diagnostics.phone_number.verified_name}</span></>}
                          {diagnostics.phone_number.display_phone_number && <><span className="text-slate-400">Number:</span><span>{diagnostics.phone_number.display_phone_number}</span></>}
                          {diagnostics.phone_number.quality_rating && <><span className="text-slate-400">Quality:</span><span className={diagnostics.phone_number.quality_rating === "GREEN" ? "text-green-600" : "text-amber-600"}>{diagnostics.phone_number.quality_rating}</span></>}
                          {diagnostics.phone_number.status && <><span className="text-slate-400">Status:</span><span>{diagnostics.phone_number.status}</span></>}
                        </div>
                      </div>
                    )}
                    {diagnostics.phone_number?.error && (
                      <p className="text-xs text-red-600 bg-red-50 rounded p-2">
                        Phone Number API error: {diagnostics.phone_number.error?.message || JSON.stringify(diagnostics.phone_number.error)}
                      </p>
                    )}
                  </div>
                </CardContent>
              )}
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
                    { key: "reminder_template", label: "Payment Reminders (Before / On Due Date)", desc: "Template used for reminders sent before or on the due date" },
                    { key: "payment_due_reminder_template", label: "Payment Due Reminders (Overdue)", desc: "Template for overdue invoice reminders — sent after the due date has passed" },
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

                  <div className="pt-2 border-t border-slate-200">
                    <p className="text-sm font-semibold text-slate-700 mb-3">Operator Notifications (sent to operator's phone)</p>
                    {[
                      { key: "operator_low_balance_template", label: "Operator Low Balance Alert", desc: "Sent to operator when wallet balance drops below ₹500" },
                      { key: "operator_account_expiry_template", label: "Operator Account Expiry", desc: "Sent to operator when subscription expires or trial ends" },
                      { key: "operator_renewal_template", label: "Operator Renewal Reminder", desc: "Sent to operator 7, 3, and 1 day(s) before subscription expires" },
                      { key: "operator_daily_report_template", label: "Operator Daily Report", desc: "Daily billing summary sent to operator at the configured report time" },
                    ].map(({ key, label, desc }) => (
                      <div key={key} className="space-y-1.5 mb-4">
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
                  </div>

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
                    <p className="text-xs text-emerald-600">Daily at {settings?.cron_backup_time || DEFAULT_SETTINGS.cron_backup_time} IST</p>
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
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5" /> Cryptography Keys
                  </CardTitle>
                  <p className="text-sm text-slate-500">Manage critical system security keys.</p>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSaveSecuritySettings} className="space-y-4">
                    <div className="space-y-2">
                      <Label>JWT Secret</Label>
                      <div className="relative">
                        <Input
                          type={showSecurityKeys.jwt ? "text" : "password"}
                          value={securitySettings.jwt_secret}
                          onChange={(e) => setSecuritySettings(s => ({ ...s, jwt_secret: e.target.value }))}
                          placeholder={securitySettings.jwt_secret_preview || "Enter new JWT secret"}
                        />
                        <button
                          type="button"
                          onClick={() => setShowSecurityKeys(p => ({ ...p, jwt: !p.jwt }))}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                          {showSecurityKeys.jwt ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      <p className="text-xs text-slate-400">Used for signing authentication tokens. Change requires app restart.</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Backup Encryption Password</Label>
                      <div className="relative">
                        <Input
                          type={showSecurityKeys.backup ? "text" : "password"}
                          value={securitySettings.backup_password}
                          onChange={(e) => setSecuritySettings(s => ({ ...s, backup_password: e.target.value }))}
                          placeholder={securitySettings.backup_password_preview || "Enter backup encryption password"}
                        />
                        <button
                          type="button"
                          onClick={() => setShowSecurityKeys(p => ({ ...p, backup: !p.backup }))}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                          {showSecurityKeys.backup ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      <p className="text-xs text-slate-400">Encrypts all system backups. Store securely for recovery.</p>
                    </div>
                    <Button type="submit" disabled={securitySaving} className="w-full">
                      {securitySaving ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Saving...</> : "Save Security Settings"}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5" /> Admin Profile
                  </CardTitle>
                  <p className="text-sm text-slate-500">Update the display name shown across the admin panel.</p>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleUpdateAdminProfile} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="admin_name">Admin Name</Label>
                      <Input
                        id="admin_name"
                        value={adminProfileForm.name}
                        onChange={(e) => setAdminProfileForm({ name: e.target.value })}
                        placeholder="Enter admin name"
                      />
                    </div>
                    <Button type="submit" disabled={profileSaving} className="w-full">
                      {profileSaving ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Saving...</> : "Save Admin Name"}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="w-5 h-5" /> Browser Cache
                  </CardTitle>
                  <p className="text-sm text-slate-500">Clear stale dashboard and API data stored in this browser.</p>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    Use this if dashboard values look outdated after login. Login now also clears the app cache automatically.
                  </div>
                  <Button type="button" onClick={handleClearBrowserCache} disabled={cacheClearing} className="w-full">
                    {cacheClearing ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Clearing...</> : "Clear Browser Cache"}
                  </Button>
                </CardContent>
              </Card>

              <Card className="lg:col-span-2 max-w-lg">
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
            </div>
          </TabsContent>

          {/* Email API Tab */}
          <TabsContent value="email" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  Email Delivery Configuration
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(emailConfig.is_configured || emailConfig.is_smtp_configured) && (
                  <div className="mb-4 grid gap-3 md:grid-cols-2">
                    <div className={`flex items-center gap-2 border px-4 py-2.5 rounded-lg text-sm ${
                      emailConfig.is_configured ? "bg-green-50 border-green-200 text-green-700" : "bg-slate-50 border-slate-200 text-slate-500"
                    }`}>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Resend {emailConfig.is_configured ? "configured" : "not configured"}</span>
                      {emailConfig.resend_api_key_preview && (
                        <span className="ml-1 font-mono text-xs">({emailConfig.resend_api_key_preview})</span>
                      )}
                    </div>
                    <div className={`flex items-center gap-2 border px-4 py-2.5 rounded-lg text-sm ${
                      emailConfig.is_smtp_configured ? "bg-blue-50 border-blue-200 text-blue-700" : "bg-slate-50 border-slate-200 text-slate-500"
                    }`}>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>SMTP fallback {emailConfig.is_smtp_configured ? "configured" : "not configured"}</span>
                    </div>
                  </div>
                )}
                <form onSubmit={handleSaveEmailConfig} className="space-y-4">
                  <div className="rounded-lg border border-slate-200 p-4 space-y-4">
                    <div>
                      <p className="font-medium text-slate-900">Primary Provider: Resend</p>
                      <p className="text-sm text-slate-500">Used first for transactional emails. If delivery fails, SMTP fallback is tried next.</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Resend API Key</Label>
                      <div className="relative">
                        <Input
                          type={showEmailKey ? "text" : "password"}
                          value={emailConfig.resend_api_key}
                          onChange={(e) => setEmailConfig(prev => ({ ...prev, resend_api_key: e.target.value }))}
                          placeholder={emailConfig.is_configured ? "Enter new key to update" : "re_......"}
                          className="pr-10"
                          data-testid="email-api-key-input"
                        />
                        <button type="button" tabIndex={-1}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                          onClick={() => setShowEmailKey(v => !v)}>
                          {showEmailKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      <p className="text-xs text-slate-400">Get your API key from <a href="https://resend.com/api-keys" target="_blank" rel="noopener noreferrer" className="underline text-blue-500">resend.com/api-keys <ExternalLink className="inline w-3 h-3" /></a></p>
                    </div>
                    <div className="space-y-2">
                      <Label>Resend From Email</Label>
                      <Input
                        type="email"
                        value={emailConfig.resend_from_email}
                        onChange={(e) => setEmailConfig(prev => ({ ...prev, resend_from_email: e.target.value }))}
                        placeholder="noreply@yourdomain.com"
                        data-testid="email-from-input"
                      />
                      <p className="text-xs text-slate-400">Required if you provide a Resend API key.</p>
                    </div>
                  </div>
                  <div className="rounded-lg border border-blue-200 bg-blue-50/40 p-4 space-y-4">
                    <div>
                      <p className="font-medium text-slate-900">Fallback Provider: SMTP</p>
                      <p className="text-sm text-slate-500">Used automatically if Resend fails. You can also keep only SMTP configured.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>SMTP Host</Label>
                        <Input
                          value={emailConfig.smtp_host}
                          onChange={(e) => setEmailConfig(prev => ({ ...prev, smtp_host: e.target.value }))}
                          placeholder="smtp.yourdomain.com"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>SMTP Port</Label>
                        <Input
                          type="number"
                          value={emailConfig.smtp_port}
                          onChange={(e) => setEmailConfig(prev => ({ ...prev, smtp_port: e.target.value }))}
                          placeholder="587"
                        />
                        <p className="text-xs text-slate-400">Use `587` for STARTTLS or `465` for SSL. Port `465` now uses SSL automatically during test/send.</p>
                      </div>
                      <div className="space-y-2">
                        <Label>SMTP Username</Label>
                        <Input
                          value={emailConfig.smtp_username}
                          onChange={(e) => setEmailConfig(prev => ({ ...prev, smtp_username: e.target.value }))}
                          placeholder="mailer@yourdomain.com"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>SMTP Password</Label>
                        <Input
                          type="password"
                          value={emailConfig.smtp_password}
                          onChange={(e) => setEmailConfig(prev => ({ ...prev, smtp_password: e.target.value }))}
                          placeholder={emailConfig.is_smtp_configured ? "Enter new password to update" : "SMTP password"}
                        />
                      </div>
                      <div className="space-y-2 md:col-span-2">
                        <Label>SMTP From Email</Label>
                        <Input
                          type="email"
                          value={emailConfig.smtp_from_email}
                          onChange={(e) => setEmailConfig(prev => ({ ...prev, smtp_from_email: e.target.value }))}
                          placeholder="smtp@yourdomain.com"
                        />
                        <p className="text-xs text-slate-400">If left blank, the Resend from email will be reused.</p>
                      </div>
                      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 md:col-span-2">
                        <div>
                          <p className="font-medium text-slate-900">Use TLS</p>
                          <p className="text-xs text-slate-500">Enable STARTTLS for secure SMTP delivery.</p>
                        </div>
                        <Switch
                          checked={!!emailConfig.smtp_use_tls}
                          onCheckedChange={(checked) => setEmailConfig(prev => ({ ...prev, smtp_use_tls: checked }))}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-4 space-y-4">
                    <div>
                      <p className="font-medium text-slate-900">Send Test Email</p>
                      <p className="text-sm text-slate-500">Verify Resend and SMTP separately with the currently saved settings.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-3 items-end">
                      <div className="space-y-2">
                        <Label>Test Email Address</Label>
                        <Input
                          type="email"
                          value={testEmail}
                          onChange={(e) => setTestEmail(e.target.value)}
                          placeholder="admin@example.com"
                        />
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => handleSendEmailTest("resend")}
                        disabled={emailTestSending.resend}
                      >
                        {emailTestSending.resend ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Sending...</> : "Send Resend Test"}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => handleSendEmailTest("smtp")}
                        disabled={emailTestSending.smtp}
                      >
                        {emailTestSending.smtp ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Sending...</> : "Send SMTP Test"}
                      </Button>
                    </div>
                    <p className="text-xs text-slate-400">
                      If your SMTP server does not support AUTH, E-Bill will now skip SMTP login and still attempt delivery.
                    </p>
                  </div>
                  <Button type="submit" disabled={emailSaving} className="bg-[#0066B2] hover:bg-[#004080] text-white" data-testid="save-email-btn">
                    {emailSaving ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Saving...</> : "Save Email Settings"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Danger Zone Tab */}
          <TabsContent value="danger" className="mt-6">
            <Card className="border-red-200">
              <CardHeader className="bg-red-50">
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <AlertTriangle className="w-5 h-5" />
                  Danger Zone
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-6">
                {/* System Reset Section */}
                <div className="rounded-lg border-2 border-red-300 bg-red-50 p-6">
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-lg font-semibold text-red-800 flex items-center gap-2">
                        <Database className="w-5 h-5" />
                        Complete System Reset
                      </h3>
                      <p className="text-sm text-red-700 mt-2">
                        This will permanently delete <strong>ALL operator data</strong> from the platform including:
                      </p>
                      <ul className="mt-2 ml-6 text-sm text-red-700 list-disc space-y-1">
                        <li>All operators and their data</li>
                        <li>All subscribers and subscriptions</li>
                        <li>All invoices and payment records</li>
                        <li>All wallet transactions</li>
                        <li>All payment gateways and settings</li>
                      </ul>
                      <p className="text-sm text-red-700 mt-3 font-medium">
                        ⚠️ This action is <strong>IRREVERSIBLE</strong> and cannot be undone.
                      </p>
                      <p className="text-sm text-green-700 mt-2">
                        ✓ Admin settings preserved: WhatsApp templates, backup files, platform settings
                      </p>
                    </div>
                    
                    <div className="bg-white rounded-lg border border-red-200 p-4">
                      <p className="text-sm text-slate-700 font-medium mb-2">Security Verification Required:</p>
                      <p className="text-xs text-slate-600">
                        To proceed, you'll need to verify your identity using a One-Time Password (OTP) sent to your registered admin email.
                      </p>
                    </div>

                    <Button 
                      variant="destructive" 
                      className="w-full sm:w-auto bg-red-600 hover:bg-red-700"
                      onClick={() => setShowResetConfirm(true)}
                      data-testid="reset-entire-system-btn"
                    >
                      <AlertTriangle className="w-4 h-4 mr-2" />
                      Reset Entire System
                    </Button>
                  </div>
                </div>

                {/* Result Display */}
                {resetResult && (
                  <div className={`rounded-lg border-2 p-4 ${
                    resetResult.success 
                      ? 'border-green-300 bg-green-50' 
                      : 'border-red-300 bg-red-50'
                  }`}>
                    <p className={`font-medium ${resetResult.success ? 'text-green-800' : 'text-red-800'}`}>
                      {resetResult.message}
                    </p>
                    {resetResult.summary && (
                      <div className="mt-3 space-y-1 text-sm text-slate-700">
                        <p><strong>Deleted:</strong></p>
                        <ul className="ml-6 list-disc">
                          <li>{resetResult.summary.operators || 0} operators</li>
                          <li>{resetResult.summary.invoices || 0} invoices</li>
                          <li>{resetResult.summary.subscribers || 0} subscribers</li>
                          <li>{resetResult.summary.plans || 0} plans</li>
                          <li>{resetResult.summary.users || 0} users</li>
                          <li>{resetResult.summary.wallets || 0} wallets</li>
                          <li>{resetResult.summary.wallet_transactions || 0} wallet transactions</li>
                          <li>{resetResult.summary.payment_gateways || 0} payment gateways</li>
                        </ul>
                        <p className="text-xs text-green-700 mt-2">✓ WhatsApp templates and backup files preserved</p>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* System Reset OTP Confirmation Dialog */}
        <Dialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-700">
                <AlertTriangle className="w-5 h-5" />
                Confirm System Reset
              </DialogTitle>
              <DialogDescription>
                This will permanently delete <strong>ALL operator data</strong>. Admin settings will be preserved.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              {/* Warning Box */}
              <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800 font-medium flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Are you absolutely sure?
                </p>
                <p className="text-xs text-red-700 mt-2">
                  All operators, subscribers, invoices, and transactions will be permanently deleted.
                </p>
                <p className="text-xs text-green-700 mt-1">
                  WhatsApp templates and backup files will be preserved.
                </p>
              </div>

              {/* OTP Step */}
              {!resetOtpSent ? (
                <div className="space-y-3">
                  <p className="text-sm text-slate-700">
                    Click below to receive a One-Time Password (OTP) via email to verify this action.
                  </p>
                  <Button 
                    onClick={handleRequestResetOTP}
                    disabled={resetOtpLoading}
                    className="w-full bg-red-600 hover:bg-red-700"
                    data-testid="send-otp-btn"
                  >
                    {resetOtpLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Sending OTP...
                      </>
                    ) : (
                      <>
                        <Shield className="w-4 h-4 mr-2" />
                        Send OTP to Email
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="text-sm text-green-800 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      OTP sent to your registered email
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Lock className="w-4 h-4" />
                      Enter OTP
                    </Label>
                    <Input 
                      type="text" 
                      placeholder="Enter 6-digit OTP"
                      value={resetOtpInput}
                      onChange={(e) => setResetOtpInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleExecuteReset()}
                      maxLength={6}
                      className="text-center text-lg tracking-widest"
                      data-testid="reset-otp-input"
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      className="flex-1"
                      onClick={() => {
                        setShowResetConfirm(false);
                        setResetOtpSent(false);
                        setResetOtpInput("");
                      }}
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleExecuteReset}
                      disabled={resetExecuteLoading || !resetOtpInput.trim()}
                      className="flex-1 bg-red-600 hover:bg-red-700"
                      data-testid="confirm-reset-btn"
                    >
                      {resetExecuteLoading ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          Resetting...
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          Confirm Reset
                        </>
                      )}
                    </Button>
                  </div>

                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={handleRequestResetOTP}
                    disabled={resetOtpLoading}
                    className="w-full text-xs"
                  >
                    Didn't receive OTP? Resend
                  </Button>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>


        {/* Add Gateway Dialog */}
        <Dialog open={showGatewayDialog} onOpenChange={setShowGatewayDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Payment Gateway</DialogTitle>
              <DialogDescription>Configure platform keys or assign gateway credentials directly to an operator.</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddGateway} className="space-y-4">
              <div className="space-y-2">
                <Label>Assign To</Label>
                <Select value={gatewayForm.for_operator_id} onValueChange={(v) => setGatewayForm(f => ({ ...f, for_operator_id: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="platform">Platform / SaaS Payments</SelectItem>
                    {operators.map((operator) => (
                      <SelectItem key={operator.id} value={operator.id}>
                        {operator.company_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-500">
                  Choose platform keys for SaaS collections or assign operator-specific keys for subscriber payment links.
                </p>
              </div>
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
                <Button variant="outline" type="button" onClick={() => {
                  setShowGatewayDialog(false);
                  setGatewayForm({ gateway_type: "razorpay", api_key: "", api_secret: "", webhook_secret: "", is_active: true, for_operator_id: "platform" });
                }}>Cancel</Button>
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
