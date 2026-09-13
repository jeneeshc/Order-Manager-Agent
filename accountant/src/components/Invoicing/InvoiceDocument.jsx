import React from 'react';
import { Printer, ArrowLeft, Download, Share2, CheckCircle2, ShieldAlert } from 'lucide-react';
import { storageService, parseCurrency } from '../../services/storageService';

export default function InvoiceDocument({ invoice, onBack, onMarkPaid }) {
  const config = storageService.getConfig();

  if (!invoice) {
    return (
      <div className="glass-panel" style={{ padding: '30px', textAlign: 'center' }}>
        <p>No invoice selected.</p>
        <button className="btn btn-secondary" onClick={onBack} style={{ marginTop: '12px' }}>
          Back to Invoices
        </button>
      </div>
    );
  }

  const getCustomerPhone = () => {
    if (invoice.customerPhone) return invoice.customerPhone;
    const customers = storageService.getCustomers();
    const match = customers.find(c =>
      String(c.name).trim().toLowerCase() === String(invoice.customer).trim().toLowerCase() ||
      String(c.id).trim().toLowerCase() === String(invoice.customer).trim().toLowerCase()
    );
    return match?.phone || '';
  };

  const openWhatsAppLink = (cleanPhone, message) => {
    const encodedText = encodeURIComponent(message);
    const waUrl = cleanPhone
      ? `https://wa.me/${cleanPhone}?text=${encodedText}`
      : `https://api.whatsapp.com/send?text=${encodedText}`;
    window.open(waUrl, '_blank', 'noopener,noreferrer');
  };

  const handleShare = async () => {
    const rawPhone = getCustomerPhone();
    let cleanPhone = rawPhone.replace(/[^0-9]/g, '');
    if (cleanPhone.length === 10) {
      cleanPhone = '91' + cleanPhone;
    }

    const studioName = config.studio_name || 'CJS Designs';
    const totalFormatted = `₹${parseCurrency(invoice.grossTotal).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const message = [
      `*INVOICE: #${invoice.id}*`,
      `*${studioName}*`,
      `---------------------------------`,
      `Dear ${invoice.customer || 'Customer'},`,
      `Thank you for choosing ${studioName}. Here are your invoice details:`,
      ``,
      `📅 *Date:* ${invoice.date}`,
      `🧵 *Service:* ${invoice.serviceType || 'Embroidery Work'}`,
      `📝 *Description:* ${invoice.description || 'Custom embroidery craft and thread work'}`,
      `💰 *Total Amount:* ${totalFormatted}`,
      `📌 *Status:* ${invoice.status || 'Pending'}`,
      ``,
      `Please let us know if you need any further assistance.`,
      `---------------------------------`,
      `*${studioName}* | Phone: ${config.studio_phone || '+91 8289897413'}`
    ].join('\n');

    // On mobile devices and supported browsers, invoke the native OS Share Sheet (WhatsApp, Email, Bluetooth, Quick Share, etc.)
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Invoice #${invoice.id} - ${studioName}`,
          text: message
        });
        return;
      } catch (err) {
        if (err.name === 'AbortError') return;
      }
    }

    // Fallback if navigator.share is unavailable (e.g. desktop browser)
    openWhatsAppLink(cleanPhone, message);
  };

  const handlePrint = () => {
    window.print();
  };

  const gstRate = parseFloat(config.gst_rate_percent) || 18;
  const isPaid = invoice.status === 'Paid';

  // Resolve design reference image from invoice, linked order, or description regex
  const orderImage = invoice.imageUrl ||
    (invoice.orderRef ? storageService.getOrderById(invoice.orderRef)?.imageUrl : null) ||
    (invoice.orderId ? storageService.getOrderById(invoice.orderId)?.imageUrl : null) ||
    (() => {
      const m = (invoice.description || '').match(/CJS-[A-Z0-9]+/i);
      return m ? storageService.getOrderById(m[0])?.imageUrl : null;
    })() || '';

  return (
    <div style={{ maxWidth: '850px', margin: '0 auto' }}>
      {/* Top Action Toolbar (Hidden during Print) */}
      <div className="no-print" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '20px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={16} />
          <span>Back to Invoices</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {!isPaid && onMarkPaid && (
            <button className="btn btn-emerald" onClick={() => onMarkPaid(invoice.id)}>
              <CheckCircle2 size={16} />
              <span>Mark as Paid</span>
            </button>
          )}
          
          {/* Native System Share Button (WhatsApp, Email, Bluetooth, etc.) */}
          <button
            type="button"
            className="btn btn-secondary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              fontWeight: 600,
              borderColor: 'rgba(99, 102, 241, 0.4)',
              background: 'rgba(99, 102, 241, 0.12)',
              color: '#a5b4fc'
            }}
            onClick={handleShare}
            title="Share invoice via WhatsApp, Email, Bluetooth, etc."
          >
            <Share2 size={16} />
            <span>Share</span>
          </button>

          <button className="btn btn-primary" onClick={handlePrint}>
            <Printer size={16} />
            <span>Print / Save as PDF</span>
          </button>
        </div>
      </div>

      {/* Confidentiality Notice Alert (Screen only) */}
      <div className="no-print" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '10px 16px',
        borderRadius: 'var(--radius-md)',
        background: 'rgba(16, 185, 129, 0.1)',
        border: '1px solid rgba(16, 185, 129, 0.25)',
        color: '#34d399',
        fontSize: '0.82rem',
        marginBottom: '20px'
      }}>
        <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
        <span>
          <strong>Confidentiality Verified:</strong> Internal metrics (Stitches: {invoice.totalStitches?.toLocaleString() || 0}, Labor: {invoice.laborMinutes ? `${invoice.laborMinutes} mins` : `${invoice.laborHours || 0} hrs`}, Margin: {invoice.marginPercent || 0}%) are <strong>completely hidden</strong> on this customer invoice.
        </span>
      </div>

      {/* The Printable Invoice Document Container */}
      <div className="invoice-printable" style={{
        background: '#ffffff',
        color: '#0f172a',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.45)',
        padding: '48px',
        border: '1px solid #e2e8f0',
        fontFamily: "'Plus Jakarta Sans', sans-serif"
      }}>
        {/* Header Branding */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          borderBottom: '2px solid #f1f5f9',
          paddingBottom: '28px',
          marginBottom: '28px'
        }}>
          {/* Logo & Business Info */}
          <div>
            <div style={{ marginBottom: '10px' }}>
              <img src="/siteLogo.png" alt="CJS Designs" style={{ height: '48px', width: 'auto' }} />
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', color: '#15803d', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                {config.tagline || 'Crafting fashion on fabric'}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>
                {config.studio_address}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                Phone: {config.studio_phone} | Email: {config.studio_email}
              </div>
              {config.studio_gstin && (
                <div style={{ fontSize: '0.8rem', color: '#0f172a', fontWeight: 600, marginTop: '2px' }}>
                  GSTIN: {config.studio_gstin}
                </div>
              )}
            </div>
          </div>

          {/* Invoice Badge & Meta */}
          <div style={{ textAlign: 'right' }}>
            <div style={{
              display: 'inline-block',
              padding: '4px 14px',
              borderRadius: '6px',
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              fontFamily: "'Outfit', sans-serif",
              fontSize: '1rem',
              fontWeight: 800,
              color: '#0f172a',
              marginBottom: '10px'
            }}>
              INVOICE
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', fontFamily: "'Outfit', sans-serif" }}>
              #{invoice.id}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '4px' }}>
              Date: <strong style={{ color: '#0f172a' }}>{invoice.date}</strong>
            </div>
            <div style={{ marginTop: '6px' }}>
              <span style={{
                display: 'inline-block',
                padding: '3px 10px',
                borderRadius: '999px',
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                background: isPaid ? '#dcfce7' : '#fef3c7',
                color: isPaid ? '#166534' : '#92400e',
                border: isPaid ? '1px solid #bbf7d0' : '1px solid #fde68a'
              }}>
                {isPaid ? '● PAID' : '● PAYMENT DUE'}
              </span>
            </div>
          </div>
        </div>

        {/* Bill To & Order Summary */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '24px',
          marginBottom: '32px',
          background: '#f8fafc',
          padding: '20px',
          borderRadius: '12px',
          border: '1px solid #e2e8f0'
        }}>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
              BILLED TO:
            </div>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
              {invoice.customer}
            </div>
            {invoice.customerPhone && (
              <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '2px' }}>
                Contact: {invoice.customerPhone}
              </div>
            )}
            {invoice.customerAddress && (
              <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '2px' }}>
                {invoice.customerAddress}
              </div>
            )}
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
              SERVICE CATEGORY:
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>
              {invoice.serviceType}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '4px' }}>
              Status: <span style={{ fontWeight: 600, color: isPaid ? '#16a34a' : '#ea580c' }}>{invoice.status}</span>
              {invoice.paymentDate && ` (${invoice.paymentDate})`}
            </div>
          </div>
        </div>

        {/* Customer-Facing Line Items Table */}
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          marginBottom: '32px'
        }}>
          <thead>
            <tr style={{ background: '#f1f5f9', borderBottom: '2px solid #cbd5e1' }}>
              <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.82rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>#</th>
              <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.82rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Service Description</th>
              <th style={{ textAlign: 'center', padding: '12px 16px', fontSize: '0.82rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Qty</th>
              <th style={{ textAlign: 'right', padding: '12px 16px', fontSize: '0.82rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '16px', verticalAlign: 'top', color: '#64748b', fontWeight: 600 }}>01</td>
              <td style={{ padding: '16px', verticalAlign: 'top' }}>
                <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                  {orderImage && (
                    <div style={{ flexShrink: 0, textAlign: 'center' }}>
                      <a href={orderImage} target="_blank" rel="noopener noreferrer" title="Click to view full size design artwork">
                        <img 
                          src={orderImage} 
                          alt="Design Reference" 
                          style={{ 
                            width: '84px', 
                            height: '84px', 
                            objectFit: 'contain', 
                            background: '#f8fafc',
                            borderRadius: '8px', 
                            border: '1px solid #cbd5e1',
                            padding: '2px',
                            display: 'block'
                          }} 
                        />
                      </a>
                      <div style={{ fontSize: '0.68rem', color: '#64748b', marginTop: '4px', fontWeight: 600 }}>
                        Design Ref
                      </div>
                    </div>
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: '#0f172a', fontSize: '0.98rem' }}>
                      {invoice.serviceType}
                    </div>
                    <div style={{ fontSize: '0.88rem', color: '#475569', marginTop: '4px', lineHeight: 1.4 }}>
                      {invoice.description || 'Custom embroidery craft and high-precision thread work.'}
                    </div>
                  </div>
                </div>
              </td>
              <td style={{ textAlign: 'center', padding: '16px', verticalAlign: 'top', fontWeight: 600, color: '#0f172a' }}>
                1
              </td>
              <td style={{ textAlign: 'right', padding: '16px', verticalAlign: 'top', fontWeight: 700, color: '#0f172a', fontSize: '1rem' }}>
                ₹{parseCurrency(invoice.netPrice).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </td>
            </tr>
          </tbody>
        </table>

        {/* Totals Block */}
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          marginBottom: '32px'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '380px',
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '10px',
            padding: '18px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: '0.92rem', color: '#475569' }}>
              <span>Subtotal:</span>
              <span style={{ fontWeight: 600, color: '#0f172a' }}>
                ₹{parseCurrency(invoice.netPrice).toFixed(2)}
              </span>
            </div>

            {parseCurrency(invoice.courier) > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: '0.92rem', color: '#475569' }}>
                <span>Courier / Delivery:</span>
                <span style={{ fontWeight: 600, color: '#0f172a' }}>
                  ₹{parseCurrency(invoice.courier).toFixed(2)}
                </span>
              </div>
            )}

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '12px 0 4px',
              borderTop: '2px solid #0f172a',
              marginTop: '8px',
              fontFamily: "'Outfit', sans-serif"
            }}>
              <span style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>
                Total Amount:
              </span>
              <span style={{ fontSize: '1.35rem', fontWeight: 800, color: '#b45309' }}>
                ₹{parseCurrency(invoice.grossTotal).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>

        {/* Footer Terms & Sign */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          borderTop: '1px solid #e2e8f0',
          paddingTop: '24px',
          marginTop: '40px'
        }}>
          <div style={{ fontSize: '0.78rem', color: '#64748b', maxWidth: '380px' }}>
            <p><strong>Terms & Conditions:</strong></p>
            <p>1. Payment is expected within 7 days of invoice issue.</p>
            <p>2. Customized embroidery designs & digitized EMB/DST files remain property of CJS Designs until full settlement.</p>
          </div>

          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontFamily: "'Outfit', sans-serif",
              fontWeight: 700,
              fontSize: '1rem',
              color: '#0f172a',
              marginBottom: '36px'
            }}>
              For {config.studio_name || 'CJS Designs'}
            </div>
            <div style={{ borderTop: '1px dashed #94a3b8', width: '160px', paddingTop: '4px', fontSize: '0.75rem', color: '#64748b' }}>
              Authorized Signatory
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
