import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
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
  Banknote,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  IndianRupee,
  TrendingUp,
  Calendar,
  Receipt,
  Building2,
  CreditCard,
  FileText,
  XCircle
} from "lucide-react";

const OperatorSettlements = () => {
  const { authAxios } = useAuth();
  const [settlements, setSettlements] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Detail Dialog
  const [selectedSettlement, setSelectedSettlement] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [settlementDetail, setSettlementDetail] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [settlementsRes, summaryRes] = await Promise.all([
        authAxios.get(`/operator/settlements?page=${page}&limit=15${statusFilter !== "all" ? `&status=${statusFilter}` : ""}`),
        authAxios.get("/operator/settlements/summary"),
      ]);
      setSettlements(settlementsRes.data.settlements || []);
      setTotalPages(settlementsRes.data.pages || 1);
      setSummary(summaryRes.data);
    } catch (error) {
      toast.error("Failed to load settlements");
    } finally {
      setLoading(false);
    }
  }, [authAxios, page, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const fetchSettlementDetail = async (settlementId) => {
    setDetailLoading(true);
    try {
      const res = await authAxios.get(`/operator/settlements/${settlementId}`);
      setSettlementDetail(res.data);
    } catch (error) {
      toast.error("Failed to load settlement details");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleViewDetails = (settlement) => {
    setSelectedSettlement(settlement);
    fetchSettlementDetail(settlement.id);
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: { class: "bg-amber-100 text-amber-700", icon: Clock },
      processing: { class: "bg-blue-100 text-blue-700", icon: Loader2 },
      completed: { class: "bg-emerald-100 text-emerald-700", icon: CheckCircle2 },
      failed: { class: "bg-red-100 text-red-700", icon: XCircle },
    };
    const badge = badges[status] || badges.pending;
    const Icon = badge.icon;
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.class}`}>
        <Icon className={`w-3 h-3 ${status === "processing" ? "animate-spin" : ""}`} />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amount || 0);
  };

  const filteredSettlements = settlements.filter(s =>
    s.settlement_date.includes(searchTerm) ||
    s.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <OperatorLayout title="Settlements">
      <div className="space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-l-4 border-l-emerald-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Total Settled</p>
                  <p className="text-2xl font-bold text-emerald-600">
                    {formatCurrency(summary?.total_settled)}
                  </p>
                </div>
                <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-amber-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Pending</p>
                  <p className="text-2xl font-bold text-amber-600">
                    {formatCurrency(summary?.total_pending)}
                  </p>
                </div>
                <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center">
                  <Clock className="w-6 h-6 text-amber-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Total Collections</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {formatCurrency(summary?.total_collections)}
                  </p>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-purple-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Platform Fees Paid</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {formatCurrency(summary?.total_platform_fee)}
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                  <Banknote className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <Banknote className="w-5 h-5 text-[#0066B2]" />
              Settlement History
            </CardTitle>
            <CardDescription>
              View all your settlement records and payment history
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by date or ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Settlements Table */}
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50">
                    <TableHead>Date</TableHead>
                    <TableHead>Collections</TableHead>
                    <TableHead>Platform Fee</TableHead>
                    <TableHead>Net Settlement</TableHead>
                    <TableHead>Invoices</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin mx-auto text-slate-400" />
                      </TableCell>
                    </TableRow>
                  ) : filteredSettlements.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                        No settlements found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredSettlements.map((settlement) => (
                      <TableRow key={settlement.id} className="hover:bg-slate-50">
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-slate-400" />
                            {settlement.settlement_date}
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">
                          {formatCurrency(settlement.total_collections)}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            <span className="text-red-600">{formatCurrency(settlement.platform_fee)}</span>
                            <span className="text-xs text-slate-400 ml-1">
                              ({settlement.platform_fee_percentage}%)
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="font-bold text-emerald-600">
                          {formatCurrency(settlement.net_settlement)}
                        </TableCell>
                        <TableCell>
                          <span className="bg-slate-100 px-2 py-1 rounded text-xs font-medium">
                            {settlement.payment_count} invoices
                          </span>
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(settlement.status)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDetails(settlement)}
                            className="text-[#0066B2] hover:text-[#004080]"
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            View Details
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-slate-500">
                  Page {page} of {totalPages}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Settlement Detail Dialog */}
        <Dialog open={!!selectedSettlement} onOpenChange={() => setSelectedSettlement(null)}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Receipt className="w-5 h-5 text-[#0066B2]" />
                Settlement Details
              </DialogTitle>
              <DialogDescription>
                Settlement for {selectedSettlement?.settlement_date}
              </DialogDescription>
            </DialogHeader>
            
            {detailLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
              </div>
            ) : settlementDetail && (
              <div className="space-y-6">
                {/* Status Banner */}
                <div className={`p-4 rounded-lg ${
                  settlementDetail.status === "completed" ? "bg-emerald-50 border border-emerald-200" :
                  settlementDetail.status === "pending" ? "bg-amber-50 border border-amber-200" :
                  settlementDetail.status === "processing" ? "bg-blue-50 border border-blue-200" :
                  "bg-red-50 border border-red-200"
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusBadge(settlementDetail.status)}
                      {settlementDetail.utr_number && (
                        <span className="text-sm text-slate-600">
                          UTR: <span className="font-mono font-medium">{settlementDetail.utr_number}</span>
                        </span>
                      )}
                    </div>
                    {settlementDetail.paid_at && (
                      <span className="text-sm text-slate-500">
                        Paid: {new Date(settlementDetail.paid_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>

                {/* Financial Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Total Collections</p>
                    <p className="text-xl font-bold text-slate-900 mt-1">
                      {formatCurrency(settlementDetail.total_collections)}
                    </p>
                  </div>
                  <div className="p-4 bg-red-50 rounded-lg">
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Platform Fee ({settlementDetail.platform_fee_percentage}%)</p>
                    <p className="text-xl font-bold text-red-600 mt-1">
                      -{formatCurrency(settlementDetail.platform_fee)}
                    </p>
                  </div>
                  <div className="p-4 bg-orange-50 rounded-lg">
                    <p className="text-xs text-slate-500 uppercase tracking-wide">GST on Fee (18%)</p>
                    <p className="text-xl font-bold text-orange-600 mt-1">
                      -{formatCurrency(settlementDetail.tax_on_platform_fee)}
                    </p>
                  </div>
                  <div className="p-4 bg-emerald-50 rounded-lg">
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Net Settlement</p>
                    <p className="text-xl font-bold text-emerald-600 mt-1">
                      {formatCurrency(settlementDetail.net_settlement)}
                    </p>
                  </div>
                </div>

                {/* Bank Details */}
                {settlementDetail.operator_details && (
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-slate-700 flex items-center gap-2 mb-3">
                      <Building2 className="w-4 h-4" />
                      Bank Account Details
                    </h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-slate-500">Account Name</p>
                        <p className="font-medium">{settlementDetail.operator_details.bank_account_name || "-"}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Account Number</p>
                        <p className="font-mono font-medium">{settlementDetail.operator_details.bank_account_number || "-"}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">IFSC Code</p>
                        <p className="font-mono font-medium">{settlementDetail.operator_details.bank_ifsc || "-"}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Bank Name</p>
                        <p className="font-medium">{settlementDetail.operator_details.bank_name || "-"}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Included Invoices */}
                <div>
                  <h4 className="font-medium text-slate-700 flex items-center gap-2 mb-3">
                    <FileText className="w-4 h-4" />
                    Included Invoices ({settlementDetail.payment_count})
                  </h4>
                  <div className="rounded-lg border overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-slate-50">
                          <TableHead>Invoice #</TableHead>
                          <TableHead>Subscriber</TableHead>
                          <TableHead>Plan</TableHead>
                          <TableHead>Amount</TableHead>
                          <TableHead>Paid At</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {settlementDetail.invoices?.map((inv) => (
                          <TableRow key={inv.id}>
                            <TableCell className="font-mono text-sm">{inv.invoice_number}</TableCell>
                            <TableCell>{inv.subscriber_name}</TableCell>
                            <TableCell>{inv.plan_name}</TableCell>
                            <TableCell className="font-medium">{formatCurrency(inv.final_amount)}</TableCell>
                            <TableCell className="text-sm text-slate-500">
                              {inv.paid_at ? new Date(inv.paid_at).toLocaleString() : "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>

                {/* Settlement ID */}
                <div className="text-center text-xs text-slate-400 pt-4 border-t">
                  Settlement ID: <span className="font-mono">{settlementDetail.id}</span>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorSettlements;
