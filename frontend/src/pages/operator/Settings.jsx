import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { toast } from "sonner";
import { 
  Building2, 
  CreditCard, 
  Bell,
  Shield,
  Save,
  Key,
  FileText,
  CheckCircle2,
  LayoutTemplate,
  Clock,
  CalendarClock,
  Palette,
  Loader2,
  Upload,
} from "lucide-react";

const OperatorSettings = () => {
  const { authAxios, user, features } = useAuth();
  const isImpersonated = !!user?.impersonated_by;
  const hasPaymentReminder = !!features?.whatsapp_notifications;
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [logoUploading, setLogoUploading] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [profile, setProfile] = useState(null);
  const [gatewayConfig, setGatewayConfig] = useState(null);

  // Theme state
  const [currentTheme, setCurrentTheme] = useState("modern");
  const [themeSaving, setThemeSaving] = useState(false);

  const [reminderSaving, setReminderSaving] = useState(false);
  
  const [profileForm, setProfileForm] = useState({
    company_name: "",
    owner_name: "",
    phone: "",
    gst_number: "",
    charge_gst: false,
    bank_account_name: "",
    bank_account_number: "",
    bank_ifsc: "",
    bank_name: ""
  });

  const [invoiceForm, setInvoiceForm] = useState({
    company_name: "",
    company_address: "",
    company_phone: "",
    company_email: "",
    logo_url: "",
    invoice_prefix: "INV",
    invoice_footer: "",
    show_gst: true,
    terms_conditions: "",
    invoice_template: "classic",
    visible_fields: {
      show_logo: true,
      show_company_address: true,
      show_company_phone: true,
      show_company_email: true,
      show_bank_details: true,
      show_subscriber_phone: true,
      show_subscriber_email: true,
      show_subscriber_address: true,
    },
  });

  const [gatewayForm, setGatewayForm] = useState({
    gateway_type: "razorpay",
    api_key: "",
    api_secret: "",
    webhook_secret: ""
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const promises = [
        authAxios.get("/operator/dashboard"),
        authAxios.get("/operator/profile"),
        authAxios.get("/operator/payment-gateway").catch(() => ({ data: { configured: false } })),
        authAxios.get("/operator/invoice-settings").catch(() => ({ data: {} })),
        authAxios.get("/operator/theme-settings").catch(() => ({ data: { theme: "modern" } })),
      ];
      const [dashboardRes, profileRes, gatewayRes, invoiceRes, themeRes] = await Promise.all(promises);

      setDashboardStats(dashboardRes.data);
      setProfile(profileRes.data);
      setGatewayConfig(gatewayRes.data);
      setCurrentTheme(themeRes.data.theme || "modern");

      setProfileForm({
        company_name: profileRes.data.company_name || "",
        owner_name: profileRes.data.owner_name || "",
        phone: profileRes.data.phone || "",
        gst_number: profileRes.data.gst_number || "",
        charge_gst: profileRes.data.charge_gst || false,
        bank_account_name: profileRes.data.bank_account_name || "",
        bank_account_number: profileRes.data.bank_account_number || "",
        bank_ifsc: profileRes.data.bank_ifsc || "",
        bank_name: profileRes.data.bank_name || ""
      });

      setInvoiceForm({
        company_name: invoiceRes.data.company_name || profileRes.data.company_name || "",
        company_address: invoiceRes.data.company_address || "",
        company_phone: invoiceRes.data.company_phone || profileRes.data.phone || "",
        company_email: invoiceRes.data.company_email || profileRes.data.email || "",
        logo_url: invoiceRes.data.logo_url || "",
        invoice_prefix: invoiceRes.data.invoice_prefix || "INV",
        invoice_footer: invoiceRes.data.invoice_footer || "",
        show_gst: invoiceRes.data.show_gst !== false,
        terms_conditions: invoiceRes.data.terms_conditions || "",
        invoice_template: invoiceRes.data.invoice_template || "classic",
        visible_fields: {
          show_logo: invoiceRes.data.visible_fields?.show_logo !== false,
          show_company_address: invoiceRes.data.visible_fields?.show_company_address !== false,
          show_company_phone: invoiceRes.data.visible_fields?.show_company_phone !== false,
          show_company_email: invoiceRes.data.visible_fields?.show_company_email !== false,
          show_bank_details: invoiceRes.data.visible_fields?.show_bank_details !== false,
          show_subscriber_phone: invoiceRes.data.visible_fields?.show_subscriber_phone !== false,
          show_subscriber_email: invoiceRes.data.visible_fields?.show_subscriber_email !== false,
          show_subscriber_address: invoiceRes.data.visible_fields?.show_subscriber_address !== false,
        },
      });

      if (gatewayRes.data.configured) {
        setGatewayForm(prev => ({
          ...prev,
          gateway_type: gatewayRes.data.gateway_type || "razorpay"
        }));
      }
    } catch (error) {
      toast.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    // Validation
    if (!profileForm.company_name?.trim() || profileForm.company_name.trim().length < 2) {
      toast.error("Company name must be at least 2 characters"); return;
    }
    if (!profileForm.owner_name?.trim() || profileForm.owner_name.trim().length < 2) {
      toast.error("Owner name must be at least 2 characters"); return;
    }
    const phoneDigits = (profileForm.phone || "").replace(/\D/g, "");
    if (!phoneDigits || phoneDigits.length !== 10) {
      toast.error("Phone number must be exactly 10 digits"); return;
    }
    if (profileForm.gst_number && !/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/i.test(profileForm.gst_number)) {
      toast.error("Please enter a valid GST number (e.g. 22AAAAA0000A1Z5)"); return;
    }
    setSaving(true);
    try {
      await authAxios.put("/operator/profile", profileForm);
      toast.success("Profile updated successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const handleGatewaySubmit = async (e) => {
    e.preventDefault();
    if (!gatewayForm.api_key?.trim() || !gatewayForm.api_secret?.trim()) {
      toast.error("API Key and API Secret are required"); return;
    }
    if (gatewayForm.api_key.trim().length < 10) {
      toast.error("Please enter a valid API Key"); return;
    }
    setSaving(true);
    try {
      await authAxios.post("/operator/payment-gateway", gatewayForm);
      toast.success("Payment gateway configured successfully");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to configure gateway");
    } finally {
      setSaving(false);
    }
  };

  const handleInvoiceSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await authAxios.put("/operator/invoice-settings", invoiceForm);
      toast.success("Invoice settings updated successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update invoice settings");
    } finally {
      setSaving(false);
    }
  };

  const handleThemeChange = async (newTheme) => {
    setThemeSaving(true);
    try {
      await authAxios.put(`/operator/theme-settings?theme=${newTheme}`);
      setCurrentTheme(newTheme);
      toast.success(`Theme changed to ${newTheme === 'modern' ? 'Modern' : 'Classic'}`);
    } catch (error) {
      toast.error("Failed to update theme");
    } finally {
      setThemeSaving(false);
    }
  };

  const handleInvoiceLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"];
    if (!allowedTypes.includes(file.type)) {
      toast.error("Please upload a PNG, JPG, or SVG image");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error("File size must be less than 5MB");
      return;
    }

    setLogoUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await authAxios.post("/operator/invoice-settings/upload-logo", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setInvoiceForm(prev => ({ ...prev, logo_url: res.data.url }));
      toast.success("Logo uploaded successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload logo");
    } finally {
      setLogoUploading(false);
      e.target.value = "";
    }
  };

  if (loading) {
    return (
      <OperatorLayout title="Settings">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const isReadOnly = dashboardStats?.is_read_only;
  const hasCustomPaymentGateway = !!features?.custom_payment_gateway;
  const showPaymentGatewayTab = isImpersonated || hasCustomPaymentGateway;

  return (
    <OperatorLayout title="Settings" isReadOnly={isReadOnly}>
      <div className="max-w-4xl animate-fade-in">
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList>
            <TabsTrigger value="profile" data-testid="tab-profile">
              <Building2 className="w-4 h-4 mr-2" />
              Business Profile
            </TabsTrigger>
            {showPaymentGatewayTab && (
              <TabsTrigger value="payment" data-testid="tab-payment">
                <CreditCard className="w-4 h-4 mr-2" />
                Payment Gateway
              </TabsTrigger>
            )}
            <TabsTrigger value="invoice" data-testid="tab-invoice">
              <FileText className="w-4 h-4 mr-2" />
              Invoice
            </TabsTrigger>
            <TabsTrigger value="theme" data-testid="tab-theme">
              <Palette className="w-4 h-4 mr-2" />
              Theme
            </TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="w-5 h-5" />
                  Business Profile
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleProfileSubmit} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Company Name</Label>
                      <Input
                        value={profileForm.company_name}
                        onChange={(e) => setProfileForm(prev => ({ ...prev, company_name: e.target.value }))}
                        disabled={isReadOnly}
                        data-testid="company-name-input"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Owner Name</Label>
                      <Input
                        value={profileForm.owner_name}
                        onChange={(e) => setProfileForm(prev => ({ ...prev, owner_name: e.target.value }))}
                        disabled={isReadOnly}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Phone</Label>
                      <Input
                        value={profileForm.phone}
                        onChange={(e) => setProfileForm(prev => ({ ...prev, phone: e.target.value }))}
                        disabled={isReadOnly}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>GST Number</Label>
                      <Input
                        value={profileForm.gst_number}
                        onChange={(e) => setProfileForm(prev => ({ ...prev, gst_number: e.target.value }))}
                        placeholder="22AAAAA0000A1Z5"
                        disabled={isReadOnly}
                        data-testid="gst-number-input"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <Label className="text-sm font-medium">Charge GST to Customers</Label>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Enable to apply GST on customer invoices
                      </p>
                    </div>
                    <Switch
                      checked={profileForm.charge_gst}
                      onCheckedChange={(checked) => {
                        if (checked && !profileForm.gst_number?.trim()) {
                          toast.error("Please add your GST number first before enabling GST charging");
                          return;
                        }
                        setProfileForm(prev => ({ ...prev, charge_gst: checked }));
                      }}
                      disabled={isReadOnly}
                      data-testid="charge-gst-switch"
                    />
                  </div>

                  <div className="border-t pt-6">
                    <h4 className="text-sm font-medium text-slate-700 mb-4">Bank Details (For Reference)</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Account Holder Name</Label>
                        <Input
                          value={profileForm.bank_account_name}
                          onChange={(e) => setProfileForm(prev => ({ ...prev, bank_account_name: e.target.value }))}
                          disabled={isReadOnly}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Account Number</Label>
                        <Input
                          value={profileForm.bank_account_number}
                          onChange={(e) => setProfileForm(prev => ({ ...prev, bank_account_number: e.target.value }))}
                          disabled={isReadOnly}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>IFSC Code</Label>
                        <Input
                          value={profileForm.bank_ifsc}
                          onChange={(e) => setProfileForm(prev => ({ ...prev, bank_ifsc: e.target.value }))}
                          disabled={isReadOnly}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Bank Name</Label>
                        <Input
                          value={profileForm.bank_name}
                          onChange={(e) => setProfileForm(prev => ({ ...prev, bank_name: e.target.value }))}
                          disabled={isReadOnly}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-4 border-t">
                    <Button type="submit" disabled={isReadOnly || saving} data-testid="save-profile-btn">
                      <Save className="w-4 h-4 mr-2" />
                      {saving ? "Saving..." : "Save Changes"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Payment Gateway Tab */}
          <TabsContent value="payment">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5" />
                  Payment Gateway Configuration
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* Info about custom payment gateway */}
                {hasCustomPaymentGateway && !isImpersonated && (
                  <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                    <strong>Custom Payment Gateway</strong> add-on is active. Configure your own Razorpay API keys below.
                    Subscriber payment links will use your account directly.
                  </div>
                )}
                {gatewayConfig?.configured && (
                  <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <div className="flex items-center gap-2 text-emerald-700">
                      <Shield className="w-5 h-5" />
                      <span className="font-medium">Gateway Configured</span>
                    </div>
                    <p className="text-sm text-emerald-600 mt-1">
                      {gatewayConfig.gateway_type?.toUpperCase()} - API Key: {gatewayConfig.api_key}
                    </p>
                  </div>
                )}

                <form onSubmit={handleGatewaySubmit} className="space-y-6">
                  <div className="space-y-2">
                    <Label>Payment Gateway</Label>
                    <Select 
                      value={gatewayForm.gateway_type} 
                      onValueChange={(value) => setGatewayForm(prev => ({ ...prev, gateway_type: value }))}
                      disabled={isReadOnly}
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

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>API Key</Label>
                      <Input
                        value={gatewayForm.api_key}
                        onChange={(e) => setGatewayForm(prev => ({ ...prev, api_key: e.target.value }))}
                        placeholder="rzp_live_xxxxx"
                        disabled={isReadOnly}
                        data-testid="api-key-input"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>API Secret</Label>
                      <Input
                        type="password"
                        value={gatewayForm.api_secret}
                        onChange={(e) => setGatewayForm(prev => ({ ...prev, api_secret: e.target.value }))}
                        placeholder="Enter API secret"
                        disabled={isReadOnly}
                        data-testid="api-secret-input"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Webhook Secret (Optional)</Label>
                    <Input
                      value={gatewayForm.webhook_secret}
                      onChange={(e) => setGatewayForm(prev => ({ ...prev, webhook_secret: e.target.value }))}
                      placeholder="For webhook signature verification"
                      disabled={isReadOnly}
                    />
                  </div>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="font-medium text-blue-800 mb-2">Important Notes:</h4>
                    <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
                      <li>Your API credentials are stored securely and encrypted</li>
                      <li>Payments flow directly from customers to your gateway account</li>
                      <li>Platform does not hold or process customer payments</li>
                      <li>Configure webhooks in your gateway dashboard for real-time updates</li>
                    </ul>
                  </div>

                  <div className="flex justify-end pt-4 border-t">
                    <Button type="submit" disabled={isReadOnly || saving} data-testid="save-gateway-btn">
                      <Key className="w-4 h-4 mr-2" />
                      {saving ? "Saving..." : "Configure Gateway"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Invoice Customization Tab */}
          <TabsContent value="invoice">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Invoice Customization
                </CardTitle>
                <p className="text-sm text-slate-500">
                  Customize how your invoices look when sent to subscribers
                </p>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleInvoiceSubmit} className="space-y-6">
                  {/* Invoice Template Selector */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <LayoutTemplate className="w-4 h-4 text-slate-600" />
                      <p className="text-sm font-medium text-slate-700">Invoice Design Template</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {/* Classic */}
                      <button
                        type="button"
                        onClick={() => setInvoiceForm(prev => ({ ...prev, invoice_template: "classic" }))}
                        className={`relative text-left rounded-xl border-2 overflow-hidden transition-all ${
                          invoiceForm.invoice_template === "classic"
                            ? "border-slate-900 shadow-md"
                            : "border-slate-200 hover:border-slate-400"
                        }`}
                      >
                        {/* Mini preview */}
                        <div className="bg-white p-3">
                          <div className="bg-slate-900 h-5 rounded-sm mb-2 flex items-center px-2">
                            <div className="w-16 h-1.5 bg-white/70 rounded" />
                            <div className="ml-auto w-10 h-1.5 bg-white/40 rounded" />
                          </div>
                          <div className="flex gap-2 mb-2">
                            <div className="flex-1 space-y-1">
                              <div className="h-1.5 bg-slate-200 rounded w-3/4" />
                              <div className="h-1.5 bg-slate-200 rounded w-1/2" />
                            </div>
                            <div className="flex-1 space-y-1">
                              <div className="h-1.5 bg-slate-200 rounded w-full" />
                              <div className="h-1.5 bg-slate-200 rounded w-3/4" />
                            </div>
                          </div>
                          <div className="border border-slate-200 rounded">
                            <div className="bg-slate-800 h-3 rounded-t" />
                            <div className="px-1 py-0.5 space-y-0.5">
                              <div className="h-1 bg-slate-100 rounded" />
                              <div className="h-1 bg-slate-100 rounded" />
                            </div>
                          </div>
                          <div className="mt-2 ml-auto w-24 bg-slate-100 rounded h-3 flex items-center justify-end pr-1">
                            <div className="h-1.5 w-12 bg-slate-400 rounded" />
                          </div>
                        </div>
                        <div className="px-3 pb-3 flex items-center justify-between">
                          <div>
                            <p className="font-semibold text-sm text-slate-800">Classic</p>
                            <p className="text-xs text-slate-500">Dark header · Clean corporate</p>
                          </div>
                          {invoiceForm.invoice_template === "classic" && (
                            <CheckCircle2 className="w-5 h-5 text-slate-900 shrink-0" />
                          )}
                        </div>
                      </button>

                      {/* Modern */}
                      <button
                        type="button"
                        onClick={() => setInvoiceForm(prev => ({ ...prev, invoice_template: "modern" }))}
                        className={`relative text-left rounded-xl border-2 overflow-hidden transition-all ${
                          invoiceForm.invoice_template === "modern"
                            ? "border-teal-600 shadow-md"
                            : "border-slate-200 hover:border-teal-400"
                        }`}
                      >
                        <div className="bg-white p-3">
                          <div className="bg-teal-700 h-5 rounded-sm mb-2 flex items-center px-2">
                            <div className="w-16 h-1.5 bg-white/70 rounded" />
                            <div className="ml-auto w-10 h-1.5 bg-white/40 rounded" />
                          </div>
                          <div className="bg-teal-50 border border-teal-200 rounded p-1.5 mb-2 flex gap-2">
                            <div className="flex-1 space-y-1">
                              <div className="h-1.5 bg-teal-200 rounded w-1/2" />
                              <div className="h-1.5 bg-slate-200 rounded w-3/4" />
                            </div>
                            <div className="flex-1 space-y-1">
                              <div className="h-1.5 bg-teal-200 rounded w-1/2" />
                              <div className="h-1.5 bg-slate-200 rounded w-3/4" />
                            </div>
                          </div>
                          <div className="border border-slate-200 rounded">
                            <div className="bg-teal-700 h-3 rounded-t" />
                            <div className="px-1 py-0.5 space-y-0.5">
                              <div className="h-1 bg-teal-50 rounded" />
                              <div className="h-1 bg-white rounded" />
                            </div>
                          </div>
                          <div className="mt-2 ml-auto w-24 bg-teal-50 border border-teal-200 rounded h-3 flex items-center justify-end pr-1">
                            <div className="h-1.5 w-12 bg-teal-600 rounded" />
                          </div>
                        </div>
                        <div className="px-3 pb-3 flex items-center justify-between">
                          <div>
                            <p className="font-semibold text-sm text-teal-800">Modern</p>
                            <p className="text-xs text-slate-500">Teal accent · Colourful</p>
                          </div>
                          {invoiceForm.invoice_template === "modern" && (
                            <CheckCircle2 className="w-5 h-5 text-teal-600 shrink-0" />
                          )}
                        </div>
                      </button>
                    </div>
                  </div>

                  {/* Company Info */}
                  <div className="border-t pt-5 space-y-4">
                    <p className="text-sm font-medium text-slate-700">Company Details on Invoice</p>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Company Name</Label>
                        <Input
                          value={invoiceForm.company_name}
                          onChange={(e) => setInvoiceForm(prev => ({...prev, company_name: e.target.value}))}
                          placeholder="Your Company Ltd."
                          data-testid="inv-company-name"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Company Email</Label>
                        <Input
                          type="email"
                          value={invoiceForm.company_email}
                          onChange={(e) => setInvoiceForm(prev => ({...prev, company_email: e.target.value}))}
                          placeholder="billing@company.com"
                          data-testid="inv-company-email"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Company Phone</Label>
                        <Input
                          value={invoiceForm.company_phone}
                          onChange={(e) => setInvoiceForm(prev => ({...prev, company_phone: e.target.value}))}
                          placeholder="+91 9876543210"
                          data-testid="inv-company-phone"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Company Address</Label>
                      <Textarea
                        value={invoiceForm.company_address}
                        onChange={(e) => setInvoiceForm(prev => ({...prev, company_address: e.target.value}))}
                        placeholder="123 Business Park, City, State - PIN"
                        rows={2}
                        data-testid="inv-company-address"
                      />
                    </div>
                  </div>

                  {/* Branding */}
                  <div className="border-t pt-4 space-y-4">
                    <p className="text-sm font-medium text-slate-700">Branding</p>
                    <div className="space-y-2">
                      <Label>Logo URL</Label>
                      <Input
                        value={invoiceForm.logo_url}
                        onChange={(e) => setInvoiceForm(prev => ({...prev, logo_url: e.target.value}))}
                        placeholder="https://yourcompany.com/logo.png"
                        data-testid="inv-logo-url"
                      />
                      <div className="flex flex-wrap items-center gap-3">
                        <label className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 cursor-pointer hover:bg-slate-50">
                          {logoUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                          {logoUploading ? "Uploading..." : "Upload Logo"}
                          <input
                            type="file"
                            accept=".png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml"
                            className="hidden"
                            onChange={handleInvoiceLogoUpload}
                            disabled={logoUploading || isReadOnly}
                          />
                        </label>
                        <p className="text-xs text-slate-500">Use upload for best PDF compatibility, or paste a direct logo URL.</p>
                      </div>
                      {invoiceForm.logo_url && (
                        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 inline-flex">
                          <img src={invoiceForm.logo_url} alt="Invoice logo preview" className="max-h-12 w-auto" />
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="border-t pt-4 space-y-4">
                    <p className="text-sm font-medium text-slate-700">Visible Fields on Invoice</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        ["show_logo", "Show Logo"],
                        ["show_company_address", "Show Company Address"],
                        ["show_company_phone", "Show Company Phone"],
                        ["show_company_email", "Show Company Email"],
                        ["show_bank_details", "Show Bank Details"],
                        ["show_subscriber_phone", "Show Subscriber Phone"],
                        ["show_subscriber_email", "Show Subscriber Email"],
                        ["show_subscriber_address", "Show Subscriber Address"],
                      ].map(([key, label]) => (
                        <div key={key} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                          <Label className="font-normal">{label}</Label>
                          <Switch
                            checked={invoiceForm.visible_fields?.[key] !== false}
                            onCheckedChange={(checked) => setInvoiceForm(prev => ({
                              ...prev,
                              visible_fields: {
                                ...(prev.visible_fields || {}),
                                [key]: checked,
                              },
                            }))}
                            disabled={isReadOnly}
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Tax & Footer */}
                  <div className="border-t pt-4 space-y-4">
                    <p className="text-sm font-medium text-slate-700">Tax & Footer</p>
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-normal">Show GST on Invoice</Label>
                        <p className="text-xs text-slate-500">Display GST breakdown (CGST + SGST or IGST)</p>
                      </div>
                      <Switch
                        checked={invoiceForm.show_gst}
                        onCheckedChange={(checked) => setInvoiceForm(prev => ({...prev, show_gst: checked}))}
                        data-testid="inv-show-gst"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Invoice Footer</Label>
                      <Input
                        value={invoiceForm.invoice_footer}
                        onChange={(e) => setInvoiceForm(prev => ({...prev, invoice_footer: e.target.value}))}
                        placeholder="Thank you for your business!"
                        data-testid="inv-footer"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Terms & Conditions</Label>
                      <Textarea
                        value={invoiceForm.terms_conditions}
                        onChange={(e) => setInvoiceForm(prev => ({...prev, terms_conditions: e.target.value}))}
                        placeholder="Payment is due within 7 days of invoice date..."
                        rows={3}
                        data-testid="inv-terms"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end pt-4 border-t">
                    <Button type="submit" disabled={isReadOnly || saving} data-testid="save-invoice-btn">
                      <Save className="w-4 h-4 mr-2" />
                      {saving ? "Saving..." : "Save Invoice Settings"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Theme Tab */}
          <TabsContent value="theme">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="w-5 h-5 text-purple-600" />
                  Theme Settings
                </CardTitle>
                <CardDescription>
                  Choose your preferred color theme for the dashboard
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Modern Theme */}
                  <div
                    onClick={() => !themeSaving && handleThemeChange("modern")}
                    className={`cursor-pointer rounded-xl border-2 p-4 transition-all ${
                      currentTheme === "modern" 
                        ? "border-blue-500 bg-blue-50" 
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600" />
                      <div>
                        <p className="font-semibold text-slate-900">Modern</p>
                        <p className="text-xs text-slate-500">Fresh blue theme (Default)</p>
                      </div>
                      {currentTheme === "modern" && (
                        <CheckCircle2 className="w-5 h-5 text-blue-500 ml-auto" />
                      )}
                    </div>
                    <div className="flex gap-2 mt-3">
                      <div className="w-8 h-8 rounded bg-[#3B82F6]" title="Primary" />
                      <div className="w-8 h-8 rounded bg-[#10B981]" title="Secondary" />
                      <div className="w-8 h-8 rounded bg-[#6366F1]" title="Accent" />
                      <div className="w-8 h-8 rounded bg-[#1E293B]" title="Sidebar" />
                    </div>
                  </div>

                  {/* Classic Theme */}
                  <div
                    onClick={() => !themeSaving && handleThemeChange("classic")}
                    className={`cursor-pointer rounded-xl border-2 p-4 transition-all ${
                      currentTheme === "classic" 
                        ? "border-[#0066B2] bg-blue-50" 
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#0066B2] to-[#004080]" />
                      <div>
                        <p className="font-semibold text-slate-900">Classic</p>
                        <p className="text-xs text-slate-500">E-Bill brand colors (Pro)</p>
                      </div>
                      {currentTheme === "classic" && (
                        <CheckCircle2 className="w-5 h-5 text-[#0066B2] ml-auto" />
                      )}
                    </div>
                    <div className="flex gap-2 mt-3">
                      <div className="w-8 h-8 rounded bg-[#0066B2]" title="EB Blue" />
                      <div className="w-8 h-8 rounded bg-[#44AB62]" title="EB Green" />
                      <div className="w-8 h-8 rounded bg-[#004080]" title="EB Deep Blue" />
                      <div className="w-8 h-8 rounded bg-[#EFEFEF] border" title="Cool Gray" />
                    </div>
                  </div>
                </div>

                {themeSaving && (
                  <p className="text-sm text-slate-500 mt-4 flex items-center gap-2">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-600"></span>
                    Saving theme...
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reminders Tab */}
          {hasPaymentReminder && (
            <TabsContent value="reminders">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CalendarClock className="w-5 h-5" />
                    Payment Reminder Schedule
                  </CardTitle>
                  <p className="text-sm text-slate-500">
                    Configure automatic WhatsApp reminders for pending invoices. Reminders run daily at 07:00 UTC.
                  </p>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleReminderSubmit} className="space-y-6">
                    {/* Master toggle */}
                    <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                      <div>
                        <Label className="text-sm font-medium">Enable Auto Reminders</Label>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Automatically send WhatsApp reminders based on your schedule below
                        </p>
                      </div>
                      <Switch
                        checked={reminderForm.enabled}
                        onCheckedChange={(checked) => setReminderForm(prev => ({ ...prev, enabled: checked }))}
                        disabled={isReadOnly}
                        data-testid="reminder-enabled-switch"
                      />
                    </div>

                    {/* Before due date */}
                    <div className={`space-y-3 ${!reminderForm.enabled ? "opacity-50 pointer-events-none" : ""}`}>
                      <div>
                        <p className="text-sm font-medium text-slate-700 flex items-center gap-2">
                          <Clock className="w-4 h-4 text-blue-500" />
                          Before Due Date
                        </p>
                        <p className="text-xs text-slate-500 ml-6">Send a reminder X days before the invoice is due</p>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-6">
                        {[7, 5, 3, 2, 1].map(day => (
                          <button
                            key={`before-${day}`}
                            type="button"
                            onClick={() => toggleBeforeDay(day)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                              reminderForm.remind_before_due.includes(day)
                                ? "bg-blue-50 border-blue-300 text-blue-700"
                                : "bg-white border-slate-200 text-slate-500 hover:border-slate-300"
                            }`}
                            data-testid={`before-due-${day}`}
                          >
                            {day} {day === 1 ? "day" : "days"}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* On due date */}
                    <div className={`${!reminderForm.enabled ? "opacity-50 pointer-events-none" : ""}`}>
                      <div className="flex items-center justify-between p-3 bg-amber-50 border border-amber-100 rounded-lg">
                        <div>
                          <p className="text-sm font-medium text-amber-800 flex items-center gap-2">
                            <Bell className="w-4 h-4" />
                            On Due Date
                          </p>
                          <p className="text-xs text-amber-600 ml-6">Send a reminder on the exact due date</p>
                        </div>
                        <Switch
                          checked={reminderForm.remind_on_due}
                          onCheckedChange={(checked) => setReminderForm(prev => ({ ...prev, remind_on_due: checked }))}
                          disabled={isReadOnly}
                          data-testid="reminder-on-due-switch"
                        />
                      </div>
                    </div>

                    {/* After due date */}
                    <div className={`space-y-3 ${!reminderForm.enabled ? "opacity-50 pointer-events-none" : ""}`}>
                      <div>
                        <p className="text-sm font-medium text-slate-700 flex items-center gap-2">
                          <Clock className="w-4 h-4 text-red-500" />
                          After Due Date (Overdue)
                        </p>
                        <p className="text-xs text-slate-500 ml-6">Send follow-up reminders for overdue invoices</p>
                      </div>
                      <div className="flex flex-wrap gap-2 ml-6">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(day => (
                          <button
                            key={`after-${day}`}
                            type="button"
                            onClick={() => toggleAfterDay(day)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                              reminderForm.remind_after_due.includes(day)
                                ? "bg-red-50 border-red-300 text-red-700"
                                : "bg-white border-slate-200 text-slate-500 hover:border-slate-300"
                            }`}
                            data-testid={`after-due-${day}`}
                          >
                            {day} {day === 1 ? "day" : "days"}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Max reminders */}
                    <div className={`space-y-2 ${!reminderForm.enabled ? "opacity-50 pointer-events-none" : ""}`}>
                      <Label>Max Reminders Per Invoice</Label>
                      <Select
                        value={String(reminderForm.max_reminders_per_invoice)}
                        onValueChange={(val) => setReminderForm(prev => ({ ...prev, max_reminders_per_invoice: parseInt(val) }))}
                        disabled={isReadOnly}
                      >
                        <SelectTrigger className="w-40" data-testid="max-reminders-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {[3, 5, 10, 15, 20].map(n => (
                            <SelectItem key={n} value={String(n)}>{n} reminders</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-slate-500">Stop sending reminders after this count is reached per invoice</p>
                    </div>

                    {/* Summary */}
                    {reminderForm.enabled && (
                      <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                        <p className="text-sm font-medium text-slate-700 mb-2">Schedule Summary</p>
                        <div className="text-xs text-slate-600 space-y-1">
                          {reminderForm.remind_before_due.length > 0 && (
                            <p>
                              Before due: {[...reminderForm.remind_before_due].sort((a, b) => b - a).map(d => `${d}d`).join(", ")} before
                            </p>
                          )}
                          {reminderForm.remind_on_due && <p>On due date</p>}
                          {reminderForm.remind_after_due.length > 0 && (
                            <p>
                              After due: {[...reminderForm.remind_after_due].sort((a, b) => a - b).map(d => `${d}d`).join(", ")} after
                            </p>
                          )}
                          {!reminderForm.remind_before_due.length && !reminderForm.remind_on_due && !reminderForm.remind_after_due.length && (
                            <p className="text-amber-600">No reminder schedule configured yet. Select at least one option above.</p>
                          )}
                          <p className="mt-1 text-slate-500">Max {reminderForm.max_reminders_per_invoice} reminders per invoice</p>
                        </div>
                      </div>
                    )}

                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <p className="text-sm font-medium text-blue-800 mb-1">How it works</p>
                      <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
                        <li>Reminders are processed daily at 07:00 UTC automatically</li>
                        <li>Each invoice tracks how many reminders have been sent</li>
                        <li>Duplicate reminders for the same day are prevented</li>
                        <li>Requires WhatsApp Business API to be configured</li>
                      </ul>
                    </div>

                    <div className="flex justify-end pt-4 border-t">
                      <Button type="submit" disabled={isReadOnly || reminderSaving} data-testid="save-reminder-btn">
                        <Save className="w-4 h-4 mr-2" />
                        {reminderSaving ? "Saving..." : "Save Reminder Settings"}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </OperatorLayout>
  );
};

export default OperatorSettings;
