import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import InviteModal from '../../components/InviteModal';
import { 
  TrendingUp, TrendingDown, Users, ArrowRight, Gift, Key, Receipt, 
  Wallet, CreditCard, Target, Settings, Star, Zap, Crown, Copy, Check,
  Sparkles, MessageCircle, ChevronRight
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalDashboard = () => {
  const navigate = useNavigate();
  const { portalClient, portalToken, clientToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [copied, setCopied] = useState(false);

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

  const handleCopyCode = () => {
    const code = dashboard?.referral_summary?.referral_code || portalClient?.referral_code;
    if (code) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
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
  const totalBalance = realBalance + bonusBalance;
  const referralEarnings = overview.referral_earnings || 0;
  const referralCode = referralSummary.referral_code || portalClient?.referral_code || 'N/A';

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

          {/* SINGLE COMBINED WALLET - Click to see details */}
          <div 
            onClick={() => navigate('/portal/wallets')}
            className="bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600 rounded-2xl p-5 cursor-pointer hover:from-emerald-600 hover:via-teal-600 hover:to-emerald-700 transition-all shadow-lg shadow-emerald-500/20"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white/20 rounded-xl">
                  <Wallet className="w-7 h-7 text-white" />
                </div>
                <div>
                  <p className="text-white/80 text-sm font-medium">Total Balance</p>
                  <p className="text-4xl font-black text-white">${totalBalance.toFixed(2)}</p>
                  <p className="text-white/60 text-xs mt-1">
                    Real: ${realBalance.toFixed(2)} + Bonus: ${bonusBalance.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="flex flex-col items-end">
                <ChevronRight className="w-6 h-6 text-white/60" />
                <span className="text-white/60 text-xs mt-1">View Details</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="px-4 py-4 space-y-4">
          
          {/* 🔥 $5 FREEPLAY HIGHLIGHT - 100% REDEEMABLE */}
          <div
            onClick={() => navigate('/portal/bonus-tasks')}
            className="bg-gradient-to-br from-purple-600 via-pink-500 to-orange-500 rounded-2xl p-5 cursor-pointer relative overflow-hidden shadow-lg shadow-purple-500/30"
          >
            {/* Animated sparkles background */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-bl-full"></div>
            <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-tr-full"></div>
            
            <div className="relative">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-6 h-6 text-yellow-300 animate-pulse" />
                <span className="text-yellow-300 font-black text-lg">FREE $5 PLAY!</span>
              </div>
              
              <h3 className="text-3xl font-black text-white mb-2">
                GET 5 REFERRALS
              </h3>
              
              <div className="flex items-center gap-3 mb-3">
                <span className="px-3 py-1 bg-white/20 backdrop-blur rounded-full text-white font-bold text-sm">
                  🎮 100% REDEEMABLE
                </span>
                <span className="px-3 py-1 bg-yellow-400/20 backdrop-blur rounded-full text-yellow-300 font-bold text-sm">
                  USE IN ANY GAME
                </span>
              </div>
              
              <p className="text-white/80 text-sm mb-3">
                Your friends just need to <span className="text-yellow-300 font-bold">text your code in Messenger</span> - that's it!
              </p>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageCircle className="w-4 h-4 text-white/60" />
                  <span className="text-white/60 text-xs">Progress: {referralSummary.valid_referrals || 0}/5 referrals</span>
                </div>
                <span className="text-white font-bold flex items-center gap-1">
                  Claim Now <ArrowRight className="w-4 h-4" />
                </span>
              </div>
            </div>
          </div>

          {/* 🔥 EARN UP TO 30% - LIFETIME */}
          <div
            onClick={() => navigate('/portal/referrals')}
            className="bg-gradient-to-br from-amber-500/20 via-orange-500/20 to-red-500/20 border-2 border-amber-500/50 rounded-2xl p-5 cursor-pointer hover:border-amber-400 transition-all relative overflow-hidden"
            data-testid="earn-30-card"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-amber-400/20 to-transparent rounded-bl-full"></div>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Crown className="w-6 h-6 text-amber-400" />
                  <span className="text-amber-400 font-bold text-lg">LIFETIME EARNINGS</span>
                </div>
                <h3 className="text-3xl font-black text-white mb-1">
                  EARN UP TO <span className="text-amber-400">30%</span>
                </h3>
                <p className="text-gray-400 text-sm">From all your referral deposits - FOREVER!</p>
              </div>
              <Zap className="w-8 h-8 text-amber-400 animate-pulse" />
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-emerald-400 text-sm font-medium">
                Current Rate: {referralSummary.percentage || 5}% (Tier {referralSummary.tier || 0})
              </span>
              <span className="text-amber-400 text-sm font-bold flex items-center gap-1">
                Start Earning <ArrowRight className="w-4 h-4" />
              </span>
            </div>
          </div>

          {/* Referral Code Card */}
          <div
            className="bg-gray-900 border border-emerald-500/30 rounded-xl p-4"
            data-testid="referral-code-card"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Star className="w-5 h-5 text-emerald-400" />
                <span className="text-white font-medium">Your Referral Code</span>
              </div>
              <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded-full">
                Share & Earn
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-black border border-gray-700 rounded-lg px-4 py-3 text-center">
                <span className="text-2xl font-mono font-bold text-emerald-400 tracking-wider">
                  {referralCode}
                </span>
              </div>
              <button
                onClick={handleCopyCode}
                className="p-3 bg-emerald-500 hover:bg-emerald-600 rounded-lg transition-colors"
              >
                {copied ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <Copy className="w-5 h-5 text-white" />
                )}
              </button>
            </div>
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => setShowInviteModal(true)}
                className="flex-1 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all text-sm"
              >
                Share Code
              </button>
              <button
                onClick={() => navigate('/portal/referrals')}
                className="flex-1 py-2 bg-gray-800 text-white font-medium rounded-lg hover:bg-gray-700 transition-all text-sm"
              >
                View Referrals
              </button>
            </div>
            
            {/* How to share explanation */}
            <div className="mt-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <p className="text-blue-300 text-xs flex items-start gap-2">
                <MessageCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>Tell your friends to <span className="font-bold">message your code in our Messenger</span> when they sign up!</span>
              </p>
            </div>
          </div>

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
                <p className="text-gray-500 text-xs">Ref Earn</p>
              </div>
              <p className="text-blue-400 text-lg font-bold">${referralEarnings.toFixed(2)}</p>
            </div>
          </div>

          {/* Referral Progress Card */}
          <div
            onClick={() => navigate('/portal/referrals')}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 cursor-pointer hover:border-gray-700 transition-all"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-emerald-400" />
                <span className="text-white font-medium">Referral Progress</span>
              </div>
              <span className="text-xs text-gray-500">Tier {referralSummary.tier || 0}</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">{referralSummary.valid_referrals || 0} active referrals</span>
              <span className="text-emerald-400 text-sm font-medium">{referralSummary.percentage || 5}% earn rate</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden mb-3">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all"
                style={{ width: `${referralSummary.progress_to_next || 0}%` }}
              ></div>
            </div>
            {bonusInfo.referrals_until_next > 0 && (
              <span className="text-xs text-purple-400">
                🎁 {bonusInfo.referrals_until_next} more referrals for ${bonusInfo.next_bonus_amount?.toFixed(2)} bonus!
              </span>
            )}
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
        referralCode={referralCode}
      />
    </div>
  );
};

export default PortalDashboard;
