import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
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
import { toast } from "sonner";
import { Bell, Send, Plus, Users, Clock } from "lucide-react";

const OperatorAnnouncements = () => {
  const { authAxios } = useAuth();
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [sending, setSending] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [weeklyStats, setWeeklyStats] = useState(null);
  const [form, setForm] = useState({
    title: "",
    message: "",
    send_whatsapp: false,
    send_email: false,
    send_to_all: true,
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
    } catch { /* ignore */ }
  };

  const fetchDashboard = async () => {
    try {
      const res = await authAxios.get("/operator/dashboard");
      setDashboardStats(res.data);
    } catch { /* ignore */ }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || form.title.trim().length < 3) {
      toast.error("Title must be at least 3 characters"); return;
    }
    if (!form.message.trim() || form.message.trim().length < 5) {
      toast.error("Message must be at least 5 characters"); return;
    }
    setSending(true);
    try {
      const res = await authAxios.post("/operator/announcements", form);
      toast.success(`Announcement sent to ${res.data.recipients} subscriber(s)`);
      setShowDialog(false);
      setForm({ title: "", message: "", send_whatsapp: false, send_email: false, send_to_all: true });
      fetchAnnouncements();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send announcement");
    } finally {
      setSending(false);
    }
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
            onClick={() => setShowDialog(true)}
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
                          {new Date(item.created_at).toLocaleDateString("en-IN", {
                            day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
                          })}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Create Announcement Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>New Announcement</DialogTitle>
              <DialogDescription>
                Send a message to all your active subscribers
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSend} className="space-y-4">
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
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div>
                  <Label className="font-normal">Send via WhatsApp</Label>
                  <p className="text-xs text-slate-500">Also send this message via WhatsApp to all subscribers</p>
                </div>
                <Switch
                  checked={form.send_whatsapp}
                  onCheckedChange={(checked) => setForm(f => ({ ...f, send_whatsapp: checked }))}
                  data-testid="announcement-whatsapp-toggle"
                />
              </div>
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <div>
                  <Label className="font-normal">Send via Email</Label>
                  <p className="text-xs text-slate-500">Also send this message via email to all subscribers</p>
                </div>
                <Switch
                  checked={form.send_email}
                  onCheckedChange={(checked) => setForm(f => ({ ...f, send_email: checked }))}
                  data-testid="announcement-email-toggle"
                />
              </div>
              <DialogFooter>
                <Button variant="outline" type="button" onClick={() => setShowDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={sending} data-testid="send-announcement-btn">
                  <Send className="w-4 h-4 mr-2" />
                  {sending ? "Sending..." : "Send Announcement"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </OperatorLayout>
  );
};

export default OperatorAnnouncements;
