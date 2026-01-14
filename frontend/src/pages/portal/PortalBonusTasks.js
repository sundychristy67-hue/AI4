import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import { ArrowLeft, Gift, Target, Check, Clock, Trophy } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalBonusTasks = () => {
  const navigate = useNavigate();
  const { portalToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchBonusTasks();
  }, []);

  const fetchBonusTasks = async () => {
    try {
      const response = await axios.get(`${API}/portal/bonus-tasks`, {
        headers: { 'X-Portal-Token': portalToken }
      });
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch bonus tasks:', error);
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

  const tasks = data?.tasks || [];
  const bonusHistory = data?.bonus_history || [];
  const bonusBalance = data?.wallet_bonus_balance || 0;

  return (
    <div className="min-h-screen bg-black pb-20">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="bg-gray-900 border-b border-gray-800 px-4 py-4 sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/portal')}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-6 h-6 text-gray-400" />
            </button>
            <h1 className="text-xl font-bold text-white">Bonus Tasks</h1>
            <div className="w-10"></div>
          </div>
        </div>

        <div className="px-4 py-4 space-y-4">
          {/* Bonus Wallet Summary */}
          <div className="bg-gradient-to-br from-purple-600 to-pink-600 rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-3 bg-white/20 rounded-xl">
                <Gift className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-white/80 text-sm">Bonus Wallet Balance</h3>
                <p className="text-3xl font-bold text-white">${bonusBalance.toFixed(2)}</p>
              </div>
            </div>
            <p className="text-white/60 text-xs">
              Bonus funds can be used to load games but cannot be withdrawn.
            </p>
          </div>

          {/* Active Tasks */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-emerald-400" />
              Active Tasks
            </h3>

            {tasks.length === 0 ? (
              <p className="text-gray-500 text-center py-6">No active tasks available</p>
            ) : (
              <div className="space-y-4">
                {tasks.map((task) => {
                  const progress = (task.progress / task.target) * 100;
                  const isComplete = task.status === 'claimable' || progress >= 100;

                  return (
                    <div
                      key={task.id}
                      className={`p-4 rounded-xl border ${
                        isComplete
                          ? 'border-emerald-500/30 bg-emerald-500/5'
                          : 'border-gray-700 bg-black'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h4 className="text-white font-medium">{task.title}</h4>
                          <p className="text-gray-400 text-sm mt-1">{task.description}</p>
                        </div>
                        <div className="text-right">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            isComplete
                              ? 'bg-emerald-500/10 text-emerald-400'
                              : 'bg-yellow-500/10 text-yellow-400'
                          }`}>
                            {isComplete ? 'Complete!' : 'In Progress'}
                          </span>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="mb-3">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-gray-400">
                            {task.progress} / {task.target} referrals
                          </span>
                          <span className="text-emerald-400 font-medium">
                            +${task.reward_amount?.toFixed(2)} bonus
                          </span>
                        </div>
                        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              isComplete ? 'bg-emerald-500' : 'bg-gradient-to-r from-emerald-500 to-teal-500'
                            }`}
                            style={{ width: `${Math.min(100, progress)}%` }}
                          ></div>
                        </div>
                      </div>

                      {!isComplete && task.remaining > 0 && (
                        <p className="text-gray-500 text-sm">
                          {task.remaining} more referral{task.remaining > 1 ? 's' : ''} needed
                        </p>
                      )}

                      {isComplete && (
                        <div className="flex items-center gap-2 text-emerald-400 text-sm">
                          <Check className="w-4 h-4" />
                          Bonus automatically credited to your wallet!
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Bonus History */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-purple-400" />
              Bonus History
            </h3>

            {bonusHistory.length === 0 ? (
              <div className="text-center py-6">
                <Gift className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500">No bonuses earned yet</p>
                <p className="text-gray-600 text-sm mt-1">Complete tasks to earn bonus rewards!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {bonusHistory.map((bonus, idx) => (
                  <div
                    key={bonus.transaction_id || idx}
                    className="flex items-center justify-between p-3 bg-black border border-gray-800 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-purple-500/10 rounded-lg">
                        <Gift className="w-4 h-4 text-purple-400" />
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">
                          {bonus.reason || 'Referral Bonus'}
                        </p>
                        <p className="text-gray-500 text-xs">
                          {new Date(bonus.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <p className="text-purple-400 font-bold">+${bonus.amount?.toFixed(2)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* How It Works */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">How Referral Bonuses Work</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-emerald-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-emerald-400 font-bold text-xs">1</span>
                </div>
                <p className="text-gray-400">Get 5 valid referrals → Earn <span className="text-emerald-400">$5.00</span> bonus</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-emerald-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-emerald-400 font-bold text-xs">2</span>
                </div>
                <p className="text-gray-400">Every 5 additional referrals → Earn <span className="text-emerald-400">$2.00</span> bonus</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-purple-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Gift className="w-3 h-3 text-purple-400" />
                </div>
                <p className="text-gray-400">Bonuses are credited automatically when milestones are reached</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <BottomNav />
    </div>
  );
};

export default PortalBonusTasks;
