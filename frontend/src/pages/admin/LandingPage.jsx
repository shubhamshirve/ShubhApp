import { useState, useEffect, useRef } from "react";
import { useAuth, API } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { toast } from "sonner";
import {
  Palette,
  Type,
  Layout,
  BarChart3,
  Phone,
  Save,
  RefreshCw,
  Eye,
  ExternalLink,
  Image,
  Loader2,
  Upload,
  Link2,
  Plus,
  Trash2,
  GripVertical
} from "lucide-react";

const ICON_OPTIONS = [
  "Users", "FileText", "CreditCard", "MessageCircle", "Receipt", "BarChart3",
  "Bell", "Shield", "Zap", "IndianRupee", "Clock", "Building2", "Wifi",
  "TrendingUp", "Phone",
];

const AdminLandingPage = () => {
  const { authAxios } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const defaultSettings = {
    brand: {
      name: "E-Bill",
      tagline: "ISP & Cable Billing Solutions",
      business_name: "Teasy Services",
      logo_url: "/ebill-logo.svg",
    },
    colors: {
      primary: "#0066B2",
      secondary: "#44AB62",
      background: "#EFEFEF",
      accent: "#004080",
    },
    hero: {
      badge: "India's GST-Ready Billing Platform",
      title: "Automate Your",
      title_highlight: "Recurring Billing",
      subtitle: "Multi-tenant billing platform for subscription businesses in India. Auto-generate invoices, send WhatsApp reminders, and collect payments through your own payment gateway.",
      cta_primary: "Start Free Trial",
      cta_primary_link: "/register",
      cta_secondary: "Watch Demo",
      cta_secondary_link: "#features",
      features: ["No credit card required", "GST compliant invoices", "WhatsApp integration"],
    },
    stats: {
      stat1_value: "10K+",
      stat1_label: "Active Subscribers",
      stat2_value: "₹5Cr+",
      stat2_label: "Processed Monthly",
      stat3_value: "500+",
      stat3_label: "Businesses Trust Us",
      stat4_value: "99.9%",
      stat4_label: "Uptime",
    },
    features: {
      title: "Everything You Need to Manage Billing",
      subtitle: "A complete solution for subscription businesses with GST compliance, automated workflows, and seamless payment collection.",
      items: [
        { icon: "Users", title: "Subscriber Management", description: "Efficiently manage your subscribers with billing dates, plans, and discounts." },
        { icon: "FileText", title: "Auto Invoice Generation", description: "Invoices are automatically generated 5 days before billing date." },
        { icon: "CreditCard", title: "Razorpay Integration", description: "Accept payments via UPI, cards, netbanking with your own gateway." },
        { icon: "MessageCircle", title: "WhatsApp Notifications", description: "Send invoices and reminders directly to customer's WhatsApp." },
        { icon: "Receipt", title: "GST Compliant", description: "Full GST support with CGST/SGST calculations and tax invoices." },
        { icon: "BarChart3", title: "Reports & Analytics", description: "Track revenue, GST collected, pending payments, and more." },
      ],
    },
    contact: {
      email: "support@teasyservices.com",
      phone: "+91 98765 43210",
      whatsapp: "+91 98765 43210",
    },
    footer: {
      copyright: "© 2026 E-Bill by Teasy Services. All rights reserved.",
      tagline: "Made in India 🇮🇳",
    },
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await authAxios.get("/admin/landing-page");
      setSettings(res.data);
    } catch (err) {
      setSettings(defaultSettings);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await authAxios.put("/admin/landing-page", settings);
      toast.success("Landing page settings saved successfully!");
    } catch (err) {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setSettings(defaultSettings);
    toast.info("Settings reset to defaults (not saved yet)");
  };

  const updateNestedState = (section, field, value) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }));
  };

  const updateFeaturesList = (value) => {
    const features = value.split(",").map(f => f.trim()).filter(f => f);
    updateNestedState("hero", "features", features);
  };

  // Feature items management
  const addFeatureItem = () => {
    const items = settings?.features?.items || [];
    if (items.length >= 12) { toast.error("Maximum 12 features allowed"); return; }
    setSettings(prev => ({
      ...prev,
      features: {
        ...prev.features,
        items: [...(prev.features?.items || []), { icon: "Zap", title: "", description: "" }]
      }
    }));
  };

  const removeFeatureItem = (index) => {
    setSettings(prev => ({
      ...prev,
      features: {
        ...prev.features,
        items: (prev.features?.items || []).filter((_, i) => i !== index)
      }
    }));
  };

  const updateFeatureItem = (index, field, value) => {
    setSettings(prev => {
      const items = [...(prev.features?.items || [])];
      items[index] = { ...items[index], [field]: value };
      return { ...prev, features: { ...prev.features, items } };
    });
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml'];
    if (!allowedTypes.includes(file.type)) {
      toast.error("Please upload a PNG, JPG, or SVG image");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error("File size must be less than 5MB");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await authAxios.post('/admin/upload-logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      updateNestedState("brand", "logo_url", res.data.url);
      toast.success("Logo uploaded successfully!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload logo");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  if (loading) {
    return (
      <AdminLayout title="Landing Page">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Landing Page">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Layout className="w-6 h-6 text-indigo-600" />
              Landing Page Settings
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Customize your landing page content, colors, and branding
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => window.open("/", "_blank")}
              className="gap-2"
            >
              <Eye className="w-4 h-4" />
              Preview
              <ExternalLink className="w-3 h-3" />
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              className="gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reset
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving}
              className="gap-2 bg-indigo-600 hover:bg-indigo-700"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Changes
            </Button>
          </div>
        </div>

        <Tabs defaultValue="brand" className="space-y-6">
          <TabsList className="bg-slate-100">
            <TabsTrigger value="brand" className="gap-2">
              <Image className="w-4 h-4" />
              Brand
            </TabsTrigger>
            <TabsTrigger value="colors" className="gap-2">
              <Palette className="w-4 h-4" />
              Colors
            </TabsTrigger>
            <TabsTrigger value="hero" className="gap-2">
              <Type className="w-4 h-4" />
              Hero Section
            </TabsTrigger>
            <TabsTrigger value="stats" className="gap-2">
              <BarChart3 className="w-4 h-4" />
              Stats
            </TabsTrigger>
            <TabsTrigger value="contact" className="gap-2">
              <Phone className="w-4 h-4" />
              Contact
            </TabsTrigger>
          </TabsList>

          {/* Brand Tab */}
          <TabsContent value="brand">
            <Card>
              <CardHeader>
                <CardTitle>Brand Settings</CardTitle>
                <CardDescription>Configure your brand name, logo, and business details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="brand-name">Brand Name</Label>
                    <Input
                      id="brand-name"
                      value={settings?.brand?.name || ""}
                      onChange={(e) => updateNestedState("brand", "name", e.target.value)}
                      placeholder="E-Bill"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="brand-tagline">Tagline</Label>
                    <Input
                      id="brand-tagline"
                      value={settings?.brand?.tagline || ""}
                      onChange={(e) => updateNestedState("brand", "tagline", e.target.value)}
                      placeholder="ISP & Cable Billing Solutions"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="business-name">Business Name</Label>
                    <Input
                      id="business-name"
                      value={settings?.brand?.business_name || ""}
                      onChange={(e) => updateNestedState("brand", "business_name", e.target.value)}
                      placeholder="Teasy Services"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="logo-url">Logo URL</Label>
                    <Input
                      id="logo-url"
                      value={settings?.brand?.logo_url || ""}
                      onChange={(e) => updateNestedState("brand", "logo_url", e.target.value)}
                      placeholder="/ebill-logo.svg"
                    />
                    <p className="text-xs text-slate-500">Path to logo image or external URL</p>
                  </div>
                </div>
                
                {/* Logo Upload */}
                <div className="border-t pt-4">
                  <Label className="mb-2 block">Upload New Logo</Label>
                  <div className="flex items-center gap-4">
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept=".png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml"
                      onChange={handleLogoUpload}
                      className="hidden"
                      id="logo-upload"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      className="gap-2"
                    >
                      {uploading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Upload className="w-4 h-4" />
                      )}
                      {uploading ? "Uploading..." : "Choose File"}
                    </Button>
                    <p className="text-xs text-slate-500">PNG, JPG, or SVG (max 5MB)</p>
                  </div>
                </div>

                {/* Logo Preview */}
                {settings?.brand?.logo_url && (
                  <div className="mt-4 p-4 bg-slate-50 rounded-lg">
                    <p className="text-sm font-medium text-slate-700 mb-2">Logo Preview</p>
                    <img 
                      src={settings.brand.logo_url} 
                      alt="Logo Preview" 
                      className="h-16 object-contain"
                      onError={(e) => e.target.style.display = 'none'}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Colors Tab */}
          <TabsContent value="colors">
            <Card>
              <CardHeader>
                <CardTitle>Color Palette</CardTitle>
                <CardDescription>Customize the colors used throughout your landing page</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="color-primary">Primary (EB Blue)</Label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={settings?.colors?.primary || "#0066B2"}
                        onChange={(e) => updateNestedState("colors", "primary", e.target.value)}
                        className="w-12 h-10 rounded border border-slate-300 cursor-pointer"
                      />
                      <Input
                        id="color-primary"
                        value={settings?.colors?.primary || ""}
                        onChange={(e) => updateNestedState("colors", "primary", e.target.value)}
                        placeholder="#0066B2"
                        className="font-mono"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="color-secondary">Secondary (EB Green)</Label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={settings?.colors?.secondary || "#44AB62"}
                        onChange={(e) => updateNestedState("colors", "secondary", e.target.value)}
                        className="w-12 h-10 rounded border border-slate-300 cursor-pointer"
                      />
                      <Input
                        id="color-secondary"
                        value={settings?.colors?.secondary || ""}
                        onChange={(e) => updateNestedState("colors", "secondary", e.target.value)}
                        placeholder="#44AB62"
                        className="font-mono"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="color-background">Background (Cool Gray)</Label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={settings?.colors?.background || "#EFEFEF"}
                        onChange={(e) => updateNestedState("colors", "background", e.target.value)}
                        className="w-12 h-10 rounded border border-slate-300 cursor-pointer"
                      />
                      <Input
                        id="color-background"
                        value={settings?.colors?.background || ""}
                        onChange={(e) => updateNestedState("colors", "background", e.target.value)}
                        placeholder="#EFEFEF"
                        className="font-mono"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="color-accent">Accent (EB Deep Blue)</Label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={settings?.colors?.accent || "#004080"}
                        onChange={(e) => updateNestedState("colors", "accent", e.target.value)}
                        className="w-12 h-10 rounded border border-slate-300 cursor-pointer"
                      />
                      <Input
                        id="color-accent"
                        value={settings?.colors?.accent || ""}
                        onChange={(e) => updateNestedState("colors", "accent", e.target.value)}
                        placeholder="#004080"
                        className="font-mono"
                      />
                    </div>
                  </div>
                </div>
                
                {/* Color Preview */}
                <div className="mt-6 p-4 bg-slate-50 rounded-lg">
                  <p className="text-sm font-medium text-slate-700 mb-3">Color Preview</p>
                  <div className="flex gap-4">
                    <div className="text-center">
                      <div 
                        className="w-16 h-16 rounded-lg shadow-sm"
                        style={{ backgroundColor: settings?.colors?.primary }}
                      />
                      <p className="text-xs text-slate-500 mt-1">Primary</p>
                    </div>
                    <div className="text-center">
                      <div 
                        className="w-16 h-16 rounded-lg shadow-sm"
                        style={{ backgroundColor: settings?.colors?.secondary }}
                      />
                      <p className="text-xs text-slate-500 mt-1">Secondary</p>
                    </div>
                    <div className="text-center">
                      <div 
                        className="w-16 h-16 rounded-lg shadow-sm border"
                        style={{ backgroundColor: settings?.colors?.background }}
                      />
                      <p className="text-xs text-slate-500 mt-1">Background</p>
                    </div>
                    <div className="text-center">
                      <div 
                        className="w-16 h-16 rounded-lg shadow-sm"
                        style={{ backgroundColor: settings?.colors?.accent }}
                      />
                      <p className="text-xs text-slate-500 mt-1">Accent</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Hero Tab */}
          <TabsContent value="hero">
            <Card>
              <CardHeader>
                <CardTitle>Hero Section</CardTitle>
                <CardDescription>Customize the main hero section of your landing page</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="hero-badge">Badge Text</Label>
                    <Input
                      id="hero-badge"
                      value={settings?.hero?.badge || ""}
                      onChange={(e) => updateNestedState("hero", "badge", e.target.value)}
                      placeholder="India's GST-Ready Billing Platform"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hero-title">Title</Label>
                    <Input
                      id="hero-title"
                      value={settings?.hero?.title || ""}
                      onChange={(e) => updateNestedState("hero", "title", e.target.value)}
                      placeholder="Automate Your"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hero-highlight">Title Highlight (Second Line)</Label>
                    <Input
                      id="hero-highlight"
                      value={settings?.hero?.title_highlight || ""}
                      onChange={(e) => updateNestedState("hero", "title_highlight", e.target.value)}
                      placeholder="Recurring Billing"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hero-cta-primary">Primary CTA Button</Label>
                    <Input
                      id="hero-cta-primary"
                      value={settings?.hero?.cta_primary || ""}
                      onChange={(e) => updateNestedState("hero", "cta_primary", e.target.value)}
                      placeholder="Start Free Trial"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hero-cta-primary-link">Primary CTA Link</Label>
                    <div className="flex items-center gap-2">
                      <Link2 className="w-4 h-4 text-slate-400" />
                      <Input
                        id="hero-cta-primary-link"
                        value={settings?.hero?.cta_primary_link || ""}
                        onChange={(e) => updateNestedState("hero", "cta_primary_link", e.target.value)}
                        placeholder="/register"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hero-cta-secondary">Secondary CTA Button</Label>
                    <Input
                      id="hero-cta-secondary"
                      value={settings?.hero?.cta_secondary || ""}
                      onChange={(e) => updateNestedState("hero", "cta_secondary", e.target.value)}
                      placeholder="Watch Demo"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hero-cta-secondary-link">Secondary CTA Link</Label>
                    <div className="flex items-center gap-2">
                      <Link2 className="w-4 h-4 text-slate-400" />
                      <Input
                        id="hero-cta-secondary-link"
                        value={settings?.hero?.cta_secondary_link || ""}
                        onChange={(e) => updateNestedState("hero", "cta_secondary_link", e.target.value)}
                        placeholder="#features"
                      />
                    </div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="hero-subtitle">Subtitle</Label>
                  <textarea
                    id="hero-subtitle"
                    value={settings?.hero?.subtitle || ""}
                    onChange={(e) => updateNestedState("hero", "subtitle", e.target.value)}
                    placeholder="Multi-tenant billing platform for subscription businesses..."
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    rows={3}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="hero-features">Feature Bullets (comma separated)</Label>
                  <Input
                    id="hero-features"
                    value={settings?.hero?.features?.join(", ") || ""}
                    onChange={(e) => updateFeaturesList(e.target.value)}
                    placeholder="No credit card required, GST compliant invoices, WhatsApp integration"
                  />
                  <p className="text-xs text-slate-500">Separate each feature with a comma</p>
                </div>
              </CardContent>
            </Card>
            
            {/* Features Section Title */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Features Section</CardTitle>
                <CardDescription>Customize the features section heading and individual feature cards</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="features-title">Section Title</Label>
                  <Input
                    id="features-title"
                    value={settings?.features?.title || ""}
                    onChange={(e) => updateNestedState("features", "title", e.target.value)}
                    placeholder="Everything You Need to Manage Billing"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="features-subtitle">Section Subtitle</Label>
                  <textarea
                    id="features-subtitle"
                    value={settings?.features?.subtitle || ""}
                    onChange={(e) => updateNestedState("features", "subtitle", e.target.value)}
                    placeholder="A complete solution for subscription businesses..."
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    rows={2}
                  />
                </div>

                {/* Feature Items */}
                <div className="pt-4 border-t border-slate-200">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="font-medium text-slate-800">Feature Cards</p>
                      <p className="text-xs text-slate-500">{(settings?.features?.items || []).length} of 12 features</p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addFeatureItem}
                      disabled={(settings?.features?.items || []).length >= 12}
                      className="gap-1"
                    >
                      <Plus className="w-4 h-4" /> Add Feature
                    </Button>
                  </div>

                  <div className="space-y-4">
                    {(settings?.features?.items || []).map((item, idx) => (
                      <div key={idx} className="flex gap-3 p-4 bg-slate-50 rounded-lg border border-slate-200">
                        <div className="flex items-start pt-1 text-slate-400">
                          <GripVertical className="w-4 h-4" />
                        </div>
                        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-3">
                          {/* Icon selector */}
                          <div className="md:col-span-2 space-y-1">
                            <Label className="text-xs">Icon</Label>
                            <select
                              value={item.icon || "Zap"}
                              onChange={(e) => updateFeatureItem(idx, "icon", e.target.value)}
                              className="w-full px-2 py-2 text-sm border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
                            >
                              {ICON_OPTIONS.map(icon => (
                                <option key={icon} value={icon}>{icon}</option>
                              ))}
                            </select>
                          </div>
                          {/* Title */}
                          <div className="md:col-span-4 space-y-1">
                            <Label className="text-xs">Title</Label>
                            <Input
                              value={item.title || ""}
                              onChange={(e) => updateFeatureItem(idx, "title", e.target.value)}
                              placeholder="Feature title"
                            />
                          </div>
                          {/* Description */}
                          <div className="md:col-span-6 space-y-1">
                            <Label className="text-xs">Description</Label>
                            <Input
                              value={item.description || ""}
                              onChange={(e) => updateFeatureItem(idx, "description", e.target.value)}
                              placeholder="Feature description..."
                            />
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFeatureItem(idx)}
                          className="text-red-500 hover:text-red-700 hover:bg-red-50 self-center"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                    {(!settings?.features?.items || settings.features.items.length === 0) && (
                      <div className="text-center py-8 text-slate-400">
                        <p className="text-sm">No features configured. Click "Add Feature" to start.</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Stats Tab */}
          <TabsContent value="stats">
            <Card>
              <CardHeader>
                <CardTitle>Statistics Section</CardTitle>
                <CardDescription>Showcase your platform's achievements</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                    <p className="font-medium text-slate-700">Stat 1</p>
                    <div className="space-y-2">
                      <Label htmlFor="stat1-value">Value</Label>
                      <Input
                        id="stat1-value"
                        value={settings?.stats?.stat1_value || ""}
                        onChange={(e) => updateNestedState("stats", "stat1_value", e.target.value)}
                        placeholder="10K+"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="stat1-label">Label</Label>
                      <Input
                        id="stat1-label"
                        value={settings?.stats?.stat1_label || ""}
                        onChange={(e) => updateNestedState("stats", "stat1_label", e.target.value)}
                        placeholder="Active Subscribers"
                      />
                    </div>
                  </div>
                  
                  <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                    <p className="font-medium text-slate-700">Stat 2</p>
                    <div className="space-y-2">
                      <Label htmlFor="stat2-value">Value</Label>
                      <Input
                        id="stat2-value"
                        value={settings?.stats?.stat2_value || ""}
                        onChange={(e) => updateNestedState("stats", "stat2_value", e.target.value)}
                        placeholder="₹5Cr+"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="stat2-label">Label</Label>
                      <Input
                        id="stat2-label"
                        value={settings?.stats?.stat2_label || ""}
                        onChange={(e) => updateNestedState("stats", "stat2_label", e.target.value)}
                        placeholder="Processed Monthly"
                      />
                    </div>
                  </div>
                  
                  <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                    <p className="font-medium text-slate-700">Stat 3</p>
                    <div className="space-y-2">
                      <Label htmlFor="stat3-value">Value</Label>
                      <Input
                        id="stat3-value"
                        value={settings?.stats?.stat3_value || ""}
                        onChange={(e) => updateNestedState("stats", "stat3_value", e.target.value)}
                        placeholder="500+"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="stat3-label">Label</Label>
                      <Input
                        id="stat3-label"
                        value={settings?.stats?.stat3_label || ""}
                        onChange={(e) => updateNestedState("stats", "stat3_label", e.target.value)}
                        placeholder="Businesses Trust Us"
                      />
                    </div>
                  </div>
                  
                  <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                    <p className="font-medium text-slate-700">Stat 4</p>
                    <div className="space-y-2">
                      <Label htmlFor="stat4-value">Value</Label>
                      <Input
                        id="stat4-value"
                        value={settings?.stats?.stat4_value || ""}
                        onChange={(e) => updateNestedState("stats", "stat4_value", e.target.value)}
                        placeholder="99.9%"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="stat4-label">Label</Label>
                      <Input
                        id="stat4-label"
                        value={settings?.stats?.stat4_label || ""}
                        onChange={(e) => updateNestedState("stats", "stat4_label", e.target.value)}
                        placeholder="Uptime"
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Contact Tab */}
          <TabsContent value="contact">
            <Card>
              <CardHeader>
                <CardTitle>Contact Information</CardTitle>
                <CardDescription>Update your contact details displayed on the landing page</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="contact-email">Email</Label>
                    <Input
                      id="contact-email"
                      type="email"
                      value={settings?.contact?.email || ""}
                      onChange={(e) => updateNestedState("contact", "email", e.target.value)}
                      placeholder="support@teasyservices.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-phone">Phone</Label>
                    <Input
                      id="contact-phone"
                      value={settings?.contact?.phone || ""}
                      onChange={(e) => updateNestedState("contact", "phone", e.target.value)}
                      placeholder="+91 98765 43210"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-whatsapp">WhatsApp</Label>
                    <Input
                      id="contact-whatsapp"
                      value={settings?.contact?.whatsapp || ""}
                      onChange={(e) => updateNestedState("contact", "whatsapp", e.target.value)}
                      placeholder="+91 98765 43210"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Footer Settings */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Footer</CardTitle>
                <CardDescription>Customize the footer text</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="footer-copyright">Copyright Text</Label>
                    <Input
                      id="footer-copyright"
                      value={settings?.footer?.copyright || ""}
                      onChange={(e) => updateNestedState("footer", "copyright", e.target.value)}
                      placeholder="© 2026 E-Bill by Teasy Services. All rights reserved."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="footer-tagline">Footer Tagline</Label>
                    <Input
                      id="footer-tagline"
                      value={settings?.footer?.tagline || ""}
                      onChange={(e) => updateNestedState("footer", "tagline", e.target.value)}
                      placeholder="Made in India 🇮🇳"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
};

export default AdminLandingPage;
