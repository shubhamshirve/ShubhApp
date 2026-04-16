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
import { Plus, Pencil, Trash2, MessageSquare, ToggleLeft, ToggleRight, Info, X } from "lucide-react";

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
  { value: "customer_name",  label: "Customer Name" },
  { value: "plan_name",      label: "Plan Name" },
  { value: "tenure",         label: "Tenure (Date Range)" },
  { value: "invoice_number", label: "Invoice Number" },
  { value: "amount",         label: "Amount" },
  { value: "due_date",       label: "Due Date" },
  { value: "payment_link",   label: "Payment Link" },
  { value: "company_logo",   label: "Company Logo (Image)" },
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
  has_payment_button: false,
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
      has_payment_button: tmpl.has_payment_button || false,
      is_active: tmpl.is_active !== false,
    });
    setVariableInput("");
    setSelectedVariable("");
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
      toast.error("Variable already added");
      return;
    }
    setForm({ ...form, body_variables: [...form.body_variables, v] });
    setVariableInput("");
  };

  const addSelectedVariable = () => {
    if (!selectedVariable) return;
    if (form.body_variables.includes(selectedVariable)) {
      toast.error("Variable already added");
      return;
    }
    setForm({ ...form, body_variables: [...form.body_variables, selectedVariable] });
    setSelectedVariable("");
  };

  const removeVariable = (idx) => {
    const updated = form.body_variables.filter((_, i) => i !== idx);
    setForm({ ...form, body_variables: updated });
  };

  const filteredTemplates = filterType === "all"
    ? templates
    : templates.filter((t) => t.template_type === filterType);

  return (
    <AdminLayout title="WhatsApp Templates">
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">WhatsApp Message Templates</h2>
            <p className="text-sm text-slate-500 mt-1">
              Manage pre-approved WhatsApp Business API templates used for invoices, reminders, and notifications.
            </p>
          </div>
          <Button onClick={openCreate} className="gap-2 bg-green-600 hover:bg-green-700 text-white">
            <Plus className="w-4 h-4" />
            New Template
          </Button>
        </div>

        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex gap-3">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Template names must match exactly with approved Meta/WhatsApp Business templates</p>
            <p className="text-blue-600">Templates must be pre-approved in your Meta Business Suite before they can be used for sending messages. The <strong>template name</strong> here must match the approved template name exactly.</p>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-3">
          <Label className="text-slate-600 text-sm">Filter by type:</Label>
          <div className="flex gap-2 flex-wrap">
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
                <p className="text-slate-400 text-sm mt-1">Create your first WhatsApp message template</p>
                <Button onClick={openCreate} className="mt-4 gap-2 bg-green-600 hover:bg-green-700 text-white">
                  <Plus className="w-4 h-4" /> New Template
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50">
                    <TableHead>Display Name</TableHead>
                    <TableHead>Template Name (API)</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Language</TableHead>
                    <TableHead>Header</TableHead>
                    <TableHead>Body Variables</TableHead>
                    <TableHead>Payment Btn</TableHead>
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
                          <span className={`text-[10px] font-bold uppercase ${tmpl.header_type === 'none' ? 'text-slate-300' : 'text-blue-600'}`}>
                            {tmpl.header_type || 'none'}
                          </span>
                          {tmpl.header_variable && (
                            <span className="text-xs text-slate-500 truncate max-w-[100px]">
                              {tmpl.header_variable}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {tmpl.body_variables && tmpl.body_variables.length > 0 ? (
                          <div className="flex flex-wrap gap-1 max-w-36">
                            {tmpl.body_variables.slice(0, 3).map((v, i) => (
                              <span key={i} className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-xs">
                                {`{{${i + 1}}} ${v}`}
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
                          <span className="text-green-600 text-xs font-medium">Yes</span>
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
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEdit(tmpl)}
                            className="h-8 w-8 p-0 text-slate-600 hover:text-blue-600"
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteConfirm(tmpl)}
                            className="h-8 w-8 p-0 text-slate-400 hover:text-red-600"
                          >
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
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editTemplate ? "Edit Template" : "New WhatsApp Template"}</DialogTitle>
            <DialogDescription>
              {editTemplate ? "Update the template details." : "Add a new pre-approved WhatsApp Business API template."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSave} className="space-y-4 mt-2">
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
                <Label>Template Name (API) <span className="text-red-500">*</span></Label>
                <Input
                  placeholder="e.g. invoice_notification"
                  value={form.template_name}
                  onChange={(e) => setForm({ ...form, template_name: e.target.value.toLowerCase().replace(/\s+/g, "_") })}
                  required
                />
                <p className="text-xs text-slate-400">Must match approved template name exactly</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Template Type</Label>
                <Select
                  value={form.template_type}
                  onValueChange={(v) => setForm({ ...form, template_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
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
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Description</Label>
              <Input
                placeholder="Brief description of when this template is used"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            {/* Header Settings */}
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-slate-500 uppercase flex items-center gap-1.5">
                <Info className="w-3 h-3" /> Header Component
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                   <Label>Header Type</Label>
                   <Select
                     value={form.header_type}
                     onValueChange={(v) => setForm({ ...form, header_type: v, header_variable: v === 'none' ? '' : form.header_variable })}
                   >
                     <SelectTrigger className="bg-white">
                       <SelectValue />
                     </SelectTrigger>
                     <SelectContent>
                       <SelectItem value="none">None (Body Only)</SelectItem>
                       <SelectItem value="text">Text Header</SelectItem>
                       <SelectItem value="image">Image Header</SelectItem>
                     </SelectContent>
                   </Select>
                </div>
                {form.header_type !== 'none' && (
                  <div className="space-y-1.5">
                     <Label>{form.header_type === 'image' ? 'Image Variable' : 'Text Variable'}</Label>
                     {INVOICE_TYPE_TEMPLATES.includes(form.template_type) ? (
                       <Select 
                          value={form.header_variable} 
                          onValueChange={(v) => setForm({ ...form, header_variable: v })}
                       >
                         <SelectTrigger className="bg-white">
                           <SelectValue placeholder="Select variable..." />
                         </SelectTrigger>
                         <SelectContent>
                           {INVOICE_VARIABLE_OPTIONS.map((opt) => (
                             <SelectItem key={opt.value} value={opt.value}>
                               {opt.label}
                             </SelectItem>
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
              </div>
            </div>

            {/* Body Variables */}
            <div className="space-y-2">
              <Label>Body Variables</Label>
              <p className="text-xs text-slate-500">
                Add variables in order — these become <code className="bg-slate-100 px-1 rounded">{`{{1}}`}</code>, <code className="bg-slate-100 px-1 rounded">{`{{2}}`}</code>, etc. in the template.
              </p>
              {INVOICE_TYPE_TEMPLATES.includes(form.template_type) ? (
                <div className="flex gap-2">
                  <Select value={selectedVariable} onValueChange={setSelectedVariable}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a variable..." />
                    </SelectTrigger>
                    <SelectContent>
                      {INVOICE_VARIABLE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
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
                  <Button type="button" variant="outline" onClick={addVariable} className="shrink-0">
                    Add
                  </Button>
                </div>
              )}
              {form.body_variables.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {form.body_variables.map((v, i) => (
                    <span key={i} className="flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-1 rounded-full text-xs">
                      <span className="text-slate-400">{`{{${i + 1}}}`}</span>
                      {v}
                      <button
                        type="button"
                        onClick={() => removeVariable(i)}
                        className="ml-1 text-slate-400 hover:text-red-500"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Options */}
            <div className="flex items-center justify-between pt-2 border-t">
              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.has_payment_button}
                    onChange={(e) => setForm({ ...form, has_payment_button: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-slate-700">Has Payment Link Button</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-slate-700">Active</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>Cancel</Button>
              <Button type="submit" disabled={saving} className="bg-green-600 hover:bg-green-700 text-white">
                {saving ? "Saving..." : editTemplate ? "Update Template" : "Create Template"}
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
              Are you sure you want to delete <strong>{deleteConfirm?.display_name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => handleDelete(deleteConfirm)}
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
