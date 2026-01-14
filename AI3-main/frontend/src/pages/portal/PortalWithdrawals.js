import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import { ArrowLeft, Wallet, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalWithdrawals = () => {
  const navigate = useNavigate();
  const { portalToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [withdrawals, setWithdrawals] = useState([]);

  useEffect(() => {
    fetchWithdrawals();
  }, []);

  const fetchWithdrawals = async () => {
    try {
      const response = await axios.get(`${API}/portal/withdrawals`, {
        headers: { 'X-Portal-Token': portalToken }
      });
      setWithdrawals(response.data.withdrawals || []);
    } catch (error) {
      console.error('Failed to fetch withdrawals:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'confirmed':
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'rejected':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'pending_payout':
      case 'pending_confirmation':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'confirmed': return 'Completed';
      case 'rejected': return 'Rejected';
      case 'pending_payout': return 'Processing';
      case 'pending_confirmation': return 'Pending';
      case 'cancelled': return 'Cancelled';
      default: return status;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  const totalPending = withdrawals
    .filter(w => ['pending_payout', 'pending_confirmation'].includes(w.status))
    .reduce((sum, w) => sum + w.amount, 0);
  const totalCompleted = withdrawals
    .filter(w => w.status === 'confirmed')
    .reduce((sum, w) => sum + w.amount, 0);

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
            <h1 className="text-xl font-bold text-white">Withdrawals</h1>
            <div className="w-10"></div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-black border border-yellow-500/20 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Pending</p>
              <p className="text-yellow-400 text-xl font-bold">${totalPending.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-emerald-500/20 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Completed</p>
              <p className="text-emerald-400 text-xl font-bold">${totalCompleted.toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Withdrawal List */}
        <div className="px-4 py-4 space-y-3">
          {withdrawals.length === 0 ? (
            <div className="text-center py-12">
              <Wallet className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 mb-2">No withdrawal requests</p>
              <p className="text-gray-500 text-sm">Request a redeem through Messenger</p>
            </div>
          ) : (
            withdrawals.map((withdrawal) => (
              <div
                key={withdrawal.order_id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      withdrawal.status === 'confirmed' ? 'bg-emerald-500/10' :
                      withdrawal.status === 'rejected' ? 'bg-red-500/10' : 'bg-yellow-500/10'
                    }`}>
                      {getStatusIcon(withdrawal.status)}
                    </div>
                    <div>
                      <p className="text-white font-medium">{withdrawal.game}</p>
                      <p className="text-gray-500 text-xs">
                        {new Date(withdrawal.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-red-400 text-lg font-bold">-${withdrawal.amount?.toFixed(2)}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      withdrawal.status === 'confirmed' ? 'bg-emerald-500/10 text-emerald-400' :
                      withdrawal.status === 'rejected' ? 'bg-red-500/10 text-red-400' :
                      'bg-yellow-500/10 text-yellow-400'
                    }`}>
                      {getStatusLabel(withdrawal.status)}
                    </span>
                  </div>
                </div>

                {withdrawal.payout_tag && (
                  <div className="bg-black border border-gray-800 rounded-lg p-2 text-sm">
                    <span className="text-gray-500">Payout: </span>
                    <span className="text-emerald-400 font-mono">{withdrawal.payout_tag}</span>
                  </div>
                )}

                {withdrawal.original_amount && withdrawal.original_amount !== withdrawal.amount && (
                  <p className="text-yellow-400 text-xs mt-2">
                    Original: ${withdrawal.original_amount.toFixed(2)} (adjusted)
                  </p>
                )}
              </div>
            ))
          )}
        </div>

        {/* Help Text */}
        <div className="px-4">
          <div className="bg-blue-900/20 border border-blue-700/50 rounded-xl p-4">
            <p className="text-blue-400 text-sm">
              <strong>How to withdraw:</strong> Message us on Messenger and say "redeem" to request a withdrawal.
            </p>
          </div>
        </div>
      </div>

      <BottomNav />
    </div>
  );
};

export default PortalWithdrawals;
