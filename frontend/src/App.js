import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import './App.css';

// Components
import PortalRoute from './components/PortalRoute';
import AdminRoute from './components/AdminRoute';
import AdminLayout from './components/AdminLayout';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import PublicGames from './pages/PublicGames';

// Portal Pages
import PortalLanding from './pages/portal/PortalLanding';
import PortalDashboard from './pages/portal/PortalDashboard';
import PortalTransactions from './pages/portal/PortalTransactions';
import PortalCredentials from './pages/portal/PortalCredentials';
import PortalReferrals from './pages/portal/PortalReferrals';
import PortalWithdrawals from './pages/portal/PortalWithdrawals';
import PortalWallets from './pages/portal/PortalWallets';
import PortalLoadGame from './pages/portal/PortalLoadGame';
import PortalBonusTasks from './pages/portal/PortalBonusTasks';
import ClientLogin from './pages/portal/ClientLogin';
import PortalSecuritySettings from './pages/portal/PortalSecuritySettings';

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminClients from './pages/admin/AdminClients';
import AdminClientDetail from './pages/admin/AdminClientDetail';
import AdminOrders from './pages/admin/AdminOrders';
import AdminGames from './pages/admin/AdminGames';
import AdminAuditLogs from './pages/admin/AdminAuditLogs';
import AdminSettings from './pages/admin/AdminSettings';
import AdminAITestSpot from './pages/admin/AdminAITestSpot';
import AdminPaymentPanel from './pages/admin/AdminPaymentPanel';
import AdminTelegramSetup from './pages/admin/AdminTelegramSetup';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-black">
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/games" element={<PublicGames />} />
            
            {/* Portal Magic Link Landing */}
            <Route path="/p/:token" element={<PortalLanding />} />
            
            {/* Protected Portal routes */}
            <Route path="/portal" element={
              <PortalRoute>
                <PortalDashboard />
              </PortalRoute>
            } />
            <Route path="/portal/transactions" element={
              <PortalRoute>
                <PortalTransactions />
              </PortalRoute>
            } />
            <Route path="/portal/credentials" element={
              <PortalRoute>
                <PortalCredentials />
              </PortalRoute>
            } />
            <Route path="/portal/referrals" element={
              <PortalRoute>
                <PortalReferrals />
              </PortalRoute>
            } />
            <Route path="/portal/withdrawals" element={
              <PortalRoute>
                <PortalWithdrawals />
              </PortalRoute>
            } />
            <Route path="/portal/wallets" element={
              <PortalRoute>
                <PortalWallets />
              </PortalRoute>
            } />
            <Route path="/portal/load-game" element={
              <PortalRoute>
                <PortalLoadGame />
              </PortalRoute>
            } />
            <Route path="/portal/bonus-tasks" element={
              <PortalRoute>
                <PortalBonusTasks />
              </PortalRoute>
            } />
            <Route path="/portal/security" element={
              <PortalRoute>
                <PortalSecuritySettings />
              </PortalRoute>
            } />
            
            {/* Client Login (optional password auth) */}
            <Route path="/client-login" element={<ClientLogin />} />
            
            {/* Protected Admin routes */}
            <Route path="/admin" element={
              <AdminRoute>
                <AdminLayout />
              </AdminRoute>
            }>
              <Route index element={<AdminDashboard />} />
              <Route path="clients" element={<AdminClients />} />
              <Route path="clients/:clientId" element={<AdminClientDetail />} />
              <Route path="orders" element={<AdminOrders />} />
              <Route path="games" element={<AdminGames />} />
              <Route path="payment-panel" element={<AdminPaymentPanel />} />
              <Route path="telegram" element={<AdminTelegramSetup />} />
              <Route path="ai-test" element={<AdminAITestSpot />} />
              <Route path="audit-logs" element={<AdminAuditLogs />} />
              <Route path="settings" element={<AdminSettings />} />
            </Route>
            
            {/* Default redirect to public games (no login required) */}
            <Route path="/" element={<Navigate to="/games" replace />} />
            <Route path="*" element={<Navigate to="/games" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
