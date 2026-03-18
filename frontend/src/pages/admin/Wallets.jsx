import { useState, useEffect } from "react";
import { AdminLayout } from "../../components/Layout";
import { useAuth } from "../../App";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { toast } from "sonner";
import { Wallet, AlertTriangle, TrendingDown, RefreshCw, Search } from "lucide-react";

export default function AdminWallets() {
  const { authAxios } = useAuth();
  const [wallets, setWallets] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedOperator, setSelectedOperator] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [txLoading, setTxLoading] = useState(false);

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

  const filtered = wallets.filter(w =>
    !search || w.company_name?.toLowerCase().includes(search.toLowerCase())
  );

  const criticalCount = wallets.filter(w => w.balance < 100).length;
  const lowCount = wallets.filter(w => w.balance >= 100 && w.balance < 500).length;
  const totalBalance = wallets.reduce((sum, w) => sum + (w.balance || 0), 0);

  const getTxColor = (type) => {
    if (["topup", "credit", "subscription_credit", "referral_reward"].includes(type)) return "text-green-700";
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
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{w.company_name}</p>
                        <p className="text-xs text-slate-400">{w.operator_id}</p>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-bold ${w.balance < 100 ? "text-red-600" : w.balance < 500 ? "text-amber-600" : "text-green-700"}`}>
                          ₹{w.balance?.toFixed(2)}
                        </p>
                        <div className="flex gap-1 justify-end mt-0.5">
                          {w.wallet_suspended && <Badge variant="destructive" className="text-xs">Suspended</Badge>}
                          {w.balance < 100 && !w.wallet_suspended && <Badge variant="destructive" className="text-xs">Critical</Badge>}
                          {w.balance >= 100 && w.balance < 500 && <Badge variant="outline" className="text-xs border-amber-300 text-amber-700">Low</Badge>}
                        </div>
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
    </AdminLayout>
  );
}
