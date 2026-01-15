import React, { useState, useEffect, useCallback } from 'react';
import { 
  Plus, Edit2, Trash2, Search, Gift, Users, 
  TrendingUp, DollarSign, Gamepad2, RefreshCw,
  CheckCircle, XCircle, Clock, Percent
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function AdminPerksPage() {
  const [perks, setPerks] = useState([]);
  const [users, setUsers] = useState([]);
  const [games, setGames] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterActive, setFilterActive] = useState(null);
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedPerk, setSelectedPerk] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    referral_code: '',
    game_name: '',
    percent_bonus: 5,
    flat_bonus: 0,
    max_bonus: '',
    min_amount: '',
    valid_until: '',
    max_uses: '',
    is_active: true
  });

  // Auth token (you can get this from your auth context)
  const [token, setToken] = useState('');
  const [authForm, setAuthForm] = useState({ username: '', password: '' });
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const [perksRes, usersRes, gamesRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/admin/perks`, { headers }),
        fetch(`${API_URL}/api/v1/admin/users?limit=100`, { headers }),
        fetch(`${API_URL}/api/v1/admin/games`, { headers }),
        fetch(`${API_URL}/api/v1/admin/stats`, { headers })
      ]);

      if (!perksRes.ok) throw new Error('Failed to fetch perks');
      
      setPerks(await perksRes.json());
      setUsers(await usersRes.json());
      setGames(await gamesRes.json());
      setStats(await statsRes.json());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated, fetchData]);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      // First authenticate and get magic link
      const magicRes = await fetch(`${API_URL}/api/v1/auth/magic-link/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(authForm)
      });
      
      if (!magicRes.ok) {
        const err = await magicRes.json();
        throw new Error(err.detail?.message || 'Authentication failed');
      }
      
      const magicData = await magicRes.json();
      const magicToken = magicData.magic_link.split('token=')[1];
      
      // Consume the magic link to get access token
      const tokenRes = await fetch(`${API_URL}/api/v1/auth/magic-link/consume?token=${magicToken}`);
      if (!tokenRes.ok) throw new Error('Failed to get access token');
      
      const tokenData = await tokenRes.json();
      setToken(tokenData.access_token);
      setIsAuthenticated(true);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCreatePerk = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        game_name: formData.game_name || null,
        max_bonus: formData.max_bonus ? parseFloat(formData.max_bonus) : null,
        min_amount: formData.min_amount ? parseFloat(formData.min_amount) : null,
        max_uses: formData.max_uses ? parseInt(formData.max_uses) : null,
        valid_until: formData.valid_until ? new Date(formData.valid_until).toISOString() : null
      };

      const res = await fetch(`${API_URL}/api/v1/admin/perks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || 'Failed to create perk');
      }

      setShowCreateModal(false);
      resetForm();
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdatePerk = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        percent_bonus: formData.percent_bonus,
        flat_bonus: formData.flat_bonus,
        max_bonus: formData.max_bonus ? parseFloat(formData.max_bonus) : 0,
        min_amount: formData.min_amount ? parseFloat(formData.min_amount) : 0,
        max_uses: formData.max_uses ? parseInt(formData.max_uses) : 0,
        valid_until: formData.valid_until ? new Date(formData.valid_until).toISOString() : null,
        is_active: formData.is_active
      };

      const res = await fetch(`${API_URL}/api/v1/admin/perks/${selectedPerk.perk_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Failed to update perk');

      setShowEditModal(false);
      setSelectedPerk(null);
      resetForm();
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeletePerk = async (perkId) => {
    if (!window.confirm('Are you sure you want to delete this perk?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/perks/${perkId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) throw new Error('Failed to delete perk');
      fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const resetForm = () => {
    setFormData({
      referral_code: '',
      game_name: '',
      percent_bonus: 5,
      flat_bonus: 0,
      max_bonus: '',
      min_amount: '',
      valid_until: '',
      max_uses: '',
      is_active: true
    });
  };

  const openEditModal = (perk) => {
    setSelectedPerk(perk);
    setFormData({
      referral_code: perk.referral_code,
      game_name: perk.game_name || '',
      percent_bonus: perk.percent_bonus,
      flat_bonus: perk.flat_bonus,
      max_bonus: perk.max_bonus || '',
      min_amount: perk.min_amount || '',
      valid_until: perk.valid_until ? perk.valid_until.split('T')[0] : '',
      max_uses: perk.max_uses || '',
      is_active: perk.is_active
    });
    setShowEditModal(true);
  };

  const filteredPerks = perks.filter(perk => {
    const matchesSearch = !searchTerm || 
      perk.referral_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (perk.game_name && perk.game_name.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesActive = filterActive === null || perk.is_active === filterActive;
    return matchesSearch && matchesActive;
  });

  // Login form
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-8 w-full max-w-md border border-slate-700">
          <h1 className="text-2xl font-bold text-white mb-6 text-center">Admin Login</h1>
          {error && (
            <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Username</label>
              <input
                type="text"
                value={authForm.username}
                onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Enter username"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
              <input
                type="password"
                value={authForm.password}
                onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Enter password"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all"
            >
              Sign In
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-slate-800/50 backdrop-blur-xl border-b border-slate-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Gift className="w-8 h-8 text-purple-400" />
              <h1 className="text-2xl font-bold text-white">Referral Perks Admin</h1>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-5 border border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-500/20 rounded-lg">
                  <Users className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Total Users</p>
                  <p className="text-2xl font-bold text-white">{stats.total_users}</p>
                </div>
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-5 border border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-green-500/20 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Total Orders</p>
                  <p className="text-2xl font-bold text-white">{stats.total_orders}</p>
                </div>
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-5 border border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-500/20 rounded-lg">
                  <DollarSign className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Total Volume</p>
                  <p className="text-2xl font-bold text-white">${stats.total_order_amount?.toFixed(2)}</p>
                </div>
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-5 border border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-pink-500/20 rounded-lg">
                  <Gift className="w-6 h-6 text-pink-400" />
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Bonus Distributed</p>
                  <p className="text-2xl font-bold text-white">${stats.total_bonus_distributed?.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Perks Section */}
        <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 overflow-hidden">
          {/* Toolbar */}
          <div className="p-4 border-b border-slate-700 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search perks..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
              <select
                value={filterActive === null ? '' : filterActive.toString()}
                onChange={(e) => setFilterActive(e.target.value === '' ? null : e.target.value === 'true')}
                className="px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Status</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </div>
            <button
              onClick={() => { resetForm(); setShowCreateModal(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all"
            >
              <Plus className="w-5 h-5" />
              Create Perk
            </button>
          </div>

          {/* Table */}
          {loading ? (
            <div className="p-8 text-center text-slate-400">Loading...</div>
          ) : filteredPerks.length === 0 ? (
            <div className="p-8 text-center text-slate-400">No perks found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-700/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Referral Code</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Game</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Bonus</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Limits</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Usage</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {filteredPerks.map((perk) => (
                    <tr key={perk.perk_id} className="hover:bg-slate-700/30 transition-colors">
                      <td className="px-4 py-4">
                        <span className="font-mono text-purple-400 font-semibold">{perk.referral_code}</span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="text-slate-300">{perk.game_name || 'All Games'}</span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center px-2 py-1 bg-green-500/20 text-green-400 rounded text-sm">
                            <Percent className="w-3 h-3 mr-1" />
                            {perk.percent_bonus}%
                          </span>
                          {perk.flat_bonus > 0 && (
                            <span className="inline-flex items-center px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-sm">
                              +${perk.flat_bonus}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-400">
                        {perk.max_bonus && <div>Max: ${perk.max_bonus}</div>}
                        {perk.min_amount && <div>Min: ${perk.min_amount}</div>}
                      </td>
                      <td className="px-4 py-4">
                        <span className="text-slate-300">
                          {perk.current_uses}{perk.max_uses ? `/${perk.max_uses}` : ''}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        {perk.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 rounded text-sm">
                            <CheckCircle className="w-3 h-3" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 rounded text-sm">
                            <XCircle className="w-3 h-3" /> Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openEditModal(perk)}
                            className="p-2 hover:bg-slate-600 rounded-lg transition-colors text-slate-400 hover:text-white"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeletePerk(perk.perk_id)}
                            className="p-2 hover:bg-red-600/20 rounded-lg transition-colors text-slate-400 hover:text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Games Section */}
        <div className="mt-8 bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 overflow-hidden">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Gamepad2 className="w-5 h-5 text-purple-400" />
              Games & Bonus Rules
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
            {games.map((game) => (
              <div key={game.game_id} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white">{game.display_name}</h3>
                  <span className={`px-2 py-1 rounded text-xs ${game.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {game.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="text-sm text-slate-400 mb-3">{game.description}</p>
                <div className="text-sm text-slate-300">
                  <div>Amount: ${game.min_recharge_amount} - ${game.max_recharge_amount}</div>
                  <div className="mt-2">
                    <span className="text-slate-400">Default Bonus:</span>{' '}
                    <span className="text-green-400">{game.bonus_rules?.default?.percent_bonus || 0}%</span>
                    {game.bonus_rules?.default?.flat_bonus > 0 && (
                      <span className="text-blue-400 ml-1">+${game.bonus_rules.default.flat_bonus}</span>
                    )}
                  </div>
                  {game.bonus_rules?.first_recharge && (
                    <div>
                      <span className="text-slate-400">First Recharge:</span>{' '}
                      <span className="text-green-400">{game.bonus_rules.first_recharge.percent_bonus}%</span>
                      {game.bonus_rules.first_recharge.flat_bonus > 0 && (
                        <span className="text-blue-400 ml-1">+${game.bonus_rules.first_recharge.flat_bonus}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-lg">
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Create Referral Perk</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white">
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleCreatePerk} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Referral Code *</label>
                <select
                  value={formData.referral_code}
                  onChange={(e) => setFormData({ ...formData, referral_code: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  required
                >
                  <option value="">Select user's referral code</option>
                  {users.map((u) => (
                    <option key={u.user_id} value={u.referral_code}>
                      {u.referral_code} - {u.display_name} (@{u.username})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Game (optional)</label>
                <select
                  value={formData.game_name}
                  onChange={(e) => setFormData({ ...formData, game_name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                >
                  <option value="">All Games</option>
                  {games.map((g) => (
                    <option key={g.game_id} value={g.game_name}>{g.display_name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Percent Bonus (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formData.percent_bonus}
                    onChange={(e) => setFormData({ ...formData, percent_bonus: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Flat Bonus ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.flat_bonus}
                    onChange={(e) => setFormData({ ...formData, flat_bonus: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Max Bonus ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.max_bonus}
                    onChange={(e) => setFormData({ ...formData, max_bonus: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                    placeholder="No limit"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Min Amount ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.min_amount}
                    onChange={(e) => setFormData({ ...formData, min_amount: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                    placeholder="No minimum"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Valid Until</label>
                  <input
                    type="date"
                    value={formData.valid_until}
                    onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Max Uses</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.max_uses}
                    onChange={(e) => setFormData({ ...formData, max_uses: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                    placeholder="Unlimited"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700"
                />
                <label htmlFor="is_active" className="text-sm text-slate-300">Active</label>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all"
                >
                  Create Perk
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedPerk && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-lg">
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Edit Perk: {selectedPerk.referral_code}</h2>
              <button onClick={() => setShowEditModal(false)} className="text-slate-400 hover:text-white">
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleUpdatePerk} className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Percent Bonus (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formData.percent_bonus}
                    onChange={(e) => setFormData({ ...formData, percent_bonus: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Flat Bonus ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.flat_bonus}
                    onChange={(e) => setFormData({ ...formData, flat_bonus: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Max Bonus ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.max_bonus}
                    onChange={(e) => setFormData({ ...formData, max_bonus: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                    placeholder="No limit"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Min Amount ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.min_amount}
                    onChange={(e) => setFormData({ ...formData, min_amount: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                    placeholder="No minimum"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Valid Until</label>
                  <input
                    type="date"
                    value={formData.valid_until}
                    onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Max Uses</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.max_uses}
                    onChange={(e) => setFormData({ ...formData, max_uses: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                    placeholder="Unlimited"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="edit_is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700"
                />
                <label htmlFor="edit_is_active" className="text-sm text-slate-300">Active</label>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3 text-sm text-slate-400">
                <p>Current Usage: {selectedPerk.current_uses} / {selectedPerk.max_uses || '∞'}</p>
                <p>Game: {selectedPerk.game_name || 'All Games'}</p>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
