import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { toast } from "sonner";
import {
  Search,
  Download,
  Printer,
  RefreshCw,
  ChevronDown,
  BadgeDollarSign,
  TrendingUp,
  CreditCard,
  Users,
} from "lucide-react";
import * as XLSX from "xlsx";
import { formatDate, formatDateTime } from "../../utils/dateFormat";

// Payment mode labels
const MODE_LABELS = {
  cash: "Cash",
  online: "Online",
  upi: "UPI",
  bank_transfer: "Bank Transfer",
  cheque: "Cheque",
  card: "Card",
  neft: "NEFT",
  rtgs: "RTGS",
  imps: "IMPS",
  razorpay: "Razorpay",
  stripe: "Stripe",
  other: "Other",
};

const formatCurrency = (v) =>
  `₹${Number(v || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

const StatusBadge = ({ status }) => {
  if (status === "paid")
    return (
      <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 font-medium text-xs">
        Paid
      </Badge>
    );
  if (status === "partial")
    return (
      <Badge className="bg-amber-100 text-amber-700 border-amber-200 font-medium text-xs">
        Partial
      </Badge>
    );
  return <Badge variant="outline">{status}</Badge>;
};

export default function OperatorPayments() {
  const { authAxios } = useAuth();
  const [payments, setPayments] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const printRef = useRef(null);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const fetchPayments = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: 500 });
      if (debouncedSearch) params.set("search", debouncedSearch);
      const res = await authAxios.get(`/operator/payments?${params}`);
      setPayments(res.data.payments || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      toast.error("Failed to load payments");
    } finally {
      setLoading(false);
    }
  }, [authAxios, debouncedSearch]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  // ── Stats ──────────────────────────────────────────────────────────────────
  const totalAmount = payments.reduce((s, p) => s + (p.amount_paid || 0), 0);
  const uniqueSubscribers = new Set(payments.map((p) => p.subscriber_id)).size;
  const modesCount = payments.reduce((acc, p) => {
    const m = p.payment_mode || "unknown";
    acc[m] = (acc[m] || 0) + 1;
    return acc;
  }, {});
  const topMode = Object.entries(modesCount).sort((a, b) => b[1] - a[1])[0]?.[0] || "—";

  // ── Export ─────────────────────────────────────────────────────────────────
  const exportData = payments.map((p, i) => ({
    "#": i + 1,
    "Invoice No.": p.invoice_number || "—",
    "Subscriber": p.subscriber_name || "—",
    "Invoice Amount": p.amount || 0,
    "Amount Paid": p.amount_paid || 0,
    "Payment Mode": MODE_LABELS[p.payment_mode] || p.payment_mode || "—",
    "Payment ID": p.payment_id || "—",
    "Paid On": p.paid_at ? formatDate(p.paid_at) : "—",
    "Invoice Date": p.created_at ? formatDate(p.created_at) : "—",
    "Status": p.status === "paid" ? "Paid" : "Partial",
  }));

  const handleExportXLSX = () => {
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Payments");
    XLSX.writeFile(wb, `payments_${new Date().toISOString().slice(0, 10)}.xlsx`);
    toast.success("Exported as XLSX");
  };

  const handleExportCSV = () => {
    const ws = XLSX.utils.json_to_sheet(exportData);
    const csv = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `payments_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Exported as CSV");
  };

  const handlePrint = () => {
    const printContent = printRef.current?.innerHTML;
    if (!printContent) return;
    const win = window.open("", "_blank");
    win.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Payments Report</title>
          <style>
            body { font-family: Arial, sans-serif; font-size: 12px; margin: 20px; color: #111; }
            h2 { color: #004080; margin-bottom: 4px; }
            p.sub { color: #666; margin-bottom: 16px; font-size: 11px; }
            table { width: 100%; border-collapse: collapse; }
            th { background: #004080; color: #fff; padding: 6px 8px; text-align: left; font-size: 11px; }
            td { padding: 5px 8px; border-bottom: 1px solid #e2e8f0; font-size: 11px; }
            tr:nth-child(even) td { background: #f8fafc; }
            .text-right { text-align: right; }
            .badge-paid { background: #d1fae5; color: #065f46; padding: 1px 6px; border-radius: 4px; }
            .badge-partial { background: #fef3c7; color: #92400e; padding: 1px 6px; border-radius: 4px; }
            .footer { margin-top: 20px; font-size: 10px; color: #666; border-top: 1px solid #e2e8f0; padding-top: 8px; }
          </style>
        </head>
        <body>
          <h2>Payments Report</h2>
          <p class="sub">Generated on ${formatDateTime(new Date())} &nbsp;|&nbsp; Total: ${total} payments</p>
          ${printContent}
          <p class="footer">Printed from E-Bill &mdash; ${window.location.origin}</p>
        </body>
      </html>
    `);
    win.document.close();
    win.focus();
    win.print();
    win.close();
  };

  return (
    <OperatorLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Payments</h1>
            <p className="text-slate-500 text-sm mt-0.5">
              All payments received from subscribers
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchPayments}
              disabled={loading}
              className="gap-1.5"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrint}
              className="gap-1.5"
            >
              <Printer className="w-4 h-4" />
              Print
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" className="gap-1.5 bg-[#0066B2] hover:bg-[#0052A3]">
                  <Download className="w-4 h-4" />
                  Export
                  <ChevronDown className="w-3 h-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleExportXLSX}>
                  Export as XLSX
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleExportCSV}>
                  Export as CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-0 shadow-sm bg-gradient-to-br from-emerald-50 to-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <BadgeDollarSign className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Total Collected</p>
                  <p className="text-lg font-bold text-slate-900">
                    {formatCurrency(totalAmount)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-0 shadow-sm bg-gradient-to-br from-blue-50 to-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Total Payments</p>
                  <p className="text-lg font-bold text-slate-900">{total}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-0 shadow-sm bg-gradient-to-br from-violet-50 to-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-violet-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Unique Subscribers</p>
                  <p className="text-lg font-bold text-slate-900">{uniqueSubscribers}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-0 shadow-sm bg-gradient-to-br from-amber-50 to-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                  <CreditCard className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Top Mode</p>
                  <p className="text-lg font-bold text-slate-900 capitalize">
                    {MODE_LABELS[topMode] || topMode}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search by name, invoice no., mode..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Table */}
        <Card className="border-0 shadow-sm overflow-hidden">
          <div ref={printRef}>
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead className="w-8 text-center">#</TableHead>
                  <TableHead>Invoice No.</TableHead>
                  <TableHead>Subscriber</TableHead>
                  <TableHead className="text-right">Invoice Amt</TableHead>
                  <TableHead className="text-right">Paid Amt</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Payment ID</TableHead>
                  <TableHead>Paid On</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-12 text-slate-400">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                      Loading payments...
                    </TableCell>
                  </TableRow>
                ) : payments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-16 text-slate-400">
                      <BadgeDollarSign className="w-10 h-10 mx-auto mb-3 opacity-30" />
                      <p className="font-medium">No payments found</p>
                      <p className="text-sm mt-1">
                        {search
                          ? "Try a different search term"
                          : "Payments will appear here once invoices are marked as paid"}
                      </p>
                    </TableCell>
                  </TableRow>
                ) : (
                  payments.map((p, i) => (
                    <TableRow key={p.id} className="hover:bg-slate-50/50">
                      <TableCell className="text-center text-slate-400 text-xs">
                        {i + 1}
                      </TableCell>
                      <TableCell className="font-medium text-[#0066B2] text-sm">
                        {p.invoice_number || `#${p.id?.slice(-6)}`}
                      </TableCell>
                      <TableCell className="text-sm font-medium text-slate-800">
                        {p.subscriber_name || "—"}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {formatCurrency(p.amount)}
                      </TableCell>
                      <TableCell className="text-right text-sm font-semibold text-emerald-700">
                        {formatCurrency(p.amount_paid)}
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-700 text-xs font-medium">
                          {MODE_LABELS[p.payment_mode] || p.payment_mode || "—"}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500 font-mono">
                        {p.payment_id || "—"}
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">
                        {p.paid_at ? formatDate(p.paid_at) : "—"}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={p.status} />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {!loading && payments.length > 0 && (
            <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>
                Showing {payments.length} of {total} payments
              </span>
              <span className="font-semibold text-slate-700">
                Total: {formatCurrency(totalAmount)}
              </span>
            </div>
          )}
        </Card>
      </div>
    </OperatorLayout>
  );
}
