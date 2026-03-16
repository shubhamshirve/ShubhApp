import { useState } from "react";
import { Link } from "react-router-dom";
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
  Building2
} from "lucide-react";

const LandingPage = () => {
  const [selectedPlan, setSelectedPlan] = useState("professional");

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
      id: "starter",
      name: "Starter",
      price: 0,
      period: "3 days trial",
      description: "Try before you buy",
      features: [
        "10 subscribers",
        "1 staff member",
        "Basic invoicing",
        "Manual reminders"
      ],
      highlighted: false,
      cta: "Start Free Trial"
    },
    {
      id: "basic",
      name: "Basic",
      price: 999,
      period: "/month",
      description: "For small businesses",
      features: [
        "100 subscribers",
        "3 staff members",
        "Auto notifications",
        "Auto reminders",
        "Payment gateway"
      ],
      highlighted: false,
      cta: "Get Started"
    },
    {
      id: "professional",
      name: "Professional",
      price: 2499,
      period: "/month",
      description: "Most popular choice",
      features: [
        "500 subscribers",
        "10 staff members",
        "Auto notifications",
        "Auto reminders",
        "Payment gateway",
        "Audit logs",
        "Priority support"
      ],
      highlighted: true,
      cta: "Get Started"
    },
    {
      id: "enterprise",
      name: "Enterprise",
      price: 4999,
      period: "/month",
      description: "For large operations",
      features: [
        "2000 subscribers",
        "25 staff members",
        "All features",
        "Dedicated support",
        "Custom integrations",
        "API access"
      ],
      highlighted: false,
      cta: "Contact Sales"
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

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold">SB</span>
              </div>
              <span className="font-heading font-bold text-xl text-slate-900">SaaS Billing</span>
            </div>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-slate-600 hover:text-slate-900 text-sm font-medium">Features</a>
              <a href="#pricing" className="text-slate-600 hover:text-slate-900 text-sm font-medium">Pricing</a>
              <a href="#how-it-works" className="text-slate-600 hover:text-slate-900 text-sm font-medium">How It Works</a>
              <a href="#contact" className="text-slate-600 hover:text-slate-900 text-sm font-medium">Contact</a>
            </div>
            
            <div className="flex items-center gap-3">
              <Link to="/login">
                <Button variant="ghost" size="sm">Login</Button>
              </Link>
              <Link to="/register">
                <Button size="sm" className="bg-slate-900 hover:bg-slate-800" data-testid="hero-cta">
                  Start Free Trial
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-slate-50 to-white">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full text-blue-700 text-sm font-medium mb-6">
            <Zap className="w-4 h-4" />
            India's GST-Ready Billing Platform
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-heading font-bold text-slate-900 leading-tight mb-6">
            Automate Your
            <br />
            <span className="text-blue-600">Recurring Billing</span>
          </h1>
          
          <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-8">
            Multi-tenant billing platform for subscription businesses in India. 
            Auto-generate invoices, send WhatsApp reminders, and collect payments 
            through your own payment gateway.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <Link to="/register">
              <Button size="lg" className="bg-slate-900 hover:bg-slate-800 px-8 h-12 text-base">
                Start 3-Day Free Trial
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="px-8 h-12 text-base">
              Watch Demo
            </Button>
          </div>
          
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500">
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-emerald-500" />
              No credit card required
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-emerald-500" />
              GST compliant invoices
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-emerald-500" />
              WhatsApp integration
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">10K+</div>
              <div className="text-slate-400 text-sm">Active Subscribers</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">₹5Cr+</div>
              <div className="text-slate-400 text-sm">Processed Monthly</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">500+</div>
              <div className="text-slate-400 text-sm">Businesses Trust Us</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold mb-2">99.9%</div>
              <div className="text-slate-400 text-sm">Uptime</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-heading font-bold text-slate-900 mb-4">
              Everything You Need to Manage Billing
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              A complete solution for subscription businesses with GST compliance, 
              automated workflows, and seamless payment collection.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <Card key={index} className="border-slate-200 hover:border-slate-300 hover:shadow-lg transition-all duration-300">
                  <CardHeader>
                    <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6 text-blue-600" />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 px-4 sm:px-6 lg:px-8 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-heading font-bold text-slate-900 mb-4">
              Get Started in Minutes
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Set up your billing automation in four simple steps
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step, index) => (
              <div key={index} className="relative">
                <div className="text-6xl font-bold text-slate-100 mb-4">{step.number}</div>
                <h3 className="text-xl font-semibold text-slate-900 mb-2">{step.title}</h3>
                <p className="text-slate-600">{step.description}</p>
                {index < steps.length - 1 && (
                  <ChevronRight className="hidden lg:block absolute top-8 -right-4 w-8 h-8 text-slate-300" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-heading font-bold text-slate-900 mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Choose the plan that fits your business. All plans include GST compliance.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {plans.map((plan) => (
              <Card 
                key={plan.id} 
                className={`relative ${plan.highlighted ? 'border-blue-500 border-2 shadow-xl scale-105' : 'border-slate-200'}`}
                data-testid={`pricing-${plan.id}`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    Most Popular
                  </div>
                )}
                <CardHeader className="text-center pb-2">
                  <CardTitle className="text-xl">{plan.name}</CardTitle>
                  <CardDescription>{plan.description}</CardDescription>
                </CardHeader>
                <CardContent className="text-center">
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-slate-900">
                      {plan.price === 0 ? 'Free' : `₹${plan.price.toLocaleString('en-IN')}`}
                    </span>
                    <span className="text-slate-500 text-sm">{plan.period}</span>
                  </div>
                  
                  <ul className="space-y-3 text-left mb-6">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-slate-600">
                        <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  
                  <Link to="/register">
                    <Button 
                      className={`w-full ${plan.highlighted ? 'bg-blue-600 hover:bg-blue-700' : 'bg-slate-900 hover:bg-slate-800'}`}
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
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-slate-900 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-heading font-bold mb-4">
            Ready to Automate Your Billing?
          </h2>
          <p className="text-slate-300 mb-8 text-lg">
            Join 500+ businesses already using SaaS Billing to streamline their recurring revenue.
          </p>
          <Link to="/register">
            <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 px-8 h-12 text-base">
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
              <h2 className="text-3xl font-heading font-bold text-slate-900 mb-4">
                Get in Touch
              </h2>
              <p className="text-slate-600 mb-8">
                Have questions? Our team is here to help you get started with 
                the perfect plan for your business.
              </p>
              
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
                    <Mail className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Email Us</div>
                    <div className="text-slate-600">support@saasbilling.in</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center">
                    <Phone className="w-6 h-6 text-emerald-600" />
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Call Us</div>
                    <div className="text-slate-600">+91 98765 43210</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center">
                    <MessageCircle className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">WhatsApp Support</div>
                    <div className="text-slate-600">+91 98765 43210</div>
                  </div>
                </div>
              </div>
            </div>
            
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle>Send us a message</CardTitle>
                <CardDescription>We'll get back to you within 24 hours</CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                      <input 
                        type="text" 
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="John Doe"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Company</label>
                      <input 
                        type="text" 
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Your Company"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                    <input 
                      type="email" 
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="you@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Phone</label>
                    <input 
                      type="tel" 
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="+91 98765 43210"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Message</label>
                    <textarea 
                      rows={4}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Tell us about your business needs..."
                    />
                  </div>
                  <Button className="w-full bg-slate-900 hover:bg-slate-800">
                    Send Message
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 sm:px-6 lg:px-8 bg-slate-50 border-t border-slate-200">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-slate-900 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">SB</span>
                </div>
                <span className="font-heading font-bold text-slate-900">SaaS Billing</span>
              </div>
              <p className="text-sm text-slate-600">
                India's leading multi-tenant recurring billing platform for subscription businesses.
              </p>
            </div>
            
            <div>
              <h4 className="font-semibold text-slate-900 mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><a href="#features" className="hover:text-slate-900">Features</a></li>
                <li><a href="#pricing" className="hover:text-slate-900">Pricing</a></li>
                <li><a href="#" className="hover:text-slate-900">API</a></li>
                <li><a href="#" className="hover:text-slate-900">Integrations</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-slate-900 mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><a href="#" className="hover:text-slate-900">About Us</a></li>
                <li><a href="#" className="hover:text-slate-900">Blog</a></li>
                <li><a href="#" className="hover:text-slate-900">Careers</a></li>
                <li><a href="#contact" className="hover:text-slate-900">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-slate-900 mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><a href="#" className="hover:text-slate-900">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-slate-900">Terms of Service</a></li>
                <li><a href="#" className="hover:text-slate-900">Refund Policy</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-slate-200 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-slate-500">
              © 2026 SaaS Billing. All rights reserved.
            </p>
            <p className="text-sm text-slate-500">
              Made in India 🇮🇳
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
