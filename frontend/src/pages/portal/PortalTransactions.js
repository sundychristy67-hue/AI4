import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import BottomNav from '../../components/BottomNav';
import { ArrowLeft, TrendingUp, TrendingDown, DollarSign, Filter } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PortalTransactions = () => {
  const navigate = useNavigate();
  const { portalToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [filter, setFilter] = useState('all');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  useEffect(() => {
    fetchTransactions();
  }, [filter]);

  const fetchTransactions = async () => {
    try {
      let url = `${API}/portal/transactions`;
      if (filter !== 'all') {
        url += `?type_filter=${filter}`;
      }
      const response = await axios.get(url, {
        headers: { 'X-Portal-Token': portalToken }
      });
      setTransactions(response.data);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'IN':
        return <TrendingUp className="w-5 h-5 text-emerald-400" />;
      case 'OUT':
        return <TrendingDown className="w-5 h-5 text-red-400" />;
      case 'REFERRAL_EARN':
        return <DollarSign className="w-5 h-5 text-blue-400" />;
      default:
        return <DollarSign className="w-5 h-5 text-gray-400" />;
    }
  };

  const getTypeLabel = (type) => {
    switch (type) {
      case 'IN': return 'Deposit';
      case 'OUT': return 'Withdrawal';
      case 'REFERRAL_EARN': return 'Referral Bonus';
      case 'ADJUST': return 'Adjustment';
      default: return type;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  const totals = transactions.reduce((acc, tx) => {
    if (tx.status === 'confirmed') {
      if (tx.type === 'IN') acc.in += tx.amount;
      else if (tx.type === 'OUT') acc.out += tx.amount;
    }
    return acc;
  }, { in: 0, out: 0 });

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
            <h1 className="text-xl font-bold text-white">Transactions</h1>
            <div className="w-10"></div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-black border border-emerald-500/20 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Total In</p>
              <p className="text-emerald-400 text-xl font-bold">${totals.in.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-red-500/20 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Total Out</p>
              <p className="text-red-400 text-xl font-bold">${totals.out.toFixed(2)}</p>
            </div>
          </div>

          {/* Filter */}
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className="w-full px-4 py-2 bg-black border border-gray-700 rounded-lg text-white text-sm flex items-center justify-between hover:border-gray-600 transition-colors"
            >
              <span className="flex items-center gap-2">
                <Filter className="w-4 h-4" />
                Filter: {filter === 'all' ? 'All' : getTypeLabel(filter)}
              </span>
            </button>
            {showFilterMenu && (
              <div className="absolute top-full mt-2 left-0 right-0 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-20">
                {['all', 'IN', 'OUT', 'REFERRAL_EARN'].map((f, idx) => (
                  <button
                    key={f}
                    onClick={() => { setFilter(f); setShowFilterMenu(false); }}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-800 transition-colors ${
                      filter === f ? 'text-emerald-400 font-medium' : 'text-white'
                    } ${idx !== 3 ? 'border-b border-gray-800' : ''}`}
                  >
                    {f === 'all' ? 'All Transactions' : getTypeLabel(f)}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Transaction List */}
        <div className="px-4 py-4 space-y-3">
          {transactions.length === 0 ? (
            <div className="text-center py-12">
              <DollarSign className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No transactions found</p>
            </div>
          ) : (
            transactions.map((tx) => (
              <div
                key={tx.transaction_id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      tx.type === 'IN' ? 'bg-emerald-500/10' :
                      tx.type === 'OUT' ? 'bg-red-500/10' : 'bg-blue-500/10'
                    }`}>
                      {getTypeIcon(tx.type)}
                    </div>
                    <div>
                      <p className="text-white font-medium">{getTypeLabel(tx.type)}</p>
                      <p className="text-gray-500 text-xs">
                        {new Date(tx.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-bold ${
                      tx.type === 'OUT' ? 'text-red-400' : 'text-emerald-400'
                    }`}>
                      {tx.type === 'OUT' ? '-' : '+'}${tx.amount?.toFixed(2)}
                    </p>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      tx.status === 'confirmed' ? 'bg-emerald-500/10 text-emerald-400' :
                      tx.status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>
                      {tx.status}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  );
};

export default PortalTransactions;
