import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { toast } from "sonner";
import { BarChart3, IndianRupee, Download, FileText, TrendingUp } from "lucide-react";

const AdminReports = () => {
  const { authAxios } = useAuth();
  const [paymentReport, setPaymentReport] = useState(null);
  const [saasReport, setSaasReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const qs = new URLSearchParams(params).toString();

      const [payRes, saasRes] = await Promise.all([
        authAxios.get(`/admin/reports/payments${qs ? `?${qs}` : ""}`),
        authAxios.get(`/admin/reports/saas-revenue${qs ? `?${qs}` : ""}`)
      ]);
      setPaymentReport(payRes.data);
      setSaasReport(saasRes.data);
    } catch (error) {
      toast.error("Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = (data, filename) => {
    if (!data || !data.by_operator || data.by_operator.length === 0) {
      toast.error("No data to export");
      return;
    }
    const headers = ["Company Name", "Invoices", "Revenue", "Tax"];
    const rows = data.by_operator.map(op => [
      op.company_name, op.count, op.revenue, op.tax
    ]);
    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
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
              <Button onClick={fetchReports} data-testid="filter-reports-btn">
                <BarChart3 className="w-4 h-4 mr-2" /> Apply Filter
              </Button>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="payments">
          <TabsList data-testid="report-tabs">
            <TabsTrigger value="payments" data-testid="tab-payments">Operator Payments</TabsTrigger>
            <TabsTrigger value="saas" data-testid="tab-saas">SaaS Revenue</TabsTrigger>
          </TabsList>

          <TabsContent value="payments" className="mt-6 space-y-6">
            {/* KPIs */}
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
                    ₹{(paymentReport?.total_revenue || 0).toLocaleString('en-IN')}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">Total Tax Collected</p>
                  <p className="text-3xl font-bold mt-1" data-testid="total-tax">
                    ₹{(paymentReport?.total_tax || 0).toLocaleString('en-IN')}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* By Operator */}
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
                        <TableCell>₹{op.revenue?.toLocaleString('en-IN')}</TableCell>
                        <TableCell>₹{op.tax?.toLocaleString('en-IN')}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="saas" className="mt-6 space-y-6">
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
                    ₹{(saasReport?.total_revenue || 0).toLocaleString('en-IN')}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-slate-500">GST Collected</p>
                  <p className="text-3xl font-bold mt-1" data-testid="saas-gst">
                    ₹{(saasReport?.total_gst || 0).toLocaleString('en-IN')}
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
};

export default AdminReports;
