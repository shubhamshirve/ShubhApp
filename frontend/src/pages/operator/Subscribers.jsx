import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { formatDate, formatDateTime } from "../../utils/dateFormat";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
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
import { toast } from "sonner";
import { cn } from "../../lib/utils";
import { Plus, Search, MoreVertical, Pencil, Trash2, Users, Phone, MessageCircle, Upload, Download, FileSpreadsheet, CheckCircle, XCircle, AlertCircle, Ban, History, Clock, FileText, ChevronsUpDown, Check } from "lucide-react";
import { sanitize } from "../../utils/sanitize";
import SubscriberLedger from "../../components/SubscriberLedger";

const OperatorSubscribers = () => {
  const { authAxios, user } = useAuth();
  const navigate = useNavigate();
  const isStaff = user?.role === "staff";
  const isAdminImpersonating = !!user?.impersonated_by; // admin logged in as operator
  const [subscribers, setSubscribers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const [showDialog, setShowDialog] = useState(false);
  const [editingSubscriber, setEditingSubscriber] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [limitError, setLimitError] = useState(null); // for plan limit exceeded errors

  // Track which plan-row combobox is open (by row index, null = none)
  const [openPlanCombo, setOpenPlanCombo] = useState(null);
  const [subFieldErrors, setSubFieldErrors] = useState({});
  const fileInputRef = useRef(null);
  // Always keep a fresh copy of plans accessible inside async state updaters
  const plansRef = useRef(plans);
  useEffect(() => { plansRef.current = plans; }, [plans]);

  // Expiry audit state
  const [showExpiryAudit, setShowExpiryAudit] = useState(false);
  const [expiryAuditData, setExpiryAuditData] = useState(null);
  const [expiryAuditLoading, setExpiryAuditLoading] = useState(false);

  // Ledger state
  const [ledgerOpen, setLedgerOpen] = useState(false);
  const [ledgerSubscriber, setLedgerSubscriber] = useState(null);

  // Helpers for expiry-date approach
  // start + N calendar months - 1 day  (e.g. Apr 21 + 1mo → May 20)
  const VALIDITY_MONTHS = { monthly: 1, quarterly: 3, half_yearly: 6, yearly: 12 };
  const VALIDITY_OPTIONS = [
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "half_yearly", label: "Half-Yearly" },
    { value: "yearly", label: "Yearly" },
  ];

  /** Scale plan base price to a selected tenure */
  const priceForTenure = (basePrice, baseValidity, selectedValidity) => {
    const bm = VALIDITY_MONTHS[baseValidity] || 1;
    const sm = VALIDITY_MONTHS[selectedValidity] || bm;
    return Math.round((basePrice / bm * sm) * 100) / 100;
  };

  const calcExpiry = (startDateStr, validity) => {
    if (!startDateStr || !validity) return "";
    try {
      const [yr, mo, dy] = startDateStr.split("-").map(Number);
      const months = VALIDITY_MONTHS[validity];
      if (months) {
        // Use UTC Date to avoid DST shifts
        const expiry = new Date(Date.UTC(yr, mo - 1 + months, dy));
        expiry.setUTCDate(expiry.getUTCDate() - 1);
        return expiry.toISOString().slice(0, 10);
      }
      // fallback for unknown validity
      const expiry = new Date(Date.UTC(yr, mo - 1, dy + 29));
      return expiry.toISOString().slice(0, 10);
    } catch { return ""; }
  };
  const todayStr = () => new Date().toISOString().slice(0, 10);

  const [formData, setFormData] = useState({
    name: "",
    whatsapp_number: "",
    email: "",
    address: "",
    generate_first_invoice: false,
    plans: [{
      plan_id: "",
      selected_validity: "",
      plan_start_date: todayStr(),
      plan_expiry_date: "",
      discount: 0
    }]
  });

  useEffect(() => {
    fetchSubscribers();
    fetchPlans();
    fetchDashboard();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-calculate plan_expiry_date after plan selection or start-date change
  // Runs after state commits so `plans` is always fresh
  useEffect(() => {
    if (!plans.length) return; // plans not loaded yet
    setFormData(prev => {
      let changed = false;
      const updated = prev.plans.map(p => {
        if (!p.plan_id || !p.plan_start_date) return p;
        const planDef = plans.find(pl => pl.id === p.plan_id);
        if (!planDef) return p;
        const validity = p.selected_validity || planDef.validity;
        // Only auto-fill if still empty (don't overwrite a manual override)
        if (p.plan_expiry_date) return p;
        const calc = calcExpiry(p.plan_start_date, validity);
        if (!calc || calc === p.plan_expiry_date) return p;
        changed = true;
        return { ...p, plan_expiry_date: calc };
      });
      return changed ? { ...prev, plans: updated } : prev;
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.plans.map(p => `${p.plan_id}|${p.plan_start_date}|${p.selected_validity}`).join(','), plans]);

  const fetchDashboard = async () => {
    try {
      const response = await authAxios.get("/operator/dashboard");
      setDashboardStats(response.data);
    } catch (error) {
      console.error("Failed to load dashboard");
    }
  };

  const fetchSubscribers = async () => {
    try {
      const response = await authAxios.get("/operator/subscribers");
      setSubscribers(response.data);
    } catch (error) {
      toast.error("Failed to load subscribers");
    } finally {
      setLoading(false);
    }
  };

  const fetchPlans = async () => {
    try {
      const response = await authAxios.get("/operator/plans");
      const sorted = [...response.data].sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
      );
      setPlans(sorted);
    } catch (error) {
      console.error("Failed to load plans");
    }
  };

  const validateSubField = (name, value) => {
    const v = typeof value === "string" ? value.trim() : value;
    if (name === "name") {
      if (!v || v.length < 2) return "Name must be at least 2 characters";
    } else if (name === "whatsapp_number") {
      const digits = (value || "").replace(/\D/g, "");
      if (!digits || digits.length < 10 || digits.length > 13) return "Enter a valid 10-digit WhatsApp number";
    } else if (name === "email") {
      if (v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return "Enter a valid email address";
    }
    return "";
  };

  const handleSubBlur = (e) => {
    const { name, value } = e.target;
    setSubFieldErrors((prev) => ({ ...prev, [name]: validateSubField(name, value) }));
  };

  const handleSubChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (subFieldErrors[field]) setSubFieldErrors((prev) => ({ ...prev, [field]: "" }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Validate all sub-fields
    const nameErr = validateSubField("name", formData.name);
    const phoneErr = validateSubField("whatsapp_number", formData.whatsapp_number);
    const emailErr = validateSubField("email", formData.email);
    if (nameErr || phoneErr || emailErr) {
      setSubFieldErrors({ name: nameErr, whatsapp_number: phoneErr, email: emailErr });
      toast.error("Please fix the errors before submitting");
      return;
    }

    const phoneDigits = formData.whatsapp_number.replace(/\D/g, "");
    
    if (formData.plans.length === 0) {
      toast.error("Please add at least one plan");
      return;
    }

    for (const p of formData.plans) {
      if (!p.plan_id) { toast.error("Please select a plan for all entries"); return; }
      if (p.discount < 0) { toast.error("Discount cannot be negative"); return; }
    }

    const payload = {
      ...formData,
      name: sanitize(formData.name),
      email: sanitize(formData.email),
      address: sanitize(formData.address),
      whatsapp_number: phoneDigits,
    };
    try {
      if (editingSubscriber) {
        await authAxios.put(`/operator/subscribers/${editingSubscriber.id}`, payload);
        toast.success("Subscriber updated successfully");
      } else {
        await authAxios.post("/operator/subscribers", payload);
        toast.success("Subscriber created successfully");
      }
      setShowDialog(false);
      resetForm();
      fetchSubscribers();
    } catch (error) {
      const detailRaw = error.response?.data?.detail;
      const detail = typeof detailRaw === "string" ? detailRaw
        : Array.isArray(detailRaw) ? detailRaw.map(e => e.msg || String(e)).join("; ")
        : "Failed to save subscriber";
      if (!editingSubscriber && (detail.toLowerCase().includes("upgrade") || detail.toLowerCase().includes("limit"))) {
        setShowDialog(false);
        setLimitError(detail);
      } else {
        toast.error(detail);
      }
    }
  };

  const handleDelete = async (subscriberId) => {
    if (!confirm("Are you sure you want to delete this subscriber? This action cannot be undone.")) return;
    try {
      await authAxios.delete(`/operator/subscribers/${subscriberId}`);
      toast.success("Subscriber deleted");
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete subscriber");
    }
  };

  const handleSuspend = async (subscriberId) => {
    try {
      await authAxios.post(`/operator/subscribers/${subscriberId}/suspend`);
      toast.success("Subscriber suspended");
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to suspend subscriber");
    }
  };

  const handleActivate = async (subscriberId) => {
    try {
      await authAxios.post(`/operator/subscribers/${subscriberId}/activate`);
      toast.success("Subscriber activated");
      fetchSubscribers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to activate subscriber");
    }
  };

  const openExpiryAudit = async (subscriber) => {
    setExpiryAuditData(null);
    setShowExpiryAudit(true);
    setExpiryAuditLoading(true);
    try {
      const res = await authAxios.get(`/operator/subscribers/${subscriber.id}/expiry-audit`);
      setExpiryAuditData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load expiry history");
      setShowExpiryAudit(false);
    } finally {
      setExpiryAuditLoading(false);
    }
  };

  const openEditDialog = async (subscriber) => {
    setEditingSubscriber(subscriber);
    setShowDialog(true);
    // Fetch fresh subscriber data so plan dates reflect latest invoice syncs
    try {
      const res = await authAxios.get(`/operator/subscribers/${subscriber.id}`);
      const fresh = res.data;
      setFormData({
        name: fresh.name,
        whatsapp_number: fresh.whatsapp_number,
        email: fresh.email || "",
        address: fresh.address || "",
        generate_first_invoice: false,
        plans: (fresh.plans || []).map(p => ({
          plan_id: p.plan_id,
          plan_start_date: p.plan_start_date || todayStr(),
          plan_expiry_date: p.plan_expiry_date || "",
          discount: p.discount || 0,
          selected_validity: p.selected_validity || "",
        }))
      });
    } catch {
      // Fallback to cached data if fetch fails
      setFormData({
        name: subscriber.name,
        whatsapp_number: subscriber.whatsapp_number,
        email: subscriber.email || "",
        address: subscriber.address || "",
        generate_first_invoice: false,
        plans: (subscriber.plans || []).map(p => ({
          plan_id: p.plan_id,
          plan_start_date: p.plan_start_date || todayStr(),
          plan_expiry_date: p.plan_expiry_date || "",
          discount: p.discount || 0,
          selected_validity: p.selected_validity || "",
        }))
      });
    }
  };

  const resetForm = () => {
    setOpenPlanCombo(null);
    setEditingSubscriber(null);
    setSubFieldErrors({});
    setFormData({
      name: "",
      whatsapp_number: "",
      email: "",
      address: "",
      generate_first_invoice: false,
      plans: [{
        plan_id: "",
        plan_start_date: todayStr(),
        plan_expiry_date: "",
        discount: 0
      }]
    });
  };

  const addPlanRow = () => {
    setFormData(prev => ({
      ...prev,
      plans: [...prev.plans, { plan_id: "", plan_start_date: todayStr(), plan_expiry_date: "", discount: 0 }]
    }));
  };

  const removePlanRow = (index) => {
    setFormData(prev => ({
      ...prev,
      plans: prev.plans.filter((_, i) => i !== index)
    }));
  };

  const updatePlanRow = (index, field, value) => {
    // Calculate planDef OUTSIDE the functional updater to avoid stale closure issues
    // At this point, `plans` is the current state value from the last render
    const currentPlanId = field === "plan_id" ? value : null;
    const planDefForUpdate = currentPlanId
      ? plans.find(pl => pl.id === currentPlanId)
      : null;

    setFormData(prev => {
      const updated = prev.plans.map((p, i) => {
        if (i !== index) return p;
        const newRow = { ...p, [field]: value };
        // Use the planDef computed outside the updater (not stale)
        const planDef = planDefForUpdate || plans.find(pl => pl.id === newRow.plan_id) || plansRef.current.find(pl => pl.id === newRow.plan_id);

        // When plan changes, reset selected_validity to base validity and recalc expiry
        if (field === "plan_id" && planDef) {
          newRow.selected_validity = planDef.validity;
          if (newRow.plan_start_date) {
            newRow.plan_expiry_date = calcExpiry(newRow.plan_start_date, planDef.validity);
          }
        }
        // When tenure changes, recalc expiry using selected_validity
        if (field === "selected_validity" && newRow.plan_start_date) {
          newRow.plan_expiry_date = calcExpiry(newRow.plan_start_date, value);
        }
        // When start_date changes, recalc expiry using current selected_validity or plan validity
        if (field === "plan_start_date" && planDef) {
          const v = newRow.selected_validity || planDef.validity;
          newRow.plan_expiry_date = calcExpiry(value, v);
        }
        return newRow;
      });
      return { ...prev, plans: updated };
    });
  };

  const filteredSubscribers = subscribers.filter(sub =>
    sub.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sub.whatsapp_number.includes(searchTerm)
  );

  const totalPages = Math.max(1, Math.ceil(filteredSubscribers.length / ITEMS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedSubscribers = filteredSubscribers.slice(
    (safePage - 1) * ITEMS_PER_PAGE,
    safePage * ITEMS_PER_PAGE
  );

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1); // reset to page 1 on new search
  };

  // ── Bulk Upload ───────────────────────────────────────────────────────────
  const handleDownloadSample = async () => {
    try {
      const res = await authAxios.get("/operator/subscribers/sample-csv", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = "subscribers_sample.csv";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch { toast.error("Failed to download sample"); }
  };

  const pollJobStatusInBackground = async (jobId) => {
    const maxAttempts = 300;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const res = await authAxios.get(`/operator/jobs/${jobId}`);
        const { status, result, error } = res.data;

        if (status === "completed") {
          fetchSubscribers();
          fetchDashboard();
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
    setLimitError(null);
    try {
      const form = new FormData();
      form.append("file", bulkFile);
      const res = await authAxios.post("/operator/subscribers/bulk-upload", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      const { job_id } = res.data;
      toast.success("File uploaded successfully. Processing in background...");
      // Close dialog immediately
      setShowBulkDialog(false);
      setBulkUploading(false);
      // Start background polling without awaiting
      pollJobStatusInBackground(job_id);
    } catch (e) {
      const detail = e.response?.data?.detail || "Upload failed";
      if (detail.toLowerCase().includes("upgrade") || detail.toLowerCase().includes("limit")) {
        setShowBulkDialog(false);
        setLimitError(detail);
      } else {
        toast.error(detail);
      }
      setBulkUploading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      active: "badge-active",
      inactive: "badge-suspended"
    };
    return <span className={badges[status] || "badge-pending"}>{status}</span>;
  };

  const handleMigrateToExpiry = async () => {
    if (!window.confirm("This will convert all existing subscribers from the old billing-date system to the new expiry-date system. Subscribers already migrated will be skipped. Continue?")) return;
    try {
      const res = await authAxios.post("/operator/subscribers/migrate-to-expiry-dates");
      toast.success(`Migration done — ${res.data.plans_migrated} plans migrated, ${res.data.plans_skipped_already_migrated} already on expiry-date billing.`);
      fetchSubscribers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Migration failed");
    }
  };

  if (loading) {
    return (
      <OperatorLayout title="Subscribers">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const isReadOnly = dashboardStats?.is_read_only;

  return (
    <>
    <OperatorLayout title="Subscribers" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search subscribers..."
              value={searchTerm}
              onChange={handleSearchChange}
              className="pl-10"
              data-testid="search-subscribers"
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => { setShowBulkDialog(true); setBulkFile(null); setBulkResult(null); }}
              disabled={isReadOnly || isStaff}
            >
              <Upload className="w-4 h-4 mr-2" />
              Bulk Upload
            </Button>
            <Button 
              onClick={() => { resetForm(); setShowDialog(true); }}
              disabled={isReadOnly}
              data-testid="add-subscriber-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Subscriber
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleMigrateToExpiry}
              title="Migrate existing subscribers to expiry-date billing"
              className="text-xs"
            >
              Migrate to Expiry Billing
            </Button>
          </div>
        </div>

        {/* Subscriber usage bar */}
        {dashboardStats?.max_subscribers != null && (
          <div className="flex items-center gap-3 px-1">
            <span className="text-sm text-slate-500 whitespace-nowrap">
              Subscribers:
              <span className={`ml-1 font-semibold ${
                dashboardStats.total_subscribers >= dashboardStats.max_subscribers
                  ? "text-red-600"
                  : dashboardStats.total_subscribers >= dashboardStats.max_subscribers * 0.8
                  ? "text-amber-600"
                  : "text-slate-700"
              }`}>
                {dashboardStats.total_subscribers} / {dashboardStats.max_subscribers}
              </span>
            </span>
            <div className="flex-1 max-w-[200px] h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  dashboardStats.total_subscribers >= dashboardStats.max_subscribers
                    ? "bg-red-500"
                    : dashboardStats.total_subscribers >= dashboardStats.max_subscribers * 0.8
                    ? "bg-amber-400"
                    : "bg-emerald-500"
                }`}
                style={{ width: `${Math.min(100, (dashboardStats.total_subscribers / dashboardStats.max_subscribers) * 100)}%` }}
              />
            </div>
            {dashboardStats.total_subscribers >= dashboardStats.max_subscribers && (
              <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                Limit reached
              </span>
            )}
          </div>
        )}

        {/* Subscribers Table */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>WhatsApp</TableHead>
                  <TableHead>Active Plans</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedSubscribers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                      <Users className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      No subscribers found
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedSubscribers.map((subscriber) => (
                    <TableRow key={subscriber.id} data-testid={`subscriber-row-${subscriber.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <span className="text-blue-600 font-medium text-sm">
                              {subscriber.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <span className="font-medium block">{subscriber.name}</span>
                            <span className="text-xs text-slate-400 font-mono">{subscriber.id}</span>
                            {subscriber.email && (
                              <span className="text-xs text-slate-500 block">{subscriber.email}</span>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Phone className="w-3 h-3 text-emerald-600" />
                          <span className="font-mono text-sm">{subscriber.whatsapp_number}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          {subscriber.plans?.map((p, idx) => {
                            const expiry = p.plan_expiry_date;
                            const today = new Date().toISOString().slice(0, 10);
                            const daysLeft = expiry
                              ? Math.ceil((new Date(expiry) - new Date(today)) / 86400000)
                              : null;
                            const isExpired = daysLeft !== null && daysLeft < 0;
                            const isUrgent = daysLeft !== null && daysLeft >= 0 && daysLeft <= 7;
                            return (
                              <div key={idx} className="text-xs border-b border-slate-50 last:border-0 pb-1 last:pb-0">
                                <span className="font-medium text-slate-700">{p.plan_name}</span>
                                <div className="flex gap-2 mt-0.5 flex-wrap">
                                  {expiry ? (
                                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                      isExpired ? "bg-red-100 text-red-700" :
                                      isUrgent  ? "bg-amber-100 text-amber-700" :
                                                  "bg-slate-100 text-slate-600"
                                    }`}>
                                      {isExpired
                                        ? `Expired ${Math.abs(daysLeft)}d ago`
                                        : daysLeft === 0 ? "Expires today"
                                        : `Expires ${expiry}`}
                                    </span>
                                  ) : p.billing_date ? (
                                    <span className="text-slate-400">Day {p.billing_date}</span>
                                  ) : null}
                                  {p.discount > 0 && <span className="text-slate-400">-₹{p.discount}</span>}
                                </div>
                              </div>
                            );
                          })}
                          {(!subscriber.plans || subscriber.plans.length === 0) && (
                            <span className="text-slate-400">-</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{getStatusBadge(subscriber.status)}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" disabled={isReadOnly}>
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => openEditDialog(subscriber)}>
                              <Pencil className="w-4 h-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => { navigate(`/operator/subscribers/${subscriber.id}/ledger`); }}>
                              <FileText className="w-4 h-4 mr-2 text-blue-600" />
                              View Ledger
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => openExpiryAudit(subscriber)}>
                              <History className="w-4 h-4 mr-2 text-blue-600" />
                              Expiry History
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => {
                                let phone = (subscriber.whatsapp_number || "").replace(/[^0-9]/g, '');
                                if (phone.length === 10) phone = "91" + phone;
                                if (!phone) { return; }
                                window.open(`https://wa.me/${phone}`, '_blank');
                              }}
                              data-testid={`wa-subscriber-${subscriber.id}`}
                            >
                              <MessageCircle className="w-4 h-4 mr-2 text-emerald-600" />
                              WhatsApp
                            </DropdownMenuItem>
                            {!isStaff && (
                              subscriber.status === "active" ? (
                                <DropdownMenuItem
                                  onClick={() => handleSuspend(subscriber.id)}
                                  className="text-amber-600"
                                  data-testid={`suspend-subscriber-${subscriber.id}`}
                                >
                                  <Ban className="w-4 h-4 mr-2" />
                                  Suspend
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem
                                  onClick={() => handleActivate(subscriber.id)}
                                  className="text-emerald-600"
                                  data-testid={`activate-subscriber-${subscriber.id}`}
                                >
                                  <CheckCircle className="w-4 h-4 mr-2" />
                                  Activate
                                </DropdownMenuItem>
                              )
                            )}
                            {isAdminImpersonating && (
                              <DropdownMenuItem
                                onClick={() => handleDelete(subscriber.id)}
                                className="text-red-600"
                                data-testid={`delete-subscriber-${subscriber.id}`}
                              >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Delete
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

        {/* Pagination Controls */}
        {filteredSubscribers.length > ITEMS_PER_PAGE && (
          <div className="flex items-center justify-between text-sm text-slate-500 px-1">
            <span>
              Showing {Math.min((safePage - 1) * ITEMS_PER_PAGE + 1, filteredSubscribers.length)}–
              {Math.min(safePage * ITEMS_PER_PAGE, filteredSubscribers.length)} of {filteredSubscribers.length}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={safePage <= 1}
                className="h-8 px-3"
              >
                ‹ Prev
              </Button>
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(p => p === 1 || p === totalPages || Math.abs(p - safePage) <= 2)
                .reduce((acc, p, idx, arr) => {
                  if (idx > 0 && arr[idx - 1] !== p - 1) acc.push("...");
                  acc.push(p);
                  return acc;
                }, [])
                .map((item, idx) =>
                  item === "..." ? (
                    <span key={`dots-${idx}`} className="px-1">…</span>
                  ) : (
                    <Button
                      key={item}
                      variant={item === safePage ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(item)}
                      className="h-8 w-8 p-0"
                    >
                      {item}
                    </Button>
                  )
                )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={safePage >= totalPages}
                className="h-8 px-3"
              >
                Next ›
              </Button>
            </div>
          </div>
        )}
        {/* Compact count when no pagination needed */}
        {filteredSubscribers.length > 0 && filteredSubscribers.length <= ITEMS_PER_PAGE && (
          <p className="text-xs text-slate-400 px-1">{filteredSubscribers.length} subscriber{filteredSubscribers.length !== 1 ? "s" : ""}</p>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingSubscriber ? "Edit Subscriber" : "Add New Subscriber"}</DialogTitle>
              <DialogDescription>
                {editingSubscriber ? "Update subscriber details" : "Add a new subscriber to your list"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-slate-900 border-b pb-2">Basic Information</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2 space-y-2">
                    <Label>Name *</Label>
                    <Input
                      name="name"
                      value={formData.name}
                      onChange={(e) => handleSubChange("name", e.target.value)}
                      onBlur={handleSubBlur}
                      className={subFieldErrors.name ? "border-red-500" : ""}
                      placeholder="Subscriber name"
                      required
                      data-testid="subscriber-name-input"
                    />
                    {subFieldErrors.name && <p className="text-xs text-red-500 mt-1">{subFieldErrors.name}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label>WhatsApp Number *</Label>
                    <Input
                      name="whatsapp_number"
                      value={formData.whatsapp_number}
                      onChange={(e) => handleSubChange("whatsapp_number", e.target.value)}
                      onBlur={handleSubBlur}
                      className={subFieldErrors.whatsapp_number ? "border-red-500" : ""}
                      placeholder="9876543210"
                      required
                      data-testid="subscriber-phone-input"
                    />
                    {subFieldErrors.whatsapp_number && <p className="text-xs text-red-500 mt-1">{subFieldErrors.whatsapp_number}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleSubChange("email", e.target.value)}
                      onBlur={handleSubBlur}
                      className={subFieldErrors.email ? "border-red-500" : ""}
                      placeholder="email@example.com"
                    />
                    {subFieldErrors.email && <p className="text-xs text-red-500 mt-1">{subFieldErrors.email}</p>}
                  </div>

                  <div className="col-span-2 space-y-2">
                    <Label>Address</Label>
                    <Input
                      value={formData.address}
                      onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                      placeholder="Full address"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between border-b pb-2">
                  <h4 className="text-sm font-semibold text-slate-900">Active Plans</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addPlanRow}>
                    <Plus className="w-3 h-3 mr-1" /> Add Plan
                  </Button>
                </div>

                <div className="space-y-4">
                  {formData.plans.map((plan, index) => {
                    const planDef = plans.find(p => p.id === plan.plan_id);
                    return (
                      <div key={`plan-row-${index}`} className="p-4 bg-slate-50 rounded-lg relative border border-slate-100">
                        {formData.plans.length > 1 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-white border shadow-sm text-red-500"
                            onClick={() => removePlanRow(index)}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        )}

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {/* Plan selector — searchable combobox */}
                          <div className="space-y-2">
                            <Label>Plan *</Label>
                            <Popover
                              open={openPlanCombo === index}
                              onOpenChange={(isOpen) =>
                                setOpenPlanCombo(isOpen ? index : null)
                              }
                            >
                              <PopoverTrigger asChild>
                                <Button
                                  type="button"
                                  variant="outline"
                                  role="combobox"
                                  aria-expanded={openPlanCombo === index}
                                  className="w-full justify-between font-normal text-left h-10 px-3"
                                >
                                  <span className="truncate">
                                    {plan.plan_id
                                      ? (() => {
                                          const d = plans.find(p => p.id === plan.plan_id);
                                          return d ? `${d.name} — ₹${d.price}/${d.validity}` : "Select plan";
                                        })()
                                      : <span className="text-muted-foreground">Select plan</span>
                                    }
                                  </span>
                                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                </Button>
                              </PopoverTrigger>
                              <PopoverContent
                                className="p-0 w-[var(--radix-popover-trigger-width)]"
                                align="start"
                              >
                                <Command>
                                  <CommandInput placeholder="Search plan name…" />
                                  <CommandEmpty>No plans found.</CommandEmpty>
                                  <CommandGroup className="max-h-60 overflow-y-auto">
                                    {plans.map((p) => (
                                      <CommandItem
                                        key={p.id}
                                        value={p.name}
                                        onSelect={() => {
                                          updatePlanRow(index, "plan_id", p.id);
                                          setOpenPlanCombo(null);
                                        }}
                                      >
                                        <Check
                                          className={cn(
                                            "mr-2 h-4 w-4 shrink-0",
                                            plan.plan_id === p.id ? "opacity-100" : "opacity-0"
                                          )}
                                        />
                                        <span className="flex-1 truncate">
                                          {p.name}
                                        </span>
                                        <span className="ml-2 text-xs text-muted-foreground whitespace-nowrap">
                                          ₹{p.price}/{p.validity}
                                        </span>
                                      </CommandItem>
                                    ))}
                                  </CommandGroup>
                                </Command>
                              </PopoverContent>
                            </Popover>
                          </div>

                          {/* Tenure selector */}
                          <div className="space-y-2">
                            <Label>Tenure</Label>
                            {(() => {
                              const planDef = plans.find(pl => pl.id === plan.plan_id);
                              const avail = planDef?.available_validities?.length
                                ? planDef.available_validities
                                : planDef ? [planDef.validity] : [];
                              return (
                                <Select
                                  value={plan.selected_validity || planDef?.validity || ""}
                                  onValueChange={(v) => updatePlanRow(index, "selected_validity", v)}
                                  disabled={!planDef || avail.length <= 1}
                                >
                                  <SelectTrigger>
                                    <SelectValue placeholder="Select tenure" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {avail.map(v => {
                                      const labels = { monthly:"Monthly", quarterly:"Quarterly", half_yearly:"Half-Yearly", yearly:"Yearly" };
                                      const price = planDef ? priceForTenure(planDef.price, planDef.validity, v) : 0;
                                      return (
                                        <SelectItem key={v} value={v}>
                                          {labels[v] || v} — ₹{price.toLocaleString('en-IN')}
                                        </SelectItem>
                                      );
                                    })}
                                  </SelectContent>
                                </Select>
                              );
                            })()}
                          </div>

                          {/* Plan start date */}
                          <div className="space-y-2">
                            <Label>Plan Start Date *</Label>
                            <Input
                              type="date"
                              value={plan.plan_start_date || ""}
                              onChange={(e) => updatePlanRow(index, "plan_start_date", e.target.value)}
                            />
                          </div>

                          {/* Plan end date — auto-calculated, allows manual override */}
                          <div className="space-y-2">
                            <Label className="flex items-center gap-1">
                              Plan End Date
                              <span className="text-[10px] font-normal text-indigo-500 bg-indigo-50 rounded px-1 py-0.5 leading-none">auto</span>
                            </Label>
                            <Input
                              type="date"
                              value={plan.plan_expiry_date || ""}
                              onChange={(e) => updatePlanRow(index, "plan_expiry_date", e.target.value)}
                              placeholder="Auto-calculated"
                              title="Auto-calculated from start date + tenure. You can override this."
                            />
                          </div>

                          {/* Discount */}
                          <div className="space-y-2">
                            <Label>Discount (₹)</Label>
                            <Input
                              type="number"
                              value={plan.discount}
                              onChange={(e) => updatePlanRow(index, "discount", parseFloat(e.target.value) || 0)}
                              min="0"
                              placeholder="0"
                            />
                          </div>
                        </div>

                        {/* Price preview */}
                        {plan.plan_id && (() => {
                          const planDef = plans.find(pl => pl.id === plan.plan_id);
                          const tenure = plan.selected_validity || planDef?.validity;
                          const calcPrice = planDef ? priceForTenure(planDef.price, planDef.validity, tenure) : 0;
                          return planDef ? (
                            <div className="flex flex-wrap gap-2 mt-2">
                              <p className="text-xs text-emerald-700 bg-emerald-50 rounded px-2 py-1">
                                ₹{calcPrice.toLocaleString('en-IN')} / {tenure}
                              </p>
                            </div>
                          ) : null;
                        })()}
                      </div>
                    );
                  })}
                </div>

                {/* Generate first invoice toggle — only for new subscribers */}
                {!editingSubscriber && (
                  <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-amber-50 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-slate-800">Generate First Invoice Now?</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Creates an invoice for the current billing period immediately on subscriber creation.
                      </p>
                    </div>
                    <Switch
                      checked={formData.generate_first_invoice}
                      onCheckedChange={(v) => setFormData(prev => ({ ...prev, generate_first_invoice: v }))}
                    />
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="save-subscriber-btn">
                  {editingSubscriber ? "Update Subscriber" : "Create Subscriber"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Bulk Upload Dialog */}
        <Dialog open={showBulkDialog} onOpenChange={(o) => { setShowBulkDialog(o); if (!o) { setBulkFile(null); setBulkResult(null); } }}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                Bulk Upload Subscribers
              </DialogTitle>
              <DialogDescription>Upload a CSV or XLSX file to add multiple subscribers at once.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {/* Sample Download */}
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-800">Download Sample File</p>
                  <p className="text-xs text-blue-600 mt-0.5">One row per subscriber. Supports up to 5 plans per subscriber via plan_name_1…5, plan_start_date_1…5 (YYYY-MM-DD), discount_1…5 columns.</p>
                </div>
                <Button variant="outline" size="sm" className="shrink-0 border-blue-200 text-blue-700" onClick={handleDownloadSample}>
                  <Download className="w-3.5 h-3.5 mr-1" /> Sample CSV
                </Button>
              </div>

              {/* File Picker */}
              <div
                className="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center cursor-pointer hover:border-slate-400 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  onChange={(e) => { setBulkFile(e.target.files[0]); setBulkResult(null); }}
                />
                <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                {bulkFile ? (
                  <p className="text-sm font-medium text-slate-700">{bulkFile.name}</p>
                ) : (
                  <p className="text-sm text-slate-500">Click to select CSV or XLSX file</p>
                )}
              </div>

              {/* Result */}
              {bulkResult && (
                <div className="bg-slate-50 rounded-lg p-3 space-y-2">
                  <div className="flex gap-4 text-sm">
                    <span className="flex items-center gap-1 text-emerald-700"><CheckCircle className="w-4 h-4" /> {bulkResult.created} created</span>
                    <span className="flex items-center gap-1 text-amber-600"><AlertCircle className="w-4 h-4" /> {bulkResult.skipped} skipped</span>
                    <span className="flex items-center gap-1 text-red-600"><XCircle className="w-4 h-4" /> {bulkResult.errors?.length || 0} errors</span>
                  </div>
                  {bulkResult.errors?.length > 0 && (
                    <div className="text-xs text-red-600 space-y-0.5 max-h-24 overflow-y-auto">
                      {bulkResult.errors.map((e, i) => <div key={`sub-err-${e.row}-${i}`}>Row {e.row}{e.name ? ` (${e.name})` : ""}: {e.reason}</div>)}
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
      </div>
    </OperatorLayout>

    {/* Plan Limit Exceeded Dialog */}
    <Dialog open={!!limitError} onOpenChange={() => setLimitError(null)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertCircle className="w-5 h-5" />
            Subscriber Limit Reached
          </DialogTitle>
        </DialogHeader>
        <div className="py-3 space-y-4">
          <p className="text-slate-700 text-sm leading-relaxed">{limitError}</p>
          {dashboardStats?.max_subscribers != null && (
            <div className="p-3 bg-slate-50 rounded-lg space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Current subscribers</span>
                <span className="font-semibold">{dashboardStats.total_subscribers}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Plan limit</span>
                <span className="font-semibold">{dashboardStats.max_subscribers}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Available slots</span>
                <span className="font-semibold text-amber-600">{Math.max(0, dashboardStats.max_subscribers - dashboardStats.total_subscribers)}</span>
              </div>
            </div>
          )}
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => setLimitError(null)}>Close</Button>
          <Button
            onClick={() => { setLimitError(null); window.location.href = "/operator/subscription"; }}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Upgrade Plan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Expiry Audit Dialog */}
    <Dialog open={showExpiryAudit} onOpenChange={(o) => { setShowExpiryAudit(o); if (!o) setExpiryAuditData(null); }}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="w-5 h-5 text-blue-600" />
            Plan Expiry History
            {expiryAuditData && (
              <span className="text-sm font-normal text-slate-500 ml-1">— {expiryAuditData.subscriber_name}</span>
            )}
          </DialogTitle>
          <DialogDescription>
            Timeline of plan expiry changes triggered by invoices
          </DialogDescription>
        </DialogHeader>

        {expiryAuditLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : expiryAuditData ? (
          expiryAuditData.events.length === 0 ? (
            <div className="text-center py-10 text-slate-500">
              <Clock className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p className="text-sm">No invoice-based expiry changes found.</p>
              <p className="text-xs mt-1 text-slate-400">Expiry history is derived from invoices with service dates.</p>
            </div>
          ) : (
            <div className="relative mt-2">
              {/* Timeline */}
              <div className="space-y-0">
                {expiryAuditData.events.map((ev, idx) => {
                  const statusColors = {
                    paid: "bg-green-100 text-green-700 border-green-200",
                    pending: "bg-amber-100 text-amber-700 border-amber-200",
                    cancelled: "bg-red-100 text-red-700 border-red-200",
                    overdue: "bg-orange-100 text-orange-700 border-orange-200",
                  };
                  const badgeCls = statusColors[ev.invoice_status] || "bg-slate-100 text-slate-600 border-slate-200";
                  const validityLabel = ev.selected_validity
                    ? ev.selected_validity.replace("_", "-").replace(/\b\w/g, c => c.toUpperCase())
                    : "";
                  return (
                    <div key={idx} className="flex gap-4 group">
                      {/* Timeline connector */}
                      <div className="flex flex-col items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 z-10 ${idx === 0 ? "bg-blue-600" : "bg-slate-200"}`}>
                          <FileText className={`w-4 h-4 ${idx === 0 ? "text-white" : "text-slate-500"}`} />
                        </div>
                        {idx < expiryAuditData.events.length - 1 && (
                          <div className="w-0.5 flex-1 bg-slate-200 my-1" />
                        )}
                      </div>

                      {/* Event card */}
                      <div className={`flex-1 pb-4 ${idx < expiryAuditData.events.length - 1 ? "" : ""}`}>
                        <div className="bg-white border border-slate-200 rounded-lg p-3 hover:border-slate-300 transition-colors">
                          <div className="flex items-start justify-between gap-2 flex-wrap">
                            <div>
                              <p className="font-medium text-slate-800 text-sm">{ev.plan_name}</p>
                              {validityLabel && (
                                <span className="text-xs text-slate-500">{validityLabel}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${badgeCls} capitalize`}>
                                {ev.invoice_status}
                              </span>
                              <span className="font-mono text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                                {ev.invoice_number}
                              </span>
                            </div>
                          </div>

                          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <p className="text-slate-400">Service Start</p>
                              <p className="font-medium text-slate-700">{ev.service_start_date || "—"}</p>
                            </div>
                            <div>
                              <p className="text-slate-400">Service End / New Expiry</p>
                              <p className="font-medium text-blue-700">{ev.service_end_date || "—"}</p>
                            </div>
                          </div>

                          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            Invoice created: {formatDateTime(ev.invoice_created_at)}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )
        ) : null}
      </DialogContent>
    </Dialog>

    {/* Subscriber Ledger */}
    <SubscriberLedger
      subscriberId={ledgerSubscriber?.id}
      subscriberName={ledgerSubscriber?.name}
      open={ledgerOpen}
      onClose={() => { setLedgerOpen(false); setLedgerSubscriber(null); }}
    />
    </>
  );
};

export default OperatorSubscribers;
