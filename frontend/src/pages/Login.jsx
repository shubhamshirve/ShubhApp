import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Eye, EyeOff, LogIn, Wifi, Receipt, TrendingUp } from "lucide-react";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) { toast.error("Email is required"); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { toast.error("Please enter a valid email address"); return; }
    if (!password || password.length < 6) { toast.error("Password must be at least 6 characters"); return; }
    setLoading(true);
    try {
      const user = await login(email, password);
      toast.success("Login successful!");
      if (user.role === "admin") {
        navigate("/admin");
      } else {
        navigate("/operator");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div 
        className="hidden lg:flex lg:w-1/2 flex-col justify-center items-center p-12"
        style={{ background: 'linear-gradient(135deg, #0066B2 0%, #004080 100%)' }}
      >
        <div className="max-w-md text-center text-white">
          <img 
            src="/ebill-logo.svg" 
            alt="E-Bill" 
            className="w-32 h-32 mx-auto mb-6"
          />
          <h1 className="text-4xl font-bold mb-4">E-Bill</h1>
          <p className="text-xl mb-8 text-blue-100">ISP & Cable Billing Solutions</p>
          
          <div className="space-y-4 text-left">
            <div className="flex items-center gap-4 p-4 bg-white/10 rounded-lg backdrop-blur-sm">
              <div className="w-10 h-10 rounded-full bg-[#44AB62] flex items-center justify-center">
                <Wifi className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="font-semibold">ISP Billing</p>
                <p className="text-sm text-blue-100">Automated broadband billing</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-white/10 rounded-lg backdrop-blur-sm">
              <div className="w-10 h-10 rounded-full bg-[#44AB62] flex items-center justify-center">
                <Receipt className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="font-semibold">GST Compliant</p>
                <p className="text-sm text-blue-100">Tax invoices & reports</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-white/10 rounded-lg backdrop-blur-sm">
              <div className="w-10 h-10 rounded-full bg-[#44AB62] flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="font-semibold">Growth Analytics</p>
                <p className="text-sm text-blue-100">Track revenue & collections</p>
              </div>
            </div>
          </div>
          
          <p className="mt-8 text-sm text-blue-200">
            by Teasy Services
          </p>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-6 bg-[#EFEFEF]">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="text-center mb-8 lg:hidden">
            <img 
              src="/ebill-logo.svg" 
              alt="E-Bill" 
              className="w-20 h-20 mx-auto mb-4"
            />
            <h1 className="text-2xl font-bold text-[#004080]">E-Bill</h1>
            <p className="text-[#0066B2] mt-1">ISP & Cable Billing Solutions</p>
          </div>

          <Card className="border-slate-200 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-xl font-bold text-[#004080]">Welcome Back</CardTitle>
              <CardDescription>Sign in to your account to continue</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-[#004080]">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="border-slate-300 focus:border-[#0066B2] focus:ring-[#0066B2]"
                    data-testid="login-email"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-[#004080]">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="pr-10 border-slate-300 focus:border-[#0066B2] focus:ring-[#0066B2]"
                      data-testid="login-password"
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

                <div className="text-right">
                  <Link 
                    to="/forgot-password" 
                    className="text-sm text-[#0066B2] hover:text-[#004080] font-medium"
                  >
                    Forgot Password?
                  </Link>
                </div>

                <Button
                  type="submit"
                  className="w-full text-white"
                  style={{ backgroundColor: '#0066B2' }}
                  disabled={loading}
                  data-testid="login-submit"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                      Signing in...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <LogIn className="w-4 h-4" />
                      Sign in
                    </span>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-sm text-slate-500">
                  Don't have an account?{" "}
                  <Link to="/register" className="text-[#0066B2] hover:text-[#004080] font-medium">
                    Register as Operator
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>

          <p className="mt-6 text-center text-xs text-slate-500">
            © 2026 E-Bill by Teasy Services. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
