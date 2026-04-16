import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
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
import { Badge } from "../../components/ui/badge";
import { toast } from "sonner";
import {
  Plus, Pencil, Trash2, MessageSquare, ToggleLeft, ToggleRight,
  Info, X, Zap, ChevronDown, ChevronUp, HelpCircle
} from "lucide-react";

const TEMPLATE_TYPES = [
  { value: "invoice_notification", label: "Invoice Notification" },
  { value: "payment_reminder", label: "Payment Reminder" },
  { value: "payment_confirmation", label: "Payment Confirmation" },
  { value: "announcement", label: "Announcement" },
  { value: "custom", label: "Custom" },
];

const TYPE_COLORS = {
  invoice_notification: "bg-blue-100 text-blue-800",
  payment_reminder: "bg-amber-100 text-amber-800",
  payment_confirmation: "bg-green-100 text-green-800",
  announcement: "bg-purple-100 text-purple-800",
  custom: "bg-slate-100 text-slate-800",
};

const INVOICE_TYPE_TEMPLATES = ["invoice_notification", "payment_reminder", "payment_confirmation"];

const INVOICE_VARIABLE_OPTIONS = [
  { value: "customer_name",      label: "Customer Name ({{N}})" },
  { value: "plan_name",          label: "Plan Name ({{N}})" },
  { value: "tenure",             label: "Tenure / Date Range ({{N}})" },
  { value: "amount",             label: "Amount ({{N}})" },
  { value: "due_date",           label: "Due Date ({{N}})" },
  { value: "invoice_number",     label: "Invoice Number ({{N}})" },
  { value: "days_overdue",       label: "Days Overdue ({{N}})" },
  { value: "invoice_public_url", label: "Invoice Public URL ({{N}}) — for body text" },
  { value: "payment_link",       label: "Payment / Razorpay Link ({{N}})" },
  { value: "company_logo",       label: "Company Logo URL ({{N}}) — image header" },
];

// Quick-setup preset templates
const QUICK_TEMPLATES = [
  {
    label: "Invoice Notification (with static image header + button)",
    template_name: "invoice_notification",
    display_name: "Invoice Notification",
    template_type: "invoice_notification",
    language_code: "en",
    description: "Sends invoice details with a button to open the invoice",
    body_variables: ["customer_name", "plan_name", "tenure", "due_date", "amount"],
    header_type: "image",
    header_variable: "",
    header_image_static: true,
    has_payment_button: true,
    button_url_variable: "invoice_public_url",
    is_active: true,
  },
  {
    label: "Payment Reminder (body-only, no header)",
    template_name: "payment_reminder",
    display_name: "Payment Reminder",
    template_type: "payment_reminder",
    language_code: "en",
    description: "Reminds subscribers about overdue payment",
    body_variables: ["customer_name", "invoice_number", "amount", "days_overdue"],
    header_type: "none",
    header_variable: "",
    header_image_static: false,
    has_payment_button: true,
    button_url_variable: "invoice_public_url",
    is_active: true,
  },
  {
    label: "Payment Confirmation (body-only)",
    template_name: "payment_confirmation",
    display_name: "Payment Confirmation",
    template_type: "payment_confirmation",
    language_code: "en",
    description: "Confirms successful payment to subscriber",
    body_variables: ["customer_name", "invoice_number", "amount", "due_date"],
    header_type: "none",
    header_variable: "",
    header_image_static: false,
    has_payment_button: false,
    button_url_variable: "invoice_public_url",
    is_active: true,
  },
];

const defaultForm = {
  template_name: "",
  display_name: "",
  template_type: "invoice_notification",
  language_code: "en",
  description: "",
  body_variables: [],
  header_type: "none",
  header_variable: "",
  header_image_static: false,
  has_payment_button: false,
  button_url_variable: "invoice_public_url",
  is_active: true,
};

export default function WhatsAppTemplates() {
  const { authAxios } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editTemplate, setEditTemplate] = useState(null);
  const [form, setForm] = useState(defaultForm);
  const [saving, setSaving] = useState(false);
  const [variableInput, setVariableInput] = useState("");
  const [selectedVariable, setSelectedVariable] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [showQuickSetup, setShowQuickSetup] = useState(false);
  const [showHelpTips, setShowHelpTips] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const res = await authAxios.get("/admin/whatsapp-templates");
      setTemplates(res.data);
    } catch (e) {
      toast.error("Failed to load WhatsApp templates");
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditTemplate(null);
    setForm(defaultForm);
    setVariableInput("");
    setSelectedVariable("");
    setShowDialog(true);
  };

  const openEdit = (tmpl) => {
    setEditTemplate(tmpl);
    setForm({
      template_name: tmpl.template_name,
      display_name: tmpl.display_name,
      template_type: tmpl.template_type,
      language_code: tmpl.language_code || "en",
      description: tmpl.description || "",
      body_variables: tmpl.body_variables || [],
      header_type: tmpl.header_type || "none",
      header_variable: tmpl.header_variable || "",
      header_image_static: tmpl.header_image_static || false,
      has_payment_button: tmpl.has_payment_button || false,
      button_url_variable: tmpl.button_url_variable || "invoice_public_url",
      is_active: tmpl.is_active !== false,
    });
    setVariableInput("");
    setSelectedVariable("");
    setShowDialog(true);
  };

  const applyQuickTemplate = (preset) => {
    const { label, ...formData } = preset;
    setEditTemplate(null);
    setForm(formData);
    setVariableInput("");
    setSelectedVariable("");
    setShowQuickSetup(false);
    setShowDialog(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.display_name.trim() || form.display_name.trim().length < 2) {
      toast.error("Display name must be at least 2 characters"); return;
    }
    if (!form.template_name.trim() || form.template_name.trim().length < 2) {
      toast.error("Template name (API) must be at least 2 characters"); return;
    }
    if (!/^[a-z0-9_]+$/.test(form.template_name.trim())) {
      toast.error("Template name (API) must be lowercase letters, numbers and underscores only"); return;
    }
    if (!form.language_code.trim()) {
      toast.error("Language code is required (e.g. en, hi)"); return;
    }
    setSaving(true);
    try {
      if (editTemplate) {
        await authAxios.put(`/admin/whatsapp-templates/${editTemplate.id}`, form);
        toast.success("Template updated successfully");
      } else {
        await authAxios.post("/admin/whatsapp-templates", form);
        toast.success("Template created successfully");
      }
      setShowDialog(false);
      fetchTemplates();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save template");
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (tmpl) => {
    try {
      const res = await authAxios.patch(`/admin/whatsapp-templates/${tmpl.id}/toggle`);
      toast.success(res.data.message);
      fetchTemplates();
    } catch (e) {
      toast.error("Failed to toggle template status");
    }
  };

  const handleDelete = async (tmpl) => {
    try {
      await authAxios.delete(`/admin/whatsapp-templates/${tmpl.id}`);
      toast.success("Template deleted");
      setDeleteConfirm(null);
      fetchTemplates();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete template");
    }
  };

  const addVariable = () => {
    const v = variableInput.trim();
    if (!v) return;
    if (form.body_variables.includes(v)) {
      toast.error("Variable already added"); return;
    }
    setForm({ ...form, body_variables: [...form.body_variables, v] });
    setVariableInput("");
  };

  const addSelectedVariable = () => {
    if (!selectedVariable) return;
    if (form.body_variables.includes(selectedVariable)) {
      toast.error("Variable already added"); return;
    }
    setForm({ ...form, body_variables: [...form.body_variables, selectedVariable] });
    setSelectedVariable("");
  };

  const removeVariable = (idx) => {
    setForm({ ...form, body_variables: form.body_variables.filter((_, i) => i !== idx) });
  };

  const filteredTemplates = filterType === "all"
    ? templates
    : templates.filter((t) => t.template_type === filterType);

  // Derive whether the header config UI should show variable selector
  const showHeaderVariableSelector = form.header_type !== "none" && !form.header_image_static;

  return (
    <AdminLayout title="WhatsApp Templates">
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">WhatsApp Message Templates</h2>
            <p className="text-sm text-slate-500 mt-1">
              Configure pre-approved WhatsApp Business API templates used for invoices, reminders, and notifications.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setShowQuickSetup(!showQuickSetup)}
              className="gap-2 border-green-300 text-green-700 hover:bg-green-50"
            >
              <Zap className="w-4 h-4" />
              Quick Setup
            </Button>
            <Button onClick={openCreate} className="gap-2 bg-green-600 hover:bg-green-700 text-white">
              <Plus className="w-4 h-4" />
              New Template
            </Button>
          </div>
        </div>

        {/* Quick Setup Panel */}
        {showQuickSetup && (
          <Card className="border-green-200 bg-green-50">
            <CardContent className="p-4">
              <p className="text-sm font-medium text-green-800 mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Quick Setup — click to pre-fill a common template
              </p>
              <div className="flex flex-wrap gap-2">
                {QUICK_TEMPLATES.map((t) => (
                  <button
                    key={t.template_name}
                    onClick={() => applyQuickTemplate(t)}
                    className="px-3 py-2 bg-white border border-green-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-green-100 hover:border-green-400 transition-colors text-left"
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <button
            onClick={() => setShowHelpTips(!showHelpTips)}
            className="w-full flex items-center justify-between text-left"
          >
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-blue-600 flex-shrink-0" />
              <p className="text-sm font-medium text-blue-800">Setup Guide &amp; Tips</p>
            </div>
            {showHelpTips ? <ChevronUp className="w-4 h-4 text-blue-600" /> : <ChevronDown className="w-4 h-4 text-blue-600" />}
          </button>
          {showHelpTips && (
            <div className="mt-3 space-y-2 text-xs text-blue-700 border-t border-blue-200 pt-3">
              <p><strong>Template Name (API)</strong> — must exactly match the approved template name in Meta Business Manager (e.g. <code className="bg-blue-100 px-1 rounded">invoice_notification</code>).</p>
              <p><strong>Body Variables</strong> — add them in the exact order as in your Meta template. They become <code className="bg-blue-100 px-1 rounded">{"{{1}}"}</code>, <code className="bg-blue-100 px-1 rounded">{"{{2}}"}</code>, … in the message body.</p>
              <p><strong>Static Header Image</strong> — if your template has a header image uploaded/fixed in Meta Business Manager, enable this option. The system will NOT pass any image URL — Meta handles it. Do NOT enable if your template has a dynamic (variable) header image.</p>
              <p><strong>URL Button</strong> — enable "Has URL Button" if your template has a Visit Website / CTA button. The <strong>invoice public URL</strong> (e.g. <code className="bg-blue-100 px-1 rounded">https://yourdomain.com/invoice/INV-001</code>) is passed as the button's dynamic value. In Meta, the button URL should be configured as <code className="bg-blue-100 px-1 rounded">{"{{1}}"}</code> or contain <code className="bg-blue-100 px-1 rounded">{"{{1}}"}</code> at the end.</p>
            </div>
          )}
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-3 flex-wrap">
          <Label className="text-slate-600 text-sm">Filter:</Label>
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${filterType === "all" ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
          >
            All ({templates.length})
          </button>
          {TEMPLATE_TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => setFilterType(t.value)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${filterType === t.value ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
            >
              {t.label} ({templates.filter((tmpl) => tmpl.template_type === t.value).length})
            </button>
          ))}
        </div>

        {/* Table */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
              </div>
            ) : filteredTemplates.length === 0 ? (
              <div className="text-center py-16">
                <MessageSquare className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500 font-medium">No templates found</p>
                <p className="text-slate-400 text-sm mt-1">Create or use Quick Setup to add your first template</p>
                <div className="flex justify-center gap-2 mt-4">
                  <Button variant="outline" onClick={() => setShowQuickSetup(true)} className="gap-2 border-green-300 text-green-700">
                    <Zap className="w-4 h-4" /> Quick Setup
                  </Button>
                  <Button onClick={openCreate} className="gap-2 bg-green-600 hover:bg-green-700 text-white">
                    <Plus className="w-4 h-4" /> New Template
                  </Button>
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50">
                    <TableHead>Display Name</TableHead>
                    <TableHead>Template (API)</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Lang</TableHead>
                    <TableHead>Header</TableHead>
                    <TableHead>Body Variables</TableHead>
                    <TableHead>Button</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTemplates.map((tmpl) => (
                    <TableRow key={tmpl.id} className="hover:bg-slate-50">
                      <TableCell>
                        <div>
                          <p className="font-medium text-slate-800">{tmpl.display_name}</p>
                          {tmpl.description && (
                            <p className="text-xs text-slate-400 mt-0.5 max-w-48 truncate">{tmpl.description}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <code className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs font-mono">
                          {tmpl.template_name}
                        </code>
                      </TableCell>
                      <TableCell>
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${TYPE_COLORS[tmpl.template_type] || "bg-slate-100 text-slate-700"}`}>
                          {TEMPLATE_TYPES.find(t => t.value === tmpl.template_type)?.label || tmpl.template_type}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-slate-600">{tmpl.language_code || "en"}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-0.5">
                          {tmpl.header_type === "none" || !tmpl.header_type ? (
                            <span className="text-[10px] text-slate-300 uppercase font-bold">None</span>
                          ) : tmpl.header_image_static ? (
                            <span className="text-[10px] text-purple-600 uppercase font-bold flex items-center gap-0.5">
                              IMG (static)
                            </span>
                          ) : (
                            <span className={`text-[10px] font-bold uppercase ${tmpl.header_type === 'image' ? 'text-blue-600' : 'text-slate-500'}`}>
                              {tmpl.header_type}
                              {tmpl.header_variable && <span className="ml-1 font-normal normal-case text-slate-400">({tmpl.header_variable})</span>}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {tmpl.body_variables && tmpl.body_variables.length > 0 ? (
                          <div className="flex flex-wrap gap-1 max-w-40">
                            {tmpl.body_variables.slice(0, 3).map((v, i) => (
                              <span key={i} className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-xs">
                                {`{{${i + 1}}}`} <span className="text-slate-400">{v}</span>
                              </span>
                            ))}
                            {tmpl.body_variables.length > 3 && (
                              <span className="text-xs text-slate-400">+{tmpl.body_variables.length - 3} more</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 text-xs">None</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {tmpl.has_payment_button ? (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-green-600 text-xs font-medium">URL Button</span>
                            {tmpl.button_url_variable && (
                              <span className="text-xs text-slate-400">{tmpl.button_url_variable === "invoice_number" ? "invoice no." : "full URL"}</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 text-xs">No</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <button
                          onClick={() => handleToggle(tmpl)}
                          className="flex items-center gap-1.5 text-sm"
                          title={tmpl.is_active ? "Click to deactivate" : "Click to activate"}
                        >
                          {tmpl.is_active ? (
                            <>
                              <ToggleRight className="w-5 h-5 text-green-600" />
                              <span className="text-green-600 font-medium">Active</span>
                            </>
                          ) : (
                            <>
                              <ToggleLeft className="w-5 h-5 text-slate-400" />
                              <span className="text-slate-500">Inactive</span>
                            </>
                          )}
                        </button>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => openEdit(tmpl)} className="h-8 w-8 p-0 text-slate-600 hover:text-blue-600">
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setDeleteConfirm(tmpl)} className="h-8 w-8 p-0 text-slate-400 hover:text-red-600">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create / Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-xl max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editTemplate ? "Edit Template" : "New WhatsApp Template"}</DialogTitle>
            <DialogDescription>
              {editTemplate
                ? "Update the template settings. Template name must match exactly what is approved in Meta Business Manager."
                : "Add a pre-approved WhatsApp Business API template. The template name must match exactly what is approved in Meta."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSave} className="space-y-5 mt-2">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Display Name <span className="text-red-500">*</span></Label>
                <Input
                  placeholder="e.g. Invoice Notification"
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label className="flex items-center gap-1">
                  Template Name (API) <span className="text-red-500">*</span>
                  <HelpCircle className="w-3 h-3 text-slate-400" title="Must match the approved template name in Meta exactly (e.g. invoice_notification)" />
                </Label>
                <Input
                  placeholder="e.g. invoice_notification"
                  value={form.template_name}
                  onChange={(e) => setForm({ ...form, template_name: e.target.value.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "") })}
                  required
                />
                <p className="text-[11px] text-slate-400">Lowercase, letters/numbers/underscores</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Template Type</Label>
                <Select value={form.template_type} onValueChange={(v) => setForm({ ...form, template_type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TEMPLATE_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Language Code</Label>
                <Input
                  placeholder="e.g. en, hi, mr"
                  value={form.language_code}
                  onChange={(e) => setForm({ ...form, language_code: e.target.value })}
                />
                <p className="text-[11px] text-slate-400">Use <code>en_US</code> if needed</p>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Description <span className="text-slate-400 text-xs">(optional)</span></Label>
              <Input
                placeholder="Brief description of when this template is used"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            {/* ── Header Settings ── */}
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wide flex items-center gap-1.5">
                <Info className="w-3 h-3" /> Header Component
              </h4>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>Header Type</Label>
                  <Select
                    value={form.header_type}
                    onValueChange={(v) => setForm({
                      ...form,
                      header_type: v,
                      header_variable: v === "none" ? "" : form.header_variable,
                      header_image_static: v !== "image" ? false : form.header_image_static,
                    })}
                  >
                    <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None (Body Only)</SelectItem>
                      <SelectItem value="text">Text Header</SelectItem>
                      <SelectItem value="image">Image Header</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {form.header_type === "image" && (
                  <div className="space-y-1.5 self-end">
                    <label className="flex items-center gap-2 cursor-pointer bg-white border border-slate-200 rounded-lg p-2.5">
                      <input
                        type="checkbox"
                        checked={form.header_image_static}
                        onChange={(e) => setForm({ ...form, header_image_static: e.target.checked, header_variable: e.target.checked ? "" : form.header_variable })}
                        className="rounded accent-purple-600"
                      />
                      <div>
                        <p className="text-sm font-medium text-slate-700">Static Image</p>
                        <p className="text-[11px] text-slate-500">Image is fixed in Meta, no URL needed</p>
                      </div>
                    </label>
                  </div>
                )}
              </div>

              {/* Dynamic image/text variable selector */}
              {showHeaderVariableSelector && (
                <div className="space-y-1.5">
                  <Label>{form.header_type === "image" ? "Image URL Variable" : "Text Variable"}</Label>
                  {INVOICE_TYPE_TEMPLATES.includes(form.template_type) ? (
                    <Select
                      value={form.header_variable}
                      onValueChange={(v) => setForm({ ...form, header_variable: v })}
                    >
                      <SelectTrigger className="bg-white"><SelectValue placeholder="Select variable..." /></SelectTrigger>
                      <SelectContent>
                        {INVOICE_VARIABLE_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      placeholder="e.g. business_name"
                      value={form.header_variable}
                      onChange={(e) => setForm({ ...form, header_variable: e.target.value })}
                      className="bg-white"
                    />
                  )}
                </div>
              )}

              {form.header_type === "image" && form.header_image_static && (
                <div className="flex items-start gap-2 bg-purple-50 border border-purple-200 rounded p-2.5 text-xs text-purple-700">
                  <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span>Static mode: The image uploaded in Meta Business Manager is used automatically. No image URL will be passed in the API call.</span>
                </div>
              )}
            </div>

            {/* ── Body Variables ── */}
            <div className="space-y-2">
              <Label className="flex items-center gap-1">
                Body Variables
                <HelpCircle className="w-3 h-3 text-slate-400" title="Add variables in order — they map to {{1}}, {{2}}, etc. in your Meta template body." />
              </Label>
              <p className="text-xs text-slate-500">
                Add in the same order as in your Meta template. They become{" "}
                <code className="bg-slate-100 px-1 rounded">{"{{1}}"}</code>,{" "}
                <code className="bg-slate-100 px-1 rounded">{"{{2}}"}</code>, … in the message.
              </p>
              {INVOICE_TYPE_TEMPLATES.includes(form.template_type) ? (
                <div className="flex gap-2">
                  <Select value={selectedVariable} onValueChange={setSelectedVariable}>
                    <SelectTrigger><SelectValue placeholder="Select a variable to add..." /></SelectTrigger>
                    <SelectContent>
                      {INVOICE_VARIABLE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button type="button" variant="outline" onClick={addSelectedVariable} className="shrink-0">
                    Add
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. promo_text"
                    value={variableInput}
                    onChange={(e) => setVariableInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addVariable(); } }}
                  />
                  <Button type="button" variant="outline" onClick={addVariable} className="shrink-0">Add</Button>
                </div>
              )}
              {form.body_variables.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {form.body_variables.map((v, i) => (
                    <span key={i} className="flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-1 rounded-full text-xs">
                      <span className="text-blue-500 font-mono">{`{{${i + 1}}}`}</span>
                      <span className="text-slate-600">{v}</span>
                      <button type="button" onClick={() => removeVariable(i)} className="ml-1 text-slate-400 hover:text-red-500">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* ── Button / Options ── */}
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wide">URL Button (CTA)</h4>

              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.has_payment_button}
                  onChange={(e) => setForm({ ...form, has_payment_button: e.target.checked })}
                  className="rounded"
                />
                <div>
                  <p className="text-sm font-medium text-slate-700">Has URL Button (Visit Website / Open Invoice)</p>
                  <p className="text-[11px] text-slate-500">Enable if your Meta template has a CTA URL button</p>
                </div>
              </label>

              {form.has_payment_button && (
                <div className="space-y-1.5 pl-6">
                  <Label>Button Dynamic Value</Label>
                  <Select
                    value={form.button_url_variable}
                    onValueChange={(v) => setForm({ ...form, button_url_variable: v })}
                  >
                    <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="invoice_public_url">Full Invoice URL (https://site.com/invoice/INV-001)</SelectItem>
                      <SelectItem value="invoice_number">Invoice Number only (INV-001)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-[11px] text-slate-400">
                    This value is passed as <code>{"{{1}}"}</code> in the button URL. If your Meta button URL is just <code>{"{{1}}"}</code>, choose "Full Invoice URL".
                  </p>
                </div>
              )}
            </div>

            {/* Active toggle */}
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-slate-700 font-medium">Active</span>
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>Cancel</Button>
              <Button type="submit" disabled={saving} className="bg-green-600 hover:bg-green-700 text-white min-w-[120px]">
                {saving ? "Saving…" : editTemplate ? "Update Template" : "Create Template"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete Template</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteConfirm?.display_name}</strong>? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
            <Button variant="destructive" onClick={() => handleDelete(deleteConfirm)}>Delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
