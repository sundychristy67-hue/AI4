import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Lock, User, Eye, EyeOff, Check, AlertCircle, Shield } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalSecuritySettings = () => {
  const { portalToken, clientToken } = useAuth();
  const [authStatus, setAuthStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  
  const [form, setForm] = useState({
    username: '',
    password: '',
    confirmPassword: ''
  });

  useEffect(() => {
    fetchAuthStatus();
  }, []);

  const getAuthHeaders = () => {
    if (clientToken) {
      return { Authorization: `Bearer ${clientToken}` };
    } else if (portalToken) {
      return { 'X-Portal-Token': portalToken };
    }
    return {};
  };

  const fetchAuthStatus = async () => {
    try {
      const response = await axios.get(`${API}/portal/auth/status`, {
        headers: getAuthHeaders()
      });
      setAuthStatus(response.data);
      if (response.data.username) {
        setForm(f => ({ ...f, username: response.data.username }));
      }
    } catch (err) {
      console.error('Failed to fetch auth status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSetupPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validate
    if (form.username.length < 3) {
      setError('Username must be at least 3 characters');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setSaving(true);
    try {
      const response = await axios.post(`${API}/portal/auth/setup-password`, {
        username: form.username,
        password: form.password
      }, {
        headers: getAuthHeaders()
      });

      if (response.data.success) {
        setSuccess('Password set up successfully! You can now log in with your username and password.');
        setAuthStatus(prev => ({ ...prev, password_auth_enabled: true, username: form.username }));
        setForm(f => ({ ...f, password: '', confirmPassword: '' }));
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to set up password');
    } finally {
      setSaving(false);
    }
  };

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
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
          <Shield className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Security Settings</h2>
          <p className="text-sm text-gray-400">Manage your account security</p>
        </div>
      </div>

      {/* Password Auth Status */}
      <div className={`p-4 rounded-xl border ${
        authStatus?.password_auth_enabled 
          ? 'bg-emerald-500/10 border-emerald-500/30' 
          : 'bg-gray-800 border-gray-700'
      }`}>
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
            authStatus?.password_auth_enabled ? 'bg-emerald-500/20' : 'bg-gray-700'
          }`}>
            {authStatus?.password_auth_enabled ? (
              <Check className="w-5 h-5 text-emerald-400" />
            ) : (
              <Lock className="w-5 h-5 text-gray-400" />
            )}
          </div>
          <div className="flex-1">
            <p className="font-medium text-white">
              {authStatus?.password_auth_enabled ? 'Password Login Enabled' : 'Password Login Not Set Up'}
            </p>
            <p className="text-sm text-gray-400">
              {authStatus?.password_auth_enabled 
                ? `Username: ${authStatus.username}` 
                : 'Set up a username and password to log in directly'}
            </p>
          </div>
        </div>
      </div>

      {/* Success Message */}
      {success && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-start gap-3">
          <Check className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <p className="text-emerald-400 text-sm">{success}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Setup/Update Form */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          {authStatus?.password_auth_enabled ? 'Update Password' : 'Set Up Password Login'}
        </h3>

        <form onSubmit={handleSetupPassword} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Username</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type="text"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase() })}
                className="w-full pl-10 pr-4 py-3 bg-black border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                placeholder="Choose a username"
                required
                minLength={3}
                maxLength={50}
                disabled={authStatus?.password_auth_enabled}
                data-testid="security-username"
              />
            </div>
            {authStatus?.password_auth_enabled && (
              <p className="text-xs text-gray-500 mt-1">Username cannot be changed</p>
            )}
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">
              {authStatus?.password_auth_enabled ? 'New Password' : 'Password'}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full pl-10 pr-12 py-3 bg-black border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                placeholder="Enter password (min 6 characters)"
                required
                minLength={6}
                data-testid="security-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Confirm Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type={showConfirm ? 'text' : 'password'}
                value={form.confirmPassword}
                onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                className="w-full pl-10 pr-12 py-3 bg-black border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                placeholder="Confirm your password"
                required
                data-testid="security-confirm-password"
              />
              <button
                type="button"
                onClick={() => setShowConfirm(!showConfirm)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showConfirm ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full py-3 bg-emerald-500 text-white font-semibold rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50"
            data-testid="security-submit"
          >
            {saving ? 'Saving...' : (authStatus?.password_auth_enabled ? 'Update Password' : 'Set Up Password Login')}
          </button>
        </form>
      </div>

      {/* Info Box */}
      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
        <p className="text-blue-400 text-sm">
          <strong>Note:</strong> Password login is optional. You can always access your account via the magic link sent to your messenger.
        </p>
      </div>
    </div>
  );
};

export default PortalSecuritySettings;
