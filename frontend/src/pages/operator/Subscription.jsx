import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
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
} from "lucide-react";

const OperatorSubscription = () => {
  const { authAxios } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [addons, setAddons] = useState([]);
  const [paymentHistory, setPaymentHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("subscription"); // subscription | history
  const [showRenewDialog, setShowRenewDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [months, setMonths] = useState("1");
  const [processing, setProcessing] = useState(false);
  const [purchasing, setPurchasing] = useState(null);
  const [showAddonConfirm, setShowAddonConfirm] = useState(null);
  // Addons to bundle with subscription renewal
  const [selectedAddonCodes, setSelectedAddonCodes] = useState([]);

  const fetchSubscription = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/subscription");
      setSubscription(res.data);
      if (res.data.saas_plan_id) setSelectedPlan(res.data.saas_plan_id);
    } catch {
      toast.error("Failed to load subscription details");
    }
  }, [authAxios]);

  const fetchAddons = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/addons/store");
      setAddons(res.data);
    } catch {
      // silently fail
    }
  }, [authAxios]);

  const fetchPaymentHistory = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/payment-history");
      setPaymentHistory(res.data);
    } catch {
      // silently fail
    }
  }, [authAxios]);

  useEffect(() => {
    Promise.all([fetchSubscription(), fetchAddons(), fetchPaymentHistory()]).finally(() =>
      setLoading(false)
    );
  }, [fetchSubscription, fetchAddons, fetchPaymentHistory]);

  const openRazorpay = (orderData, onSuccess) => {
    if (!window.Razorpay) {
      toast.error("Payment gateway not loaded. Please refresh the page.");
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
    if (!selectedPlan) {
      toast.error("Please select a plan");
      return;
    }
    setProcessing(true);
    try {
      const addonParam = selectedAddonCodes.length > 0 ? `&addon_codes=${selectedAddonCodes.join(",")}` : "";
      const res = await authAxios.post(
        `/operator/checkout/create-order?item_type=subscription&plan_id=${selectedPlan}&months=${months}${addonParam}`
      );
      setShowRenewDialog(false);
      setSelectedAddonCodes([]);
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

  const handleAddonPurchase = async (addon) => {
    setShowAddonConfirm(null);
    setPurchasing(addon.code);
    try {
      const res = await authAxios.post(
        `/operator/checkout/create-order?item_type=addon&item_code=${addon.code}`
      );
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
  const baseAmount = selectedPlanDetails
    ? selectedPlanDetails.monthly_price * parseInt(months || "1")
    : 0;
  // Addons available to bundle (not already owned)
  const purchasableAddons = addons.filter(
    (a) => a.status !== "purchased" && a.status !== "included_in_plan"
  );
  const selectedAddonTotal = purchasableAddons
    .filter((a) => selectedAddonCodes.includes(a.code))
    .reduce((sum, a) => sum + a.price, 0);
  const combinedBase = baseAmount + selectedAddonTotal;
  // Rounding: compute exact (base + GST) then round to integer
  const gstAmount = parseFloat((combinedBase * 0.18).toFixed(2));
  const exactTotal = parseFloat((combinedBase + gstAmount).toFixed(2));
  const totalAmount = Math.round(exactTotal);
  const roundingDiff = parseFloat((totalAmount - exactTotal).toFixed(2));

  const toggleAddonSelection = (code) => {
    setSelectedAddonCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  return (
    <OperatorLayout title="Subscription" isReadOnly={subscription?.is_read_only}>
      <div className="max-w-4xl space-y-6 animate-fade-in">

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
                    ₹{subscription.saas_plan_price}/month
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
              </div>
            )}

            {/* Always-available renew button when subscription is healthy */}
            {!isExpired() &&
              !subscription?.is_read_only &&
              subscription?.status !== "trial" &&
              (days === null || days >= 15) && (
                <Button
                  variant="outline"
                  onClick={() => setShowRenewDialog(true)}
                  data-testid="renew-early-btn"
                >
                  <Calendar className="w-4 h-4 mr-2" /> Renew / Extend Subscription
                </Button>
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
                      <span className="text-[10px] font-semibold bg-blue-600 text-white px-2 py-0.5 rounded mb-2 inline-block">
                        CURRENT
                      </span>
                    )}
                    <p className="font-semibold text-slate-900">{plan.name}</p>
                    <p className="text-2xl font-bold mt-1">
                      ₹{plan.monthly_price.toLocaleString("en-IN")}
                      <span className="text-sm font-normal text-slate-500">/month</span>
                    </p>
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
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Base</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">GST</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Total</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paymentHistory.map((p, i) => (
                        <tr key={i} className="border-b border-slate-50 hover:bg-slate-50 transition-colors" data-testid={`history-row-${i}`}>
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
                          <td className="px-4 py-3 text-right text-slate-700">₹{p.base_amount?.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-right text-slate-500">₹{p.gst_amount?.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-right font-semibold text-slate-900">₹{p.total_amount?.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-slate-500">
                            {p.created_at ? new Date(p.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-slate-50 border-t-2 border-slate-200">
                        <td colSpan={4} className="px-4 py-3 font-semibold text-slate-700 text-right">Total Paid</td>
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
      <Dialog open={showRenewDialog} onOpenChange={(open) => { setShowRenewDialog(open); if (!open) setSelectedAddonCodes([]); }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Renew / Purchase Subscription</DialogTitle>
            <DialogDescription>
              Choose a plan and duration. You can also bundle add-ons. You will be redirected to Razorpay to complete payment.
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
                      {plan.name} — ₹{plan.monthly_price}/mo
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Duration</Label>
              <Select value={months} onValueChange={setMonths}>
                <SelectTrigger data-testid="renew-months-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 Month</SelectItem>
                  <SelectItem value="3">3 Months</SelectItem>
                  <SelectItem value="6">6 Months</SelectItem>
                  <SelectItem value="12">12 Months</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Add-ons bundling section */}
            {purchasableAddons.length > 0 && (
              <div className="space-y-2">
                <Label>Bundle Add-ons (optional)</Label>
                <div className="space-y-2 border border-slate-200 rounded-lg p-3 max-h-48 overflow-y-auto">
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
              </div>
            )}

            {selectedPlanDetails && (
              <div className="p-4 bg-slate-50 rounded-lg space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">
                    {selectedPlanDetails.name} × {months} month(s)
                  </span>
                  <span>₹{baseAmount.toLocaleString("en-IN")}</span>
                </div>
                {selectedAddonTotal > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">
                      Add-ons ({selectedAddonCodes.length})
                    </span>
                    <span>₹{selectedAddonTotal.toLocaleString("en-IN")}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">GST (18%)</span>
                  <span>₹{gstAmount.toLocaleString("en-IN")}</span>
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
                  <span>Total (Rounded)</span>
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
              disabled={!selectedPlan || processing}
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
        onOpenChange={(open) => !open && setShowAddonConfirm(null)}
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
              const gst = parseFloat((base * 0.18).toFixed(2));
              const exact = parseFloat((base + gst).toFixed(2));
              const rounded = Math.round(exact);
              const diff = parseFloat((rounded - exact).toFixed(2));
              return (
                <div className="space-y-3 py-4">
                  <p className="text-sm text-slate-600">
                    {showAddonConfirm.description}
                  </p>
                  <div className="p-4 bg-slate-50 rounded-lg space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Base Price</span>
                      <span>₹{base.toLocaleString("en-IN")}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">GST (18%)</span>
                      <span>₹{gst.toLocaleString("en-IN")}</span>
                    </div>
                    {diff !== 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-500">Rounding</span>
                        <span className={diff > 0 ? "text-red-500" : "text-emerald-600"}>
                          {diff > 0 ? `+₹${diff.toFixed(2)}` : `-₹${Math.abs(diff).toFixed(2)}`}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between font-semibold border-t pt-2 mt-1">
                      <span>Total (Rounded)</span>
                      <span data-testid="addon-purchase-total">
                        ₹{rounded.toLocaleString("en-IN")}
                      </span>
                    </div>
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
