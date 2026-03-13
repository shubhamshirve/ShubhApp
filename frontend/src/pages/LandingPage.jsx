import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import {
  Check,
  ArrowRight,
  Users,
  FileText,
  CreditCard,
  Bell,
  BarChart3,
  Shield,
  Zap,
  IndianRupee,
  ChevronRight,
  Phone,
  Mail,
  MapPin,
  MessageCircle,
  Clock,
  Receipt,
  Building2,
  Wifi,
  TrendingUp,
  Menu,
  X
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

const LandingPage = () => {
  const [selectedPlan, setSelectedPlan] = useState("professional");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await axios.get(`${API}/landing-page`);
      setSettings(res.data);
    } catch (err) {
      // Use default settings if fetch fails
      setSettings(null);
    } finally {
      setLoading(false);
    }
  };

  // Default settings
  const defaults = {
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
      cta_secondary: "Watch Demo",
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

  // Merge settings with defaults
  const s = settings || defaults;
  const brand = { ...defaults.brand, ...(s.brand || {}) };
  const colors = { ...defaults.colors, ...(s.colors || {}) };
  const hero = { ...defaults.hero, ...(s.hero || {}) };
  const stats = { ...defaults.stats, ...(s.stats || {}) };
  const featuresSection = { ...defaults.features, ...(s.features || {}) };
  const contact = { ...defaults.contact, ...(s.contact || {}) };
  const footer = { ...defaults.footer, ...(s.footer || {}) };

  const features = [
    {
      icon: Users,
      title: "Subscriber Management",
      description: "Efficiently manage your subscribers with billing dates, plans, and discounts."
    },
    {
      icon: FileText,
      title: "Auto Invoice Generation",
      description: "Invoices are automatically generated 5 days before billing date."
    },
    {
      icon: CreditCard,
      title: "Razorpay Integration",
      description: "Accept payments via UPI, cards, netbanking with your own gateway."
    },
    {
      icon: MessageCircle,
      title: "WhatsApp Notifications",
      description: "Send invoices and reminders directly to customer's WhatsApp."
    },
    {
      icon: Receipt,
      title: "GST Compliant",
      description: "Full GST support with CGST/SGST calculations and tax invoices."
    },
    {
      icon: BarChart3,
      title: "Reports & Analytics",
      description: "Track revenue, GST collected, pending payments, and more."
    }
  ];

  const plans = [
    {
      id: "basic",
      name: "Basic",
      price: 500,
      period: "/month",
      description: "For small ISPs",
      features: [
        "200 subscribers",
        "Basic invoicing",
        "Manual reminders",
        "Email support"
      ],
      highlighted: false,
      cta: "Get Started"
    },
    {
      id: "pro",
      name: "Pro",
      price: 2500,
      period: "/month",
      description: "Most popular choice",
      features: [
        "1000 subscribers",
        "5 staff members",
        "Auto notifications",
        "WhatsApp reminders",
        "Priority support"
      ],
      highlighted: true,
      cta: "Get Started"
    }
  ];

  const steps = [
    {
      number: "01",
      title: "Register Your Business",
      description: "Sign up with your business details and start your free trial instantly."
    },
    {
      number: "02",
      title: "Add Your Subscribers",
      description: "Import or add subscribers with their billing dates and service plans."
    },
    {
      number: "03",
      title: "Set Up Payment Gateway",
      description: "Connect your Razorpay account to start accepting payments."
    },
    {
      number: "04",
      title: "Automate & Relax",
      description: "Invoices, reminders, and collection happen automatically."
    }
  ];

  // Custom CSS variables for E-Bill colors
  const customStyles = {
    '--eb-blue': colors.primary,
    '--eb-green': colors.secondary,
    '--eb-gray': colors.background,
    '--eb-deep-blue': colors.accent,
  };

  return (
    <div className="min-h-screen bg-white" style={customStyles}>
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <img 
                src={brand.logo_url} 
                alt={brand.name} 
                className="w-12 h-12 object-contain"
              />
              <div className="flex flex-col">
                <span className="font-bold text-xl" style={{ color: colors.primary }}>
                  {brand.name}
                </span>
                <span className="text-xs text-slate-500 hidden sm:block">{brand.tagline}</span>
              </div>
            </div>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-slate-600 hover:text-slate-900 text-sm font-medium transition">Features</a>
              <a href="#pricing" className="text-slate-600 hover:text-slate-900 text-sm font-medium transition">Pricing</a>
              <a href="#how-it-works" className="text-slate-600 hover:text-slate-900 text-sm font-medium transition">How It Works</a>
              <a href="#contact" className="text-slate-600 hover:text-slate-900 text-sm font-medium transition">Contact</a>
            </div>
            
            <div className="flex items-center gap-3">
              <Link to="/login" className="hidden sm:block">
                <Button variant="ghost" size="sm">Login</Button>
              </Link>
              <Link to="/register">
                <Button 
                  size="sm" 
                  className="text-white"
                  style={{ backgroundColor: colors.primary }}
                  data-testid="hero-cta"
                >
                  {hero.cta_primary}
                </Button>
              </Link>
              <button 
                className="md:hidden p-2 hover:bg-slate-100 rounded-lg"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </div>
          
          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden py-4 border-t border-slate-100">
              <div className="flex flex-col gap-3">
                <a href="#features" onClick={() => setMobileMenuOpen(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-50 rounded-lg">Features</a>
                <a href="#pricing" onClick={() => setMobileMenuOpen(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-50 rounded-lg">Pricing</a>
                <a href="#how-it-works" onClick={() => setMobileMenuOpen(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-50 rounded-lg">How It Works</a>
                <a href="#contact" onClick={() => setMobileMenuOpen(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-50 rounded-lg">Contact</a>
                <Link to="/login" onClick={() => setMobileMenuOpen(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-50 rounded-lg">Login</Link>
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8" style={{ background: `linear-gradient(135deg, ${colors.background} 0%, #ffffff 100%)` }}>
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div 
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium mb-6"
                style={{ backgroundColor: `${colors.primary}15`, color: colors.primary }}
              >
                <Zap className="w-4 h-4" />
                {hero.badge}
              </div>
              
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6" style={{ color: colors.accent }}>
                {hero.title}
                <br />
                <span style={{ color: colors.primary }}>{hero.title_highlight}</span>
              </h1>
              
              <p className="text-lg text-slate-600 mb-8 max-w-xl">
                {hero.subtitle}
              </p>
              
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-8">
                <Link to="/register">
                  <Button 
                    size="lg" 
                    className="px-8 h-12 text-base text-white"
                    style={{ backgroundColor: colors.primary }}
                  >
                    {hero.cta_primary}
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Button 
                  size="lg" 
                  variant="outline" 
                  className="px-8 h-12 text-base"
                  style={{ borderColor: colors.primary, color: colors.primary }}
                >
                  {hero.cta_secondary}
                </Button>
              </div>
              
              <div className="flex flex-wrap items-center gap-6 text-sm text-slate-500">
                {hero.features?.map((feature, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Check className="w-5 h-5" style={{ color: colors.secondary }} />
                    {feature}
                  </div>
                ))}
              </div>
            </div>
            
            <div className="relative">
              <div 
                className="absolute inset-0 rounded-3xl opacity-20 blur-3xl"
                style={{ backgroundColor: colors.primary }}
              />
              <div className="relative bg-white rounded-2xl shadow-2xl p-8 border border-slate-200">
                <div className="flex items-center gap-4 mb-6">
                  <img src={brand.logo_url} alt={brand.name} className="w-16 h-16 object-contain" />
                  <div>
                    <h3 className="font-bold text-xl" style={{ color: colors.accent }}>{brand.name}</h3>
                    <p className="text-sm text-slate-500">{brand.tagline}</p>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-3 rounded-lg" style={{ backgroundColor: `${colors.secondary}10` }}>
                    <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: colors.secondary }}>
                      <Wifi className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-700">ISP Billing</p>
                      <p className="text-xs text-slate-500">Automated broadband billing</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3 p-3 rounded-lg" style={{ backgroundColor: `${colors.primary}10` }}>
                    <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: colors.primary }}>
                      <Receipt className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-700">GST Invoices</p>
                      <p className="text-xs text-slate-500">Compliant tax invoices</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3 p-3 rounded-lg" style={{ backgroundColor: `${colors.accent}10` }}>
                    <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: colors.accent }}>
                      <TrendingUp className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-700">Growth Analytics</p>
                      <p className="text-xs text-slate-500">Track your business growth</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 text-white" style={{ backgroundColor: colors.accent }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">{stats.stat1_value}</div>
              <div className="text-slate-300 text-sm">{stats.stat1_label}</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">{stats.stat2_value}</div>
              <div className="text-slate-300 text-sm">{stats.stat2_label}</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">{stats.stat3_value}</div>
              <div className="text-slate-300 text-sm">{stats.stat3_label}</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">{stats.stat4_value}</div>
              <div className="text-slate-300 text-sm">{stats.stat4_label}</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4" style={{ color: colors.accent }}>
              {featuresSection.title}
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              {featuresSection.subtitle}
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <Card key={index} className="border-slate-200 hover:border-slate-300 hover:shadow-lg transition-all duration-300 group">
                  <CardHeader>
                    <div 
                      className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-colors"
                      style={{ backgroundColor: `${colors.primary}15` }}
                    >
                      <Icon className="w-6 h-6" style={{ color: colors.primary }} />
                    </div>
                    <CardTitle className="text-lg" style={{ color: colors.accent }}>{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 px-4 sm:px-6 lg:px-8" style={{ backgroundColor: colors.background }}>
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4" style={{ color: colors.accent }}>
              Get Started in Minutes
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Set up your billing automation in four simple steps
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step, index) => (
              <div key={index} className="relative">
                <div className="text-6xl font-bold mb-4" style={{ color: `${colors.primary}20` }}>{step.number}</div>
                <h3 className="text-xl font-semibold mb-2" style={{ color: colors.accent }}>{step.title}</h3>
                <p className="text-slate-600">{step.description}</p>
                {index < steps.length - 1 && (
                  <ChevronRight className="hidden lg:block absolute top-8 -right-4 w-8 h-8" style={{ color: colors.primary }} />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4" style={{ color: colors.accent }}>
              Simple, Transparent Pricing
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Choose the plan that fits your business. All plans include GST compliance.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl mx-auto">
            {plans.map((plan) => (
              <Card 
                key={plan.id} 
                className={`relative ${plan.highlighted ? 'border-2 shadow-xl scale-105' : 'border-slate-200'}`}
                style={plan.highlighted ? { borderColor: colors.primary } : {}}
                data-testid={`pricing-${plan.id}`}
              >
                {plan.highlighted && (
                  <div 
                    className="absolute -top-3 left-1/2 -translate-x-1/2 text-white text-xs font-semibold px-3 py-1 rounded-full"
                    style={{ backgroundColor: colors.secondary }}
                  >
                    Most Popular
                  </div>
                )}
                <CardHeader className="text-center pb-2">
                  <CardTitle className="text-xl" style={{ color: colors.accent }}>{plan.name}</CardTitle>
                  <CardDescription>{plan.description}</CardDescription>
                </CardHeader>
                <CardContent className="text-center">
                  <div className="mb-6">
                    <span className="text-4xl font-bold" style={{ color: colors.accent }}>
                      ₹{plan.price.toLocaleString('en-IN')}
                    </span>
                    <span className="text-slate-500 text-sm">{plan.period}</span>
                  </div>
                  
                  <ul className="space-y-3 text-left mb-6">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-slate-600">
                        <Check className="w-4 h-4 flex-shrink-0" style={{ color: colors.secondary }} />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  
                  <Link to="/register">
                    <Button 
                      className="w-full text-white"
                      style={{ backgroundColor: plan.highlighted ? colors.primary : colors.accent }}
                    >
                      {plan.cta}
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
          
          <div className="text-center mt-8 text-slate-500 text-sm">
            All prices are exclusive of GST (18%)
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 text-white" style={{ backgroundColor: colors.primary }}>
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Ready to Automate Your Billing?
          </h2>
          <p className="text-white/80 mb-8 text-lg">
            Join 500+ ISPs and cable operators already using {brand.name} to streamline their recurring revenue.
          </p>
          <Link to="/register">
            <Button 
              size="lg" 
              className="px-8 h-12 text-base"
              style={{ backgroundColor: 'white', color: colors.primary }}
            >
              Start Your Free Trial
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            <div>
              <h2 className="text-3xl font-bold mb-4" style={{ color: colors.accent }}>
                Get in Touch
              </h2>
              <p className="text-slate-600 mb-8">
                Have questions? Our team is here to help you get started with 
                the perfect plan for your business.
              </p>
              
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div 
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${colors.primary}15` }}
                  >
                    <Mail className="w-6 h-6" style={{ color: colors.primary }} />
                  </div>
                  <div>
                    <div className="font-medium" style={{ color: colors.accent }}>Email Us</div>
                    <div className="text-slate-600">{contact.email}</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div 
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${colors.secondary}15` }}
                  >
                    <Phone className="w-6 h-6" style={{ color: colors.secondary }} />
                  </div>
                  <div>
                    <div className="font-medium" style={{ color: colors.accent }}>Call Us</div>
                    <div className="text-slate-600">{contact.phone}</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div 
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${colors.accent}15` }}
                  >
                    <MessageCircle className="w-6 h-6" style={{ color: colors.accent }} />
                  </div>
                  <div>
                    <div className="font-medium" style={{ color: colors.accent }}>WhatsApp Support</div>
                    <div className="text-slate-600">{contact.whatsapp}</div>
                  </div>
                </div>
              </div>
            </div>
            
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle style={{ color: colors.accent }}>Send us a message</CardTitle>
                <CardDescription>We'll get back to you within 24 hours</CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                      <input 
                        type="text" 
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:border-transparent"
                        style={{ '--tw-ring-color': colors.primary }}
                        placeholder="John Doe"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Company</label>
                      <input 
                        type="text" 
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:border-transparent"
                        placeholder="Your Company"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                    <input 
                      type="email" 
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:border-transparent"
                      placeholder="you@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Phone</label>
                    <input 
                      type="tel" 
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:border-transparent"
                      placeholder="+91 98765 43210"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Message</label>
                    <textarea 
                      rows={4}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:border-transparent"
                      placeholder="Tell us about your business needs..."
                    />
                  </div>
                  <Button 
                    className="w-full text-white"
                    style={{ backgroundColor: colors.primary }}
                  >
                    Send Message
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-slate-200" style={{ backgroundColor: colors.background }}>
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <img src={brand.logo_url} alt={brand.name} className="w-10 h-10 object-contain" />
                <span className="font-bold" style={{ color: colors.accent }}>{brand.name}</span>
              </div>
              <p className="text-sm text-slate-600">
                {brand.tagline} by {brand.business_name}. India's leading multi-tenant recurring billing platform for ISPs and cable operators.
              </p>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4" style={{ color: colors.accent }}>Product</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><a href="#features" className="hover:text-slate-900 transition">Features</a></li>
                <li><a href="#pricing" className="hover:text-slate-900 transition">Pricing</a></li>
                <li><a href="#" className="hover:text-slate-900 transition">API</a></li>
                <li><a href="#" className="hover:text-slate-900 transition">Integrations</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4" style={{ color: colors.accent }}>Company</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><a href="#" className="hover:text-slate-900 transition">About Us</a></li>
                <li><a href="#" className="hover:text-slate-900 transition">Blog</a></li>
                <li><a href="#" className="hover:text-slate-900 transition">Careers</a></li>
                <li><a href="#contact" className="hover:text-slate-900 transition">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4" style={{ color: colors.accent }}>Legal</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><a href="#" className="hover:text-slate-900 transition">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-slate-900 transition">Terms of Service</a></li>
                <li><a href="#" className="hover:text-slate-900 transition">Refund Policy</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-slate-200 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-slate-500">
              {footer.copyright}
            </p>
            <p className="text-sm text-slate-500">
              {footer.tagline}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
