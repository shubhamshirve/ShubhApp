import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { ArrowLeft, Mail, MessageCircle, KeyRound, Check, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL || ""}/api`;

const ForgotPassword = () => {
  const [step, setStep] = useState(1); // 1: email, 2: otp, 3: new password
  const [email, setEmail] = useState("");
  const [method, setMethod] = useState("email");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [recoveryId, setRecoveryId] = useState("");
  const [loading, setLoading] = useState(false);
  const [phoneLast4, setPhoneLast4] = useState("");
  const [emailMasked, setEmailMasked] = useState("");
  const navigate = useNavigate();

  const handleRequestOTP = async (e) => {
    e.preventDefault();
    if (!email.trim()) { toast.error("Email is required"); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { toast.error("Please enter a valid email"); return; }
    
    setLoading(true);
    try {
      const res = await axios.post(`${API}/auth/forgot-password`, { email, method });
      setRecoveryId(res.data.recovery_id);
      setPhoneLast4(res.data.phone_last4 || "");
      setEmailMasked(res.data.email_masked || "");
      toast.success("Recovery code sent!");
      setStep(2);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send recovery code");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    if (!otp.trim() || otp.length !== 6) { 
      toast.error("Please enter a valid 6-digit OTP"); 
      return; 
    }
    
    setLoading(true);
    try {
      await axios.post(`${API}/auth/verify-recovery-otp`, { recovery_id: recoveryId, otp });
      toast.success("OTP verified!");
      setStep(3);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Invalid OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!newPassword || newPassword.length < 6) { 
      toast.error("Password must be at least 6 characters"); 
      return; 
    }
    if (newPassword !== confirmPassword) { 
      toast.error("Passwords don't match"); 
      return; 
    }
    
    setLoading(true);
    try {
      await axios.post(`${API}/auth/reset-password`, { recovery_id: recoveryId, new_password: newPassword });
      toast.success("Password reset successfully!");
      navigate("/login");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to reset password");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/auth/resend-recovery-otp?recovery_id=${recoveryId}`);
      toast.success("New OTP sent!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to resend OTP");
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
          
          <div className="space-y-3">
            <div className={`flex items-center gap-3 p-3 rounded-lg ${step >= 1 ? 'bg-white/20' : 'bg-white/5'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step > 1 ? 'bg-[#44AB62]' : 'bg-white/20'}`}>
                {step > 1 ? <Check className="w-4 h-4 text-white" /> : <span className="text-sm">1</span>}
              </div>
              <span className="text-sm">Enter your email</span>
            </div>
            <div className={`flex items-center gap-3 p-3 rounded-lg ${step >= 2 ? 'bg-white/20' : 'bg-white/5'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step > 2 ? 'bg-[#44AB62]' : step >= 2 ? 'bg-white/20' : 'bg-white/5'}`}>
                {step > 2 ? <Check className="w-4 h-4 text-white" /> : <span className="text-sm">2</span>}
              </div>
              <span className="text-sm">Verify OTP</span>
            </div>
            <div className={`flex items-center gap-3 p-3 rounded-lg ${step >= 3 ? 'bg-white/20' : 'bg-white/5'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step === 3 ? 'bg-white/20' : 'bg-white/5'}`}>
                <span className="text-sm">3</span>
              </div>
              <span className="text-sm">Set new password</span>
            </div>
          </div>
          
          <p className="mt-8 text-sm text-blue-200">by Teasy Services</p>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 bg-[#EFEFEF]">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="text-center mb-8 lg:hidden">
            <img src="/ebill-logo.svg" alt="E-Bill" className="w-20 h-20 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-[#004080]">E-Bill</h1>
            <p className="text-[#0066B2] mt-1">Password Recovery</p>
          </div>

          <Card className="border-slate-200 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <Link to="/login" className="inline-flex items-center text-sm text-[#0066B2] hover:text-[#004080] mb-2">
                <ArrowLeft className="w-4 h-4 mr-1" />
                Back to Login
              </Link>
              <CardTitle className="text-xl font-bold text-[#004080]">
                {step === 1 && "Forgot Password"}
                {step === 2 && "Verify OTP"}
                {step === 3 && "Set New Password"}
              </CardTitle>
              <CardDescription>
                {step === 1 && "Enter your email to receive a recovery code"}
                {step === 2 && `Enter the 6-digit code sent to your ${method === 'whatsapp' ? `WhatsApp (****${phoneLast4})` : (emailMasked || 'email address')}`}
                {step === 3 && "Create a new secure password for your account"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Step 1: Email Input */}
              {step === 1 && (
                <form onSubmit={handleRequestOTP} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-[#004080]">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="border-slate-300 focus:border-[#0066B2]"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-[#004080]">Receive OTP via</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => setMethod("email")}
                        className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all ${
                          method === "email" 
                            ? "border-[#0066B2] bg-[#0066B2]/5" 
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <Mail className={`w-5 h-5 ${method === "email" ? "text-[#0066B2]" : "text-slate-400"}`} />
                        <span className={method === "email" ? "text-[#0066B2] font-medium" : "text-slate-600"}>Email</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setMethod("whatsapp")}
                        className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all ${
                          method === "whatsapp" 
                            ? "border-[#44AB62] bg-[#44AB62]/5" 
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <MessageCircle className={`w-5 h-5 ${method === "whatsapp" ? "text-[#44AB62]" : "text-slate-400"}`} />
                        <span className={method === "whatsapp" ? "text-[#44AB62] font-medium" : "text-slate-600"}>WhatsApp</span>
                      </button>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="w-full text-white"
                    style={{ backgroundColor: '#0066B2' }}
                    disabled={loading}
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Sending...
                      </span>
                    ) : (
                      "Send Recovery Code"
                    )}
                  </Button>
                </form>
              )}

              {/* Step 2: OTP Verification */}
              {step === 2 && (
                <form onSubmit={handleVerifyOTP} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="otp" className="text-[#004080]">Enter 6-digit OTP</Label>
                    <Input
                      id="otp"
                      type="text"
                      placeholder="000000"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      maxLength={6}
                      required
                      className="text-center text-2xl tracking-widest border-slate-300 focus:border-[#0066B2]"
                    />
                  </div>

                  <Button
                    type="submit"
                    className="w-full text-white"
                    style={{ backgroundColor: '#0066B2' }}
                    disabled={loading}
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Verifying...
                      </span>
                    ) : (
                      "Verify OTP"
                    )}
                  </Button>

                  <div className="text-center">
                    <button
                      type="button"
                      onClick={handleResendOTP}
                      disabled={loading}
                      className="text-sm text-[#0066B2] hover:text-[#004080]"
                    >
                      Didn't receive code? Resend
                    </button>
                  </div>
                </form>
              )}

              {/* Step 3: New Password */}
              {step === 3 && (
                <form onSubmit={handleResetPassword} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="newPassword" className="text-[#004080]">New Password</Label>
                    <Input
                      id="newPassword"
                      type="password"
                      placeholder="Enter new password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={6}
                      className="border-slate-300 focus:border-[#0066B2]"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword" className="text-[#004080]">Confirm Password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      placeholder="Confirm new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      minLength={6}
                      className="border-slate-300 focus:border-[#0066B2]"
                    />
                  </div>

                  <Button
                    type="submit"
                    className="w-full text-white"
                    style={{ backgroundColor: '#44AB62' }}
                    disabled={loading}
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Resetting...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <KeyRound className="w-4 h-4" />
                        Reset Password
                      </span>
                    )}
                  </Button>
                </form>
              )}
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

export default ForgotPassword;
