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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Eye, EyeOff, UserPlus, ArrowLeft, MessageCircle, RefreshCw, ShieldCheck, ChevronDown, ChevronUp, Building2, CreditCard, Info } from "lucide-react";
import { sanitize, sanitizeFormData } from "../utils/sanitize";

const API = `${process.env.REACT_APP_BACKEND_URL || ""}/api`;

const BUSINESS_TYPES = [
  "Sole Proprietorship",
  "Partnership",
  "LLP",
  "Private Limited",
  "Public Limited",
  "Others"
];

const Register = () => {
  const [step, setStep] = useState(1); // 1: form, 2: OTP verification
  const [formData, setFormData] = useState({
    company_name: "",
    owner_name: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    business_type: "",
    gst_number: "",
    pan_number: "",
    address: "",
    charge_gst: false,
    referral_code: "",
    // Bank details
    bank_account_name: "",
    bank_name: "",
    bank_account_number: "",
    bank_ifsc: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [showBankDetails, setShowBankDetails] = useState(false);
  const [loading, setLoading] = useState(false);
  const [registrationId, setRegistrationId] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [otpSent, setOtpSent] = useState(false);
  const [otpEmailMasked, setOtpEmailMasked] = useState("");
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

  const validateField = (name, value) => {
    const v = typeof value === "string" ? value.trim() : value;
    switch (name) {
      case "company_name":
        if (!v || v.length < 2) return "Business name must be at least 2 characters";
        break;
      case "owner_name":
        if (!v || v.length < 2) return "Owner name must be at least 2 characters";
        break;
      case "email":
        if (!v) return "Email is required";
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return "Enter a valid email address";
        break;
      case "phone": {
        const digits = value.replace(/\D/g, "");
        if (digits.length < 10) return "Phone number must be at least 10 digits";
        break;
      }
      case "password":
        if (!v || v.length < 6) return "Password must be at least 6 characters";
        break;
      case "confirmPassword":
        if (v !== formData.password) return "Passwords do not match";
        break;
      case "gst_number":
        if (v && !/^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$/i.test(v))
          return "Invalid GST format (e.g., 22AAAAA0000A1Z5)";
        break;
      case "pan_number":
        if (v && !/^[A-Z]{5}[0-9]{4}[A-Z]$/i.test(v))
          return "Invalid PAN format (e.g., ABCDE1234F)";
        break;
      case "bank_ifsc":
        if (v && !/^[A-Z]{4}0[A-Z0-9]{6}$/i.test(v))
          return "Invalid IFSC format (e.g., SBIN0001234)";
        break;
      default:
        break;
    }
    return "";
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    const error = validateField(name, value);
    setFieldErrors((prev) => ({ ...prev, [name]: error }));
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error on change if it was previously shown
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const FieldError = ({ name }) =>
    fieldErrors[name] ? (
      <p className="text-xs text-red-500 mt-1">{fieldErrors[name]}</p>
    ) : null;

  // Step 1: Submit registration form
  const handleSubmit = async (e) => {
    e.preventDefault();
    const { company_name, owner_name, email, phone, password, confirmPassword, gst_number, pan_number, bank_ifsc } = formData;

    // Validate all required fields and collect errors
    const requiredFields = ["company_name", "owner_name", "email", "phone", "password", "confirmPassword", "gst_number", "pan_number", "bank_ifsc"];
    const errors = {};
    requiredFields.forEach((name) => {
      const error = validateField(name, formData[name]);
      if (error) errors[name] = error;
    });
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      toast.error("Please fix the errors before submitting");
      return;
    }

    const phoneDigits = phone.replace(/\D/g, "");
    setLoading(true);
    try {
      const sanitized = sanitizeFormData(formData);
      const res = await axios.post(`${API}/auth/register-init`, {
        company_name: sanitized.company_name,
        owner_name: sanitized.owner_name,
        email: sanitized.email,
        phone: phoneDigits,
        password,
        business_type: sanitized.business_type || null,
        gst_number: sanitized.gst_number?.toUpperCase() || null,
        pan_number: sanitized.pan_number?.toUpperCase() || null,
        address: sanitized.address || null,
        charge_gst: formData.charge_gst,
        bank_account_name: sanitized.bank_account_name || null,
        bank_name: sanitized.bank_name || null,
        bank_account_number: sanitized.bank_account_number || null,
        bank_ifsc: sanitized.bank_ifsc?.toUpperCase() || null,
        referral_code: sanitized.referral_code?.toUpperCase() || null,
      });
      setRegistrationId(res.data.registration_id);
      setOtpSent(res.data.otp_sent);
      setOtpEmailMasked(res.data.email_masked || "");
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
                    <Label htmlFor="company_name" className="text-[#004080]">Business Name *</Label>
                    <Input
                      id="company_name"
                      name="company_name"
                      placeholder="Your Company Ltd."
                      value={formData.company_name}
                      onChange={handleChange}
                      onBlur={handleBlur}
                      className={fieldErrors.company_name ? "border-red-500" : ""}
                      required
                      data-testid="register-company"
                    />
                    <FieldError name="company_name" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="owner_name" className="text-[#004080]">Owner Name *</Label>
                    <Input
                      id="owner_name"
                      name="owner_name"
                      placeholder="John Doe"
                      value={formData.owner_name}
                      onChange={handleChange}
                      onBlur={handleBlur}
                      className={fieldErrors.owner_name ? "border-red-500" : ""}
                      required
                      data-testid="register-owner"
                    />
                    <FieldError name="owner_name" />
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
                      onBlur={handleBlur}
                      className={fieldErrors.email ? "border-red-500" : ""}
                      required
                      data-testid="register-email"
                    />
                    <FieldError name="email" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number *</Label>
                    <Input
                      id="phone"
                      name="phone"
                      type="tel"
                      placeholder="9876543210"
                      value={formData.phone}
                      onChange={handleChange}
                      onBlur={handleBlur}
                      className={fieldErrors.phone ? "border-red-500" : ""}
                      required
                      data-testid="register-phone"
                    />
                    {fieldErrors.phone
                      ? <FieldError name="phone" />
                      : <p className="text-xs text-slate-400">Used for account communication and WhatsApp notifications</p>
                    }
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
                        onBlur={handleBlur}
                        required
                        className={`pr-10 ${fieldErrors.password ? "border-red-500" : ""}`}
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
                    <FieldError name="password" />
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
                      onBlur={handleBlur}
                      className={fieldErrors.confirmPassword ? "border-red-500" : ""}
                      required
                      data-testid="register-confirm-password"
                    />
                    <FieldError name="confirmPassword" />
                  </div>
                </div>

                {/* KYC Information Section */}
                <div className="border-t border-slate-200 pt-4 mt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Building2 className="w-4 h-4 text-[#004080]" />
                    <p className="text-sm font-medium text-slate-700">KYC Information (Optional)</p>
                  </div>
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="business_type">Business Type</Label>
                        <Select
                          value={formData.business_type}
                          onValueChange={(value) => setFormData((prev) => ({ ...prev, business_type: value }))}
                        >
                          <SelectTrigger data-testid="register-business-type">
                            <SelectValue placeholder="Select business type" />
                          </SelectTrigger>
                          <SelectContent>
                            {BUSINESS_TYPES.map((type) => (
                              <SelectItem key={type} value={type}>{type}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="pan_number">PAN Number</Label>
                        <Input
                          id="pan_number"
                          name="pan_number"
                          placeholder="ABCDE1234F"
                          value={formData.pan_number}
                          onChange={handleChange}
                          onBlur={handleBlur}
                          className={`uppercase ${fieldErrors.pan_number ? "border-red-500" : ""}`}
                          data-testid="register-pan"
                        />
                        <FieldError name="pan_number" />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="gst_number">GST Number (GSTIN)</Label>
                        <Input
                          id="gst_number"
                          name="gst_number"
                          placeholder="22AAAAA0000A1Z5"
                          value={formData.gst_number}
                          onChange={handleChange}
                          onBlur={handleBlur}
                          className={`uppercase ${fieldErrors.gst_number ? "border-red-500" : ""}`}
                          data-testid="register-gst"
                        />
                        <FieldError name="gst_number" />
                      </div>
                      <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg h-[66px]">
                        <div>
                          <Label htmlFor="charge_gst" className="text-sm font-medium">Charge GST</Label>
                          <p className="text-xs text-slate-500">Enable to charge GST on invoices</p>
                        </div>
                        <Switch
                          id="charge_gst"
                          checked={formData.charge_gst}
                          onCheckedChange={(checked) => setFormData((prev) => ({ ...prev, charge_gst: checked }))}
                          data-testid="register-charge-gst"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="address">Business Address</Label>
                      <Input
                        id="address"
                        name="address"
                        placeholder="Complete business address"
                        value={formData.address}
                        onChange={handleChange}
                        data-testid="register-address"
                      />
                    </div>
                  </div>
                </div>

                {/* Bank Details Section - Collapsible */}
                <div className="border-t border-slate-200 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowBankDetails(!showBankDetails)}
                    className="flex items-center justify-between w-full text-left"
                  >
                    <div className="flex items-center gap-2">
                      <CreditCard className="w-4 h-4 text-[#004080]" />
                      <span className="text-sm font-medium text-slate-700">Bank Account Details (Optional)</span>
                    </div>
                    {showBankDetails ? (
                      <ChevronUp className="w-4 h-4 text-slate-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-500" />
                    )}
                  </button>
                  
                  {/* Info note */}
                  <div className="flex items-start gap-2 mt-2 p-2 bg-blue-50 rounded-md">
                    <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-blue-700">
                      Bank details are required only if you want to accept payments through payment gateway
                    </p>
                  </div>

                  {showBankDetails && (
                    <div className="space-y-4 mt-4 animate-fade-in">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="bank_account_name">Account Holder Name</Label>
                          <Input
                            id="bank_account_name"
                            name="bank_account_name"
                            placeholder="Account holder name"
                            value={formData.bank_account_name}
                            onChange={handleChange}
                            data-testid="register-bank-name"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="bank_name">Bank Name</Label>
                          <Input
                            id="bank_name"
                            name="bank_name"
                            placeholder="State Bank of India"
                            value={formData.bank_name}
                            onChange={handleChange}
                            data-testid="register-bank"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="bank_account_number">Account Number</Label>
                          <Input
                            id="bank_account_number"
                            name="bank_account_number"
                            placeholder="1234567890"
                            value={formData.bank_account_number}
                            onChange={handleChange}
                            data-testid="register-account-number"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="bank_ifsc">IFSC Code</Label>
                          <Input
                            id="bank_ifsc"
                            name="bank_ifsc"
                            placeholder="SBIN0001234"
                            value={formData.bank_ifsc}
                            onChange={handleChange}
                            onBlur={handleBlur}
                            className={`uppercase ${fieldErrors.bank_ifsc ? "border-red-500" : ""}`}
                            data-testid="register-ifsc"
                          />
                          <FieldError name="bank_ifsc" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Referral Code */}
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1.5 block">
                    Referral Code <span className="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <Input
                    id="referral_code"
                    name="referral_code"
                    placeholder="e.g. REF-ABC123"
                    value={formData.referral_code}
                    onChange={handleChange}
                    className="uppercase"
                    data-testid="register-referral-code"
                  />
                  <p className="text-xs text-slate-400 mt-1">Enter a referral code to receive the current platform referral discount on your first eligible payment.</p>
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
                      Send Email OTP
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
                  <>We sent a verification code to your email address <span className="font-semibold text-slate-700">{otpEmailMasked || formData.email}</span></>
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
                    Didn't receive the OTP? Check your inbox or spam folder, then try resending.
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
