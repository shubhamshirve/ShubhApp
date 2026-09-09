import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { formatDate } from "../../utils/dateFormat";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../../components/ui/table";
import { toast } from "sonner";
import {
  BarChart3, IndianRupee, Download, FileText, TrendingUp,
  Search, ChevronLeft, ChevronRight, Tag,
} from "lucide-react";

const PAGE_SIZE = 20;

const AdminReports = () => {
  const { authAxios } = useAuth();
  const [paymentReport, setPaymentReport] = useState(null);
  const [saasReport, setSaasReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Subscriptions list state
  const [subscriptions, setSubscriptions] = useState([]);
  const [subTotal, setSubTotal] = useState(0);
  const [subTotalPages, setSubTotalPages] = useState(1);
  const [subPage, setSubPage] = useState(1);
  const [subSearch, setSubSearch] = useState("");
  const [subSearchInput, setSubSearchInput] = useState("");
  const [subLoading, setSubLoading] = useState(false);

  useEffect(() => { fetchReports(); }, []);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const qs = new URLSearchParams(params).toString();
      const [payRes, saasRes] = await Promise.all([
        authAxios.get(`/admin/reports/payments${qs ? `?${qs}` : ""}`),
        authAxios.get(`/admin/reports/saas-revenue${qs ? `?${qs}` : ""}`),
      ]);
      setPaymentReport(payRes.data);
      setSaasReport(saasRes.data);
    } catch {
      toast.error("Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscriptions = useCallback(async (page = 1, search = "") => {
    setSubLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: PAGE_SIZE });
      if (search) params.append("search", search);
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      const res = await authAxios.get(`/admin/reports/saas-subscriptions?${params}`);
      setSubscriptions(res.data.subscriptions || []);
      setSubTotal(res.data.total || 0);
      setSubTotalPages(res.data.total_pages || 1);
      setSubPage(page);
    } catch {
      toast.error("Failed to load subscriptions");
    } finally {
      setSubLoading(false);
    }
  }, [authAxios, startDate, endDate]);

  // Load subscriptions when SaaS tab is opened (lazy)
  const handleTabChange = (val) => {
    if (val === "saas" && subscriptions.length === 0) {
      fetchSubscriptions(1, subSearch);
    }
  };

  const handleSubSearch = () => {
    setSubSearch(subSearchInput);
    fetchSubscriptions(1, subSearchInput);
  };

  const handleSubPageChange = (newPage) => {
    if (newPage < 1 || newPage > subTotalPages) return;
    fetchSubscriptions(newPage, subSearch);
  };

  const exportSubCSV = () => {
    if (!subscriptions.length) { toast.error("No data to export"); return; }
    const headers = ["Date", "Company", "Owner", "Plan", "Months", "Base (₹)", "Discount (₹)", "Coupon", "GST (₹)", "Total (₹)", "Type"];
    const rows = subscriptions.map(s => [
      s.created_at ? formatDate(s.created_at) : "-",
      s.company_name, s.owner_name, s.plan_name, s.months,
      s.base_amount, s.discount_amount || 0, s.coupon_code || "-",
      s.gst_amount, s.total_amount, s.item_type,
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `saas_subscriptions_page${subPage}.csv`;
    a.click();
  };

  const exportCSV = (data, filename) => {
    if (!data?.by_operator?.length) { toast.error("No data to export"); return; }
    const headers = ["Company Name", "Invoices", "Revenue", "Tax"];
    const rows = data.by_operator.map(op => [op.company_name, op.count, op.revenue, op.tax]);
    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
  };

  if (loading) {
    return (
      <AdminLayout title="Reports">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Payment Reports">
      <div className="space-y-6 animate-fade-in">
        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row items-end gap-4">
              <div className="space-y-2 flex-1">
                <Label>Start Date</Label>
                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} data-testid="report-start-date" />
              </div>
              <div className="space-y-2 flex-1">
                <Label>End Date</Label>
                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} data-testid="report-end-date" />
              </div>
              <Button onClick={() => { fetchReports(); fetchSubscriptions(1, subSearch); }} data-testid="filter-reports-btn">
                <BarChart3 className="w-4 h-4 mr-2" /> Apply Filter
              </Button>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="payments" onValueChange={handleTabChange}>
          <TabsList data-testid="report-tabs">
            <TabsTrigger value="payments" data-testid="tab-payments">Operator Payments</TabsTrigger>
            <TabsTrigger value="saas" data-testid="tab-saas">SaaS Revenue</TabsTrigger>
          </TabsList>

          {/* ─── Operator Payments Tab ─── */}
          <TabsContent value="payments" className="mt-6 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">Total Invoices Paid</p>
                  <p className="text-3xl font-bold mt-1" data-testid="total-invoices">{paymentReport?.total_invoices || 0}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">Total Revenue</p>
                  <p className="text-3xl font-bold mt-1 text-emerald-600" data-testid="total-revenue">
                    ₹{(paymentReport?.total_revenue || 0).toLocaleString("en-IN")}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">Total Tax Collected</p>
                  <p className="text-3xl font-bold mt-1" data-testid="total-tax">
                    ₹{(paymentReport?.total_tax || 0).toLocaleString("en-IN")}
                  </p>
                </CardContent>
              </Card>
            </div>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Revenue by Operator</CardTitle>
                <Button variant="outline" size="sm" onClick={() => exportCSV(paymentReport, "payment_report.csv")} data-testid="export-payment-csv">
                  <Download className="w-4 h-4 mr-1" /> Export CSV
                </Button>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Company</TableHead>
                      <TableHead>Invoices</TableHead>
                      <TableHead>Revenue</TableHead>
                      <TableHead>Tax</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(!paymentReport?.by_operator || paymentReport.by_operator.length === 0) ? (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center py-8 text-slate-500">No payment data</TableCell>
                      </TableRow>
                    ) : paymentReport.by_operator.map((op, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{op.company_name}</TableCell>
                        <TableCell>{op.count}</TableCell>
                        <TableCell>₹{op.revenue?.toLocaleString("en-IN")}</TableCell>
                        <TableCell>₹{op.tax?.toLocaleString("en-IN")}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ─── SaaS Revenue Tab ─── */}
          <TabsContent value="saas" className="mt-6 space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">Total SaaS Payments</p>
                  <p className="text-3xl font-bold mt-1" data-testid="saas-total-payments">{saasReport?.total_payments || 0}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">SaaS Revenue</p>
                  <p className="text-3xl font-bold mt-1 text-emerald-600" data-testid="saas-revenue">
                    ₹{(saasReport?.total_revenue || 0).toLocaleString("en-IN")}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">GST Collected</p>
                  <p className="text-3xl font-bold mt-1" data-testid="saas-gst">
                    ₹{(saasReport?.total_gst || 0).toLocaleString("en-IN")}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Recent Subscriptions List */}
            <Card>
              <CardHeader>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="w-5 h-5" />
                      Recent Subscriptions
                    </CardTitle>
                    <p className="text-sm text-slate-500 mt-0.5">
                      {subTotal} total record{subTotal !== 1 ? "s" : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Search */}
                    <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Search operator or plan…"
                        value={subSearchInput}
                        onChange={(e) => setSubSearchInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSubSearch()}
                        className="pl-8 pr-3 py-1.5 text-sm border border-slate-200 rounded-md w-56 focus:outline-none focus:ring-2 focus:ring-slate-300"
                        data-testid="sub-search-input"
                      />
                    </div>
                    <Button size="sm" variant="outline" onClick={handleSubSearch} data-testid="sub-search-btn">
                      Search
                    </Button>
                    <Button size="sm" variant="outline" onClick={exportSubCSV} data-testid="export-sub-csv">
                      <Download className="w-4 h-4 mr-1" /> CSV
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {subLoading ? (
                  <div className="flex justify-center py-10">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-700"></div>
                  </div>
                ) : subscriptions.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <FileText className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                    <p>No subscription records found</p>
                    {subSearch && <p className="text-sm mt-1">Try a different search term</p>}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-slate-50">
                          <TableHead>Date</TableHead>
                          <TableHead>Company</TableHead>
                          <TableHead>Plan</TableHead>
                          <TableHead className="text-center">Months</TableHead>
                          <TableHead className="text-right">Base</TableHead>
                          <TableHead className="text-right">Discount</TableHead>
                          <TableHead className="text-right">GST</TableHead>
                          <TableHead className="text-right font-semibold">Total</TableHead>
                          <TableHead>Type</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {subscriptions.map((s) => (
                          <TableRow key={s.id} className="hover:bg-slate-50">
                            <TableCell className="text-sm text-slate-600 whitespace-nowrap">
                              {s.created_at ? formatDate(s.created_at) : "—"}
                            </TableCell>
                            <TableCell>
                              <div>
                                <p className="font-medium text-slate-900 text-sm">{s.company_name}</p>
                                <p className="text-xs text-slate-400">{s.owner_name}</p>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div>
                                <p className="text-sm text-slate-700">{s.plan_name}</p>
                              </div>
                            </TableCell>
                            <TableCell className="text-center text-sm">{s.months}</TableCell>
                            <TableCell className="text-right text-sm">₹{(s.base_amount || 0).toLocaleString("en-IN")}</TableCell>
                            <TableCell className="text-right text-sm">
                              {s.discount_amount > 0 ? (
                                <span className="text-emerald-600">
                                  -₹{s.discount_amount.toLocaleString("en-IN")}
                                  {s.coupon_code && (
                                    <span className="ml-1 inline-flex items-center gap-0.5 text-xs bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded">
                                      <Tag className="w-2.5 h-2.5" />{s.coupon_code}
                                    </span>
                                  )}
                                </span>
                              ) : <span className="text-slate-400">—</span>}
                            </TableCell>
                            <TableCell className="text-right text-sm">₹{(s.gst_amount || 0).toLocaleString("en-IN")}</TableCell>
                            <TableCell className="text-right">
                              <span className="font-semibold text-slate-900">₹{(s.total_amount || 0).toLocaleString("en-IN")}</span>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline" className={`text-xs ${
                                s.item_type === "subscription"
                                  ? "border-blue-200 text-blue-700 bg-blue-50"
                                  : "border-purple-200 text-purple-700 bg-purple-50"
                              }`}>
                                {s.item_type === "subscription" ? "Subscription" : "Add-on"}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}

                {/* Pagination */}
                {subTotalPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
                    <p className="text-sm text-slate-500">
                      Page <span className="font-medium">{subPage}</span> of{" "}
                      <span className="font-medium">{subTotalPages}</span>{" "}
                      &mdash; {subTotal} record{subTotal !== 1 ? "s" : ""}
                    </p>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="outline" size="sm"
                        onClick={() => handleSubPageChange(subPage - 1)}
                        disabled={subPage <= 1}
                        data-testid="sub-prev-btn"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </Button>
                      {/* Page number pills */}
                      {Array.from({ length: Math.min(5, subTotalPages) }, (_, i) => {
                        const pg = Math.max(1, Math.min(subPage - 2, subTotalPages - 4)) + i;
                        return pg <= subTotalPages ? (
                          <Button
                            key={pg}
                            variant={pg === subPage ? "default" : "outline"}
                            size="sm"
                            className="w-8 h-8 p-0"
                            onClick={() => handleSubPageChange(pg)}
                          >
                            {pg}
                          </Button>
                        ) : null;
                      })}
                      <Button
                        variant="outline" size="sm"
                        onClick={() => handleSubPageChange(subPage + 1)}
                        disabled={subPage >= subTotalPages}
                        data-testid="sub-next-btn"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
};

export default AdminReports;
