import { useState, useEffect, useRef, useCallback } from "react";
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
import { resolveMediaUrl } from "../../lib/mediaUrl";
import { 
  Building2, 
  Save,
  FileText,
  CheckCircle2,
  LayoutTemplate,
  Clock,
  CalendarClock,
  Palette,
  Loader2,
  Upload,
  Database,
  MessageCircle,
  QrCode,
  Wifi,
  WifiOff,
  RefreshCw,
  LogOut,
  Smartphone,
  AlertCircle,
} from "lucide-react";

const OperatorSettings = () => {
  const { authAxios, clearBrowserCache } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [logoUploading, setLogoUploading] = useState(false);
  const [cacheClearing, setCacheClearing] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);

  // Theme state
  const [currentTheme, setCurrentTheme] = useState("modern");
  const [themeSaving, setThemeSaving] = useState(false);

  // WhatsApp WebJS state
  const [waWebStatus, setWaWebStatus] = useState("disconnected");
  const [waWebQr, setWaWebQr] = useState(null);
  const [waWebLoading, setWaWebLoading] = useState(false);
  const [waWebInitializing, setWaWebInitializing] = useState(false);
  const [waWebDisconnecting, setWaWebDisconnecting] = useState(false);
  const qrPollRef = useRef(null);
  
  const [profileForm, setProfileForm] = useState({
    company_name: "",
    owner_name: "",
    phone: "",
    gst_number: "",
    charge_gst: false,
    bank_account_name: "",
    bank_account_number: "",
    bank_ifsc: "",
    bank_name: "",
    upi_id: ""
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
    accept_payment_gateway: true,
    accept_upi: false,
    terms_conditions: "",
    invoice_template: "classic",
    visible_fields: {
      show_logo: false,
      show_company_address: true,
      show_company_phone: true,
      show_company_email: true,
      show_bank_details: true,
      show_subscriber_phone: true,
      show_subscriber_email: true,
      show_subscriber_address: true,
    },
  });

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchData = async () => {
    try {
      const promises = [
        authAxios.get("/operator/dashboard"),
        authAxios.get("/operator/profile"),
        authAxios.get("/operator/invoice-settings").catch(() => ({ data: {} })),
        authAxios.get("/operator/theme-settings").catch(() => ({ data: { theme: "modern" } })),
      ];
      const [dashboardRes, profileRes, invoiceRes, themeRes] = await Promise.all(promises);

      setDashboardStats(dashboardRes.data);
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
        bank_name: profileRes.data.bank_name || "",
        upi_id: profileRes.data.upi_id || ""
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
        accept_payment_gateway: invoiceRes.data.accept_payment_gateway !== false,
        accept_upi: invoiceRes.data.accept_upi === true,
        terms_conditions: invoiceRes.data.terms_conditions || "",
        invoice_template: invoiceRes.data.invoice_template || "classic",
        visible_fields: {
          show_logo: false,
          show_company_address: invoiceRes.data.visible_fields?.show_company_address !== false,
          show_company_phone: invoiceRes.data.visible_fields?.show_company_phone !== false,
          show_company_email: invoiceRes.data.visible_fields?.show_company_email !== false,
          show_bank_details: invoiceRes.data.visible_fields?.show_bank_details !== false,
          show_subscriber_phone: invoiceRes.data.visible_fields?.show_subscriber_phone !== false,
          show_subscriber_email: invoiceRes.data.visible_fields?.show_subscriber_email !== false,
          show_subscriber_address: invoiceRes.data.visible_fields?.show_subscriber_address !== false,
        },
      });
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

  // ─── WhatsApp WebJS Functions ────────────────────────────────────────────
  const fetchWaWebStatus = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/whatsapp-webjs/status");
      setWaWebStatus(res.data.status || "disconnected");
      return res.data;
    } catch (error) {
      setWaWebStatus("error");
      return null;
    }
  }, [authAxios]);

  const fetchWaWebQr = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/whatsapp-webjs/qr");
      if (res.data.qr) {
        setWaWebQr(res.data.qr);
      }
      if (res.data.status) {
        setWaWebStatus(res.data.status);
      }
      return res.data;
    } catch (error) {
      console.error("Failed to fetch QR:", error);
      return null;
    }
  }, [authAxios]);

  const startQrPolling = useCallback(() => {
    // Clear existing interval
    if (qrPollRef.current) {
      clearInterval(qrPollRef.current);
    }

    // Give Chromium ~5s to spin up before the first poll
    const startPolling = () => {
      qrPollRef.current = setInterval(async () => {
        const data = await fetchWaWebQr();
        if (data?.status === "ready") {
          // Connected! Stop polling
          clearInterval(qrPollRef.current);
          qrPollRef.current = null;
          setWaWebQr(null);
          toast.success("WhatsApp connected successfully!");
        } else if (data?.status === "error" || data?.status === "auth_failed") {
          // Failed — stop polling and show error
          clearInterval(qrPollRef.current);
          qrPollRef.current = null;
          setWaWebStatus(data.status);
          toast.error(data.error || "WhatsApp connection failed. Please try again.");
        }
      }, 4000); // Poll every 4 seconds
    };

    // Wait 5 seconds initially so Chromium has time to launch
    setTimeout(startPolling, 5000);
  }, [fetchWaWebQr]);

  const stopQrPolling = useCallback(() => {
    if (qrPollRef.current) {
      clearInterval(qrPollRef.current);
      qrPollRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopQrPolling();
  }, [stopQrPolling]);

  const handleConnectWhatsApp = async () => {
    setWaWebInitializing(true);
    setWaWebQr(null);
    try {
      const res = await authAxios.post("/operator/whatsapp-webjs/init");
      if (res.data.status === "already_ready") {
        setWaWebStatus("ready");
        toast.success("WhatsApp is already connected!");
      } else {
        setWaWebStatus("initializing");
        // Start polling for QR code after a short delay
        startQrPolling();
        toast.info("Starting WhatsApp... QR code may take 20-40 seconds to appear on first launch.");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to initialize WhatsApp");
      setWaWebStatus("error");
    } finally {
      setWaWebInitializing(false);
    }
  };

  const handleDisconnectWhatsApp = async () => {
    setWaWebDisconnecting(true);
    stopQrPolling();
    try {
      await authAxios.post("/operator/whatsapp-webjs/disconnect");
      setWaWebStatus("disconnected");
      setWaWebQr(null);
      toast.success("WhatsApp disconnected successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to disconnect WhatsApp");
    } finally {
      setWaWebDisconnecting(false);
    }
  };

  const handleRefreshStatus = async () => {
    setWaWebLoading(true);
    await fetchWaWebStatus();
    setWaWebLoading(false);
  };

  // Fetch WhatsApp status on mount
  useEffect(() => {
    fetchWaWebStatus();
  }, [fetchWaWebStatus]);

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
  return (
    <OperatorLayout title="Settings" isReadOnly={isReadOnly}>
      <div className="max-w-4xl animate-fade-in">
        <Card className="mb-6 border-amber-200 bg-amber-50/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="w-5 h-5 text-amber-700" />
              Browser Cache
            </CardTitle>
            <CardDescription>
              Clear stale dashboard data stored in this browser. Login now also clears the app cache automatically.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={handleClearBrowserCache} disabled={cacheClearing}>
              {cacheClearing ? "Clearing..." : "Clear Browser Cache"}
            </Button>
          </CardContent>
        </Card>
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList>
            <TabsTrigger value="profile" data-testid="tab-profile">
              <Building2 className="w-4 h-4 mr-2" />
              Business Profile
            </TabsTrigger>
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

                      <div className="space-y-2">
                        <Label>UPI ID</Label>
                        <Input
                          value={profileForm.upi_id}
                          onChange={(e) => setProfileForm(prev => ({ ...prev, upi_id: e.target.value }))}
                          placeholder="e.g. yourname@upi"
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
                        <label className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm font-medium text-slate-500 cursor-not-allowed opacity-50">
                          {logoUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                          {logoUploading ? "Uploading..." : "Upload Logo"}
                          <input
                            type="file"
                            accept=".png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml"
                            className="hidden"
                            onChange={handleInvoiceLogoUpload}
                            disabled={true}
                          />
                        </label>
                        <p className="text-xs text-slate-500">Use upload for best PDF compatibility, or paste a direct logo URL.</p>
                      </div>
                      {invoiceForm.logo_url && (
                        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 inline-flex">
                          <img src={resolveMediaUrl(invoiceForm.logo_url)} alt="Invoice logo preview" className="max-h-12 w-auto" />
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
                            checked={key === "show_logo" ? false : invoiceForm.visible_fields?.[key] !== false}
                            onCheckedChange={(checked) => setInvoiceForm(prev => ({
                              ...prev,
                              visible_fields: {
                                ...(prev.visible_fields || {}),
                                [key]: checked,
                              },
                            }))}
                            disabled={key === "show_logo" || isReadOnly}
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
                    <div className="space-y-4 pt-4 border-t">
                      <p className="text-sm font-medium text-slate-700">Payment Options</p>
                      <div className="space-y-2">
                        <Label>Accepted Payment Methods on Invoice</Label>
                        <Select
                          value={
                            invoiceForm.accept_payment_gateway && invoiceForm.accept_upi ? "both" 
                            : invoiceForm.accept_payment_gateway ? "gateway" 
                            : invoiceForm.accept_upi ? "upi" 
                            : "none"
                          }
                          onValueChange={(val) => {
                            if ((val === "upi" || val === "both") && !profileForm.upi_id?.trim()) {
                              toast.error("Please add your UPI ID in Business Profile first");
                              return;
                            }
                            setInvoiceForm(prev => ({
                              ...prev,
                              accept_payment_gateway: val === "gateway" || val === "both",
                              accept_upi: val === "upi" || val === "both"
                            }));
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select Payment Methods" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="both">Both (Payment Gateway & UPI App)</SelectItem>
                            <SelectItem value="gateway">Payment Gateway Only</SelectItem>
                            <SelectItem value="upi">UPI App Only</SelectItem>
                            <SelectItem value="none">Do not accept payments online</SelectItem>
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-slate-500">
                          Configure which "Pay Now" options are visible to subscribers on their invoice.
                        </p>
                      </div>
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

        </Tabs>
      </div>
    </OperatorLayout>
  );
};

export default OperatorSettings;
