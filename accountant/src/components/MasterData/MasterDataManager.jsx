import React, { useState, useEffect } from 'react';
import { 
  SlidersHorizontal, 
  Calendar, 
  Users, 
  Store, 
  FileText, 
  Save, 
  Plus, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';

export default function MasterDataManager() {
  const [activeSubTab, setActiveSubTab] = useState('config');
  const [loading, setLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  // States
  const [config, setConfig] = useState({});
  const [holidays, setHolidays] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [templates, setTemplates] = useState([]);

  // New item inputs
  const [newHoliday, setNewHoliday] = useState({ date: '', event: '' });
  const [newCustomer, setNewCustomer] = useState({ name: '', phone: '', address: '' });
  const [newVendor, setNewVendor] = useState({ name: '', category: '', contact_person: '', phone: '', address: '' });
  const [newTemplate, setNewTemplate] = useState({ 
    template_name: '', 
    service_category: 'Machine Embroidery', 
    machine: 'Ricoma', 
    labor_minutes: 60, 
    stitch_count: 10000 
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cfgRes, holRes, custRes, vendRes, tmplRes] = await Promise.all([
        fetch('/api/config').then(r => r.json()),
        fetch('/api/holidays').then(r => r.json()),
        fetch('/api/customers').then(r => r.json()),
        fetch('/api/vendors').then(r => r.json()),
        fetch('/api/templates').then(r => r.json())
      ]);

      if (cfgRes.success) setConfig(cfgRes.config || {});
      if (holRes.success) setHolidays(holRes.holidays || []);
      if (custRes.success) setCustomers(custRes.customers || []);
      if (vendRes.success) setVendors(vendRes.vendors || []);
      if (tmplRes.success) setTemplates(tmplRes.templates || []);
    } catch (e) {
      console.error('Failed to load master data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const showSuccess = (msg) => {
    setSaveStatus({ type: 'success', message: msg });
    setTimeout(() => setSaveStatus(null), 3000);
  };

  const showError = (msg) => {
    setSaveStatus({ type: 'error', message: msg });
    setTimeout(() => setSaveStatus(null), 4000);
  };

  // 1. Config Save
  const handleSaveConfig = async (key, value) => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value })
      });
      if (res.ok) {
        showSuccess(`Saved "${key}"!`);
      } else {
        showError('Failed to save config.');
      }
    } catch (e) {
      showError(e.message);
    }
  };

  // 2. Holidays
  const handleAddHoliday = async (e) => {
    e.preventDefault();
    if (!newHoliday.date || !newHoliday.event) return;
    try {
      const res = await fetch('/api/holidays', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newHoliday)
      });
      if (res.ok) {
        setNewHoliday({ date: '', event: '' });
        showSuccess('Holiday added!');
        fetchData();
      }
    } catch (e) {
      showError(e.message);
    }
  };

  const handleDeleteHoliday = async (id) => {
    if (!confirm('Delete this holiday?')) return;
    try {
      await fetch(`/api/holidays/${encodeURIComponent(id)}`, { method: 'DELETE' });
      showSuccess('Holiday deleted!');
      fetchData();
    } catch (e) {
      showError(e.message);
    }
  };

  // 3. Customers
  const handleAddCustomer = async (e) => {
    e.preventDefault();
    if (!newCustomer.name) return;
    try {
      const res = await fetch('/api/customers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCustomer)
      });
      if (res.ok) {
        setNewCustomer({ name: '', phone: '', address: '' });
        showSuccess('Customer added!');
        fetchData();
      }
    } catch (e) {
      showError(e.message);
    }
  };

  // 4. Vendors
  const handleAddVendor = async (e) => {
    e.preventDefault();
    if (!newVendor.name) return;
    try {
      const res = await fetch('/api/vendors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newVendor)
      });
      if (res.ok) {
        setNewVendor({ name: '', category: '', contact_person: '', phone: '', address: '' });
        showSuccess('Vendor added!');
        fetchData();
      }
    } catch (e) {
      showError(e.message);
    }
  };

  // 5. Templates
  const handleAddTemplate = async (e) => {
    e.preventDefault();
    if (!newTemplate.template_name) return;
    try {
      const res = await fetch('/api/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTemplate)
      });
      if (res.ok) {
        setNewTemplate({ 
          template_name: '', 
          service_category: 'Machine Embroidery', 
          machine: 'Ricoma', 
          labor_minutes: 60, 
          stitch_count: 10000 
        });
        showSuccess('Template added!');
        fetchData();
      }
    } catch (e) {
      showError(e.message);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <SlidersHorizontal style={{ color: 'var(--accent-gold)' }} />
            Master Data Management
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
            Manage pricing parameters, studio configuration, holidays, customers, vendors, and embroidery templates backed by Google Cloud Firestore.
          </p>
        </div>
        <button 
          className="btn btn-secondary" 
          onClick={fetchData} 
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Alert toast */}
      {saveStatus && (
        <div style={{
          padding: '12px 18px',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: saveStatus.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
          border: `1px solid ${saveStatus.type === 'success' ? 'var(--accent-emerald)' : 'var(--accent-rose)'}`,
          color: 'var(--text-primary)'
        }}>
          {saveStatus.type === 'success' ? <CheckCircle2 size={18} color="var(--accent-emerald)" /> : <AlertCircle size={18} color="var(--accent-rose)" />}
          <span>{saveStatus.message}</span>
        </div>
      )}

      {/* Sub tabs */}
      <div style={{
        display: 'flex',
        gap: '10px',
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: '24px',
        overflowX: 'auto',
        paddingBottom: '8px'
      }}>
        {[
          { id: 'config', label: 'Pricing & Config', icon: SlidersHorizontal },
          { id: 'holidays', label: 'Studio Holidays', icon: Calendar },
          { id: 'customers', label: 'Customers', icon: Users },
          { id: 'vendors', label: 'Vendors', icon: Store },
          { id: 'templates', label: 'Templates', icon: FileText }
        ].map(tab => {
          const Icon = tab.icon;
          const active = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                background: active ? 'var(--bg-card-hover)' : 'transparent',
                border: 'none',
                color: active ? 'var(--accent-gold)' : 'var(--text-secondary)',
                borderBottom: active ? '2px solid var(--accent-gold)' : '2px solid transparent',
                padding: '10px 16px',
                borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontWeight: active ? 600 : 500,
                fontSize: '0.92rem'
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: Config */}
      {activeSubTab === 'config' && (
        <div className="card" style={{ padding: '24px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <h3 style={{ marginBottom: '16px', color: 'var(--text-primary)' }}>Pricing & Studio Parameters</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '20px' }}>
            Changes made here are applied instantly to WhatsApp quote calculations and CJS Accountant invoice estimates.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            {Object.entries(config).map(([key, value]) => (
              <div key={key} style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)'
              }}>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  {key}
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    defaultValue={value}
                    id={`cfg_${key}`}
                    style={{
                      flex: 1,
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-medium)',
                      color: 'var(--text-primary)',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.95rem'
                    }}
                  />
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      const el = document.getElementById(`cfg_${key}`);
                      if (el) handleSaveConfig(key, el.value);
                    }}
                    style={{ padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Save size={14} />
                    Save
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: Holidays */}
      {activeSubTab === 'holidays' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Add Holiday Form */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <h3 style={{ marginBottom: '14px' }}>Add New Holiday</h3>
            <form onSubmit={handleAddHoliday} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <input
                type="date"
                value={newHoliday.date}
                onChange={e => setNewHoliday({ ...newHoliday, date: e.target.value })}
                required
                style={{
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-medium)',
                  color: 'var(--text-primary)',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)'
                }}
              />
              <input
                type="text"
                placeholder="Holiday Event Name (e.g. Vishu, Easter)"
                value={newHoliday.event}
                onChange={e => setNewHoliday({ ...newHoliday, event: e.target.value })}
                required
                style={{
                  flex: 1,
                  minWidth: '240px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-medium)',
                  color: 'var(--text-primary)',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)'
                }}
              />
              <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Plus size={16} />
                Add Holiday
              </button>
            </form>
          </div>

          {/* Holiday List */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <h3 style={{ marginBottom: '16px' }}>Upcoming Holidays ({holidays.length})</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {holidays.map(h => (
                <div key={h.id || h.date} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: 'var(--bg-input)',
                  padding: '12px 18px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)'
                }}>
                  <div>
                    <span style={{ fontWeight: 600, color: 'var(--accent-gold)', marginRight: '14px' }}>
                      {h.date}
                    </span>
                    <span style={{ color: 'var(--text-primary)' }}>{h.event}</span>
                  </div>
                  <button
                    onClick={() => handleDeleteHoliday(h.id || h.date)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--accent-rose)', cursor: 'pointer' }}
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Customers */}
      {activeSubTab === 'customers' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Add Customer Form */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <h3 style={{ marginBottom: '14px' }}>Register Customer</h3>
            <form onSubmit={handleAddCustomer} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              <input
                type="text"
                placeholder="Customer Name"
                value={newCustomer.name}
                onChange={e => setNewCustomer({ ...newCustomer, name: e.target.value })}
                required
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <input
                type="text"
                placeholder="Phone (optional)"
                value={newCustomer.phone}
                onChange={e => setNewCustomer({ ...newCustomer, phone: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <input
                type="text"
                placeholder="Address / City (optional)"
                value={newCustomer.address}
                onChange={e => setNewCustomer({ ...newCustomer, address: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Plus size={16} />
                Save Customer
              </button>
            </form>
          </div>

          {/* Customer Table */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', overflowX: 'auto' }}>
            <h3 style={{ marginBottom: '16px' }}>Registered Customers ({customers.length})</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-medium)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '10px' }}>ID</th>
                  <th style={{ padding: '10px' }}>Name</th>
                  <th style={{ padding: '10px' }}>Phone</th>
                  <th style={{ padding: '10px' }}>Address</th>
                </tr>
              </thead>
              <tbody>
                {customers.map(c => (
                  <tr key={c.id || c.customer_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px', color: 'var(--accent-gold)' }}>{c.customer_id || c.id}</td>
                    <td style={{ padding: '10px', fontWeight: 600 }}>{c.name}</td>
                    <td style={{ padding: '10px' }}>{c.phone || '—'}</td>
                    <td style={{ padding: '10px' }}>{c.address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: Vendors */}
      {activeSubTab === 'vendors' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Add Vendor Form */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <h3 style={{ marginBottom: '14px' }}>Add Vendor</h3>
            <form onSubmit={handleAddVendor} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
              <input
                type="text"
                placeholder="Vendor Name"
                value={newVendor.name}
                onChange={e => setNewVendor({ ...newVendor, name: e.target.value })}
                required
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <input
                type="text"
                placeholder="Category (e.g. Threads)"
                value={newVendor.category}
                onChange={e => setNewVendor({ ...newVendor, category: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <input
                type="text"
                placeholder="Contact Person"
                value={newVendor.contact_person}
                onChange={e => setNewVendor({ ...newVendor, contact_person: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <input
                type="text"
                placeholder="Phone"
                value={newVendor.phone}
                onChange={e => setNewVendor({ ...newVendor, phone: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <input
                type="text"
                placeholder="Location"
                value={newVendor.address}
                onChange={e => setNewVendor({ ...newVendor, address: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Plus size={16} />
                Save Vendor
              </button>
            </form>
          </div>

          {/* Vendors Table */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', overflowX: 'auto' }}>
            <h3 style={{ marginBottom: '16px' }}>Active Vendors ({vendors.length})</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-medium)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '10px' }}>ID</th>
                  <th style={{ padding: '10px' }}>Vendor</th>
                  <th style={{ padding: '10px' }}>Category</th>
                  <th style={{ padding: '10px' }}>Contact</th>
                  <th style={{ padding: '10px' }}>Phone</th>
                  <th style={{ padding: '10px' }}>Location</th>
                </tr>
              </thead>
              <tbody>
                {vendors.map(v => (
                  <tr key={v.id || v.vendor_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px', color: 'var(--accent-gold)' }}>{v.vendor_id || v.id}</td>
                    <td style={{ padding: '10px', fontWeight: 600 }}>{v.name}</td>
                    <td style={{ padding: '10px' }}>{v.category}</td>
                    <td style={{ padding: '10px' }}>{v.contact_person || '—'}</td>
                    <td style={{ padding: '10px' }}>{v.phone || '—'}</td>
                    <td style={{ padding: '10px' }}>{v.address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: Templates */}
      {activeSubTab === 'templates' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Add Template Form */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <h3 style={{ marginBottom: '14px' }}>Add Description Template</h3>
            <form onSubmit={handleAddTemplate} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              <input
                type="text"
                placeholder="Template Name (e.g. Heavy Bridal)"
                value={newTemplate.template_name}
                onChange={e => setNewTemplate({ ...newTemplate, template_name: e.target.value })}
                required
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <select
                value={newTemplate.service_category}
                onChange={e => setNewTemplate({ ...newTemplate, service_category: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              >
                <option value="Machine Embroidery">Machine Embroidery</option>
                <option value="Embroidery designing">Embroidery designing</option>
              </select>
              <select
                value={newTemplate.machine}
                onChange={e => setNewTemplate({ ...newTemplate, machine: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              >
                <option value="Ricoma">Ricoma</option>
                <option value="Aakruthi">Aakruthi</option>
                <option value="None">None</option>
              </select>
              <input
                type="number"
                placeholder="Labor Minutes"
                value={newTemplate.labor_minutes}
                onChange={e => setNewTemplate({ ...newTemplate, labor_minutes: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <input
                type="number"
                placeholder="Stitch Count"
                value={newTemplate.stitch_count}
                onChange={e => setNewTemplate({ ...newTemplate, stitch_count: e.target.value })}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-medium)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}
              />
              <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Plus size={16} />
                Save Template
              </button>
            </form>
          </div>

          {/* Templates Table */}
          <div className="card" style={{ padding: '20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', overflowX: 'auto' }}>
            <h3 style={{ marginBottom: '16px' }}>Active Templates ({templates.length})</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-medium)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '10px' }}>Template</th>
                  <th style={{ padding: '10px' }}>Category</th>
                  <th style={{ padding: '10px' }}>Machine</th>
                  <th style={{ padding: '10px' }}>Labor</th>
                  <th style={{ padding: '10px' }}>Stitches</th>
                </tr>
              </thead>
              <tbody>
                {templates.map(t => (
                  <tr key={t.id || t.template_name} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px', fontWeight: 600, color: 'var(--accent-gold)' }}>{t.template_name}</td>
                    <td style={{ padding: '10px' }}>{t.service_category}</td>
                    <td style={{ padding: '10px' }}>{t.machine}</td>
                    <td style={{ padding: '10px' }}>{t.labor_minutes} min</td>
                    <td style={{ padding: '10px' }}>{Number(t.stitch_count || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
