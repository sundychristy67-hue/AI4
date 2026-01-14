import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Users, Gamepad2, ShoppingCart, TrendingUp, TrendingDown, AlertCircle, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const StatCard = ({ title, value, subtitle, icon: Icon, iconColor, valueColor }) => (
  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-all">
    <div className="flex items-center justify-between mb-2">
      <p className="text-gray-400 text-sm font-medium">{title}</p>
      <div className={`p-2 ${iconColor} rounded-lg`}>
        <Icon className="w-4 h-4" />
      </div>
    </div>
    <p className={`text-2xl font-bold ${valueColor || 'text-white'}`}>{value}</p>
    {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
  </div>
);

const AdminDashboard = () => {
  const { token } = useAuth();
  const [stats, setStats] = useState(null);
  const [attention, setAttention] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, attentionRes] = await Promise.all([
          axios.get(`${API}/admin/dashboard-stats`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          axios.get(`${API}/admin/attention-required`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);
        setStats(statsRes.data);
        setAttention(attentionRes.data.items || []);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
        <p className="text-gray-400 text-sm">System overview and metrics</p>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Clients"
          value={stats?.total_clients || 0}
          subtitle={`${stats?.active_clients || 0} active`}
          icon={Users}
          iconColor="bg-emerald-500/10 text-emerald-400"
        />
        <StatCard
          title="Pending Orders"
          value={stats?.pending_orders || 0}
          subtitle={`${stats?.pending_withdrawals || 0} withdrawals`}
          icon={ShoppingCart}
          iconColor="bg-yellow-500/10 text-yellow-400"
          valueColor="text-yellow-400"
        />
        <StatCard
          title="Total Ledger In"
          value={`$${stats?.total_ledger_in?.toFixed(2) || '0.00'}`}
          icon={TrendingUp}
          iconColor="bg-emerald-500/10 text-emerald-400"
          valueColor="text-emerald-400"
        />
        <StatCard
          title="Total Ledger Out"
          value={`$${stats?.total_ledger_out?.toFixed(2) || '0.00'}`}
          icon={TrendingDown}
          iconColor="bg-red-500/10 text-red-400"
          valueColor="text-red-400"
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Total Games"
          value={stats?.total_games || 0}
          icon={Gamepad2}
          iconColor="bg-blue-500/10 text-blue-400"
        />
        <StatCard
          title="Total Users"
          value={stats?.total_users || 0}
          subtitle={`${stats?.active_users || 0} active`}
          icon={Users}
          iconColor="bg-purple-500/10 text-purple-400"
        />
        <StatCard
          title="Referral Earnings"
          value={`$${stats?.total_earnings_distributed?.toFixed(2) || '0.00'}`}
          icon={TrendingUp}
          iconColor="bg-teal-500/10 text-teal-400"
          valueColor="text-teal-400"
        />
      </div>

      {/* Attention Required */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-500" />
            Attention Required
          </h3>
        </div>
        {attention.length === 0 ? (
          <p className="text-gray-500 text-center py-6">No items require attention</p>
        ) : (
          <div className="space-y-3">
            {attention.map((item) => (
              <Link
                key={item.id}
                to={item.action_url}
                className="flex items-center justify-between p-4 bg-black/50 border border-gray-800 rounded-lg hover:border-gray-700 transition-all group"
                data-testid={`attention-item-${item.id}`}
              >
                <div>
                  <p className="text-white font-medium">{item.title}</p>
                  <p className="text-xs text-gray-400 mt-1">{item.description}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    item.priority === 'high' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                    item.priority === 'medium' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                    'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                  }`}>
                    {item.priority}
                  </span>
                  <ArrowRight className="w-4 h-4 text-gray-500 group-hover:text-emerald-400 transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Link
          to="/admin/clients"
          className="py-4 px-4 bg-gray-900 border border-gray-800 rounded-xl text-center hover:border-emerald-500/50 transition-all group"
          data-testid="admin-quick-clients"
        >
          <Users className="w-6 h-6 mx-auto mb-2 text-gray-400 group-hover:text-emerald-400 transition-colors" />
          <span className="text-white text-sm font-medium">Clients</span>
        </Link>
        <Link
          to="/admin/orders"
          className="py-4 px-4 bg-gray-900 border border-gray-800 rounded-xl text-center hover:border-emerald-500/50 transition-all group"
          data-testid="admin-quick-orders"
        >
          <ShoppingCart className="w-6 h-6 mx-auto mb-2 text-gray-400 group-hover:text-emerald-400 transition-colors" />
          <span className="text-white text-sm font-medium">Orders</span>
        </Link>
        <Link
          to="/admin/games"
          className="py-4 px-4 bg-gray-900 border border-gray-800 rounded-xl text-center hover:border-emerald-500/50 transition-all group"
          data-testid="admin-quick-games"
        >
          <Gamepad2 className="w-6 h-6 mx-auto mb-2 text-gray-400 group-hover:text-emerald-400 transition-colors" />
          <span className="text-white text-sm font-medium">Games</span>
        </Link>
        <Link
          to="/admin/audit-logs"
          className="py-4 px-4 bg-gray-900 border border-gray-800 rounded-xl text-center hover:border-emerald-500/50 transition-all group"
          data-testid="admin-quick-logs"
        >
          <AlertCircle className="w-6 h-6 mx-auto mb-2 text-gray-400 group-hover:text-emerald-400 transition-colors" />
          <span className="text-white text-sm font-medium">Audit Logs</span>
        </Link>
      </div>
    </div>
  );
};

export default AdminDashboard;
