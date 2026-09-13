import React, { useState, useEffect } from 'react';
import { 
  Landmark, 
  Cpu, 
  PlusCircle, 
  Calendar, 
  TrendingDown, 
  Trash2, 
  ShieldCheck, 
  Info, 
  ArrowRight,
  DollarSign
} from 'lucide-react';
import { storageService, parseCurrency, parseInteger } from '../../services/storageService';
import { googleSheetsService } from '../../services/googleSheetsService';

export default function AssetManager() {
  const [assets, setAssets] = useState(storageService.getAssets());
  const [capital, setCapital] = useState(storageService.getCapital());
  const [subTab, setSubTab] = useState('assets'); // 'assets' | 'capital'

  // Asset Form State
  const [showAssetModal, setShowAssetModal] = useState(false);
  const [assetName, setAssetName] = useState('');
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().split('T')[0]);
  const [purchasePrice, setPurchasePrice] = useState('');
  const [usefulLifeMonths, setUsefulLifeMonths] = useState(60); // default 5 years

  // Capital Form State
  const [showCapitalModal, setShowCapitalModal] = useState(false);
  const [capDate, setCapDate] = useState(new Date().toISOString().split('T')[0]);
  const [transactionType, setTransactionType] = useState('Investment');
  const [capDescription, setCapDescription] = useState('');
  const [capAmount, setCapAmount] = useState('');

  useEffect(() => {
    return storageService.subscribe(() => {
      setAssets(storageService.getAssets());
      setCapital(storageService.getCapital());
    });
  }, []);

  // Submit Asset
  const handleAssetSubmit = (e) => {
    e.preventDefault();
    const price = parseCurrency(purchasePrice);
    const months = parseInteger(usefulLifeMonths);

    if (!assetName.trim() || isNaN(price) || price <= 0 || isNaN(months) || months <= 0) {
      alert('Please fill in valid asset details.');
      return;
    }

    const newAsset = {
      name: assetName.trim(),
      purchaseDate,
      purchasePrice: price,
      usefulLifeMonths: months,
      monthlyDepreciation: Number((price / months).toFixed(2))
    };

    const saved = storageService.addAsset(newAsset);
    googleSheetsService.appendAssetToSheet(saved).catch(err => {
      console.warn('Asset sheet sync error:', err);
    });

    setAssetName('');
    setPurchasePrice('');
    setUsefulLifeMonths(60);
    setShowAssetModal(false);
  };

  // Submit Capital
  const handleCapitalSubmit = (e) => {
    e.preventDefault();
    const amt = parseCurrency(capAmount);
    if (isNaN(amt) || amt <= 0) {
      alert('Please enter a valid capital amount.');
      return;
    }

    const newCap = {
      date: capDate,
      transactionType,
      description: capDescription.trim() || `${transactionType} entry`,
      amount: amt
    };

    const saved = storageService.addCapital(newCap);
    googleSheetsService.appendCapitalToSheet(saved).catch(err => {
      console.warn('Capital sheet sync error:', err);
    });

    setCapDescription('');
    setCapAmount('');
    setShowCapitalModal(false);
  };

  const handleDeleteAsset = (id) => {
    if (window.confirm('Remove this asset from ledger?')) {
      storageService.deleteAsset(id);
    }
  };

  const handleDeleteCapital = (id) => {
    if (window.confirm('Delete this capital record?')) {
      storageService.deleteCapital(id);
    }
  };

  // Metrics
  const totalAssetValue = assets.reduce((sum, a) => sum + (parseCurrency(a.purchasePrice) || 0), 0);
  const totalMonthlyDepreciation = storageService.getTotalMonthlyDepreciation();
  const totalInvestments = capital.filter(c => c.transactionType === 'Investment').reduce((s, c) => s + (parseCurrency(c.amount) || 0), 0);
  const totalLoans = capital.filter(c => c.transactionType === 'Loan').reduce((s, c) => s + (parseCurrency(c.amount) || 0), 0);

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
              background: 'rgba(99, 102, 241, 0.15)',
              color: 'var(--accent-indigo)'
            }}>
              <Landmark size={22} />
            </div>
            <h2 style={{ fontSize: '1.75rem' }}>Fixed Assets & Capital Registry</h2>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {subTab === 'assets' ? (
            <button
              className="btn btn-primary"
              style={{ padding: '10px 18px' }}
              onClick={() => setShowAssetModal(true)}
            >
              <PlusCircle size={17} />
              <span>+ Add Fixed Asset</span>
            </button>
          ) : (
            <button
              className="btn btn-emerald"
              style={{ padding: '10px 18px' }}
              onClick={() => setShowCapitalModal(true)}
            >
              <PlusCircle size={17} />
              <span>+ Record Capital Entry</span>
            </button>
          )}
        </div>
      </div>

      {/* Depreciation Engine Alert Card */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 20px',
        borderRadius: 'var(--radius-lg)',
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(18, 26, 44, 0.7) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        marginBottom: '24px',
        flexWrap: 'wrap',
        gap: '14px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'rgba(99, 102, 241, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#a5b4fc'
          }}>
            <TrendingDown size={22} />
          </div>
          <div>
            <div style={{ fontWeight: 700, color: '#ffffff', fontSize: '1rem' }}>
              Automated Monthly Depreciation Active
            </div>
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Monthly P&L Impact
          </div>
          <div className="stat-val" style={{ fontSize: '1.5rem', color: 'var(--accent-indigo)' }}>
            ₹{totalMonthlyDepreciation.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / month
          </div>
        </div>
      </div>

      {/* Subtab Switcher */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <button
          className="btn"
          style={{
            background: subTab === 'assets' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.04)',
            borderColor: subTab === 'assets' ? 'var(--accent-indigo)' : 'var(--border-subtle)',
            color: subTab === 'assets' ? '#a5b4fc' : 'var(--text-secondary)',
            padding: '8px 18px',
            fontSize: '0.88rem'
          }}
          onClick={() => setSubTab('assets')}
        >
          <Cpu size={16} />
          <span>Fixed Assets ({assets.length})</span>
        </button>

        <button
          className="btn"
          style={{
            background: subTab === 'capital' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.04)',
            borderColor: subTab === 'capital' ? 'var(--accent-emerald)' : 'var(--border-subtle)',
            color: subTab === 'capital' ? '#34d399' : 'var(--text-secondary)',
            padding: '8px 18px',
            fontSize: '0.88rem'
          }}
          onClick={() => setSubTab('capital')}
        >
          <Landmark size={16} />
          <span>Capital & Loans ({capital.length})</span>
        </button>
      </div>

      {subTab === 'assets' ? (
        /* ASSET LEDGER VIEW */
        <div>
          {/* Summary Stat Tiles */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginBottom: '20px'
          }}>
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Total Plant & Equipment Cost
              </div>
              <div className="stat-val" style={{ fontSize: '1.7rem', color: '#ffffff' }}>
                ₹{totalAssetValue.toLocaleString('en-IN')}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                {assets.length} Registered Machines/Computers
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Total Monthly Depreciation
              </div>
              <div className="stat-val" style={{ fontSize: '1.7rem', color: 'var(--accent-indigo)' }}>
                ₹{totalMonthlyDepreciation.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Auto-injected into Monthly Expenses
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Annual Depreciation Shield
              </div>
              <div className="stat-val" style={{ fontSize: '1.7rem', color: 'var(--accent-emerald)' }}>
                ₹{(totalMonthlyDepreciation * 12).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Per Annum P&L Allowance
              </div>
            </div>
          </div>

          {/* Assets Table */}
          <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-subtle)' }}>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Asset Name</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Purchase Date</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Purchase Price</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Useful Life</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Monthly Depreciation</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {assets.map((asset) => (
                    <tr
                      key={asset.id}
                      style={{ borderBottom: '1px solid var(--border-subtle)' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.95rem' }}>{asset.name}</div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>ID: {asset.id}</div>
                      </td>
                      <td style={{ padding: '14px 18px', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                        {asset.purchaseDate}
                      </td>
                      <td style={{ padding: '14px 18px', fontWeight: 700, color: '#ffffff', fontSize: '0.95rem' }}>
                        ₹{parseCurrency(asset.purchasePrice).toLocaleString('en-IN')}
                      </td>
                      <td style={{ padding: '14px 18px', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                        {asset.usefulLifeMonths} Months ({(parseInteger(asset.usefulLifeMonths) / 12).toFixed(1)} Yrs)
                      </td>
                      <td style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--accent-indigo)', fontSize: '0.95rem' }}>
                        ₹{parseCurrency(asset.monthlyDepreciation).toLocaleString('en-IN', { minimumFractionDigits: 2 })} / mo
                      </td>
                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '6px', color: 'var(--accent-rose)' }}
                          onClick={() => handleDeleteAsset(asset.id)}
                          title="Delete Asset"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* CAPITAL REGISTRY VIEW */
        <div>
          {/* Summary Stat Tiles */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginBottom: '20px'
          }}>
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Owner Equity Investments
              </div>
              <div className="stat-val" style={{ fontSize: '1.7rem', color: 'var(--accent-emerald)' }}>
                ₹{totalInvestments.toLocaleString('en-IN')}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Contributed Capital
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Active Machine Loans / Debt
              </div>
              <div className="stat-val" style={{ fontSize: '1.7rem', color: 'var(--accent-gold)' }}>
                ₹{totalLoans.toLocaleString('en-IN')}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Outstanding Liabilities
              </div>
            </div>
          </div>

          {/* Capital Table */}
          <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-subtle)' }}>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Date</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Transaction Type</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Description</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Amount</th>
                    <th style={{ padding: '14px 18px', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {capital.map((cap) => (
                    <tr
                      key={cap.id}
                      style={{ borderBottom: '1px solid var(--border-subtle)' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '14px 18px', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                        {cap.date}
                      </td>
                      <td style={{ padding: '14px 18px' }}>
                        <span className={`badge ${cap.transactionType === 'Investment' ? 'badge-emerald' : 'badge-gold'}`}>
                          {cap.transactionType}
                        </span>
                      </td>
                      <td style={{ padding: '14px 18px', color: '#f8fafc', fontWeight: 500 }}>
                        {cap.description}
                      </td>
                      <td style={{ padding: '14px 18px', textAlign: 'right', fontWeight: 700, fontSize: '0.98rem', color: '#ffffff' }}>
                        ₹{parseCurrency(cap.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '6px', color: 'var(--accent-rose)' }}
                          onClick={() => handleDeleteCapital(cap.id)}
                          title="Delete Record"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Add Asset Modal */}
      {showAssetModal && (
        <div className="modal-overlay" onClick={() => setShowAssetModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Cpu size={20} style={{ color: 'var(--accent-gold)' }} />
                <h3>Add New Equipment Asset</h3>
              </div>
              <button className="btn btn-ghost" onClick={() => setShowAssetModal(false)}>✕</button>
            </div>
            <form onSubmit={handleAssetSubmit}>
              <div className="modal-body">
                <div className="input-group">
                  <label className="input-label">ASSET / MACHINE NAME *</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Barudan 2-Head Commercial Machine"
                    value={assetName}
                    onChange={(e) => setAssetName(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div className="input-group">
                    <label className="input-label">PURCHASE DATE *</label>
                    <input
                      type="date"
                      className="input-field"
                      value={purchaseDate}
                      onChange={(e) => setPurchaseDate(e.target.value)}
                      required
                    />
                  </div>

                  <div className="input-group">
                    <label className="input-label">PURCHASE PRICE (₹) *</label>
                    <input
                      type="number"
                      min="1"
                      placeholder="e.g. 650000"
                      className="input-field"
                      style={{ fontSize: '1.05rem', fontWeight: 700 }}
                      value={purchasePrice}
                      onChange={(e) => setPurchasePrice(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">
                    <span>USEFUL LIFE (MONTHS) *</span>
                    <span style={{ color: 'var(--accent-indigo)', fontWeight: 600 }}>
                      {(parseInt(usefulLifeMonths) / 12).toFixed(1)} Years
                    </span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    className="input-field"
                    value={usefulLifeMonths}
                    onChange={(e) => setUsefulLifeMonths(e.target.value)}
                    required
                  />
                </div>

                {purchasePrice && usefulLifeMonths > 0 && (
                  <div style={{
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(99, 102, 241, 0.1)',
                    border: '1px solid rgba(99, 102, 241, 0.25)',
                    fontSize: '0.85rem',
                    color: '#c7d2fe'
                  }}>
                    Calculated Monthly Depreciation: <strong>₹{(parseCurrency(purchasePrice) / Math.max(1, parseInteger(usefulLifeMonths))).toFixed(2)}/mo</strong>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAssetModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Asset to Ledger
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Capital Modal */}
      {showCapitalModal && (
        <div className="modal-overlay" onClick={() => setShowCapitalModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Landmark size={20} style={{ color: 'var(--accent-emerald)' }} />
                <h3>Record Capital / Loan Entry</h3>
              </div>
              <button className="btn btn-ghost" onClick={() => setShowCapitalModal(false)}>✕</button>
            </div>
            <form onSubmit={handleCapitalSubmit}>
              <div className="modal-body">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div className="input-group">
                    <label className="input-label">DATE *</label>
                    <input
                      type="date"
                      className="input-field"
                      value={capDate}
                      onChange={(e) => setCapDate(e.target.value)}
                      required
                    />
                  </div>

                  <div className="input-group">
                    <label className="input-label">TRANSACTION TYPE *</label>
                    <select
                      className="input-field"
                      value={transactionType}
                      onChange={(e) => setTransactionType(e.target.value)}
                    >
                      <option value="Investment">Investment (Owner Equity)</option>
                      <option value="Loan">Loan (Debt / Machinery Financing)</option>
                    </select>
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">DESCRIPTION *</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Bank Machinery Loan disbursement"
                    value={capDescription}
                    onChange={(e) => setCapDescription(e.target.value)}
                    required
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">AMOUNT (₹) *</label>
                  <input
                    type="number"
                    min="1"
                    placeholder="e.g. 350000"
                    className="input-field"
                    style={{ fontSize: '1.05rem', fontWeight: 700 }}
                    value={capAmount}
                    onChange={(e) => setCapAmount(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCapitalModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-emerald">
                  Save to Capital Ledger
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
