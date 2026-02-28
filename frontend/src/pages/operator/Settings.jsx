import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
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
  MessageCircle
} from "lucide-react";

const OperatorSettings = () => {
  const { authAxios } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [profile, setProfile] = useState(null);
  const [gatewayConfig, setGatewayConfig] = useState(null);
  const [whatsappConfig, setWhatsappConfig] = useState(null);
  
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

  const [gatewayForm, setGatewayForm] = useState({
    gateway_type: "razorpay",
    api_key: "",
    api_secret: "",
    webhook_secret: ""
  });

  const [whatsappForm, setWhatsappForm] = useState({
    phone_number_id: "",
    access_token: ""
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [dashboardRes, profileRes, gatewayRes, waRes] = await Promise.all([
        authAxios.get("/operator/dashboard"),
        authAxios.get("/operator/profile"),
        authAxios.get("/operator/payment-gateway").catch(() => ({ data: { configured: false } })),
        authAxios.get("/operator/whatsapp-config").catch(() => ({ data: { configured: false } }))
      ]);

      setDashboardStats(dashboardRes.data);
      setProfile(profileRes.data);
      setGatewayConfig(gatewayRes.data);
      setWhatsappConfig(waRes.data);

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

  const handleWhatsAppSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await authAxios.post("/operator/whatsapp-config", whatsappForm);
      toast.success("WhatsApp configured successfully");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to configure WhatsApp");
    } finally {
      setSaving(false);
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

  return (
    <OperatorLayout title="Settings" isReadOnly={isReadOnly}>
      <div className="max-w-4xl animate-fade-in">
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList>
            <TabsTrigger value="profile" data-testid="tab-profile">
              <Building2 className="w-4 h-4 mr-2" />
              Business Profile
            </TabsTrigger>
            <TabsTrigger value="payment" data-testid="tab-payment">
              <CreditCard className="w-4 h-4 mr-2" />
              Payment Gateway
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
                      onCheckedChange={(checked) => setProfileForm(prev => ({ ...prev, charge_gst: checked }))}
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
        </Tabs>
      </div>
    </OperatorLayout>
  );
};

export default OperatorSettings;
