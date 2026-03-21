import { useState, useEffect } from "react";
import { AdminLayout } from "../../components/Layout";
import { useAuth } from "../../App";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { toast } from "sonner";
import {
  Wallet, AlertTriangle, TrendingDown, RefreshCw, Search,
  PlusCircle, MinusCircle, Lock, Unlock
} from "lucide-react";

export default function AdminWallets() {
  const { authAxios } = useAuth();
  const [wallets, setWallets] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedOperator, setSelectedOperator] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [txLoading, setTxLoading] = useState(false);

  // Adjustment modal state
  const [adjustModal, setAdjustModal] = useState(null); // { operator, type: 'credit'|'debit' }
  const [adjustAmount, setAdjustAmount] = useState("");
  const [adjustReason, setAdjustReason] = useState("");
  const [adjustSaving, setAdjustSaving] = useState(false);

  // Suspend dialog state
  const [suspendModal, setSuspendModal] = useState(null); // { operator, suspend: bool }
  const [suspendReason, setSuspendReason] = useState("");
  const [suspendSaving, setSuspendSaving] = useState(false);

  const fetchWallets = async () => {
    setLoading(true);
    try {
      const res = await authAxios.get("/admin/wallets?limit=100");
      setWallets(res.data.wallets || []);
      setTotal(res.data.total || 0);
    } catch {
      toast.error("Failed to load wallets");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchWallets(); }, []);

  const fetchTransactions = async (operatorId) => {
    setTxLoading(true);
    try {
      const res = await authAxios.get(`/admin/wallets/${operatorId}/transactions?limit=50`);
      setTransactions(res.data || []);
    } catch {
      toast.error("Failed to load transactions");
    } finally {
      setTxLoading(false);
    }
  };

  const handleViewTx = async (wallet) => {
    setSelectedOperator(wallet);
    await fetchTransactions(wallet.operator_id);
  };

  const openAdjust = (e, operator, type) => {
    e.stopPropagation();
    setAdjustModal({ operator, type });
    setAdjustAmount("");
    setAdjustReason("");
  };

  const handleAdjustSubmit = async (e) => {
    e.preventDefault();
    const amount = parseFloat(adjustAmount);
    if (!amount || amount <= 0) { toast.error("Enter a valid amount"); return; }
    if (!adjustReason.trim() || adjustReason.trim().length < 5) { toast.error("Reason must be at least 5 characters"); return; }
    setAdjustSaving(true);
    try {
      const { operator, type } = adjustModal;
      const endpoint = `/admin/wallets/${operator.operator_id}/${type}`;
      const res = await authAxios.post(endpoint, { amount, reason: adjustReason.trim() });
      toast.success(res.data.message);
      if (res.data.auto_suspended) toast.warning("Wallet was auto-suspended (balance < ₹100)");
      if (res.data.auto_unsuspended) toast.success("Wallet auto-unsuspended!");
      setAdjustModal(null);
      await fetchWallets();
      if (selectedOperator?.operator_id === operator.operator_id) {
        await fetchTransactions(operator.operator_id);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Action failed");
    } finally {
      setAdjustSaving(false);
    }
  };

  const openSuspendToggle = (e, operator) => {
    e.stopPropagation();
    setSuspendModal({ operator, suspend: !operator.wallet_suspended });
    setSuspendReason("");
  };

  const handleSuspendSubmit = async (e) => {
    e.preventDefault();
    if (!suspendReason.trim() || suspendReason.trim().length < 5) { toast.error("Reason must be at least 5 characters"); return; }
    setSuspendSaving(true);
    try {
      const { operator, suspend } = suspendModal;
      const res = await authAxios.post(`/admin/wallets/${operator.operator_id}/suspend`, {
        suspend,
        reason: suspendReason.trim()
      });
      toast.success(res.data.message);
      setSuspendModal(null);
      await fetchWallets();
      if (selectedOperator?.operator_id === operator.operator_id) {
        setSelectedOperator(prev => prev ? { ...prev, wallet_suspended: suspend } : prev);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Action failed");
    } finally {
      setSuspendSaving(false);
    }
  };

  const filtered = wallets.filter(w =>
    !search || w.company_name?.toLowerCase().includes(search.toLowerCase())
  );

  const criticalCount = wallets.filter(w => w.balance < 100).length;
  const lowCount = wallets.filter(w => w.balance >= 100 && w.balance < 500).length;
  const totalBalance = wallets.reduce((sum, w) => sum + (w.balance || 0), 0);

  const getTxColor = (type) => {
    if (["topup", "credit", "subscription_credit", "referral_reward", "admin_credit"].includes(type)) return "text-green-700";
    return "text-red-600";
  };

  return (
    <AdminLayout title="Operator Wallets">
      <div className="space-y-6">

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card data-testid="wallets-total-balance">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Wallet className="w-8 h-8 text-blue-600" />
                <div>
                  <p className="text-xs text-slate-500">Total Wallet Balance</p>
                  <p className="text-2xl font-bold text-slate-900">₹{totalBalance.toFixed(2)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card data-testid="wallets-low-count">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-8 h-8 text-amber-500" />
                <div>
                  <p className="text-xs text-slate-500">Low Balance (100-500)</p>
                  <p className="text-2xl font-bold text-amber-600">{lowCount}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card data-testid="wallets-critical-count">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <TrendingDown className="w-8 h-8 text-red-500" />
                <div>
                  <p className="text-xs text-slate-500">Critical (&lt;100) / Suspended</p>
                  <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Wallet List */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center justify-between">
                <span>Operator Wallets ({total})</span>
                <Button variant="ghost" size="sm" onClick={fetchWallets} data-testid="refresh-wallets-btn">
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </CardTitle>
              <div className="relative mt-2">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  className="pl-9"
                  placeholder="Search operator..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  data-testid="wallet-search"
                />
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600" />
                </div>
              ) : (
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  {filtered.map((w) => (
                    <div
                      key={w.operator_id}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer hover:bg-slate-50 transition-colors ${
                        selectedOperator?.operator_id === w.operator_id ? "border-blue-300 bg-blue-50" : "border-slate-100"
                      }`}
                      onClick={() => handleViewTx(w)}
                      data-testid={`wallet-row-${w.operator_id}`}
                    >
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{w.company_name}</p>
                        <div className="flex gap-1 mt-0.5">
                          {w.wallet_suspended && <Badge variant="destructive" className="text-xs">Suspended</Badge>}
                          {w.balance < 100 && !w.wallet_suspended && <Badge variant="destructive" className="text-xs">Critical</Badge>}
                          {w.balance >= 100 && w.balance < 500 && <Badge variant="outline" className="text-xs border-amber-300 text-amber-700">Low</Badge>}
                        </div>
                      </div>

                      {/* Balance */}
                      <div className="text-right shrink-0 mr-1">
                        <p className={`text-sm font-bold ${w.balance < 100 ? "text-red-600" : w.balance < 500 ? "text-amber-600" : "text-green-700"}`}>
                          ₹{w.balance?.toFixed(2)}
                        </p>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost" size="icon"
                          className="h-7 w-7 text-green-600 hover:bg-green-50"
                          title="Credit wallet"
                          data-testid={`credit-btn-${w.operator_id}`}
                          onClick={(e) => openAdjust(e, w, "credit")}
                        >
                          <PlusCircle className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost" size="icon"
                          className="h-7 w-7 text-red-500 hover:bg-red-50"
                          title="Debit wallet"
                          data-testid={`debit-btn-${w.operator_id}`}
                          onClick={(e) => openAdjust(e, w, "debit")}
                        >
                          <MinusCircle className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost" size="icon"
                          className={`h-7 w-7 hover:bg-slate-100 ${w.wallet_suspended ? "text-green-600" : "text-slate-500"}`}
                          title={w.wallet_suspended ? "Unsuspend wallet" : "Suspend wallet"}
                          data-testid={`suspend-btn-${w.operator_id}`}
                          onClick={(e) => openSuspendToggle(e, w)}
                        >
                          {w.wallet_suspended ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>
                  ))}
                  {filtered.length === 0 && <p className="text-sm text-slate-400 text-center py-4">No wallets found</p>}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Transaction Detail */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {selectedOperator ? `${selectedOperator.company_name} — Transactions` : "Select an operator"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!selectedOperator ? (
                <div className="text-center py-12 text-slate-400">
                  <Wallet className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Click on an operator to view transactions</p>
                </div>
              ) : txLoading ? (
                <div className="text-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600" />
                </div>
              ) : transactions.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-sm">No transactions found</div>
              ) : (
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  {transactions.map((tx) => (
                    <div key={tx.id} className="flex items-center gap-2 p-2 rounded border border-slate-100 text-sm">
                      <div className="flex-1 min-w-0">
                        <p className="truncate font-medium text-slate-700">{tx.description}</p>
                        <p className="text-xs text-slate-400">{new Date(tx.created_at).toLocaleString("en-IN")}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className={`font-semibold ${getTxColor(tx.type)}`}>
                          {tx.amount > 0 ? "+" : ""}₹{Math.abs(tx.amount).toFixed(2)}
                        </p>
                        <p className="text-xs text-slate-400">₹{tx.balance_after?.toFixed(2)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Credit / Debit Modal */}
      <Dialog open={!!adjustModal} onOpenChange={(open) => !open && setAdjustModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {adjustModal?.type === "credit" ? "Credit Wallet" : "Debit Wallet"} — {adjustModal?.operator?.company_name}
            </DialogTitle>
            <DialogDescription>
              Current balance: ₹{adjustModal?.operator?.balance?.toFixed(2)}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAdjustSubmit} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label>Amount (₹)</Label>
              <Input
                type="number"
                min="1"
                max="50000"
                step="0.01"
                value={adjustAmount}
                onChange={(e) => setAdjustAmount(e.target.value)}
                placeholder="e.g. 500"
                data-testid="adjust-amount-input"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea
                value={adjustReason}
                onChange={(e) => setAdjustReason(e.target.value)}
                placeholder="Why is this adjustment being made?"
                rows={3}
                data-testid="adjust-reason-input"
              />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={() => setAdjustModal(null)}>Cancel</Button>
              <Button
                type="submit"
                disabled={adjustSaving}
                className={adjustModal?.type === "debit" ? "bg-red-600 hover:bg-red-700 text-white" : ""}
                data-testid="adjust-submit-btn"
              >
                {adjustSaving ? "Processing..." : adjustModal?.type === "credit" ? "Credit Wallet" : "Debit Wallet"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Suspend / Unsuspend Dialog */}
      <Dialog open={!!suspendModal} onOpenChange={(open) => !open && setSuspendModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {suspendModal?.suspend ? "Suspend Wallet" : "Unsuspend Wallet"} — {suspendModal?.operator?.company_name}
            </DialogTitle>
            <DialogDescription>
              {suspendModal?.suspend
                ? "Suspending will put the account in read-only mode immediately."
                : "Unsuspending will restore full access to the operator."
              }
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSuspendSubmit} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                placeholder="Reason for this action..."
                rows={3}
                data-testid="suspend-reason-input"
                autoFocus
              />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={() => setSuspendModal(null)}>Cancel</Button>
              <Button
                type="submit"
                disabled={suspendSaving}
                className={suspendModal?.suspend ? "bg-red-600 hover:bg-red-700 text-white" : "bg-green-600 hover:bg-green-700 text-white"}
                data-testid="suspend-submit-btn"
              >
                {suspendSaving ? "Processing..." : suspendModal?.suspend ? "Suspend Wallet" : "Unsuspend Wallet"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
