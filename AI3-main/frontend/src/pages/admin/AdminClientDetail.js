import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { ArrowLeft, User, Ban, CheckCircle, Lock, Unlock, Key, DollarSign, TrendingUp, TrendingDown, Plus, Eye, EyeOff, Shield } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminClientDetail = () => {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [clientData, setClientData] = useState(null);
  const [showCredModal, setShowCredModal] = useState(false);
  const [credForm, setCredForm] = useState({ game_id: '', game_user_id: '', game_password: '' });
  const [games, setGames] = useState([]);

  useEffect(() => {
    fetchClientDetail();
    fetchGames();
  }, [clientId]);

  const fetchClientDetail = async () => {
    try {
      const response = await axios.get(`${API}/admin/clients/${clientId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setClientData(response.data);
    } catch (error) {
      console.error('Failed to fetch client:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchGames = async () => {
    try {
      const response = await axios.get(`${API}/admin/games`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGames(response.data);
    } catch (error) {
      console.error('Failed to fetch games:', error);
    }
  };

  const handleStatusUpdate = async (newStatus) => {
    try {
      await axios.put(`${API}/admin/clients/${clientId}`, { status: newStatus }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchClientDetail();
    } catch (error) {
      alert('Failed to update status');
    }
  };

  const handleLockToggle = async (field, value) => {
    try {
      await axios.put(`${API}/admin/clients/${clientId}`, { [field]: value }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchClientDetail();
    } catch (error) {
      alert('Failed to update');
    }
  };

  const handleVisibilityChange = async (newLevel) => {
    try {
      await axios.put(`${API}/admin/clients/${clientId}`, { visibility_level: newLevel }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchClientDetail();
    } catch (error) {
      alert('Failed to update visibility');
    }
  };

  const handleAssignCredential = async () => {
    if (!credForm.game_id || !credForm.game_user_id || !credForm.game_password) {
      alert('Please fill all fields');
      return;
    }
    try {
      await axios.post(`${API}/admin/clients/${clientId}/credentials`, {
        client_id: clientId,
        ...credForm
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setShowCredModal(false);
      setCredForm({ game_id: '', game_user_id: '', game_password: '' });
      fetchClientDetail();
    } catch (error) {
      alert('Failed to assign credentials');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!clientData) {
    return <div className="text-white">Client not found</div>;
  }

  const { client, financial_summary, credentials, recent_transactions, recent_orders } = clientData;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/admin/clients')}
          className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-6 h-6 text-gray-400" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">{client.display_name}</h1>
          <p className="text-gray-400 text-sm">{client.client_id}</p>
        </div>
      </div>

      {/* Client Info & Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Info Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-gray-400" />
            Client Information
          </h3>
          <div className="space-y-3">
            <div>
              <p className="text-gray-500 text-xs">Status</p>
              <span className={`px-2 py-1 text-xs rounded-full ${
                client.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' :
                client.status === 'frozen' ? 'bg-yellow-500/10 text-yellow-400' :
                'bg-red-500/10 text-red-400'
              }`}>
                {client.status}
              </span>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Referral Code</p>
              <p className="text-emerald-400 font-mono">{client.referral_code}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Referred By</p>
              <p className="text-white">{client.referred_by_code || 'None'}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Joined</p>
              <p className="text-white text-sm">{new Date(client.created_at).toLocaleString()}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 space-y-2">
            <h4 className="text-gray-400 text-sm font-medium">Actions</h4>
            <div className="flex flex-wrap gap-2">
              {client.status !== 'banned' && (
                <button
                  onClick={() => handleStatusUpdate('banned')}
                  className="px-3 py-1.5 bg-red-500/10 text-red-400 rounded-lg text-sm hover:bg-red-500/20 transition flex items-center gap-1"
                >
                  <Ban className="w-4 h-4" /> Ban
                </button>
              )}
              {client.status === 'banned' && (
                <button
                  onClick={() => handleStatusUpdate('active')}
                  className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/20 transition flex items-center gap-1"
                >
                  <CheckCircle className="w-4 h-4" /> Unban
                </button>
              )}
              <button
                onClick={() => handleLockToggle('withdraw_locked', !client.withdraw_locked)}
                className={`px-3 py-1.5 rounded-lg text-sm transition flex items-center gap-1 ${
                  client.withdraw_locked ? 'bg-yellow-500/10 text-yellow-400' : 'bg-gray-700 text-gray-300'
                }`}
              >
                {client.withdraw_locked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                {client.withdraw_locked ? 'Unlock Withdraw' : 'Lock Withdraw'}
              </button>
            </div>
          </div>

          {/* Visibility Settings */}
          <div className="mt-6 space-y-2">
            <h4 className="text-gray-400 text-sm font-medium flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Portal Visibility
            </h4>
            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={() => handleVisibilityChange('full')}
                className={`px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  client.visibility_level === 'full' || !client.visibility_level
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <Eye className="w-4 h-4" />
                Full Access
              </button>
              <button
                onClick={() => handleVisibilityChange('summary')}
                className={`px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  client.visibility_level === 'summary'
                    ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <Eye className="w-4 h-4" />
                Summary Only
              </button>
              <button
                onClick={() => handleVisibilityChange('hidden')}
                className={`px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  client.visibility_level === 'hidden'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <EyeOff className="w-4 h-4" />
                Hidden
              </button>
            </div>
            <p className="text-gray-500 text-xs mt-1">
              Controls what the client can see in their portal
            </p>
          </div>
        </div>

        {/* Financial Summary */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-gray-400" />
            Financial Summary
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-black border border-emerald-500/20 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Total In</p>
              <p className="text-emerald-400 font-bold">${financial_summary.total_in?.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-red-500/20 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Total Out</p>
              <p className="text-red-400 font-bold">${financial_summary.total_out?.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-gray-700 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Net Balance</p>
              <p className="text-white font-bold">${financial_summary.net_balance?.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-blue-500/20 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Referral Earnings</p>
              <p className="text-blue-400 font-bold">${financial_summary.referral_earnings?.toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Credentials */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Key className="w-5 h-5 text-gray-400" />
              Game Credentials
            </h3>
            <button
              onClick={() => setShowCredModal(true)}
              className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg hover:bg-emerald-500/20 transition"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          {credentials.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No credentials assigned</p>
          ) : (
            <div className="space-y-2">
              {credentials.map((cred) => (
                <div key={cred.id} className="bg-black border border-gray-700 rounded-lg p-3">
                  <p className="text-white font-medium">{cred.game_name}</p>
                  <p className="text-gray-500 text-xs mt-1">
                    {cred.is_active ? (
                      <span className="text-emerald-400">Active</span>
                    ) : (
                      <span className="text-red-400">Inactive / Not Set</span>
                    )}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4">Recent Transactions</h3>
        {recent_transactions.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No transactions</p>
        ) : (
          <div className="space-y-2">
            {recent_transactions.map((tx) => (
              <div key={tx.transaction_id} className="flex items-center justify-between p-3 bg-black border border-gray-800 rounded-lg">
                <div className="flex items-center gap-3">
                  {tx.type === 'IN' ? (
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-400" />
                  )}
                  <div>
                    <p className="text-white text-sm">{tx.type}</p>
                    <p className="text-gray-500 text-xs">{new Date(tx.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <p className={`font-bold ${tx.type === 'OUT' ? 'text-red-400' : 'text-emerald-400'}`}>
                  ${tx.amount?.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Credential Modal */}
      {showCredModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowCredModal(false)}>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="text-xl font-bold text-white mb-4">Assign Credentials</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Game</label>
                <select
                  value={credForm.game_id}
                  onChange={(e) => setCredForm({ ...credForm, game_id: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                >
                  <option value="">Select Game</option>
                  {games.map(game => (
                    <option key={game.id} value={game.id}>{game.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Username</label>
                <input
                  type="text"
                  value={credForm.game_user_id}
                  onChange={(e) => setCredForm({ ...credForm, game_user_id: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Password</label>
                <input
                  type="text"
                  value={credForm.game_password}
                  onChange={(e) => setCredForm({ ...credForm, game_password: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowCredModal(false)}
                  className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssignCredential}
                  className="flex-1 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition"
                >
                  Assign
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminClientDetail;
