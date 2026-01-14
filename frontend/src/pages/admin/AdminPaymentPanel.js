import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { 
  CreditCard, AlertTriangle, Check, X, Edit3, RefreshCw, 
  DollarSign, User, Clock, ChevronRight, Plus, Search,
  ArrowDownCircle, ArrowUpCircle, FileText, Eye, Wallet
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminPaymentPanel = () => {
  const { token } = useAuth();
  const [pendingPayments, setPendingPayments] = useState([]);
  const [testStats, setTestStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showSimulateModal, setShowSimulateModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [testOnly, setTestOnly] = useState(false);
  const [processing, setProcessing] = useState(false);

  // Simulate form state
  const [simulateForm, setSimulateForm] = useState({
    client_id: '',
    amount: '',
    payment_type: 'cashin',
    payment_method: 'GCash',
    notes: ''
  });

  // Adjustment form state
  const [adjustAmount, setAdjustAmount] = useState('');
  const [adjustReason, setAdjustReason] = useState('');
  const [rejectReason, setRejectReason] = useState('');

  const [clients, setClients] = useState([]);
  const [clientSearch, setClientSearch] = useState('');

  const config = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchPendingPayments();
    fetchTestStats();
    fetchClients();
  }, [testOnly]);

  const fetchPendingPayments = async () => {
    try {
      const response = await axios.get(
        `${API}/admin/test/payment/pending?test_only=${testOnly}`, 
        config
      );
      setPendingPayments(response.data.orders || []);
    } catch (error) {
      console.error('Failed to fetch pending payments:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTestStats = async () => {
    try {
      const response = await axios.get(`${API}/admin/test/data/stats`, config);
      setTestStats(response.data.stats);
    } catch (error) {
      console.error('Failed to fetch test stats:', error);
    }
  };

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/admin/clients`, config);
      setClients(response.data || []);
    } catch (error) {
      console.error('Failed to fetch clients:', error);
    }
  };

  const handleSimulatePayment = async () => {
    if (!simulateForm.client_id || !simulateForm.amount) return;
    
    setProcessing(true);
    try {
      await axios.post(`${API}/admin/test/payment/simulate`, {
        client_id: simulateForm.client_id,
        amount: parseFloat(simulateForm.amount),
        payment_type: simulateForm.payment_type,
        payment_method: simulateForm.payment_method,
        notes: simulateForm.notes
      }, config);
      
      setShowSimulateModal(false);
      setSimulateForm({
        client_id: '',
        amount: '',
        payment_type: 'cashin',
        payment_method: 'GCash',
        notes: ''
      });
      fetchPendingPayments();
      fetchTestStats();
    } catch (error) {
      console.error('Failed to simulate payment:', error);
      alert('Failed to simulate payment: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setProcessing(false);
    }
  };

  const handlePaymentAction = async (orderId, action, extraData = {}) => {
    setProcessing(true);
    try {
      await axios.post(`${API}/admin/test/payment/action`, {
        order_id: orderId,
        action: action,
        ...extraData
      }, config);
      
      setShowDetailModal(false);
      setSelectedOrder(null);
      setAdjustAmount('');
      setAdjustReason('');
      setRejectReason('');
      fetchPendingPayments();
      fetchTestStats();
    } catch (error) {
      console.error('Failed to process action:', error);
      alert('Failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setProcessing(false);
    }
  };

  const viewOrderDetail = async (orderId) => {
    try {
      const response = await axios.get(`${API}/admin/test/payment/order/${orderId}`, config);
      setSelectedOrder(response.data);
      setShowDetailModal(true);
    } catch (error) {
      console.error('Failed to fetch order detail:', error);
    }
  };

  const createTestClient = async () => {
    try {
      const response = await axios.post(`${API}/admin/test/data/create-test-client`, {}, config);
      fetchClients();
      alert(`Test client created: ${response.data.client.display_name} (ID: ${response.data.client.client_id})`);
    } catch (error) {
      console.error('Failed to create test client:', error);
    }
  };

  const filteredClients = clients.filter(c => 
    c.display_name?.toLowerCase().includes(clientSearch.toLowerCase()) ||
    c.client_id.includes(clientSearch)
  );

  return (
    <div className="space-y-6" data-testid="payment-panel">
      {/* Test Mode Warning Banner */}
      <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-yellow-400 flex-shrink-0" />
          <div>
            <h3 className="text-yellow-400 font-bold">TEMPORARY PAYMENT VERIFICATION PANEL</h3>
            <p className="text-yellow-300/80 text-sm">
              This panel replaces Telegram/Chatwoot payment verification temporarily. 
              Use to simulate and verify payments during development.
            </p>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-blue-400" />
            </div>
            <span className="text-gray-400 text-sm">Pending Payments</span>
          </div>
          <div className="text-2xl font-bold text-white">{testStats?.pending_payments || 0}</div>
        </div>
        
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-gray-400 text-sm">Test Orders</span>
          </div>
          <div className="text-2xl font-bold text-white">{testStats?.test_orders || 0}</div>
        </div>
        
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <User className="w-5 h-5 text-emerald-400" />
            </div>
            <span className="text-gray-400 text-sm">Test Clients</span>
          </div>
          <div className="text-2xl font-bold text-white">{testStats?.test_clients || 0}</div>
        </div>
        
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-orange-500/20 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-orange-400" />
            </div>
            <span className="text-gray-400 text-sm">AI Tests</span>
          </div>
          <div className="text-2xl font-bold text-white">{testStats?.ai_test_conversations || 0}</div>
        </div>
      </div>

      {/* Actions Bar */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex gap-3">
          <button
            onClick={() => setShowSimulateModal(true)}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white font-medium rounded-lg transition flex items-center gap-2"
            data-testid="simulate-payment-btn"
          >
            <Plus className="w-4 h-4" />
            Simulate Payment
          </button>
          <button
            onClick={createTestClient}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-lg transition flex items-center gap-2"
          >
            <User className="w-4 h-4" />
            Create Test Client
          </button>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={testOnly}
              onChange={(e) => setTestOnly(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-emerald-500 focus:ring-emerald-500"
            />
            <span className="text-gray-400 text-sm">Show test orders only</span>
          </label>
          <button
            onClick={fetchPendingPayments}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Pending Payments List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-lg font-bold text-white">Pending Payment Verification</h2>
          <p className="text-gray-400 text-sm">Mark payments as received, failed, or adjust amounts</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
          </div>
        ) : pendingPayments.length === 0 ? (
          <div className="text-center py-12">
            <CreditCard className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No pending payments</p>
            <p className="text-gray-500 text-sm">Simulate a payment to test the verification flow</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {pendingPayments.map(order => (
              <div key={order.order_id} className="p-4 hover:bg-gray-800/50 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      order.order_type === 'create' ? 'bg-emerald-500/20' : 'bg-red-500/20'
                    }`}>
                      {order.order_type === 'create' ? (
                        <ArrowDownCircle className="w-6 h-6 text-emerald-400" />
                      ) : (
                        <ArrowUpCircle className="w-6 h-6 text-red-400" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{order.client_name}</span>
                        {order.is_test && (
                          <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                            TEST
                          </span>
                        )}
                      </div>
                      <div className="text-gray-400 text-sm">
                        {order.order_type === 'create' ? 'Cash-in / Load' : 'Cash-out / Redeem'} 
                        • {order.payment_method || 'N/A'}
                      </div>
                      <div className="text-gray-500 text-xs">
                        {new Date(order.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className={`text-xl font-bold ${
                        order.order_type === 'create' ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {order.order_type === 'create' ? '+' : '-'}${order.amount?.toFixed(2)}
                      </div>
                      {order.original_amount && order.original_amount !== order.amount && (
                        <div className="text-gray-500 text-xs line-through">
                          ${order.original_amount?.toFixed(2)}
                        </div>
                      )}
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={() => handlePaymentAction(order.order_id, 'received')}
                        disabled={processing}
                        className="p-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-lg transition"
                        title="Mark as Received"
                        data-testid={`mark-received-${order.order_id}`}
                      >
                        <Check className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => viewOrderDetail(order.order_id)}
                        className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition"
                        title="View Details / Adjust"
                        data-testid={`view-detail-${order.order_id}`}
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Mark this payment as FAILED?')) {
                            handlePaymentAction(order.order_id, 'failed', { reason: 'Payment not received' });
                          }
                        }}
                        disabled={processing}
                        className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition"
                        title="Mark as Failed"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Simulate Payment Modal */}
      {showSimulateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-gray-800">
              <h3 className="text-lg font-bold text-white">Simulate Payment</h3>
              <p className="text-gray-400 text-sm">Create a test payment for verification</p>
            </div>

            <div className="p-6 space-y-4">
              {/* Client Search */}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Client</label>
                <input
                  type="text"
                  value={clientSearch}
                  onChange={(e) => setClientSearch(e.target.value)}
                  placeholder="Search clients..."
                  className="w-full bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-emerald-500 mb-2"
                />
                <select
                  value={simulateForm.client_id}
                  onChange={(e) => setSimulateForm({...simulateForm, client_id: e.target.value})}
                  className="w-full bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-emerald-500"
                  data-testid="client-select"
                >
                  <option value="">Select a client...</option>
                  {filteredClients.map(client => (
                    <option key={client.client_id} value={client.client_id}>
                      {client.display_name} ({client.client_id.substring(0, 8)}...)
                    </option>
                  ))}
                </select>
              </div>

              {/* Payment Type */}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Payment Type</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setSimulateForm({...simulateForm, payment_type: 'cashin'})}
                    className={`p-3 rounded-lg border transition flex items-center justify-center gap-2 ${
                      simulateForm.payment_type === 'cashin'
                        ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400'
                        : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    <ArrowDownCircle className="w-5 h-5" />
                    Cash-In
                  </button>
                  <button
                    type="button"
                    onClick={() => setSimulateForm({...simulateForm, payment_type: 'cashout'})}
                    className={`p-3 rounded-lg border transition flex items-center justify-center gap-2 ${
                      simulateForm.payment_type === 'cashout'
                        ? 'border-red-500 bg-red-500/20 text-red-400'
                        : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    <ArrowUpCircle className="w-5 h-5" />
                    Cash-Out
                  </button>
                </div>
              </div>

              {/* Amount */}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Amount</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type="number"
                    value={simulateForm.amount}
                    onChange={(e) => setSimulateForm({...simulateForm, amount: e.target.value})}
                    placeholder="0.00"
                    className="w-full bg-gray-800 text-white pl-10 pr-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-emerald-500"
                    data-testid="amount-input"
                  />
                </div>
              </div>

              {/* Payment Method */}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Payment Method</label>
                <select
                  value={simulateForm.payment_method}
                  onChange={(e) => setSimulateForm({...simulateForm, payment_method: e.target.value})}
                  className="w-full bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-emerald-500"
                >
                  <option value="GCash">GCash</option>
                  <option value="PayMaya">PayMaya</option>
                  <option value="Bank Transfer">Bank Transfer</option>
                  <option value="Cash">Cash</option>
                </select>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Notes (optional)</label>
                <input
                  type="text"
                  value={simulateForm.notes}
                  onChange={(e) => setSimulateForm({...simulateForm, notes: e.target.value})}
                  placeholder="Test notes..."
                  className="w-full bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-800 flex gap-3 justify-end">
              <button
                onClick={() => setShowSimulateModal(false)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSimulatePayment}
                disabled={processing || !simulateForm.client_id || !simulateForm.amount}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium rounded-lg transition"
                data-testid="confirm-simulate-btn"
              >
                {processing ? 'Creating...' : 'Create Payment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Order Detail Modal */}
      {showDetailModal && selectedOrder && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-800">
              <h3 className="text-lg font-bold text-white">Payment Details</h3>
              {selectedOrder.is_test && (
                <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                  TEST ORDER
                </span>
              )}
            </div>

            <div className="p-6 space-y-6">
              {/* Order Info */}
              <div className="bg-gray-800 rounded-lg p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Order ID</span>
                  <span className="text-white font-mono text-sm">{selectedOrder.order?.order_id?.substring(0, 16)}...</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Client</span>
                  <span className="text-white">{selectedOrder.client?.display_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Type</span>
                  <span className="text-white">{selectedOrder.order?.order_type === 'create' ? 'Cash-In' : 'Cash-Out'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Amount</span>
                  <span className={`text-lg font-bold ${
                    selectedOrder.order?.order_type === 'create' ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    ${selectedOrder.order?.amount?.toFixed(2)}
                  </span>
                </div>
                {selectedOrder.order?.original_amount && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Original Amount</span>
                    <span className="text-gray-500 line-through">${selectedOrder.order?.original_amount?.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-400">Status</span>
                  <span className="text-yellow-400">{selectedOrder.order?.status}</span>
                </div>
              </div>

              {/* Wallet Balance */}
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Wallet className="w-4 h-4 text-blue-400" />
                  <span className="text-gray-300">Current Wallet Balance</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-gray-400 text-sm">Real</div>
                    <div className="text-white font-bold">${selectedOrder.wallet?.real_balance?.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-sm">Bonus</div>
                    <div className="text-purple-400 font-bold">${selectedOrder.wallet?.bonus_balance?.toFixed(2)}</div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              {selectedOrder.available_actions?.length > 0 && (
                <div className="space-y-4">
                  {/* Adjust Amount */}
                  <div className="bg-gray-800 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <Edit3 className="w-4 h-4 text-blue-400" />
                      Adjust Amount
                    </h4>
                    <div className="flex gap-3">
                      <input
                        type="number"
                        value={adjustAmount}
                        onChange={(e) => setAdjustAmount(e.target.value)}
                        placeholder="New amount"
                        className="flex-1 bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-blue-500"
                      />
                      <button
                        onClick={() => handlePaymentAction(selectedOrder.order?.order_id, 'adjust', {
                          new_amount: parseFloat(adjustAmount),
                          reason: adjustReason || 'Amount adjusted by admin'
                        })}
                        disabled={!adjustAmount || processing}
                        className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded-lg transition"
                      >
                        Adjust
                      </button>
                    </div>
                    <input
                      type="text"
                      value={adjustReason}
                      onChange={(e) => setAdjustReason(e.target.value)}
                      placeholder="Reason for adjustment"
                      className="w-full mt-2 bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  {/* Quick Actions */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => handlePaymentAction(selectedOrder.order?.order_id, 'received')}
                      disabled={processing}
                      className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
                    >
                      <Check className="w-5 h-5" />
                      Mark as Received
                    </button>
                    <button
                      onClick={() => {
                        const reason = prompt('Enter rejection reason:');
                        if (reason) {
                          handlePaymentAction(selectedOrder.order?.order_id, 'failed', { reason });
                        }
                      }}
                      disabled={processing}
                      className="flex-1 py-3 bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
                    >
                      <X className="w-5 h-5" />
                      Mark as Failed
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-800">
              <button
                onClick={() => {
                  setShowDetailModal(false);
                  setSelectedOrder(null);
                }}
                className="w-full py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPaymentPanel;
