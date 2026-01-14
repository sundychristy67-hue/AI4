import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import { ArrowLeft, Gamepad2, Wallet, Gift, Check, AlertCircle, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalLoadGame = () => {
  const navigate = useNavigate();
  const { portalToken, portalClient } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [games, setGames] = useState([]);
  const [wallet, setWallet] = useState(null);
  const [selectedGame, setSelectedGame] = useState(null);
  const [walletType, setWalletType] = useState('real');
  const [amount, setAmount] = useState('');
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [gamesRes, walletRes] = await Promise.all([
        axios.get(`${API}/portal/games`, {
          headers: { 'X-Portal-Token': portalToken }
        }),
        axios.get(`${API}/portal/wallets`, {
          headers: { 'X-Portal-Token': portalToken }
        })
      ]);
      setGames(gamesRes.data.games || []);
      setWallet(walletRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedGame || !amount || parseFloat(amount) <= 0) {
      setError('Please select a game and enter a valid amount');
      return;
    }

    const balance = walletType === 'real' ? wallet?.real_balance : wallet?.bonus_balance;
    if (parseFloat(amount) > balance) {
      setError(`Insufficient ${walletType} wallet balance`);
      return;
    }

    setError('');
    setSubmitting(true);

    try {
      const response = await axios.post(
        `${API}/portal/load-to-game`,
        {
          game_id: selectedGame.id,
          amount: parseFloat(amount),
          wallet_type: walletType
        },
        { headers: { 'X-Portal-Token': portalToken } }
      );

      setSuccess(response.data);
      setAmount('');
      setSelectedGame(null);
      fetchData(); // Refresh wallet
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to submit load request');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  const currentBalance = walletType === 'real' ? wallet?.real_balance : wallet?.bonus_balance;

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
            <h1 className="text-xl font-bold text-white">Load to Game</h1>
            <div className="w-10"></div>
          </div>
        </div>

        <div className="px-4 py-4 space-y-4">
          {/* Success Message */}
          {success && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-2">
                <Check className="w-5 h-5 text-emerald-400" />
                <p className="text-emerald-400 font-medium">Load Request Submitted!</p>
              </div>
              <p className="text-gray-400 text-sm">{success.message}</p>
              <p className="text-gray-500 text-xs mt-2">Order ID: {success.order_id?.slice(0, 8)}...</p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Wallet Selection */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Select Wallet</h3>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setWalletType('real')}
                className={`p-4 rounded-xl border-2 transition-all ${
                  walletType === 'real'
                    ? 'border-emerald-500 bg-emerald-500/10'
                    : 'border-gray-700 bg-black hover:border-gray-600'
                }`}
              >
                <Wallet className={`w-6 h-6 mx-auto mb-2 ${walletType === 'real' ? 'text-emerald-400' : 'text-gray-400'}`} />
                <p className={`font-medium ${walletType === 'real' ? 'text-emerald-400' : 'text-white'}`}>Real Wallet</p>
                <p className="text-lg font-bold text-white mt-1">${(wallet?.real_balance || 0).toFixed(2)}</p>
              </button>
              <button
                onClick={() => setWalletType('bonus')}
                className={`p-4 rounded-xl border-2 transition-all ${
                  walletType === 'bonus'
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-gray-700 bg-black hover:border-gray-600'
                }`}
              >
                <Gift className={`w-6 h-6 mx-auto mb-2 ${walletType === 'bonus' ? 'text-purple-400' : 'text-gray-400'}`} />
                <p className={`font-medium ${walletType === 'bonus' ? 'text-purple-400' : 'text-white'}`}>Bonus Wallet</p>
                <p className="text-lg font-bold text-white mt-1">${(wallet?.bonus_balance || 0).toFixed(2)}</p>
              </button>
            </div>
          </div>

          {/* Game Selection */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Select Game</h3>
            {games.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No games available</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {games.map((game) => (
                  <button
                    key={game.id}
                    onClick={() => game.has_credentials && setSelectedGame(game)}
                    disabled={!game.has_credentials}
                    className={`w-full p-3 rounded-lg border-2 text-left transition-all ${
                      selectedGame?.id === game.id
                        ? 'border-emerald-500 bg-emerald-500/10'
                        : game.has_credentials
                        ? 'border-gray-700 bg-black hover:border-gray-600'
                        : 'border-gray-800 bg-gray-900/50 opacity-50 cursor-not-allowed'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gray-800 rounded-lg">
                        <Gamepad2 className="w-5 h-5 text-gray-400" />
                      </div>
                      <div className="flex-1">
                        <p className={`font-medium ${selectedGame?.id === game.id ? 'text-emerald-400' : 'text-white'}`}>
                          {game.name}
                        </p>
                        {!game.has_credentials && (
                          <p className="text-xs text-red-400">No credentials assigned</p>
                        )}
                      </div>
                      {selectedGame?.id === game.id && (
                        <Check className="w-5 h-5 text-emerald-400" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Amount Input */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Enter Amount</h3>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">$</span>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full pl-8 pr-4 py-3 bg-black border border-gray-700 rounded-lg text-white text-lg placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                min="0"
                step="0.01"
              />
            </div>
            <p className="text-gray-500 text-sm mt-2">
              Available: ${currentBalance?.toFixed(2) || '0.00'}
            </p>
            <div className="flex gap-2 mt-3">
              {[10, 25, 50, 100].map((preset) => (
                <button
                  key={preset}
                  onClick={() => setAmount(preset.toString())}
                  className="flex-1 py-2 bg-gray-800 text-white text-sm rounded-lg hover:bg-gray-700 transition-colors"
                >
                  ${preset}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={submitting || !selectedGame || !amount || parseFloat(amount) <= 0}
            className="w-full py-4 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold rounded-xl hover:from-emerald-600 hover:to-teal-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Submitting...
              </>
            ) : (
              'Submit Load Request'
            )}
          </button>

          {/* Info Note */}
          <div className="bg-blue-900/20 border border-blue-700/50 rounded-xl p-4">
            <p className="text-blue-400 text-sm">
              <strong>Note:</strong> Load requests require confirmation. You'll be notified once your load is processed.
            </p>
          </div>
        </div>
      </div>

      <BottomNav />
    </div>
  );
};

export default PortalLoadGame;
