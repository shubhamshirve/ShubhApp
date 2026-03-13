import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Calendar } from "../../components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../../components/ui/popover";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { toast } from "sonner";
import { format } from "date-fns";
import { 
  CalendarIcon, 
  IndianRupee, 
  TrendingUp, 
  FileText,
  AlertTriangle,
  Download,
  Search,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Receipt
} from "lucide-react";

const OperatorReports = () => {
  const { authAxios } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [revenueReport, setRevenueReport] = useState(null);
  const [gstReport, setGstReport] = useState(null);
  const [pendingReport, setPendingReport] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setDate(1)),
    end: new Date()
  });

  // Recent invoices state
  const [recentInvoices, setRecentInvoices] = useState([]);
  const [invoicePage, setInvoicePage] = useState(1);
  const [invoiceTotal, setInvoiceTotal] = useState(0);
  const [invoiceTotalPages, setInvoiceTotalPages] = useState(1);
  const [invoiceLimit] = useState(15);
  const [invoiceSearch, setInvoiceSearch] = useState("");
  const [invoiceStatus, setInvoiceStatus] = useState("all");
  const [invoiceLoading, setInvoiceLoading] = useState(false);
  const [invoiceSortBy, setInvoiceSortBy] = useState("created_at");
  const [invoiceSortOrder, setInvoiceSortOrder] = useState("desc");

  useEffect(() => {
    fetchDashboard();
    fetchReports();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await authAxios.get("/operator/dashboard");
      setDashboardStats(response.data);
    } catch (error) {
      console.error("Failed to load dashboard");
    }
  };

  const fetchReports = async () => {
    setLoading(true);
    try {
      const startDate = format(dateRange.start, "yyyy-MM-dd");
      const endDate = format(dateRange.end, "yyyy-MM-dd");

      const [revenue, gst, pending, invoiceRes] = await Promise.all([
        authAxios.get(`/operator/reports/revenue?start_date=${startDate}&end_date=${endDate}`),
        authAxios.get(`/operator/reports/gst-summary?start_date=${startDate}&end_date=${endDate}`),
        authAxios.get("/operator/reports/pending-overdue"),
        authAxios.get("/operator/invoices").catch(() => ({ data: [] }))
      ]);

      setRevenueReport(revenue.data);
      setGstReport(gst.data);
      setPendingReport(pending.data);
      setInvoices(Array.isArray(invoiceRes.data) ? invoiceRes.data : []);
    } catch (error) {
      toast.error("Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentInvoices = useCallback(async (page = 1) => {
    setInvoiceLoading(true);
    try {
      const startDate = format(dateRange.start, "yyyy-MM-dd");
      const endDate = format(dateRange.end, "yyyy-MM-dd");
      const params = new URLSearchParams({
        page: String(page),
        limit: String(invoiceLimit),
        start_date: startDate,
        end_date: endDate,
        sort_by: invoiceSortBy,
        sort_order: invoiceSortOrder,
      });
      if (invoiceStatus && invoiceStatus !== "all") params.set("status", invoiceStatus);
      if (invoiceSearch.trim()) params.set("search", invoiceSearch.trim());

      const res = await authAxios.get(`/operator/reports/invoices?${params.toString()}`);
      setRecentInvoices(res.data.invoices || []);
      setInvoiceTotal(res.data.total || 0);
      setInvoiceTotalPages(res.data.total_pages || 1);
      setInvoicePage(res.data.page || 1);
    } catch {
      toast.error("Failed to load invoices");
    } finally {
      setInvoiceLoading(false);
    }
  }, [authAxios, dateRange, invoiceLimit, invoiceSearch, invoiceStatus, invoiceSortBy, invoiceSortOrder]);

  // Fetch recent invoices when tab changes or filters change
  useEffect(() => {
    fetchRecentInvoices(1);
  }, [invoiceStatus, invoiceSortBy, invoiceSortOrder]);

  const handleInvoiceSearch = (e) => {
    e.preventDefault();
    fetchRecentInvoices(1);
  };

  const handleSort = (field) => {
    if (invoiceSortBy === field) {
      setInvoiceSortOrder(prev => prev === "desc" ? "asc" : "desc");
    } else {
      setInvoiceSortBy(field);
      setInvoiceSortOrder("desc");
    }
  };

  const exportInvoicesCSV = () => {
    if (!invoices.length) {
      toast.error("No invoice data to export");
      return;
    }
    const headers = ["Invoice #", "Subscriber", "Amount", "Tax", "Total", "Status", "Due Date", "Created"];
    const rows = invoices.map(inv => [
      inv.invoice_number || "",
      inv.subscriber_name || "",
      inv.base_amount || 0,
      inv.tax_amount || 0,
      inv.final_amount || 0,
      inv.status || "",
      inv.due_date ? new Date(inv.due_date).toLocaleDateString("en-IN") : "",
      inv.created_at ? new Date(inv.created_at).toLocaleDateString("en-IN") : ""
    ]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `invoices_${format(dateRange.start, "yyyyMMdd")}_${format(dateRange.end, "yyyyMMdd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("CSV exported");
  };

  const exportGSTCSV = () => {
    if (!gstReport) { toast.error("No GST data"); return; }
    const headers = ["Metric", "Amount (₹)"];
    const rows = [
      ["Taxable Amount", gstReport.total_taxable_amount || 0],
      ["Total GST", gstReport.total_gst_collected || 0],
      ["CGST (9%)", gstReport.cgst || 0],
      ["SGST (9%)", gstReport.sgst || 0]
    ];
    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gst_report_${format(dateRange.start, "yyyyMMdd")}_${format(dateRange.end, "yyyyMMdd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("GST report exported");
  };

  const statusBadge = (status) => {
    const styles = {
      paid: "bg-emerald-100 text-emerald-700 border-emerald-200",
      pending: "bg-amber-100 text-amber-700 border-amber-200",
      overdue: "bg-red-100 text-red-700 border-red-200",
      cancelled: "bg-slate-100 text-slate-500 border-slate-200",
    };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status] || "bg-slate-100 text-slate-600"}`}>
        {status?.charAt(0).toUpperCase() + status?.slice(1)}
      </span>
    );
  };

  const SortHeader = ({ field, label }) => (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-900 select-none"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <ArrowUpDown className={`w-3 h-3 ${invoiceSortBy === field ? "text-slate-900" : "text-slate-300"}`} />
      </div>
    </th>
  );

  const isReadOnly = dashboardStats?.is_read_only;

  return (
    <OperatorLayout title="Reports" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Date Range Filter */}
        <Card className="p-4">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-[180px] justify-start text-left font-normal">
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {format(dateRange.start, "PP")}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={dateRange.start}
                    onSelect={(date) => date && setDateRange(prev => ({ ...prev, start: date }))}
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-2">
              <Label>End Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-[180px] justify-start text-left font-normal">
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {format(dateRange.end, "PP")}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={dateRange.end}
                    onSelect={(date) => date && setDateRange(prev => ({ ...prev, end: date }))}
                  />
                </PopoverContent>
              </Popover>
            </div>

            <Button onClick={() => { fetchReports(); fetchRecentInvoices(1); }} disabled={loading} data-testid="apply-filter-btn">
              Apply Filter
            </Button>
          </div>
        </Card>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
          </div>
        ) : (
          <Tabs defaultValue="revenue" className="space-y-6">
            <TabsList>
              <TabsTrigger value="revenue" data-testid="tab-revenue">Revenue</TabsTrigger>
              <TabsTrigger value="gst" data-testid="tab-gst">GST Summary</TabsTrigger>
              <TabsTrigger value="pending" data-testid="tab-pending">Pending & Overdue</TabsTrigger>
              <TabsTrigger value="invoices" data-testid="tab-invoices" onClick={() => fetchRecentInvoices(1)}>
                <Receipt className="w-4 h-4 mr-1" /> Recent Invoices
              </TabsTrigger>
            </TabsList>

            {/* Revenue Tab */}
            <TabsContent value="revenue" className="space-y-4">
              <div className="flex justify-end">
                <Button variant="outline" size="sm" onClick={exportInvoicesCSV} data-testid="export-invoices-csv">
                  <Download className="w-4 h-4 mr-1" /> Export Invoices CSV
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="kpi-card">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                      <IndianRupee className="w-6 h-6 text-emerald-600" />
                    </div>
                    <div>
                      <p className="kpi-value">₹{(revenueReport?.total_revenue || 0).toLocaleString('en-IN')}</p>
                      <p className="kpi-label">Total Revenue</p>
                    </div>
                  </div>
                </Card>

                <Card className="kpi-card">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                      <p className="kpi-value">{revenueReport?.total_invoices || 0}</p>
                      <p className="kpi-label">Total Invoices</p>
                    </div>
                  </div>
                </Card>

                <Card className="kpi-card">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                      <TrendingUp className="w-6 h-6 text-purple-600" />
                    </div>
                    <div>
                      <p className="kpi-value">₹{(revenueReport?.total_base_amount || 0).toLocaleString('en-IN')}</p>
                      <p className="kpi-label">Base Amount</p>
                    </div>
                  </div>
                </Card>

                <Card className="kpi-card">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center">
                      <IndianRupee className="w-6 h-6 text-amber-600" />
                    </div>
                    <div>
                      <p className="kpi-value">₹{(revenueReport?.total_discount || 0).toLocaleString('en-IN')}</p>
                      <p className="kpi-label">Total Discount</p>
                    </div>
                  </div>
                </Card>
              </div>
            </TabsContent>

            {/* GST Tab */}
            <TabsContent value="gst" className="space-y-4">
              <div className="flex justify-end">
                <Button variant="outline" size="sm" onClick={exportGSTCSV} data-testid="export-gst-csv">
                  <Download className="w-4 h-4 mr-1" /> Export GST CSV
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="kpi-card">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                      <IndianRupee className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                      <p className="kpi-value">₹{(gstReport?.total_taxable_amount || 0).toLocaleString('en-IN')}</p>
                      <p className="kpi-label">Taxable Amount</p>
                    </div>
                  </div>
                </Card>

                <Card className="kpi-card">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                      <TrendingUp className="w-6 h-6 text-emerald-600" />
                    </div>
                    <div>
                      <p className="kpi-value">₹{(gstReport?.total_gst_collected || 0).toLocaleString('en-IN')}</p>
                      <p className="kpi-label">Total GST</p>
                    </div>
                  </div>
                </Card>

                <Card className="kpi-card">
                  <div>
                    <p className="kpi-value">₹{(gstReport?.cgst || 0).toLocaleString('en-IN')}</p>
                    <p className="kpi-label">CGST (9%)</p>
                  </div>
                </Card>

                <Card className="kpi-card">
                  <div>
                    <p className="kpi-value">₹{(gstReport?.sgst || 0).toLocaleString('en-IN')}</p>
                    <p className="kpi-label">SGST (9%)</p>
                  </div>
                </Card>
              </div>
            </TabsContent>

            {/* Pending & Overdue Tab */}
            <TabsContent value="pending" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="kpi-card border-amber-200 bg-amber-50/50">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-amber-600" />
                    </div>
                    <div>
                      <p className="kpi-value text-amber-900">{pendingReport?.pending_count || 0}</p>
                      <p className="kpi-label text-amber-700">Pending Invoices</p>
                      <p className="text-sm font-medium text-amber-800 mt-1">
                        ₹{(pendingReport?.pending_amount || 0).toLocaleString('en-IN')}
                      </p>
                    </div>
                  </div>
                </Card>

                <Card className="kpi-card border-red-200 bg-red-50/50">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                      <AlertTriangle className="w-6 h-6 text-red-600" />
                    </div>
                    <div>
                      <p className="kpi-value text-red-900">{pendingReport?.overdue_count || 0}</p>
                      <p className="kpi-label text-red-700">Overdue Invoices</p>
                      <p className="text-sm font-medium text-red-800 mt-1">
                        ₹{(pendingReport?.overdue_amount || 0).toLocaleString('en-IN')}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>
            </TabsContent>

            {/* Recent Invoices Tab */}
            <TabsContent value="invoices" className="space-y-4">
              {/* Filters & Search */}
              <div className="flex flex-wrap items-center gap-3">
                <form onSubmit={handleInvoiceSearch} className="flex items-center gap-2 flex-1 min-w-[200px] max-w-sm">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      placeholder="Search invoice # or subscriber..."
                      value={invoiceSearch}
                      onChange={(e) => setInvoiceSearch(e.target.value)}
                      className="pl-9"
                      data-testid="invoice-search"
                    />
                  </div>
                  <Button type="submit" size="sm" variant="outline" data-testid="invoice-search-btn">
                    Search
                  </Button>
                </form>

                <Select value={invoiceStatus} onValueChange={(v) => { setInvoiceStatus(v); setInvoicePage(1); }}>
                  <SelectTrigger className="w-[150px]" data-testid="invoice-status-filter">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="paid">Paid</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="overdue">Overdue</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>

                <div className="ml-auto text-sm text-slate-500">
                  {invoiceTotal} invoice{invoiceTotal !== 1 ? "s" : ""} found
                </div>
              </div>

              {/* Invoice Table */}
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-50 border-b">
                      <tr>
                        <SortHeader field="invoice_number" label="Invoice #" />
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Subscriber</th>
                        <SortHeader field="final_amount" label="Amount" />
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Tax</th>
                        <SortHeader field="status" label="Status" />
                        <SortHeader field="due_date" label="Due Date" />
                        <SortHeader field="created_at" label="Created" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {invoiceLoading ? (
                        <tr>
                          <td colSpan={7} className="text-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900 mx-auto"></div>
                            <p className="text-sm text-slate-500 mt-2">Loading invoices...</p>
                          </td>
                        </tr>
                      ) : recentInvoices.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="text-center py-12 text-slate-500">
                            <FileText className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                            No invoices found for the selected criteria
                          </td>
                        </tr>
                      ) : (
                        recentInvoices.map((inv) => (
                          <tr key={inv.id} className="hover:bg-slate-50/50 transition-colors">
                            <td className="px-4 py-3">
                              <span className="font-mono text-sm font-medium text-slate-900">{inv.invoice_number}</span>
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-sm text-slate-700">{inv.subscriber_name}</span>
                            </td>
                            <td className="px-4 py-3">
                              <span className="font-semibold text-slate-900">₹{(inv.final_amount || 0).toLocaleString('en-IN')}</span>
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-sm text-slate-500">₹{(inv.tax_amount || 0).toLocaleString('en-IN')}</span>
                            </td>
                            <td className="px-4 py-3">
                              {statusBadge(inv.status)}
                            </td>
                            <td className="px-4 py-3 text-sm text-slate-600">
                              {inv.due_date ? new Date(inv.due_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—"}
                            </td>
                            <td className="px-4 py-3 text-sm text-slate-500">
                              {inv.created_at ? new Date(inv.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—"}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {invoiceTotalPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t bg-slate-50/50">
                    <div className="text-sm text-slate-600">
                      Page {invoicePage} of {invoiceTotalPages}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={invoicePage <= 1}
                        onClick={() => fetchRecentInvoices(invoicePage - 1)}
                      >
                        <ChevronLeft className="w-4 h-4 mr-1" /> Previous
                      </Button>
                      {/* Page number buttons (show max 5) */}
                      {Array.from({ length: Math.min(5, invoiceTotalPages) }, (_, i) => {
                        let pageNum;
                        if (invoiceTotalPages <= 5) {
                          pageNum = i + 1;
                        } else if (invoicePage <= 3) {
                          pageNum = i + 1;
                        } else if (invoicePage >= invoiceTotalPages - 2) {
                          pageNum = invoiceTotalPages - 4 + i;
                        } else {
                          pageNum = invoicePage - 2 + i;
                        }
                        return (
                          <Button
                            key={pageNum}
                            variant={invoicePage === pageNum ? "default" : "outline"}
                            size="sm"
                            className="w-8 h-8 p-0"
                            onClick={() => fetchRecentInvoices(pageNum)}
                          >
                            {pageNum}
                          </Button>
                        );
                      })}
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={invoicePage >= invoiceTotalPages}
                        onClick={() => fetchRecentInvoices(invoicePage + 1)}
                      >
                        Next <ChevronRight className="w-4 h-4 ml-1" />
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </OperatorLayout>
  );
};

export default OperatorReports;
