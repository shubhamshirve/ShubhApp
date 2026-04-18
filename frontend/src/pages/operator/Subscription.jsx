import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import { toast } from "sonner";
import { loadRazorpayScript } from "../../lib/razorpay";
import {
  CreditCard,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Clock,
  Puzzle,
  Check,
  Zap,
  Loader2,
  History,
  Wallet,
  ArrowUpRight,
  ArrowDownLeft,
  RefreshCw,
  Plus,
} from "lucide-react";

const OperatorSubscription = () => {
  const { authAxios } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [addons, setAddons] = useState([]);
  const [paymentHistory, setPaymentHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("subscription");
  const [showRenewDialog, setShowRenewDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [processing, setProcessing] = useState(false);
  const [purchasing, setPurchasing] = useState(null);
  const [showAddonConfirm, setShowAddonConfirm] = useState(null);
  const [selectedAddonCodes, setSelectedAddonCodes] = useState([]);
  const [planValidationWarning, setPlanValidationWarning] = useState(null);
  // Coupon state for Renew Dialog
  const [renewCoupon, setRenewCoupon] = useState("");
  const [renewCouponResult, setRenewCouponResult] = useState(null);
  const [renewCouponLoading, setRenewCouponLoading] = useState(false);
  // Coupon state for Addon Confirm Dialog
  const [addonCoupon, setAddonCoupon] = useState("");
  const [addonCouponResult, setAddonCouponResult] = useState(null);
  const [addonCouponLoading, setAddonCouponLoading] = useState(false);
  // Wallet top-up state
  const [wallet, setWallet] = useState(null);
  const [walletLoading, setWalletLoading] = useState(false);
  const [topupAmount, setTopupAmount] = useState("");
  const [topupLoading, setTopupLoading] = useState(false);

  const fetchSubscription = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/subscription");
      setSubscription(res.data);
      if (res.data.saas_plan_id) setSelectedPlan(res.data.saas_plan_id);
    } catch (err) {
      console.error("Failed to load subscription:", err);
      toast.error("Failed to load subscription details");
    }
  }, [authAxios]);

  const fetchAddons = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/addons/store");
      setAddons(res.data);
    } catch (err) {
      console.error("Failed to load addons store:", err);
    }
  }, [authAxios]);

  const fetchPaymentHistory = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/payment-history");
      setPaymentHistory(res.data);
    } catch (err) {
      console.error("Failed to load payment history:", err);
    }
  }, [authAxios]);

  const fetchWallet = useCallback(async () => {
    setWalletLoading(true);
    try {
      const res = await authAxios.get("/operator/wallet");
      setWallet(res.data);
    } catch (err) {
      console.error("Failed to load wallet:", err);
      toast.error("Failed to load wallet");
    } finally {
      setWalletLoading(false);
    }
  }, [authAxios]);

  useEffect(() => {
    Promise.all([fetchSubscription(), fetchAddons(), fetchPaymentHistory()]).finally(() =>
      setLoading(false)
    );
  }, [fetchSubscription, fetchAddons, fetchPaymentHistory]);

  useEffect(() => {
    if (activeTab === "topup") {
      fetchWallet();
    }
  }, [activeTab, fetchWallet]);

  // Validate that current plan matches one in available plans
  useEffect(() => {
    if (subscription && subscription.available_plans && subscription.saas_plan_id) {
      const currentPlanExists = subscription.available_plans.some(p => p.id === subscription.saas_plan_id);
      
      if (!currentPlanExists) {
        const warning = `Your current plan (${subscription.saas_plan_name}) is not found in available plans. This may indicate a data inconsistency.`;
        setPlanValidationWarning(warning);
        console.warn("Plan Validation Warning:", warning, {
          currentPlanId: subscription.saas_plan_id,
          currentPlanName: subscription.saas_plan_name,
          availablePlanIds: subscription.available_plans.map(p => p.id),
        });
      } else {
        setPlanValidationWarning(null);
      }
      
      // Also validate that the plan_validation data matches
      if (subscription.plan_validation && !subscription.plan_validation.is_valid) {
        console.warn("Backend plan validation failed:", subscription.plan_validation);
      }
    }
  }, [subscription]);

  const openRazorpay = async (orderData, onSuccess) => {
    const scriptLoaded = await loadRazorpayScript();
    if (!scriptLoaded) {
      toast.error("Payment gateway failed to load. Please try again.");
      return;
    }
    const options = {
      key: orderData.razorpay_key,
      amount: orderData.amount,
      currency: orderData.currency || "INR",
      name: "Platform Name",
      description: "Monthly Recurring",
      order_id: orderData.razorpay_order_id,
      prefill: orderData.prefill || {},
      handler: async (response) => {
        try {
          await authAxios.post(
            `/operator/checkout/verify?razorpay_order_id=${response.razorpay_order_id}&razorpay_payment_id=${response.razorpay_payment_id}&razorpay_signature=${response.razorpay_signature}`
          );
          toast.success("Payment successful! Your account has been updated.");
          onSuccess();
        } catch (err) {
          toast.error(
            err.response?.data?.detail || "Payment verification failed"
          );
        }
      },
      modal: { ondismiss: () => toast.info("Payment cancelled") },
      theme: { color: "#0f172a" },
    };
    const rzp = new window.Razorpay(options);
    rzp.open();
  };

  const handleRenew = async () => {
    if (subscription?.maintenance_mode) {
      toast.error(subscription?.maintenance_message || "The app is under maintenance.");
      return;
    }
    if (!selectedPlan) {
      toast.error("Please select a plan");
      return;
    }
    setProcessing(true);
    try {
      const addonParam = selectedAddonCodes.length > 0 ? `&addon_codes=${selectedAddonCodes.join(",")}` : "";
      const couponParam = renewCouponResult?.valid ? `&coupon_code=${renewCouponResult.code}` : "";
      // Always 1 month (backend enforces this for subscriptions)
      const res = await authAxios.post(
        `/operator/checkout/create-order?item_type=subscription&plan_id=${selectedPlan}&months=1${addonParam}${couponParam}`
      );
      setShowRenewDialog(false);
      setSelectedAddonCodes([]);
      setRenewCoupon("");
      setRenewCouponResult(null);
      openRazorpay(res.data, () => {
        fetchSubscription();
        fetchAddons();
        fetchPaymentHistory();
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to initiate checkout");
    } finally {
      setProcessing(false);
    }
  };

  const applyRenewCoupon = async () => {
    if (!renewCoupon.trim()) return;
    setRenewCouponLoading(true);
    try {
      const res = await authAxios.post(`/operator/checkout/validate-coupon?code=${renewCoupon.trim()}&amount=${exactTotal}`);
      setRenewCouponResult(res.data);
      toast.success(res.data.message);
    } catch (err) {
      setRenewCouponResult(null);
      toast.error(err.response?.data?.detail || "Invalid coupon code");
    } finally {
      setRenewCouponLoading(false);
    }
  };

  const applyAddonCoupon = async (basePrice) => {
    if (!addonCoupon.trim()) return;
    setAddonCouponLoading(true);
    try {
      const res = await authAxios.post(`/operator/checkout/validate-coupon?code=${addonCoupon.trim()}&amount=${basePrice}`);
      setAddonCouponResult(res.data);
      toast.success(res.data.message);
    } catch (err) {
      setAddonCouponResult(null);
      toast.error(err.response?.data?.detail || "Invalid coupon code");
    } finally {
      setAddonCouponLoading(false);
    }
  };

  const handleAddonPurchase = async (addon) => {
    setShowAddonConfirm(null);
    setPurchasing(addon.code);
    try {
      const couponParam = addonCouponResult?.valid ? `&coupon_code=${addonCouponResult.code}` : "";
      const res = await authAxios.post(
        `/operator/checkout/create-order?item_type=addon&item_code=${addon.code}${couponParam}`
      );
      setAddonCoupon("");
      setAddonCouponResult(null);
      if (res.data.status === "activated_free") {
        toast.success(res.data.message);
        fetchAddons();
        return;
      }
      openRazorpay(res.data, () => {
        fetchSubscription();
        fetchAddons();
        fetchPaymentHistory();
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to purchase add-on");
    } finally {
      setPurchasing(null);
    }
  };

  const handleTopup = async () => {
    if (subscription?.maintenance_mode) {
      toast.error(subscription?.maintenance_message || "The app is under maintenance.");
      return;
    }
    const amt = parseFloat(topupAmount);
    if (!amt || amt < 100) {
      toast.error("Minimum top-up amount is ₹100");
      return;
    }
    if (amt > 50000) {
      toast.error("Maximum top-up amount is ₹50,000");
      return;
    }
    setTopupLoading(true);
    try {
      const res = await authAxios.post(`/operator/wallet/topup/create-order?amount=${amt}`);
      const orderData = res.data;
      
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        toast.error("Payment gateway failed to load. Please try again.");
        setTopupLoading(false);
        return;
      }
      const rzp = new window.Razorpay({
        key: orderData.razorpay_key,
        amount: orderData.amount,
        currency: orderData.currency,
        name: orderData.name,
        description: orderData.description,
        order_id: orderData.razorpay_order_id,
        prefill: orderData.prefill,
        theme: { color: "#0066B2" },
        handler: async (response) => {
          try {
            const verifyRes = await authAxios.post(
              `/operator/wallet/topup/verify?razorpay_order_id=${response.razorpay_order_id}&razorpay_payment_id=${response.razorpay_payment_id}&razorpay_signature=${response.razorpay_signature}`
            );
            toast.success(
              `Wallet credited ₹${verifyRes.data.credited_amount?.toFixed?.(2) ?? verifyRes.data.credited_amount}. ` +
              `Paid ₹${verifyRes.data.paid_amount?.toFixed?.(2) ?? verifyRes.data.paid_amount}. ` +
              `New balance: ₹${verifyRes.data.new_balance?.toFixed?.(2) ?? verifyRes.data.new_balance}`
            );
            setTopupAmount("");
            fetchWallet();
          } catch (err) {
            toast.error(err.response?.data?.detail || "Payment verification failed");
          } finally {
            setTopupLoading(false);
          }
        },
        modal: { ondismiss: () => setTopupLoading(false) },
      });
      rzp.open();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create top-up order");
      setTopupLoading(false);
    }
  };

  const getStatusInfo = () => {
    if (!subscription) return { color: "slate", label: "Unknown", icon: Clock };
    switch (subscription.status) {
      case "active":
        return { color: "emerald", label: "Active", icon: CheckCircle };
      case "trial":
        return { color: "blue", label: "Trial", icon: Clock };
      case "suspended":
        return { color: "red", label: "Suspended", icon: AlertTriangle };
      case "expired":
        return { color: "amber", label: "Expired", icon: AlertTriangle };
      default:
        return { color: "slate", label: subscription.status, icon: Clock };
    }
  };

  const getExpiryDate = () => {
    if (subscription?.subscription_ends_at)
      return new Date(subscription.subscription_ends_at);
    if (subscription?.trial_ends_at) return new Date(subscription.trial_ends_at);
    return null;
  };

  const isExpired = () => {
    const expiry = getExpiryDate();
    return expiry ? expiry < new Date() : false;
  };

  const daysRemaining = () => {
    const expiry = getExpiryDate();
    if (!expiry) return null;
    return Math.ceil((expiry - new Date()) / (1000 * 60 * 60 * 24));
  };

  const isRenewalAllowed = () => {
    const days = daysRemaining();
    // Allow renewal if expired OR within 3 days of expiry
    return isExpired() || (days !== null && days <= 3);
  };

  const getRenewalDisabledMessage = () => {
    const days = daysRemaining();
    if (isExpired()) return "Your subscription has expired";
    if (days !== null && days > 3) {
      return `Renewal available in ${days - 3} days`;
    }
    return "Not eligible for renewal";
  };

  const getAddonStatusBadge = (status) => {
    if (status === "purchased")
      return (
        <span className="text-xs font-semibold bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full">
          Active
        </span>
      );
    if (status === "included_in_plan")
      return (
        <span className="text-xs font-semibold bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">
          Included
        </span>
      );
    return null;
  };

  if (loading) {
    return (
      <OperatorLayout title="Subscription">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;
  const days = daysRemaining();
  const isTrial = subscription?.status === "trial";
  const selectedPlanDetails = subscription?.available_plans?.find(
    (p) => p.id === selectedPlan
  );

  // All pricing is GST inclusive, fixed 1-month term
  const baseAmount = selectedPlanDetails?.monthly_price || 0;
  const ownedPurchasedAddons = addons.filter((a) => a.status === "purchased");
  const ownedAddonTotal = ownedPurchasedAddons.reduce((sum, a) => sum + a.price, 0);
  const purchasableAddons = addons.filter(
    (a) => a.status !== "purchased" && a.status !== "included_in_plan"
  );
  const selectedAddonTotal = purchasableAddons
    .filter((a) => selectedAddonCodes.includes(a.code))
    .reduce((sum, a) => sum + a.price, 0);
  const combinedBase = baseAmount + ownedAddonTotal + selectedAddonTotal;

  // Coupon discount
  const renewDiscount = renewCouponResult?.valid
    ? parseFloat((renewCouponResult.discount_type === "percentage"
        ? combinedBase * renewCouponResult.discount_value / 100
        : Math.min(renewCouponResult.discount_value, combinedBase)).toFixed(2))
    : 0;
  // GST inclusive — no separate GST calculation
  const exactTotal = parseFloat((combinedBase - renewDiscount).toFixed(2));
  const totalAmount = Math.round(exactTotal);
  const roundingDiff = parseFloat((totalAmount - exactTotal).toFixed(2));

  const toggleAddonSelection = (code) => {
    setSelectedAddonCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  // Wallet helpers
  const balance = wallet?.balance ?? 0;
  const isLow = balance < 500;
  const isCritical = balance < 100;
  const isMaintenance = !!subscription?.maintenance_mode;

  return (
    <OperatorLayout title="Subscription" isReadOnly={subscription?.is_read_only}>
      <div className="max-w-4xl space-y-6 animate-fade-in">

        {/* Plan Validation Warning */}
        {planValidationWarning && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-red-800">Plan Validation Warning</p>
              <p className="text-sm text-red-700 mt-1">{planValidationWarning}</p>
              <p className="text-xs text-red-600 mt-2">
                Please contact support if this issue persists. Your current plan is: <strong>{subscription?.saas_plan_name}</strong>
              </p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit">
          <button
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === "subscription"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
            onClick={() => setActiveTab("subscription")}
            data-testid="tab-subscription"
          >
            <CreditCard className="w-4 h-4 inline mr-1.5 -mt-0.5" />
            Subscription & Add-ons
          </button>

          <button
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === "history"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
            onClick={() => setActiveTab("history")}
            data-testid="tab-history"
          >
            <History className="w-4 h-4 inline mr-1.5 -mt-0.5" />
            Payment History
            {paymentHistory.length > 0 && (
              <span className="ml-1.5 bg-slate-700 text-white text-xs px-1.5 py-0.5 rounded-full">
                {paymentHistory.length}
              </span>
            )}
          </button>
        </div>

        {activeTab === "subscription" && (
          <>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Current Subscription
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Status</p>
                <div className="flex items-center gap-2">
                  <StatusIcon className={`w-5 h-5 text-${statusInfo.color}-600`} />
                  <span
                    className={`text-lg font-bold text-${statusInfo.color}-700 capitalize`}
                    data-testid="subscription-status"
                  >
                    {statusInfo.label}
                  </span>
                </div>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Current Plan</p>
                <p className="text-lg font-bold text-slate-900" data-testid="current-plan">
                  {subscription?.saas_plan_name || "No Plan"}
                </p>
                {subscription?.saas_plan_price && (
                  <p className="text-sm text-slate-500">
                    ₹{subscription.saas_plan_price?.toLocaleString("en-IN")}/month <span className="text-xs text-slate-400">(GST incl.)</span>
                  </p>
                )}
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">
                  {subscription?.status === "trial" ? "Trial Expires" : "Expires On"}
                </p>
                <p className="text-lg font-bold text-slate-900" data-testid="expiry-date">
                  {getExpiryDate()
                    ? getExpiryDate().toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })
                    : "N/A"}
                </p>
                {days !== null && (
                  <p
                    className={`text-sm ${
                      days < 0
                        ? "text-red-600 font-medium"
                        : days < 7
                        ? "text-amber-600"
                        : "text-slate-500"
                    }`}
                  >
                    {days < 0
                      ? `Expired ${Math.abs(days)} days ago`
                      : `${days} days remaining`}
                  </p>
                )}
              </div>
            </div>

            {/* Renewal CTA — urgent */}
            {(isExpired() ||
              subscription?.is_read_only ||
              subscription?.status === "trial" ||
              (days !== null && days < 15)) && (
              <div
                className={`p-4 rounded-lg border flex items-center justify-between ${
                  isExpired()
                    ? "bg-red-50 border-red-200"
                    : "bg-amber-50 border-amber-200"
                }`}
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle
                    className={`w-5 h-5 ${
                      isExpired() ? "text-red-600" : "text-amber-600"
                    }`}
                  />
                  <div>
                    <p
                      className={`font-medium ${
                        isExpired() ? "text-red-800" : "text-amber-800"
                      }`}
                    >
                      {isExpired()
                        ? "Your subscription has expired"
                        : subscription?.status === "trial"
                        ? "Your trial is ending soon"
                        : "Your subscription is expiring soon"}
                    </p>
                    <p
                      className={`text-sm ${
                        isExpired() ? "text-red-600" : "text-amber-600"
                      }`}
                    >
                      {isExpired()
                        ? "Renew now to regain full access."
                        : "Renew early to avoid any disruption."}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  {isRenewalAllowed() && (
                    <Button
                      onClick={() => setShowRenewDialog(true)}
                      className={
                        isExpired()
                          ? "bg-red-600 hover:bg-red-700"
                          : "bg-amber-600 hover:bg-amber-700"
                      }
                      data-testid="renew-now-btn"
                    >
                      Renew Now
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    className="border-amber-300"
                    data-testid="wallet-topup-btn"
                    onClick={() => {
                      window.location.href = "/operator/wallet";
                    }}
                  >
                    <Wallet className="w-4 h-4 mr-2" />
                    Topup Wallet
                  </Button>
                </div>
              </div>
            )}

            {/* Always-available renew button when subscription is healthy */}
            {!isExpired() &&
              !subscription?.is_read_only &&
              subscription?.status !== "trial" &&
              (days === null || days >= 15) && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowRenewDialog(true)}
                    disabled={!isRenewalAllowed()}
                    title={!isRenewalAllowed() ? getRenewalDisabledMessage() : ""}
                    data-testid="renew-early-btn"
                  >
                    <Calendar className="w-4 h-4 mr-2" /> Renew / Extend Subscription
                  </Button>
                  <Button
                    variant="outline"
                    className="border-blue-200"
                    data-testid="wallet-topup-btn"
                    onClick={() => {
                      window.location.href = "/operator/wallet";
                    }}
                  >
                    <Wallet className="w-4 h-4 mr-2" />
                    Topup Wallet
                  </Button>
                </div>
              )}
          </CardContent>
        </Card>

        {/* Available Plans */}
        {subscription?.available_plans?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Available Plans</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {subscription.available_plans.map((plan) => (
                  <div
                    key={plan.id}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      subscription.saas_plan_id === plan.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-slate-200"
                    }`}
                    data-testid={`plan-option-${plan.id}`}
                  >
                    {subscription.saas_plan_id === plan.id && (
                      <div className="flex items-center gap-1.5 mb-2">
                        <span className="text-[10px] font-semibold bg-blue-600 text-white px-2 py-0.5 rounded">
                          CURRENT
                        </span>
                        {subscription.plan_validation?.is_valid && (
                          <span className="text-[9px] text-green-700 bg-green-100 px-1.5 py-0.5 rounded">
                            ✓ Verified
                          </span>
                        )}
                        {subscription.plan_validation && !subscription.plan_validation.is_valid && (
                          <span className="text-[9px] text-red-700 bg-red-100 px-1.5 py-0.5 rounded">
                            ⚠ Mismatch
                          </span>
                        )}
                      </div>
                    )}
                    <p className="font-semibold text-slate-900">{plan.name}</p>
                    <p className="text-2xl font-bold mt-1">
                      ₹{plan.monthly_price?.toLocaleString("en-IN")}
                      <span className="text-sm font-normal text-slate-500">/month</span>
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">GST inclusive · ₹{plan.per_invoice_price ?? 10}/invoice</p>
                    {(plan.included_addons || []).length > 0 && (
                      <p className="text-xs text-blue-600 mt-1 font-medium">{(plan.included_addons || []).length} add-on(s) included</p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Add-ons Store */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Puzzle className="w-5 h-5" />
              Add-ons
            </CardTitle>
            <p className="text-sm text-slate-500 mt-1">
              Enhance your platform with powerful add-ons
            </p>
          </CardHeader>
          <CardContent>
            {isTrial && (
              <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
                <Zap className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-amber-800">Add-on purchases are not available on the Trial plan. Please subscribe to a paid plan to unlock add-ons.</p>
              </div>
            )}
            {addons.length === 0 ? (
              <div className="py-10 text-center text-slate-500">
                <Puzzle className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                <p className="font-medium">No add-ons available</p>
                <p className="text-sm mt-1">Check back later for new features</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {addons.map((addon) => {
                  const isOwned =
                    addon.status === "purchased" ||
                    addon.status === "included_in_plan";
                  return (
                    <div
                      key={addon.code}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        isOwned
                          ? "border-emerald-200 bg-emerald-50/40"
                          : "border-slate-200 hover:border-slate-300 hover:shadow-sm"
                      }`}
                      data-testid={`addon-card-${addon.code}`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                              isOwned ? "bg-emerald-100" : "bg-slate-100"
                            }`}
                          >
                            {isOwned ? (
                              <Check className="w-5 h-5 text-emerald-600" />
                            ) : (
                              <Puzzle className="w-5 h-5 text-slate-600" />
                            )}
                          </div>
                          <p className="font-semibold text-slate-900 text-sm">
                            {addon.name}
                          </p>
                        </div>
                        {getAddonStatusBadge(addon.status)}
                      </div>

                      <p className="text-xs text-slate-500 min-h-[32px] mb-3">
                        {addon.description || "Enhance your platform capabilities"}
                      </p>

                      {/* Expiry date for owned addons */}
                      {isOwned && addon.expires_at && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2">
                          <Calendar className="w-3.5 h-3.5" />
                          <span>
                            Expires:{" "}
                            <span className="font-medium text-slate-700">
                              {new Date(addon.expires_at).toLocaleDateString("en-IN", {
                                day: "numeric", month: "short", year: "numeric"
                              })}
                            </span>
                          </span>
                        </div>
                      )}

                      <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                        <div>
                          {addon.status === "included_in_plan" ? (
                            <span className="text-base font-bold text-blue-600">Free</span>
                          ) : (
                            <>
                              <span className="text-xl font-bold text-slate-900">
                                ₹{addon.price}
                              </span>
                              <span className="text-xs text-slate-500">/mo</span>
                            </>
                          )}
                        </div>

                        {isOwned ? (
                          <span className="text-sm font-medium text-emerald-600 flex items-center gap-1">
                            <Check className="w-4 h-4" /> Enabled
                          </span>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => setShowAddonConfirm(addon)}
                            disabled={purchasing === addon.code || isTrial}
                            title={isTrial ? "Subscribe to a paid plan to purchase add-ons" : undefined}
                            data-testid={`buy-addon-${addon.code}`}
                          >
                            {purchasing === addon.code ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                                Processing
                              </>
                            ) : (
                              <>
                                <Zap className="w-4 h-4 mr-1" /> Get Add-on
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
        </>
        )}



        {activeTab === "history" && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="w-5 h-5" />
                Payment History
              </CardTitle>
              <p className="text-sm text-slate-500 mt-1">All your SaaS platform payments</p>
            </CardHeader>
            <CardContent className="p-0">
              {paymentHistory.length === 0 ? (
                <div className="py-12 text-center text-slate-500">
                  <History className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                  <p className="font-medium">No payments yet</p>
                  <p className="text-sm mt-1">Your subscription and add-on payments will appear here</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Type</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Description</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Amount</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paymentHistory.map((p, i) => (
                        <tr key={p.id || p.transaction_id || i} className="border-b border-slate-50 hover:bg-slate-50 transition-colors" data-testid={`history-row-${i}`}>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                              p.item_type === "subscription"
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-purple-100 text-purple-700"
                            }`}>
                              {p.item_type === "subscription" ? "Subscription" : "Add-on"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-700">
                            {p.item_type === "addon" ? p.item_code : "Plan Renewal"}
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-slate-900">₹{p.total_amount?.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-slate-500">
                            {p.created_at ? new Date(p.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-slate-50 border-t-2 border-slate-200">
                        <td colSpan={2} className="px-4 py-3 font-semibold text-slate-700 text-right">Total Paid</td>
                        <td className="px-4 py-3 text-right font-bold text-slate-900">
                          ₹{paymentHistory.reduce((s, p) => s + (p.total_amount || 0), 0).toLocaleString("en-IN")}
                        </td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Renew Subscription Dialog */}
      <Dialog open={showRenewDialog} onOpenChange={(open) => {
        setShowRenewDialog(open);
        if (!open) {
          setSelectedAddonCodes([]);
          setRenewCoupon("");
          setRenewCouponResult(null);
        }
      }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Renew / Purchase Subscription</DialogTitle>
            <DialogDescription>
              1-month renewal. All prices are GST inclusive. Existing add-ons are auto-renewed.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Select Plan</Label>
              <Select value={selectedPlan} onValueChange={setSelectedPlan}>
                <SelectTrigger data-testid="renew-plan-select">
                  <SelectValue placeholder="Choose a plan" />
                </SelectTrigger>
                <SelectContent>
                  {(subscription?.available_plans || []).map((plan) => (
                    <SelectItem key={plan.id} value={plan.id}>
                      {plan.name} — ₹{plan.monthly_price?.toLocaleString("en-IN")}/mo
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Owned addons that will auto-renew */}
            {ownedPurchasedAddons.length > 0 && (
              <div className="space-y-2">
                <Label>Add-ons (auto-renewed with plan)</Label>
                <div className="border border-slate-200 rounded-lg p-3 space-y-1.5 bg-slate-50">
                  {ownedPurchasedAddons.map((addon) => (
                    <div key={addon.code} className="flex items-center justify-between text-sm">
                      <span className="text-slate-700 font-medium flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full inline-block"></span>
                        {addon.name}
                      </span>
                      <span className="text-slate-500">₹{addon.price}/mo</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* New add-ons bundling section */}
            <div className="space-y-2">
              <Label>Add New Add-ons (optional)</Label>
              {purchasableAddons.length === 0 ? (
                <p className="text-sm text-slate-400 italic px-1">
                  All available add-ons are already active on your account.
                </p>
              ) : (
                <div className="space-y-2 border border-slate-200 rounded-lg p-3 max-h-40 overflow-y-auto">
                  {purchasableAddons.map((addon) => (
                    <label
                      key={addon.code}
                      className="flex items-center gap-3 cursor-pointer hover:bg-slate-50 rounded p-1"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAddonCodes.includes(addon.code)}
                        onChange={() => toggleAddonSelection(addon.code)}
                        className="w-4 h-4 rounded border-slate-300 text-blue-600"
                      />
                      <span className="flex-1 text-sm font-medium text-slate-700">{addon.name}</span>
                      <span className="text-sm text-slate-500">+₹{addon.price}/mo</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Discount Code */}
            <div className="space-y-2">
              <Label>Discount Code</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter coupon code"
                  value={renewCoupon}
                  onChange={(e) => { setRenewCoupon(e.target.value.toUpperCase()); setRenewCouponResult(null); }}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={applyRenewCoupon}
                  disabled={!renewCoupon.trim() || renewCouponLoading}
                >
                  {renewCouponLoading ? "..." : "Apply"}
                </Button>
              </div>
              {renewCouponResult?.valid && (
                <p className="text-sm text-emerald-600 font-medium">
                  ✓ {renewCouponResult.message}
                </p>
              )}
            </div>

            {selectedPlanDetails && (
              <div className="p-4 bg-slate-50 rounded-lg space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">
                    {selectedPlanDetails.name} × 1 month
                  </span>
                  <span>₹{baseAmount.toLocaleString("en-IN")}</span>
                </div>
                {ownedAddonTotal > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">
                      Existing add-ons renewal ({ownedPurchasedAddons.length})
                    </span>
                    <span>₹{ownedAddonTotal.toLocaleString("en-IN")}</span>
                  </div>
                )}
                {selectedAddonTotal > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">
                      New add-ons ({selectedAddonCodes.length})
                    </span>
                    <span>₹{selectedAddonTotal.toLocaleString("en-IN")}</span>
                  </div>
                )}
                {renewDiscount > 0 && (
                  <div className="flex justify-between text-sm text-emerald-600">
                    <span>Discount ({renewCouponResult?.code})</span>
                    <span>-₹{renewDiscount.toLocaleString("en-IN")}</span>
                  </div>
                )}
                <div className="flex justify-between text-xs text-slate-400 border-t pt-2 mt-1">
                  <span>All prices are GST inclusive</span>
                </div>
                {roundingDiff !== 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Rounding</span>
                    <span className={roundingDiff > 0 ? "text-red-500" : "text-emerald-600"}>
                      {roundingDiff > 0
                        ? `+₹${roundingDiff.toFixed(2)}`
                        : `-₹${Math.abs(roundingDiff).toFixed(2)}`}
                    </span>
                  </div>
                )}
                <div className="flex justify-between font-semibold border-t pt-2 mt-2">
                  <span>Total</span>
                  <span data-testid="renew-total">
                    ₹{totalAmount.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRenewDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRenew}
              disabled={!selectedPlan || processing || isMaintenance}
              data-testid="confirm-renew-btn"
            >
              {processing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Processing...
                </>
              ) : (
                <>
                  <CreditCard className="w-4 h-4 mr-2" /> Pay Now
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add-on Purchase Confirm Dialog */}
      <Dialog
        open={!!showAddonConfirm}
        onOpenChange={(open) => { if (!open) { setShowAddonConfirm(null); setAddonCoupon(""); setAddonCouponResult(null); } }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Purchase Add-on</DialogTitle>
            <DialogDescription>
              You're about to purchase{" "}
              <strong>{showAddonConfirm?.name}</strong>
            </DialogDescription>
          </DialogHeader>
          {showAddonConfirm && (() => {
              const base = showAddonConfirm.price;
              const addonDiscount = addonCouponResult?.valid
                ? parseFloat((addonCouponResult.discount_type === "percentage"
                    ? base * addonCouponResult.discount_value / 100
                    : Math.min(addonCouponResult.discount_value, base)).toFixed(2))
                : 0;
              const discBase = parseFloat((base - addonDiscount).toFixed(2));
              const rounded = Math.round(discBase);
              const diff = parseFloat((rounded - discBase).toFixed(2));
              return (
                <div className="space-y-3 py-4">
                  <p className="text-sm text-slate-600">
                    {showAddonConfirm.description}
                  </p>
                  <div className="p-4 bg-slate-50 rounded-lg space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Price (GST inclusive)</span>
                      <span>₹{base.toLocaleString("en-IN")}</span>
                    </div>
                    {addonDiscount > 0 && (
                      <div className="flex justify-between text-sm text-emerald-600">
                        <span>Discount ({addonCouponResult?.code})</span>
                        <span>-₹{addonDiscount.toLocaleString("en-IN")}</span>
                      </div>
                    )}
                    {diff !== 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-500">Rounding</span>
                        <span className={diff > 0 ? "text-red-500" : "text-emerald-600"}>
                          {diff > 0 ? `+₹${diff.toFixed(2)}` : `-₹${Math.abs(diff).toFixed(2)}`}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between font-semibold border-t pt-2 mt-1">
                      <span>Total</span>
                      <span data-testid="addon-purchase-total">
                        ₹{rounded.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>
                  {/* Discount Code */}
                  <div className="space-y-1.5">
                    <Label className="text-sm">Discount Code</Label>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Enter coupon code"
                        value={addonCoupon}
                        onChange={(e) => { setAddonCoupon(e.target.value.toUpperCase()); setAddonCouponResult(null); }}
                        className="flex-1 h-8 text-sm"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => applyAddonCoupon(base)}
                        disabled={!addonCoupon.trim() || addonCouponLoading}
                      >
                        {addonCouponLoading ? "..." : "Apply"}
                      </Button>
                    </div>
                    {addonCouponResult?.valid && (
                      <p className="text-xs text-emerald-600 font-medium">✓ {addonCouponResult.message}</p>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    Razorpay checkout will open to complete your payment securely.
                  </p>
                </div>
              );
            })()}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddonConfirm(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => handleAddonPurchase(showAddonConfirm)}
              data-testid="confirm-addon-purchase-btn"
            >
              <CreditCard className="w-4 h-4 mr-2" /> Pay Now
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </OperatorLayout>
  );
};

export default OperatorSubscription;
