import { useState, useEffect, useCallback } from "react";
import { OperatorLayout } from "../../components/Layout";
import { useAuth } from "../../App";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { toast } from "sonner";
import {
  Wallet, TrendingUp, TrendingDown, Plus, Copy, Gift, AlertTriangle,
  ArrowUpRight, ArrowDownLeft, RefreshCw, History
} from "lucide-react";

export default function WalletPage() {
  const { authAxios, user } = useAuth();
  const [wallet, setWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [topupAmount, setTopupAmount] = useState("");
  const [topupLoading, setTopupLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [totalTxns, setTotalTxns] = useState(0);
  const LIMIT = 20;

  const fetchWallet = useCallback(async () => {
    try {
      const res = await authAxios.get("/operator/wallet");
      setWallet(res.data);
    } catch (err) {
      toast.error("Failed to load wallet");
    }
  }, [authAxios]);

  const fetchTransactions = useCallback(async (p = 0) => {
    try {
      const res = await authAxios.get(`/operator/wallet/transactions?skip=${p * LIMIT}&limit=${LIMIT}`);
      setTransactions(res.data.transactions || []);
      setTotalTxns(res.data.total || 0);
    } catch (err) {
      toast.error("Failed to load transactions");
    }
  }, [authAxios]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([fetchWallet(), fetchTransactions(0)]);
      setLoading(false);
    };
    load();
  }, [fetchWallet, fetchTransactions]);

  const handlePageChange = (p) => {
    setPage(p);
    fetchTransactions(p);
  };

  const copyReferralCode = () => {
    if (wallet?.referral_code) {
      navigator.clipboard.writeText(wallet.referral_code);
      toast.success("Referral code copied!");
    }
  };

  const handleTopup = async () => {
    const amt = parseFloat(topupAmount);
    if (!amt || amt < 100) {
      toast.error("Minimum topup amount is Rs.100");
      return;
    }
    if (amt > 50000) {
      toast.error("Maximum topup amount is Rs.50,000");
      return;
    }
    setTopupLoading(true);
    try {
      const res = await authAxios.post(`/operator/wallet/topup/create-order?amount=${amt}`);
      const orderData = res.data;

      if (!window.Razorpay) {
        toast.error("Payment gateway not loaded. Please refresh the page.");
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
              `Wallet credited Rs.${verifyRes.data.credited_amount?.toFixed?.(2) ?? verifyRes.data.credited_amount}. ` +
              `Paid Rs.${verifyRes.data.paid_amount?.toFixed?.(2) ?? verifyRes.data.paid_amount}. ` +
              `New balance: Rs.${verifyRes.data.new_balance?.toFixed?.(2) ?? verifyRes.data.new_balance}`
            );
            setTopupAmount("");
            await fetchWallet();
            await fetchTransactions(0);
            setPage(0);
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
      toast.error(err.response?.data?.detail || "Failed to create topup order");
      setTopupLoading(false);
    }
  };

  const getTxIcon = (type) => {
    if (["topup", "credit", "subscription_credit", "referral_reward"].includes(type)) {
      return <ArrowUpRight className="w-4 h-4 text-green-600" />;
    }
    return <ArrowDownLeft className="w-4 h-4 text-red-500" />;
  };

  const getTxColor = (type) => {
    if (["topup", "credit", "subscription_credit", "referral_reward"].includes(type)) {
      return "text-green-700";
    }
    return "text-red-600";
  };

  const getTxBadge = (type) => {
    const map = {
      topup: { label: "Topup", variant: "default" },
      credit: { label: "Credit", variant: "default" },
      subscription_credit: { label: "Subscription", variant: "secondary" },
      referral_reward: { label: "Referral Reward", variant: "outline" },
      deduction: { label: "Deduction", variant: "destructive" },
    };
    return map[type] || { label: type, variant: "outline" };
  };

  const totalPages = Math.ceil(totalTxns / LIMIT);

  if (loading) {
    return (
      <OperatorLayout title="Wallet">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </OperatorLayout>
    );
  }

  const balance = wallet?.balance ?? 0;
  const isLow = balance < 500;
  const isCritical = balance < 100;

  return (
    <OperatorLayout title="Wallet">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Suspension Alert */}
        {wallet?.wallet_suspended && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3" data-testid="wallet-suspended-banner">
            <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-red-800">Account Suspended — Low Wallet Balance</p>
              <p className="text-sm text-red-700 mt-1">
                Your wallet balance is critically low. All automation has been stopped and your account is in read-only mode.
                Topup at least Rs.100 to resume service.
              </p>
            </div>
          </div>
        )}

        {/* Critical Balance Warning (not yet suspended) */}
        {isCritical && !wallet?.wallet_suspended && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3" data-testid="wallet-critical-banner">
            <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-red-800">Critical: Wallet Balance Below Rs.100</p>
              <p className="text-sm text-red-700 mt-1">
                Your balance is critically low. Please topup immediately — once balance reaches Rs.100, your account will be suspended and all automation will stop.
              </p>
            </div>
          </div>
        )}

        {/* Low Balance Warning */}
        {isLow && !isCritical && !wallet?.wallet_suspended && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3" data-testid="wallet-low-banner">
            <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-amber-800">Low Wallet Balance</p>
              <p className="text-sm text-amber-700 mt-1">
                Your wallet balance is below Rs.500. Please topup to keep services active.
                If balance drops below Rs.100, your account will be automatically suspended.
              </p>
            </div>
          </div>
        )}

        {/* Balance Card + Topup */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className={`border-2 ${isCritical ? 'border-red-300' : isLow ? 'border-amber-300' : 'border-green-200'}`} data-testid="wallet-balance-card">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isCritical ? 'bg-red-100' : isLow ? 'bg-amber-100' : 'bg-green-100'}`}>
                  <Wallet className={`w-6 h-6 ${isCritical ? 'text-red-600' : isLow ? 'text-amber-600' : 'text-green-600'}`} />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Wallet Balance</p>
                  <p className={`text-3xl font-bold ${isCritical ? 'text-red-600' : isLow ? 'text-amber-600' : 'text-slate-900'}`} data-testid="wallet-balance">
                    ₹{balance.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="text-xs text-slate-500 space-y-1">
                <p>• Per-invoice charges follow your active subscription plan</p>
                <p className={balance < 500 ? "text-amber-600 font-medium" : ""}>• Reminder when balance &lt; Rs.500</p>
                <p className={balance < 100 ? "text-red-600 font-medium" : ""}>• Account suspended when balance &lt; Rs.100</p>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="wallet-topup-card">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Plus className="w-4 h-4" /> Topup Wallet
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <label className="text-sm text-slate-600 mb-1 block">Wallet Credit Amount (Rs., before GST)</label>
                  <Input
                    type="number"
                    placeholder="Min wallet credit Rs.100"
                    value={topupAmount}
                    onChange={(e) => setTopupAmount(e.target.value)}
                    min={100}
                    max={50000}
                    data-testid="topup-amount-input"
                  />
                </div>
                <div className="flex gap-2 flex-wrap">
                  {[500, 1000, 2000, 5000].map((amt) => (
                    <button
                      key={amt}
                      onClick={() => setTopupAmount(String(amt))}
                      className="px-3 py-1 text-xs border border-slate-200 rounded-full hover:bg-slate-100 transition-colors"
                      data-testid={`quick-topup-${amt}`}
                    >
                      ₹{amt}
                    </button>
                  ))}
                </div>
                <Button
                  onClick={handleTopup}
                  disabled={topupLoading || !topupAmount}
                  className="w-full bg-[#0066B2] hover:bg-[#004080]"
                  data-testid="topup-submit-btn"
                >
                  {topupLoading ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
                  Pay & Topup
                </Button>
                <p className="text-xs text-slate-500">
                  GST is added at checkout. Your wallet is credited only with the pre-GST amount you enter.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Referral Card */}
        <Card data-testid="referral-card">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Gift className="w-4 h-4 text-purple-600" /> Referral Program
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-slate-500 mb-2">Your Referral Code</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-slate-100 px-3 py-2 rounded-lg font-mono text-sm font-bold text-[#0066B2]" data-testid="referral-code">
                    {wallet?.referral_code || "—"}
                  </code>
                  <Button variant="outline" size="sm" onClick={copyReferralCode} data-testid="copy-referral-btn">
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
                <p className="text-xs text-slate-400 mt-2">Share this code with other operators</p>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-start gap-2">
                  <TrendingDown className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                  <span className="text-slate-600">New operator using your code: <strong>You earn 5%</strong> of their payments for 3 months</span>
                </div>
                <div className="flex items-start gap-2">
                  <TrendingUp className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                  <span className="text-slate-600">If you registered with a code: <strong>10% off</strong> your first payment (up to Rs.500)</span>
                </div>
                {wallet?.referral_discount_used && (
                  <Badge variant="secondary" className="text-xs mt-1">Referral discount used</Badge>
                )}
                {wallet?.referred_by_code && !wallet?.referral_discount_used && (
                  <Badge variant="default" className="text-xs mt-1 bg-green-600">10% discount active on first payment!</Badge>
                )}
                {wallet?.referral_reward_active && (
                  <Badge variant="outline" className="text-xs mt-1 border-purple-300 text-purple-700">Referral rewards active (3-month window)</Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Transaction History */}
        <Card data-testid="wallet-transactions-card">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <History className="w-4 h-4" /> Transaction History
              <Badge variant="outline" className="ml-auto text-xs">{totalTxns} total</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {transactions.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <History className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No transactions yet</p>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  {transactions.map((tx) => {
                    const badge = getTxBadge(tx.type);
                    return (
                      <div
                        key={tx.id}
                        className="flex items-center gap-3 p-3 rounded-lg border border-slate-100 hover:bg-slate-50 transition-colors"
                        data-testid={`tx-item-${tx.id}`}
                      >
                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                          {getTxIcon(tx.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-800 truncate">{tx.description}</p>
                          <p className="text-xs text-slate-400">
                            {new Date(tx.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                          </p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className={`text-sm font-semibold ${getTxColor(tx.type)}`}>
                            {tx.amount > 0 ? "+" : ""}₹{Math.abs(tx.amount).toFixed(2)}
                          </p>
                          <p className="text-xs text-slate-400">Bal: ₹{tx.balance_after?.toFixed(2)}</p>
                        </div>
                        <Badge variant={badge.variant} className="text-xs hidden sm:flex">
                          {badge.label}
                        </Badge>
                      </div>
                    );
                  })}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page === 0}
                      onClick={() => handlePageChange(page - 1)}
                      data-testid="tx-prev-btn"
                    >
                      Previous
                    </Button>
                    <span className="text-sm text-slate-500">Page {page + 1} of {totalPages}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages - 1}
                      onClick={() => handlePageChange(page + 1)}
                      data-testid="tx-next-btn"
                    >
                      Next
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </OperatorLayout>
  );
}
