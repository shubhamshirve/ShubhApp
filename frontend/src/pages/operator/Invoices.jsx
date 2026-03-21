import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { Calendar } from "../../components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../../components/ui/popover";
import { toast } from "sonner";
import { format } from "date-fns";
import { 
  Plus, 
  Search, 
  MoreVertical, 
  FileText, 
  CheckCircle, 
  Clock,
  AlertTriangle,
  CalendarIcon,
  IndianRupee,
  Link2,
  Download,
  QrCode,
  Send,
  Bell,
  MessageCircle,
  ExternalLink,
  Eye,
  Trash2
} from "lucide-react";

const OperatorInvoices = () => {
  const { authAxios, features } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [subscribers, setSubscribers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showDialog, setShowDialog] = useState(false);
  const [showPaymentLinkDialog, setShowPaymentLinkDialog] = useState(false);
  const [paymentLinkData, setPaymentLinkData] = useState(null);
  const [generatingLink, setGeneratingLink] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [formData, setFormData] = useState({
    subscriber_id: "",
    line_items: [{
      plan_id: "",
      base_amount: 0,
      discount: 0,
      service_start_date: new Date(),
      service_end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
    }],
    due_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000)
  });

  useEffect(() => {
    fetchInvoices();
    fetchSubscribers();
    fetchPlans();
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await authAxios.get("/operator/dashboard");
      setDashboardStats(response.data);
    } catch (error) {
      console.error("Failed to load dashboard");
    }
  };

  const fetchInvoices = async () => {
    try {
      const response = await authAxios.get("/operator/invoices");
      setInvoices(response.data);
    } catch (error) {
      toast.error("Failed to load invoices");
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscribers = async () => {
    try {
      const response = await authAxios.get("/operator/subscribers");
      setSubscribers(response.data);
    } catch (error) {
      console.error("Failed to load subscribers");
    }
  };

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/operator/plans");
      setPlans(response.data);
    } catch (error) {
      console.error("Failed to load plans");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Validation
    if (!formData.subscriber_id) { toast.error("Please select a subscriber"); return; }
    if (formData.line_items.length === 0) { toast.error("Please add at least one line item"); return; }
    
    for (const item of formData.line_items) {
      if (!item.plan_id) { toast.error("Please select a plan for all items"); return; }
      if (item.base_amount <= 0) { toast.error("Base amount must be greater than 0"); return; }
      if (item.discount < 0) { toast.error("Discount cannot be negative"); return; }
      if (item.discount > item.base_amount) { toast.error("Discount cannot exceed base amount"); return; }
      if (!item.service_start_date) { toast.error("Please select a service start date"); return; }
      if (!item.service_end_date) { toast.error("Please select a service end date"); return; }
      if (item.service_end_date <= item.service_start_date) {
        toast.error("Service end date must be after start date"); return;
      }
    }
    
    if (!formData.due_date) { toast.error("Please select a due date"); return; }
    
    try {
      const payload = {
        subscriber_id: formData.subscriber_id,
        due_date: formData.due_date.toISOString(),
        line_items: formData.line_items.map(item => ({
          ...item,
          service_start_date: item.service_start_date.toISOString(),
          service_end_date: item.service_end_date.toISOString()
        }))
      };
      
      await authAxios.post("/operator/invoices", payload);
      toast.success("Invoice created successfully");
      setShowDialog(false);
      resetForm();
      fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create invoice");
    }
  };

  const addLineItem = () => {
    setFormData(prev => ({
      ...prev,
      line_items: [...prev.line_items, {
        plan_id: "",
        base_amount: 0,
        discount: 0,
        service_start_date: new Date(),
        service_end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
      }]
    }));
  };

  const removeLineItem = (index) => {
    setFormData(prev => ({
      ...prev,
      line_items: prev.line_items.filter((_, i) => i !== index)
    }));
  };

  const updateLineItem = (index, field, value) => {
    const updatedItems = [...formData.line_items];
    updatedItems[index] = { ...updatedItems[index], [field]: value };
    
    // Auto-fill price if plan is selected
    if (field === "plan_id") {
      const plan = plans.find(p => p.id === value);
      if (plan) {
        updatedItems[index].base_amount = plan.price;
      }
    }
    
    setFormData(prev => ({ ...prev, line_items: updatedItems }));
  };

  const resetForm = () => {
    setFormData({
      subscriber_id: "",
      line_items: [{
        plan_id: "",
        base_amount: 0,
        discount: 0,
        service_start_date: new Date(),
        service_end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
      }],
      due_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000)
    });
  };

  const handleStatusUpdate = async (invoiceId, status) => {
    try {
      await authAxios.put(`/operator/invoices/${invoiceId}/status?status=${status}`);
      toast.success(`Invoice marked as ${status}`);
      fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update status");
    }
  };

  const handleGeneratePaymentLink = async (invoiceId) => {
    setGeneratingLink(true);
    try {
      const response = await authAxios.post(`/operator/invoices/${invoiceId}/payment-link`);
      setPaymentLinkData(response.data);
      setShowPaymentLinkDialog(true);
      fetchInvoices();
      toast.success("Payment link generated!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate payment link");
    } finally {
      setGeneratingLink(false);
    }
  };

  const handleDownloadPDF = async (invoiceId, invoiceNumber) => {
    try {
      const response = await authAxios.get(`/operator/invoices/${invoiceId}/pdf`, {
        responseType: 'blob'
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Invoice_${invoiceNumber}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
      toast.success("PDF downloaded!");
    } catch (error) {
      toast.error("Failed to download PDF");
    }
  };

  const handleSendNotification = async (invoiceId, type = "invoice") => {
    try {
      await authAxios.post("/operator/send-notification", {
        invoice_id: invoiceId,
        notification_type: type
      });
      toast.success("Notification sent via WhatsApp!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send notification");
    }
  };

  const handleSendWhatsAppWeb = (invoice) => {
    const subscriber = subscribers.find(s => s.id === invoice.subscriber_id);
    if (!subscriber || !subscriber.whatsapp_number) {
      toast.error("Subscriber WhatsApp number not found");
      return;
    }
    
    let phone = subscriber.whatsapp_number.replace(/[^0-9]/g, '');
    if (phone.length === 10) phone = "91" + phone;
    
    const message = encodeURIComponent(
      `Hello ${subscriber.name},\n\n` +
      `Invoice ${invoice.invoice_number}\n` +
      `Amount: ₹${invoice.final_amount?.toLocaleString('en-IN')}\n` +
      `Due Date: ${invoice.due_date ? new Date(invoice.due_date).toLocaleDateString('en-IN') : 'N/A'}\n` +
      (invoice.payment_link ? `\nPay here: ${invoice.payment_link}\n` : '') +
      `\nThank you!`
    );
    
    window.open(`https://wa.me/${phone}?text=${message}`, '_blank');
    toast.success("WhatsApp Web opened");
  };

  const handlePlanSelect = (planId) => {
    const plan = plans.find(p => p.id === planId);
    if (plan) {
      setFormData(prev => ({
        ...prev,
        plan_id: planId,
        base_amount: plan.price
      }));
    }
  };

  const filteredInvoices = invoices.filter(inv => {
    const matchesSearch = 
      inv.invoice_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.subscriber_name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || inv.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status) => {
    const config = {
      pending: { class: "badge-pending", icon: Clock },
      paid: { class: "badge-paid", icon: CheckCircle },
      overdue: { class: "badge-overdue", icon: AlertTriangle },
      cancelled: { class: "badge-suspended", icon: null }
    };
    const { class: badgeClass, icon: Icon } = config[status] || config.pending;
    return (
      <span className={`${badgeClass} flex items-center gap-1`}>
        {Icon && <Icon className="w-3 h-3" />}
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <OperatorLayout title="Invoices">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const isReadOnly = dashboardStats?.is_read_only;

  return (
    <OperatorLayout title="Invoices" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between gap-4">
          <div className="flex gap-4 flex-1">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Search invoices..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
                data-testid="search-invoices"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="paid">Paid</SelectItem>
                <SelectItem value="overdue">Overdue</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button 
            onClick={() => { resetForm(); setShowDialog(true); }}
            disabled={isReadOnly}
            data-testid="create-invoice-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create Invoice
          </Button>
        </div>

        {/* Invoices Table */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Subscriber</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInvoices.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                      <FileText className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No invoices found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredInvoices.map((invoice) => (
                    <TableRow key={invoice.id} data-testid={`invoice-row-${invoice.id}`}>
                      <TableCell>
                        <span className="font-mono text-sm font-medium">{invoice.invoice_number}</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-medium block">{invoice.subscriber_name}</span>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          {invoice.line_items?.map((item, idx) => (
                            <span key={idx} className="text-xs bg-slate-100 px-1.5 py-0.5 rounded block w-fit">
                              {item.plan_name}
                            </span>
                          ))}
                          {(!invoice.line_items || invoice.line_items.length === 0) && (
                            <span className="text-xs text-slate-400">{invoice.plan_name}</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <span className="font-medium">₹{invoice.final_amount.toLocaleString('en-IN')}</span>
                          {invoice.tax_amount > 0 && (
                            <span className="text-xs text-slate-500 block">
                              Tax: ₹{invoice.tax_amount}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {new Date(invoice.due_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell>{getStatusBadge(invoice.status)}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" disabled={isReadOnly}>
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {invoice.status !== "paid" && !invoice.payment_link && (features?.payment_gateway || features?.custom_payment_gateway) && (
                              <DropdownMenuItem onClick={() => handleGeneratePaymentLink(invoice.id)}>
                                <Link2 className="w-4 h-4 mr-2 text-blue-600" />
                                Generate Payment Link
                              </DropdownMenuItem>
                            )}
                            {invoice.payment_link && (
                              <DropdownMenuItem onClick={() => {
                                setPaymentLinkData({ payment_link: invoice.payment_link });
                                setShowPaymentLinkDialog(true);
                              }}>
                                <QrCode className="w-4 h-4 mr-2 text-purple-600" />
                                View Payment Link/QR
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem onClick={() => handleDownloadPDF(invoice.id, invoice.invoice_number)}>
                              <Download className="w-4 h-4 mr-2 text-slate-600" />
                              Download PDF
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => window.open(`/invoice/${invoice.invoice_number || invoice.id}`, '_blank')}
                            >
                              <ExternalLink className="w-4 h-4 mr-2 text-blue-600" />
                              View Public Invoice
                            </DropdownMenuItem>
                            {features?.whatsapp_notifications && (
                              <DropdownMenuItem onClick={() => handleSendNotification(invoice.id, "invoice")}>
                                <Send className="w-4 h-4 mr-2 text-emerald-600" />
                                Send via WhatsApp API
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem onClick={() => handleSendWhatsAppWeb(invoice)} data-testid={`wa-web-${invoice.id}`}>
                              <MessageCircle className="w-4 h-4 mr-2 text-emerald-600" />
                              Send via WhatsApp Web
                            </DropdownMenuItem>
                            {invoice.status === "overdue" && features?.whatsapp_notifications && (
                              <DropdownMenuItem onClick={() => handleSendNotification(invoice.id, "reminder")}>
                                <Bell className="w-4 h-4 mr-2 text-amber-600" />
                                Send Reminder
                              </DropdownMenuItem>
                            )}
                            {invoice.status === "pending" && (
                              <DropdownMenuItem onClick={() => handleStatusUpdate(invoice.id, "paid")}>
                                <CheckCircle className="w-4 h-4 mr-2 text-emerald-600" />
                                Mark as Paid
                              </DropdownMenuItem>
                            )}
                            {invoice.status !== "overdue" && invoice.status !== "paid" && (
                              <DropdownMenuItem onClick={() => handleStatusUpdate(invoice.id, "overdue")}>
                                <AlertTriangle className="w-4 h-4 mr-2 text-red-600" />
                                Mark as Overdue
                              </DropdownMenuItem>
                            )}
                            {invoice.status !== "cancelled" && (
                              <DropdownMenuItem onClick={() => handleStatusUpdate(invoice.id, "cancelled")}>
                                Cancel Invoice
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Create Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create Invoice</DialogTitle>
              <DialogDescription>Generate a new invoice with multiple line items</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-b pb-4">
                <div className="space-y-2">
                  <Label>Subscriber *</Label>
                  <Select 
                    value={formData.subscriber_id} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, subscriber_id: value }))}
                  >
                    <SelectTrigger data-testid="invoice-subscriber-select">
                      <SelectValue placeholder="Select subscriber" />
                    </SelectTrigger>
                    <SelectContent>
                      {subscribers.map((sub) => (
                        <SelectItem key={sub.id} value={sub.id}>
                          {sub.name} - {sub.whatsapp_number}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Due Date *</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left font-normal">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {format(formData.due_date, "PPP")}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0 z-[100]" align="start">
                      <Calendar
                        mode="single"
                        selected={formData.due_date}
                        onSelect={(date) => date && setFormData(prev => ({ ...prev, due_date: date }))}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-slate-900">Line Items</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                    <Plus className="w-3 h-3 mr-1" /> Add Item
                  </Button>
                </div>

                <div className="space-y-4">
                  {formData.line_items.map((item, index) => (
                    <div key={index} className="p-4 bg-slate-50 rounded-lg relative border border-slate-100 space-y-4">
                      {formData.line_items.length > 1 && (
                        <Button 
                          type="button" 
                          variant="ghost" 
                          size="icon" 
                          className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-white border shadow-sm text-red-500"
                          onClick={() => removeLineItem(index)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label>Plan *</Label>
                          <Select 
                            value={item.plan_id || undefined} 
                            onValueChange={(val) => updateLineItem(index, "plan_id", val)}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select plan" />
                            </SelectTrigger>
                            <SelectContent>
                              {plans.map((plan) => (
                                <SelectItem key={plan.id} value={plan.id}>
                                  {plan.name} - ₹{plan.price}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label>Base Amount (₹) *</Label>
                          <Input
                            type="number"
                            value={item.base_amount}
                            onChange={(e) => updateLineItem(index, "base_amount", parseFloat(e.target.value) || 0)}
                            min="0"
                            required
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Discount (₹)</Label>
                          <Input
                            type="number"
                            value={item.discount}
                            onChange={(e) => updateLineItem(index, "discount", parseFloat(e.target.value) || 0)}
                            min="0"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Service Period Start *</Label>
                          <Popover>
                            <PopoverTrigger asChild>
                              <Button variant="outline" className="w-full justify-start text-left font-normal bg-white">
                                <CalendarIcon className="mr-2 h-4 w-4" />
                                {format(item.service_start_date, "PPP")}
                              </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0 z-[100]" align="start">
                              <Calendar
                                mode="single"
                                selected={item.service_start_date}
                                onSelect={(date) => date && updateLineItem(index, "service_start_date", date)}
                              />
                            </PopoverContent>
                          </Popover>
                        </div>

                        <div className="space-y-2">
                          <Label>Service Period End *</Label>
                          <Popover>
                            <PopoverTrigger asChild>
                              <Button variant="outline" className="w-full justify-start text-left font-normal bg-white">
                                <CalendarIcon className="mr-2 h-4 w-4" />
                                {format(item.service_end_date, "PPP")}
                              </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0 z-[100]" align="start">
                              <Calendar
                                mode="single"
                                selected={item.service_end_date}
                                onSelect={(date) => date && updateLineItem(index, "service_end_date", date)}
                              />
                            </PopoverContent>
                          </Popover>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-invoice-btn">
                  Create Invoice
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Payment Link Dialog */}
        <Dialog open={showPaymentLinkDialog} onOpenChange={setShowPaymentLinkDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <QrCode className="w-5 h-5 text-purple-600" />
                Payment Link Generated
              </DialogTitle>
              <DialogDescription>Share this link with your customer to collect payment</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {paymentLinkData?.qr_code && (
                <div className="flex justify-center">
                  <div className="p-4 bg-white border rounded-lg shadow-sm">
                    <img 
                      src={`data:image/png;base64,${paymentLinkData.qr_code}`} 
                      alt="Payment QR Code"
                      className="w-48 h-48"
                    />
                  </div>
                </div>
              )}
              
              <div className="space-y-2">
                <Label>Payment Link</Label>
                <div className="flex gap-2">
                  <Input 
                    value={paymentLinkData?.payment_link || ""} 
                    readOnly 
                    className="font-mono text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      navigator.clipboard.writeText(paymentLinkData?.payment_link || "");
                      toast.success("Link copied!");
                    }}
                  >
                    <Link2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              
              {paymentLinkData?.amount && (
                <div className="p-4 bg-emerald-50 rounded-lg text-center">
                  <p className="text-sm text-emerald-700">Amount to collect</p>
                  <p className="text-2xl font-bold text-emerald-800">
                    ₹{paymentLinkData.amount.toLocaleString('en-IN')}
                  </p>
                </div>
              )}
              
              <div className="flex gap-2 pt-4">
                <Button
                  className="flex-1"
                  onClick={() => {
                    window.open(paymentLinkData?.payment_link, '_blank');
                  }}
                >
                  Open Link
                </Button>
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowPaymentLinkDialog(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorInvoices;
