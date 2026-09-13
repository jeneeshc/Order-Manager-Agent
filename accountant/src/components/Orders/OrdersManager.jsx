import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Package,
  Search, 
  RefreshCw, 
  Receipt, 
  Clock, 
  Sparkles, 
  Layers, 
  Cpu, 
  Calendar, 
  Phone, 
  User, 
  Info, 
  ChevronRight, 
  FileText,
  ExternalLink,
  XCircle,
  RotateCcw
} from 'lucide-react';
import { storageService, parseCurrency, parseInteger } from '../../services/storageService';
import { googleSheetsService } from '../../services/googleSheetsService';

export default function OrdersManager({ onGenerateInvoice }) {
  const [orders, setOrders] = useState(() => storageService.getOrders());
  const [customers, setCustomers] = useState(() => storageService.getCustomers());
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('Estimated');
  const [selectedReasoningOrder, setSelectedReasoningOrder] = useState(null);
  const [updatingOrderId, setUpdatingOrderId] = useState(null);

  // Subscribe to storage changes
  useEffect(() => {
    return storageService.subscribe(() => {
      setOrders(storageService.getOrders());
      setCustomers(storageService.getCustomers());
    });
  }, []);

  // Helper to map Customer ID & Name to Customer Details
  const resolveCustomer = (customerId, customerName = '', orderPhone = '') => {
    if (!customerId && !customerName) return { name: 'Unknown Customer', phone: '' };
    const cleanId = String(customerId || '').trim().toLowerCase();
    const cleanName = String(customerName || '').trim().toLowerCase();
    const match = customers.find(c => 
      (cleanId && String(c.id).trim().toLowerCase() === cleanId) || 
      (cleanId && String(c.name).trim().toLowerCase() === cleanId) ||
      (cleanName && String(c.name).trim().toLowerCase() === cleanName)
    );
    if (match) {
      return {
        name: match.name,
        phone: orderPhone || match.phone || '',
        address: match.address || '',
        isKnown: true
      };
    }
    return {
      name: customerName || customerId || 'Unknown Customer',
      phone: orderPhone || '',
      isKnown: false
    };
  };

  // Helper to construct pre-filled invoice payload from AI order
  const buildInvoicePayload = (order) => {
    const cust = resolveCustomer(order.customerId, order.customerName, order.phone);
    const customerDisplayName = order.customerName || cust.name;
    const parts = [
      order.templateName,
      order.orderType || order.embroideryType || 'Machine Embroidery',
      order.material ? `on ${order.material}` : '',
      order.quantity > 1 ? `(Qty: ${order.quantity})` : ''
    ].filter(Boolean);
    const descriptionText = (parts.length > 0 ? parts.join(' ') : 'Machine Embroidery') + ` (AI Order: ${order.id})`;

    const lHrs = parseFloat(order.laborHours || 0) || 0;
    const lMins = order.laborMinutes !== undefined ? order.laborMinutes : Math.round(lHrs * 60);

    return {
      orderId: order.id,
      customer: customerDisplayName,
      customerPhone: order.phone || cust.phone || '',
      customerAddress: cust.address || '',
      serviceType: order.orderType || 'Machine Embroidery',
      description: descriptionText,
      totalStitches: order.stitchCount || 0,
      laborMinutes: lMins,
      laborHrs: lHrs,
      laborHours: lHrs,
      estimatedCost: parseCurrency(order.estimatedCost),
      status: 'Pending',
      imageUrl: order.imageUrl || order['Image URL'] || ''
    };
  };

  // Status helpers
  const isOrderComplete = (status) => {
    const s = (status || '').trim().toLowerCase();
    return s === 'complete' || s === 'completed';
  };

  const isOrderCancelled = (status) => {
    const s = (status || '').trim().toLowerCase();
    return s === 'cancelled' || s === 'canceled' || s === 'dropped' || s === 'lost' || s === 'rejected';
  };

  const isOrderEstimated = (status) => {
    return !isOrderComplete(status) && !isOrderCancelled(status);
  };

  // Update order status handler (Estimated | Cancelled)
  const handleUpdateStatus = async (order, newStatus) => {
    setUpdatingOrderId(order.id);
    try {
      storageService.updateOrderStatus(order.id, newStatus);
      setOrders(storageService.getOrders());
      googleSheetsService.updateOrderStatus(order.id, newStatus).catch(() => {});
    } catch (err) {
      console.warn('Status update error:', err);
    } finally {
      setUpdatingOrderId(null);
    }
  };

  // Filter orders
  const filteredOrders = orders.filter(order => {
    const cust = resolveCustomer(order.customerId, order.customerName, order.phone);
    const matchesSearch = 
      order.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.customerId?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.customerName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cust.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.phone?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.material?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.orderType?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.templateName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.embroideryType?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.machine?.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filterStatus === 'All') return true;
    if (filterStatus === 'Estimated') return isOrderEstimated(order.status);
    if (filterStatus === 'Complete') return isOrderComplete(order.status);
    if (filterStatus === 'Cancelled') return isOrderCancelled(order.status);
    return true;
  });

  // KPI Metrics
  const totalOrdersCount = orders.length;
  const estimatedOrders = orders.filter(o => isOrderEstimated(o.status));
  const completedOrders = orders.filter(o => isOrderComplete(o.status));
  const cancelledOrders = orders.filter(o => isOrderCancelled(o.status));

  // Pipeline value (strictly active pending estimated orders)
  const totalEstimatedPipeline = estimatedOrders.reduce((sum, o) => sum + parseCurrency(o.estimatedCost), 0);

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header & Sync Action */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '24px',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              padding: '8px',
              borderRadius: '12px',
              background: 'rgba(245, 158, 11, 0.15)',
              color: 'var(--accent-gold)'
            }}>
              <Package size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.75rem', margin: 0 }}>
                Orders
              </h2>
            </div>
          </div>
        </div>
      </div>



      {/* Top Stat KPI Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        {/* Estimated Orders Action Needed */}
        <div className="glass-panel" style={{
          padding: '20px',
          borderLeft: '4px solid var(--accent-gold)',
          background: estimatedOrders.length > 0 ? 'rgba(245, 158, 11, 0.06)' : undefined
        }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Action Needed (Estimated)
          </div>
          <div className="stat-val" style={{ fontSize: '1.8rem', color: 'var(--accent-gold)' }}>
            {estimatedOrders.length} {estimatedOrders.length === 1 ? 'Order' : 'Orders'}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Awaiting Invoice / Payment
          </div>
        </div>

        {/* Estimated Pipeline Value */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Active Pipeline Value
          </div>
          <div className="stat-val" style={{ fontSize: '1.8rem', color: '#ffffff' }}>
            ₹{totalEstimatedPipeline.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Pending estimated revenue
          </div>
        </div>

        {/* Completed Orders */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Completed & Paid
          </div>
          <div className="stat-val" style={{ fontSize: '1.8rem', color: 'var(--accent-emerald)' }}>
            {completedOrders.length}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Payment settled & delivered
          </div>
        </div>

        {/* Cancelled */}
        <div className="glass-panel" style={{
          padding: '20px',
          borderLeft: cancelledOrders.length > 0 ? '4px solid #ef4444' : undefined
        }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Cancelled
          </div>
          <div className="stat-val" style={{ fontSize: '1.8rem', color: '#f87171' }}>
            {cancelledOrders.length}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Estimates cancelled / dropped
          </div>
        </div>

        {/* Total Orders */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Total Orders Logged
          </div>
          <div className="stat-val" style={{ fontSize: '1.8rem', color: 'var(--accent-indigo)' }}>
            {totalOrdersCount}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            All orders received via AI Agent
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel" style={{
        padding: '16px 20px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        {/* Search Input */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: 'var(--bg-input)',
          padding: '8px 14px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          flex: '1',
          minWidth: '240px',
          maxWidth: '420px'
        }}>
          <Search size={18} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search Order ID, customer, material, machine..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              outline: 'none',
              width: '100%',
              fontSize: '0.9rem'
            }}
          />
        </div>

        {/* Status Filter Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { key: 'Estimated', label: `Estimated (${estimatedOrders.length})` },
            { key: 'Complete', label: `Complete (${completedOrders.length})` },
            { key: 'Cancelled', label: `Cancelled (${cancelledOrders.length})` },
            { key: 'All', label: `All (${totalOrdersCount})` }
          ].map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className="btn"
              style={{
                padding: '6px 14px',
                fontSize: '0.82rem',
                background: filterStatus === key ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                borderColor: filterStatus === key ? 'var(--accent-gold)' : 'var(--border-subtle)',
                color: filterStatus === key ? '#fbbf24' : 'var(--text-secondary)'
              }}
              onClick={() => setFilterStatus(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Orders Table Container */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(255, 255, 255, 0.02)', borderBottom: '1px solid var(--border-subtle)' }}>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Order ID</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Date & Target</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Customer & Contact</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Embroidery & Fabric</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Stitches / Machine</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Est. Cost</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Status</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <Bot size={36} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                    <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
                      {filterStatus === 'Estimated'
                        ? 'No Estimated Orders Pending!'
                        : filterStatus === 'Cancelled'
                        ? 'No Cancelled Orders'
                        : filterStatus === 'Complete'
                        ? 'No Completed Orders'
                        : 'No orders found matching your criteria.'}
                    </div>
                    <div style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                      {filterStatus === 'Estimated'
                        ? 'All orders from the AI Agent have been invoiced, completed, or archived.'
                        : 'Try selecting a different status filter above.'}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => {
                  const cust = resolveCustomer(order.customerId, order.customerName, order.phone);
                  const isComplete = isOrderComplete(order.status);
                  const isCancelled = isOrderCancelled(order.status);
                  const isEstimated = isOrderEstimated(order.status);
                  const isUpdating = updatingOrderId === order.id;

                  return (
                    <tr
                      key={order.id}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background 0.15s ease',
                        background: isCancelled
                          ? 'rgba(239, 68, 68, 0.02)'
                          : isEstimated
                          ? 'rgba(245, 158, 11, 0.02)'
                          : 'transparent',
                        opacity: isCancelled ? 0.82 : 1
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = isCancelled ? 'rgba(239, 68, 68, 0.02)' : isEstimated ? 'rgba(245, 158, 11, 0.02)' : 'transparent'}
                    >
                      {/* Order ID */}
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ fontWeight: 700, fontFamily: 'var(--font-heading)', color: isCancelled ? '#94a3b8' : '#fbbf24', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>{order.id}</span>
                        </div>
                        {order.reasoning && (
                          <button
                            type="button"
                            onClick={() => setSelectedReasoningOrder(order)}
                            title="View AI Agent decision log"
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--text-muted)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              cursor: 'pointer',
                              padding: '2px 4px',
                              marginTop: '4px',
                              borderRadius: '4px'
                            }}
                          >
                            <Info size={13} />
                          </button>
                        )}
                      </td>

                      {/* Date & Delivery Target */}
                      <td style={{ padding: '14px 18px', fontSize: '0.84rem' }}>
                        <div style={{ color: 'var(--text-secondary)' }}>
                          {order.orderDate ? order.orderDate.split(' ')[0] : 'N/A'}
                        </div>
                        {order.estimatedDeliveryDate && order.estimatedDeliveryDate !== 'Unknown' && (
                          <div style={{ fontSize: '0.74rem', color: isCancelled ? 'var(--text-muted)' : 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                            <Clock size={12} />
                            <span>Target: {order.estimatedDeliveryDate}</span>
                          </div>
                        )}
                      </td>

                      {/* Customer & Phone */}
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <User size={13} style={{ color: 'var(--text-muted)' }} />
                          <span style={{ textDecoration: isCancelled ? 'line-through' : 'none' }}>
                            {order.customerName || cust.name}
                          </span>
                          {order.customerId && (
                            <span style={{ fontSize: '0.68rem', background: 'rgba(255,255,255,0.06)', padding: '2px 5px', borderRadius: '4px', color: 'var(--text-muted)' }}>
                              #{order.customerId}
                            </span>
                          )}
                        </div>
                        {(order.phone || cust.phone) && (
                          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                            <Phone size={12} style={{ color: 'var(--accent-emerald)' }} />
                            <span>{order.phone || cust.phone}</span>
                          </div>
                        )}
                      </td>

                      {/* Embroidery Type & Material / Template */}
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ fontWeight: 600, color: isCancelled ? '#cbd5e1' : '#ffffff', fontSize: '0.88rem' }}>
                          {order.templateName || order.orderType || order.embroideryType || 'Custom Embroidery'}
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                          {order.templateName && order.orderType ? (
                            <span>{order.orderType}</span>
                          ) : order.material ? (
                            <span>Material: <span style={{ color: 'var(--text-secondary)' }}>{order.material}</span></span>
                          ) : (
                            <span>Embroidery Service</span>
                          )}
                          {order.quantity > 1 && (
                            <span style={{ marginLeft: '6px', color: 'var(--accent-gold)' }}>• Qty: {order.quantity}</span>
                          )}
                        </div>
                      </td>

                      {/* Stitches / Machine */}
                      <td style={{ padding: '14px 18px', fontSize: '0.86rem' }}>
                        <div style={{ color: isCancelled ? 'var(--text-muted)' : 'var(--accent-indigo)', fontWeight: 600 }}>
                          {(order.stitchCount || 0).toLocaleString()} stitches
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                            <Cpu size={12} />
                            <span>{order.machine || 'Auto'}</span>
                          </span>
                          {(order.laborMinutes > 0 || order.laborHours > 0) && (
                            <span style={{ color: 'var(--text-secondary)' }}>
                              • {order.laborMinutes ? `${order.laborMinutes}m` : `${Math.round((order.laborHours || 0) * 60)}m`}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Est. Cost */}
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ fontWeight: 700, fontSize: '0.96rem', color: isCancelled ? '#94a3b8' : '#fbbf24', fontFamily: 'var(--font-heading)' }}>
                          ₹{parseCurrency(order.estimatedCost).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </div>
                      </td>

                      {/* Status */}
                      <td style={{ padding: '14px 18px' }}>
                        {isComplete ? (
                          <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <Check size={12} />
                            <span>Complete</span>
                          </span>
                        ) : isCancelled ? (
                          <span className="badge" style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            background: 'rgba(239, 68, 68, 0.15)',
                            color: '#f87171',
                            border: '1px solid rgba(239, 68, 68, 0.3)'
                          }}>
                            <XCircle size={12} />
                            <span>Cancelled</span>
                          </span>
                        ) : (
                          <span className="badge badge-gold" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <Clock size={12} />
                            <span>Estimated</span>
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '8px', alignItems: 'center' }}>
                          {/* Active Estimated Order Actions */}
                          {isEstimated && (
                            <>
                              {/* Generate Invoice Button */}
                              <button
                                type="button"
                                className="btn btn-primary"
                                style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                                onClick={() => onGenerateInvoice && onGenerateInvoice(buildInvoicePayload(order))}
                                title="Generate a pre-filled invoice for this order"
                              >
                                <Receipt size={14} />
                                <span>Generate Invoice</span>
                              </button>

                              {/* Cancel Button */}
                              <button
                                type="button"
                                className="btn btn-ghost"
                                style={{
                                  padding: '6px 10px',
                                  fontSize: '0.82rem',
                                  color: '#f87171',
                                  border: '1px solid rgba(239, 68, 68, 0.3)',
                                  background: 'rgba(239, 68, 68, 0.08)'
                                }}
                                onClick={() => handleUpdateStatus(order, 'Cancelled')}
                                disabled={isUpdating}
                                title="Customer cancelled or did not proceed"
                              >
                                <XCircle size={14} />
                                <span>Cancel</span>
                              </button>
                            </>
                          )}

                          {/* Cancelled / Unmaterialized Order Actions */}
                          {isCancelled && (
                            <>
                              {/* Reopen Order Button */}
                              <button
                                type="button"
                                className="btn btn-secondary"
                                style={{ padding: '6px 12px', fontSize: '0.82rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                                onClick={() => handleUpdateStatus(order, 'Estimated')}
                                disabled={isUpdating}
                                title="Customer decided to proceed: Reopen back to Estimated"
                              >
                                {isUpdating ? (
                                  <RefreshCw size={14} className="spin-animation" />
                                ) : (
                                  <RotateCcw size={14} />
                                )}
                                <span>{isUpdating ? 'Saving...' : 'Reopen Order'}</span>
                              </button>

                              {/* Generate Invoice button */}
                              <button
                                type="button"
                                className="btn btn-ghost"
                                style={{ padding: '6px 10px', fontSize: '0.82rem', opacity: 0.8 }}
                                onClick={() => onGenerateInvoice && onGenerateInvoice(buildInvoicePayload(order))}
                                title="Generate invoice for this order"
                              >
                                <Receipt size={14} />
                                <span>Invoice</span>
                              </button>
                            </>
                          )}

                          {/* Completed Order Actions */}
                          {isComplete && (
                            <button
                              type="button"
                              className="btn btn-secondary"
                              style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                              onClick={() => handleUpdateStatus(order, 'Estimated')}
                              disabled={isUpdating}
                              title="Click to revert back to Estimated"
                            >
                              {isUpdating ? (
                                <RefreshCw size={14} className="spin-animation" />
                              ) : (
                                <CheckCircle2 size={14} style={{ color: 'var(--accent-emerald)' }} />
                              )}
                              <span>{isUpdating ? 'Saving...' : 'Complete ✓'}</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI Reasoning Modal / Dialog */}
      {selectedReasoningOrder && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{
            maxWidth: '680px',
            width: '100%',
            maxHeight: '85vh',
            overflowY: 'auto',
            padding: '28px',
            position: 'relative'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Bot size={22} style={{ color: 'var(--accent-gold)' }} />
                <h3 style={{ fontSize: '1.25rem' }}>AI Agent Decision & Routing Log</h3>
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setSelectedReasoningOrder(null)}
                style={{ padding: '6px 10px' }}
              >
                ✕ Close
              </button>
            </div>

            <div style={{ marginBottom: '16px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <div className="badge badge-gold">Order ID: {selectedReasoningOrder.id}</div>
              <div className="badge badge-indigo">Machine: {selectedReasoningOrder.machine}</div>
              <div className="badge badge-emerald">Stitches: {selectedReasoningOrder.stitchCount?.toLocaleString()}</div>
            </div>

            <div style={{
              background: 'rgba(0, 0, 0, 0.5)',
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              fontFamily: 'monospace',
              fontSize: '0.82rem',
              lineHeight: 1.6,
              color: '#e2e8f0',
              whiteSpace: 'pre-wrap'
            }}>
              {selectedReasoningOrder.reasoning || 'No logic recorded for this order.'}
            </div>

            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  const ord = selectedReasoningOrder;
                  setSelectedReasoningOrder(null);
                  if (onGenerateInvoice) {
                    onGenerateInvoice(buildInvoicePayload(ord));
                  }
                }}
              >
                <Receipt size={16} />
                <span>Proceed to Generate Invoice</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Helper CSS for animation */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin-animation {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}
