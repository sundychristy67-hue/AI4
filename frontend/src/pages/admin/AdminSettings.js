import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { 
  Settings, Users, Gift, Shield, Save, RefreshCw, Plus, Trash2, 
  Edit2, X, ChevronDown, ChevronUp, AlertTriangle, Check, Percent,
  Target, Award, Lock
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminSettings = () => {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('general');
  const [expandedSection, setExpandedSection] = useState(null);
  
  // Edit modals
  const [showTierModal, setShowTierModal] = useState(false);
  const [showMilestoneModal, setShowMilestoneModal] = useState(false);
  const [editingTier, setEditingTier] = useState(null);
  const [editingMilestone, setEditingMilestone] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/admin/settings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      alert('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const saveGlobalSettings = async (updates) => {
    setSaving(true);
    try {
      await axios.put(`${API}/admin/settings`, updates, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchSettings();
      alert('Settings saved successfully');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const saveTiers = async (tiers) => {
    setSaving(true);
    try {
      await axios.put(`${API}/admin/settings/referral-tiers`, tiers, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchSettings();
      alert('Tiers saved successfully');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to save tiers');
    } finally {
      setSaving(false);
    }
  };

  const deleteTier = async (tierNumber) => {
    if (!confirm('Are you sure you want to delete this tier?')) return;
    setSaving(true);
    try {
      await axios.delete(`${API}/admin/settings/referral-tiers/${tierNumber}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchSettings();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete tier');
    } finally {
      setSaving(false);
    }
  };

  const saveMilestones = async (milestones) => {
    setSaving(true);
    try {
      await axios.put(`${API}/admin/settings/bonus-milestones`, milestones, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchSettings();
      alert('Milestones saved successfully');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to save milestones');
    } finally {
      setSaving(false);
    }
  };

  const deleteMilestone = async (milestoneNumber) => {
    if (!confirm('Are you sure you want to delete this milestone?')) return;
    setSaving(true);
    try {
      await axios.delete(`${API}/admin/settings/bonus-milestones/${milestoneNumber}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchSettings();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete milestone');
    } finally {
      setSaving(false);
    }
  };

  const saveAntiFraud = async (updates) => {
    setSaving(true);
    try {
      await axios.put(`${API}/admin/settings/anti-fraud`, updates, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchSettings();
      alert('Anti-fraud settings saved');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to save anti-fraud settings');
    } finally {
      setSaving(false);
    }
  };

  const resetToDefaults = async (section) => {
    if (!confirm(`Reset ${section} settings to defaults? This cannot be undone.`)) return;
    setSaving(true);
    try {
      await axios.post(`${API}/admin/settings/reset-defaults?section=${section}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchSettings();
      alert('Settings reset to defaults');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reset settings');
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'tiers', label: 'Referral Tiers', icon: Award },
    { id: 'milestones', label: 'Bonus Milestones', icon: Gift },
    { id: 'antifraud', label: 'Anti-Fraud', icon: Shield },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Platform Settings</h1>
          <p className="text-gray-400 text-sm">Configure referral rewards, bonuses, and anti-fraud rules</p>
        </div>
        <button
          onClick={fetchSettings}
          disabled={saving}
          className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${saving ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-gray-800 pb-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              activeTab === tab.id
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        {activeTab === 'general' && (
          <GeneralSettings 
            settings={settings} 
            onSave={saveGlobalSettings}
            onReset={() => resetToDefaults('all')}
            saving={saving}
          />
        )}
        
        {activeTab === 'tiers' && (
          <ReferralTiersSettings
            tiers={settings?.referral_tier_config?.tiers || []}
            onSave={saveTiers}
            onDelete={deleteTier}
            onReset={() => resetToDefaults('tiers')}
            saving={saving}
            showModal={showTierModal}
            setShowModal={setShowTierModal}
            editingTier={editingTier}
            setEditingTier={setEditingTier}
          />
        )}
        
        {activeTab === 'milestones' && (
          <BonusMilestonesSettings
            milestones={settings?.bonus_rules?.milestones || []}
            enabled={settings?.bonus_rules?.enabled !== false}
            onSave={saveMilestones}
            onDelete={deleteMilestone}
            onReset={() => resetToDefaults('milestones')}
            saving={saving}
            showModal={showMilestoneModal}
            setShowModal={setShowMilestoneModal}
            editingMilestone={editingMilestone}
            setEditingMilestone={setEditingMilestone}
          />
        )}
        
        {activeTab === 'antifraud' && (
          <AntiFraudSettings
            antiFraud={settings?.anti_fraud || {}}
            onSave={saveAntiFraud}
            onReset={() => resetToDefaults('antifraud')}
            saving={saving}
          />
        )}
      </div>
    </div>
  );
};

// ==================== GENERAL SETTINGS ====================

const GeneralSettings = ({ settings, onSave, onReset, saving }) => {
  const [form, setForm] = useState({
    withdrawals_enabled: settings?.withdrawals_enabled ?? true,
    bonus_system_enabled: settings?.bonus_system_enabled ?? true,
    referral_system_enabled: settings?.referral_system_enabled ?? true,
    min_withdrawal_amount: settings?.min_withdrawal_amount ?? 20,
    max_withdrawal_amount: settings?.max_withdrawal_amount ?? 10000,
  });

  const handleSave = () => {
    onSave(form);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">General Settings</h3>
        <button
          onClick={onReset}
          className="text-sm text-gray-400 hover:text-red-400 flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" /> Reset All
        </button>
      </div>

      {/* Feature Toggles */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide">Feature Toggles</h4>
        
        <ToggleSwitch
          label="Withdrawals Enabled"
          description="Allow clients to withdraw funds"
          value={form.withdrawals_enabled}
          onChange={(v) => setForm({...form, withdrawals_enabled: v})}
        />
        
        <ToggleSwitch
          label="Bonus System Enabled"
          description="Enable bonus wallet and milestone rewards"
          value={form.bonus_system_enabled}
          onChange={(v) => setForm({...form, bonus_system_enabled: v})}
        />
        
        <ToggleSwitch
          label="Referral System Enabled"
          description="Enable referral codes and commissions"
          value={form.referral_system_enabled}
          onChange={(v) => setForm({...form, referral_system_enabled: v})}
        />
      </div>

      {/* Withdrawal Limits */}
      <div className="space-y-4 pt-4 border-t border-gray-800">
        <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide">Withdrawal Limits</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Minimum Withdrawal ($)</label>
            <input
              type="number"
              value={form.min_withdrawal_amount}
              onChange={(e) => setForm({...form, min_withdrawal_amount: parseFloat(e.target.value) || 0})}
              className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              min="0"
              step="1"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Maximum Withdrawal ($)</label>
            <input
              type="number"
              value={form.max_withdrawal_amount}
              onChange={(e) => setForm({...form, max_withdrawal_amount: parseFloat(e.target.value) || 0})}
              className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              min="0"
              step="100"
            />
          </div>
        </div>
      </div>

      <div className="pt-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-3 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
};

// ==================== REFERRAL TIERS ====================

const ReferralTiersSettings = ({ tiers, onSave, onDelete, onReset, saving, showModal, setShowModal, editingTier, setEditingTier }) => {
  const [localTiers, setLocalTiers] = useState([...tiers]);

  useEffect(() => {
    setLocalTiers([...tiers]);
  }, [tiers]);

  const openAddModal = () => {
    setEditingTier({
      name: '',
      min_referrals: Math.max(...localTiers.map(t => t.min_referrals || 0), 0) + 10,
      commission_percentage: 5.0
    });
    setShowModal(true);
  };

  const openEditModal = (tier) => {
    setEditingTier({...tier});
    setShowModal(true);
  };

  const saveTierModal = () => {
    if (!editingTier.name || editingTier.commission_percentage < 0) {
      alert('Please fill in all fields');
      return;
    }

    let newTiers;
    if (editingTier.tier_number !== undefined) {
      // Editing existing
      newTiers = localTiers.map(t => 
        t.tier_number === editingTier.tier_number ? editingTier : t
      );
    } else {
      // Adding new
      newTiers = [...localTiers, editingTier];
    }
    
    onSave(newTiers);
    setShowModal(false);
    setEditingTier(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Referral Tiers</h3>
          <p className="text-sm text-gray-400">Configure commission percentages for each tier</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            className="text-sm text-gray-400 hover:text-red-400 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Reset
          </button>
          <button
            onClick={openAddModal}
            className="px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Tier
          </button>
        </div>
      </div>

      {/* Tiers Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Tier</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Name</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Min Referrals</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Commission %</th>
              <th className="text-right px-4 py-3 text-gray-400 font-medium text-sm">Actions</th>
            </tr>
          </thead>
          <tbody>
            {localTiers.sort((a, b) => a.min_referrals - b.min_referrals).map((tier, idx) => (
              <tr key={tier.tier_number} className="border-b border-gray-800 hover:bg-gray-800/50">
                <td className="px-4 py-3">
                  <span className="px-2 py-1 bg-gray-800 text-gray-300 rounded text-sm">
                    Tier {idx}
                  </span>
                </td>
                <td className="px-4 py-3 text-white font-medium">{tier.name}</td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-1 text-gray-300">
                    <Target className="w-4 h-4 text-gray-500" />
                    {tier.min_referrals}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-1 text-emerald-400 font-bold">
                    <Percent className="w-4 h-4" />
                    {tier.commission_percentage}%
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => openEditModal(tier)}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    {tier.min_referrals > 0 && (
                      <button
                        onClick={() => onDelete(tier.tier_number)}
                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Tier Edit Modal */}
      {showModal && editingTier && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">
                {editingTier.tier_number !== undefined ? 'Edit Tier' : 'Add New Tier'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Tier Name</label>
                <input
                  type="text"
                  value={editingTier.name}
                  onChange={(e) => setEditingTier({...editingTier, name: e.target.value})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  placeholder="e.g., Diamond"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">Min Referrals Required</label>
                <input
                  type="number"
                  value={editingTier.min_referrals}
                  onChange={(e) => setEditingTier({...editingTier, min_referrals: parseInt(e.target.value) || 0})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="0"
                  disabled={editingTier.tier_number === 0}
                />
                {editingTier.tier_number === 0 && (
                  <p className="text-xs text-gray-500 mt-1">Base tier cannot change min referrals</p>
                )}
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">Commission Percentage (%)</label>
                <input
                  type="number"
                  value={editingTier.commission_percentage}
                  onChange={(e) => setEditingTier({...editingTier, commission_percentage: parseFloat(e.target.value) || 0})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="0"
                  max="100"
                  step="0.5"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={saveTierModal}
                  disabled={saving}
                  className="flex-1 py-3 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Tier'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ==================== BONUS MILESTONES ====================

const BonusMilestonesSettings = ({ milestones, enabled, onSave, onDelete, onReset, saving, showModal, setShowModal, editingMilestone, setEditingMilestone }) => {
  const [localMilestones, setLocalMilestones] = useState([...milestones]);

  useEffect(() => {
    setLocalMilestones([...milestones]);
  }, [milestones]);

  const openAddModal = () => {
    setEditingMilestone({
      referrals_required: Math.max(...localMilestones.map(m => m.referrals_required || 0), 0) + 5,
      bonus_amount: 2.0,
      bonus_type: 'bonus',
      description: ''
    });
    setShowModal(true);
  };

  const openEditModal = (milestone) => {
    setEditingMilestone({...milestone});
    setShowModal(true);
  };

  const saveMilestoneModal = () => {
    if (!editingMilestone.bonus_amount || editingMilestone.referrals_required < 1) {
      alert('Please fill in all fields');
      return;
    }

    let newMilestones;
    if (editingMilestone.milestone_number !== undefined) {
      newMilestones = localMilestones.map(m => 
        m.milestone_number === editingMilestone.milestone_number ? editingMilestone : m
      );
    } else {
      newMilestones = [...localMilestones, editingMilestone];
    }
    
    onSave(newMilestones);
    setShowModal(false);
    setEditingMilestone(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Bonus Milestones</h3>
          <p className="text-sm text-gray-400">Configure bonus rewards at referral milestones</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            className="text-sm text-gray-400 hover:text-red-400 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Reset
          </button>
          <button
            onClick={openAddModal}
            className="px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Milestone
          </button>
        </div>
      </div>

      {/* Status Banner */}
      <div className={`p-4 rounded-lg border ${enabled ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-red-500/10 border-red-500/20'}`}>
        <div className="flex items-center gap-2">
          {enabled ? (
            <>
              <Check className="w-5 h-5 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Bonus System Active</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <span className="text-red-400 font-medium">Bonus System Disabled</span>
            </>
          )}
        </div>
      </div>

      {/* Milestones Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">#</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Referrals Required</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Bonus Amount</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Type</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Description</th>
              <th className="text-right px-4 py-3 text-gray-400 font-medium text-sm">Actions</th>
            </tr>
          </thead>
          <tbody>
            {localMilestones.sort((a, b) => a.referrals_required - b.referrals_required).map((milestone, idx) => (
              <tr key={milestone.milestone_number} className="border-b border-gray-800 hover:bg-gray-800/50">
                <td className="px-4 py-3">
                  <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-sm">
                    M{idx + 1}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-1 text-white font-medium">
                    <Users className="w-4 h-4 text-gray-500" />
                    {milestone.referrals_required}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-emerald-400 font-bold">${milestone.bonus_amount}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    milestone.bonus_type === 'bonus' 
                      ? 'bg-purple-500/20 text-purple-400' 
                      : 'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {milestone.bonus_type === 'bonus' ? 'Bonus Wallet' : 'Real Wallet'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-sm">{milestone.description}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => openEditModal(milestone)}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(milestone.milestone_number)}
                      className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
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

      {/* Milestone Edit Modal */}
      {showModal && editingMilestone && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">
                {editingMilestone.milestone_number !== undefined ? 'Edit Milestone' : 'Add New Milestone'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Referrals Required</label>
                <input
                  type="number"
                  value={editingMilestone.referrals_required}
                  onChange={(e) => setEditingMilestone({...editingMilestone, referrals_required: parseInt(e.target.value) || 1})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="1"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">Bonus Amount ($)</label>
                <input
                  type="number"
                  value={editingMilestone.bonus_amount}
                  onChange={(e) => setEditingMilestone({...editingMilestone, bonus_amount: parseFloat(e.target.value) || 0})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="0"
                  step="0.5"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">Bonus Type</label>
                <select
                  value={editingMilestone.bonus_type}
                  onChange={(e) => setEditingMilestone({...editingMilestone, bonus_type: e.target.value})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="bonus">Bonus Wallet (Non-withdrawable)</option>
                  <option value="real">Real Wallet (Withdrawable)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">Description</label>
                <input
                  type="text"
                  value={editingMilestone.description}
                  onChange={(e) => setEditingMilestone({...editingMilestone, description: e.target.value})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  placeholder="e.g., First milestone bonus"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={saveMilestoneModal}
                  disabled={saving}
                  className="flex-1 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Milestone'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ==================== ANTI-FRAUD SETTINGS ====================

const AntiFraudSettings = ({ antiFraud, onSave, onReset, saving }) => {
  const [form, setForm] = useState({
    enabled: antiFraud?.enabled ?? true,
    max_referrals_per_ip: antiFraud?.max_referrals_per_ip ?? 3,
    ip_cooldown_hours: antiFraud?.ip_cooldown_hours ?? 24,
    min_account_age_hours: antiFraud?.min_account_age_hours ?? 1,
    min_deposit_for_valid_referral: antiFraud?.min_deposit_for_valid_referral ?? 10,
    flag_same_ip_referrals: antiFraud?.flag_same_ip_referrals ?? true,
    flag_rapid_signups: antiFraud?.flag_rapid_signups ?? true,
    rapid_signup_threshold_minutes: antiFraud?.rapid_signup_threshold_minutes ?? 5,
    auto_flag_suspicious: antiFraud?.auto_flag_suspicious ?? true,
    auto_reject_fraud: antiFraud?.auto_reject_fraud ?? false,
  });

  const handleSave = () => {
    onSave(form);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Anti-Fraud Detection</h3>
          <p className="text-sm text-gray-400">Configure fraud detection and prevention rules</p>
        </div>
        <button
          onClick={onReset}
          className="text-sm text-gray-400 hover:text-red-400 flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" /> Reset
        </button>
      </div>

      {/* Main Toggle */}
      <div className={`p-4 rounded-lg border ${form.enabled ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-red-500/10 border-red-500/20'}`}>
        <ToggleSwitch
          label="Anti-Fraud System"
          description="Enable fraud detection for referrals"
          value={form.enabled}
          onChange={(v) => setForm({...form, enabled: v})}
        />
      </div>

      {form.enabled && (
        <>
          {/* IP-Based Rules */}
          <div className="space-y-4 pt-4 border-t border-gray-800">
            <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide flex items-center gap-2">
              <Lock className="w-4 h-4" /> IP-Based Detection
            </h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Max Referrals Per IP</label>
                <input
                  type="number"
                  value={form.max_referrals_per_ip}
                  onChange={(e) => setForm({...form, max_referrals_per_ip: parseInt(e.target.value) || 1})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="1"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">IP Cooldown (hours)</label>
                <input
                  type="number"
                  value={form.ip_cooldown_hours}
                  onChange={(e) => setForm({...form, ip_cooldown_hours: parseInt(e.target.value) || 1})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="1"
                />
              </div>
            </div>

            <ToggleSwitch
              label="Flag Same IP Referrals"
              description="Flag referrals from same IP as referrer"
              value={form.flag_same_ip_referrals}
              onChange={(v) => setForm({...form, flag_same_ip_referrals: v})}
            />
          </div>

          {/* Time-Based Rules */}
          <div className="space-y-4 pt-4 border-t border-gray-800">
            <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Time-Based Detection
            </h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Min Account Age (hours)</label>
                <input
                  type="number"
                  value={form.min_account_age_hours}
                  onChange={(e) => setForm({...form, min_account_age_hours: parseInt(e.target.value) || 0})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Rapid Signup Threshold (minutes)</label>
                <input
                  type="number"
                  value={form.rapid_signup_threshold_minutes}
                  onChange={(e) => setForm({...form, rapid_signup_threshold_minutes: parseInt(e.target.value) || 1})}
                  className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  min="1"
                />
              </div>
            </div>

            <ToggleSwitch
              label="Flag Rapid Signups"
              description="Flag accounts created too quickly after referral"
              value={form.flag_rapid_signups}
              onChange={(v) => setForm({...form, flag_rapid_signups: v})}
            />
          </div>

          {/* Deposit Rules */}
          <div className="space-y-4 pt-4 border-t border-gray-800">
            <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide">Deposit Requirements</h4>
            
            <div>
              <label className="block text-sm text-gray-400 mb-2">Min Deposit for Valid Referral ($)</label>
              <input
                type="number"
                value={form.min_deposit_for_valid_referral}
                onChange={(e) => setForm({...form, min_deposit_for_valid_referral: parseFloat(e.target.value) || 0})}
                className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500 max-w-xs"
                min="0"
                step="1"
              />
              <p className="text-xs text-gray-500 mt-1">Minimum first deposit to count referral as valid</p>
            </div>
          </div>

          {/* Auto Actions */}
          <div className="space-y-4 pt-4 border-t border-gray-800">
            <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide">Automatic Actions</h4>
            
            <ToggleSwitch
              label="Auto-Flag Suspicious"
              description="Automatically flag suspicious referrals for review"
              value={form.auto_flag_suspicious}
              onChange={(v) => setForm({...form, auto_flag_suspicious: v})}
            />
            
            <ToggleSwitch
              label="Auto-Reject Fraud"
              description="Automatically reject clearly fraudulent referrals"
              value={form.auto_reject_fraud}
              onChange={(v) => setForm({...form, auto_reject_fraud: v})}
              danger
            />
          </div>
        </>
      )}

      <div className="pt-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-3 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Anti-Fraud Settings'}
        </button>
      </div>
    </div>
  );
};

// ==================== TOGGLE SWITCH COMPONENT ====================

const ToggleSwitch = ({ label, description, value, onChange, danger = false }) => {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-white font-medium">{label}</p>
        {description && <p className="text-sm text-gray-400">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!value)}
        className={`relative w-14 h-7 rounded-full transition-colors ${
          value 
            ? (danger ? 'bg-red-500' : 'bg-emerald-500') 
            : 'bg-gray-700'
        }`}
      >
        <span 
          className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full transition-transform ${
            value ? 'translate-x-7' : ''
          }`}
        />
      </button>
    </div>
  );
};

export default AdminSettings;
