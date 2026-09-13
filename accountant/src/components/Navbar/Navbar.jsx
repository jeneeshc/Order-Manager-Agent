import React from 'react';
import { 
  LayoutDashboard, 
  ReceiptText, 
  Wallet, 
  Landmark, 
  SlidersHorizontal, 
  Lock, 
  PlusCircle, 
  Package
} from 'lucide-react';
import { storageService } from '../../services/storageService';

export default function Navbar({ 
  activeTab, 
  setActiveTab, 
  onLock, 
  onOpenNewInvoice, 
  onOpenNewExpense
}) {
  const config = storageService.getConfig();
  const [estimatedCount, setEstimatedCount] = React.useState(() => storageService.getEstimatedOrdersCount());

  React.useEffect(() => {
    return storageService.subscribe(() => {
      setEstimatedCount(storageService.getEstimatedOrdersCount());
    });
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'orders', label: 'Orders', icon: Package, badge: estimatedCount },
    { id: 'invoicing', label: 'Invoices', icon: ReceiptText },
    { id: 'expenses', label: 'Expenses', icon: Wallet },
    { id: 'assets', label: 'Assets & Capital', icon: Landmark },
    { id: 'master_data', label: 'Master Data', icon: SlidersHorizontal },
  ];

  return (
    <>
      {/* Top Header Bar */}
      <header className="no-print" style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        background: 'rgba(9, 13, 22, 0.88)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '10px 20px'
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          {/* Main Top Header: App Logo, Tagline & Settings / Lock */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px'
          }}>
            {/* Brand Logo & Tagline */}
            <div 
              style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} 
              onClick={() => setActiveTab('dashboard')}
              title="CJS Designs - Return to Dashboard"
            >
              <div style={{
                height: '38px',
                padding: '3px 10px',
                borderRadius: '10px',
                background: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 2px 10px rgba(0, 0, 0, 0.2)'
              }}>
                <img src="/siteLogo.png" alt="CJS Designs" style={{ height: '28px', width: 'auto' }} />
              </div>
              <div>
                <div style={{ 
                  fontSize: '0.78rem', 
                  color: 'var(--accent-gold)', 
                  fontWeight: 600, 
                  letterSpacing: '0.02em',
                  lineHeight: 1.2
                }}>
                  Crafting fashion on fabric
                </div>
              </div>
            </div>

            {/* Right Side: Lock Icon */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {/* Lock Session */}
              <button
                className="btn btn-ghost"
                style={{ padding: '8px', borderRadius: 'var(--radius-md)', color: 'var(--accent-rose)' }}
                onClick={onLock}
                title="Lock Screen with PIN"
              >
                <Lock size={18} />
              </button>
            </div>
          </div>

          {/* Sub-Header Row: Navigation Tabs (Desktop) + 3 Action Buttons (New Invoice, Log Expense, Sync Sheets) */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            paddingTop: '8px',
            flexWrap: 'wrap'
          }}>
            {/* Desktop Navigation Tabs */}
            <div className="desktop-only" style={{
              display: 'flex',
              gap: '6px',
              alignItems: 'center'
            }}>
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '7px 14px',
                      borderRadius: 'var(--radius-md)',
                      background: isActive ? 'rgba(245, 158, 11, 0.12)' : 'transparent',
                      border: isActive ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid transparent',
                      color: isActive ? '#fbbf24' : 'var(--text-secondary)',
                      fontFamily: 'var(--font-heading)',
                      fontWeight: isActive ? 700 : 500,
                      fontSize: '0.86rem',
                      cursor: 'pointer',
                      transition: 'all 0.18s ease'
                    }}
                  >
                    <Icon size={16} />
                    <span>{item.label}</span>
                    {item.badge > 0 && (
                      <span style={{
                        background: '#f59e0b',
                        color: '#090d16',
                        borderRadius: '10px',
                        padding: '2px 7px',
                        fontSize: '0.72rem',
                        fontWeight: 800,
                        lineHeight: 1,
                        marginLeft: '4px'
                      }}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Action Buttons: New Invoice, Log Expense */}
            <div className="header-actions-row" style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginLeft: 'auto'
            }}>
              {/* Quick Action: New Invoice */}
              <button
                className="btn btn-primary"
                style={{ padding: '7px 14px', fontSize: '0.84rem' }}
                onClick={onOpenNewInvoice}
              >
                <PlusCircle size={15} />
                <span>+ New Invoice</span>
              </button>

              {/* Quick Action: Log Expense */}
              <button
                className="btn btn-emerald"
                style={{ padding: '7px 14px', fontSize: '0.84rem' }}
                onClick={onOpenNewExpense}
              >
                <PlusCircle size={15} />
                <span>+ Log Expense</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Bottom Navigation Bar (Optimized for iPhone thumb navigation) */}
      <nav className="mobile-bottom-nav no-print" style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 90,
        background: 'rgba(11, 15, 25, 0.92)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-around',
        padding: '6px 8px env(safe-area-inset-bottom, 12px) 8px',
      }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '3px',
                background: 'transparent',
                border: 'none',
                color: isActive ? '#fbbf24' : 'var(--text-muted)',
                padding: '6px 10px',
                cursor: 'pointer',
                borderRadius: '12px',
                minWidth: '58px',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{
                position: 'relative',
                transform: isActive ? 'scale(1.15)' : 'scale(1)',
                transition: 'transform 0.2s ease'
              }}>
                <Icon size={20} />
                {item.badge > 0 && (
                  <span style={{
                    position: 'absolute',
                    top: '-6px',
                    right: '-9px',
                    background: '#f59e0b',
                    color: '#090d16',
                    borderRadius: '8px',
                    padding: '1px 5px',
                    fontSize: '0.62rem',
                    fontWeight: 800,
                    lineHeight: 1
                  }}>
                    {item.badge}
                  </span>
                )}
              </div>
              <span style={{
                fontSize: '0.68rem',
                fontFamily: 'var(--font-heading)',
                fontWeight: isActive ? 700 : 500
              }}>
                {item.label.split(' ')[0]}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Responsive media helper CSS */}
      <style>{`
        @media (max-width: 768px) {
          .desktop-only {
            display: none !important;
          }
          .mobile-bottom-nav {
            display: flex !important;
          }
          .header-actions-row {
            width: 100% !important;
            margin-left: 0 !important;
            justify-content: space-between !important;
            gap: 6px !important;
          }
          .header-actions-row .btn {
            flex: 1 1 0;
            justify-content: center;
            padding: 7px 6px !important;
            font-size: 0.76rem !important;
            white-space: nowrap;
          }
        }
        @media (min-width: 769px) {
          .mobile-bottom-nav {
            display: none !important;
          }
          .desktop-only {
            display: flex;
          }
        }
      `}</style>
    </>
  );
}
