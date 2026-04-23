import { useState, useEffect, useRef, useMemo } from "react";
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
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../../components/ui/command";
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../components/ui/popover";
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
  MessageSquare,
  ExternalLink,
  Pencil,
  Trash2,
  Upload,
  FileSpreadsheet,
  AlertCircle,
  XCircle,
  Loader2,
  Smartphone,
  ChevronsUpDown,
  Check,
  ChevronDown,
  ChevronRight,
  Users,
  LayoutList,
} from "lucide-react";

const SearchableSubscriberSelect = ({ value, onSelect, authAxios }) => {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedSubscriber, setSelectedSubscriber] = useState(null);

  // Debounced search
  useEffect(() => {
    if (!open) return;
    
    const timeoutId = setTimeout(() => {
      searchSubscribers(searchQuery);
    }, 300);
    
    return () => clearTimeout(timeoutId);
  }, [searchQuery, open]);

  // Load selected subscriber details when value changes
  useEffect(() => {
    if (value && !selectedSubscriber) {
      authAxios.get(`/operator/subscribers/search?q=&limit=100`)
        .then(res => {
          const found = res.data.find(s => s.id === value);
          if (found) setSelectedSubscriber(found);
        })
        .catch(err => console.error("Failed to load subscriber", err));
    }
  }, [value]);

  const searchSubscribers = async (query) => {
    setSearching(true);
    try {
      const response = await authAxios.get(`/operator/subscribers/search?q=${encodeURIComponent(query)}&limit=50`);
      setSearchResults(response.data);
    } catch (error) {
      console.error("Failed to search subscribers", error);
      toast.error("Failed to search subscribers");
    } finally {
      setSearching(false);
    }
  };

  const handleSelect = (subscriber) => {
    setSelectedSubscriber(subscriber);
    onSelect(subscriber.id);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between bg-white"
          data-testid="invoice-subscriber-select"
        >
          {selectedSubscriber ? (
            <span className="truncate">{selectedSubscriber.name} - {selectedSubscriber.whatsapp_number}</span>
          ) : (
            <span className="text-muted-foreground">Select subscriber...</span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0 z-[100]" align="start">
        <Command shouldFilter={false}>
          <CommandInput 
            placeholder="Search by name, phone, email..." 
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList>
            {searching ? (
              <div className="py-6 text-center text-sm">
                <Loader2 className="h-4 w-4 animate-spin mx-auto" />
              </div>
            ) : searchResults.length === 0 ? (
              <CommandEmpty>No subscribers found.</CommandEmpty>
            ) : (
              <CommandGroup>
                {searchResults.map((subscriber) => (
                  <CommandItem
                    key={subscriber.id}
                    value={subscriber.id}
                    onSelect={() => handleSelect(subscriber)}
                    className="cursor-pointer"
                  >
                    <Check
                      className={`mr-2 h-4 w-4 ${
                        value === subscriber.id ? "opacity-100" : "opacity-0"
                      }`}
                    />
                    <div className="flex flex-col">
                      <span className="font-medium">{subscriber.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {subscriber.whatsapp_number}
                        {subscriber.email && ` • ${subscriber.email}`}
                      </span>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
};

const PAYMENT_MODE_OPTIONS = [
  { value: "cash", label: "Cash" },
  { value: "own_upi", label: "Own UPI" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "cheque", label: "Cheque" },
];

const OperatorInvoices = () => {
  const { authAxios, features } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [subscribers, setSubscribers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [viewMode, setViewMode] = useState("flat"); // "flat" | "grouped"
  const [expandedSubscribers, setExpandedSubscribers] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 20;
  const [showDialog, setShowDialog] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState(null);
  const [savingInvoice, setSavingInvoice] = useState(false);
  const [showPaymentLinkDialog, setShowPaymentLinkDialog] = useState(false);
  const [paymentLinkData, setPaymentLinkData] = useState(null);
  const [generatingLink, setGeneratingLink] = useState(false);
  const [showPaymentConfirmDialog, setShowPaymentConfirmDialog] = useState(false);
  const [paymentTargetInvoice, setPaymentTargetInvoice] = useState(null);
  const [paymentForm, setPaymentForm] = useState({
    payment_mode: "cash",
    payment_date: new Date(),
  });
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [sendingWebJS, setSendingWebJS] = useState(null); // invoice id being sent via WebJS
  const [invoiceSettings, setInvoiceSettings] = useState(null);
  const [gatewayConfigured, setGatewayConfigured] = useState(false);
  const fileInputRef = useRef(null);
  const [formData, setFormData] = useState({
    subscriber_id: "",
    line_items: [{
      plan_id: "",
      item_type: "plan", // "plan" or "custom"
      description: "",
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
    fetchInvoiceSettings();
  }, []);

  const fetchInvoiceSettings = async () => {
    try {
      const [settingsRes, gatewayRes] = await Promise.all([
        authAxios.get("/operator/invoice-settings").catch(() => ({ data: {} })),
        authAxios.get("/operator/payment-gateway").catch(() => ({ data: { configured: false } })),
      ]);
      setInvoiceSettings(settingsRes.data);
      setGatewayConfigured(
        gatewayRes.data?.configured === true || gatewayRes.data?.is_active === true
      );
    } catch (err) {
      console.warn("Non-critical settings load failed:", err);
      // non-critical, ignore
    }
  };

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
      if (item.item_type === "custom") {
        if (!item.description?.trim()) { toast.error("Please enter a description for custom items"); return; }
      } else {
        if (!item.plan_id) { toast.error("Please select a plan for all items"); return; }
      }
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
    
    setSavingInvoice(true);
    try {
      const payload = {
        subscriber_id: formData.subscriber_id,
        due_date: formData.due_date.toISOString(),
        line_items: formData.line_items.map(item => ({
          plan_id: item.item_type === "custom" ? null : item.plan_id,
          is_custom: item.item_type === "custom",
          description: item.item_type === "custom" ? item.description : null,
          base_amount: item.base_amount,
          discount: item.discount,
          service_start_date: item.service_start_date.toISOString(),
          service_end_date: item.service_end_date.toISOString()
        }))
      };
      
      if (editingInvoice) {
        await authAxios.put(`/operator/invoices/${editingInvoice.id}`, payload);
        toast.success("Invoice updated successfully");
      } else {
        await authAxios.post("/operator/invoices", payload);
        toast.success("Invoice created successfully");
      }
      setShowDialog(false);
      resetForm();
      fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${editingInvoice ? "update" : "create"} invoice`);
    } finally {
      setSavingInvoice(false);
    }
  };

  const handleDownloadSample = async () => {
    try {
      const res = await authAxios.get("/operator/invoices/sample-csv", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "invoices_sample.csv";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download sample");
    }
  };

  const pollJobStatusInBackground = async (jobId) => {
    const maxAttempts = 300;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const res = await authAxios.get(`/operator/jobs/${jobId}`);
        const { status, result, error } = res.data;

        if (status === "completed") {
          await fetchInvoices();
          await fetchDashboard();
          return;
        } else if (status === "failed") {
          return;
        }
        await new Promise(resolve => setTimeout(resolve, 3000));
      } catch (e) {
        return;
      }
    }
  };

  const handleBulkUpload = async () => {
    if (!bulkFile) return;
    setBulkUploading(true);
    setBulkResult(null);
    try {
      const form = new FormData();
      form.append("file", bulkFile);
      const res = await authAxios.post("/operator/invoices/bulk-upload", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      const { job_id } = res.data;
      toast.success("File uploaded successfully. Processing in background...");
      // Close dialog immediately
      setShowBulkDialog(false);
      setBulkUploading(false);
      // Start background polling without awaiting
      pollJobStatusInBackground(job_id);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Upload failed");
      setBulkUploading(false);
    }
  };

  const addLineItem = () => {
    setFormData(prev => ({
      ...prev,
      line_items: [...prev.line_items, {
        plan_id: "",
        item_type: "plan",
        description: "",
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
    
    // When switching item type, reset plan_id or description
    if (field === "item_type") {
      if (value === "custom") {
        updatedItems[index].plan_id = "";
      } else {
        updatedItems[index].description = "";
      }
    }
    
    setFormData(prev => ({ ...prev, line_items: updatedItems }));
  };

  const resetForm = () => {
    setEditingInvoice(null);
    setFormData({
      subscriber_id: "",
      line_items: [{
        plan_id: "",
        item_type: "plan",
        description: "",
        base_amount: 0,
        discount: 0,
        service_start_date: new Date(),
        service_end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
      }],
      due_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000)
    });
  };

  const handleEditInvoice = (invoice) => {
    setEditingInvoice(invoice);
    setFormData({
      subscriber_id: invoice.subscriber_id,
      line_items: (invoice.line_items || []).map((item) => ({
        plan_id: item.plan_id || "",
        item_type: item.is_custom ? "custom" : "plan",
        description: item.description || item.plan_name || "",
        base_amount: item.base_amount ?? 0,
        discount: item.discount ?? 0,
        service_start_date: new Date(item.service_start_date),
        service_end_date: new Date(item.service_end_date),
      })),
      due_date: new Date(invoice.due_date),
    });
    setShowDialog(true);
  };

  const handleStatusUpdate = async (invoiceId, status, extra = {}) => {
    try {
      await authAxios.put(`/operator/invoices/${invoiceId}/status`, { status, ...extra });
      toast.success(`Invoice marked as ${status}`);
      fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update status");
    }
  };

  const openPaymentConfirmDialog = (invoice) => {
    setPaymentTargetInvoice(invoice);
    setPaymentForm({
      payment_mode: "cash",
      payment_date: new Date(),
    });
    setShowPaymentConfirmDialog(true);
  };

  const submitPaymentConfirmation = async () => {
    if (!paymentTargetInvoice) return;
    await handleStatusUpdate(paymentTargetInvoice.id, "paid", {
      payment_mode: paymentForm.payment_mode,
      payment_date: paymentForm.payment_date.toISOString(),
    });
    setShowPaymentConfirmDialog(false);
    setPaymentTargetInvoice(null);
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
      const inv = invoices.find(i => i.id === invoiceId);
      if (!inv) return;
      window.open(`/invoice/${inv.invoice_number}?print=true`, "_blank");
    } catch (error) {
      toast.error("Failed to open invoice");
    }
  };

  const handleSendNotification = async (invoiceId, type = "invoice") => {
    try {
      const res = await authAxios.post("/operator/send-notification", {
        invoice_id: invoiceId,
        notification_type: type
      });
      const { message_id, recipient_wa_id, wallet_balance } = res.data || {};
      const detail = recipient_wa_id
        ? `Sent to +${recipient_wa_id}${message_id ? ` (ID: ${message_id.slice(-8)})` : ""}`
        : "WhatsApp message sent!";
      
      // Show wallet balance in success message
      const balanceMsg = wallet_balance !== undefined ? ` | Wallet: ₹${wallet_balance.toFixed(2)}` : "";
      toast.success(detail + balanceMsg, { duration: 6000 });
      
      // Refresh dashboard to update wallet balance
      fetchDashboard();
    } catch (error) {
      // Handle insufficient balance error (402)
      if (error.response?.status === 402) {
        toast.error(
          error.response?.data?.detail || "Insufficient wallet balance. Please top up to send WhatsApp messages.",
          { duration: 8000 }
        );
      } else {
        toast.error(error.response?.data?.detail || "Failed to send notification");
      }
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

  const handleSendViaWebJS = async (invoice) => {
    setSendingWebJS(invoice.id);
    try {
      const res = await authAxios.post(`/operator/whatsapp-webjs/send-invoice/${invoice.id}`);
      if (res.data.success) {
        toast.success("Invoice sent via WhatsApp successfully!");
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Failed to send via WhatsApp";
      if (errorMsg.includes("not connected")) {
        toast.error("WhatsApp is not connected. Please connect from Settings → WhatsApp Web first.");
      } else {
        toast.error(errorMsg);
      }
    } finally {
      setSendingWebJS(null);
    }
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

  // Infer validity label from a line item's service window (in days)
  const getValidityLabel = (item) => {
    if (!item?.service_start_date || !item?.service_end_date) return null;
    const days = Math.round(
      (new Date(item.service_end_date) - new Date(item.service_start_date)) / (1000 * 60 * 60 * 24)
    );
    if (days <= 0) return null;
    if (days <= 45) return "Monthly";
    if (days <= 120) return "Quarterly";
    if (days <= 220) return "Half-Yearly";
    return "Yearly";
  };

  // Group filteredInvoices by subscriber_id for the consolidated view
  const groupedBySubscriber = useMemo(() => {
    const map = new Map();
    for (const inv of filteredInvoices) {
      const key = inv.subscriber_id || inv.subscriber_name || inv.id;
      if (!map.has(key)) {
        map.set(key, {
          subscriber_id: inv.subscriber_id,
          subscriber_name: inv.subscriber_name || "—",
          invoices: [],
          total_due: 0,
          total_paid: 0,
          validity_counts: {},
          status_counts: { pending: 0, paid: 0, overdue: 0, cancelled: 0 },
        });
      }
      const g = map.get(key);
      g.invoices.push(inv);
      if (inv.status === "paid") g.total_paid += inv.final_amount || 0;
      else if (inv.status !== "cancelled") g.total_due += inv.final_amount || 0;
      g.status_counts[inv.status] = (g.status_counts[inv.status] || 0) + 1;
      (inv.line_items || []).forEach((li) => {
        const v = getValidityLabel(li) || (li.is_custom ? "Custom" : "Other");
        g.validity_counts[v] = (g.validity_counts[v] || 0) + 1;
      });
    }
    // Sort by outstanding amount desc, then by name
    return Array.from(map.values()).sort((a, b) => {
      if (b.total_due !== a.total_due) return b.total_due - a.total_due;
      return a.subscriber_name.localeCompare(b.subscriber_name);
    });
  }, [filteredInvoices]);

  const toggleSubscriberExpanded = (key) => {
    setExpandedSubscribers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const expandAllGroups = () => {
    const all = {};
    groupedBySubscriber.forEach((g) => {
      all[g.subscriber_id || g.subscriber_name] = true;
    });
    setExpandedSubscribers(all);
  };

  const collapseAllGroups = () => setExpandedSubscribers({});

  // Reset to page 1 whenever filters/view change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, statusFilter, viewMode]);

  const isReadOnly = dashboardStats?.is_read_only;

  const renderInvoiceRow = (invoice, { hideSubscriber = false } = {}) => (
    <TableRow key={invoice.id} data-testid={`invoice-row-${invoice.id}`}>
      <TableCell>
        <span className="font-mono text-sm font-medium">{invoice.invoice_number}</span>
      </TableCell>
      {!hideSubscriber && (
        <TableCell>
          <span className="font-medium block">{invoice.subscriber_name}</span>
        </TableCell>
      )}
      <TableCell>
        <div className="space-y-1">
          {invoice.line_items?.map((item, idx) => {
            const validity = getValidityLabel(item);
            return (
              <span
                key={idx}
                className={`text-xs px-1.5 py-0.5 rounded block w-fit ${
                  item.is_custom ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-700"
                }`}
              >
                {item.is_custom ? (item.description || item.plan_name) : item.plan_name}
                {item.is_custom && <span className="ml-1 opacity-60">(custom)</span>}
                {!item.is_custom && validity && (
                  <span className="ml-2 opacity-70 border-l border-slate-300 pl-2">{validity}</span>
                )}
              </span>
            );
          })}
          {(!invoice.line_items || invoice.line_items.length === 0) && (
            <span className="text-xs text-slate-400">{invoice.plan_name}</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div>
          <span className="font-medium">₹{invoice.final_amount.toLocaleString("en-IN")}</span>
          {invoice.tax_amount > 0 && (
            <span className="text-xs text-slate-500 block">Tax: ₹{invoice.tax_amount}</span>
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
            {invoice.status === "pending" && !invoice.payment_link && features?.payment_gateway && gatewayConfigured && invoiceSettings?.accept_payment_gateway && (
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
            {invoice.status === "pending" && (
              <DropdownMenuItem onClick={() => handleEditInvoice(invoice)}>
                <Pencil className="w-4 h-4 mr-2 text-blue-600" />
                Edit Invoice
              </DropdownMenuItem>
            )}
            <DropdownMenuItem
              onClick={() => window.open(`/invoice/${invoice.invoice_number || invoice.id}`, "_blank")}
            >
              <ExternalLink className="w-4 h-4 mr-2 text-blue-600" />
              View Public Invoice
            </DropdownMenuItem>
            {features?.whatsapp_notifications && (
              <DropdownMenuItem onClick={() => handleSendNotification(invoice.id, "invoice")}>
                <Send className="w-4 h-4 mr-2 text-emerald-600" />
                Send via WhatsApp API (Rs 0.5)
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => handleSendWhatsAppWeb(invoice)}>
              <MessageSquare className="w-4 h-4 mr-2 text-green-600" />
              Send via WhatsApp Web
            </DropdownMenuItem>
            {invoice.status === "overdue" && features?.whatsapp_notifications && (
              <DropdownMenuItem onClick={() => handleSendNotification(invoice.id, "reminder")}>
                <Bell className="w-4 h-4 mr-2 text-amber-600" />
                Send Reminder
              </DropdownMenuItem>
            )}
            {invoice.status === "pending" && (
              <DropdownMenuItem onClick={() => openPaymentConfirmDialog(invoice)}>
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
            {invoice.status !== "cancelled" && invoice.status !== "paid" && (
              <DropdownMenuItem onClick={() => handleStatusUpdate(invoice.id, "cancelled")}>
                Cancel Invoice
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );


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

  return (
    <OperatorLayout title="Invoices" isReadOnly={isReadOnly}>
      <div className="space-y-8 animate-fade-in">
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
            <div className="inline-flex rounded-md border border-slate-200 overflow-hidden" data-testid="view-mode-toggle">
              <button
                type="button"
                onClick={() => setViewMode("flat")}
                className={`px-3 py-2 text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  viewMode === "flat" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
                data-testid="view-mode-flat"
              >
                <LayoutList className="w-3.5 h-3.5" />
                Flat
              </button>
              <button
                type="button"
                onClick={() => setViewMode("grouped")}
                className={`px-3 py-2 text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  viewMode === "grouped" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
                data-testid="view-mode-grouped"
              >
                <Users className="w-3.5 h-3.5" />
                By Subscriber
              </button>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => { setShowBulkDialog(true); setBulkFile(null); setBulkResult(null); }}
              disabled={isReadOnly}
            >
              <Upload className="w-4 h-4 mr-2" />
              Bulk Upload
            </Button>
            <Button 
              onClick={() => { resetForm(); setShowDialog(true); }}
              disabled={isReadOnly}
              data-testid="create-invoice-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Invoice
            </Button>
          </div>
        </div>

        {/* Invoices Table / Grouped View */}
        {(() => {
          const sourceList = viewMode === "flat" ? filteredInvoices : groupedBySubscriber;
          const totalItems = sourceList.length;
          const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
          const safePage = Math.min(currentPage, totalPages);
          const startIdx = (safePage - 1) * PAGE_SIZE;
          const endIdx = startIdx + PAGE_SIZE;
          const pagedFlat = viewMode === "flat" ? filteredInvoices.slice(startIdx, endIdx) : [];
          const pagedGroups = viewMode === "grouped" ? groupedBySubscriber.slice(startIdx, endIdx) : [];

          const PaginationBar = () => {
            if (totalItems <= PAGE_SIZE) return null;
            const goTo = (p) => setCurrentPage(Math.min(Math.max(1, p), totalPages));
            const rangeStart = startIdx + 1;
            const rangeEnd = Math.min(endIdx, totalItems);
            const unit = viewMode === "flat" ? "invoices" : "subscribers";
            return (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2" data-testid="invoices-pagination">
                <p className="text-xs text-slate-500">
                  Showing <span className="font-medium text-slate-700">{rangeStart}–{rangeEnd}</span> of{" "}
                  <span className="font-medium text-slate-700">{totalItems}</span> {unit}
                </p>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goTo(safePage - 1)}
                    disabled={safePage <= 1}
                    data-testid="pagination-prev"
                  >
                    Previous
                  </Button>
                  <span className="text-xs px-3 text-slate-600" data-testid="pagination-info">
                    Page {safePage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goTo(safePage + 1)}
                    disabled={safePage >= totalPages}
                    data-testid="pagination-next"
                  >
                    Next
                  </Button>
                </div>
              </div>
            );
          };

          return viewMode === "flat" ? (
            <div className="space-y-3">
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
                      {pagedFlat.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                            <FileText className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                            No invoices found
                          </TableCell>
                        </TableRow>
                      ) : (
                        pagedFlat.map((invoice) => renderInvoiceRow(invoice))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
              <PaginationBar />
            </div>
          ) : (
            <div className="space-y-3" data-testid="grouped-invoices-view">
              <div className="flex items-center justify-between px-1">
                <p className="text-sm text-slate-500">
                  {groupedBySubscriber.length} {groupedBySubscriber.length === 1 ? "subscriber" : "subscribers"} · {filteredInvoices.length} invoices
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={expandAllGroups}
                    className="text-xs text-slate-600 hover:text-slate-900 underline underline-offset-2"
                    data-testid="expand-all-groups"
                  >
                    Expand all
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    type="button"
                    onClick={collapseAllGroups}
                    className="text-xs text-slate-600 hover:text-slate-900 underline underline-offset-2"
                    data-testid="collapse-all-groups"
                  >
                    Collapse all
                  </button>
                </div>
              </div>

              {pagedGroups.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center text-slate-500">
                    <FileText className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    No invoices found
                  </CardContent>
                </Card>
              ) : (
                pagedGroups.map((group) => {
                  const key = group.subscriber_id || group.subscriber_name;
                  const isOpen = !!expandedSubscribers[key];
                  const validityPills = Object.entries(group.validity_counts).sort(
                    (a, b) => b[1] - a[1]
                  );
                  return (
                    <Card key={key} data-testid={`group-card-${key}`}>
                      <button
                        type="button"
                        onClick={() => toggleSubscriberExpanded(key)}
                        className="w-full flex flex-col sm:flex-row sm:items-center gap-3 p-4 text-left hover:bg-slate-50 transition-colors"
                        data-testid={`group-toggle-${key}`}
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          {isOpen ? (
                            <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                          )}
                          <div className="min-w-0">
                            <p className="font-semibold text-slate-900 truncate">{group.subscriber_name}</p>
                            <div className="flex flex-wrap gap-1.5 mt-1">
                              {validityPills.map(([validity, count]) => (
                                <span
                                  key={validity}
                                  className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium"
                                >
                                  {validity} × {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-6 sm:gap-8 text-sm shrink-0">
                          <div className="text-right">
                            <p className="text-xs text-slate-500">Outstanding</p>
                            <p className={`font-semibold ${group.total_due > 0 ? "text-red-600" : "text-slate-400"}`}>
                              ₹{group.total_due.toLocaleString("en-IN")}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-500">Paid</p>
                            <p className="font-semibold text-emerald-600">
                              ₹{group.total_paid.toLocaleString("en-IN")}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-500">Invoices</p>
                            <p className="font-semibold text-slate-700">{group.invoices.length}</p>
                          </div>
                        </div>
                      </button>
                      {isOpen && (
                        <div className="border-t border-slate-100">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Invoice #</TableHead>
                                <TableHead>Items</TableHead>
                                <TableHead>Amount</TableHead>
                                <TableHead>Due Date</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="w-[50px]"></TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {group.invoices.map((inv) => renderInvoiceRow(inv, { hideSubscriber: true }))}
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </Card>
                  );
                })
              )}
              <PaginationBar />
            </div>
          );
        })()}

        {/* Create Dialog */}
        <Dialog
          open={showDialog}
          onOpenChange={(open) => {
            setShowDialog(open);
            if (!open) {
              resetForm();
            }
          }}
        >
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingInvoice ? "Edit Invoice" : "Create Invoice"}</DialogTitle>
              <DialogDescription>
                {editingInvoice ? "Update the pending invoice details before payment is collected" : "Generate a new invoice with multiple line items"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-b pb-4">
                <div className="space-y-2">
                  <Label>Subscriber *</Label>
                  <SearchableSubscriberSelect
                    value={formData.subscriber_id}
                    onSelect={(id) => setFormData(prev => ({ ...prev, subscriber_id: id }))}
                    authAxios={authAxios}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Due Date *</Label>
                  <Input
                    type="date"
                    value={formData.due_date ? format(formData.due_date, "yyyy-MM-dd") : ""}
                    onChange={(e) => setFormData(prev => ({ ...prev, due_date: e.target.value ? new Date(e.target.value) : null }))}
                    required
                  />
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
                    <div key={`line-item-${index}`} className="p-4 bg-slate-50 rounded-lg relative border border-slate-100 space-y-4">
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

                      {/* Item type toggle */}
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant={item.item_type !== "custom" ? "default" : "outline"}
                          className="h-7 text-xs"
                          onClick={() => updateLineItem(index, "item_type", "plan")}
                        >
                          Plan
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant={item.item_type === "custom" ? "default" : "outline"}
                          className="h-7 text-xs"
                          onClick={() => updateLineItem(index, "item_type", "custom")}
                        >
                          Custom Item
                        </Button>
                        {item.item_type === "custom" && (
                          <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                            Ad-hoc charge (not linked to a plan)
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="space-y-2">
                          {item.item_type === "custom" ? (
                            <>
                              <Label>Item Description *</Label>
                              <Input
                                type="text"
                                placeholder="e.g. Installation charge, Router rental..."
                                value={item.description || ""}
                                onChange={(e) => updateLineItem(index, "description", e.target.value)}
                                required
                              />
                            </>
                          ) : (
                            <>
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
                            </>
                          )}
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
                          <Input
                            type="date"
                            value={item.service_start_date ? format(item.service_start_date, "yyyy-MM-dd") : ""}
                            onChange={(e) => updateLineItem(index, "service_start_date", e.target.value ? new Date(e.target.value) : null)}
                            required
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Service Period End *</Label>
                          <Input
                            type="date"
                            value={item.service_end_date ? format(item.service_end_date, "yyyy-MM-dd") : ""}
                            onChange={(e) => updateLineItem(index, "service_end_date", e.target.value ? new Date(e.target.value) : null)}
                            required
                          />
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
                <Button type="submit" data-testid="save-invoice-btn" disabled={savingInvoice}>
                  {savingInvoice ? "Saving..." : (editingInvoice ? "Update Invoice" : "Create Invoice")}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        <Dialog
          open={showBulkDialog}
          onOpenChange={(open) => {
            setShowBulkDialog(open);
            if (!open) {
              setBulkFile(null);
              setBulkResult(null);
            }
          }}
        >
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                Bulk Upload Invoices
              </DialogTitle>
              <DialogDescription>
                Upload a CSV or XLSX file to create multiple invoices at once.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-800">Download Sample File</p>
                  <p className="text-xs text-blue-600 mt-0.5">
                    Columns: subscriber_whatsapp_number, plan_name, base_amount, discount, service_start_date, service_end_date, due_date
                  </p>
                </div>
                <Button variant="outline" size="sm" className="shrink-0 border-blue-200 text-blue-700" onClick={handleDownloadSample}>
                  <Download className="w-3.5 h-3.5 mr-1" /> Sample CSV
                </Button>
              </div>

              <div
                className="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center cursor-pointer hover:border-slate-400 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  onChange={(e) => { setBulkFile(e.target.files?.[0] || null); setBulkResult(null); }}
                />
                <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                {bulkFile ? (
                  <p className="text-sm font-medium text-slate-700">{bulkFile.name}</p>
                ) : (
                  <p className="text-sm text-slate-500">Click to select CSV or XLSX file</p>
                )}
              </div>

              {bulkResult && (
                <div className="bg-slate-50 rounded-lg p-3 space-y-2">
                  <div className="flex gap-4 text-sm">
                    <span className="flex items-center gap-1 text-emerald-700"><CheckCircle className="w-4 h-4" /> {bulkResult.created} created</span>
                    <span className="flex items-center gap-1 text-amber-600"><AlertCircle className="w-4 h-4" /> {bulkResult.skipped} skipped</span>
                    <span className="flex items-center gap-1 text-red-600"><XCircle className="w-4 h-4" /> {bulkResult.errors?.length || 0} errors</span>
                  </div>
                  {bulkResult.errors?.length > 0 && (
                    <div className="text-xs text-red-600 space-y-0.5 max-h-24 overflow-y-auto">
                      {bulkResult.errors.map((e, i) => <div key={`inv-err-${e.row}-${i}`}>Row {e.row}: {e.reason}</div>)}
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setShowBulkDialog(false)}>Close</Button>
                <Button className="flex-1" onClick={handleBulkUpload} disabled={!bulkFile || bulkUploading}>
                  {bulkUploading ? "Uploading..." : "Upload File"}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog
          open={showPaymentConfirmDialog}
          onOpenChange={(open) => {
            setShowPaymentConfirmDialog(open);
            if (!open) setPaymentTargetInvoice(null);
          }}
        >
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Confirm Payment</DialogTitle>
              <DialogDescription>
                Record how this invoice was paid before marking it as paid.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>Payment Mode *</Label>
                <Select
                  value={paymentForm.payment_mode}
                  onValueChange={(value) => setPaymentForm(prev => ({ ...prev, payment_mode: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select payment mode" />
                  </SelectTrigger>
                  <SelectContent>
                    {PAYMENT_MODE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Payment Date *</Label>
                <Input
                  type="date"
                  value={paymentForm.payment_date ? format(paymentForm.payment_date, "yyyy-MM-dd") : ""}
                  onChange={(e) => setPaymentForm(prev => ({ ...prev, payment_date: e.target.value ? new Date(e.target.value) : null }))}
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setShowPaymentConfirmDialog(false)}>
                  Cancel
                </Button>
                <Button type="button" onClick={submitPaymentConfirmation}>
                  Confirm Payment
                </Button>
              </div>
            </div>
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
