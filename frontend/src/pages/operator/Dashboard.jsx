import { useState, useEffect } from "react";
import { useAuth } from "../../App";
import { OperatorLayout } from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { toast } from "sonner";
import {
  Users,
  FileText,
  IndianRupee,
  Clock,
  AlertTriangle,
  CheckCircle,
  TrendingUp
} from "lucide-react";

const formatCurrency = (value) => `₹${Number(value || 0).toLocaleString("en-IN")}`;

const OperatorDashboard = () => {
  const { authAxios } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await authAxios.get("/operator/dashboard");
      setStats(response.data);
    } catch (error) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <OperatorLayout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
        </div>
      </OperatorLayout>
    );
  }

  const subscriberCards = [
    {
      title: "Total Subscribers",
      value: stats?.total_subscribers || 0,
      icon: Users,
      color: "bg-slate-100 text-slate-700"
    },
    {
      title: "Active Subscribers",
      value: stats?.active_subscribers || 0,
      icon: CheckCircle,
      color: "bg-emerald-100 text-emerald-700"
    }
  ];

  const invoiceCards = [
    {
      title: "Total Invoices",
      value: stats?.total_invoices || 0,
      icon: FileText,
      color: "bg-blue-100 text-blue-700"
    },
    {
      title: "Pending",
      value: stats?.pending_invoices || 0,
      icon: Clock,
      color: "bg-amber-100 text-amber-700"
    },
    {
      title: "Overdue",
      value: stats?.overdue_invoices || 0,
      icon: AlertTriangle,
      color: "bg-red-100 text-red-700"
    },
    {
      title: "Paid",
      value: stats?.paid_invoices || 0,
      icon: CheckCircle,
      color: "bg-emerald-100 text-emerald-700"
    }
  ];

  const monthlyValueCards = [
    {
      title: "Invoice Value This Month",
      value: formatCurrency(stats?.total_invoice_value_this_month),
      icon: FileText,
      color: "bg-indigo-100 text-indigo-700"
    },
    {
      title: "Received This Month",
      value: formatCurrency(stats?.total_value_received_this_month),
      icon: IndianRupee,
      color: "bg-emerald-100 text-emerald-700"
    },
    {
      title: "Pending This Month",
      value: formatCurrency(stats?.total_value_pending_this_month),
      icon: Clock,
      color: "bg-amber-100 text-amber-700"
    },
    {
      title: "Total Pending Value",
      value: formatCurrency(stats?.total_pending_value),
      icon: AlertTriangle,
      color: "bg-rose-100 text-rose-700"
    }
  ];

  return (
    <OperatorLayout title="Dashboard" isReadOnly={stats?.is_read_only}>
      <div className="space-y-8 animate-fade-in">
        {/* Subscription Status */}
        {stats?.status === "trial" && (
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Clock className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-blue-900">Trial Period Active</p>
                  <p className="text-sm text-blue-700">
                    Your trial expires on {stats?.trial_ends_at ? new Date(stats.trial_ends_at).toLocaleDateString() : "N/A"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Revenue Card */}
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-300 text-sm mb-1">Invoice Revenue (Collected)</p>
                <p className="text-4xl font-bold font-heading">
                  ₹{(stats?.total_revenue || 0).toLocaleString('en-IN')}
                </p>
                <p className="text-slate-400 text-xs mt-1">From paid subscriber invoices</p>
              </div>
              <div className="w-14 h-14 bg-white/10 rounded-xl flex items-center justify-center">
                <IndianRupee className="w-7 h-7" />
              </div>
            </div>
          </CardContent>
        </Card>

        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Monthly Value Snapshot</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {monthlyValueCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <Card key={index} className="kpi-card card-hover">
                  <div className={`w-10 h-10 rounded-lg ${card.color} flex items-center justify-center mb-3`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <p className="kpi-value text-2xl">{card.value}</p>
                  <p className="kpi-label">{card.title}</p>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Subscribers Section */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Subscribers</h2>
          <div className="grid grid-cols-2 gap-4">
            {subscriberCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <Card key={index} className="kpi-card card-hover" data-testid={`kpi-${card.title.toLowerCase().replace(/\s+/g, '-')}`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-lg ${card.color} flex items-center justify-center`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="kpi-value">{card.value}</p>
                      <p className="kpi-label">{card.title}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Invoices Section */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Invoices</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {invoiceCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <Card key={index} className="kpi-card card-hover" data-testid={`invoice-${card.title.toLowerCase()}`}>
                  <div className={`w-10 h-10 rounded-lg ${card.color} flex items-center justify-center mb-3`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <p className="kpi-value">{card.value}</p>
                  <p className="kpi-label">{card.title}</p>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Quick Actions */}
        <section>
          <h2 className="text-lg font-heading font-semibold text-slate-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card 
              className="p-4 hover:bg-slate-50 cursor-pointer transition-colors" 
              onClick={() => window.location.href = '/operator/subscribers'}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Add Subscriber</p>
                  <p className="text-sm text-slate-500">Create a new subscriber</p>
                </div>
              </div>
            </Card>
            
            <Card 
              className="p-4 hover:bg-slate-50 cursor-pointer transition-colors"
              onClick={() => window.location.href = '/operator/invoices'}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Create Invoice</p>
                  <p className="text-sm text-slate-500">Generate a new invoice</p>
                </div>
              </div>
            </Card>
            
            <Card 
              className="p-4 hover:bg-slate-50 cursor-pointer transition-colors"
              onClick={() => window.location.href = '/operator/reports'}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">View Reports</p>
                  <p className="text-sm text-slate-500">Revenue & GST reports</p>
                </div>
              </div>
            </Card>
          </div>
        </section>
      </div>
    </OperatorLayout>
  );
};

export default OperatorDashboard;
