import React, { useState, useEffect } from 'react';
import { 
  Calculator, 
  Sparkles, 
  Percent, 
  Clock, 
  Scissors, 
  Truck, 
  ArrowRight, 
  CheckCircle2, 
  Info,
  DollarSign,
  TrendingUp,
  Receipt
} from 'lucide-react';
import { storageService, parseCurrency, parseInteger } from '../../services/storageService';
import { googleSheetsService } from '../../services/googleSheetsService';

const SERVICES = [
  'Machine Embroidery',
  'Machine Embroidery Design Making',
  'Custom Monogram & Logo Embroidery',
  'Sample Swatch / Prototype Strike-off',
  'Garment Embroidery Alteration / Rework'
];

export default function PricingCalculator({ onTransferToInvoice }) {
  const [config, setConfig] = useState(storageService.getConfig());
  
  // Service selection: 'Machine Embroidery' or 'Machine Embroidery Design Making'
  const [serviceType, setServiceType] = useState('Machine Embroidery');
  
  // Inputs
  const [stitchCount, setStitchCount] = useState(75000);
  const [laborHours, setLaborHours] = useState(6);
  const [profitMargin, setProfitMargin] = useState(25); // percentage e.g. 25%
  const [courierCharge, setCourierCharge] = useState(150);
  const [hasCourier, setHasCourier] = useState(true);
  
  // Job Info
  const [customerName, setCustomerName] = useState('');
  const [jobDescription, setJobDescription] = useState('');

  // Collect all customers dynamically from Google Sheets
  const [sheetCustomers, setSheetCustomers] = useState(() => googleSheetsService.getCustomers());

  useEffect(() => {
    setSheetCustomers(googleSheetsService.getCustomers());
    return storageService.subscribe(() => {
      setSheetCustomers(googleSheetsService.getCustomers());
    });
  }, []);

  const allCustomerNames = Array.from(new Set(
    sheetCustomers.map(c => c.Name || c.name).filter(Boolean)
  ));
  const isPredefinedCust = allCustomerNames.some(c => c.toLowerCase() === customerName.toLowerCase());
  const [isCustomCustomer, setIsCustomCustomer] = useState(!isPredefinedCust && !!customerName);

  // Update config if updated elsewhere
  useEffect(() => {
    return storageService.subscribe(() => {
      setConfig(storageService.getConfig());
    });
  }, []);

  // When service type changes to Design Making, stitch count is forced to 0
  useEffect(() => {
    if (serviceType === 'Machine Embroidery Design Making') {
      setStitchCount(0);
    } else if (stitchCount === 0) {
      setStitchCount(50000);
    }
  }, [serviceType]);

  // Rates from config
  const ratePer1000 = parseCurrency(config.stitch_rate_per_1000) || 8;
  const hourlyRate = parseCurrency(config.hourly_labor_rate) || 100;
  const gstRate = parseCurrency(config.gst_rate_percent) || 18;

  // Pricing Engine Calculations
  // Stitch Cost = (Stitch Count / 1000) * 8
  const stitchCost = serviceType === 'Machine Embroidery' 
    ? (Math.max(0, parseInteger(stitchCount)) / 1000) * ratePer1000
    : 0;

  // Labor Cost = Labor Hours * 100
  const laborCost = (Math.max(0, parseCurrency(laborHours))) * hourlyRate;

  // Base Cost = Stitch Cost + Labor Cost
  const baseCost = stitchCost + laborCost;

  // Selling Price (Pre-Tax) = Base Cost * (1 + (Profit Margin % / 100))
  const marginMultiplier = 1 + (parseCurrency(profitMargin) / 100);
  const preTaxSellingPrice = Number((baseCost * marginMultiplier).toFixed(2));
  const markupAmount = Number((preTaxSellingPrice - baseCost).toFixed(2));

  // GST = Selling Price (Pre-Tax) * (GST Rate / 100)
  const gstAmount = Number((preTaxSellingPrice * (gstRate / 100)).toFixed(2));

  // Final Courier
  const activeCourier = hasCourier ? parseCurrency(courierCharge) : 0;

  // Final Invoice Total = (Selling Price (Pre-Tax) * 1.18) + Courier Charge
  const finalInvoiceTotal = Number((preTaxSellingPrice + gstAmount + activeCourier).toFixed(2));

  // Preset buttons
  const stitchPresets = [25000, 50000, 85000, 120000, 200000, 350000];
  const laborPresets = [1, 2, 4, 6, 8, 12, 16];
  const marginPresets = [15, 20, 25, 30, 35, 50];

  const handleGenerateInvoice = () => {
    const defaultDesc = jobDescription.trim() || (
      serviceType === 'Machine Embroidery'
        ? `Custom Machine Embroidery (${parseInteger(stitchCount).toLocaleString()} Stitches)`
        : `Embroidery Digitizing & Master EMB/DST File Preparation`
    );

    const invoicePayload = {
      customer: customerName.trim() || 'Valued Boutique Client',
      serviceType,
      description: defaultDesc,
      totalStitches: serviceType === 'Machine Embroidery' ? parseInteger(stitchCount) : 0,
      laborHours: parseCurrency(laborHours),
      marginPercent: parseCurrency(profitMargin),
      baseCost,
      netPrice: preTaxSellingPrice,
      gst: gstAmount,
      courier: activeCourier,
      grossTotal: finalInvoiceTotal
    };

    onTransferToInvoice(invoicePayload);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <div style={{
            padding: '8px',
            borderRadius: '12px',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            color: '#fbbf24'
          }}>
            <Calculator size={22} />
          </div>
          <h2 style={{ fontSize: '1.75rem' }}>Dynamic Pricing Engine</h2>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
          Real-time order costing, margin optimization, and tax breakdown configured to CJS Designs formulas.
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
        gap: '24px',
        alignItems: 'start'
      }}>
        {/* Left Column: Input Form */}
        <div className="glass-panel" style={{ padding: '26px' }}>
          {/* Service Category Selection */}
          <div style={{ marginBottom: '22px' }}>
            <label className="input-label" style={{ marginBottom: '8px' }}>
              <span>SELECT SERVICE CATEGORY</span>
              <span className="badge badge-gold">Active</span>
            </label>
            <select
              className="input-field"
              style={{ fontSize: '0.95rem', fontWeight: 600, padding: '12px 14px' }}
              value={serviceType}
              onChange={(e) => setServiceType(e.target.value)}
            >
              {SERVICES.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Stitch Count (only if Machine Embroidery) */}
          {serviceType === 'Machine Embroidery' ? (
            <div className="input-group" style={{ marginBottom: '22px' }}>
              <div className="input-label">
                <span>TOTAL STITCH COUNT</span>
                <span style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>
                  ₹{ratePer1000} / 1,000 stitches
                </span>
              </div>
              <input
                type="number"
                min="0"
                step="1000"
                className="input-field"
                style={{ fontSize: '1.1rem', fontWeight: 600 }}
                value={stitchCount}
                onChange={(e) => setStitchCount(e.target.value)}
              />
              {/* Presets */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                {stitchPresets.map((val) => (
                  <button
                    key={val}
                    type="button"
                    className="btn btn-secondary"
                    style={{
                      padding: '4px 8px',
                      fontSize: '0.74rem',
                      background: parseInt(stitchCount) === val ? 'rgba(245, 158, 11, 0.25)' : undefined,
                      borderColor: parseInt(stitchCount) === val ? 'var(--accent-gold)' : undefined
                    }}
                    onClick={() => setStitchCount(val)}
                  >
                    {(val / 1000)}k
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div style={{
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              color: '#c7d2fe',
              fontSize: '0.84rem',
              marginBottom: '22px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <Info size={18} style={{ color: '#818cf8', flexShrink: 0 }} />
              <span>Design Making service defaults stitch count to <strong>0</strong>. Pricing is calculated purely on digitizing labor hours.</span>
            </div>
          )}

          {/* Labor Hours */}
          <div className="input-group" style={{ marginBottom: '22px' }}>
            <div className="input-label">
              <span>LABOR HOURS BILLED</span>
              <span style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}>
                ₹{hourlyRate} / hour
              </span>
            </div>
            <input
              type="number"
              min="0"
              step="0.5"
              className="input-field"
              style={{ fontSize: '1.1rem', fontWeight: 600 }}
              value={laborHours}
              onChange={(e) => setLaborHours(e.target.value)}
            />
            {/* Presets */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
              {laborPresets.map((val) => (
                <button
                  key={val}
                  type="button"
                  className="btn btn-secondary"
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.74rem',
                    background: parseFloat(laborHours) === val ? 'rgba(16, 185, 129, 0.25)' : undefined,
                    borderColor: parseFloat(laborHours) === val ? 'var(--accent-emerald)' : undefined
                  }}
                  onClick={() => setLaborHours(val)}
                >
                  {val} {val === 1 ? 'hr' : 'hrs'}
                </button>
              ))}
            </div>
          </div>

          {/* Profit Margin % */}
          <div className="input-group" style={{ marginBottom: '22px' }}>
            <div className="input-label">
              <span>TARGET PROFIT MARGIN</span>
              <span style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>
                {profitMargin}% Markup
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={profitMargin}
                onChange={(e) => setProfitMargin(e.target.value)}
                style={{
                  flex: 1,
                  accentColor: 'var(--accent-gold)',
                  cursor: 'pointer'
                }}
              />
              <input
                type="number"
                min="0"
                max="200"
                className="input-field"
                style={{ width: '76px', textAlign: 'center', fontWeight: 700 }}
                value={profitMargin}
                onChange={(e) => setProfitMargin(e.target.value)}
              />
            </div>
            {/* Presets */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
              {marginPresets.map((val) => (
                <button
                  key={val}
                  type="button"
                  className="btn btn-secondary"
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.74rem',
                    background: parseFloat(profitMargin) === val ? 'rgba(245, 158, 11, 0.25)' : undefined,
                    borderColor: parseFloat(profitMargin) === val ? 'var(--accent-gold)' : undefined
                  }}
                  onClick={() => setProfitMargin(val)}
                >
                  {val}%
                </button>
              ))}
            </div>
          </div>

          {/* Courier Charges */}
          <div className="input-group" style={{ marginBottom: '24px' }}>
            <div className="input-label">
              <span>COURIER / SHIPPING CHARGE (OPTIONAL)</span>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={hasCourier}
                  onChange={(e) => setHasCourier(e.target.checked)}
                  style={{ accentColor: 'var(--accent-gold)' }}
                />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Include Courier</span>
              </label>
            </div>
            {hasCourier && (
              <input
                type="number"
                min="0"
                step="10"
                className="input-field"
                placeholder="Enter courier amount in ₹"
                value={courierCharge}
                onChange={(e) => setCourierCharge(e.target.value)}
              />
            )}
          </div>

          {/* Optional Client Details */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '18px' }}>
            <div className="input-group">
              <label className="input-label">CUSTOMER / BOUTIQUE NAME (OPTIONAL)</label>
              <select
                className="input-field"
                style={{ marginBottom: isCustomCustomer ? '8px' : '0' }}
                value={isCustomCustomer ? '__custom__' : (customerName || '')}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '__custom__') {
                    setIsCustomCustomer(true);
                    setCustomerName('');
                  } else {
                    setIsCustomCustomer(false);
                    setCustomerName(val);
                  }
                }}
              >
                <option value="">-- Select Customer / Boutique (Optional) --</option>
                <optgroup label="Saved Customers & Boutiques">
                  {allCustomerNames.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </optgroup>
                <option value="__custom__">+ Enter New Customer...</option>
              </select>

              {isCustomCustomer && (
                <input
                  type="text"
                  className="input-field"
                  placeholder="Enter customer or boutique name"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  autoFocus
                />
              )}
            </div>
            <div className="input-group">
              <label className="input-label">JOB / GARMENT DESCRIPTION</label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. Floral Blouse Yoke & Sleeve Borders"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Right Column: Live Calculation Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Main Price Card */}
          <div className="glass-panel glass-panel-gold" style={{ padding: '28px', position: 'relative', overflow: 'hidden' }}>
            <div style={{
              position: 'absolute',
              top: '-30px',
              right: '-30px',
              width: '140px',
              height: '140px',
              borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(245, 158, 11, 0.2) 0%, transparent 70%)',
              pointerEvents: 'none'
            }} />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span className="badge badge-gold">
                PRICING BREAKDOWN
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                GST ({gstRate}%) Included
              </span>
            </div>

            {/* Final Total Big Display */}
            <div style={{ marginBottom: '24px' }}>
              <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Final Invoice Total (Client Payable)
              </div>
              <div style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '3rem',
                fontWeight: 800,
                color: '#ffffff',
                display: 'flex',
                alignItems: 'baseline',
                gap: '4px',
                letterSpacing: '-0.03em'
              }}>
                <span style={{ color: 'var(--accent-gold)', fontSize: '2rem' }}>₹</span>
                <span>{finalInvoiceTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            </div>

            {/* Step-by-step Math Audit */}
            <div style={{
              background: 'rgba(9, 13, 22, 0.6)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              border: '1px solid var(--border-subtle)',
              marginBottom: '24px'
            }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
                Specification Calculation Formula
              </div>

              {/* Stitch Cost */}
              {serviceType === 'Machine Embroidery' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.88rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    Stitch Cost <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>({parseInt(stitchCount || 0).toLocaleString()} / 1000 × ₹{ratePer1000})</span>
                  </span>
                  <span style={{ fontWeight: 600 }}>₹{stitchCost.toFixed(2)}</span>
                </div>
              )}

              {/* Labor Cost */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.88rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>
                  Labor Cost <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>({laborHours} hrs × ₹{hourlyRate})</span>
                </span>
                <span style={{ fontWeight: 600 }}>₹{laborCost.toFixed(2)}</span>
              </div>

              {/* Base Cost */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.88rem', color: 'var(--accent-indigo)' }}>
                <span style={{ fontWeight: 600 }}>Base Cost (Internal COGS)</span>
                <span style={{ fontWeight: 700 }}>₹{baseCost.toFixed(2)}</span>
              </div>

              {/* Margin / Markup */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.88rem', color: '#fbbf24' }}>
                <span>Profit Margin ({profitMargin}%)</span>
                <span style={{ fontWeight: 600 }}>+₹{markupAmount.toFixed(2)}</span>
              </div>

              {/* Selling Price Pre-Tax */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.92rem', fontWeight: 700 }}>
                <span>Selling Price (Pre-Tax)</span>
                <span style={{ color: '#ffffff' }}>₹{preTaxSellingPrice.toFixed(2)}</span>
              </div>

              {/* GST 18% */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.88rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>GST ({gstRate}%)</span>
                <span style={{ fontWeight: 600 }}>+₹{gstAmount.toFixed(2)}</span>
              </div>

              {/* Courier */}
              {hasCourier && activeCourier > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: '0.88rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Courier Shipping</span>
                  <span style={{ fontWeight: 600 }}>+₹{activeCourier.toFixed(2)}</span>
                </div>
              )}
            </div>

            {/* Confidentiality Reminder */}

            {/* Action: Transfer to Invoice */}
            <button
              type="button"
              className="btn btn-primary"
              style={{
                width: '100%',
                padding: '14px',
                fontSize: '1.05rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px'
              }}
              onClick={handleGenerateInvoice}
            >
              <Receipt size={20} />
              <span>Generate Customer Invoice</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
