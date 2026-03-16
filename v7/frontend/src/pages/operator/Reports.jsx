import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Calendar } from "../../components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../../components/ui/popover";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { toast } from "sonner";
import { format } from "date-fns";
import { 
  CalendarIcon, 
  IndianRupee, 
  TrendingUp, 
  FileText,
  AlertTriangle,
  Download
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

            <Button onClick={fetchReports} disabled={loading} data-testid="apply-filter-btn">
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
          </Tabs>
        )}
      </div>
    </OperatorLayout>
  );
};

export default OperatorReports;
