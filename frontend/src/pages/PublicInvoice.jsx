import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { toast, Toaster } from "sonner";
import { resolveMediaUrl } from "../lib/mediaUrl";
import { loadRazorpayScript } from "../lib/razorpay";
import {
  FileText, Download, CreditCard, CheckCircle2, Clock, XCircle,
  Building2, User, MapPin, Phone, Mail, Calendar, IndianRupee,
  AlertCircle, Loader2, Receipt, ArrowLeft, Smartphone
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL || ""}/api`;

// Format currency
const formatCurrency = (amount) => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount || 0);
};

// Format date
const formatDate = (dateStr) => {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

// Status badge component
const StatusBadge = ({ status }) => {
  const config = {
    pending: { bg: "bg-amber-50 border-amber-200", text: "text-amber-700", icon: Clock, label: "Unpaid" },
    paid: { bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700", icon: CheckCircle2, label: "Paid" },
    overdue: { bg: "bg-red-50 border-red-200", text: "text-red-700", icon: AlertCircle, label: "Overdue" },
    cancelled: { bg: "bg-slate-50 border-slate-200", text: "text-slate-500", icon: XCircle, label: "Cancelled" },
  };
  const c = config[status] || config.pending;
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border ${c.bg} ${c.text}`}>
      <Icon className="w-4 h-4" />
      {c.label}
    </span>
  );
};

export default function PublicInvoice() {
  const { invoiceRef } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paying, setPaying] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  const fetchInvoice = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/public/invoice/${invoiceRef}`);
      setData(res.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setError("Invoice not found. Please check the URL and try again.");
      } else {
        setError("Failed to load invoice. Please try again later.");
      }
    } finally {
      setLoading(false);
    }
  }, [invoiceRef]);

  useEffect(() => {
    fetchInvoice();
  }, [fetchInvoice]);

  useEffect(() => {
    if (data) {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("print") === "true") {
        setTimeout(() => window.print(), 1000);
      }
    }
  }, [data]);

  // Download PDF
  const handleDownloadPdf = () => {
    window.print();
  };

  // Handle Pay Now
  const handlePayNow = async () => {
    setPaying(true);
    try {
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        toast.error("Failed to load payment gateway. Please try again.");
        setPaying(false);
        return;
      }

      // Create order
      const orderRes = await axios.post(`${API}/public/invoice/${invoiceRef}/create-payment-order`);
      const orderData = orderRes.data;

      const options = {
        key: orderData.razorpay_key,
        amount: Math.round(orderData.amount * 100),
        currency: orderData.currency,
        name: orderData.operator_name,
        description: `Payment for Invoice #${orderData.invoice_number}`,
        order_id: orderData.razorpay_order_id,
        prefill: {
          name: orderData.subscriber_name,
          email: orderData.subscriber_email,
          contact: orderData.subscriber_phone,
        },
        theme: { color: "#4f46e5" },
        handler: async function (response) {
          try {
            await axios.post(
              `${API}/public/invoice/${invoiceRef}/verify-payment?razorpay_order_id=${response.razorpay_order_id}&razorpay_payment_id=${response.razorpay_payment_id}&razorpay_signature=${response.razorpay_signature}`
            );
            toast.success("Payment successful! Invoice has been marked as paid.");
            fetchInvoice(); // Refresh invoice data
          } catch {
            toast.error("Payment verification failed. Please contact support.");
          }
        },
        modal: {
          ondismiss: function () {
            setPaying(false);
          },
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", function (response) {
        toast.error(`Payment failed: ${response.error.description}`);
        setPaying(false);
      });
      rzp.open();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to initiate payment");
    } finally {
      setPaying(false);
    }
  };

  const handlePayViaUpi = () => {
    if (!data?.operator?.upi_id) {
      toast.error("Operator UPI ID not found.");
      return;
    }
    const upiLink = `upi://pay?pa=${data.operator.upi_id}&pn=${encodeURIComponent(data.operator.company_name || "Merchant")}&tr=${data.invoice.invoice_number}&am=${data.invoice.final_amount}&cu=INR`;
    window.location.href = upiLink;
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 flex items-center justify-center">
        <Toaster position="top-right" richColors closeButton />
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-500 text-sm">Loading invoice...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-red-50/30 flex items-center justify-center p-4">
        <Toaster position="top-right" richColors closeButton />
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-xl font-semibold text-slate-800 mb-2">Invoice Not Found</h2>
          <p className="text-slate-500">{error}</p>
        </div>
      </div>
    );
  }

  const { invoice, operator, subscriber, plan, invoice_settings, payment } = data;
  const isUnpaid = invoice.status === "pending" || invoice.status === "overdue";
  const acceptPaymentGateway = invoice_settings?.accept_payment_gateway !== false && payment?.enabled;
  const acceptUpi = invoice_settings?.accept_upi === true && operator?.upi_id;
  const showPayButton = isUnpaid && (acceptPaymentGateway || acceptUpi);
  const showGst = invoice_settings?.show_gst !== false;
  const visibleFields = invoice_settings?.visible_fields || {};
  const taxPercentage = plan?.tax_percentage || 0;
  const taxType = plan?.tax_type || "none";
  const subtotalAfterDiscount = invoice.base_amount - (invoice.discount || 0);

  // Check if overdue
  const isOverdue = isUnpaid && new Date(invoice.due_date) < new Date();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      <Toaster position="top-right" richColors closeButton />

      {/* Top Bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10 print:hidden">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Receipt className="w-5 h-5 text-indigo-600" />
            <span className="font-semibold text-slate-800 text-sm sm:text-base">Invoice #{invoice.invoice_number}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadPdf}
              disabled={pdfLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition disabled:opacity-50"
            >
              {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              <span className="hidden sm:inline">Download PDF</span>
            </button>
            {showPayButton && (
              <div className="flex gap-2">
                {acceptUpi && (
                  <button
                    onClick={handlePayViaUpi}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-semibold text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition shadow-sm"
                  >
                    <Smartphone className="w-4 h-4" />
                    <span className="hidden sm:inline">Pay via UPI App</span>
                    <span className="sm:hidden">UPI</span>
                  </button>
                )}
                {acceptPaymentGateway && (
                  <button
                    onClick={handlePayNow}
                    disabled={paying}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
                  >
                    {paying ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                    <span className="hidden sm:inline">Pay Online</span>
                    <span className="sm:hidden">Pay</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* Invoice Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">

          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 px-6 sm:px-8 py-6 sm:py-8">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  {visibleFields.show_logo !== false && operator.logo_url && (
                    <img
                      src={resolveMediaUrl(operator.logo_url)}
                      alt={`${invoice_settings?.company_name || operator.company_name} logo`}
                      className="h-10 w-auto rounded bg-white/95 p-1"
                    />
                  )}
                  <div>
                    <h1 className="text-white text-2xl sm:text-3xl font-bold tracking-tight">INVOICE</h1>
                    <p className="text-indigo-200 text-sm mt-1">#{invoice.invoice_number}</p>
                  </div>
                </div>
              </div>
              <div className="text-left sm:text-right">
                <StatusBadge status={isOverdue ? "overdue" : invoice.status} />
                <p className="text-indigo-200 text-xs mt-2">
                  Issued: {formatDate(invoice.created_at)}
                </p>
              </div>
            </div>
          </div>

          {/* Party Details */}
          <div className="px-6 sm:px-8 py-6 grid grid-cols-1 sm:grid-cols-2 gap-6 border-b border-slate-100">
            {/* From (Operator) */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">From</p>
              <div className="space-y-1">
                <p className="font-semibold text-slate-800 text-lg flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-indigo-500" />
                  {invoice_settings?.company_name || operator.company_name}
                </p>
                {operator.phone && visibleFields.show_company_phone !== false && (
                  <p className="text-sm text-slate-500 flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    {operator.phone}
                  </p>
                )}
                {operator.email && visibleFields.show_company_email !== false && (
                  <p className="text-sm text-slate-500 flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    {operator.email}
                  </p>
                )}
                {operator.company_address && visibleFields.show_company_address !== false && (
                  <p className="text-sm text-slate-500 flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    {operator.company_address}
                  </p>
                )}
                {showGst && operator.gst_number && (
                  <p className="text-sm text-slate-600 font-medium mt-1">
                    GSTIN: {operator.gst_number}
                  </p>
                )}
              </div>
            </div>

            {/* To (Subscriber) */}
            {subscriber && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Bill To</p>
                <div className="space-y-1">
                  <p className="font-semibold text-slate-800 text-lg flex items-center gap-2">
                    <User className="w-4 h-4 text-indigo-500" />
                    {subscriber.name}
                  </p>
                  {subscriber.phone && visibleFields.show_subscriber_phone !== false && (
                    <p className="text-sm text-slate-500 flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-slate-400" />
                      {subscriber.phone}
                    </p>
                  )}
                  {subscriber.email && visibleFields.show_subscriber_email !== false && (
                    <p className="text-sm text-slate-500 flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                      {subscriber.email}
                    </p>
                  )}
                  {subscriber.address && visibleFields.show_subscriber_address !== false && (
                    <p className="text-sm text-slate-500 flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      {subscriber.address}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Invoice Details Row */}
          <div className="px-6 sm:px-8 py-4 bg-slate-50/50 border-b border-slate-100">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Invoice Date</p>
                <p className="text-sm font-medium text-slate-700 mt-0.5">{formatDate(invoice.created_at)}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Due Date</p>
                <p className={`text-sm font-medium mt-0.5 ${isOverdue ? "text-red-600" : "text-slate-700"}`}>
                  {formatDate(invoice.due_date)}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Status</p>
                <p className="text-sm font-medium text-slate-700 mt-0.5 capitalize">{invoice.status}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Items</p>
                <p className="text-sm font-medium text-slate-700 mt-0.5">
                  {(invoice.line_items?.length || 1)} {invoice.line_items?.length === 1 ? 'Plan' : 'Plans'}
                </p>
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <div className="px-6 sm:px-8 py-6">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left pb-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Description</th>
                  <th className="text-right pb-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Amount</th>
                </tr>
              </thead>
              <tbody>
                {invoice.line_items && invoice.line_items.length > 0 ? (
                  invoice.line_items.map((item, idx) => (
                    <tr key={idx} className="border-b border-slate-100 last:border-0">
                      <td className="py-4">
                        <p className="font-medium text-slate-800">{item.plan_name}</p>
                        <p className="text-sm text-slate-500 mt-0.5">
                          {formatDate(item.service_start_date)} to {formatDate(item.service_end_date)}
                        </p>
                      </td>
                      <td className="py-4 text-right font-medium text-slate-800">
                        {formatCurrency(item.base_amount)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr className="border-b border-slate-100 last:border-0">
                    <td className="py-4">
                      <p className="font-medium text-slate-800">{invoice.plan_name}</p>
                      <p className="text-sm text-slate-500 mt-0.5">
                        {formatDate(invoice.service_start_date)} to {formatDate(invoice.service_end_date)}
                      </p>
                    </td>
                    <td className="py-4 text-right font-medium text-slate-800">
                      {formatCurrency(invoice.base_amount)}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Totals Section */}
          <div className="px-6 sm:px-8 pb-6">
            <div className="flex justify-end">
              <div className="w-full sm:w-80">
                <div className="space-y-2 text-sm">
                  {/* Subtotal */}
                  <div className="flex justify-between text-slate-600">
                    <span>Subtotal</span>
                    <span>{formatCurrency(invoice.base_amount)}</span>
                  </div>

                  {/* Discount */}
                  {invoice.discount > 0 && (
                    <div className="flex justify-between text-emerald-600">
                      <span>Discount</span>
                      <span>- {formatCurrency(invoice.discount)}</span>
                    </div>
                  )}

                  {/* Subtotal after discount */}
                  {invoice.discount > 0 && (
                    <div className="flex justify-between text-slate-600 pt-1 border-t border-dashed border-slate-200">
                      <span>Net Amount</span>
                      <span>{formatCurrency(subtotalAfterDiscount)}</span>
                    </div>
                  )}

                  {/* Tax / GST */}
                  {showGst && invoice.tax_amount > 0 && (
                    <>
                      {taxType === "exclusive" ? (
                        <>
                          <div className="flex justify-between text-slate-600">
                            <span>
                              CGST @ {taxPercentage / 2}%
                            </span>
                            <span>{formatCurrency(invoice.tax_amount / 2)}</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>
                              SGST @ {taxPercentage / 2}%
                            </span>
                            <span>{formatCurrency(invoice.tax_amount / 2)}</span>
                          </div>
                        </>
                      ) : taxType === "inclusive" ? (
                        <div className="flex justify-between text-slate-500 italic">
                          <span>
                            Includes GST @ {taxPercentage}%
                          </span>
                          <span>{formatCurrency(invoice.tax_amount)}</span>
                        </div>
                      ) : (
                        <div className="flex justify-between text-slate-600">
                          <span>GST @ {taxPercentage}%</span>
                          <span>{formatCurrency(invoice.tax_amount)}</span>
                        </div>
                      )}
                    </>
                  )}

                  {/* Total */}
                  <div className="flex justify-between items-center pt-3 mt-2 border-t-2 border-slate-800">
                    <span className="text-base font-bold text-slate-800">Total Amount</span>
                    <span className="text-xl font-bold text-slate-800">{formatCurrency(invoice.final_amount)}</span>
                  </div>

                  {/* Amount in words - for Indian format */}
                  {invoice.final_amount > 0 && (
                    <div className="text-xs text-slate-400 text-right italic">
                      {taxType === "inclusive" && invoice.tax_amount > 0
                        ? "(Inclusive of GST)"
                        : taxType === "exclusive" && invoice.tax_amount > 0
                        ? "(Exclusive of GST added above)"
                        : ""}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Bank Details (if available) */}
          {visibleFields.show_bank_details !== false && (operator.bank_account_name || operator.bank_account_number) && (
            <div className="px-6 sm:px-8 py-5 bg-slate-50 border-t border-slate-200">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Bank Details for Payment</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                {operator.bank_name && (
                  <div>
                    <p className="text-slate-400 text-xs">Bank</p>
                    <p className="text-slate-700 font-medium">{operator.bank_name}</p>
                  </div>
                )}
                {operator.bank_account_name && (
                  <div>
                    <p className="text-slate-400 text-xs">Account Name</p>
                    <p className="text-slate-700 font-medium">{operator.bank_account_name}</p>
                  </div>
                )}
                {operator.bank_account_number && (
                  <div>
                    <p className="text-slate-400 text-xs">Account No.</p>
                    <p className="text-slate-700 font-medium">{operator.bank_account_number}</p>
                  </div>
                )}
                {operator.bank_ifsc && (
                  <div>
                    <p className="text-slate-400 text-xs">IFSC</p>
                    <p className="text-slate-700 font-medium">{operator.bank_ifsc}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Footer / Terms */}
          <div className="px-6 sm:px-8 py-5 border-t border-slate-200">
            {invoice_settings?.terms_conditions && (
              <div className="mb-3">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Terms & Conditions</p>
                <p className="text-xs text-slate-500 whitespace-pre-line">{invoice_settings.terms_conditions}</p>
              </div>
            )}
            {invoice_settings?.invoice_footer && (
              <p className="text-xs text-slate-400 text-center">{invoice_settings.invoice_footer}</p>
            )}
            {!invoice_settings?.invoice_footer && (
              <p className="text-xs text-slate-400 text-center">
                This is a computer-generated invoice and does not require a signature. Payment status: {invoice.status}.
              </p>
            )}
          </div>
        </div>

        {/* Pay Now CTA (Large, sticky at bottom on mobile) */}
        {showPayButton && (
          <div className="mt-6 sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 p-4 shadow-lg z-20 print:hidden flex gap-2">
            {acceptUpi && (
              <button
                onClick={handlePayViaUpi}
                className="flex-1 flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 text-white font-semibold py-3.5 rounded-xl transition shadow-sm"
              >
                <Smartphone className="w-5 h-5" />
                UPI App
              </button>
            )}
            {acceptPaymentGateway && (
              <button
                onClick={handlePayNow}
                disabled={paying}
                className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3.5 rounded-xl transition shadow-sm disabled:opacity-50"
              >
                {paying ? <Loader2 className="w-5 h-5 animate-spin" /> : <CreditCard className="w-5 h-5" />}
                Pay Online
              </button>
            )}
          </div>
        )}

        {/* Paid Confirmation */}
        {invoice.status === "paid" && (
          <div className="mt-8 bg-emerald-50 border border-emerald-200 rounded-2xl p-6 sm:p-8 text-center shadow-sm">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-100 mb-4">
              <CheckCircle2 className="w-8 h-8 text-emerald-600" />
            </div>
            <h3 className="text-2xl font-bold text-emerald-800 mb-2">Payment Received</h3>
            <p className="text-emerald-600 font-medium mb-6">
              Thank you! This invoice has been successfully paid.
            </p>
            {(invoice.payment_id || invoice.paid_at) && (
              <div className="max-w-md mx-auto bg-white rounded-xl shadow-sm border border-emerald-100 overflow-hidden text-left">
                <div className="px-6 py-3 bg-emerald-600 text-white text-sm font-semibold tracking-wider uppercase">
                  Payment Details
                </div>
                <div className="p-6 space-y-4">
                  {invoice.payment_id && (
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Transaction Ref</p>
                      <p className="font-mono text-slate-800 bg-slate-50 px-3 py-2 rounded-md text-sm border">{invoice.payment_id}</p>
                    </div>
                  )}
                  {invoice.paid_at && (
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Date Paid</p>
                      <p className="text-slate-800 font-medium">{formatDate(invoice.paid_at)}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 pb-8 sm:pb-4">
          <p className="text-xs text-slate-400">
            Powered by <span className="font-medium text-slate-500">E-Bill - Billing solution for cable operators and ISPs</span>
          </p>
        </div>
      </div>
    </div>
  );
}
