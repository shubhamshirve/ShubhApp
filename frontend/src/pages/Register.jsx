import { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { toast } from "sonner";
import axios from "axios";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Switch } from "../components/ui/switch";
import { Eye, EyeOff, UserPlus, ArrowLeft, MessageCircle, RefreshCw, ShieldCheck } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Register = () => {
  const [step, setStep] = useState(1); // 1: form, 2: OTP verification
  const [formData, setFormData] = useState({
    company_name: "",
    owner_name: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    gst_number: "",
    charge_gst: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [registrationId, setRegistrationId] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [otpSent, setOtpSent] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const otpRefs = useRef([]);
  const navigate = useNavigate();

  // Auth context
  const { login: authLogin } = useAuth();

  // Countdown timer for resend
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Step 1: Submit registration form
  const handleSubmit = async (e) => {
    e.preventDefault();
    const { company_name, owner_name, email, phone, password, confirmPassword, gst_number } = formData;

    if (!company_name.trim() || company_name.trim().length < 2) {
      toast.error("Company name must be at least 2 characters");
      return;
    }
    if (!owner_name.trim() || owner_name.trim().length < 2) {
      toast.error("Owner name must be at least 2 characters");
      return;
    }
    if (!email.trim()) {
      toast.error("Email is required");
      return;
    }
    const phoneDigits = phone.replace(/\D/g, "");
    if (phoneDigits.length < 10) {
      toast.error("Phone number must be at least 10 digits");
      return;
    }
    if (password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    if (gst_number && !/^\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d{1}[A-Z]{1}\d{1}$/.test(gst_number.trim())) {
      toast.error("Invalid GST number format");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API}/auth/register-init`, {
        company_name: company_name.trim(),
        owner_name: owner_name.trim(),
        email: email.trim(),
        phone: phoneDigits.length === 10 ? phoneDigits : phoneDigits,
        password,
        gst_number: gst_number.trim() || null,
        charge_gst: formData.charge_gst,
      });
      setRegistrationId(res.data.registration_id);
      setOtpSent(res.data.otp_sent);
      setStep(2);
      setCountdown(30);
      toast.success(res.data.message || "OTP sent! Please verify.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  // OTP input handlers
  const handleOtpChange = (index, value) => {
    if (value.length > 1) value = value.slice(-1);
    if (value && !/^\d$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  };

  const handleOtpPaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length > 0) {
      const newOtp = [...otp];
      for (let i = 0; i < 6; i++) {
        newOtp[i] = pasted[i] || "";
      }
      setOtp(newOtp);
      const focusIdx = Math.min(pasted.length, 5);
      otpRefs.current[focusIdx]?.focus();
    }
  };

  // Step 2: Verify OTP
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    const otpValue = otp.join("");
    if (otpValue.length !== 6) {
      toast.error("Please enter the 6-digit OTP");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API}/auth/verify-otp`, {
        registration_id: registrationId,
        otp: otpValue,
      });
      // Store token and user data
      const { access_token, user: userData } = res.data;
      localStorage.setItem("token", access_token);
      toast.success("Registration successful! Welcome!");
      // Redirect - reload to set auth context
      window.location.href = "/operator";
    } catch (error) {
      toast.error(error.response?.data?.detail || "OTP verification failed");
      // Clear OTP on failure
      setOtp(["", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  // Resend OTP
  const handleResendOtp = async () => {
    setResending(true);
    try {
      const res = await axios.post(`${API}/auth/resend-otp?registration_id=${registrationId}`);
      toast.success(res.data.message || "OTP resent!");
      setCountdown(30);
      setOtp(["", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to resend OTP");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#EFEFEF] flex items-center justify-center p-4 py-8">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-8">
          <img src="/ebill-logo.svg" alt="E-Bill" className="w-16 h-16 mx-auto mb-4" />
          <h1 className="text-2xl font-heading font-bold text-[#004080]">Register as Operator</h1>
          <p className="text-slate-500 mt-1">Start with a 3-day trial on our Starter plan</p>
        </div>

        {step === 1 ? (
          /* ── Step 1: Registration Form ── */
          <Card className="border-slate-200 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-xl font-heading text-[#004080]">Create your account</CardTitle>
              <CardDescription>Fill in your business details to get started</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="company_name" className="text-[#004080]">Company Name *</Label>
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
                    <Label htmlFor="owner_name" className="text-[#004080]">Owner Name *</Label>
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
                    <Label htmlFor="email" className="text-[#004080]">Email *</Label>
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
                    <Label htmlFor="phone">WhatsApp Number *</Label>
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
                    <p className="text-xs text-slate-400">OTP will be sent to this number</p>
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
                        onCheckedChange={(checked) => setFormData((prev) => ({ ...prev, charge_gst: checked }))}
                        data-testid="register-charge-gst"
                      />
                    </div>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full text-white"
                  style={{ backgroundColor: '#0066B2' }}
                  disabled={loading}
                  data-testid="register-submit"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                      Verifying...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <MessageCircle className="w-4 h-4" />
                      Send OTP & Verify
                    </span>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-sm text-slate-500">
                  Already have an account?{" "}
                  <Link to="/login" className="text-[#0066B2] hover:text-[#004080] font-medium">Sign in</Link>
                </p>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
                <p className="text-sm font-medium text-[#004080] mb-1">3-Day Trial Includes:</p>
                <ul className="text-xs text-[#0066B2] space-y-1">
                  <li>• Full access to Starter plan features</li>
                  <li>• No credit card required</li>
                  <li>• Upgrade anytime to continue after trial</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        ) : (
          /* ── Step 2: OTP Verification ── */
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="space-y-1 pb-4">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => { setStep(1); setOtp(["", "", "", "", "", ""]); }}
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <CardTitle className="text-xl font-heading">Verify Your Number</CardTitle>
              </div>
              <CardDescription>
                {otpSent ? (
                  <>We sent a verification code to your WhatsApp number ending in <span className="font-semibold text-slate-700">****{formData.phone.slice(-4)}</span></>
                ) : (
                  <>Please enter the verification code to complete registration</>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleVerifyOtp} className="space-y-6">
                {/* OTP illustration */}
                <div className="flex justify-center">
                  <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center">
                    <ShieldCheck className="w-8 h-8 text-emerald-600" />
                  </div>
                </div>

                {/* OTP Input */}
                <div className="flex justify-center gap-2" onPaste={handleOtpPaste}>
                  {otp.map((digit, i) => (
                    <Input
                      key={i}
                      ref={(el) => (otpRefs.current[i] = el)}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleOtpChange(i, e.target.value)}
                      onKeyDown={(e) => handleOtpKeyDown(i, e)}
                      className="w-12 h-14 text-center text-xl font-bold border-2 focus:border-emerald-500 focus:ring-emerald-500"
                      data-testid={`otp-input-${i}`}
                      autoFocus={i === 0}
                    />
                  ))}
                </div>

                <Button
                  type="submit"
                  className="w-full bg-emerald-600 hover:bg-emerald-700"
                  disabled={loading || otp.join("").length !== 6}
                  data-testid="verify-otp-btn"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                      Verifying...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4" />
                      Verify & Create Account
                    </span>
                  )}
                </Button>

                {/* Resend */}
                <div className="text-center">
                  {countdown > 0 ? (
                    <p className="text-sm text-slate-400">
                      Resend OTP in <span className="font-semibold text-slate-600">{countdown}s</span>
                    </p>
                  ) : (
                    <button
                      type="button"
                      onClick={handleResendOtp}
                      disabled={resending}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
                    >
                      <RefreshCw className={`w-3 h-3 ${resending ? "animate-spin" : ""}`} />
                      {resending ? "Resending..." : "Resend OTP"}
                    </button>
                  )}
                </div>

                <div className="p-3 bg-amber-50 rounded-lg border border-amber-100 text-center">
                  <p className="text-xs text-amber-700">
                    Didn't receive the OTP? Check your WhatsApp messages or try resending.
                  </p>
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Register;
