import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { formatDate, formatDateTime } from "../../utils/dateFormat";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
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
  Bell,
  Send,
  Plus,
  Users,
  Clock,
  Eye,
  Search,
  CheckSquare,
  Square,
  X,
  UserCheck,
} from "lucide-react";

// ─── Subscriber picker with search ─────────────────────────────────────────
const SubscriberPicker = ({ selectedIds, onChange, authAxios }) => {
  const [subscribers, setSubscribers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef(null);

  // Debounce the search input
  const handleSearchChange = (val) => {
    setSearch(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(val), 350);
  };

  // Fetch subscribers whenever search changes
  const fetchSubscribers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: 200, status: "active" });
      if (debouncedSearch) params.set("q", debouncedSearch);
      const res = await authAxios.get(`/operator/subscribers/search?${params}`);
      setSubscribers(res.data || []);
    } catch {
      setSubscribers([]);
    } finally {
      setLoading(false);
    }
  }, [authAxios, debouncedSearch]);

  useEffect(() => {
    fetchSubscribers();
  }, [fetchSubscribers]);

  const toggleOne = (id) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((s) => s !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const toggleAll = () => {
    const visibleIds = subscribers.map((s) => s.id);
    const allSelected = visibleIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      // Deselect all visible
      onChange(selectedIds.filter((id) => !visibleIds.includes(id)));
    } else {
      // Select all visible (merge with existing)
      const merged = Array.from(new Set([...selectedIds, ...visibleIds]));
      onChange(merged);
    }
  };

  const visibleIds = subscribers.map((s) => s.id);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Search bar + select-all */}
      <div className="p-2 border-b bg-slate-50 flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search subscribers..."
            className="pl-8 h-8 text-sm"
          />
          {search && (
            <button
              type="button"
              onClick={() => handleSearchChange("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={toggleAll}
          className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 whitespace-nowrap px-2 py-1 rounded hover:bg-slate-200"
        >
          {allVisibleSelected ? (
            <CheckSquare className="w-3.5 h-3.5 text-[#0066B2]" />
          ) : (
            <Square className="w-3.5 h-3.5" />
          )}
          {allVisibleSelected ? "Deselect All" : "Select All"}
        </button>
      </div>

      {/* Subscriber list */}
      <div className="max-h-56 overflow-y-auto divide-y">
        {loading ? (
          <div className="py-6 text-center text-sm text-slate-400">Loading...</div>
        ) : subscribers.length === 0 ? (
          <div className="py-6 text-center text-sm text-slate-400">
            {search ? "No subscribers match your search" : "No active subscribers found"}
          </div>
        ) : (
          subscribers.map((sub) => {
            const isSelected = selectedIds.includes(sub.id);
            return (
              <button
                key={sub.id}
                type="button"
                onClick={() => toggleOne(sub.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-slate-50 transition-colors ${
                  isSelected ? "bg-blue-50" : ""
                }`}
              >
                <div className={`flex-shrink-0 w-4 h-4 rounded border-2 flex items-center justify-center ${
                  isSelected
                    ? "bg-[#0066B2] border-[#0066B2]"
                    : "border-slate-300"
                }`}>
                  {isSelected && (
                    <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 10 10">
                      <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{sub.name}</p>
                  <p className="text-xs text-slate-500 truncate">
                    {sub.whatsapp_number || sub.email || sub.id}
                  </p>
                </div>
                {isSelected && (
                  <span className="flex-shrink-0 w-1.5 h-1.5 bg-[#0066B2] rounded-full" />
                )}
              </button>
            );
          })
        )}
      </div>

      {/* Footer */}
      {selectedIds.length > 0 && (
        <div className="px-3 py-2 border-t bg-blue-50 flex items-center justify-between">
          <span className="text-xs text-blue-700 font-medium flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5" />
            {selectedIds.length} subscriber{selectedIds.length !== 1 ? "s" : ""} selected
          </span>
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-xs text-blue-600 hover:text-blue-800 underline"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
};

// ─── Main Page ──────────────────────────────────────────────────────────────
const OperatorAnnouncements = () => {
  const { authAxios } = useAuth();
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [showViewDialog, setShowViewDialog] = useState(false);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState(null);
  const [sending, setSending] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [weeklyStats, setWeeklyStats] = useState(null);
  const [form, setForm] = useState({
    title: "",
    message: "",
    send_whatsapp: false,
    send_email: false,
    send_to_all: true,
    subscriber_ids: [],
  });

  useEffect(() => {
    Promise.all([fetchAnnouncements(), fetchDashboard()])
      .finally(() => setLoading(false));
  }, []);

  const fetchAnnouncements = async () => {
    try {
      const res = await authAxios.get("/operator/announcements");
      setAnnouncements(res.data.announcements || res.data);
      setWeeklyStats({
        limit: res.data.weekly_limit || 6,
        count: res.data.this_week_count || 0,
        remaining: res.data.remaining_this_week || 0
      });
    } catch (err) { console.warn("Failed to load announcements:", err); }
  };

  const fetchDashboard = async () => {
    try {
      const res = await authAxios.get("/operator/dashboard");
      setDashboardStats(res.data);
    } catch (err) { console.warn("Failed to load dashboard stats:", err); }
  };

  const resetForm = () => setForm({
    title: "",
    message: "",
    send_whatsapp: false,
    send_email: false,
    send_to_all: true,
    subscriber_ids: [],
  });

  const handleSend = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || form.title.trim().length < 3) {
      toast.error("Title must be at least 3 characters"); return;
    }
    if (!form.message.trim() || form.message.trim().length < 5) {
      toast.error("Message must be at least 5 characters"); return;
    }
    if (!form.send_to_all && form.subscriber_ids.length === 0) {
      toast.error("Please select at least one subscriber"); return;
    }
    setSending(true);
    try {
      const payload = {
        title: form.title,
        message: form.message,
        send_whatsapp: form.send_whatsapp,
        send_email: form.send_email,
        send_to_all: form.send_to_all,
        subscriber_ids: form.send_to_all ? [] : form.subscriber_ids,
      };
      const res = await authAxios.post("/operator/announcements", payload);
      toast.success(`Announcement sent to ${res.data.recipients} subscriber(s)`);
      setShowDialog(false);
      resetForm();
      fetchAnnouncements();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send announcement");
    } finally {
      setSending(false);
    }
  };

  const handleView = (item) => {
    setSelectedAnnouncement(item);
    setShowViewDialog(true);
  };

  const handleOpenDialog = () => {
    resetForm();
    setShowDialog(true);
  };

  const isReadOnly = dashboardStats?.is_read_only;

  if (loading) {
    return (
      <OperatorLayout title="Announcements">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  return (
    <OperatorLayout title="Announcements" isReadOnly={isReadOnly}>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex justify-between items-center">
          <p className="text-slate-500">Send bulk messages and announcements to your subscribers</p>
          <Button
            onClick={handleOpenDialog}
            disabled={isReadOnly}
            data-testid="new-announcement-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Announcement
          </Button>
        </div>

        {/* Announcements History */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                Announcement History
              </CardTitle>
              {weeklyStats && (
                <div className="text-sm text-slate-600 bg-blue-50 px-3 py-1.5 rounded-lg">
                  <span>{weeklyStats.count}/6 announcements this week</span>
                  {weeklyStats.remaining > 0 && (
                    <span className="text-emerald-600 ml-2">({weeklyStats.remaining} remaining)</span>
                  )}
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {announcements.length === 0 ? (
              <div className="text-center py-12 text-slate-500">
                <Bell className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p className="font-medium">No announcements yet</p>
                <p className="text-sm mt-1">Create your first announcement to notify subscribers</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Recipients</TableHead>
                    <TableHead>WhatsApp</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {announcements.map((item) => (
                    <TableRow key={item.id} data-testid={`announcement-row-${item.id}`}>
                      <TableCell className="font-medium">{item.title}</TableCell>
                      <TableCell className="text-sm text-slate-500 max-w-[250px] truncate">
                        {item.message}
                      </TableCell>
                      <TableCell>
                        <span className="flex items-center gap-1 text-sm">
                          <Users className="w-3 h-3" /> {item.recipient_count}
                        </span>
                      </TableCell>
                      <TableCell>
                        {item.sent_via_whatsapp
                          ? <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-medium">Sent</span>
                          : <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">No</span>
                        }
                      </TableCell>
                      <TableCell>
                        {item.sent_via_email
                          ? <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-medium">Sent</span>
                          : <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">No</span>
                        }
                      </TableCell>
                      <TableCell className="text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDateTime(item.created_at)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleView(item)}
                          className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                          title="View Announcement"
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Create Announcement Dialog */}
        <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>New Announcement</DialogTitle>
              <DialogDescription>
                Send a message to your subscribers
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSend} className="space-y-4">
              {/* Title */}
              <div className="space-y-2">
                <Label>Title *</Label>
                <Input
                  value={form.title}
                  onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))}
                  placeholder="e.g., Service Update"
                  required
                  data-testid="announcement-title"
                />
              </div>

              {/* Message */}
              <div className="space-y-2">
                <Label>Message *</Label>
                <Textarea
                  value={form.message}
                  onChange={(e) => setForm(f => ({ ...f, message: e.target.value }))}
                  placeholder="Write your announcement message..."
                  rows={4}
                  required
                  data-testid="announcement-message"
                />
              </div>

              {/* Recipients section */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Recipients</Label>

                {/* Send to all toggle */}
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                  <div>
                    <p className="text-sm font-medium text-slate-700">Send to all active subscribers</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {form.send_to_all
                        ? "All active subscribers will receive this announcement"
                        : "Choose specific subscribers below"}
                    </p>
                  </div>
                  <Switch
                    checked={form.send_to_all}
                    onCheckedChange={(checked) =>
                      setForm(f => ({ ...f, send_to_all: checked, subscriber_ids: [] }))
                    }
                    data-testid="send-to-all-toggle"
                  />
                </div>

                {/* Subscriber picker — visible only when send_to_all is false */}
                {!form.send_to_all && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs text-slate-600">Select subscribers</Label>
                      {form.subscriber_ids.length > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          {form.subscriber_ids.length} selected
                        </Badge>
                      )}
                    </div>
                    <SubscriberPicker
                      selectedIds={form.subscriber_ids}
                      onChange={(ids) => setForm(f => ({ ...f, subscriber_ids: ids }))}
                      authAxios={authAxios}
                    />
                  </div>
                )}
              </div>

              {/* WhatsApp toggle */}
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div>
                  <Label className="font-normal">Send via WhatsApp</Label>
                  <p className="text-xs text-slate-500">Also send via WhatsApp</p>
                </div>
                <Switch
                  checked={form.send_whatsapp}
                  onCheckedChange={(checked) => setForm(f => ({ ...f, send_whatsapp: checked }))}
                  data-testid="announcement-whatsapp-toggle"
                />
              </div>

              {/* Email toggle */}
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <div>
                  <Label className="font-normal">Send via Email</Label>
                  <p className="text-xs text-slate-500">Also send via email</p>
                </div>
                <Switch
                  checked={form.send_email}
                  onCheckedChange={(checked) => setForm(f => ({ ...f, send_email: checked }))}
                  data-testid="announcement-email-toggle"
                />
              </div>

              <DialogFooter>
                <Button variant="outline" type="button" onClick={() => { setShowDialog(false); resetForm(); }}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={sending || (!form.send_to_all && form.subscriber_ids.length === 0)}
                  data-testid="send-announcement-btn"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {sending ? "Sending..." : `Send${!form.send_to_all && form.subscriber_ids.length > 0 ? ` to ${form.subscriber_ids.length}` : ""}`}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* View Announcement Dialog */}
        <Dialog open={showViewDialog} onOpenChange={setShowViewDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>View Announcement</DialogTitle>
              <DialogDescription>
                Details of the announcement
              </DialogDescription>
            </DialogHeader>
            {selectedAnnouncement && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-slate-500">Title</h4>
                  <p className="mt-1 font-medium">{selectedAnnouncement.title}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-slate-500">Message</h4>
                  <div className="mt-1 p-3 bg-slate-50 rounded-md text-sm whitespace-pre-wrap">
                    {selectedAnnouncement.message}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-sm font-medium text-slate-500">Sent on</h4>
                    <p className="mt-1 text-sm flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {formatDateTime(selectedAnnouncement.created_at)}
                    </p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-slate-500">Recipients</h4>
                    <p className="mt-1 text-sm flex items-center gap-1">
                      <Users className="w-3 h-3 text-slate-400" />
                      {selectedAnnouncement.recipient_count}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 border-t pt-4">
                  {selectedAnnouncement.sent_via_whatsapp && (
                    <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-1 rounded font-medium">Sent via WhatsApp</span>
                  )}
                  {!selectedAnnouncement.sent_via_whatsapp && (
                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-1 rounded font-medium">Not sent via WhatsApp</span>
                  )}
                  {selectedAnnouncement.sent_via_email && (
                    <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded font-medium">Sent via Email</span>
                  )}
                  {!selectedAnnouncement.sent_via_email && (
                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-1 rounded font-medium">Not sent via Email</span>
                  )}
                </div>
              </div>
            )}
            <DialogFooter>
              <Button onClick={() => setShowViewDialog(false)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorAnnouncements;
