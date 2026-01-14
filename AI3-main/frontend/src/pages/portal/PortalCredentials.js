import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import { ArrowLeft, Key, Eye, EyeOff, Gamepad2, AlertCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalCredentials = () => {
  const navigate = useNavigate();
  const { portalToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [credentials, setCredentials] = useState([]);
  const [revealedCredential, setRevealedCredential] = useState(null);
  const [revealLoading, setRevealLoading] = useState(null);
  const [revealTimer, setRevealTimer] = useState(0);

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    try {
      const response = await axios.get(`${API}/portal/credentials`, {
        headers: { 'X-Portal-Token': portalToken }
      });
      setCredentials(response.data);
    } catch (error) {
      console.error('Failed to fetch credentials:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let interval;
    if (revealTimer > 0) {
      interval = setInterval(() => {
        setRevealTimer((prev) => {
          if (prev <= 1) {
            setRevealedCredential(null);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [revealTimer]);

  const handleReveal = async (gameId) => {
    if (revealLoading === gameId) return;
    
    setRevealLoading(gameId);
    try {
      const response = await axios.post(
        `${API}/portal/credentials/${gameId}/reveal`,
        {},
        { headers: { 'X-Portal-Token': portalToken } }
      );
      
      setRevealedCredential({ gameId, ...response.data });
      setRevealTimer(response.data.expires_in_seconds || 15);
    } catch (error) {
      console.error('Failed to reveal credentials:', error);
      alert(error.response?.data?.detail || 'Failed to reveal credentials');
    } finally {
      setRevealLoading(null);
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
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/portal')}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-6 h-6 text-gray-400" />
            </button>
            <h1 className="text-xl font-bold text-white">Game Credentials</h1>
            <div className="w-10"></div>
          </div>
        </div>

        {/* Credentials List */}
        <div className="px-4 py-4 space-y-4">
          {credentials.length === 0 ? (
            <div className="text-center py-12">
              <Gamepad2 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 mb-2">No game credentials yet</p>
              <p className="text-gray-500 text-sm">Create an account through Messenger to get started</p>
            </div>
          ) : (
            credentials.map((cred) => {
              const isRevealed = revealedCredential?.gameId === cred.game_id;
              const isNotSet = cred.game_user_id === '[Not Set]';
              const isSuspended = cred.game_user_id === '[Game Suspended]';
              
              return (
                <div
                  key={cred.id}
                  className={`bg-gray-900 border rounded-xl p-4 ${
                    !cred.is_active ? 'border-gray-800 opacity-60' : 'border-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-emerald-500/10 rounded-lg">
                        <Gamepad2 className="w-6 h-6 text-emerald-400" />
                      </div>
                      <div>
                        <h3 className="text-white font-semibold">{cred.game_name}</h3>
                        <p className={`text-xs ${cred.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
                          {cred.is_active ? 'Active' : 'Inactive'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {isSuspended ? (
                    <div className="flex items-center text-yellow-400 text-sm bg-yellow-500/10 rounded-lg p-3">
                      <AlertCircle className="w-4 h-4 mr-2" />
                      Game is currently suspended
                    </div>
                  ) : isNotSet ? (
                    <div className="flex items-center text-gray-400 text-sm bg-gray-800 rounded-lg p-3">
                      <AlertCircle className="w-4 h-4 mr-2" />
                      Credentials not yet assigned
                    </div>
                  ) : (
                    <>
                      <div className="space-y-3">
                        <div>
                          <label className="text-gray-500 text-xs">Username</label>
                          <div className="bg-black border border-gray-700 px-3 py-2 rounded-lg font-mono text-white">
                            {isRevealed ? revealedCredential.game_user_id : cred.game_user_id}
                          </div>
                        </div>
                        <div>
                          <label className="text-gray-500 text-xs">Password</label>
                          <div className="bg-black border border-gray-700 px-3 py-2 rounded-lg font-mono text-white">
                            {isRevealed ? revealedCredential.game_password : cred.game_password}
                          </div>
                        </div>
                      </div>

                      {isRevealed ? (
                        <div className="flex items-center justify-between mt-4 text-sm">
                          <span className="text-yellow-400">
                            Hiding in {revealTimer}s
                          </span>
                          <button
                            onClick={() => { setRevealedCredential(null); setRevealTimer(0); }}
                            className="flex items-center text-gray-400 hover:text-white"
                          >
                            <EyeOff className="w-4 h-4 mr-1" />
                            Hide Now
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleReveal(cred.game_id)}
                          disabled={revealLoading === cred.game_id || !cred.is_active}
                          className="w-full mt-4 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          {revealLoading === cred.game_id ? (
                            <span className="animate-spin">⏳</span>
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                          Reveal Credentials
                        </button>
                      )}
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  );
};

export default PortalCredentials;
