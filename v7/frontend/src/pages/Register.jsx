import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Switch } from "../components/ui/switch";
import { Eye, EyeOff, UserPlus } from "lucide-react";

const Register = () => {
  const [formData, setFormData] = useState({
    company_name: "",
    owner_name: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    gst_number: "",
    charge_gst: false
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (formData.password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    setLoading(true);

    try {
      await register({
        company_name: formData.company_name,
        owner_name: formData.owner_name,
        email: formData.email,
        phone: formData.phone,
        password: formData.password,
        gst_number: formData.gst_number || null,
        charge_gst: formData.charge_gst
      });
      toast.success("Registration successful! You have a 3-day free trial.");
      navigate("/operator");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 py-8">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-slate-900 rounded-xl mb-4">
            <span className="text-white font-bold text-xl">SB</span>
          </div>
          <h1 className="text-2xl font-heading font-bold text-slate-900">Register as Operator</h1>
          <p className="text-slate-500 mt-1">Start your 3-day free trial today</p>
        </div>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl font-heading">Create your account</CardTitle>
            <CardDescription>Fill in your business details to get started</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="company_name">Company Name *</Label>
                  <Input
                    id="company_name"
                    name="company_name"
                    placeholder="Your Company Ltd."
                    value={formData.company_name}
                    onChange={handleChange}
                    required
                    data-testid="register-company"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="owner_name">Owner Name *</Label>
                  <Input
                    id="owner_name"
                    name="owner_name"
                    placeholder="John Doe"
                    value={formData.owner_name}
                    onChange={handleChange}
                    required
                    data-testid="register-owner"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="you@company.com"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    data-testid="register-email"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Phone *</Label>
                  <Input
                    id="phone"
                    name="phone"
                    type="tel"
                    placeholder="9876543210"
                    value={formData.phone}
                    onChange={handleChange}
                    required
                    data-testid="register-phone"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Password *</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Min. 6 characters"
                      value={formData.password}
                      onChange={handleChange}
                      required
                      className="pr-10"
                      data-testid="register-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm Password *</Label>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    placeholder="Repeat password"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    required
                    data-testid="register-confirm-password"
                  />
                </div>
              </div>

              <div className="border-t border-slate-200 pt-4 mt-4">
                <p className="text-sm font-medium text-slate-700 mb-3">GST Information (Optional)</p>
                
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="gst_number">GST Number</Label>
                    <Input
                      id="gst_number"
                      name="gst_number"
                      placeholder="22AAAAA0000A1Z5"
                      value={formData.gst_number}
                      onChange={handleChange}
                      data-testid="register-gst"
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                    <div>
                      <Label htmlFor="charge_gst" className="text-sm font-medium">Charge GST to customers</Label>
                      <p className="text-xs text-slate-500 mt-0.5">Enable if you want to charge GST on invoices</p>
                    </div>
                    <Switch
                      id="charge_gst"
                      checked={formData.charge_gst}
                      onCheckedChange={(checked) => setFormData(prev => ({ ...prev, charge_gst: checked }))}
                      data-testid="register-charge-gst"
                    />
                  </div>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full bg-slate-900 hover:bg-slate-800"
                disabled={loading}
                data-testid="register-submit"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                    Creating account...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <UserPlus className="w-4 h-4" />
                    Start Free Trial
                  </span>
                )}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-slate-500">
                Already have an account?{" "}
                <Link to="/login" className="text-blue-600 hover:text-blue-700 font-medium">
                  Sign in
                </Link>
              </p>
            </div>

            {/* Trial info */}
            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm font-medium text-blue-800 mb-1">Free Trial Includes:</p>
              <ul className="text-xs text-blue-600 space-y-1">
                <li>• 3 days free access</li>
                <li>• Up to 10 subscribers</li>
                <li>• 1 staff member</li>
                <li>• Basic features</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Register;
