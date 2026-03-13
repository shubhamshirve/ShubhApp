import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { toast } from "sonner";
import {
  Banknote, ArrowUpRight, Clock, CheckCircle2, AlertCircle,
  Loader2, Search, Filter, ChevronLeft, ChevronRight,
  XCircle, RefreshCw, Eye, ArrowDown, CalendarDays,
  IndianRupee, TrendingUp, Receipt, X
} from "lucide-react";

const formatCurrency = (v) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(v || 0);

const formatDate = (d) => {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};

const StatusBadge = ({ status }) => {
  const map = {
    pending: { bg: "bg-amber-50 text-amber-700 border-amber-200", icon: Clock, label: "Pending" },
    processing: { bg: "bg-blue-50 text-blue-700 border-blue-200", icon: RefreshCw, label: "Processing" },
    completed: { bg: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle2, label: "Completed" },
    failed: { bg: "bg-red-50 text-red-700 border-red-200", icon: XCircle, label: "Failed" },
  };
  const c = map[status] || map.pending;
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.bg}`}>
      <Icon className="w-3 h-3" />
      {c.label}
    </span>
  );
};

export default function AdminSettlements() {
  const { token } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };

  const [summary, setSummary] = useState(null);
  const [settlements, setSettlements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [processing, setProcessing] = useState(false);

  // Detail dialog
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Status update dialog
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [statusTarget, setStatusTarget] = useState(null);
  const [newStatus, setNewStatus] = useState("");
  const [utrNumber, setUtrNumber] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/settlements/summary`, { headers });
      setSummary(res.data);
    } catch {
      toast.error("Failed to load settlement summary");
    }
  }, [token]);

  const fetchSettlements = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ page, limit: 15 });
      if (statusFilter) params.set("status", statusFilter);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      const res = await axios.get(`${API}/admin/settlements?${params}`, { headers });
      setSettlements(res.data.settlements);
      setTotal(res.data.total);
      setPages(res.data.pages);
    } catch {
      toast.error("Failed to load settlements");
    } finally {
      setLoading(false);
    }
  }, [token, page, statusFilter, dateFrom, dateTo]);

  useEffect(() => { fetchSummary(); }, [fetchSummary]);
  useEffect(() => { fetchSettlements(); }, [fetchSettlements]);

  const handleProcess = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/admin/settlements/process`, null, { headers });
      toast.success(res.data.message);
      fetchSummary();
      fetchSettlements();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Settlement processing failed");
    } finally {
      setProcessing(false);
    }
  };

  const openDetail = async (id) => {
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const res = await axios.get(`${API}/admin/settlements/${id}`, { headers });
      setDetailData(res.data);
    } catch {
      toast.error("Failed to load settlement details");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const openStatusDialog = (settlement) => {
    setStatusTarget(settlement);
    setNewStatus(settlement.status);
    setUtrNumber(settlement.utr_number || "");
    setStatusDialogOpen(true);
  };

  const handleStatusUpdate = async () => {
    if (!statusTarget) return;
    setUpdatingStatus(true);
    try {
      const params = new URLSearchParams({ status: newStatus });
      if (newStatus === "completed" && utrNumber) params.set("utr_number", utrNumber);
      await axios.put(`${API}/admin/settlements/${statusTarget.id}/status?${params}`, null, { headers });
      toast.success(`Settlement marked as ${newStatus}`);
      setStatusDialogOpen(false);
      fetchSummary();
      fetchSettlements();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update status");
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <AdminLayout title="Settlements">
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Banknote className="w-7 h-7 text-indigo-600" />
            Settlements
          </h1>
          <p className="text-sm text-slate-500 mt-1">Process and track operator payment settlements</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleProcess}
            disabled={processing}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Process Settlements
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500">Total Settled</p>
            <p className="text-lg font-bold text-slate-900">{formatCurrency(summary.total_settled)}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                <Clock className="w-4 h-4 text-amber-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500">Pending</p>
            <p className="text-lg font-bold text-slate-900">{formatCurrency(summary.total_pending)}</p>
            <p className="text-xs text-slate-400">{summary.pending_count} settlements</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-indigo-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500">This Month</p>
            <p className="text-lg font-bold text-slate-900">{formatCurrency(summary.month_amount)}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                <IndianRupee className="w-4 h-4 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500">Month Collections</p>
            <p className="text-lg font-bold text-slate-900">{formatCurrency(summary.month_collections)}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
                <Receipt className="w-4 h-4 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500">Platform Fees</p>
            <p className="text-lg font-bold text-slate-900">{formatCurrency(summary.month_fees)}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                <ArrowUpRight className="w-4 h-4 text-slate-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500">Completed</p>
            <p className="text-lg font-bold text-slate-900">{summary.completed_count}</p>
            <p className="text-xs text-slate-400">{summary.processing_count} processing</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-col sm:flex-row gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-500 mb-1 block">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-500 mb-1 block">From Date</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-500 mb-1 block">To Date</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            onClick={() => { setStatusFilter(""); setDateFrom(""); setDateTo(""); setPage(1); }}
            className="px-3 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
          </div>
        ) : settlements.length === 0 ? (
          <div className="text-center py-16">
            <Banknote className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No settlements found</p>
            <p className="text-slate-400 text-xs mt-1">Click "Process Settlements" to generate settlements for recent payments</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Date</th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Operator</th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Plan</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">Collections</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">Fee Rate</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">Net Settlement</th>
                    <th className="text-center px-4 py-3 font-semibold text-slate-600">Invoices</th>
                    <th className="text-center px-4 py-3 font-semibold text-slate-600">Status</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {settlements.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50 transition">
                      <td className="px-4 py-3">
                        <span className="font-medium text-slate-800">{formatDate(s.settlement_date + "T00:00:00")}</span>
                        {s.is_manual && (
                          <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-purple-100 text-purple-700 rounded font-medium">Manual</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-700">{s.operator_name}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                          s.plan_name?.toLowerCase().includes("pro") ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-700"
                        }`}>
                          {s.plan_name || "N/A"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-slate-800">
                        {formatCurrency(s.total_collections)}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-500">
                        <span className="font-medium">{s.platform_fee_percentage}%</span>
                        <span className="text-xs text-slate-400 block">{formatCurrency(s.platform_fee)}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-indigo-700">
                        {formatCurrency(s.net_settlement)}
                      </td>
                      <td className="px-4 py-3 text-center text-slate-600">{s.payment_count}</td>
                      <td className="px-4 py-3 text-center">
                        <StatusBadge status={s.status} />
                        {s.utr_number && (
                          <p className="text-[10px] text-slate-400 mt-1 font-mono">{s.utr_number}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => openDetail(s.id)}
                            className="px-2 py-1 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded transition"
                            title="View Details"
                          >
                            <Eye className="w-3 h-3 inline mr-1" />
                            View
                          </button>
                          {s.status === "pending" && (
                            <button
                              onClick={() => openStatusDialog(s)}
                              className="px-2 py-1 text-xs font-medium text-emerald-600 bg-emerald-50 hover:bg-emerald-100 rounded transition"
                              title="Mark as Completed"
                            >
                              <CheckCircle2 className="w-3 h-3 inline mr-1" />
                              Mark Paid
                            </button>
                          )}
                          {s.status === "processing" && (
                            <button
                              onClick={() => openStatusDialog(s)}
                              className="px-2 py-1 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded transition"
                              title="Update Status"
                            >
                              <RefreshCw className="w-3 h-3 inline mr-1" />
                              Update
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50/50">
              <p className="text-xs text-slate-500">{total} settlement{total !== 1 ? "s" : ""}</p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="p-1.5 rounded-lg hover:bg-slate-200 disabled:opacity-30 transition"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs text-slate-600">Page {page} of {pages}</span>
                <button
                  onClick={() => setPage(Math.min(pages, page + 1))}
                  disabled={page >= pages}
                  className="p-1.5 rounded-lg hover:bg-slate-200 disabled:opacity-30 transition"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Detail Dialog */}
      {detailOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-slate-200">
              <h2 className="text-lg font-bold text-slate-900">Settlement Details</h2>
              <button onClick={() => setDetailOpen(false)} className="p-1.5 hover:bg-slate-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            {detailLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
              </div>
            ) : detailData ? (
              <div className="p-5 space-y-5">
                {/* Settlement Info */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-slate-400">Operator</p>
                    <p className="font-semibold text-slate-800">{detailData.operator_name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Date</p>
                    <p className="font-medium text-slate-700">{formatDate(detailData.settlement_date + "T00:00:00")}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Status</p>
                    <StatusBadge status={detailData.status} />
                  </div>
                </div>

                {/* Financial Breakdown */}
                <div className="bg-slate-50 rounded-xl p-4 space-y-2">
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Financial Breakdown</h3>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">Total Collections ({detailData.payment_count} payments)</span>
                    <span className="font-medium">{formatCurrency(detailData.total_collections)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-red-600">
                    <span>Platform Fee ({detailData.platform_fee_percentage}%)</span>
                    <span>- {formatCurrency(detailData.platform_fee)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-red-500">
                    <span>GST on Platform Fee (18%)</span>
                    <span>- {formatCurrency(detailData.tax_on_platform_fee)}</span>
                  </div>
                  <div className="flex justify-between pt-2 mt-2 border-t-2 border-slate-300">
                    <span className="font-bold text-slate-800">Net Settlement</span>
                    <span className="font-bold text-indigo-700 text-lg">{formatCurrency(detailData.net_settlement)}</span>
                  </div>
                </div>

                {/* Bank Details */}
                {detailData.operator_details && (
                  <div className="bg-blue-50 rounded-xl p-4">
                    <h3 className="text-sm font-semibold text-blue-800 mb-2">Operator Bank Details</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {detailData.operator_details.bank_name && (
                        <div>
                          <p className="text-xs text-blue-500">Bank</p>
                          <p className="text-blue-900">{detailData.operator_details.bank_name}</p>
                        </div>
                      )}
                      {detailData.operator_details.bank_account_name && (
                        <div>
                          <p className="text-xs text-blue-500">Account Name</p>
                          <p className="text-blue-900">{detailData.operator_details.bank_account_name}</p>
                        </div>
                      )}
                      {detailData.operator_details.bank_account_number && (
                        <div>
                          <p className="text-xs text-blue-500">Account No.</p>
                          <p className="text-blue-900">{detailData.operator_details.bank_account_number}</p>
                        </div>
                      )}
                      {detailData.operator_details.bank_ifsc && (
                        <div>
                          <p className="text-xs text-blue-500">IFSC</p>
                          <p className="text-blue-900">{detailData.operator_details.bank_ifsc}</p>
                        </div>
                      )}
                      {!detailData.operator_details.bank_account_number && (
                        <p className="text-sm text-blue-600 italic col-span-2">No bank details configured for this operator</p>
                      )}
                    </div>
                  </div>
                )}

                {/* UTR */}
                {detailData.utr_number && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-500">UTR Number:</span>
                    <span className="font-mono font-medium text-slate-800 bg-slate-100 px-2 py-0.5 rounded">{detailData.utr_number}</span>
                  </div>
                )}
                {detailData.paid_at && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-500">Paid At:</span>
                    <span className="text-slate-700">{formatDate(detailData.paid_at)}</span>
                  </div>
                )}

                {/* Invoices */}
                {detailData.invoices && detailData.invoices.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-slate-700 mb-2">Included Invoices</h3>
                    <div className="border border-slate-200 rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-slate-50">
                            <th className="text-left px-3 py-2 text-xs font-semibold text-slate-500">Invoice #</th>
                            <th className="text-left px-3 py-2 text-xs font-semibold text-slate-500">Subscriber</th>
                            <th className="text-left px-3 py-2 text-xs font-semibold text-slate-500">Plan</th>
                            <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500">Amount</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {detailData.invoices.map((inv) => (
                            <tr key={inv.id}>
                              <td className="px-3 py-2 font-medium text-slate-700">{inv.invoice_number}</td>
                              <td className="px-3 py-2 text-slate-600">{inv.subscriber_name}</td>
                              <td className="px-3 py-2 text-slate-500">{inv.plan_name}</td>
                              <td className="px-3 py-2 text-right font-medium">{formatCurrency(inv.final_amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Status Update Dialog */}
      {statusDialogOpen && statusTarget && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
            <div className="flex items-center justify-between p-5 border-b border-slate-200">
              <h2 className="text-lg font-bold text-slate-900">Update Settlement Status</h2>
              <button onClick={() => setStatusDialogOpen(false)} className="p-1.5 hover:bg-slate-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="bg-slate-50 rounded-lg p-3 text-sm">
                <p className="text-slate-500">Operator: <span className="font-medium text-slate-800">{statusTarget.operator_name}</span></p>
                <p className="text-slate-500">Amount: <span className="font-semibold text-indigo-700">{formatCurrency(statusTarget.net_settlement)}</span></p>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700 block mb-1">Status</label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="pending">Pending</option>
                  <option value="processing">Processing</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
              {newStatus === "completed" && (
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">UTR Number</label>
                  <input
                    type="text"
                    value={utrNumber}
                    onChange={(e) => setUtrNumber(e.target.value)}
                    placeholder="Enter bank transfer reference"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setStatusDialogOpen(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleStatusUpdate}
                  disabled={updatingStatus}
                  className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                  {updatingStatus ? <Loader2 className="w-4 h-4 animate-spin" /> : "Update Status"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
    </AdminLayout>
  );
}
