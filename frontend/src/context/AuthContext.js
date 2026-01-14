import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [portalClient, setPortalClient] = useState(() => {
    // Try to restore portal client from sessionStorage for faster re-renders
    const cached = sessionStorage.getItem('portalClient');
    return cached ? JSON.parse(cached) : null;
  });
  const [portalToken, setPortalToken] = useState(localStorage.getItem('portalToken'));
  const [clientToken, setClientToken] = useState(localStorage.getItem('clientToken')); // For password auth
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      // Check for regular auth token
      if (token) {
        try {
          const response = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setUser(response.data);
        } catch (error) {
          console.error('Token validation failed:', error);
          localStorage.removeItem('token');
          setToken(null);
        }
      }
      
      // Check for client JWT token (password auth)
      const storedClientToken = localStorage.getItem('clientToken');
      if (storedClientToken) {
        try {
          const response = await axios.get(`${API}/portal/auth/status`, {
            headers: { Authorization: `Bearer ${storedClientToken}` }
          });
          if (response.data.client_id) {
            setPortalClient({
              client_id: response.data.client_id,
              display_name: response.data.display_name
            });
            setClientToken(storedClientToken);
            sessionStorage.setItem('portalClient', JSON.stringify({
              client_id: response.data.client_id,
              display_name: response.data.display_name
            }));
            setLoading(false);
            return; // Client auth validated, skip portal token check
          }
        } catch (error) {
          console.error('Client token validation failed:', error);
          localStorage.removeItem('clientToken');
          setClientToken(null);
        }
      }
      
      // Check for portal token (magic link)
      const storedPortalToken = localStorage.getItem('portalToken');
      if (storedPortalToken) {
        try {
          const response = await axios.get(`${API}/portal/validate/${storedPortalToken}`);
          if (response.data.valid) {
            setPortalClient(response.data.client);
            setPortalToken(storedPortalToken);
            // Cache portal client for faster navigation
            sessionStorage.setItem('portalClient', JSON.stringify(response.data.client));
          } else {
            localStorage.removeItem('portalToken');
            sessionStorage.removeItem('portalClient');
            setPortalToken(null);
            setPortalClient(null);
          }
        } catch (error) {
          console.error('Portal token validation failed:', error);
          localStorage.removeItem('portalToken');
          sessionStorage.removeItem('portalClient');
          setPortalToken(null);
          setPortalClient(null);
        }
      }
      
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
    
    return userData;
  };

  const register = async (email, password, username, referralCode) => {
    const response = await axios.post(`${API}/auth/register`, {
      email,
      password,
      username,
      referral_code: referralCode
    });
    
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
    
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('portalToken');
    localStorage.removeItem('clientToken');
    sessionStorage.removeItem('portalClient');
    setToken(null);
    setPortalToken(null);
    setClientToken(null);
    setUser(null);
    setPortalClient(null);
  };

  const validatePortalToken = async (newToken) => {
    try {
      const response = await axios.get(`${API}/portal/validate/${newToken}`);
      if (response.data.valid) {
        localStorage.setItem('portalToken', newToken);
        setPortalToken(newToken);
        setPortalClient(response.data.client);
        // Cache portal client for faster navigation
        sessionStorage.setItem('portalClient', JSON.stringify(response.data.client));
        return true;
      }
      return false;
    } catch (error) {
      console.error('Portal token validation failed:', error);
      return false;
    }
  };

  const clientPasswordLogin = async (username, password) => {
    try {
      const response = await axios.post(`${API}/portal/auth/login`, { username, password });
      
      if (response.data.success) {
        const { access_token, client_id, display_name } = response.data;
        
        localStorage.setItem('clientToken', access_token);
        setClientToken(access_token);
        
        const clientData = { client_id, display_name };
        setPortalClient(clientData);
        sessionStorage.setItem('portalClient', JSON.stringify(clientData));
        
        return { success: true };
      }
      
      return { success: false, message: response.data.message };
    } catch (error) {
      console.error('Client login failed:', error);
      return { success: false, message: error.response?.data?.detail || 'Login failed' };
    }
  };

  const value = {
    user,
    portalClient,
    portalToken,
    clientToken,
    token,
    loading,
    isAuthenticated: !!user,
    isPortalAuthenticated: !!(portalClient || clientToken),
    isAdmin: user?.role === 'admin',
    login,
    register,
    logout,
    validatePortalToken,
    clientPasswordLogin
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
