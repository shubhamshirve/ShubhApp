import { useState, useEffect, useCallback, useRef } from "react";
import { OperatorLayout } from "../../components/Layout";
import { useAuth } from "../../App";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { toast } from "sonner";
import {
  Plus, MessageSquare, RefreshCw, Send, ChevronLeft,
  Clock, CheckCircle, XCircle, AlertTriangle, Loader2
} from "lucide-react";

const PRIORITY_CONFIG = {
  low:    { label: "Low",    color: "bg-slate-100 text-slate-600" },
  medium: { label: "Medium", color: "bg-blue-100 text-blue-700" },
  high:   { label: "High",   color: "bg-amber-100 text-amber-700" },
  urgent: { label: "Urgent", color: "bg-red-100 text-red-700" },
};

const STATUS_CONFIG = {
  open:        { label: "Open",        icon: Clock,        color: "bg-yellow-100 text-yellow-700" },
  in_progress: { label: "In Progress", icon: Loader2,      color: "bg-blue-100 text-blue-700" },
  resolved:    { label: "Resolved",    icon: CheckCircle,  color: "bg-green-100 text-green-700" },
  closed:      { label: "Closed",      icon: XCircle,      color: "bg-slate-100 text-slate-500" },
};

export default function OperatorSupport() {
  const { authAxios, user } = useAuth();
  const [view, setView] = useState("list"); // "list" | "create" | "detail"
  const [tickets, setTickets] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [replyMsg, setReplyMsg] = useState("");
  const [replySending, setReplySending] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [form, setForm] = useState({ title: "", description: "", priority: "medium" });
  const [creating, setCreating] = useState(false);
  const bottomRef = useRef(null);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: 30 });
      if (statusFilter) params.set("status", statusFilter);
      const res = await authAxios.get(`/operator/support/tickets?${params}`);
      setTickets(res.data.tickets || []);
      setTotal(res.data.total || 0);
    } catch { toast.error("Failed to load tickets"); }
    finally { setLoading(false); }
  }, [authAxios, statusFilter]);

  const fetchTicketDetail = useCallback(async (ticketId) => {
    try {
      const res = await authAxios.get(`/operator/support/tickets/${ticketId}`);
      setSelectedTicket(res.data);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch { toast.error("Failed to load ticket"); }
  }, [authAxios]);

  useEffect(() => { fetchTickets(); }, [fetchTickets]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) {
      toast.error("Title and description are required");
      return;
    }
    setCreating(true);
    try {
      await authAxios.post("/operator/support/tickets", form);
      toast.success("Ticket created successfully!");
      setForm({ title: "", description: "", priority: "medium" });
      setView("list");
      fetchTickets();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create ticket");
    } finally { setCreating(false); }
  };

  const handleReply = async () => {
    if (!replyMsg.trim()) return;
    setReplySending(true);
    try {
      const res = await authAxios.post(`/operator/support/tickets/${selectedTicket.id}/reply`, { message: replyMsg });
      setReplyMsg("");
      await fetchTicketDetail(selectedTicket.id);
      toast.success("Reply sent");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send reply");
    } finally { setReplySending(false); }
  };

  const openTicket = async (ticket) => {
    setView("detail");
    await fetchTicketDetail(ticket.id);
  };

  const StatusBadge = ({ status }) => {
    const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.open;
    return <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>{cfg.label}</span>;
  };

  const PriorityBadge = ({ priority }) => {
    const cfg = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.medium;
    return <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>{cfg.label}</span>;
  };

  return (
    <OperatorLayout title="Support">
      <div className="max-w-3xl mx-auto space-y-4">

        {/* Header */}
        {view === "list" && (
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Support Tickets</h2>
              <p className="text-sm text-slate-500">{total} ticket{total !== 1 ? "s" : ""}</p>
            </div>
            <div className="flex gap-2">
              {/* Status filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 bg-white"
                data-testid="support-status-filter"
              >
                <option value="">All Status</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
              <Button
                onClick={() => setView("create")}
                className="bg-[#0066B2] hover:bg-[#004080] text-white"
                data-testid="new-ticket-btn"
              >
                <Plus className="w-4 h-4 mr-1" /> New Ticket
              </Button>
            </div>
          </div>
        )}

        {/* Detail Back */}
        {view === "detail" && (
          <button
            onClick={() => { setView("list"); setSelectedTicket(null); fetchTickets(); }}
            className="flex items-center gap-1 text-sm text-[#0066B2] hover:underline"
            data-testid="back-to-list-btn"
          >
            <ChevronLeft className="w-4 h-4" /> Back to tickets
          </button>
        )}

        {/* Create back */}
        {view === "create" && (
          <button
            onClick={() => setView("list")}
            className="flex items-center gap-1 text-sm text-[#0066B2] hover:underline"
          >
            <ChevronLeft className="w-4 h-4" /> Back to tickets
          </button>
        )}

        {/* Create Form */}
        {view === "create" && (
          <Card data-testid="create-ticket-form">
            <CardHeader>
              <CardTitle className="text-base">New Support Ticket</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Title <span className="text-red-500">*</span></label>
                  <Input
                    value={form.title}
                    onChange={(e) => setForm(p => ({ ...p, title: e.target.value }))}
                    placeholder="Brief summary of your issue"
                    required
                    data-testid="ticket-title-input"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Description <span className="text-red-500">*</span></label>
                  <Textarea
                    value={form.description}
                    onChange={(e) => setForm(p => ({ ...p, description: e.target.value }))}
                    placeholder="Describe your issue in detail..."
                    rows={5}
                    required
                    data-testid="ticket-description-input"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Priority</label>
                  <div className="flex gap-2 flex-wrap">
                    {["low", "medium", "high", "urgent"].map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setForm(prev => ({ ...prev, priority: p }))}
                        className={`px-3 py-1 text-sm rounded-full border transition-all ${
                          form.priority === p ? "border-[#0066B2] bg-[#0066B2] text-white" : "border-slate-200 hover:border-slate-300 text-slate-600"
                        }`}
                        data-testid={`priority-${p}`}
                      >
                        {PRIORITY_CONFIG[p].label}
                      </button>
                    ))}
                  </div>
                </div>
                <Button type="submit" disabled={creating} className="bg-[#0066B2] hover:bg-[#004080] text-white" data-testid="create-ticket-submit">
                  {creating ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                  Submit Ticket
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Ticket List */}
        {view === "list" && (
          <>
            {loading ? (
              <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 animate-spin text-blue-600" /></div>
            ) : tickets.length === 0 ? (
              <Card>
                <CardContent className="py-16 text-center">
                  <MessageSquare className="w-10 h-10 mx-auto text-slate-300 mb-3" />
                  <p className="text-slate-500 font-medium">No tickets yet</p>
                  <p className="text-slate-400 text-sm mt-1">Click "New Ticket" to raise a support request</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2" data-testid="tickets-list">
                {tickets.map((ticket) => (
                  <Card
                    key={ticket.id}
                    className="cursor-pointer hover:shadow-md transition-shadow border border-slate-100"
                    onClick={() => openTicket(ticket)}
                    data-testid={`ticket-row-${ticket.id}`}
                  >
                    <CardContent className="p-4 flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <StatusBadge status={ticket.status} />
                          <PriorityBadge priority={ticket.priority} />
                        </div>
                        <p className="font-medium text-slate-900 truncate">{ticket.title}</p>
                        <p className="text-xs text-slate-400 mt-1">
                          {new Date(ticket.created_at).toLocaleString("en-IN")}
                          {ticket.reply_count > 0 && ` · ${ticket.reply_count} repl${ticket.reply_count === 1 ? "y" : "ies"}`}
                        </p>
                      </div>
                      <MessageSquare className="w-4 h-4 text-slate-400 shrink-0 mt-1" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {/* Ticket Detail */}
        {view === "detail" && selectedTicket && (
          <div className="space-y-4" data-testid="ticket-detail">
            <Card>
              <CardContent className="p-5">
                <div className="flex items-start gap-3 justify-between flex-wrap">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-slate-900">{selectedTicket.title}</h3>
                    <div className="flex gap-2 mt-1 flex-wrap">
                      <StatusBadge status={selectedTicket.status} />
                      <PriorityBadge priority={selectedTicket.priority} />
                      <span className="text-xs text-slate-400">{new Date(selectedTicket.created_at).toLocaleString("en-IN")}</span>
                    </div>
                  </div>
                </div>
                <p className="mt-3 text-sm text-slate-700 bg-slate-50 rounded-lg p-3 whitespace-pre-wrap">{selectedTicket.description}</p>
              </CardContent>
            </Card>

            {/* Replies */}
            <div className="space-y-3" data-testid="ticket-replies">
              {(selectedTicket.replies || []).map((reply) => {
                const isAdmin = reply.author_role === "admin";
                return (
                  <div key={reply.id} className={`flex ${isAdmin ? "justify-start" : "justify-end"}`}>
                    <div className={`max-w-sm rounded-2xl px-4 py-3 text-sm shadow-sm ${
                      isAdmin ? "bg-white border border-slate-200 rounded-tl-none" : "bg-[#0066B2] text-white rounded-tr-none"
                    }`}>
                      <p className={`font-medium text-xs mb-1 ${isAdmin ? "text-slate-500" : "text-blue-100"}`}>
                        {isAdmin ? "Support Team" : reply.author_name}
                      </p>
                      <p className="whitespace-pre-wrap">{reply.message}</p>
                      <p className={`text-xs mt-1.5 ${isAdmin ? "text-slate-400" : "text-blue-200"}`}>
                        {new Date(reply.created_at).toLocaleString("en-IN")}
                      </p>
                    </div>
                  </div>
                );
              })}
              <div ref={bottomRef} />
            </div>

            {/* Reply Input */}
            {selectedTicket.status !== "closed" && (
              <Card data-testid="reply-section">
                <CardContent className="p-4">
                  <div className="flex gap-2">
                    <Textarea
                      value={replyMsg}
                      onChange={(e) => setReplyMsg(e.target.value)}
                      placeholder="Type your reply..."
                      rows={2}
                      className="flex-1 resize-none"
                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleReply(); } }}
                      data-testid="reply-input"
                    />
                    <Button
                      onClick={handleReply}
                      disabled={replySending || !replyMsg.trim()}
                      className="bg-[#0066B2] hover:bg-[#004080] text-white self-end"
                      data-testid="send-reply-btn"
                    >
                      {replySending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </Button>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Press Enter to send, Shift+Enter for new line</p>
                </CardContent>
              </Card>
            )}

            {selectedTicket.status === "closed" && (
              <div className="text-center py-4 text-sm text-slate-400 flex items-center justify-center gap-2">
                <XCircle className="w-4 h-4" /> This ticket is closed
              </div>
            )}
          </div>
        )}
      </div>
    </OperatorLayout>
  );
}
