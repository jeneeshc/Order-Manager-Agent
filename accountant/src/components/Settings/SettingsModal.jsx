import React, { useState } from 'react';
import { 
  SlidersHorizontal, 
  Cloud, 
  KeyRound, 
  Database, 
  Copy, 
  Check, 
  RefreshCw, 
  AlertCircle, 
  FileSpreadsheet, 
  Download, 
  Upload, 
  RotateCcw,
  Sparkles
} from 'lucide-react';
import { storageService } from '../../services/storageService';
import { googleSheetsService, APPS_SCRIPT_TEMPLATE } from '../../services/googleSheetsService';

export default function SettingsModal({ onClose, onLock }) {
  const [config, setConfig] = useState(storageService.getConfig());
  const [settings, setSettings] = useState(storageService.getSettings());
  const [activeTab, setActiveTab] = useState('pricing'); // 'pricing' | 'sheets' | 'security' | 'backup'
  
  // Google Sheets state
  const [scriptUrl, setScriptUrl] = useState(settings.googleScriptUrl || '');
  const [useSheets, setUseSheets] = useState(settings.useGoogleSheets || false);
  const [testStatus, setTestStatus] = useState(null);
  const [copiedScript, setCopiedScript] = useState(false);

  // Security state
  const [oldPin, setOldPin] = useState('');
  const [newPin, setNewPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [pinMessage, setPinMessage] = useState({ text: '', isError: false });

  // Save Pricing Config
  const handleConfigSubmit = (e) => {
    e.preventDefault();
    storageService.updateConfig(config);
    alert('Pricing variables and config updated successfully!');
  };

  // Save Sheets Config
  const handleSaveSheets = (e) => {
    e.preventDefault();
    storageService.updateSettings({
      googleScriptUrl: scriptUrl.trim(),
      useGoogleSheets: useSheets
    });
    setSettings(storageService.getSettings());
    alert('Google Sheets connection settings saved!');
  };

  const handleTestConnection = async () => {
    if (!scriptUrl.trim()) {
      alert('Please enter your Google Apps Script Web App URL first.');
      return;
    }
    setTestStatus({ loading: true, message: 'Connecting to Google Sheets...' });
    try {
      const res = await googleSheetsService.testConnection(scriptUrl.trim());
      setTestStatus({ success: true, message: res.message || 'Connected successfully to Google Sheet!' });
    } catch (err) {
      setTestStatus({ error: true, message: err.message || 'Connection failed. Ensure web app is deployed to "Anyone".' });
    }
  };

  const handleCopyScript = () => {
    navigator.clipboard.writeText(APPS_SCRIPT_TEMPLATE);
    setCopiedScript(true);
    setTimeout(() => setCopiedScript(false), 2000);
  };

  // Change PIN
  const handlePinSubmit = (e) => {
    e.preventDefault();
    setPinMessage({ text: '', isError: false });

    if (!storageService.verifyPin(oldPin)) {
      setPinMessage({ text: 'Current PIN is incorrect.', isError: true });
      return;
    }
    if (newPin.length !== 4 || !/^\d{4}$/.test(newPin)) {
      setPinMessage({ text: 'New PIN must be exactly 4 digits.', isError: true });
      return;
    }
    if (newPin !== confirmPin) {
      setPinMessage({ text: 'New PIN and Confirm PIN do not match.', isError: true });
      return;
    }

    storageService.setPin(newPin);
    setPinMessage({ text: 'PIN successfully changed!', isError: false });
    setOldPin('');
    setNewPin('');
    setConfirmPin('');
  };

  // Data Export
  const handleExportData = () => {
    const data = storageService.exportAllData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cjs_accountant_backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Data Import
  const handleImportData = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target.result);
        if (storageService.importAllData(json)) {
          alert('Data imported successfully! App state restored.');
          onClose();
        } else {
          alert('Invalid backup file format.');
        }
      } catch (err) {
        alert('Failed to parse JSON file.');
      }
    };
    reader.readAsText(file);
  };

  const handleResetData = () => {
    if (window.confirm('Reset all data to the initial factory seed? All custom invoices and expenses will be restored to demo state.')) {
      storageService.resetToDefault();
      alert('Reset complete.');
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '720px' }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <SlidersHorizontal size={22} style={{ color: 'var(--accent-gold)' }} />
            <div>
              <h3 style={{ fontSize: '1.25rem' }}>Settings & System Configuration</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Pricing variables, Google Sheets sync, security, and backups
              </p>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onClose}>✕</button>
        </div>

        {/* Tab Switcher */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'rgba(255,255,255,0.02)',
          padding: '0 16px'
        }}>
          {[
            { id: 'pricing', label: 'Pricing & Config', icon: SlidersHorizontal },
            { id: 'sheets', label: 'Google Sheets Sync', icon: FileSpreadsheet },
            { id: 'security', label: 'Security & PIN', icon: KeyRound },
            { id: 'backup', label: 'Data Backup', icon: Database },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '14px 16px',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: isActive ? '2px solid var(--accent-gold)' : '2px solid transparent',
                  color: isActive ? '#fbbf24' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-heading)',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.86rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* TAB 1: PRICING & CONFIG */}
          {activeTab === 'pricing' && (
            <form onSubmit={handleConfigSubmit}>
              <div style={{ marginBottom: '16px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Stored in Google Sheets <code>Config</code> tab. These global parameters dictate the dynamic pricing calculator formulas.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '20px' }}>
                <div className="input-group" style={{ margin: 0 }}>
                  <label className="input-label">STITCH RATE (PER 1,000 STITCHES)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>₹</span>
                    <input
                      type="number"
                      step="0.5"
                      className="input-field"
                      value={config.stitch_rate_per_1000}
                      onChange={(e) => setConfig({ ...config, stitch_rate_per_1000: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="input-group" style={{ margin: 0 }}>
                  <label className="input-label">HOURLY LABOR RATE</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}>₹</span>
                    <input
                      type="number"
                      step="5"
                      className="input-field"
                      value={config.hourly_labor_rate}
                      onChange={(e) => setConfig({ ...config, hourly_labor_rate: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="input-group" style={{ margin: 0 }}>
                  <label className="input-label">GST RATE PERCENT (%)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ color: 'var(--accent-indigo)', fontWeight: 700 }}>%</span>
                    <input
                      type="number"
                      step="1"
                      className="input-field"
                      value={config.gst_rate_percent}
                      onChange={(e) => setConfig({ ...config, gst_rate_percent: e.target.value })}
                      required
                    />
                  </div>
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', marginBottom: '16px' }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '12px' }}>
                  INVOICE HEADER DETAILS
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
                  <div className="input-group" style={{ margin: 0 }}>
                    <label className="input-label">BUSINESS NAME</label>
                    <input
                      type="text"
                      className="input-field"
                      value={config.studio_name}
                      onChange={(e) => setConfig({ ...config, studio_name: e.target.value })}
                    />
                  </div>
                  <div className="input-group" style={{ margin: 0 }}>
                    <label className="input-label">TAGLINE</label>
                    <input
                      type="text"
                      className="input-field"
                      value={config.tagline}
                      onChange={(e) => setConfig({ ...config, tagline: e.target.value })}
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">BUSINESS ADDRESS</label>
                  <input
                    type="text"
                    className="input-field"
                    value={config.studio_address}
                    onChange={(e) => setConfig({ ...config, studio_address: e.target.value })}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div className="input-group" style={{ margin: 0 }}>
                    <label className="input-label">PHONE</label>
                    <input
                      type="text"
                      className="input-field"
                      value={config.studio_phone}
                      onChange={(e) => setConfig({ ...config, studio_phone: e.target.value })}
                    />
                  </div>
                  <div className="input-group" style={{ margin: 0 }}>
                    <label className="input-label">GSTIN</label>
                    <input
                      type="text"
                      className="input-field"
                      value={config.studio_gstin}
                      onChange={(e) => setConfig({ ...config, studio_gstin: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }}>
                Save Pricing & Config
              </button>
            </form>
          )}

          {/* TAB 2: GOOGLE SHEETS SYNC */}
          {activeTab === 'sheets' && (
            <div>
              {/* Cloud Run Live Sheets API Status Banner */}
              <div style={{
                padding: '16px 18px',
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(6, 182, 212, 0.08))',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                marginBottom: '20px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--accent-emerald)', boxShadow: '0 0 10px var(--accent-emerald)' }}></span>
                    <span style={{ fontWeight: 700, color: '#34d399', fontSize: '0.92rem' }}>
                      Google Sheets API Active (GCP Cloud Run)
                    </span>
                  </div>
                  <span style={{ fontSize: '0.74rem', background: 'rgba(255,255,255,0.08)', padding: '2px 8px', borderRadius: '4px', color: '#94a3b8' }}>
                    10 Tabs Connected
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.5, marginBottom: '14px' }}>
                  Connected to Spreadsheet: <strong>AI_Agent</strong> (<code>1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA</code>).
                  <br />
                  Bidirectional sync active for: <code>Orders</code>, <code>Sales_Ledger</code>, <code>Expense_Ledger</code>, <code>Asset_Ledger</code>, <code>Capital_Ledger</code>, <code>Customers</code>, <code>Vendors</code>.
                </div>

                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ fontSize: '0.86rem', padding: '10px 16px' }}
                    onClick={async () => {
                      try {
                        setTestStatus({ loading: true, message: 'Syncing all data from Google Sheets...' });
                        await googleSheetsService.syncAll(true);
                        setTestStatus({ success: true, message: 'Successfully synced all data with Google Sheets!' });
                      } catch (err) {
                        setTestStatus({ error: true, message: 'Sync failed: ' + err.message });
                      }
                    }}
                  >
                    <RefreshCw size={15} />
                    <span>Sync All Data from Google Sheets Now</span>
                  </button>

                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.86rem', padding: '10px 16px', color: 'var(--accent-rose)' }}
                    onClick={async () => {
                      if (window.confirm('Clear local browser storage and pull a fresh copy of everything from Google Sheets?')) {
                        try {
                          setTestStatus({ loading: true, message: 'Clearing local cache and re-syncing...' });
                          await googleSheetsService.clearCacheAndResync();
                          setTestStatus({ success: true, message: 'Local cache cleared and fresh data loaded from Google Sheets!' });
                        } catch (err) {
                          setTestStatus({ error: true, message: 'Failed: ' + err.message });
                        }
                      }
                    }}
                  >
                    <RotateCcw size={15} />
                    <span>Clear Local Cache & Force Full Re-Sync</span>
                  </button>
                </div>

                {testStatus && (
                  <div style={{
                    marginTop: '12px',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    background: testStatus.success ? 'rgba(16, 185, 129, 0.2)' : (testStatus.error ? 'rgba(244, 63, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)'),
                    border: testStatus.success ? '1px solid #10b981' : (testStatus.error ? '1px solid #f43f5e' : '1px solid #f59e0b'),
                    color: testStatus.success ? '#34d399' : (testStatus.error ? '#f43f5e' : '#fbbf24'),
                    fontSize: '0.82rem'
                  }}>
                    {testStatus.message}
                  </div>
                )}
              </div>

              {/* Optional Apps Script Section */}
              <div style={{
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                marginBottom: '20px'
              }}>
                <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  Alternative Webhook / Apps Script Connector (Optional)
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                  If you ever host this frontend on a static hosting provider without the Cloud Run API backend, you can configure an Apps Script URL below.
                </div>
                <form onSubmit={handleSaveSheets}>
                  <div className="input-group">
                    <label className="input-label">GOOGLE APPS SCRIPT WEB APP URL</label>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="url"
                        placeholder="https://script.google.com/macros/s/.../exec"
                        className="input-field"
                        value={scriptUrl}
                        onChange={(e) => setScriptUrl(e.target.value)}
                      />
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleTestConnection}
                      >
                        <RefreshCw size={15} />
                        <span>Test</span>
                      </button>
                    </div>
                  </div>

                {testStatus && (
                  <div style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: testStatus.success ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                    border: testStatus.success ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(244, 63, 94, 0.3)',
                    color: testStatus.success ? '#34d399' : '#f43f5e',
                    fontSize: '0.84rem',
                    marginBottom: '16px'
                  }}>
                    {testStatus.message}
                  </div>
                )}

                <button type="submit" className="btn btn-primary" style={{ width: '100%', marginBottom: '14px' }}>
                  Save Connection Settings
                </button>
              </form>
            </div>

              {/* Step-by-step Apps Script Deployment Guide */}
              <div style={{
                background: 'rgba(9, 13, 22, 0.7)',
                padding: '18px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                    GOOGLE APPS SCRIPT CONNECTOR CODE
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                    onClick={handleCopyScript}
                  >
                    {copiedScript ? <Check size={14} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={14} />}
                    <span>{copiedScript ? 'Copied!' : 'Copy Script'}</span>
                  </button>
                </div>

                <ol style={{ fontSize: '0.78rem', color: 'var(--text-muted)', paddingLeft: '18px', lineHeight: 1.6 }}>
                  <li>Create a new blank Google Spreadsheet.</li>
                  <li>Go to <strong>Extensions &gt; Apps Script</strong>.</li>
                  <li>Click <strong>Copy Script</strong> above and paste it into <code>Code.gs</code>.</li>
                  <li>Click <strong>Deploy &gt; New deployment &gt; Web app</strong>. Set access to <strong>"Anyone"</strong>.</li>
                  <li>Paste the generated Web App URL into the box above and click <strong>Test</strong>!</li>
                </ol>
              </div>
            </div>
          )}

          {/* TAB 3: SECURITY & PIN */}
          {activeTab === 'security' && (
            <form onSubmit={handlePinSubmit}>
              <div style={{ marginBottom: '16px', fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                Protect pricing, client invoice history, and profit margins behind a 4-digit PIN.
              </div>

              {pinMessage.text && (
                <div style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: pinMessage.isError ? 'rgba(244, 63, 94, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                  border: pinMessage.isError ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                  color: pinMessage.isError ? '#f43f5e' : '#34d399',
                  fontSize: '0.85rem',
                  marginBottom: '16px'
                }}>
                  {pinMessage.text}
                </div>
              )}

              <div className="input-group">
                <label className="input-label">CURRENT PIN</label>
                <input
                  type="password"
                  maxLength={4}
                  className="input-field"
                  placeholder="Default is 8911"
                  value={oldPin}
                  onChange={(e) => setOldPin(e.target.value)}
                  required
                />
              </div>

              <div className="input-group">
                <label className="input-label">NEW 4-DIGIT PIN</label>
                <input
                  type="password"
                  maxLength={4}
                  className="input-field"
                  placeholder="Enter 4 digits"
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value)}
                  required
                />
              </div>

              <div className="input-group">
                <label className="input-label">CONFIRM NEW PIN</label>
                <input
                  type="password"
                  maxLength={4}
                  className="input-field"
                  placeholder="Re-enter 4 digits"
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value)}
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }}>
                Update Security PIN
              </button>
            </form>
          )}

          {/* TAB 4: DATA BACKUP & RESTORE */}
          {activeTab === 'backup' && (
            <div>
              <div style={{ marginBottom: '16px', fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                Export your full database as a JSON snapshot, import a previous backup, or reset to initial defaults.
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#f8fafc' }}>Export Database Backup</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Downloads all sales, expenses, assets, and config as JSON</div>
                  </div>
                  <button type="button" className="btn btn-secondary" onClick={handleExportData}>
                    <Download size={16} />
                    <span>Export JSON</span>
                  </button>
                </div>

                <div style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#f8fafc' }}>Restore from Backup</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Upload a previously exported JSON backup file</div>
                  </div>
                  <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
                    <Upload size={16} />
                    <span>Upload JSON</span>
                    <input type="file" accept=".json" onChange={handleImportData} style={{ display: 'none' }} />
                  </label>
                </div>

                <div style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(244, 63, 94, 0.06)',
                  border: '1px solid rgba(244, 63, 94, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginTop: '10px'
                }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#f43f5e' }}>Reset to Factory Demo Data</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Replaces current storage with original sample invoices and assets</div>
                  </div>
                  <button type="button" className="btn btn-danger" onClick={handleResetData}>
                    <RotateCcw size={16} />
                    <span>Reset</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
