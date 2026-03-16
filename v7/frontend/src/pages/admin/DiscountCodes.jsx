import { useState, useEffect } from "react";
import { AdminLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from "../../components/ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "../../components/ui/table";
import { toast } from "sonner";
import { useAuth } from "../../App";
import { Plus, Trash2, Tag, ToggleLeft, ToggleRight, Percent, DollarSign } from "lucide-react";

export default function AdminDiscountCodes() {
  const { authAxios } = useAuth();
  const [codes, setCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    code: "",
    description: "",
    discount_type: "percentage",
    discount_value: "",
    expiry_date: "",
    max_redemptions: "0",
    is_active: true,
  });

  const fetchCodes = async () => {
    try {
      const res = await authAxios.get("/admin/discount-codes");
      setCodes(res.data);
    } catch {
      toast.error("Failed to load discount codes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCodes(); }, []);

  const handleCreate = async () => {
    if (!form.code || !form.discount_value) {
      toast.error("Code and discount value are required");
      return;
    }
    setSaving(true);
    try {
      await authAxios.post("/admin/discount-codes", {
        code: form.code,
        description: form.description || null,
        discount_type: form.discount_type,
        discount_value: parseFloat(form.discount_value),
        expiry_date: form.expiry_date || null,
        max_redemptions: parseInt(form.max_redemptions) || 0,
        is_active: form.is_active,
      });
      toast.success("Discount code created");
      setShowCreate(false);
      setForm({ code: "", description: "", discount_type: "percentage", discount_value: "", expiry_date: "", max_redemptions: "0", is_active: true });
      fetchCodes();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create code");
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (id, currentState) => {
    try {
      const res = await authAxios.patch(`/admin/discount-codes/${id}/toggle`);
      toast.success(res.data.message);
      fetchCodes();
    } catch {
      toast.error("Failed to toggle status");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this discount code?")) return;
    try {
      await authAxios.delete(`/admin/discount-codes/${id}`);
      toast.success("Discount code deleted");
      fetchCodes();
    } catch {
      toast.error("Failed to delete code");
    }
  };

  return (
    <AdminLayout title="Discount Codes">
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <p className="text-slate-500">Create and manage discount codes for operator payments</p>
          <Button onClick={() => setShowCreate(true)} data-testid="create-code-btn">
            <Plus className="w-4 h-4 mr-2" /> New Discount Code
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Tag className="w-5 h-5" /> Discount Codes
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="py-12 text-center text-slate-400">Loading...</div>
            ) : codes.length === 0 ? (
              <div className="py-12 text-center text-slate-500">
                <Tag className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                <p className="font-medium">No discount codes yet</p>
                <p className="text-sm mt-1">Create your first discount code above</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Code</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Discount</TableHead>
                      <TableHead>Expiry</TableHead>
                      <TableHead>Redemptions</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-[100px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {codes.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell>
                          <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-sm">
                            {c.code}
                          </span>
                        </TableCell>
                        <TableCell className="text-slate-600 text-sm">{c.description || "-"}</TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                            {c.discount_type === "percentage" ? (
                              <><Percent className="w-3.5 h-3.5" />{c.discount_value}% off</>
                            ) : (
                              <><span className="text-xs">₹</span>{c.discount_value} off</>
                            )}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-slate-600">
                          {c.expiry_date
                            ? new Date(c.expiry_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                            : <span className="text-slate-400">No expiry</span>}
                        </TableCell>
                        <TableCell className="text-sm">
                          <span className="text-slate-700">{c.used_count}</span>
                          <span className="text-slate-400"> / </span>
                          <span className="text-slate-500">{c.max_redemptions === 0 ? "∞" : c.max_redemptions}</span>
                        </TableCell>
                        <TableCell>
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                            c.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                          }`}>
                            {c.is_active ? "Active" : "Inactive"}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleToggle(c.id, c.is_active)}
                              title={c.is_active ? "Deactivate" : "Activate"}
                              className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-slate-700"
                            >
                              {c.is_active
                                ? <ToggleRight className="w-4 h-4 text-emerald-600" />
                                : <ToggleLeft className="w-4 h-4" />}
                            </button>
                            <button
                              onClick={() => handleDelete(c.id)}
                              className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Discount Code</DialogTitle>
            <DialogDescription>Define a new discount code for operator payments.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Code <span className="text-red-500">*</span></Label>
              <Input
                placeholder="e.g. WELCOME20"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                data-testid="discount-code-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Input
                placeholder="e.g. Welcome discount for new operators"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Discount Type <span className="text-red-500">*</span></Label>
                <select
                  className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-400"
                  value={form.discount_type}
                  onChange={(e) => setForm({ ...form, discount_type: e.target.value })}
                >
                  <option value="percentage">Percentage (%)</option>
                  <option value="flat">Flat Amount (₹)</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label>Value <span className="text-red-500">*</span></Label>
                <Input
                  type="number"
                  min="0"
                  placeholder={form.discount_type === "percentage" ? "e.g. 20" : "e.g. 100"}
                  value={form.discount_value}
                  onChange={(e) => setForm({ ...form, discount_value: e.target.value })}
                  data-testid="discount-value-input"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Expiry Date</Label>
                <Input
                  type="date"
                  value={form.expiry_date}
                  onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Max Redemptions</Label>
                <Input
                  type="number"
                  min="0"
                  placeholder="0 = unlimited"
                  value={form.max_redemptions}
                  onChange={(e) => setForm({ ...form, max_redemptions: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={saving} data-testid="save-code-btn">
              {saving ? "Saving..." : "Create Code"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
