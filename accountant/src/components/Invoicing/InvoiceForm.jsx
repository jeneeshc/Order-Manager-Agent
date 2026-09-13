import React, { useState, useEffect } from 'react';
import { 
  PlusCircle, 
  Receipt, 
  Calculator, 
  Check, 
  X, 
  Scissors, 
  Sparkles, 
  Truck, 
  ArrowLeft 
} from 'lucide-react';
import { storageService, parseCurrency, parseInteger } from '../../services/storageService';
import { googleSheetsService } from '../../services/googleSheetsService';

export default function InvoiceForm({ initialData, onSaveSuccess, onCancel }) {
  const config = storageService.getConfig();
  const nextInvoiceId = storageService.getNextInvoiceId();

  // Dynamic service categories & description templates loaded from Google Sheets
  const [descriptionTemplates, setDescriptionTemplates] = useState(() => storageService.getDescriptionTemplates());
  const [serviceCategories, setServiceCategories] = useState(() => storageService.getServiceCategories());

  const [id, setId] = useState(initialData?.id || nextInvoiceId);
  const [date, setDate] = useState(initialData?.date || new Date().toISOString().split('T')[0]);
  const [customer, setCustomer] = useState(initialData?.customer || '');
  const [customerPhone, setCustomerPhone] = useState(initialData?.customerPhone || '');
  const [customerAddress, setCustomerAddress] = useState(initialData?.customerAddress || '');
  const [serviceType, setServiceType] = useState(initialData?.serviceType || serviceCategories[0] || 'Machine Embroidery');
  const [description, setDescription] = useState(initialData?.description || '');
  const orderRef = initialData?.orderId || initialData?.orderRef || '';

  // Dynamic directory of customers loaded from Google Sheets
  const [rawCustomers, setRawCustomers] = useState(() => googleSheetsService.getCustomers());

  useEffect(() => {
    setRawCustomers(googleSheetsService.getCustomers());
    setDescriptionTemplates(storageService.getDescriptionTemplates());
    setServiceCategories(storageService.getServiceCategories());
    return storageService.subscribe(() => {
      setRawCustomers(googleSheetsService.getCustomers());
      setDescriptionTemplates(storageService.getDescriptionTemplates());
      setServiceCategories(storageService.getServiceCategories());
    });
  }, []);

  const customerMap = {};
  rawCustomers.forEach(c => {
    const cName = c.Name || c.name;
    if (cName) {
      customerMap[cName] = {
        name: cName,
        phone: c.Phone || c.phone || '',
        address: c.Address || c.address || ''
      };
    }
  });
  const allCustomerList = Object.values(customerMap);

  const isPredefined = allCustomerList.some(c => c.name.toLowerCase() === (initialData?.customer || customer).toLowerCase());
  const [isCustomCustomer, setIsCustomCustomer] = useState(!isPredefined && !!(initialData?.customer || customer));

  const handleCustomerSelect = (e) => {
    const val = e.target.value;
    if (val === '__custom__') {
      setIsCustomCustomer(true);
      setCustomer('');
    } else if (val) {
      setIsCustomCustomer(false);
      setCustomer(val);
      const match = customerMap[val];
      if (match) {
        if (match.phone) setCustomerPhone(match.phone);
        if (match.address) setCustomerAddress(match.address);
      }
    } else {
      setIsCustomCustomer(false);
      setCustomer('');
    }
  };
  
  const [totalStitches, setTotalStitches] = useState(
    initialData?.totalStitches !== undefined ? initialData.totalStitches : 65000
  );
  const [laborMinutes, setLaborMinutes] = useState(() => {
    if (initialData?.laborMinutes !== undefined && initialData?.laborMinutes !== null && initialData?.laborMinutes !== '') {
      return parseInteger(initialData.laborMinutes);
    }
    const hrs = initialData?.laborHours !== undefined ? initialData.laborHours : initialData?.laborHrs;
    if (hrs !== undefined && hrs !== null && hrs !== '') {
      return Math.round(parseCurrency(hrs) * 60);
    }
    return 60;
  });
  const resolveInitialImage = () => {
    if (initialData?.imageUrl) return initialData.imageUrl;
    if (initialData?.['Image URL']) return initialData['Image URL'];
    if (initialData?.image_url) return initialData.image_url;
    const ordId = initialData?.orderId || initialData?.orderRef;
    if (ordId) {
      const linked = storageService.getOrderById(ordId);
      if (linked) return linked.imageUrl || linked['Image URL'] || linked.image_url || '';
    }
    return '';
  };
  const [imageUrl, setImageUrl] = useState(resolveInitialImage);
  const [marginPercent, setMarginPercent] = useState(
    initialData?.marginPercent !== undefined ? initialData.marginPercent : 25
  );
  const [courier, setCourier] = useState(initialData?.courier !== undefined ? initialData.courier : 0);
  const [status, setStatus] = useState(initialData?.status || 'Paid');

  // Rates
  const ratePer1000 = parseCurrency(config.stitch_rate_per_1000) || 8;
  const hourlyRate = parseCurrency(config.hourly_labor_rate) || 100;
  const gstRate = parseCurrency(config.gst_rate_percent) || 18;

  // Auto-zero stitches if Design Making
  useEffect(() => {
    if (serviceType === 'Machine Embroidery Design Making') {
      setTotalStitches(0);
    }
  }, [serviceType]);

  // Live Math calculations
  const effectiveStitches = serviceType === 'Machine Embroidery' ? parseInteger(totalStitches) : 0;
  const stitchCost = (effectiveStitches / 1000) * ratePer1000;
  const laborCost = (parseCurrency(laborMinutes) / 60.0) * hourlyRate;
  const baseCost = stitchCost + laborCost;
  const marginMultiplier = 1 + (parseCurrency(marginPercent) / 100);
  const netPrice = Number((baseCost * marginMultiplier).toFixed(2));
  const gst = Number((netPrice * (gstRate / 100)).toFixed(2));
  const activeCourier = parseCurrency(courier);
  const grossTotal = Number((netPrice + gst + activeCourier).toFixed(2));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!customer.trim()) {
      alert('Please enter a Customer or Boutique Name.');
      return;
    }

    const effectiveLaborMins = parseInteger(laborMinutes) || 0;
    const effectiveLaborHrs = Number((effectiveLaborMins / 60.0).toFixed(2));

    const saleRecord = {
      id,
      date,
      customer: customer.trim(),
      customerPhone: customerPhone.trim(),
      customerAddress: customerAddress.trim(),
      serviceType,
      description: description.trim() || `${serviceType} Order`,
      totalStitches: effectiveStitches,
      laborMinutes: effectiveLaborMins,
      laborHours: effectiveLaborHrs,
      marginPercent: parseCurrency(marginPercent),
      netPrice,
      gst,
      courier: activeCourier,
      grossTotal,
      status,
      paymentDate: status === 'Paid' ? date : null,
      orderRef: orderRef || null,
      imageUrl: imageUrl || ''
    };

    // Save to local storage
    const saved = storageService.addSale(saleRecord);

    // Sync to Google Sheet in background if configured
    googleSheetsService.appendSaleToSheet(saved).catch(err => {
      console.warn('Google Sheet background append error:', err);
    });

    // If linked to an AI Order and status is Paid, update the order in Google Sheets
    if (orderRef && status === 'Paid') {
      googleSheetsService.updateOrderStatus(orderRef, 'Complete').catch(err => {
        console.warn('Google Sheet order status sync error:', err);
      });
    }

    // Sync new customer to Google Sheet Customers tab
    if (isCustomCustomer || !allCustomerList.some(c => c.name.toLowerCase() === customer.trim().toLowerCase())) {
      googleSheetsService.appendCustomerToSheet({
        name: customer.trim(),
        phone: customerPhone.trim(),
        address: customerAddress.trim()
      }).catch(err => {
        console.warn('Google Sheet customer sync error:', err);
      });
    }

    onSaveSuccess(saved);
  };

  return (
    <div style={{ maxWidth: '840px', margin: '0 auto' }}>
      <div className="glass-panel" style={{ padding: '28px' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '18px',
          marginBottom: '24px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              padding: '8px',
              borderRadius: '12px',
              background: 'rgba(245, 158, 11, 0.15)',
              color: 'var(--accent-gold)'
            }}>
              <Receipt size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.4rem' }}>Generate New Sales Invoice</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Appends automatically to Sales_Ledger in Google Sheets.
              </p>
            </div>
          </div>

          <button className="btn btn-secondary" onClick={onCancel} style={{ padding: '6px 12px' }}>
            <ArrowLeft size={16} />
            <span>Cancel</span>
          </button>
        </div>

        {/* Linked AI Order Banner */}
        {orderRef && (
          <div style={{
            marginBottom: '20px',
            padding: '12px 18px',
            background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(15, 23, 42, 0.5) 100%)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            fontSize: '0.86rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={18} style={{ color: 'var(--accent-gold)' }} />
              <span>
                Generated from AI Order: <strong style={{ color: '#fbbf24' }}>{orderRef}</strong>
              </span>
            </div>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              Marking Paid will automatically update Google Sheet to "Complete"
            </span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Top Row: Invoice ID, Date, Status */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label">INVOICE NUMBER</label>
              <input
                type="text"
                className="input-field"
                value={id}
                onChange={(e) => setId(e.target.value)}
                required
              />
            </div>
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label">INVOICE DATE</label>
              <input
                type="date"
                className="input-field"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label">PAYMENT STATUS</label>
              <select
                className="input-field"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="Paid">Paid (Settled)</option>
                <option value="Pending">Pending (Unpaid)</option>
              </select>
            </div>
          </div>

          {/* Customer Details Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label">CUSTOMER / BOUTIQUE NAME *</label>
              <select
                className="input-field"
                style={{ marginBottom: isCustomCustomer ? '8px' : '0' }}
                value={isCustomCustomer ? '__custom__' : (customer || '')}
                onChange={handleCustomerSelect}
              >
                <option value="">-- Select Customer / Boutique --</option>
                <optgroup label="Saved Customers & Boutiques">
                  {allCustomerList.map(c => (
                    <option key={c.name} value={c.name}>{c.name}</option>
                  ))}
                </optgroup>
                <option value="__custom__">+ Enter New Customer...</option>
              </select>

              {isCustomCustomer && (
                <input
                  type="text"
                  className="input-field"
                  placeholder="Enter customer or boutique name"
                  value={customer}
                  onChange={(e) => setCustomer(e.target.value)}
                  required
                />
              )}
            </div>
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label">CONTACT PHONE / WHATSAPP</label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. +91 94471 23456"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
              />
            </div>
          </div>

          {/* Service Category Selection */}
          <div className="input-group" style={{ marginBottom: '20px' }}>
            <label className="input-label">SERVICE CATEGORY</label>
            <select
              className="input-field"
              value={serviceType}
              onChange={(e) => setServiceType(e.target.value)}
            >
              {serviceCategories.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Description with Cascading Template Filter */}
          {(() => {
            const filteredTemplates = descriptionTemplates.filter(t => 
              (t.serviceCategory || '').trim().toLowerCase() === (serviceType || '').trim().toLowerCase()
            );
            const displayTemplates = filteredTemplates.length > 0 ? filteredTemplates : descriptionTemplates;

            return (
              <div className="input-group" style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                  <label className="input-label" style={{ margin: 0 }}>ORDER / GARMENT DESCRIPTION</label>
                  <select
                    className="input-field"
                    style={{ width: 'auto', padding: '3px 8px', fontSize: '0.75rem', maxWidth: '380px' }}
                    onChange={(e) => {
                      if (e.target.value) {
                        const selectedTpl = displayTemplates.find(t => (t.id || t.description) === e.target.value);
                        if (selectedTpl) {
                          setDescription(selectedTpl.description);
                          if (selectedTpl.stitchCount > 0) {
                            setTotalStitches(selectedTpl.stitchCount);
                          }
                          if (selectedTpl.laborMinutes > 0) {
                            setLaborMinutes(selectedTpl.laborMinutes);
                          }
                        }
                        e.target.value = '';
                      }
                    }}
                  >
                    <option value="">
                      {filteredTemplates.length > 0
                        ? `-- ${serviceType} Templates (${filteredTemplates.length}) --`
                        : '-- Choose Description Template --'}
                    </option>
                    {displayTemplates.map((t, idx) => (
                      <option key={t.id || idx} value={t.id || t.description}>
                        {t.name ? `${t.name}: ${t.description}` : t.description}
                        {t.stitchCount ? ` (${t.stitchCount.toLocaleString()} st)` : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <textarea
                  className="input-field"
                  rows={2}
                  placeholder="e.g. Zari Floral Blouse Yoke Embroidery with Cording"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            );
          })()}

          {/* Order Design Reference Image Preview with Placeholder Fallback */}
          {(() => {
            const hasReal = Boolean(imageUrl);
            const displaySrc = hasReal
              ? (imageUrl.startsWith('http') ? `/api/media/proxy?url=${encodeURIComponent(imageUrl)}` : imageUrl)
              : '/placeholder-design.svg';

            return (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                padding: '14px 18px',
                background: hasReal ? 'rgba(245, 158, 11, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                border: hasReal ? '1px solid rgba(245, 158, 11, 0.25)' : '1px dashed rgba(148, 163, 184, 0.25)',
                borderRadius: 'var(--radius-md)',
                marginBottom: '20px'
              }}>
                <img
                  src={displaySrc}
                  alt="Order Design Reference"
                  style={{
                    width: '64px',
                    height: '64px',
                    objectFit: 'cover',
                    background: '#0f172a',
                    borderRadius: '8px',
                    border: hasReal ? '1.5px solid rgba(245, 158, 11, 0.6)' : '1px dashed rgba(148, 163, 184, 0.4)',
                    padding: '2px',
                    flexShrink: 0
                  }}
                  onError={(e) => {
                    if (e.target.src !== window.location.origin + '/placeholder-design.svg') {
                      e.target.src = '/placeholder-design.svg';
                    }
                  }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: hasReal ? 'var(--accent-gold)' : 'var(--text-secondary)' }}>
                    {hasReal ? 'Attached Order Design Artwork' : 'Standard Embroidery Artwork (Placeholder)'}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {hasReal
                      ? 'This artwork reference is linked to this order and will appear on the final invoice & share card.'
                      : 'No custom photo attached to this order. The standard CJS Designs artwork will appear on the invoice & WhatsApp share card.'}
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Internal Metrics & Cost Inputs */}
          <div style={{
            background: 'rgba(9, 13, 22, 0.6)',
            borderRadius: 'var(--radius-md)',
            padding: '18px',
            border: '1px solid var(--border-subtle)',
            marginBottom: '24px'
          }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '12px' }}>
              Cost Engine Parameters (Internal Metrics Only)
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px' }}>
              {serviceType === 'Machine Embroidery' ? (
                <div className="input-group" style={{ margin: 0 }}>
                  <label className="input-label">STITCH COUNT</label>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    className="input-field"
                    value={totalStitches}
                    onChange={(e) => setTotalStitches(e.target.value)}
                  />
                </div>
              ) : (
                <div className="input-group" style={{ margin: 0 }}>
                  <label className="input-label">STITCH COUNT</label>
                  <input
                    type="text"
                    disabled
                    className="input-field"
                    value="0 (Digitizing)"
                    style={{ opacity: 0.6 }}
                  />
                </div>
              )}

              <div className="input-group" style={{ margin: 0 }}>
                <label className="input-label">LABOR (MINUTES)</label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  className="input-field"
                  value={laborMinutes}
                  onChange={(e) => setLaborMinutes(e.target.value)}
                />
              </div>

              <div className="input-group" style={{ margin: 0 }}>
                <label className="input-label">MARGIN %</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="5"
                  className="input-field"
                  value={marginPercent}
                  onChange={(e) => setMarginPercent(e.target.value)}
                />
              </div>

              <div className="input-group" style={{ margin: 0 }}>
                <label className="input-label">COURIER (₹)</label>
                <input
                  type="number"
                  min="0"
                  step="10"
                  className="input-field"
                  value={courier}
                  onChange={(e) => setCourier(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Live Billing Totals Box */}
          <div className="glass-panel glass-panel-gold" style={{ padding: '20px', marginBottom: '24px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', textAlign: 'center' }}>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>BASE COST</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-secondary)' }}>₹{baseCost.toFixed(2)}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>SELLING PRICE (PRE-TAX)</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff' }}>₹{netPrice.toFixed(2)}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>GST ({gstRate}%)</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fbbf24' }}>₹{gst.toFixed(2)}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>FINAL INVOICE TOTAL</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fbbf24' }}>₹{grossTotal.toFixed(2)}</div>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" style={{ padding: '10px 24px' }}>
              <PlusCircle size={18} />
              <span>Save & View Invoice</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
