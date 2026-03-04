import { useState, useEffect } from "react";
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
import { CreditCard, Calendar, AlertTriangle, CheckCircle, ExternalLink, Clock } from "lucide-react";

const OperatorSubscription = () => {
  const { authAxios } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showRenewDialog, setShowRenewDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [months, setMonths] = useState("1");
  const [renewing, setRenewing] = useState(false);
  const [paymentResult, setPaymentResult] = useState(null);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const res = await authAxios.get("/operator/subscription");
      setSubscription(res.data);
      if (res.data.saas_plan_id) {
        setSelectedPlan(res.data.saas_plan_id);
      }
    } catch (error) {
      toast.error("Failed to load subscription details");
    } finally {
      setLoading(false);
    }
  };

  const handleRenew = async () => {
    if (!selectedPlan) {
      toast.error("Please select a plan");
      return;
    }
    setRenewing(true);
    try {
      const res = await authAxios.post(`/operator/renew-subscription?plan_id=${selectedPlan}&months=${months}`);
      setPaymentResult(res.data);
      setShowRenewDialog(false);
      toast.success("Renewal initiated! Complete the payment.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to initiate renewal");
    } finally {
      setRenewing(false);
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
    if (subscription?.subscription_ends_at) return new Date(subscription.subscription_ends_at);
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
    const diff = Math.ceil((expiry - new Date()) / (1000 * 60 * 60 * 24));
    return diff;
  };

  const selectedPlanDetails = subscription?.available_plans?.find(p => p.id === selectedPlan);
  const totalAmount = selectedPlanDetails
    ? selectedPlanDetails.monthly_price * parseInt(months || "1")
    : 0;

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

  return (
    <OperatorLayout title="Subscription" isReadOnly={subscription?.is_read_only}>
      <div className="max-w-3xl space-y-6 animate-fade-in">
        {/* Current Subscription Status */}
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
                  <span className={`text-lg font-bold text-${statusInfo.color}-700 capitalize`} data-testid="subscription-status">
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
                  <p className="text-sm text-slate-500">₹{subscription.saas_plan_price}/month</p>
                )}
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">
                  {subscription?.status === "trial" ? "Trial Expires" : "Expires On"}
                </p>
                <p className="text-lg font-bold text-slate-900" data-testid="expiry-date">
                  {getExpiryDate()
                    ? getExpiryDate().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                    : "N/A"}
                </p>
                {days !== null && (
                  <p className={`text-sm ${days < 0 ? 'text-red-600 font-medium' : days < 7 ? 'text-amber-600' : 'text-slate-500'}`}>
                    {days < 0 ? `Expired ${Math.abs(days)} days ago` : `${days} days remaining`}
                  </p>
                )}
              </div>
            </div>

            {/* Renewal CTA */}
            {(isExpired() || subscription?.is_read_only || subscription?.status === "trial" || (days !== null && days < 15)) && (
              <div className={`p-4 rounded-lg border flex items-center justify-between ${
                isExpired() ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'
              }`}>
                <div className="flex items-center gap-3">
                  <AlertTriangle className={`w-5 h-5 ${isExpired() ? 'text-red-600' : 'text-amber-600'}`} />
                  <div>
                    <p className={`font-medium ${isExpired() ? 'text-red-800' : 'text-amber-800'}`}>
                      {isExpired() ? "Your subscription has expired" : subscription?.status === "trial" ? "Your trial is ending soon" : "Your subscription is expiring soon"}
                    </p>
                    <p className={`text-sm ${isExpired() ? 'text-red-600' : 'text-amber-600'}`}>
                      {isExpired() ? "Renew now to regain full access." : "Renew early to avoid any disruption."}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={() => setShowRenewDialog(true)}
                  className={isExpired() ? "bg-red-600 hover:bg-red-700" : "bg-amber-600 hover:bg-amber-700"}
                  data-testid="renew-now-btn"
                >
                  Renew Now
                </Button>
              </div>
            )}

            {/* Always show renew option */}
            {!isExpired() && !subscription?.is_read_only && subscription?.status !== "trial" && (days === null || days >= 15) && (
              <Button variant="outline" onClick={() => setShowRenewDialog(true)} data-testid="renew-early-btn">
                <Calendar className="w-4 h-4 mr-2" /> Renew / Extend Subscription
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Payment Result */}
        {paymentResult && (
          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-6 h-6 text-emerald-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-emerald-900">Payment Link Generated</h3>
                  <p className="text-sm text-emerald-700 mt-1">
                    {paymentResult.plan_name} x {paymentResult.months} month(s) — ₹{paymentResult.total_amount?.toLocaleString('en-IN')}
                  </p>
                  {paymentResult.payment_link && (
                    <a
                      href={paymentResult.payment_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium"
                      data-testid="payment-link"
                    >
                      <ExternalLink className="w-4 h-4" /> Complete Payment
                    </a>
                  )}
                  {!paymentResult.payment_link && (
                    <p className="text-sm text-amber-700 mt-2">
                      Payment gateway not configured. Please contact admin to complete your renewal.
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

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
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                      subscription.saas_plan_id === plan.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    data-testid={`plan-option-${plan.id}`}
                  >
                    {subscription.saas_plan_id === plan.id && (
                      <span className="text-[10px] font-semibold bg-blue-600 text-white px-2 py-0.5 rounded mb-2 inline-block">CURRENT</span>
                    )}
                    <p className="font-semibold text-slate-900">{plan.name}</p>
                    <p className="text-2xl font-bold mt-1">
                      ₹{plan.monthly_price.toLocaleString('en-IN')}
                      <span className="text-sm font-normal text-slate-500">/month</span>
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Renew Dialog */}
        <Dialog open={showRenewDialog} onOpenChange={setShowRenewDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Renew Subscription</DialogTitle>
              <DialogDescription>Choose a plan and duration to renew your subscription.</DialogDescription>
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
              {selectedPlanDetails && (
                <div className="p-4 bg-slate-50 rounded-lg space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">{selectedPlanDetails.name} x {months} month(s)</span>
                    <span>₹{totalAmount.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">GST (18%)</span>
                    <span>₹{Math.round(totalAmount * 0.18).toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex justify-between font-semibold border-t pt-2 mt-2">
                    <span>Total</span>
                    <span data-testid="renew-total">₹{Math.round(totalAmount * 1.18).toLocaleString('en-IN')}</span>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowRenewDialog(false)}>Cancel</Button>
              <Button onClick={handleRenew} disabled={!selectedPlan || renewing} data-testid="confirm-renew-btn">
                {renewing ? "Processing..." : "Generate Payment Link"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorSubscription;
