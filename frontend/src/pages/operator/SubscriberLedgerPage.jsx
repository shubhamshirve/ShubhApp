import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../../App";
import { Button } from "../../components/ui/button";
import { formatDate, formatDateTime } from "../../utils/dateFormat";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { toast } from "sonner";
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  MapPin,
  RefreshCw,
  FileText,
  Download,
  CheckCircle2,
  Clock,
  XCircle,
  AlertCircle,
  Calendar,
  TrendingUp,
  Wallet,
  BadgeIndianRupee,
  CreditCard,
  Banknote,
  Smartphone,
  Building2,
  Receipt,
  BarChart3,
  List,
} from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (val) =>
  val != null
    ? `₹${Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : "—";

const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    return formatDate(iso);
  } catch { return iso; }
};

const VALIDITY_LABELS = {
  monthly: "Monthly", quarterly: "Quarterly",
  half_yearly: "Half-Yearly", yearly: "Yearly",
};

const PAYMENT_MODE_LABELS = {
  cash: "Cash", own_upi: "UPI", bank_transfer: "Bank Transfer", cheque: "Cheque",
};

const PAYMENT_MODE_ICONS = {
  cash: Banknote, own_upi: Smartphone, bank_transfer: Building2, cheque: FileText,
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const map = {
    paid:         { cls: "bg-green-100 text-green-700 border-green-200",   icon: CheckCircle2, label: "Paid" },
    pending:      { cls: "bg-amber-100 text-amber-700 border-amber-200",   icon: Clock,        label: "Pending" },
    overdue:      { cls: "bg-red-100 text-red-700 border-red-200",         icon: AlertCircle,  label: "Overdue" },
    cancelled:    { cls: "bg-slate-100 text-slate-500 border-slate-200",   icon: XCircle,      label: "Cancelled" },
    partial:      { cls: "bg-orange-100 text-orange-700 border-orange-200",icon: Clock,        label: "Partially Paid" },
    consolidated: { cls: "bg-slate-100 text-slate-400 border-slate-200",   icon: XCircle,      label: "Consolidated" },
  };
  const { cls, icon: Icon, label } = map[status] || map.pending;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border ${cls}`}>
      <Icon className="w-3 h-3" /> {label}
    </span>
  );
}

function SubscriberStatusBadge({ status }) {
  const map = {
    active:    "bg-green-100 text-green-700",
    suspended: "bg-red-100 text-red-700",
    inactive:  "bg-slate-100 text-slate-500",
  };
  return (
    <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full capitalize ${map[status] || map.inactive}`}>
      {status}
    </span>
  );
}

function DaysChip({ days }) {
  if (days == null) return null;
  if (days < 0)   return <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">Expired {Math.abs(days)}d ago</span>;
  if (days === 0) return <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">Expires today</span>;
  if (days <= 7)  return <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">{days}d left</span>;
  if (days <= 30) return <span className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">{days}d left</span>;
  return <span className="text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded-full border border-green-200">{days}d left</span>;
}

function SummaryTile({ label, value, sub, color = "slate", icon: Icon }) {
  const colors = {
    slate: { bg: "bg-slate-50 border-slate-200",  text: "text-slate-700",  icon: "text-slate-500",  badge: "text-slate-400" },
    green: { bg: "bg-green-50 border-green-200",  text: "text-green-700",  icon: "text-green-500",  badge: "text-green-400" },
    amber: { bg: "bg-amber-50 border-amber-200",  text: "text-amber-700",  icon: "text-amber-500",  badge: "text-amber-400" },
    red:   { bg: "bg-red-50 border-red-200",      text: "text-red-700",    icon: "text-red-500",    badge: "text-red-400"   },
    blue:  { bg: "bg-blue-50 border-blue-200",    text: "text-blue-700",   icon: "text-blue-500",   badge: "text-blue-400"  },
  };
  const c = colors[color];
  return (
    <div className={`${c.bg} border rounded-xl p-5 flex flex-col gap-1`}>
      <div className="flex items-center gap-2">
        {Icon && <Icon className={`w-4 h-4 ${c.icon}`} />}
        <span className="text-xs text-slate-500 font-medium">{label}</span>
      </div>
      <p className={`text-2xl font-bold mt-1 ${c.text}`}>{value}</p>
      {sub && <p className={`text-xs ${c.badge}`}>{sub}</p>}
    </div>
  );
}

// ─── Tab button ───────────────────────────────────────────────────────────────
function Tab({ active, onClick, icon: Icon, label, count }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
        active
          ? "border-blue-600 text-blue-600"
          : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
      }`}
    >
      <Icon className="w-4 h-4" />
      {label}
      {count != null && (
        <span className={`text-xs px-1.5 py-0.5 rounded-full ${active ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-500"}`}>
          {count}
        </span>
      )}
    </button>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SubscriberLedgerPage() {
  const { subscriberId } = useParams();
  const navigate = useNavigate();
  const { authAxios } = useAuth();
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  const fetchLedger = useCallback(async () => {
    if (!subscriberId) return;
    setLoading(true);
    try {
      const res = await authAxios.get(`/operator/subscribers/${subscriberId}/ledger`);
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load ledger");
      navigate("/operator/subscribers");
    } finally {
      setLoading(false);
    }
  }, [subscriberId, authAxios, navigate]);

  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  const handlePdf = (invoiceId) => {
    window.open(`${backendUrl}/api/operator/invoices/${invoiceId}/pdf`, "_blank");
  };

  const sub      = data?.subscriber;
  const summary  = data?.summary;
  const invoices = data?.invoices || [];
  const allPayments = data?.summary?.all_payments || [];

  // ── Render loading ──────────────────────────────────────────────────────────
  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
      </div>
    );
  }

  // ── Render page ─────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-50">

      {/* ── Top bar ── */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/operator/subscribers")}
                className="flex items-center gap-2 text-slate-600 hover:text-slate-900"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Subscribers
              </Button>
              <div className="h-5 w-px bg-slate-200" />
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center">
                  <User className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-base font-semibold text-slate-900 leading-tight">
                    {sub?.name || "Loading…"}
                  </h1>
                  <p className="text-xs text-slate-500">Account Ledger</p>
                </div>
                {sub?.status && <SubscriberStatusBadge status={sub.status} />}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchLedger}
              disabled={loading}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>

          {/* ── Tabs ── */}
          <div className="flex gap-0 -mb-px overflow-x-auto">
            <Tab active={activeTab === "overview"}  onClick={() => setActiveTab("overview")}  icon={BarChart3}  label="Overview" />
            <Tab active={activeTab === "invoices"}  onClick={() => setActiveTab("invoices")}  icon={Receipt}    label="Invoice History" count={invoices.length} />
            <Tab active={activeTab === "payments"}  onClick={() => setActiveTab("payments")}  icon={List}       label="All Payments" count={allPayments.length} />
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      {!data ? null : (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

          {/* ══ TAB: OVERVIEW ══════════════════════════════════════════════════ */}
          {activeTab === "overview" && (
            <div className="space-y-6">

              {/* Subscriber Info card */}
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-700">Subscriber Information</h2>
                </div>
                <div className="px-6 py-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                    <div className="flex items-center gap-2.5 text-slate-600">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
                        <Phone className="w-4 h-4 text-slate-500" />
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">Mobile / WhatsApp</p>
                        <p className="font-mono font-medium">{sub?.whatsapp_number || "—"}</p>
                      </div>
                    </div>
                    {sub?.email && (
                      <div className="flex items-center gap-2.5 text-slate-600">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
                          <Mail className="w-4 h-4 text-slate-500" />
                        </div>
                        <div>
                          <p className="text-xs text-slate-400">Email</p>
                          <p>{sub.email}</p>
                        </div>
                      </div>
                    )}
                    {sub?.address && (
                      <div className="flex items-start gap-2.5 text-slate-600">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 mt-0.5">
                          <MapPin className="w-4 h-4 text-slate-500" />
                        </div>
                        <div>
                          <p className="text-xs text-slate-400">Address</p>
                          <p>{sub.address}</p>
                        </div>
                      </div>
                    )}
                    {sub?.gst_number && (
                      <div className="flex items-center gap-2.5 text-slate-600">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
                          <BadgeIndianRupee className="w-4 h-4 text-slate-500" />
                        </div>
                        <div>
                          <p className="text-xs text-slate-400">GST Number</p>
                          <p className="font-mono">{sub.gst_number}</p>
                        </div>
                      </div>
                    )}
                    {sub?.created_at && (
                      <div className="flex items-center gap-2.5 text-slate-600">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
                          <Calendar className="w-4 h-4 text-slate-500" />
                        </div>
                        <div>
                          <p className="text-xs text-slate-400">Joined</p>
                          <p>{fmtDate(sub.created_at)}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Active Plans */}
                  {sub?.plans?.length > 0 && (
                    <div className="mt-5">
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Active Plans</p>
                      <div className="flex flex-wrap gap-3">
                        {sub.plans.map((p, i) => (
                          <div key={i} className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-sm flex items-center gap-4">
                            <div>
                              <p className="font-semibold text-blue-800">{p.plan_name || "Plan"}</p>
                              <p className="text-blue-500 text-xs">{VALIDITY_LABELS[p.selected_validity] || p.selected_validity || ""}</p>
                            </div>
                            <div className="border-l border-blue-200 pl-4">
                              <p className="text-blue-400 text-xs">Expires</p>
                              <p className="font-medium text-blue-700">{fmtDate(p.plan_expiry_date)}</p>
                            </div>
                            <DaysChip days={p.days_remaining} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Financial Summary */}
              <div>
                <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Financial Summary</h2>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <SummaryTile label="Total Invoiced" color="blue"  icon={TrendingUp}    value={fmt(summary?.total_invoiced)} sub={`${summary?.invoice_count ?? 0} invoices`} />
                  <SummaryTile label="Total Paid"     color="green" icon={CheckCircle2}  value={fmt(summary?.total_paid)}     sub={`${summary?.paid_count ?? 0} paid`} />
                  <SummaryTile label="Pending"        color="amber" icon={Clock}         value={fmt(summary?.total_pending)}  sub={`${summary?.pending_count ?? 0} pending`} />
                  <SummaryTile label="Overdue"        color="red"   icon={AlertCircle}   value={fmt(summary?.total_overdue)}  sub={`${summary?.overdue_count ?? 0} overdue`} />
                </div>
              </div>

              {/* Last payment */}
              {summary?.last_payment && (() => {
                const lp = summary.last_payment;
                const ModeIcon = PAYMENT_MODE_ICONS[lp.mode] || CreditCard;
                return (
                  <div className="bg-white rounded-xl border border-green-200 overflow-hidden">
                    <div className="px-6 py-4 bg-green-50 flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />
                      <div className="flex-1">
                        <span className="font-semibold text-green-800 text-sm">Last Payment Received</span>
                        <span className="text-slate-600 ml-3 text-sm">{fmt(lp.amount)}</span>
                        <span className="text-slate-400 mx-2">·</span>
                        <span className="text-slate-600 text-sm">{fmtDate(lp.date)}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <ModeIcon className="w-4 h-4" />
                        {PAYMENT_MODE_LABELS[lp.mode] || lp.mode || "—"}
                      </div>
                      {lp.invoice_number && (
                        <span className="font-mono text-xs text-blue-600 bg-blue-50 border border-blue-200 px-2 py-1 rounded-lg">
                          {lp.invoice_number}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* Recent invoices preview (last 3) */}
              {invoices.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-slate-700">Recent Invoices</h2>
                    <button onClick={() => setActiveTab("invoices")} className="text-xs text-blue-600 hover:underline">
                      View all {invoices.length} →
                    </button>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {invoices.slice(0, 3).map((inv) => (
                      <div key={inv.id} className="px-6 py-3 flex items-center justify-between gap-4">
                        <span className="font-mono text-sm text-blue-600 font-medium">{inv.invoice_number}</span>
                        <span className="text-sm text-slate-600 flex-1">{fmtDate(inv.invoice_date || inv.created_at)}</span>
                        <span className="text-sm font-semibold text-slate-800">{fmt(inv.final_amount)}</span>
                        <StatusBadge status={inv.status} />
                        <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => handlePdf(inv.id)}>
                          <Download className="w-3.5 h-3.5 text-slate-400" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══ TAB: INVOICE HISTORY ═══════════════════════════════════════════ */}
          {activeTab === "invoices" && (
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="text-sm font-semibold text-slate-700">Invoice History</h2>
                <p className="text-xs text-slate-400 mt-0.5">{invoices.length} invoice{invoices.length !== 1 ? "s" : ""} total</p>
              </div>

              {invoices.length === 0 ? (
                <div className="text-center py-16 text-slate-400">
                  <FileText className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                  <p className="text-sm">No invoices yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50">
                        <TableHead className="text-xs py-3">Invoice #</TableHead>
                        <TableHead className="text-xs py-3">Plan</TableHead>
                        <TableHead className="text-xs py-3">Service Period</TableHead>
                        <TableHead className="text-xs py-3 text-right">Amount</TableHead>
                        <TableHead className="text-xs py-3">Due Date</TableHead>
                        <TableHead className="text-xs py-3">Status</TableHead>
                        <TableHead className="text-xs py-3">Paid On</TableHead>
                        <TableHead className="text-xs py-3">Mode</TableHead>
                        <TableHead className="text-xs py-3 text-center">PDF</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {invoices.map((inv) => {
                        const item = (inv.line_items || [])[0] || {};
                        const ModeIcon = PAYMENT_MODE_ICONS[inv.payment_mode] || CreditCard;
                        const isOverdue = inv.status === "overdue" || (
                          inv.status === "pending" && inv.due_date && new Date(inv.due_date) < new Date()
                        );
                        const isPartial = inv.status === "partial";
                        const amountPaid = inv.amount_paid || 0;
                        const balanceDue = isPartial ? Math.max(0, inv.final_amount - amountPaid) : 0;
                        const paymentsReceived = inv.payments_received || [];

                        return (
                          <>
                            <TableRow
                              key={inv.id}
                              className={`text-xs ${isOverdue ? "bg-red-50/40" : isPartial ? "bg-orange-50/30" : "hover:bg-slate-50"}`}
                            >
                              <TableCell className="py-3 font-mono text-blue-600 font-medium whitespace-nowrap">
                                {inv.invoice_number}
                              </TableCell>
                              <TableCell className="py-3 max-w-[150px]">
                                <p className="font-medium text-slate-700 truncate" title={item.plan_name}>{item.plan_name || "—"}</p>
                                {item.selected_validity && (
                                  <p className="text-slate-400 text-[11px]">{VALIDITY_LABELS[item.selected_validity] || item.selected_validity}</p>
                                )}
                              </TableCell>
                              <TableCell className="py-3 whitespace-nowrap text-slate-600">
                                {item.plan_name === "Previous Pending"
                                  ? (item.service_start_date ? `Till ${fmtDate(item.service_start_date)}` : "Carried forward")
                                  : item.service_start_date
                                    ? `${fmtDate(item.service_start_date)} – ${fmtDate(item.service_end_date)}`
                                    : "—"}
                              </TableCell>
                              <TableCell className="py-3 text-right font-semibold text-slate-800 whitespace-nowrap">
                                <span>{fmt(inv.final_amount)}</span>
                                {isPartial && (
                                  <span className="block text-[11px] font-normal text-orange-600">
                                    Paid {fmt(amountPaid)} · Bal {fmt(balanceDue)}
                                  </span>
                                )}
                              </TableCell>
                              <TableCell className={`py-3 whitespace-nowrap ${isOverdue ? "text-red-600 font-medium" : "text-slate-600"}`}>
                                {fmtDate(inv.due_date)}
                              </TableCell>
                              <TableCell className="py-3">
                                <StatusBadge status={inv.status} />
                              </TableCell>
                              <TableCell className="py-3 text-slate-500 whitespace-nowrap">
                                {inv.paid_at
                                  ? fmtDate(inv.paid_at)
                                  : isPartial && paymentsReceived.length > 0
                                    ? fmtDate(paymentsReceived[paymentsReceived.length - 1]?.date)
                                    : "—"}
                              </TableCell>
                              <TableCell className="py-3">
                                {inv.payment_mode ? (
                                  <span className="flex items-center gap-1 text-slate-500">
                                    <ModeIcon className="w-3.5 h-3.5" />
                                    {PAYMENT_MODE_LABELS[inv.payment_mode] || inv.payment_mode}
                                  </span>
                                ) : isPartial && paymentsReceived.length > 0 ? (
                                  (() => {
                                    const lastRec = paymentsReceived[paymentsReceived.length - 1];
                                    const RecIcon = PAYMENT_MODE_ICONS[lastRec?.mode] || CreditCard;
                                    return (
                                      <span className="flex items-center gap-1 text-slate-500">
                                        <RecIcon className="w-3.5 h-3.5" />
                                        {PAYMENT_MODE_LABELS[lastRec?.mode] || lastRec?.mode || "—"}
                                      </span>
                                    );
                                  })()
                                ) : "—"}
                              </TableCell>
                              <TableCell className="py-3 text-center">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7"
                                  onClick={() => handlePdf(inv.id)}
                                  title="Download PDF"
                                >
                                  <Download className="w-3.5 h-3.5 text-slate-400 hover:text-blue-600" />
                                </Button>
                              </TableCell>
                            </TableRow>

                            {/* Payment history sub-rows for partial invoices */}
                            {isPartial && paymentsReceived.map((rec, ri) => {
                              const RecIcon = PAYMENT_MODE_ICONS[rec.mode] || CreditCard;
                              return (
                                <TableRow key={`${inv.id}-rec-${ri}`} className="bg-orange-50/60 text-xs border-l-4 border-l-orange-300">
                                  <TableCell className="py-2 pl-8 text-slate-400 italic" colSpan={2}>
                                    Payment #{ri + 1}
                                  </TableCell>
                                  <TableCell className="py-2 text-slate-500 whitespace-nowrap">{fmtDate(rec.date)}</TableCell>
                                  <TableCell className="py-2 text-right font-semibold text-orange-700">{fmt(rec.amount)}</TableCell>
                                  <TableCell className="py-2 text-slate-400" colSpan={2} />
                                  <TableCell className="py-2 text-slate-500 whitespace-nowrap">{fmtDate(rec.date)}</TableCell>
                                  <TableCell className="py-2">
                                    <span className="flex items-center gap-1 text-slate-500">
                                      <RecIcon className="w-3.5 h-3.5" />
                                      {PAYMENT_MODE_LABELS[rec.mode] || rec.mode || "—"}
                                    </span>
                                  </TableCell>
                                  <TableCell className="py-2" />
                                </TableRow>
                              );
                            })}
                          </>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )}

          {/* ══ TAB: ALL PAYMENTS ══════════════════════════════════════════════ */}
          {activeTab === "payments" && (
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="text-sm font-semibold text-slate-700">All Payments</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Chronological record of every payment received — {allPayments.length} entry{allPayments.length !== 1 ? "ies" : ""}
                </p>
              </div>

              {allPayments.length === 0 ? (
                <div className="text-center py-16 text-slate-400">
                  <Wallet className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                  <p className="text-sm">No payments recorded yet</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {allPayments.map((p, i) => {
                    const ModeIcon = PAYMENT_MODE_ICONS[p.mode] || CreditCard;
                    return (
                      <div key={i} className="px-6 py-4 flex items-center gap-4 hover:bg-slate-50 transition-colors">
                        {/* Index circle */}
                        <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                          <CheckCircle2 className="w-4 h-4 text-green-600" />
                        </div>
                        {/* Date */}
                        <div className="w-28 shrink-0">
                          <p className="text-sm font-medium text-slate-700">{fmtDate(p.date)}</p>
                          <p className="text-xs text-slate-400">
                            {p.date ? formatDateTime(p.date) : ""}
                          </p>
                        </div>
                        {/* Amount */}
                        <div className="flex-1">
                          <p className="text-lg font-bold text-green-700">{fmt(p.amount)}</p>
                        </div>
                        {/* Mode */}
                        <div className="flex items-center gap-2 text-slate-600 text-sm">
                          <ModeIcon className="w-4 h-4 text-slate-400" />
                          {PAYMENT_MODE_LABELS[p.mode] || p.mode || "—"}
                        </div>
                        {/* Invoice number */}
                        {p.invoice_number && (
                          <span className="font-mono text-xs text-blue-600 bg-blue-50 border border-blue-100 px-2 py-1 rounded-lg shrink-0">
                            {p.invoice_number}
                          </span>
                        )}
                      </div>
                    );
                  })}

                  {/* Total row */}
                  <div className="px-6 py-4 bg-slate-50 flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-600">Total Received</span>
                    <span className="text-lg font-bold text-green-700">
                      {fmt(allPayments.reduce((s, p) => s + (p.amount || 0), 0))}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
