import React, { useState, useEffect } from 'react';
import { 
  Wallet, 
  PlusCircle, 
  Search, 
  Tag, 
  Calendar, 
  CreditCard, 
  Trash2, 
  Zap, 
  Wrench, 
  Layers, 
  Home, 
  HelpCircle,
  TrendingDown,
  Info
} from 'lucide-react';
import { storageService, parseCurrency } from '../../services/storageService';
import { googleSheetsService } from '../../services/googleSheetsService';

const PREDEFINED_CATEGORIES = [
  { name: 'Cost of Thread', icon: Layers, color: '#f59e0b', desc: 'Embroidery spools, metallic zari, rayon' },
  { name: 'Stabilizer / Backing', icon: Layers, color: '#06b6d4', desc: 'Tear-away, cut-away, water soluble' },
  { name: 'Electricity', icon: Zap, color: '#eab308', desc: 'Commercial power utility bills' },
  { name: 'Machine Maintenance', icon: Wrench, color: '#f43f5e', desc: 'Needles, rotary hooks, oil, calibration' },
  { name: 'Facility / Rent', icon: Home, color: '#8b5cf6', desc: 'Facility space rent & common maintenance' },
  { name: 'Miscellaneous / Other', icon: HelpCircle, color: '#94a3b8', desc: 'Stationery, packaging, refreshments' }
];

const PAYMENT_METHODS = ['UPI', 'Bank Transfer', 'Cash', 'Credit Card', 'Cheque'];

export default function ExpenseManager({ onOpenQuickLog, initialLogTrigger }) {
  const [expenses, setExpenses] = useState(storageService.getExpenses());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  
  // Log Form State
  const [showLogModal, setShowLogModal] = useState(false);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [category, setCategory] = useState('Cost of Thread');
  const [vendor, setVendor] = useState('');
  const [customVendor, setCustomVendor] = useState('');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('UPI');

  // Dynamic list of all vendors loaded from Google Sheets
  const [sheetVendors, setSheetVendors] = useState(() => googleSheetsService.getVendors());

  useEffect(() => {
    setSheetVendors(googleSheetsService.getVendors());
    return storageService.subscribe(() => {
      setExpenses(storageService.getExpenses());
      setSheetVendors(googleSheetsService.getVendors());
    });
  }, []);

  const allVendors = Array.from(new Set(
    sheetVendors.map(v => v.Name || v.name).filter(Boolean)
  ));

  useEffect(() => {
    if (initialLogTrigger) {
      setShowLogModal(true);
    }
  }, [initialLogTrigger]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const numAmount = parseCurrency(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      alert('Please enter a valid expense amount.');
      return;
    }

    const finalVendor = vendor === '__custom__' ? customVendor.trim() : vendor.trim();
    let fullDescription = description.trim();
    if (finalVendor) {
      fullDescription = fullDescription ? `${finalVendor} - ${fullDescription}` : finalVendor;
    } else if (!fullDescription) {
      fullDescription = `${category} operational expense`;
    }

    const newExpense = {
      date,
      category,
      vendor: finalVendor,
      description: fullDescription,
      amount: numAmount,
      paymentMethod
    };

    // Save locally
    const saved = storageService.addExpense(newExpense);

    // Sync to Google Sheet Expense_Ledger
    googleSheetsService.appendExpenseToSheet(saved).catch(err => {
      console.warn('Google Sheet expense sync error:', err);
    });

    // Sync new vendor to Google Sheet Vendors tab if new
    if (finalVendor && (vendor === '__custom__' || !allVendors.some(v => v.toLowerCase() === finalVendor.toLowerCase()))) {
      googleSheetsService.appendVendorToSheet({
        name: finalVendor,
        category
      }).catch(err => {
        console.warn('Google Sheet vendor sync error:', err);
      });
    }

    // Reset Form
    setVendor('');
    setCustomVendor('');
    setDescription('');
    setAmount('');
    setShowLogModal(false);
  };

  const handleDelete = (id) => {
    if (window.confirm('Delete this expense record?')) {
      storageService.deleteExpense(id);
    }
  };

  // Filtered List
  const filteredExpenses = expenses.filter(e => {
    const matchesSearch = 
      e.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.category?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.paymentMethod?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory = selectedCategory === 'All' || e.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // KPI calculations
  const totalExpensesLogged = expenses.reduce((acc, e) => acc + (parseCurrency(e.amount) || 0), 0);
  const currentMonth = new Date().getMonth();
  const currentYear = new Date().getFullYear();
  const thisMonthExpenses = expenses
    .filter(e => {
      if (!e.date) return false;
      const d = new Date(e.date);
      return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
    })
    .reduce((acc, e) => acc + (parseCurrency(e.amount) || 0), 0);

  const totalDepreciation = storageService.getTotalMonthlyDepreciation();

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header */}
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
              background: 'rgba(16, 185, 129, 0.15)',
              color: 'var(--accent-emerald)'
            }}>
              <Wallet size={22} />
            </div>
            <h2 style={{ fontSize: '1.75rem' }}>Operational Expense Ledger</h2>
          </div>
        </div>
      </div>

      {/* Top Stat Pulse Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            This Month's Operational Costs
          </div>
          <div className="stat-val" style={{ fontSize: '1.75rem', color: 'var(--accent-rose)' }}>
            ₹{thisMonthExpenses.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Current Billing Cycle (Direct Cash Out)
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Equipment Depreciation (Monthly)
          </div>
          <div className="stat-val" style={{ fontSize: '1.75rem', color: 'var(--accent-indigo)' }}>
            ₹{totalDepreciation.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Automated from Fixed Asset Ledger
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Total Recorded Expenses
          </div>
          <div className="stat-val" style={{ fontSize: '1.75rem', color: '#ffffff' }}>
            ₹{totalExpensesLogged.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {expenses.length} Total Expense Transactions
          </div>
        </div>
      </div>

      {/* Category Quick Filters & Search */}
      <div className="glass-panel" style={{
        padding: '16px 20px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        {/* Search */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: 'var(--bg-input)',
          padding: '8px 14px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          minWidth: '240px',
          maxWidth: '380px',
          flex: 1
        }}>
          <Search size={18} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search description, vendor, or method..."
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

        {/* Category Dropdown / Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <select
            className="input-field"
            style={{ width: 'auto', padding: '8px 14px', fontSize: '0.85rem' }}
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="All">All Categories ({expenses.length})</option>
            {PREDEFINED_CATEGORIES.map(c => (
              <option key={c.name} value={c.name}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Expenses Table */}
      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-subtle)' }}>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Date</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Expense Category</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Description</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Method</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Amount</th>
                <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredExpenses.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No expense records found.
                  </td>
                </tr>
              ) : (
                filteredExpenses.map((exp) => {
                  const catConfig = PREDEFINED_CATEGORIES.find(c => c.name === exp.category) || { color: '#94a3b8' };
                  return (
                    <tr
                      key={exp.id}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      {/* Date */}
                      <td style={{ padding: '14px 18px', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                        {exp.date}
                      </td>

                      {/* Category Badge */}
                      <td style={{ padding: '14px 18px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '4px 10px',
                          borderRadius: '999px',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          background: `${catConfig.color}20`,
                          color: catConfig.color,
                          border: `1px solid ${catConfig.color}40`
                        }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: catConfig.color }} />
                          {exp.category}
                        </span>
                      </td>

                      {/* Description */}
                      <td style={{ padding: '14px 18px', color: '#f8fafc', fontWeight: 500 }}>
                        {exp.description}
                      </td>

                      {/* Payment Method */}
                      <td style={{ padding: '14px 18px', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                        <span className="badge badge-slate">{exp.paymentMethod}</span>
                      </td>

                      {/* Amount */}
                      <td style={{ padding: '14px 18px', textAlign: 'right', fontWeight: 700, fontSize: '1rem', color: '#f43f5e', fontFamily: 'var(--font-heading)' }}>
                        ₹{parseCurrency(exp.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>

                      {/* Delete */}
                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '6px', color: 'var(--accent-rose)' }}
                          onClick={() => handleDelete(exp.id)}
                          title="Delete Record"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Expense Modal */}
      {showLogModal && (
        <div className="modal-overlay" onClick={() => setShowLogModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Wallet size={20} style={{ color: 'var(--accent-emerald)' }} />
                <h3>Log Operational Expense</h3>
              </div>
              <button className="btn btn-ghost" onClick={() => setShowLogModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div className="input-group">
                    <label className="input-label">EXPENSE DATE *</label>
                    <input
                      type="date"
                      className="input-field"
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                      required
                    />
                  </div>
                  <div className="input-group">
                    <label className="input-label">AMOUNT (₹) *</label>
                    <input
                      type="number"
                      min="1"
                      step="any"
                      placeholder="e.g. 2400"
                      className="input-field"
                      style={{ fontSize: '1.1rem', fontWeight: 700 }}
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">PREDEFINED CATEGORY *</label>
                  <select
                    className="input-field"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    {PREDEFINED_CATEGORIES.map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div className="input-group">
                  <label className="input-label">VENDOR NAME</label>
                  <select
                    className="input-field"
                    value={vendor}
                    onChange={(e) => {
                      setVendor(e.target.value);
                      if (e.target.value !== '__custom__') {
                        setCustomVendor('');
                      }
                    }}
                  >
                    <option value="">-- Select Vendor --</option>
                    {allVendors.map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                    <option value="__custom__">+ Enter New Vendor...</option>
                  </select>
                </div>

                {vendor === '__custom__' && (
                  <div className="input-group">
                    <label className="input-label">CUSTOM VENDOR NAME *</label>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="Enter supplier / business name"
                      value={customVendor}
                      onChange={(e) => setCustomVendor(e.target.value)}
                      required
                    />
                  </div>
                )}

                <div className="input-group">
                  <label className="input-label">ITEM / EXPENSE DESCRIPTION</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Madeira Metallic Gold Threads 20 spools"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">PAYMENT METHOD</label>
                  <select
                    className="input-field"
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                  >
                    {PAYMENT_METHODS.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowLogModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-emerald">
                  <PlusCircle size={16} />
                  <span>Save Expense to Ledger</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
