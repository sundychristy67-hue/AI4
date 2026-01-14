import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import InviteModal from '../../components/InviteModal';
import { TrendingUp, TrendingDown, Users, ArrowRight, Gift, Key, Receipt, Wallet, CreditCard, Target, Settings } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalDashboard = () => {
  const navigate = useNavigate();
  const { portalClient, portalToken, clientToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [showInviteModal, setShowInviteModal] = useState(false);

  const getAuthHeaders = () => {
    if (clientToken) {
      return { Authorization: `Bearer ${clientToken}` };
    } else if (portalToken) {
      return { 'X-Portal-Token': portalToken };
    }
    return {};
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API}/portal/dashboard`, {
        headers: getAuthHeaders()
      });
      setDashboard(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  const wallet = dashboard?.wallet || {};
  const overview = dashboard?.overview || {};
  const referralSummary = dashboard?.referral_summary || {};
  const bonusInfo = dashboard?.bonus_info || {};
  const recentTransactions = dashboard?.recent_transactions || [];

  const realBalance = wallet.real_balance || 0;
  const bonusBalance = wallet.bonus_balance || 0;
  const referralEarnings = overview.referral_earnings || 0;

  return (
    <div className="min-h-screen bg-black pb-20">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-br from-gray-900 via-black to-gray-900 px-4 pt-6 pb-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-white">Dashboard</h1>
              <p className="text-gray-400 text-sm">Welcome, {portalClient?.display_name || 'Player'}</p>
            </div>
            <button 
              onClick={() => navigate('/portal/security')}
              className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition"
              data-testid="portal-settings-btn"
            >
              <Settings className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          {/* Dual Wallet Cards */}
          <div className="space-y-3">
            {/* Real Wallet */}
            <div 
              onClick={() => navigate('/portal/wallets')}
              className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-2xl p-4 cursor-pointer hover:from-emerald-600 hover:to-teal-700 transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white/20 rounded-lg">
                    <Wallet className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="text-white/80 text-xs font-medium">Real Wallet</p>
                    <p className="text-2xl font-bold text-white">${realBalance.toFixed(2)}</p>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 text-white/60" />
              </div>
            </div>

            {/* Bonus Wallet */}
            <div 
              onClick={() => navigate('/portal/bonus-tasks')}
              className="bg-gradient-to-r from-purple-500 to-pink-600 rounded-2xl p-4 cursor-pointer hover:from-purple-600 hover:to-pink-700 transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white/20 rounded-lg">
                    <Gift className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="text-white/80 text-xs font-medium">Bonus Wallet</p>
                    <p className="text-2xl font-bold text-white">${bonusBalance.toFixed(2)}</p>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 text-white/60" />
              </div>
            </div>
          </div>
        </div>

        {/* Balance Cards */}
        <div className="px-4 py-4 space-y-4">
          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
              <div className="flex items-center gap-1 mb-1">
                <TrendingUp className="w-3 h-3 text-emerald-400" />
                <p className="text-gray-500 text-xs">Total In</p>
              </div>
              <p className="text-emerald-400 text-lg font-bold">${(wallet.total_in || 0).toFixed(2)}</p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
              <div className="flex items-center gap-1 mb-1">
                <TrendingDown className="w-3 h-3 text-red-400" />
                <p className="text-gray-500 text-xs">Total Out</p>
              </div>
              <p className="text-red-400 text-lg font-bold">${(wallet.total_out || 0).toFixed(2)}</p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
              <div className="flex items-center gap-1 mb-1">
                <Users className="w-3 h-3 text-blue-400" />
                <p className="text-gray-500 text-xs">Earnings</p>
              </div>
              <p className="text-blue-400 text-lg font-bold">${referralEarnings.toFixed(2)}</p>
            </div>
          </div>

          {/* Referral Progress Card */}
          <div
            onClick={() => setShowInviteModal(true)}
            className="bg-gray-900 border border-emerald-500/20 rounded-xl p-4 cursor-pointer hover:border-emerald-500/40 transition-all"
            data-testid="referral-code-card"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-emerald-400" />
                <span className="text-white font-medium">Referral Progress</span>
              </div>
              <span className="text-xs text-gray-500">Tier {referralSummary.tier || 0}</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">{referralSummary.valid_referrals || 0} valid referrals</span>
              <span className="text-emerald-400 text-sm font-medium">{referralSummary.percentage || 5}% earn rate</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden mb-3">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all"
                style={{ width: `${referralSummary.progress_to_next || 0}%` }}
              ></div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500 text-xs">Code: <span className="text-emerald-400 font-mono">{referralSummary.referral_code || 'N/A'}</span></span>
              {bonusInfo.referrals_until_next > 0 && (
                <span className="text-xs text-purple-400">
                  {bonusInfo.referrals_until_next} more for ${bonusInfo.next_bonus_amount?.toFixed(2)} bonus
                </span>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-4 gap-3">
            <button
              onClick={() => navigate('/portal/load-game')}
              className="py-3 px-2 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 rounded-lg text-white hover:border-emerald-500/50 transition-all"
              data-testid="quick-load"
            >
              <CreditCard className="w-5 h-5 mx-auto mb-1 text-emerald-400" />
              <span className="text-xs">Load</span>
            </button>
            <button
              onClick={() => navigate('/portal/credentials')}
              className="py-3 px-2 bg-gray-900 border border-gray-800 rounded-lg text-white hover:border-gray-700 transition-all"
              data-testid="quick-games"
            >
              <Key className="w-5 h-5 mx-auto mb-1 text-gray-400" />
              <span className="text-xs">Games</span>
            </button>
            <button
              onClick={() => navigate('/portal/transactions')}
              className="py-3 px-2 bg-gray-900 border border-gray-800 rounded-lg text-white hover:border-gray-700 transition-all"
              data-testid="quick-history"
            >
              <Receipt className="w-5 h-5 mx-auto mb-1 text-gray-400" />
              <span className="text-xs">History</span>
            </button>
            <button
              onClick={() => navigate('/portal/withdrawals')}
              className="py-3 px-2 bg-gray-900 border border-gray-800 rounded-lg text-white hover:border-gray-700 transition-all"
              data-testid="quick-cashouts"
            >
              <Wallet className="w-5 h-5 mx-auto mb-1 text-gray-400" />
              <span className="text-xs">Cashout</span>
            </button>
          </div>

          {/* Recent Activity */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">Recent Activity</h3>
              <button
                onClick={() => navigate('/portal/transactions')}
                className="text-emerald-400 text-sm hover:underline"
              >
                View All
              </button>
            </div>
            {recentTransactions.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No recent transactions</p>
            ) : (
              <div className="space-y-3">
                {recentTransactions.slice(0, 5).map((tx) => (
                  <div
                    key={tx.transaction_id}
                    className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      {tx.type === 'IN' || tx.type === 'REFERRAL_EARN' || tx.type === 'BONUS_EARN' ? (
                        <div className={`p-2 rounded-lg ${
                          tx.type === 'BONUS_EARN' ? 'bg-purple-500/10' : 'bg-emerald-500/10'
                        }`}>
                          {tx.type === 'BONUS_EARN' ? (
                            <Gift className="w-4 h-4 text-purple-400" />
                          ) : (
                            <TrendingUp className="w-4 h-4 text-emerald-400" />
                          )}
                        </div>
                      ) : (
                        <div className="p-2 bg-red-500/10 rounded-lg">
                          <TrendingDown className="w-4 h-4 text-red-400" />
                        </div>
                      )}
                      <div>
                        <p className="text-white text-sm font-medium">
                          {tx.type === 'IN' ? 'Deposit' : 
                           tx.type === 'OUT' ? 'Withdrawal' : 
                           tx.type === 'REAL_LOAD' ? 'Game Load' :
                           tx.type === 'BONUS_LOAD' ? 'Bonus Load' :
                           tx.type === 'BONUS_EARN' ? 'Bonus Earned' :
                           tx.type === 'REFERRAL_EARN' ? 'Referral Earn' : tx.type}
                        </p>
                        <p className="text-gray-500 text-xs">
                          {new Date(tx.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <p className={`font-bold ${
                      ['OUT', 'REAL_LOAD', 'BONUS_LOAD'].includes(tx.type) ? 'text-red-400' : 
                      tx.type === 'BONUS_EARN' ? 'text-purple-400' : 'text-emerald-400'
                    }`}>
                      {['OUT', 'REAL_LOAD', 'BONUS_LOAD'].includes(tx.type) ? '-' : '+'}${tx.amount?.toFixed(2)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <BottomNav />
      <InviteModal
        isOpen={showInviteModal}
        onClose={() => setShowInviteModal(false)}
        referralCode={referralSummary.referral_code}
      />
    </div>
  );
};

export default PortalDashboard;
