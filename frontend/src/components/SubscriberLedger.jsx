import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../App";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "./ui/sheet";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { toast } from "sonner";
import {
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
} from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (val) =>
  val != null ? `₹${Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—";

const fmtDate = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }
  catch { return iso; }
};

const fmtDateTime = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
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
    paid:      { cls: "bg-green-100 text-green-700 border-green-200",  icon: CheckCircle2,   label: "Paid" },
    pending:   { cls: "bg-amber-100 text-amber-700 border-amber-200",   icon: Clock,          label: "Pending" },
    overdue:   { cls: "bg-red-100 text-red-700 border-red-200",         icon: AlertCircle,    label: "Overdue" },
    cancelled: { cls: "bg-slate-100 text-slate-500 border-slate-200",   icon: XCircle,        label: "Cancelled" },
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
    <span className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${map[status] || map.inactive}`}>
      {status}
    </span>
  );
}

function DaysChip({ days }) {
  if (days == null) return null;
  if (days < 0)  return <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">Expired {Math.abs(days)}d ago</span>;
  if (days === 0) return <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">Expires today</span>;
  if (days <= 7)  return <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">{days}d left</span>;
  if (days <= 30) return <span className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">{days}d left</span>;
  return <span className="text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded-full border border-green-200">{days}d left</span>;
}

function SummaryTile({ label, value, sub, color = "slate", icon: Icon }) {
  const colors = {
    slate:  { bg: "bg-slate-50",  text: "text-slate-700",  icon: "text-slate-500"  },
    green:  { bg: "bg-green-50",  text: "text-green-700",  icon: "text-green-500"  },
    amber:  { bg: "bg-amber-50",  text: "text-amber-700",  icon: "text-amber-500"  },
    red:    { bg: "bg-red-50",    text: "text-red-700",    icon: "text-red-500"    },
    blue:   { bg: "bg-blue-50",   text: "text-blue-700",   icon: "text-blue-500"   },
  };
  const c = colors[color];
  return (
    <div className={`${c.bg} rounded-xl p-4 flex flex-col gap-1`}>
      <div className="flex items-center gap-1.5">
        {Icon && <Icon className={`w-4 h-4 ${c.icon}`} />}
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <p className={`text-xl font-bold ${c.text}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SubscriberLedger({ subscriberId, subscriberName, open, onClose }) {
  const { authAxios, user } = useAuth();
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchLedger = useCallback(async () => {
    if (!subscriberId) return;
    setLoading(true);
    try {
      const res = await authAxios.get(`/operator/subscribers/${subscriberId}/ledger`);
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load ledger");
      onClose();
    } finally {
      setLoading(false);
    }
  }, [subscriberId, authAxios, onClose]);

  useEffect(() => {
    if (open && subscriberId) fetchLedger();
  }, [open, subscriberId, fetchLedger]);

  const handlePdf = (invoiceId) => {
    window.open(`${backendUrl}/api/operator/invoices/${invoiceId}/pdf`, "_blank");
  };

  const sub     = data?.subscriber;
  const summary = data?.summary;
  const invoices = data?.invoices || [];

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-3xl flex flex-col p-0 gap-0 overflow-hidden"
      >
        {/* ── Header ── */}
        <SheetHeader className="px-6 py-4 border-b bg-white shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                <User className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold text-slate-800 leading-tight">
                  {subscriberName || sub?.name || "Subscriber Ledger"}
                </SheetTitle>
                <p className="text-xs text-slate-500 mt-0.5">Account Ledger</p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={fetchLedger} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </SheetHeader>

        {/* ── Scrollable body ── */}
        <div className="flex-1 overflow-y-auto">
          {loading && !data ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
            </div>
          ) : !data ? null : (
            <div className="space-y-0 divide-y divide-slate-100">

              {/* ── Section 1: Subscriber info ── */}
              <div className="px-6 py-4 bg-slate-50">
                <div className="flex flex-wrap items-start gap-4">
                  <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center gap-2 text-slate-600">
                      <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="font-mono">{sub?.whatsapp_number || "—"}</span>
                    </div>
                    {sub?.email && (
                      <div className="flex items-center gap-2 text-slate-600">
                        <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate">{sub.email}</span>
                      </div>
                    )}
                    {sub?.address && (
                      <div className="flex items-start gap-2 text-slate-600 col-span-2">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                        <span>{sub.address}</span>
                      </div>
                    )}
                  </div>
                  <SubscriberStatusBadge status={sub?.status} />
                </div>

                {/* Plans */}
                {sub?.plans?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {sub.plans.map((p, i) => (
                      <div key={i} className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs flex items-center gap-3">
                        <div>
                          <p className="font-semibold text-slate-700">{p.plan_name || "Plan"}</p>
                          <p className="text-slate-400">{VALIDITY_LABELS[p.selected_validity] || p.selected_validity || ""}</p>
                        </div>
                        <div className="border-l pl-3">
                          <p className="text-slate-400">Expires</p>
                          <p className="font-medium text-slate-700">{fmtDate(p.plan_expiry_date)}</p>
                        </div>
                        <DaysChip days={p.days_remaining} />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* ── Section 2: Financial summary ── */}
              <div className="px-6 py-4">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Financial Summary</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <SummaryTile
                    label="Total Invoiced" color="blue" icon={TrendingUp}
                    value={fmt(summary?.total_invoiced)}
                    sub={`${summary?.invoice_count ?? 0} invoice${summary?.invoice_count !== 1 ? "s" : ""}`}
                  />
                  <SummaryTile
                    label="Total Paid" color="green" icon={CheckCircle2}
                    value={fmt(summary?.total_paid)}
                    sub={`${summary?.paid_count ?? 0} paid`}
                  />
                  <SummaryTile
                    label="Pending" color="amber" icon={Clock}
                    value={fmt(summary?.total_pending)}
                    sub={`${summary?.pending_count ?? 0} pending`}
                  />
                  <SummaryTile
                    label="Overdue" color="red" icon={AlertCircle}
                    value={fmt(summary?.total_overdue)}
                    sub={`${summary?.overdue_count ?? 0} overdue`}
                  />
                </div>

                {/* Last payment */}
                {summary?.last_payment && (() => {
                  const lp = summary.last_payment;
                  const ModeIcon = PAYMENT_MODE_ICONS[lp.mode] || CreditCard;
                  return (
                    <div className="mt-3 flex items-center gap-3 bg-green-50 border border-green-200 rounded-lg px-4 py-2.5 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
                      <div className="flex-1">
                        <span className="font-medium text-green-700">Last payment</span>
                        <span className="text-slate-600 ml-2">{fmt(lp.amount)}</span>
                        <span className="text-slate-400 mx-1">·</span>
                        <span className="text-slate-600">{fmtDate(lp.date)}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-slate-500">
                        <ModeIcon className="w-3.5 h-3.5" />
                        {PAYMENT_MODE_LABELS[lp.mode] || lp.mode || "—"}
                      </div>
                      {lp.invoice_number && (
                        <span className="font-mono text-xs text-blue-600 bg-blue-50 border border-blue-100 px-1.5 py-0.5 rounded">
                          {lp.invoice_number}
                        </span>
                      )}
                    </div>
                  );
                })()}
              </div>

              {/* ── Section 3: Invoice history ── */}
              <div className="px-6 py-4">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                  Invoice History
                  {invoices.length > 0 && <span className="ml-2 font-normal normal-case text-slate-400">({invoices.length})</span>}
                </p>

                {invoices.length === 0 ? (
                  <div className="text-center py-10 text-slate-400">
                    <FileText className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <p className="text-sm">No invoices yet</p>
                  </div>
                ) : (
                  <div className="rounded-lg border border-slate-200 overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-slate-50">
                          <TableHead className="text-xs py-2">Invoice #</TableHead>
                          <TableHead className="text-xs py-2">Plan</TableHead>
                          <TableHead className="text-xs py-2">Service Period</TableHead>
                          <TableHead className="text-xs py-2 text-right">Amount</TableHead>
                          <TableHead className="text-xs py-2">Due Date</TableHead>
                          <TableHead className="text-xs py-2">Status</TableHead>
                          <TableHead className="text-xs py-2">Paid On</TableHead>
                          <TableHead className="text-xs py-2">Mode</TableHead>
                          <TableHead className="text-xs py-2 text-center">PDF</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {invoices.map((inv) => {
                          const item = (inv.line_items || [])[0] || {};
                          const ModeIcon = PAYMENT_MODE_ICONS[inv.payment_mode] || CreditCard;
                          const isOverdue = inv.status === "overdue" || (
                            inv.status === "pending" &&
                            inv.due_date &&
                            new Date(inv.due_date) < new Date()
                          );
                          return (
                            <TableRow
                              key={inv.id}
                              className={`text-xs ${isOverdue ? "bg-red-50/40" : "hover:bg-slate-50"}`}
                            >
                              <TableCell className="py-2.5 font-mono text-blue-600 font-medium whitespace-nowrap">
                                {inv.invoice_number}
                              </TableCell>
                              <TableCell className="py-2.5 max-w-[120px]">
                                <p className="font-medium text-slate-700 truncate" title={item.plan_name}>{item.plan_name || "—"}</p>
                                {item.selected_validity && (
                                  <p className="text-slate-400 text-[11px]">{VALIDITY_LABELS[item.selected_validity] || item.selected_validity}</p>
                                )}
                              </TableCell>
                              <TableCell className="py-2.5 whitespace-nowrap text-slate-600">
                                {item.plan_name === "Previous Pending"
                                  ? (item.service_start_date ? `Till ${fmtDate(item.service_start_date)}` : "Carried forward")
                                  : item.service_start_date
                                    ? `${fmtDate(item.service_start_date)} – ${fmtDate(item.service_end_date)}`
                                    : "—"}
                              </TableCell>
                              <TableCell className="py-2.5 text-right font-semibold text-slate-800 whitespace-nowrap">
                                {fmt(inv.final_amount)}
                              </TableCell>
                              <TableCell className={`py-2.5 whitespace-nowrap ${isOverdue ? "text-red-600 font-medium" : "text-slate-600"}`}>
                                {fmtDate(inv.due_date)}
                              </TableCell>
                              <TableCell className="py-2.5">
                                <StatusBadge status={inv.status} />
                              </TableCell>
                              <TableCell className="py-2.5 text-slate-500 whitespace-nowrap">
                                {inv.paid_at ? fmtDate(inv.paid_at) : "—"}
                              </TableCell>
                              <TableCell className="py-2.5">
                                {inv.payment_mode ? (
                                  <span className="flex items-center gap-1 text-slate-500">
                                    <ModeIcon className="w-3.5 h-3.5" />
                                    {PAYMENT_MODE_LABELS[inv.payment_mode] || inv.payment_mode}
                                  </span>
                                ) : "—"}
                              </TableCell>
                              <TableCell className="py-2.5 text-center">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={() => handlePdf(inv.id)}
                                  title="Download PDF"
                                >
                                  <Download className="w-3.5 h-3.5 text-slate-400 hover:text-blue-600" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>

              {/* Bottom padding */}
              <div className="h-6" />
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
