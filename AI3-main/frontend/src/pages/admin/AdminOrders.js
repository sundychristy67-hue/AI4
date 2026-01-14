import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { 
  ShoppingCart, Clock, CheckCircle, XCircle, Edit2, Eye, X, 
  AlertCircle, User, Wallet, Gift, CreditCard, ArrowDownRight, ArrowUpRight 
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminOrders = () => {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editAmount, setEditAmount] = useState('');
  const [editReason, setEditReason] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchOrders();
  }, [statusFilter, typeFilter]);

  const fetchOrders = async () => {
    try {
      let url = `${API}/admin/orders`;
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('status_filter', statusFilter);
      if (typeFilter !== 'all') params.append('type_filter', typeFilter);
      if (params.toString()) url += `?${params.toString()}`;
      
      const response = await axios.get(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrders(response.data);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrderDetail = async (orderId) => {
    try {
      const response = await axios.get(`${API}/admin/orders/${orderId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedOrder(response.data);
      setShowDetailModal(true);
    } catch (error) {
      console.error('Failed to fetch order detail:', error);
      alert('Failed to load order details');
    }
  };

  const handleConfirm = async (orderId) => {
    if (!confirm('Are you sure you want to confirm this order?')) return;
    
    setProcessing(true);
    try {
      await axios.post(`${API}/admin/orders/${orderId}/confirm`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Order confirmed successfully');
      fetchOrders();
      setShowDetailModal(false);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to confirm order');
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async (orderId) => {
    if (!rejectReason.trim()) {
      alert('Please provide a reason for rejection');
      return;
    }
    
    setProcessing(true);
    try {
      await axios.post(`${API}/admin/orders/${orderId}/reject?reason=${encodeURIComponent(rejectReason)}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Order rejected');
      fetchOrders();
      setShowDetailModal(false);
      setRejectReason('');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reject order');
    } finally {
      setProcessing(false);
    }
  };

  const handleEditAmount = async () => {
    if (!editAmount || parseFloat(editAmount) <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    if (!editReason.trim()) {
      alert('Please provide a reason for the edit');
      return;
    }
    
    setProcessing(true);
    try {
      await axios.put(`${API}/admin/orders/${selectedOrder.order.order_id}/edit`, {
        new_amount: parseFloat(editAmount),
        reason: editReason
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Amount updated successfully');
      setShowEditModal(false);
      setEditAmount('');
      setEditReason('');
      fetchOrderDetail(selectedOrder.order.order_id);
      fetchOrders();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to update amount');
    } finally {
      setProcessing(false);
    }
  };

  const openEditModal = () => {
    setEditAmount(selectedOrder.order.amount.toString());
    setEditReason('');
    setShowEditModal(true);
  };

  const getStatusBadge = (status) => {
    const badges = {
      'confirmed': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      'rejected': 'bg-red-500/10 text-red-400 border-red-500/20',
      'cancelled': 'bg-gray-500/10 text-gray-400 border-gray-500/20',
      'pending_confirmation': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      'pending_payout': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      'pending_screenshot': 'bg-purple-500/10 text-purple-400 border-purple-500/20'
    };
    const labels = {
      'confirmed': 'Confirmed',
      'rejected': 'Rejected',
      'cancelled': 'Cancelled',
      'pending_confirmation': 'Pending Confirm',
      'pending_payout': 'Pending Payout',
      'pending_screenshot': 'Awaiting Screenshot'
    };
    return (
      <span className={`px-2 py-1 text-xs rounded-full border ${badges[status] || badges.cancelled}`}>
        {labels[status] || status}
      </span>
    );
  };

  const getTypeBadge = (type) => {
    const colors = {
      'load': 'bg-emerald-500/10 text-emerald-400',
      'redeem': 'bg-red-500/10 text-red-400',
      'create': 'bg-blue-500/10 text-blue-400'
    };
    return (
      <span className={`px-2 py-1 text-xs rounded-full ${colors[type] || 'bg-gray-500/10 text-gray-400'}`}>
        {type}
      </span>
    );
  };

  const isPending = (status) => ['pending_confirmation', 'pending_payout', 'pending_screenshot'].includes(status);

  const pendingCount = orders.filter(o => isPending(o.status)).length;

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Orders</h1>
          <p className="text-gray-400 text-sm">
            {orders.length} total orders
            {pendingCount > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-yellow-500/10 text-yellow-400 rounded-full text-xs">
                {pendingCount} pending
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="all">All Status</option>
          <option value="pending_confirmation">Pending Confirmation</option>
          <option value="pending_payout">Pending Payout</option>
          <option value="confirmed">Confirmed</option>
          <option value="rejected">Rejected</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="all">All Types</option>
          <option value="load">Load</option>
          <option value="redeem">Redeem/Withdraw</option>
          <option value="create">Create Account</option>
        </select>
      </div>

      {/* Orders List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {orders.length === 0 ? (
          <div className="p-8 text-center">
            <ShoppingCart className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No orders found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Order</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Type</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Game</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Wallet</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Amount</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Status</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Date</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr
                    key={order.order_id}
                    className={`border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${
                      isPending(order.status) ? 'bg-yellow-500/5' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <p className="text-white font-mono text-sm">{order.order_id.slice(0, 8)}...</p>
                    </td>
                    <td className="px-4 py-3">{getTypeBadge(order.order_type)}</td>
                    <td className="px-4 py-3 text-white">{order.game}</td>
                    <td className="px-4 py-3">
                      {order.wallet_type === 'bonus' ? (
                        <span className="flex items-center gap-1 text-purple-400 text-sm">
                          <Gift className="w-3 h-3" /> Bonus
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-emerald-400 text-sm">
                          <Wallet className="w-3 h-3" /> Real
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p className={`font-bold ${
                        order.order_type === 'redeem' ? 'text-red-400' : 'text-emerald-400'
                      }`}>
                        ${order.amount?.toFixed(2)}
                      </p>
                      {order.original_amount && order.original_amount !== order.amount && (
                        <p className="text-xs text-yellow-400">
                          (was ${order.original_amount.toFixed(2)})
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(order.status)}</td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {new Date(order.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => fetchOrderDetail(order.order_id)}
                          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {isPending(order.status) && (
                          <>
                            <button
                              onClick={() => handleConfirm(order.order_id)}
                              className="p-2 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                              title="Confirm"
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Order Detail Modal */}
      {showDetailModal && selectedOrder && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowDetailModal(false)}>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">Order Details</h3>
              <button onClick={() => setShowDetailModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Order Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div className="space-y-4">
                <div>
                  <p className="text-gray-500 text-xs mb-1">Order ID</p>
                  <p className="text-white font-mono text-sm">{selectedOrder.order.order_id}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Type</p>
                  {getTypeBadge(selectedOrder.order.order_type)}
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Game</p>
                  <p className="text-white">{selectedOrder.order.game}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Wallet Type</p>
                  <p className={selectedOrder.order.wallet_type === 'bonus' ? 'text-purple-400' : 'text-emerald-400'}>
                    {selectedOrder.order.wallet_type === 'bonus' ? 'Bonus Wallet' : 'Real Wallet'}
                  </p>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <p className="text-gray-500 text-xs mb-1">Status</p>
                  {getStatusBadge(selectedOrder.order.status)}
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Amount</p>
                  <p className={`text-2xl font-bold ${
                    selectedOrder.order.order_type === 'redeem' ? 'text-red-400' : 'text-emerald-400'
                  }`}>
                    ${selectedOrder.order.amount?.toFixed(2)}
                  </p>
                  {selectedOrder.order.original_amount && selectedOrder.order.original_amount !== selectedOrder.order.amount && (
                    <p className="text-yellow-400 text-sm">
                      Original: ${selectedOrder.order.original_amount.toFixed(2)}
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Created</p>
                  <p className="text-white text-sm">{new Date(selectedOrder.order.created_at).toLocaleString()}</p>
                </div>
                {selectedOrder.order.confirmed_at && (
                  <div>
                    <p className="text-gray-500 text-xs mb-1">Confirmed At</p>
                    <p className="text-white text-sm">{new Date(selectedOrder.order.confirmed_at).toLocaleString()}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Client Info */}
            {selectedOrder.client && (
              <div className="bg-black/50 border border-gray-800 rounded-lg p-4 mb-6">
                <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                  <User className="w-4 h-4 text-gray-400" />
                  Client Information
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Name</p>
                    <p className="text-white">{selectedOrder.client.display_name}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Status</p>
                    <p className={selectedOrder.client.status === 'active' ? 'text-emerald-400' : 'text-red-400'}>
                      {selectedOrder.client.status}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500">Referral Code</p>
                    <p className="text-emerald-400 font-mono">{selectedOrder.client.referral_code}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Client ID</p>
                    <p className="text-gray-400 font-mono text-xs">{selectedOrder.client.client_id.slice(0, 12)}...</p>
                  </div>
                </div>
              </div>
            )}

            {/* Transaction Info */}
            {selectedOrder.transaction && (
              <div className="bg-black/50 border border-gray-800 rounded-lg p-4 mb-6">
                <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-gray-400" />
                  Transaction
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Transaction ID</p>
                    <p className="text-gray-400 font-mono text-xs">{selectedOrder.transaction.transaction_id.slice(0, 12)}...</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Type</p>
                    <p className="text-white">{selectedOrder.transaction.type}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Status</p>
                    <p className={selectedOrder.transaction.status === 'confirmed' ? 'text-emerald-400' : 'text-yellow-400'}>
                      {selectedOrder.transaction.status}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500">Source</p>
                    <p className="text-gray-400">{selectedOrder.transaction.source}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Rejection Reason (if rejected) */}
            {selectedOrder.order.rejection_reason && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
                <h4 className="text-red-400 font-medium mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  Rejection Reason
                </h4>
                <p className="text-white">{selectedOrder.order.rejection_reason}</p>
              </div>
            )}

            {/* Actions for Pending Orders */}
            {isPending(selectedOrder.order.status) && (
              <div className="space-y-4">
                <div className="border-t border-gray-800 pt-4">
                  <h4 className="text-white font-medium mb-4">Actions</h4>
                  
                  {/* Edit Amount Section */}
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 mb-4">
                    <p className="text-yellow-400 text-sm mb-3">
                      <strong>Edit Before Confirm:</strong> You can adjust the amount before confirming this order.
                    </p>
                    <button
                      onClick={openEditModal}
                      className="px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors flex items-center gap-2"
                    >
                      <Edit2 className="w-4 h-4" />
                      Edit Amount
                    </button>
                  </div>

                  {/* Confirm/Reject Buttons */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleConfirm(selectedOrder.order.order_id)}
                      disabled={processing}
                      className="flex-1 py-3 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <CheckCircle className="w-5 h-5" />
                      Confirm Order
                    </button>
                    <button
                      onClick={() => {
                        const reason = prompt('Enter rejection reason:');
                        if (reason) {
                          setRejectReason(reason);
                          handleReject(selectedOrder.order.order_id);
                        }
                      }}
                      disabled={processing}
                      className="flex-1 py-3 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <XCircle className="w-5 h-5" />
                      Reject Order
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit Amount Modal */}
      {showEditModal && selectedOrder && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowEditModal(false)}>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">Edit Order Amount</h3>
              <button onClick={() => setShowEditModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-gray-500 text-sm mb-2">Current Amount</p>
                <p className="text-2xl font-bold text-white">${selectedOrder.order.amount?.toFixed(2)}</p>
                {selectedOrder.order.original_amount && (
                  <p className="text-yellow-400 text-sm">Original: ${selectedOrder.order.original_amount.toFixed(2)}</p>
                )}
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-2">New Amount</label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                  <input
                    type="number"
                    value={editAmount}
                    onChange={(e) => setEditAmount(e.target.value)}
                    className="w-full pl-8 pr-4 py-3 bg-black border border-gray-700 rounded-lg text-white text-lg focus:outline-none focus:border-emerald-500"
                    step="0.01"
                    min="0"
                  />
                </div>
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-2">Reason for Edit *</label>
                <textarea
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  className="w-full px-4 py-3 bg-black border border-gray-700 rounded-lg text-white resize-none focus:outline-none focus:border-emerald-500"
                  rows={3}
                  placeholder="e.g., Customer requested adjustment, Screenshot shows different amount"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEditAmount}
                  disabled={processing || !editReason.trim()}
                  className="flex-1 py-3 bg-yellow-500 text-black font-semibold rounded-lg hover:bg-yellow-400 transition-colors disabled:opacity-50"
                >
                  {processing ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminOrders;
