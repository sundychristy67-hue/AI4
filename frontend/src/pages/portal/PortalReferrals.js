import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import InviteModal from '../../components/InviteModal';
import { 
  ArrowLeft, Users, DollarSign, Copy, Check, Gift, Crown, 
  TrendingUp, Star, Zap, Target, ArrowRight, Info, UserCheck, 
  UserX, Clock, ChevronRight, Sparkles, Award, Trophy, MessageCircle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalReferrals = () => {
  const navigate = useNavigate();
  const { portalToken, clientToken, portalClient } = useAuth();
  const [loading, setLoading] = useState(true);
  const [referralData, setReferralData] = useState(null);
  const [copied, setCopied] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [applyCode, setApplyCode] = useState('');
  const [applying, setApplying] = useState(false);
  const [activeTab, setActiveTab] = useState('active'); // 'active' or 'inactive'

  const getAuthHeaders = () => {
    if (clientToken) {
      return { Authorization: `Bearer ${clientToken}` };
    } else if (portalToken) {
      return { 'X-Portal-Token': portalToken };
    }
    return {};
  };

  useEffect(() => {
    fetchReferrals();
  }, []);

  const fetchReferrals = async () => {
    try {
      const response = await axios.get(`${API}/portal/referrals`, {
        headers: getAuthHeaders()
      });
      setReferralData(response.data);
    } catch (error) {
      console.error('Failed to fetch referrals:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    const code = referralData?.referral_code || portalClient?.referral_code;
    if (code) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleApplyCode = async () => {
    if (!applyCode.trim()) return;
    
    setApplying(true);
    try {
      const response = await axios.post(
        `${API}/portal/referrals/apply`,
        { referral_code: applyCode.trim() },
        { headers: getAuthHeaders() }
      );
      
      if (response.data.success) {
        alert('Referral code applied successfully!');
        fetchReferrals();
        setApplyCode('');
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      alert(error.response?.data?.message || 'Failed to apply referral code');
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  const referralCode = referralData?.referral_code || portalClient?.referral_code || 'N/A';
  const referrals = referralData?.referrals || [];
  const activeReferrals = referrals.filter(r => r.status === 'active' || r.status === 'valid');
  const inactiveReferrals = referrals.filter(r => r.status !== 'active' && r.status !== 'valid');

  // Tier configuration
  const tiers = [
    { tier: 0, name: 'Starter', minRefs: 0, percentage: 5, color: 'gray' },
    { tier: 1, name: 'Bronze', minRefs: 10, percentage: 10, color: 'amber' },
    { tier: 2, name: 'Silver', minRefs: 25, percentage: 15, color: 'slate' },
    { tier: 3, name: 'Gold', minRefs: 50, percentage: 20, color: 'yellow' },
    { tier: 4, name: 'Platinum', minRefs: 100, percentage: 25, color: 'cyan' },
    { tier: 5, name: 'Diamond', minRefs: 200, percentage: 30, color: 'purple' },
  ];

  const currentTier = tiers.reduce((acc, tier) => {
    if ((referralData?.active_referrals || 0) >= tier.minRefs) return tier;
    return acc;
  }, tiers[0]);

  const nextTier = tiers.find(t => t.tier === currentTier.tier + 1);

  return (
    <div className="min-h-screen bg-black pb-20">
      <div className="max-w-lg mx-auto">
        {/* Header with Stats */}
        <div className="bg-gradient-to-br from-gray-900 via-black to-gray-900 border-b border-gray-800 px-4 py-4 sticky top-0 z-10">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate('/portal')}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-6 h-6 text-gray-400" />
            </button>
            <h1 className="text-xl font-bold text-white">Referral Program</h1>
            <div className="w-10"></div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-black border border-gray-800 rounded-lg p-3 text-center">
              <p className="text-gray-400 text-xs mb-1">Total</p>
              <p className="text-white text-2xl font-bold">{referralData?.total_referrals || 0}</p>
            </div>
            <div className="bg-black border border-emerald-500/30 rounded-lg p-3 text-center">
              <p className="text-gray-400 text-xs mb-1">Active</p>
              <p className="text-emerald-400 text-2xl font-bold">{referralData?.active_referrals || 0}</p>
            </div>
            <div className="bg-black border border-amber-500/30 rounded-lg p-3 text-center">
              <p className="text-gray-400 text-xs mb-1">Earnings</p>
              <p className="text-amber-400 text-2xl font-bold">${(referralData?.total_earnings || 0).toFixed(0)}</p>
            </div>
          </div>
        </div>

        <div className="px-4 py-4 space-y-4">
          {/* 🔥 HERO SECTION - EARN UP TO 30% */}
          <div className="bg-gradient-to-br from-amber-500/20 via-orange-500/20 to-red-500/20 border-2 border-amber-500/50 rounded-2xl p-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-amber-400/20 to-transparent rounded-bl-full"></div>
            <div className="absolute bottom-0 left-0 w-24 h-24 bg-gradient-to-tr from-orange-400/10 to-transparent rounded-tr-full"></div>
            
            <div className="flex items-center gap-2 mb-3">
              <Crown className="w-8 h-8 text-amber-400" />
              <span className="text-amber-400 font-bold text-xl">LIFETIME EARNINGS</span>
            </div>
            
            <h2 className="text-4xl font-black text-white mb-2">
              EARN UP TO <span className="text-amber-400">30%</span>
            </h2>
            
            <p className="text-gray-300 text-lg mb-4">
              From ALL your referral deposits — <span className="text-amber-400 font-bold">FOREVER!</span>
            </p>
            
            <div className="bg-black/30 rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Your Current Rate:</span>
                <span className="text-2xl font-bold text-emerald-400">{currentTier.percentage}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Your Tier:</span>
                <span className={`font-bold text-${currentTier.color}-400`}>{currentTier.name}</span>
              </div>
            </div>
            
            <div className="flex items-center gap-2 text-amber-300 text-sm">
              <Zap className="w-4 h-4" />
              <span>Every deposit your referrals make = money in YOUR wallet!</span>
            </div>
          </div>

          {/* Your Referral Code - BIG & PROMINENT */}
          <div className="bg-gray-900 border-2 border-emerald-500/30 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Star className="w-6 h-6 text-emerald-400" />
              <h3 className="text-white font-bold text-lg">Your Referral Code</h3>
            </div>
            
            <div className="flex gap-2 mb-4">
              <div className="flex-1 bg-black border-2 border-emerald-500/50 rounded-xl px-4 py-4 text-center">
                <span className="text-3xl font-mono font-black text-emerald-400 tracking-widest">
                  {referralCode}
                </span>
              </div>
              <button
                onClick={handleCopy}
                className="px-5 py-4 bg-emerald-500 hover:bg-emerald-600 rounded-xl transition-colors"
              >
                {copied ? (
                  <Check className="w-6 h-6 text-white" />
                ) : (
                  <Copy className="w-6 h-6 text-white" />
                )}
              </button>
            </div>
            
            <button
              onClick={() => setShowInviteModal(true)}
              className="w-full py-4 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-bold text-lg rounded-xl hover:from-emerald-600 hover:to-teal-700 transition-all flex items-center justify-center gap-2"
            >
              <Users className="w-5 h-5" />
              Share & Start Earning
            </button>
          </div>

          {/* TIER PROGRESSION */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-bold mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-400" />
              Commission Tiers
            </h3>
            
            <div className="space-y-3">
              {tiers.map((tier, idx) => {
                const isCurrentTier = tier.tier === currentTier.tier;
                const isUnlocked = (referralData?.active_referrals || 0) >= tier.minRefs;
                
                return (
                  <div
                    key={tier.tier}
                    className={`p-3 rounded-xl border transition-all ${
                      isCurrentTier 
                        ? 'border-emerald-500 bg-emerald-500/10' 
                        : isUnlocked 
                          ? 'border-gray-700 bg-gray-800/50' 
                          : 'border-gray-800 bg-black opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          isCurrentTier ? 'bg-emerald-500' : isUnlocked ? 'bg-gray-700' : 'bg-gray-800'
                        }`}>
                          {isCurrentTier ? (
                            <Check className="w-5 h-5 text-white" />
                          ) : tier.tier === 5 ? (
                            <Crown className="w-5 h-5 text-purple-400" />
                          ) : (
                            <span className={`font-bold ${isUnlocked ? 'text-white' : 'text-gray-500'}`}>{tier.tier}</span>
                          )}
                        </div>
                        <div>
                          <p className={`font-bold ${isCurrentTier ? 'text-emerald-400' : 'text-white'}`}>
                            {tier.name}
                          </p>
                          <p className="text-gray-500 text-xs">
                            {tier.minRefs === 0 ? 'Starting tier' : `${tier.minRefs}+ active referrals`}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-xl font-black ${
                          isCurrentTier ? 'text-emerald-400' : isUnlocked ? 'text-white' : 'text-gray-500'
                        }`}>
                          {tier.percentage}%
                        </p>
                        <p className="text-gray-500 text-xs">commission</p>
                      </div>
                    </div>
                    
                    {isCurrentTier && nextTier && (
                      <div className="mt-3 pt-3 border-t border-gray-700">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-400">
                            {nextTier.minRefs - (referralData?.active_referrals || 0)} more to reach {nextTier.name}
                          </span>
                          <span className="text-amber-400 font-bold">→ {nextTier.percentage}%</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {referralData?.referred_by && (
            <div className="bg-gray-900 border border-emerald-500/20 rounded-xl p-4">
              <p className="text-gray-400 text-sm">You were referred by:</p>
              <p className="text-emerald-400 font-mono text-lg font-bold">{referralData.referred_by}</p>
            </div>
          )}

          {/* Note about referral code application */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <MessageCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-blue-400 font-bold mb-1">How to Apply a Referral Code</h4>
                <p className="text-gray-300 text-sm">
                  Referral codes can only be applied when you <span className="text-blue-400 font-bold">first sign up via Messenger</span>. 
                  Simply text the referral code when asked during registration!
                </p>
              </div>
            </div>
          </div>

          {/* YOUR REFERRALS LIST */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-gray-800">
              <h3 className="text-white font-bold flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-400" />
                Your Referrals
              </h3>
            </div>
            
            {/* Tabs */}
            <div className="flex border-b border-gray-800">
              <button
                onClick={() => setActiveTab('active')}
                className={`flex-1 py-3 text-center font-medium transition ${
                  activeTab === 'active' 
                    ? 'text-emerald-400 border-b-2 border-emerald-400 bg-emerald-500/5' 
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                <UserCheck className="w-4 h-4 inline mr-2" />
                Active ({activeReferrals.length})
              </button>
              <button
                onClick={() => setActiveTab('inactive')}
                className={`flex-1 py-3 text-center font-medium transition ${
                  activeTab === 'inactive' 
                    ? 'text-gray-400 border-b-2 border-gray-400 bg-gray-500/5' 
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                <UserX className="w-4 h-4 inline mr-2" />
                Inactive ({inactiveReferrals.length})
              </button>
            </div>

            <div className="p-4">
              {activeTab === 'active' ? (
                activeReferrals.length === 0 ? (
                  <div className="text-center py-8">
                    <UserCheck className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No active referrals yet</p>
                    <p className="text-gray-500 text-sm mt-1">Active referrals have made a deposit</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {activeReferrals.map((ref) => (
                      <div
                        key={ref.id}
                        className="flex items-center justify-between p-3 bg-emerald-500/5 border border-emerald-500/20 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center">
                            <UserCheck className="w-5 h-5 text-emerald-400" />
                          </div>
                          <div>
                            <p className="text-white font-medium">{ref.referred_display_name}</p>
                            <p className="text-gray-500 text-xs">
                              Joined: {new Date(ref.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-emerald-400 font-bold">${(ref.total_deposits || 0).toFixed(2)}</p>
                          <p className="text-gray-500 text-xs">deposited</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                inactiveReferrals.length === 0 ? (
                  <div className="text-center py-8">
                    <UserX className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No inactive referrals</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {inactiveReferrals.map((ref) => (
                      <div
                        key={ref.id}
                        className="flex items-center justify-between p-3 bg-black border border-gray-800 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gray-800 rounded-full flex items-center justify-center">
                            <Clock className="w-5 h-5 text-gray-500" />
                          </div>
                          <div>
                            <p className="text-gray-400 font-medium">{ref.referred_display_name}</p>
                            <p className="text-gray-600 text-xs">
                              Joined: {new Date(ref.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="px-2 py-1 bg-gray-800 text-gray-500 text-xs rounded-full">
                            Pending deposit
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>
          </div>

          {/* WHAT IS AN ACTIVE REFERRAL */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-blue-400 font-bold mb-2">What is an Active Referral?</h4>
                <p className="text-gray-300 text-sm">
                  A referral becomes <span className="text-emerald-400 font-bold">ACTIVE</span> when they make their <span className="font-bold">first deposit</span>. 
                  Only active referrals count towards your tier progression and you only earn commission from active referrals&apos; deposits.
                </p>
              </div>
            </div>
          </div>

          {/* HOW IT WORKS */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-bold mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              How The Referral Program Works
            </h3>
            
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-emerald-400 font-bold">1</span>
                </div>
                <div>
                  <h4 className="text-white font-semibold">Share Your Code</h4>
                  <p className="text-gray-400 text-sm">Give your unique referral code to friends. They enter it when they sign up.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-emerald-400 font-bold">2</span>
                </div>
                <div>
                  <h4 className="text-white font-semibold">They Make a Deposit</h4>
                  <p className="text-gray-400 text-sm">When your referral makes their first deposit, they become an ACTIVE referral.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-amber-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <DollarSign className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h4 className="text-white font-semibold">You Earn Commission</h4>
                  <p className="text-gray-400 text-sm">
                    Every time they deposit, you earn <span className="text-amber-400 font-bold">{currentTier.percentage}%</span> commission. 
                    This is <span className="text-amber-400 font-bold">LIFETIME</span> — you earn from their deposits FOREVER!
                  </p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h4 className="text-white font-semibold">Level Up Your Tier</h4>
                  <p className="text-gray-400 text-sm">
                    Get more active referrals to unlock higher tiers and earn up to <span className="text-amber-400 font-bold">30% commission!</span>
                  </p>
                </div>
              </div>
            </div>

            {/* Example Calculation */}
            <div className="mt-4 p-4 bg-black rounded-xl border border-gray-700">
              <h4 className="text-amber-400 font-bold mb-2 flex items-center gap-2">
                <Award className="w-4 h-4" />
                Example Earnings
              </h4>
              <p className="text-gray-400 text-sm">
                If you have <span className="text-white font-bold">10 active referrals</span> and each deposits <span className="text-white font-bold">$100/month</span>:
              </p>
              <p className="text-amber-400 text-xl font-bold mt-2">
                = ${(10 * 100 * (currentTier.percentage / 100)).toFixed(0)}/month passive income!
              </p>
            </div>
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

export default PortalReferrals;
