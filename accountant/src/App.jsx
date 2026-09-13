import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar/Navbar';
import PinLockScreen from './components/Auth/PinLockScreen';
import Dashboard from './components/Dashboard/Dashboard';
import InvoiceManager from './components/Invoicing/InvoiceManager';
import ExpenseManager from './components/Expenses/ExpenseManager';
import AssetManager from './components/Assets/AssetManager';
import OrdersManager from './components/Orders/OrdersManager';
import SettingsModal from './components/Settings/SettingsModal';
import MasterDataManager from './components/MasterData/MasterDataManager';
import { storageService } from './services/storageService';
import { googleSheetsService } from './services/googleSheetsService';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('App uncaught error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#090d16',
          color: '#f8fafc',
          padding: '24px',
          textAlign: 'center'
        }}>
          <div style={{
            maxWidth: '480px',
            padding: '32px',
            borderRadius: '20px',
            background: 'rgba(18, 26, 44, 0.8)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)'
          }}>
            <img src="/siteLogo.png" alt="CJS Designs" style={{ maxHeight: '42px', marginBottom: '16px' }} />
            <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>Application Reload Required</h3>
            <p style={{ fontSize: '0.84rem', color: '#94a3b8', marginBottom: '20px' }}>
              {this.state.error?.message || 'A temporary display error occurred.'}
            </p>
            <button
              className="btn btn-primary"
              onClick={() => {
                localStorage.clear();
                window.location.reload();
              }}
            >
              Clear Cache & Refresh App
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}

function MainApp() {
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showSettings, setShowSettings] = useState(false);

  // Transfer states between modules
  const [invoiceViewId, setInvoiceViewId] = useState(null);
  const [invoiceCreatePayload, setInvoiceCreatePayload] = useState(null);
  const [expenseLogTrigger, setExpenseLogTrigger] = useState(false);

  // Google Sheet settings status
  const [settings, setSettings] = useState(storageService.getSettings());

  useEffect(() => {
    // Automatically pull latest Google Sheets data on app startup
    googleSheetsService.syncAll(false).catch(() => {});

    return storageService.subscribe(() => {
      setSettings(storageService.getSettings());
    });
  }, []);

  // Quick Action handlers
  const handleOpenNewInvoice = () => {
    setInvoiceCreatePayload({
      serviceType: 'Machine Embroidery',
      totalStitches: 60000,
      laborHours: 5,
      marginPercent: 25,
      courier: 0
    });
    setInvoiceViewId(null);
    setActiveTab('invoicing');
  };

  const handleOpenNewExpense = () => {
    setExpenseLogTrigger(Date.now());
    setActiveTab('expenses');
  };

  const handleGenerateInvoiceFromOrder = (orderPayload) => {
    setInvoiceCreatePayload(orderPayload);
    setInvoiceViewId(null);
    setActiveTab('invoicing');
  };

  const handleViewInvoiceFromDashboard = (invId) => {
    if (invId) {
      setInvoiceViewId(invId);
      setInvoiceCreatePayload(null);
    }
    setActiveTab('invoicing');
  };

  // If locked, render PIN screen
  if (!isUnlocked) {
    return <PinLockScreen onUnlock={() => setIsUnlocked(true)} />;
  }


  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Navbar with Header and Mobile Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLock={() => setIsUnlocked(false)}
        onOpenNewInvoice={handleOpenNewInvoice}
        onOpenNewExpense={handleOpenNewExpense}
      />

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'dashboard' && (
          <Dashboard
            onNewInvoice={handleOpenNewInvoice}
            onNewExpense={handleOpenNewExpense}
            onViewInvoice={handleViewInvoiceFromDashboard}
            onGoToOrders={() => setActiveTab('orders')}
            onGenerateInvoiceFromOrder={handleGenerateInvoiceFromOrder}
          />
        )}

        {activeTab === 'orders' && (
          <OrdersManager
            onGenerateInvoice={handleGenerateInvoiceFromOrder}
            onViewInvoice={handleViewInvoiceFromDashboard}
          />
        )}

        {activeTab === 'invoicing' && (
          <InvoiceManager
            initialViewInvoiceId={invoiceViewId}
            initialCreatePayload={invoiceCreatePayload}
            onClearInitial={() => {
              setInvoiceViewId(null);
              setInvoiceCreatePayload(null);
            }}
          />
        )}

        {activeTab === 'expenses' && (
          <ExpenseManager
            initialLogTrigger={expenseLogTrigger}
          />
        )}

        {activeTab === 'assets' && (
          <AssetManager />
        )}

        {activeTab === 'master_data' && (
          <MasterDataManager />
        )}
      </main>

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onLock={() => {
            setShowSettings(false);
            setIsUnlocked(false);
          }}
        />
      )}
    </div>
  );
}
