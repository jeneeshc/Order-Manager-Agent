import React, { useState, useEffect } from 'react';
import { 
  ReceiptText, 
  PlusCircle, 
  Search, 
  Filter, 
  Printer, 
  CheckCircle2, 
  Clock, 
  Trash2, 
  Eye, 
  FileText,
  DollarSign,
  TrendingUp,
  Download
} from 'lucide-react';
import { storageService, parseCurrency, parseInteger } from '../../services/storageService';
import { googleSheetsService } from '../../services/googleSheetsService';
import InvoiceForm from './InvoiceForm';
import InvoiceDocument from './InvoiceDocument';

export default function InvoiceManager({ initialViewInvoiceId, initialCreatePayload, onClearInitial }) {
  const [invoices, setInvoices] = useState(storageService.getSales());
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('All');
  
  // View states: 'list' | 'create' | 'view'
  const [mode, setMode] = useState('list');
  const [selectedInvoice, setSelectedInvoice] = useState(null);

  // Subscribe to storage updates
  useEffect(() => {
    return storageService.subscribe(() => {
      setInvoices(storageService.getSales());
    });
  }, []);

  // Handle passed props (e.g. from Pricing Calculator or Dashboard click)
  useEffect(() => {
    if (initialViewInvoiceId) {
      const inv = storageService.getInvoiceById(initialViewInvoiceId);
      if (inv) {
        setSelectedInvoice(inv);
        setMode('view');
      }
      if (onClearInitial) onClearInitial();
    } else if (initialCreatePayload) {
      setMode('create');
    }
  }, [initialViewInvoiceId, initialCreatePayload]);

  // Actions
  const handleMarkPaid = (id) => {
    const currentInv = storageService.getInvoiceById(id);
    storageService.updateSale(id, { 
      status: 'Paid',
      paymentDate: new Date().toISOString().split('T')[0] 
    });

    // If invoice is linked to an AI Order, automatically mark order Complete in Google Sheets
    if (currentInv && currentInv.orderRef) {
      googleSheetsService.updateOrderStatus(currentInv.orderRef, 'Complete').catch(err => {
        console.warn('Google Sheet order status sync error on invoice paid:', err);
      });
    }

    if (selectedInvoice && selectedInvoice.id === id) {
      setSelectedInvoice(prev => ({ ...prev, status: 'Paid', paymentDate: new Date().toISOString().split('T')[0] }));
    }
  };

  const handleDelete = (id) => {
    if (window.confirm(`Are you sure you want to delete invoice ${id}? This action cannot be undone.`)) {
      storageService.deleteSale(id);
      if (selectedInvoice?.id === id) {
        setMode('list');
        setSelectedInvoice(null);
      }
    }
  };

  const handleCreateSuccess = (newInvoice) => {
    setSelectedInvoice(newInvoice);
    setMode('view');
    if (onClearInitial) onClearInitial();
  };

  // Filter & Search
  const filteredInvoices = invoices.filter((inv) => {
    const matchesSearch = 
      inv.customer?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.description?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = filterStatus === 'All' || inv.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  // KPI Calculations for Sales Ledger
  const totalBilled = invoices.reduce((acc, inv) => acc + (parseCurrency(inv.grossTotal) || 0), 0);
  const totalPaid = invoices.filter(i => i.status === 'Paid').reduce((acc, inv) => acc + (parseCurrency(inv.grossTotal) || 0), 0);
  const totalPending = invoices.filter(i => i.status === 'Pending').reduce((acc, inv) => acc + (parseCurrency(inv.grossTotal) || 0), 0);
  const totalStitches = invoices.reduce((acc, inv) => acc + (parseInteger(inv.totalStitches) || 0), 0);

  if (mode === 'create') {
    return (
      <InvoiceForm
        initialData={initialCreatePayload}
        onSaveSuccess={handleCreateSuccess}
        onCancel={() => {
          setMode('list');
          if (onClearInitial) onClearInitial();
        }}
      />
    );
  }

  if (mode === 'view' && selectedInvoice) {
    return (
      <InvoiceDocument
        invoice={selectedInvoice}
        onBack={() => setMode('list')}
        onMarkPaid={handleMarkPaid}
      />
    );
  }

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header & Quick Action */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '24px',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <div style={{
              padding: '8px',
              borderRadius: '12px',
              background: 'rgba(245, 158, 11, 0.15)',
              color: 'var(--accent-gold)'
            }}>
              <ReceiptText size={22} />
            </div>
            <h2 style={{ fontSize: '1.75rem' }}>Sales & Invoicing Ledger</h2>
          </div>
        </div>
      </div>

      {/* Top Stat Pulse Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Total Invoiced (Gross)
          </div>
          <div className="stat-val" style={{ fontSize: '1.7rem', color: '#ffffff' }}>
            ₹{totalBilled.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {invoices.length} Total Invoices Generated
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Collected (Paid)
          </div>
          <div className="stat-val" style={{ fontSize: '1.7rem', color: 'var(--accent-emerald)' }}>
            ₹{totalPaid.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {invoices.filter(i => i.status === 'Paid').length} Orders Cleared
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Outstanding (Pending)
          </div>
          <div className="stat-val" style={{ fontSize: '1.7rem', color: 'var(--accent-gold)' }}>
            ₹{totalPending.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {invoices.filter(i => i.status === 'Pending').length} Pending Payments
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Total Stitches Billed
          </div>
          <div className="stat-val" style={{ fontSize: '1.7rem', color: 'var(--accent-indigo)' }}>
            {(totalStitches / 1000).toFixed(0)}k
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {totalStitches.toLocaleString()} Raw Stitches
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
            placeholder="Search client, invoice #, or description..."
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {['All', 'Paid', 'Pending'].map((status) => (
            <button
              key={status}
              type="button"
              className="btn"
              style={{
                padding: '6px 14px',
                fontSize: '0.82rem',
                background: filterStatus === status ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                borderColor: filterStatus === status ? 'var(--accent-gold)' : 'var(--border-subtle)',
                color: filterStatus === status ? '#fbbf24' : 'var(--text-secondary)'
              }}
              onClick={() => setFilterStatus(status)}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Invoices Table Container */}
      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-subtle)' }}>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Invoice</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Date</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Customer</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Service</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Pre-Tax</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>GST</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Gross Total</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Status</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No invoices found matching your criteria.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => {
                  const isPaid = inv.status === 'Paid';
                  return (
                    <tr
                      key={inv.id}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      {/* Invoice ID */}
                      <td style={{ padding: '14px 18px', fontWeight: 700, fontFamily: 'var(--font-heading)', color: '#fbbf24' }}>
                        {inv.id}
                      </td>

                      {/* Date */}
                      <td style={{ padding: '14px 18px', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                        {inv.date}
                      </td>

                      {/* Customer */}
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ fontWeight: 600, color: '#f8fafc' }}>{inv.customer}</div>
                        {inv.description && (
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', maxWidth: '240px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {inv.description}
                          </div>
                        )}
                      </td>

                      {/* Service Type */}
                      <td style={{ padding: '14px 18px' }}>
                        <span className={`badge ${inv.serviceType === 'Machine Embroidery' ? 'badge-gold' : 'badge-indigo'}`}>
                          {inv.serviceType === 'Machine Embroidery' ? 'Embroidery' : 'Digitizing'}
                        </span>
                      </td>

                      {/* Pre-Tax */}
                      <td style={{ padding: '14px 18px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                        ₹{parseCurrency(inv.netPrice).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>

                      {/* GST */}
                      <td style={{ padding: '14px 18px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                        ₹{parseCurrency(inv.gst).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>

                      {/* Gross Total */}
                      <td style={{ padding: '14px 18px', fontWeight: 800, fontSize: '0.98rem', color: '#ffffff', fontFamily: 'var(--font-heading)' }}>
                        ₹{parseCurrency(inv.grossTotal).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>

                      {/* Status */}
                      <td style={{ padding: '14px 18px' }}>
                        <button
                          type="button"
                          className={`badge ${isPaid ? 'badge-emerald' : 'badge-gold'}`}
                          style={{ cursor: 'pointer', border: 'none' }}
                          onClick={() => isPaid ? null : handleMarkPaid(inv.id)}
                          title={isPaid ? "Payment received" : "Click to mark as paid"}
                        >
                          {isPaid ? '✓ Paid' : '⏳ Pending'}
                        </button>
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                            onClick={() => {
                              setSelectedInvoice(inv);
                              setMode('view');
                            }}
                            title="View & Print Customer Invoice"
                          >
                            <Eye size={15} />
                            <span>View</span>
                          </button>

                          <button
                            className="btn btn-ghost"
                            style={{ padding: '6px', color: 'var(--accent-rose)' }}
                            onClick={() => handleDelete(inv.id)}
                            title="Delete Record"
                          >
                            <Trash2 size={15} />
                          </button>
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
    </div>
  );
}
