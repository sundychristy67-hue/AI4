import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import InviteModal from '../../components/InviteModal';
import { ArrowLeft, Users, DollarSign, Copy, Check, Gift } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalReferrals = () => {
  const navigate = useNavigate();
  const { portalToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [referralData, setReferralData] = useState(null);
  const [copied, setCopied] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [applyCode, setApplyCode] = useState('');
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    fetchReferrals();
  }, []);

  const fetchReferrals = async () => {
    try {
      const response = await axios.get(`${API}/portal/referrals`, {
        headers: { 'X-Portal-Token': portalToken }
      });
      setReferralData(response.data);
    } catch (error) {
      console.error('Failed to fetch referrals:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(referralData?.referral_code || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApplyCode = async () => {
    if (!applyCode.trim()) return;
    
    setApplying(true);
    try {
      const response = await axios.post(
        `${API}/portal/referrals/apply`,
        { referral_code: applyCode.trim() },
        { headers: { 'X-Portal-Token': portalToken } }
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

  return (
    <div className="min-h-screen bg-black pb-20">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="bg-gray-900 border-b border-gray-800 px-4 py-4 sticky top-0 z-10">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate('/portal')}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-6 h-6 text-gray-400" />
            </button>
            <h1 className="text-xl font-bold text-white">Referrals</h1>
            <div className="w-10"></div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-black border border-gray-800 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Total</p>
              <p className="text-white text-xl font-bold">{referralData?.total_referrals || 0}</p>
            </div>
            <div className="bg-black border border-emerald-500/20 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Active</p>
              <p className="text-emerald-400 text-xl font-bold">{referralData?.active_referrals || 0}</p>
            </div>
            <div className="bg-black border border-blue-500/20 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Earnings</p>
              <p className="text-blue-400 text-xl font-bold">${(referralData?.total_earnings || 0).toFixed(2)}</p>
            </div>
          </div>
        </div>

        <div className="px-4 py-4 space-y-4">
          {/* Your Referral Code */}
          <div className="bg-gray-900 border border-emerald-500/20 rounded-xl p-5">
            <h3 className="text-white font-semibold flex items-center gap-2 mb-4">
              <Gift className="w-5 h-5 text-emerald-400" />
              Your Referral Code
            </h3>
            <div className="flex gap-2">
              <div className="flex-1 bg-black border border-gray-700 rounded-lg px-4 py-3 text-center">
                <span className="text-2xl font-mono font-bold text-emerald-400">
                  {referralData?.referral_code || 'N/A'}
                </span>
              </div>
              <button
                onClick={handleCopy}
                className="px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              >
                {copied ? (
                  <Check className="w-5 h-5 text-emerald-400" />
                ) : (
                  <Copy className="w-5 h-5 text-gray-400" />
                )}
              </button>
            </div>
            <button
              onClick={() => setShowInviteModal(true)}
              className="w-full mt-4 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all"
            >
              Share Code
            </button>
          </div>

          {/* Apply Referral Code */}
          {!referralData?.referred_by && !referralData?.referral_locked && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-white font-semibold mb-3">Have a Referral Code?</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={applyCode}
                  onChange={(e) => setApplyCode(e.target.value.toUpperCase())}
                  placeholder="Enter code"
                  className="flex-1 bg-black border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                  maxLength={10}
                />
                <button
                  onClick={handleApplyCode}
                  disabled={applying || !applyCode.trim()}
                  className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50"
                >
                  {applying ? '...' : 'Apply'}
                </button>
              </div>
            </div>
          )}

          {referralData?.referred_by && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-sm">Referred By</p>
              <p className="text-emerald-400 font-mono text-lg">{referralData.referred_by}</p>
            </div>
          )}

          {referralData?.referral_locked && !referralData?.referred_by && (
            <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-xl p-4">
              <p className="text-yellow-400 text-sm">
                Referral codes can only be applied before your first deposit.
              </p>
            </div>
          )}

          {/* Referral List */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-4">Your Referrals</h3>
            {!referralData?.referrals || referralData.referrals.length === 0 ? (
              <div className="text-center py-8">
                <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No referrals yet</p>
                <p className="text-gray-500 text-sm mt-1">Share your code to get started!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {referralData.referrals.map((ref) => (
                  <div
                    key={ref.id}
                    className="flex items-center justify-between p-3 bg-black border border-gray-800 rounded-lg"
                  >
                    <div>
                      <p className="text-white font-medium">{ref.referred_display_name}</p>
                      <p className="text-gray-500 text-xs">
                        Joined: {new Date(ref.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                        ref.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-gray-700 text-gray-400'
                      }`}>
                        {ref.status}
                      </span>
                      <p className="text-gray-400 text-xs mt-1">
                        ${(ref.total_deposits || 0).toFixed(2)} deposited
                      </p>
                    </div>
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
        referralCode={referralData?.referral_code}
      />
    </div>
  );
};

export default PortalReferrals;
