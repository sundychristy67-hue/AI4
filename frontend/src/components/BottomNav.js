import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, Receipt, Wallet, Users, Gift } from 'lucide-react';

const BottomNav = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const tabs = [
    { id: 'home', label: 'Home', icon: Home, path: '/portal' },
    { id: 'wallets', label: 'Wallets', icon: Wallet, path: '/portal/wallets' },
    { id: 'transactions', label: 'History', icon: Receipt, path: '/portal/transactions' },
    { id: 'referrals', label: 'Referrals', icon: Users, path: '/portal/referrals' },
    { id: 'bonus', label: 'Bonus', icon: Gift, path: '/portal/bonus-tasks' }
  ];

  const isActive = (tab) => {
    if (tab.path === '/portal') {
      return location.pathname === '/portal';
    }
    return location.pathname.startsWith(tab.path);
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 z-50">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center justify-around px-2 py-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = isActive(tab);

            return (
              <button
                key={tab.id}
                onClick={() => navigate(tab.path)}
                className={`flex flex-col items-center justify-center gap-1 py-2 px-3 rounded-lg transition-all ${
                  active ? 'text-emerald-400' : 'text-gray-400 hover:text-gray-300'
                }`}
                data-testid={`bottom-nav-${tab.id}`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs font-medium">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default BottomNav;
