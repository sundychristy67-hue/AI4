import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { 
  Send, Settings, CheckCircle, XCircle, RefreshCw, 
  MessageCircle, Bell, Copy, Check, ExternalLink, AlertTriangle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminTelegramSetup = () => {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [chatId, setChatId] = useState('');
  const [saving, setSaving] = useState(false);
  const [testType, setTestType] = useState('deposit');
  const [copied, setCopied] = useState(false);

  const config = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API}/admin/telegram-admin/status`, config);
      setStatus(response.data);
      if (response.data.admin_chat_id_db) {
        setChatId(response.data.admin_chat_id_db);
      }
    } catch (error) {
      console.error('Failed to fetch Telegram status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSetup = async () => {
    if (!chatId.trim()) {
      alert('Please enter your Telegram Chat ID');
      return;
    }

    setSaving(true);
    try {
      await axios.post(`${API}/admin/telegram-admin/setup`, {
        admin_chat_id: chatId.trim()
      }, config);
      
      alert('Telegram bot configured! Check your Telegram for a confirmation message.');
      await fetchStatus();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to configure Telegram');
    } finally {
      setSaving(false);
    }
  };

  const handleSendTest = async (type) => {
    try {
      await axios.post(`${API}/admin/telegram-admin/send-notification`, {
        notification_type: type,
        client_name: "Test Client",
        amount: 100.00,
        order_id: `test-${Date.now()}`
      }, config);
      
      alert(`Test ${type} notification sent! Check your Telegram.`);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to send test notification');
    }
  };

  const handleSendPendingSummary = async () => {
    try {
      const response = await axios.post(`${API}/admin/telegram-admin/send-pending-summary`, {}, config);
      alert(`Pending orders summary sent! (${response.data.orders_count} orders)`);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to send summary');
    }
  };

  const copyBotLink = () => {
    navigator.clipboard.writeText('https://t.me/theultimateaitbot');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="telegram-setup">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Telegram Bot Setup</h1>
          <p className="text-gray-400 text-sm">Configure Telegram notifications for payment alerts</p>
        </div>
        <button
          onClick={fetchStatus}
          className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
        >
          <RefreshCw className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* Status Card */}
      <div className={`rounded-xl p-5 border ${
        status?.ready_to_send 
          ? 'bg-emerald-500/10 border-emerald-500/30' 
          : 'bg-yellow-500/10 border-yellow-500/30'
      }`}>
        <div className="flex items-center gap-3 mb-4">
          {status?.ready_to_send ? (
            <CheckCircle className="w-8 h-8 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-8 h-8 text-yellow-400" />
          )}
          <div>
            <h3 className={`font-bold text-lg ${status?.ready_to_send ? 'text-emerald-400' : 'text-yellow-400'}`}>
              {status?.ready_to_send ? 'Bot Connected & Ready' : 'Setup Required'}
            </h3>
            <p className="text-gray-400 text-sm">
              {status?.ready_to_send 
                ? 'You will receive payment notifications on Telegram'
                : 'Configure your Chat ID to receive notifications'
              }
            </p>
          </div>
        </div>

        {status?.bot_info && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-black/30 rounded-lg p-3">
              <p className="text-gray-400 text-xs">Bot Username</p>
              <p className="text-white font-mono">@{status.bot_info.bot_username}</p>
            </div>
            <div className="bg-black/30 rounded-lg p-3">
              <p className="text-gray-400 text-xs">Bot Name</p>
              <p className="text-white">{status.bot_info.bot_name}</p>
            </div>
          </div>
        )}

        {status?.error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
            <p className="text-red-400 text-sm">{status.error}</p>
          </div>
        )}
      </div>

      {/* Setup Instructions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-bold mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5 text-blue-400" />
          Setup Instructions
        </h3>

        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-blue-400 font-bold">1</span>
            </div>
            <div className="flex-1">
              <p className="text-white font-medium">Open the Bot on Telegram</p>
              <div className="flex items-center gap-2 mt-2">
                <a
                  href="https://t.me/theultimateaitbot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition flex items-center gap-2"
                >
                  <MessageCircle className="w-4 h-4" />
                  Open Bot
                  <ExternalLink className="w-3 h-3" />
                </a>
                <button
                  onClick={copyBotLink}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition flex items-center gap-2"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied!' : 'Copy Link'}
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-blue-400 font-bold">2</span>
            </div>
            <div>
              <p className="text-white font-medium">Send /start to the bot</p>
              <p className="text-gray-400 text-sm">The bot will reply with your Chat ID</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-blue-400 font-bold">3</span>
            </div>
            <div className="flex-1">
              <p className="text-white font-medium">Enter your Chat ID below</p>
              <div className="flex gap-2 mt-2">
                <input
                  type="text"
                  value={chatId}
                  onChange={(e) => setChatId(e.target.value)}
                  placeholder="Enter your Telegram Chat ID"
                  className="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleSetup}
                  disabled={saving || !chatId.trim()}
                  className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium rounded-lg transition flex items-center gap-2"
                >
                  {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                  {saving ? 'Saving...' : 'Save & Test'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Test Notifications */}
      {status?.ready_to_send && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-bold mb-4 flex items-center gap-2">
            <Bell className="w-5 h-5 text-purple-400" />
            Test Notifications
          </h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <button
              onClick={() => handleSendTest('deposit')}
              className="p-4 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 rounded-lg transition text-center"
            >
              <span className="text-2xl mb-2 block">💰</span>
              <span className="text-white font-medium text-sm">Test Deposit</span>
            </button>

            <button
              onClick={() => handleSendTest('withdrawal')}
              className="p-4 bg-blue-500/10 border border-blue-500/30 hover:bg-blue-500/20 rounded-lg transition text-center"
            >
              <span className="text-2xl mb-2 block">🏧</span>
              <span className="text-white font-medium text-sm">Test Withdrawal</span>
            </button>

            <button
              onClick={handleSendPendingSummary}
              className="p-4 bg-purple-500/10 border border-purple-500/30 hover:bg-purple-500/20 rounded-lg transition text-center"
            >
              <span className="text-2xl mb-2 block">📋</span>
              <span className="text-white font-medium text-sm">Send Pending</span>
            </button>

            <button
              onClick={() => handleSendTest('custom')}
              className="p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition text-center"
            >
              <span className="text-2xl mb-2 block">📨</span>
              <span className="text-white font-medium text-sm">Custom Message</span>
            </button>
          </div>

          <p className="text-gray-500 text-xs mt-3">
            Click any button to send a test notification to your Telegram
          </p>
        </div>
      )}

      {/* Bot Commands Reference */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-bold mb-4 flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-amber-400" />
          Telegram Bot Commands
        </h3>

        <div className="space-y-2 font-mono text-sm">
          <div className="flex justify-between p-2 bg-black rounded">
            <span className="text-blue-400">/start</span>
            <span className="text-gray-400">Get your Chat ID</span>
          </div>
          <div className="flex justify-between p-2 bg-black rounded">
            <span className="text-blue-400">/pending</span>
            <span className="text-gray-400">View pending orders</span>
          </div>
          <div className="flex justify-between p-2 bg-black rounded">
            <span className="text-blue-400">/confirm [order_id]</span>
            <span className="text-gray-400">Confirm an order</span>
          </div>
          <div className="flex justify-between p-2 bg-black rounded">
            <span className="text-blue-400">/reject [order_id] [reason]</span>
            <span className="text-gray-400">Reject an order</span>
          </div>
          <div className="flex justify-between p-2 bg-black rounded">
            <span className="text-blue-400">/edit [order_id] [amount] [reason]</span>
            <span className="text-gray-400">Edit order amount</span>
          </div>
          <div className="flex justify-between p-2 bg-black rounded">
            <span className="text-blue-400">/help</span>
            <span className="text-gray-400">Show all commands</span>
          </div>
        </div>

        <p className="text-gray-500 text-xs mt-3">
          You can also use inline buttons on payment notifications to confirm/reject/edit orders
        </p>
      </div>
    </div>
  );
};

export default AdminTelegramSetup;
