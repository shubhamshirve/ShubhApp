import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { toast, Toaster } from "sonner";
import {
  FileText, Download, CreditCard, CheckCircle2, Clock, XCircle,
  Building2, User, MapPin, Phone, Mail, Calendar, IndianRupee,
  AlertCircle, Loader2, Receipt, ArrowLeft
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paying, setPaying] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  const fetchInvoice = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/public/invoice/${id}`);
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
  }, [id]);

  useEffect(() => {
    fetchInvoice();
  }, [fetchInvoice]);

  // Download PDF
  const handleDownloadPdf = async () => {
    setPdfLoading(true);
    try {
      const res = await axios.get(`${API}/public/invoice/${id}/pdf`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `Invoice_${data?.invoice?.invoice_number || id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded successfully");
    } catch {
      toast.error("Failed to download PDF");
    } finally {
      setPdfLoading(false);
    }
  };

  // Load Razorpay checkout script
  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
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
      const orderRes = await axios.post(`${API}/public/invoice/${id}/create-payment-order`);
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
              `${API}/public/invoice/${id}/verify-payment?razorpay_order_id=${response.razorpay_order_id}&razorpay_payment_id=${response.razorpay_payment_id}&razorpay_signature=${response.razorpay_signature}`
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
  const showPayButton = isUnpaid && payment?.enabled;
  const showGst = invoice_settings?.show_gst !== false;
  const taxPercentage = plan?.tax_percentage || 0;
  const taxType = plan?.tax_type || "none";
  const subtotalAfterDiscount = invoice.base_amount - (invoice.discount || 0);

  // Check if overdue
  const isOverdue = isUnpaid && new Date(invoice.due_date) < new Date();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      <Toaster position="top-right" richColors closeButton />

      {/* Top Bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10">
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
              <button
                onClick={handlePayNow}
                disabled={paying}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
              >
                {paying ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                Pay Now
              </button>
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
                <h1 className="text-white text-2xl sm:text-3xl font-bold tracking-tight">INVOICE</h1>
                <p className="text-indigo-200 text-sm mt-1">#{invoice.invoice_number}</p>
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
                {operator.phone && (
                  <p className="text-sm text-slate-500 flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    {operator.phone}
                  </p>
                )}
                {operator.email && (
                  <p className="text-sm text-slate-500 flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    {operator.email}
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
                  {subscriber.phone && (
                    <p className="text-sm text-slate-500 flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-slate-400" />
                      {subscriber.phone}
                    </p>
                  )}
                  {subscriber.email && (
                    <p className="text-sm text-slate-500 flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                      {subscriber.email}
                    </p>
                  )}
                  {subscriber.address && (
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
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Service Period</p>
                <p className="text-sm font-medium text-slate-700 mt-0.5">
                  {formatDate(invoice.service_start_date)} — {formatDate(invoice.service_end_date)}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Plan</p>
                <p className="text-sm font-medium text-slate-700 mt-0.5">{invoice.plan_name}</p>
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
                <tr className="border-b border-slate-100">
                  <td className="py-4">
                    <p className="font-medium text-slate-800">{invoice.plan_name}</p>
                    <p className="text-sm text-slate-500 mt-0.5">
                      {plan?.validity ? `${plan.validity.charAt(0).toUpperCase() + plan.validity.slice(1)} subscription` : "Subscription"}
                      {" • "}
                      {formatDate(invoice.service_start_date)} to {formatDate(invoice.service_end_date)}
                    </p>
                  </td>
                  <td className="py-4 text-right font-medium text-slate-800">
                    {formatCurrency(invoice.base_amount)}
                  </td>
                </tr>
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
          {(operator.bank_account_name || operator.bank_account_number) && (
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
              <p className="text-xs text-slate-400 text-center">This is a computer-generated invoice and does not require a signature.</p>
            )}
          </div>
        </div>

        {/* Pay Now CTA (Large, sticky at bottom on mobile) */}
        {showPayButton && (
          <div className="mt-6 sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 p-4 shadow-lg z-20">
            <button
              onClick={handlePayNow}
              disabled={paying}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3.5 rounded-xl transition shadow-sm disabled:opacity-50"
            >
              {paying ? <Loader2 className="w-5 h-5 animate-spin" /> : <CreditCard className="w-5 h-5" />}
              Pay {formatCurrency(invoice.final_amount)}
            </button>
          </div>
        )}

        {/* Paid Confirmation */}
        {invoice.status === "paid" && (
          <div className="mt-6 bg-emerald-50 border border-emerald-200 rounded-xl p-4 sm:p-6 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
            <h3 className="text-lg font-semibold text-emerald-800">Payment Received</h3>
            <p className="text-sm text-emerald-600 mt-1">
              Thank you! This invoice has been paid.
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 pb-8 sm:pb-4">
          <p className="text-xs text-slate-400">
            Powered by <span className="font-medium text-slate-500">SaaS Billing Platform</span>
          </p>
        </div>
      </div>
    </div>
  );
}
