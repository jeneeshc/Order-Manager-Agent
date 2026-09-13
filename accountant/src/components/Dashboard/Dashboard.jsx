import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  Activity,
  Clock,
  Scissors,
  PlusCircle,
  ArrowUpRight,
  Receipt,
  Wallet,
  Eye,
  ChevronRight,
  ShieldCheck,
  Zap,
  Sparkles,
  Bot
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { storageService, parseCurrency } from '../../services/storageService';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
);

export default function Dashboard({ onNewInvoice, onNewExpense, onViewInvoice, onGoToOrders, onGenerateInvoiceFromOrder }) {
  const [selectedPeriod, setSelectedPeriod] = useState('all'); // 'all' or 'YYYY-M'
  const [availablePeriods, setAvailablePeriods] = useState(() => storageService.getAvailablePeriods());
  const [metrics, setMetrics] = useState(() => storageService.getAllTimeMetrics());
  const [trendData, setTrendData] = useState(() => storageService.getSixMonthTrend());
  const [categoryBreakdown, setCategoryBreakdown] = useState(() => storageService.getExpenseCategoryBreakdown('all'));
  const [recentInvoices, setRecentInvoices] = useState(() => storageService.getSales().slice(0, 5));
  const [orders, setOrders] = useState(() => storageService.getOrders());

  const loadData = (period = selectedPeriod) => {
    let currentMetrics;
    let breakdown;

    if (period === 'all') {
      currentMetrics = storageService.getAllTimeMetrics();
      breakdown = storageService.getExpenseCategoryBreakdown('all');
    } else {
      const [year, month] = period.split('-').map(Number);
      currentMetrics = storageService.getMetricsForMonth(year, month);
      breakdown = storageService.getExpenseCategoryBreakdown(year, month);
    }

    const trends = storageService.getSixMonthTrend();
    const allSales = storageService.getSales();
    const recent = allSales.slice(0, 5);
    const allOrders = storageService.getOrders();
    const periods = storageService.getAvailablePeriods();

    setAvailablePeriods(periods);
    setMetrics(currentMetrics);
    setTrendData(trends);
    setCategoryBreakdown(breakdown);
    setRecentInvoices(recent);
    setOrders(allOrders);
  };

  useEffect(() => {
    loadData(selectedPeriod);
  }, [selectedPeriod]);

  useEffect(() => {
    return storageService.subscribe(() => {
      loadData(selectedPeriod);
    });
  }, [selectedPeriod]);

  const isProfitable = metrics.netProfit >= 0;

  const currentPeriodObj = availablePeriods.find(p => `${p.year}-${p.month}` === selectedPeriod);
  const periodLabel = selectedPeriod === 'all' 
    ? 'All Time' 
    : (currentPeriodObj ? currentPeriodObj.label : 'Selected Month');
  const monthName = periodLabel;

  // Chart.js Data for 6-Month Revenue vs. Expenses Trend
  const barChartData = {
    labels: trendData.map(t => t.label),
    datasets: [
      {
        label: 'Revenue (₹)',
        data: trendData.map(t => t.revenue),
        backgroundColor: 'rgba(245, 158, 11, 0.85)',
        borderColor: '#fbbf24',
        borderWidth: 1,
        borderRadius: 8
      },
      {
        label: 'Total Expenses (₹)',
        data: trendData.map(t => t.expenses),
        backgroundColor: 'rgba(244, 63, 94, 0.75)',
        borderColor: '#f43f5e',
        borderWidth: 1,
        borderRadius: 8
      }
    ]
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#94a3b8',
          font: { family: "'Plus Jakarta Sans', sans-serif", size: 12 }
        }
      },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#ffffff',
        bodyColor: '#e2e8f0',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 12,
        boxPadding: 6
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8', font: { family: "'Plus Jakarta Sans', sans-serif" } }
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: {
          color: '#94a3b8',
          font: { family: "'Plus Jakarta Sans', sans-serif" },
          callback: (val) => `₹${(val / 1000).toFixed(0)}k`
        }
      }
    }
  };

  // Chart.js Data for Expense Category Donut
  const categoryLabels = Object.keys(categoryBreakdown).filter(k => categoryBreakdown[k] > 0);
  const categoryValues = categoryLabels.map(k => categoryBreakdown[k]);

  const categoryColors = [
    '#f59e0b', // Thread (Amber)
    '#06b6d4', // Stabilizer (Cyan)
    '#eab308', // Electricity (Yellow)
    '#f43f5e', // Maintenance (Rose)
    '#8b5cf6', // Rent (Purple)
    '#6366f1', // Asset Depreciation (Indigo)
    '#64748b'  // Misc (Slate)
  ];

  const donutChartData = {
    labels: categoryLabels,
    datasets: [
      {
        data: categoryValues,
        backgroundColor: categoryColors.slice(0, categoryLabels.length),
        borderColor: '#090d16',
        borderWidth: 3,
        hoverOffset: 6
      }
    ]
  };

  const donutChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: '#94a3b8',
          font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 },
          boxWidth: 12
        }
      },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#ffffff',
        bodyColor: '#e2e8f0',
        padding: 10,
        callbacks: {
          label: (ctx) => ` ₹${ctx.raw.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
        }
      }
    },
    cutout: '68%'
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* Top Banner & Quick Actions */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '26px',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--accent-gold)', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Business Overview
            </span>
            <span style={{ color: 'var(--text-muted)' }}>•</span>
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.35)',
                borderRadius: '8px',
                color: '#fbbf24',
                fontSize: '0.84rem',
                fontWeight: 600,
                padding: '4px 10px',
                cursor: 'pointer',
                outline: 'none',
                fontFamily: 'var(--font-sans)'
              }}
            >
              <option value="all" style={{ background: '#0b0f19', color: '#fff' }}>All Time (Lifetime Financials)</option>
              {availablePeriods.map(p => (
                <option key={`${p.year}-${p.month}`} value={`${p.year}-${p.month}`} style={{ background: '#0b0f19', color: '#fff' }}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <h2 style={{ fontSize: '1.9rem', marginTop: '4px' }}>
            Financial & Production Dashboard
          </h2>
        </div>
      </div>

      {/* AI AGENT INCOMING ORDERS PULSE BANNER */}
      {(() => {
        const estimatedOrders = orders.filter(o => {
          const s = (o.status || '').trim().toLowerCase();
          return s === 'estimated';
        });
        if (estimatedOrders.length === 0) return null;

        return (
          <div className="glass-panel" style={{
            marginBottom: '26px',
            padding: '18px 24px',
            background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(15, 23, 42, 0.6) 100%)',
            border: '1px solid rgba(245, 158, 11, 0.4)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'rgba(245, 158, 11, 0.2)',
                color: 'var(--accent-gold)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                <Bot size={24} />
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontWeight: 800, fontSize: '1.05rem', color: '#ffffff' }}>
                    {estimatedOrders.length} New AI Order{estimatedOrders.length > 1 ? 's' : ''} in "Estimated" Status
                  </span>
                  <span className="badge badge-gold" style={{ fontSize: '0.72rem' }}>
                    Action Required
                  </span>
                </div>
                <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Placed via AI Agent in Google Sheet. Generate invoices or mark complete once payment is received.
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {onGoToOrders && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={onGoToOrders}
                  style={{ padding: '8px 18px', fontSize: '0.88rem' }}
                >
                  <span>View & Process Orders ({estimatedOrders.length})</span>
                  <ChevronRight size={16} />
                </button>
              )}
            </div>
          </div>
        );
      })()}

      {/* 1. THE FINANCIAL PULSE: TOP 4 KPI TILES (CURRENT MONTH) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '18px',
        marginBottom: '28px'
      }}>
        {/* Total Revenue */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Revenue (Billed)
            </span>
            <div style={{
              padding: '6px',
              borderRadius: '8px',
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#fbbf24'
            }}>
              <DollarSign size={18} />
            </div>
          </div>
          <div className="stat-val" style={{ fontSize: '2.1rem', color: '#ffffff' }}>
            ₹{metrics.totalRevenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
            From {metrics.orderCount} customer invoices this month
          </div>
        </div>

        {/* Total Expenses */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Expenses (Costs)
            </span>
            <div style={{
              padding: '6px',
              borderRadius: '8px',
              background: 'rgba(244, 63, 94, 0.15)',
              color: '#f43f5e'
            }}>
              <TrendingDown size={18} />
            </div>
          </div>
          <div className="stat-val" style={{ fontSize: '2.1rem', color: '#f43f5e' }}>
            ₹{metrics.totalExpenses.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
            ₹{metrics.operationalExpenses.toLocaleString('en-IN', { maximumFractionDigits: 0 })} ops + ₹{metrics.monthlyDepreciation.toLocaleString('en-IN', { maximumFractionDigits: 0 })} depreciation
          </div>
        </div>

        {/* Net Profit */}
        <div className={`glass-panel ${isProfitable ? 'glass-panel-gold' : ''}`} style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Net Profit
            </span>
            <div style={{
              padding: '6px',
              borderRadius: '8px',
              background: isProfitable ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
              color: isProfitable ? 'var(--accent-emerald)' : 'var(--accent-rose)'
            }}>
              <TrendingUp size={18} />
            </div>
          </div>
          <div className="stat-val" style={{ fontSize: '2.1rem', color: isProfitable ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
            ₹{metrics.netProfit.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.8rem', color: isProfitable ? '#a7f3d0' : '#fecdd3', marginTop: '6px' }}>
            Revenue minus operational costs & equipment depreciation
          </div>
        </div>

        {/* Net Profit Margin */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Net Profit Margin
            </span>
            <div style={{
              padding: '6px',
              borderRadius: '8px',
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#a5b4fc'
            }}>
              <Percent size={18} />
            </div>
          </div>
          <div className="stat-val" style={{ fontSize: '2.1rem', color: 'var(--accent-indigo)' }}>
            {metrics.netProfitMargin.toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
            Net profit ÷ billed revenue
          </div>
        </div>
      </div>

      {/* 2. PRODUCTION METRICS (MACHINE UTILIZATION & WORKFLOW) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '28px'
      }}>
        <div className="glass-panel" style={{ padding: '18px 20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fbbf24',
            flexShrink: 0
          }}>
            <Scissors size={22} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Stitches Billed This Month
            </div>
            <div className="stat-val" style={{ fontSize: '1.45rem', color: '#ffffff' }}>
              {metrics.totalStitches.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              Helps forecast thread & maintenance
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '18px 20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#34d399',
            flexShrink: 0
          }}>
            <Clock size={22} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Labor Hours Logged
            </div>
            <div className="stat-val" style={{ fontSize: '1.45rem', color: '#ffffff' }}>
              {metrics.laborHours} hrs
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              Operator machine running time
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '18px 20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: 'rgba(99, 102, 241, 0.12)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#a5b4fc',
            flexShrink: 0
          }}>
            <Activity size={22} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Average Order Value (AOV)
            </div>
            <div className="stat-val" style={{ fontSize: '1.45rem', color: '#ffffff' }}>
              ₹{metrics.averageOrderValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              Total Revenue ÷ {metrics.orderCount || 1} Orders
            </div>
          </div>
        </div>
      </div>

      {/* 3. VISUAL CHARTS SECTION */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '22px',
        marginBottom: '28px'
      }}>
        {/* Chart 1: 6-Month Revenue vs Expenses Trend */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem' }}>Revenue vs. Expenses Trend</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                6-Month trajectory monitoring cost creep vs. sales income
              </p>
            </div>
            <span className="badge badge-gold">6 Months</span>
          </div>

          <div style={{ height: '260px', width: '100%' }}>
            <Bar data={barChartData} options={barChartOptions} />
          </div>
        </div>

        {/* Chart 2: Expense Category Breakdown Donut */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem' }}>Expense Distribution</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Expense breakdown for {periodLabel} (Operational + Depreciation)
              </p>
            </div>
            <span className="badge badge-emerald">{periodLabel}</span>
          </div>

          <div style={{ height: '260px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {categoryValues.length > 0 ? (
              <Doughnut data={donutChartData} options={donutChartOptions} />
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                No expenses logged for {periodLabel}.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4. RECENT INVOICES (LAST 5 INVOICES) */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem' }}>Recent Invoices</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Last 5 generated billing documents
            </p>
          </div>

          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.82rem', padding: '6px 14px' }}
            onClick={() => onViewInvoice && onViewInvoice(null)}
          >
            <span>View All Invoices</span>
            <ChevronRight size={15} />
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(255,255,255,0.02)' }}>
                <th style={{ padding: '12px 16px', fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Invoice</th>
                <th style={{ padding: '12px 16px', fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Date</th>
                <th style={{ padding: '12px 16px', fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Customer / Boutique</th>
                <th style={{ padding: '12px 16px', fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Service</th>
                <th style={{ padding: '12px 16px', fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Status</th>
                <th style={{ padding: '12px 16px', fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Amount</th>
                <th style={{ padding: '12px 16px', fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {recentInvoices.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No invoices generated yet. Click [ + New Invoice ] to start!
                  </td>
                </tr>
              ) : (
                recentInvoices.map((inv) => (
                  <tr
                    key={inv.id}
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '12px 16px', fontWeight: 700, color: '#fbbf24', fontFamily: 'var(--font-heading)' }}>
                      {inv.id}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                      {inv.date}
                    </td>
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f8fafc' }}>
                      {inv.customer}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span className={`badge ${inv.serviceType === 'Machine Embroidery' ? 'badge-gold' : 'badge-indigo'}`}>
                        {inv.serviceType === 'Machine Embroidery' ? 'Embroidery' : 'Digitizing'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span className={`badge ${inv.status === 'Paid' ? 'badge-emerald' : 'badge-gold'}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: '#ffffff' }}>
                      ₹{parseCurrency(inv.grossTotal).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '5px 10px', fontSize: '0.78rem' }}
                        onClick={() => onViewInvoice && onViewInvoice(inv.id)}
                      >
                        <Eye size={14} />
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
