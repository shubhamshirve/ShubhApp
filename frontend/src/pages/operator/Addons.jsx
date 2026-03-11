import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import { toast } from "sonner";
import { Puzzle, Check, ExternalLink, ShoppingCart, Zap, Loader2 } from "lucide-react";

const OperatorAddons = () => {
  const { authAxios, user } = useAuth();
  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const [paymentResult, setPaymentResult] = useState(null);
  const [showConfirm, setShowConfirm] = useState(null);
  const [activating, setActivating] = useState(null);
  const [subscriptionStatus, setSubscriptionStatus] = useState(null);

  useEffect(() => { fetchAddons(); fetchSubscription(); }, []);

  const fetchSubscription = async () => {
    try {
      const res = await authAxios.get("/operator/subscription");
      setSubscriptionStatus(res.data?.status);
    } catch { /* silent */ }
  };

  const fetchAddons = async () => {
    try {
      const res = await authAxios.get("/operator/addons/store");
      setAddons(res.data);
    } catch (error) {
      toast.error("Failed to load add-ons");
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async (addon) => {
    setShowConfirm(null);
    setPurchasing(addon.code);
    try {
      const res = await authAxios.post(`/operator/addons/purchase?addon_code=${addon.code}`);
      if (res.data.status === "activated") {
        toast.success(res.data.message);
        fetchAddons();
      } else if (res.data.payment_link) {
        setPaymentResult(res.data);
        toast.success("Payment link generated!");
      } else {
        setPaymentResult(res.data);
        toast.info("Purchase initiated. Contact admin to complete payment.");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to purchase add-on");
    } finally {
      setPurchasing(null);
    }
  };

  const handleActivate = async (addon) => {
    setActivating(addon.code);
    try {
      const res = await authAxios.post(`/operator/addons/activate?addon_code=${addon.code}`);
      toast.success(res.data.message);
      setPaymentResult(null);
      fetchAddons();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to activate");
    } finally {
      setActivating(null);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "purchased":
        return <span className="text-xs font-semibold bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full" data-testid="badge-purchased">Active</span>;
      case "included_in_plan":
        return <span className="text-xs font-semibold bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full" data-testid="badge-included">Included in Plan</span>;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <OperatorLayout title="Add-ons Store">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  return (
    <OperatorLayout title="Add-ons Store">
      <div className="space-y-6 animate-fade-in">
        <p className="text-slate-500">Enhance your platform with powerful add-ons</p>

        {/* Trial restriction banner */}
        {subscriptionStatus === "trial" && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
            <Zap className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium text-amber-800">Add-on purchases are not available on the Trial plan</p>
              <p className="text-sm text-amber-700 mt-1">Please subscribe to a paid plan to unlock add-ons.</p>
            </div>
          </div>
        )}

        {/* Payment Result Banner */}
        {paymentResult && paymentResult.payment_link && (
          <Card className="border-emerald-200 bg-emerald-50" data-testid="payment-result-card">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <ShoppingCart className="w-6 h-6 text-emerald-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-emerald-900">Payment Link Ready</h3>
                  <p className="text-sm text-emerald-700 mt-1">
                    {paymentResult.addon_name} — ₹{paymentResult.total_amount?.toLocaleString('en-IN')} (incl. GST)
                  </p>
                  <div className="flex gap-3 mt-3">
                    <a
                      href={paymentResult.payment_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium"
                      data-testid="pay-now-link"
                    >
                      <ExternalLink className="w-4 h-4" /> Pay Now
                    </a>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleActivate({ code: paymentResult.addon_code })}
                      disabled={activating === paymentResult.addon_code}
                      data-testid="activate-after-payment-btn"
                    >
                      {activating === paymentResult.addon_code 
                        ? <><Loader2 className="w-4 h-4 mr-1 animate-spin" /> Activating...</>
                        : <><Check className="w-4 h-4 mr-1" /> I've Paid — Activate Now</>
                      }
                    </Button>
                  </div>
                  <p className="text-xs text-emerald-600 mt-2">
                    Complete payment, then click "Activate Now" to enable the add-on.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {paymentResult && !paymentResult.payment_link && paymentResult.status !== "activated" && (
          <Card className="border-amber-200 bg-amber-50">
            <CardContent className="pt-6">
              <p className="text-amber-800 text-sm">
                Payment gateway not configured. Please contact your platform admin to complete the purchase of <strong>{paymentResult.addon_name}</strong>.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Add-ons Grid */}
        {addons.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-slate-500">
              <Puzzle className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="font-medium">No add-ons available</p>
              <p className="text-sm mt-1">Check back later for new features</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {addons.map((addon) => {
              const isOwned = addon.status === "purchased" || addon.status === "included_in_plan";
              return (
                <Card 
                  key={addon.code} 
                  className={`relative transition-all ${isOwned ? 'border-emerald-200 bg-emerald-50/30' : 'hover:shadow-md hover:border-slate-300'}`}
                  data-testid={`addon-card-${addon.code}`}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${isOwned ? 'bg-emerald-100' : 'bg-slate-100'}`}>
                          {isOwned 
                            ? <Check className="w-5 h-5 text-emerald-600" /> 
                            : <Puzzle className="w-5 h-5 text-slate-600" />
                          }
                        </div>
                        {addon.name}
                      </CardTitle>
                      {getStatusBadge(addon.status)}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-slate-500 min-h-[40px]">
                      {addon.description || "Enhance your platform capabilities"}
                    </p>
                    
                    <div className="flex items-end justify-between pt-2 border-t">
                      <div>
                        {addon.status === "included_in_plan" ? (
                          <span className="text-lg font-bold text-blue-600">Free</span>
                        ) : (
                          <>
                            <span className="text-2xl font-bold text-slate-900">₹{addon.price}</span>
                            <span className="text-sm text-slate-500">/mo</span>
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
                          onClick={() => setShowConfirm(addon)}
                          disabled={purchasing === addon.code || subscriptionStatus === "trial"}
                          title={subscriptionStatus === "trial" ? "Subscribe to a paid plan to purchase add-ons" : undefined}
                          data-testid={`buy-addon-${addon.code}`}
                        >
                          {purchasing === addon.code 
                            ? <><Loader2 className="w-4 h-4 mr-1 animate-spin" /> Processing</>
                            : <><Zap className="w-4 h-4 mr-1" /> Get Add-on</>
                          }
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Purchase Confirmation Dialog */}
        <Dialog open={!!showConfirm} onOpenChange={(open) => !open && setShowConfirm(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Purchase Add-on</DialogTitle>
              <DialogDescription>
                You're about to purchase <strong>{showConfirm?.name}</strong>
              </DialogDescription>
            </DialogHeader>
            {showConfirm && (() => {
              const base = showConfirm.price;
              const gst = parseFloat((base * 0.18).toFixed(2));
              const exact = parseFloat((base + gst).toFixed(2));
              const rounded = Math.round(exact);
              const diff = parseFloat((rounded - exact).toFixed(2));
              return (
                <div className="space-y-3 py-4">
                  <p className="text-sm text-slate-600">{showConfirm.description}</p>
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
                      <span data-testid="purchase-total">₹{rounded.toLocaleString("en-IN")}</span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">
                    A Razorpay payment link will be generated. Complete the payment to activate the add-on.
                  </p>
                </div>
              );
            })()}
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowConfirm(null)}>Cancel</Button>
              <Button onClick={() => handlePurchase(showConfirm)} data-testid="confirm-purchase-btn">
                <ShoppingCart className="w-4 h-4 mr-2" /> Proceed to Pay
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorAddons;
