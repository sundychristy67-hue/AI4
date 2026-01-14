import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const PortalRoute = ({ children }) => {
  const { isPortalAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!isPortalAuthenticated) {
    return <Navigate to="/client-login" replace />;
  }

  return children;
};

export default PortalRoute;
