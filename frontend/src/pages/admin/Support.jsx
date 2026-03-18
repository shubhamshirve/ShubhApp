import { useState, useEffect, useCallback, useRef } from "react";
import { AdminLayout } from "../../components/Layout";
import { useAuth } from "../../App";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { toast } from "sonner";
import {
  MessageSquare, RefreshCw, Send, ChevronLeft,
  Clock, CheckCircle, XCircle, Loader2, Search,
  AlertTriangle, Filter
} from "lucide-react";

const PRIORITY_CONFIG = {
  low:    { label: "Low",    color: "bg-slate-100 text-slate-600" },
  medium: { label: "Medium", color: "bg-blue-100 text-blue-700" },
  high:   { label: "High",   color: "bg-amber-100 text-amber-700" },
  urgent: { label: "Urgent", color: "bg-red-100 text-red-700" },
};

const STATUS_CONFIG = {
  open:        { label: "Open",        color: "bg-yellow-100 text-yellow-700" },
  in_progress: { label: "In Progress", color: "bg-blue-100 text-blue-700" },
  resolved:    { label: "Resolved",    color: "bg-green-100 text-green-700" },
  closed:      { label: "Closed",      color: "bg-slate-100 text-slate-500" },
};

export default function AdminSupport() {
  const { authAxios } = useAuth();
  const [view, setView] = useState("list");
  const [tickets, setTickets] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [replyMsg, setReplyMsg] = useState("");
  const [replySending, setReplySending] = useState(false);
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [filters, setFilters] = useState({ status: "", priority: "", search: "" });
  const bottomRef = useRef(null);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: 50 });
      if (filters.status) params.set("status", filters.status);
      if (filters.priority) params.set("priority", filters.priority);
      if (filters.search) params.set("search", filters.search);
      const [ticketsRes, statsRes] = await Promise.all([
        authAxios.get(`/admin/support/tickets?${params}`),
        authAxios.get("/admin/support/tickets/stats"),
      ]);
      setTickets(ticketsRes.data.tickets || []);
      setTotal(ticketsRes.data.total || 0);
      setStats(statsRes.data || {});
    } catch { toast.error("Failed to load tickets"); }
    finally { setLoading(false); }
  }, [authAxios, filters]);

  const fetchTicketDetail = useCallback(async (ticketId) => {
    try {
      const res = await authAxios.get(`/admin/support/tickets/${ticketId}`);
      setSelectedTicket(res.data);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch { toast.error("Failed to load ticket"); }
  }, [authAxios]);

  useEffect(() => { fetchTickets(); }, [fetchTickets]);

  const handleReply = async () => {
    if (!replyMsg.trim()) return;
    setReplySending(true);
    try {
      const res = await authAxios.post(`/admin/support/tickets/${selectedTicket.id}/reply`, { message: replyMsg });
      setReplyMsg("");
      await fetchTicketDetail(selectedTicket.id);
      // Refresh ticket status in list
      setTickets(prev => prev.map(t => t.id === selectedTicket.id ? { ...t, status: res.data.ticket_status, reply_count: (t.reply_count || 0) + 1 } : t));
      toast.success("Reply sent");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send reply");
    } finally { setReplySending(false); }
  };

  const handleStatusChange = async (newStatus) => {
    setStatusUpdating(true);
    try {
      await authAxios.put(`/admin/support/tickets/${selectedTicket.id}/status`, { status: newStatus });
      setSelectedTicket(prev => ({ ...prev, status: newStatus }));
      setTickets(prev => prev.map(t => t.id === selectedTicket.id ? { ...t, status: newStatus } : t));
      toast.success(`Ticket status updated to ${newStatus.replace("_", " ")}`);
      fetchStats();
    } catch (err) {
      toast.error("Failed to update status");
    } finally { setStatusUpdating(false); }
  };

  const fetchStats = async () => {
    try {
      const res = await authAxios.get("/admin/support/tickets/stats");
      setStats(res.data || {});
    } catch {}
  };

  const openTicket = async (ticket) => {
    setView("detail");
    await fetchTicketDetail(ticket.id);
  };

  const StatusBadge = ({ status }) => {
    const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.open;
    return <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>{cfg.label}</span>;
  };

  const PriorityBadge = ({ priority }) => {
    const cfg = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.medium;
    return <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>{cfg.label}</span>;
  };

  return (
    <AdminLayout title="Support Tickets">
      <div className="space-y-5">

        {/* Stats */}
        {view === "list" && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Open", value: stats.open || 0, color: "text-yellow-600" },
              { label: "In Progress", value: stats.in_progress || 0, color: "text-blue-600" },
              { label: "Resolved", value: stats.resolved || 0, color: "text-green-600" },
              { label: "Urgent", value: stats.urgent || 0, color: "text-red-600" },
            ].map((s) => (
              <Card key={s.label} className="text-center" data-testid={`stat-${s.label.toLowerCase().replace(" ","-")}`}>
                <CardContent className="pt-4 pb-3">
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Back button for detail view */}
        {view === "detail" && (
          <button
            onClick={() => { setView("list"); setSelectedTicket(null); fetchTickets(); }}
            className="flex items-center gap-1 text-sm text-[#0066B2] hover:underline"
            data-testid="admin-back-to-list-btn"
          >
            <ChevronLeft className="w-4 h-4" /> Back to all tickets
          </button>
        )}

        {/* Filter Row */}
        {view === "list" && (
          <div className="flex gap-2 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="Search tickets..."
                value={filters.search}
                onChange={(e) => setFilters(p => ({ ...p, search: e.target.value }))}
                data-testid="admin-search-tickets"
              />
            </div>
            <select
              value={filters.status}
              onChange={(e) => setFilters(p => ({ ...p, status: e.target.value }))}
              className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white"
              data-testid="admin-status-filter"
            >
              <option value="">All Status</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
            <select
              value={filters.priority}
              onChange={(e) => setFilters(p => ({ ...p, priority: e.target.value }))}
              className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white"
              data-testid="admin-priority-filter"
            >
              <option value="">All Priority</option>
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <Button variant="ghost" size="sm" onClick={fetchTickets} data-testid="refresh-tickets-btn">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
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
                  <p className="text-slate-500 font-medium">No tickets found</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2" data-testid="admin-tickets-list">
                {tickets.map((ticket) => (
                  <Card
                    key={ticket.id}
                    className="cursor-pointer hover:shadow-md transition-shadow border border-slate-100"
                    onClick={() => openTicket(ticket)}
                    data-testid={`admin-ticket-row-${ticket.id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <StatusBadge status={ticket.status} />
                            <PriorityBadge priority={ticket.priority} />
                            {ticket.company_name && (
                              <span className="text-xs text-slate-500 font-medium">{ticket.company_name}</span>
                            )}
                          </div>
                          <p className="font-medium text-slate-900 truncate">{ticket.title}</p>
                          <p className="text-xs text-slate-400 mt-0.5 truncate">{ticket.description}</p>
                          <p className="text-xs text-slate-400 mt-1">
                            by {ticket.created_by_name} · {new Date(ticket.created_at).toLocaleString("en-IN")}
                            {ticket.reply_count > 0 && ` · ${ticket.reply_count} repl${ticket.reply_count === 1 ? "y" : "ies"}`}
                          </p>
                        </div>
                        {ticket.priority === "urgent" && <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-1" />}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {/* Ticket Detail */}
        {view === "detail" && selectedTicket && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Main conversation */}
            <div className="lg:col-span-2 space-y-4">
              <Card>
                <CardContent className="p-5">
                  <h3 className="text-lg font-semibold text-slate-900">{selectedTicket.title}</h3>
                  <div className="flex gap-2 mt-1 flex-wrap items-center">
                    <StatusBadge status={selectedTicket.status} />
                    <PriorityBadge priority={selectedTicket.priority} />
                    <span className="text-xs text-slate-400">{selectedTicket.company_name}</span>
                  </div>
                  <p className="mt-3 text-sm text-slate-700 bg-slate-50 rounded-lg p-3 whitespace-pre-wrap">{selectedTicket.description}</p>
                </CardContent>
              </Card>

              {/* Replies */}
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1" data-testid="admin-ticket-replies">
                {(selectedTicket.replies || []).map((reply) => {
                  const isAdmin = reply.author_role === "admin";
                  return (
                    <div key={reply.id} className={`flex ${isAdmin ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-sm rounded-2xl px-4 py-3 text-sm shadow-sm ${
                        isAdmin ? "bg-[#0066B2] text-white rounded-tr-none" : "bg-white border border-slate-200 rounded-tl-none"
                      }`}>
                        <p className={`font-medium text-xs mb-1 ${isAdmin ? "text-blue-100" : "text-slate-500"}`}>
                          {isAdmin ? "Support Team (Admin)" : reply.author_name}
                        </p>
                        <p className="whitespace-pre-wrap">{reply.message}</p>
                        <p className={`text-xs mt-1.5 ${isAdmin ? "text-blue-200" : "text-slate-400"}`}>
                          {new Date(reply.created_at).toLocaleString("en-IN")}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>

              {/* Reply Box */}
              {selectedTicket.status !== "closed" && (
                <Card data-testid="admin-reply-section">
                  <CardContent className="p-4">
                    <div className="flex gap-2">
                      <Textarea
                        value={replyMsg}
                        onChange={(e) => setReplyMsg(e.target.value)}
                        placeholder="Reply to operator..."
                        rows={2}
                        className="flex-1 resize-none"
                        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleReply(); } }}
                        data-testid="admin-reply-input"
                      />
                      <Button
                        onClick={handleReply}
                        disabled={replySending || !replyMsg.trim()}
                        className="bg-[#0066B2] hover:bg-[#004080] text-white self-end"
                        data-testid="admin-send-reply-btn"
                      >
                        {replySending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      </Button>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Replying as Admin. First reply auto-sets status to "In Progress".</p>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Side Panel */}
            <div className="space-y-4">
              <Card data-testid="ticket-info-panel">
                <CardHeader><CardTitle className="text-sm">Ticket Info</CardTitle></CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <p className="text-slate-500 text-xs">Operator</p>
                    <p className="font-medium">{selectedTicket.company_name || selectedTicket.operator_info?.company_name || "—"}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">Created by</p>
                    <p className="font-medium">{selectedTicket.created_by_name} ({selectedTicket.created_by_role})</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">Created</p>
                    <p className="font-medium">{new Date(selectedTicket.created_at).toLocaleString("en-IN")}</p>
                  </div>
                  {selectedTicket.operator_info?.email && (
                    <div>
                      <p className="text-slate-500 text-xs">Email</p>
                      <p className="font-medium text-xs">{selectedTicket.operator_info.email}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Status Management */}
              <Card data-testid="ticket-status-panel">
                <CardHeader><CardTitle className="text-sm">Change Status</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {["open", "in_progress", "resolved", "closed"].map((s) => {
                    const cfg = STATUS_CONFIG[s];
                    const isActive = selectedTicket.status === s;
                    return (
                      <button
                        key={s}
                        onClick={() => !isActive && handleStatusChange(s)}
                        disabled={isActive || statusUpdating}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                          isActive ? `${cfg.color} font-semibold cursor-default` : "border border-slate-100 hover:bg-slate-50"
                        }`}
                        data-testid={`status-btn-${s}`}
                      >
                        {cfg.label} {isActive && "✓"}
                      </button>
                    );
                  })}
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
