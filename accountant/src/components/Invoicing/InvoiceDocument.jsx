import React, { useRef, useState } from 'react';
import { Printer, ArrowLeft, Download, Share2, CheckCircle2, ShieldAlert, Loader2 } from 'lucide-react';
import { storageService, parseCurrency } from '../../services/storageService';

export default function InvoiceDocument({ invoice, onBack, onMarkPaid }) {
  const config = storageService.getConfig();
  const shareCardRef = useRef(null);
  const [isSharing, setIsSharing] = useState(false);

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
    if (isSharing) return;
    setIsSharing(true);

    const rawPhone = getCustomerPhone();
    let cleanPhone = rawPhone.replace(/[^0-9]/g, '');
    if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone;

    const studioName = config.studio_name || 'CJS Designs';
    const totalFormatted = `₹${parseCurrency(invoice.grossTotal).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const textMessage = [
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

    // Try to share as an image card using html2canvas
    if (shareCardRef.current && navigator.share) {
      try {
        const html2canvas = (await import('html2canvas')).default;
        const canvas = await html2canvas(shareCardRef.current, {
          scale: 2,
          useCORS: true,
          allowTaint: false,
          backgroundColor: '#ffffff',
          logging: false
        });

        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png', 1.0));
        const imageFile = new File([blob], `invoice-${invoice.id}.png`, { type: 'image/png' });

        // Try sharing with image file
        if (navigator.canShare && navigator.canShare({ files: [imageFile] })) {
          await navigator.share({
            files: [imageFile],
            title: `Invoice #${invoice.id} - ${studioName}`,
            text: textMessage
          });
          setIsSharing(false);
          return;
        }

        // Fallback: share text only via native share sheet
        await navigator.share({
          title: `Invoice #${invoice.id} - ${studioName}`,
          text: textMessage
        });
        setIsSharing(false);
        return;
      } catch (err) {
        if (err.name === 'AbortError') { setIsSharing(false); return; }
        // If image share failed, fall through to WhatsApp link
      }
    } else if (navigator.share) {
      try {
        await navigator.share({ title: `Invoice #${invoice.id} - ${studioName}`, text: textMessage });
        setIsSharing(false);
        return;
      } catch (err) {
        if (err.name === 'AbortError') { setIsSharing(false); return; }
      }
    }

    // Desktop fallback: open WhatsApp with text
    openWhatsAppLink(cleanPhone, textMessage);
    setIsSharing(false);
  };

  const handlePrint = () => {
    window.print();
  };

  const gstRate = parseFloat(config.gst_rate_percent) || 18;
  const isPaid = invoice.status === 'Paid';

  // Resolve design reference image from invoice, linked order, or description regex
  const rawOrderImage = invoice.imageUrl ||
    invoice['Image URL'] ||
    invoice.image_url ||
    (invoice.orderRef ? (storageService.getOrderById(invoice.orderRef)?.imageUrl || storageService.getOrderById(invoice.orderRef)?.['Image URL'] || storageService.getOrderById(invoice.orderRef)?.image_url) : null) ||
    (invoice.orderId ? (storageService.getOrderById(invoice.orderId)?.imageUrl || storageService.getOrderById(invoice.orderId)?.['Image URL'] || storageService.getOrderById(invoice.orderId)?.image_url) : null) ||
    (() => {
      const m = (invoice.description || '').match(/CJS-[A-Z0-9]+/i);
      if (!m) return null;
      const linked = storageService.getOrderById(m[0]) || storageService.getOrderById(m[0].toUpperCase());
      return linked ? (linked.imageUrl || linked['Image URL'] || linked.image_url) : null;
    })() || '';

  const hasCustomImage = Boolean(rawOrderImage);
  const orderImage = hasCustomImage
    ? (rawOrderImage.startsWith('http') ? `/api/media/proxy?url=${encodeURIComponent(rawOrderImage)}` : rawOrderImage)
    : '/placeholder-design.svg';

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
          
          {/* Image Card Share Button */}
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
              color: '#a5b4fc',
              opacity: isSharing ? 0.7 : 1
            }}
            onClick={handleShare}
            disabled={isSharing}
            title="Share invoice card via WhatsApp, Email, etc."
          >
            {isSharing ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Share2 size={16} />}
            <span>{isSharing ? 'Preparing...' : 'Share'}</span>
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
                  {/* Design Artwork Reference (or Placeholder) */}
                  <div style={{ flexShrink: 0, textAlign: 'center' }}>
                    <a
                      href={hasCustomImage ? rawOrderImage : '#'}
                      target={hasCustomImage ? "_blank" : "_self"}
                      rel="noopener noreferrer"
                      onClick={(e) => { if (!hasCustomImage) e.preventDefault(); }}
                      title={hasCustomImage ? "Click to view full size design artwork" : "Standard CJS embroidery design reference"}
                    >
                      <img 
                        src={orderImage} 
                        alt="Design Reference" 
                        style={{ 
                          width: '84px', 
                          height: '84px', 
                          objectFit: 'cover', 
                          background: '#0f172a',
                          borderRadius: '8px', 
                          border: hasCustomImage ? '1.5px solid #f59e0b' : '1px dashed #cbd5e1',
                          padding: '2px',
                          display: 'block',
                          boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
                        }} 
                        onError={(e) => {
                          if (e.target.src !== window.location.origin + '/placeholder-design.svg') {
                            e.target.src = '/placeholder-design.svg';
                          }
                        }}
                      />
                    </a>
                    <div style={{ fontSize: '0.68rem', color: '#64748b', marginTop: '4px', fontWeight: 600 }}>
                      {hasCustomImage ? 'Design Ref' : 'Standard Ref'}
                    </div>
                  </div>
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

      {/* Hidden off-screen WhatsApp Share Card — captured by html2canvas */}
      <div
        ref={shareCardRef}
        style={{
          position: 'fixed',
          left: '-9999px',
          top: 0,
          width: '460px',
          background: '#ffffff',
          borderRadius: '16px',
          overflow: 'hidden',
          fontFamily: "'Outfit', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          color: '#0f172a',
          boxShadow: '0 12px 36px rgba(0,0,0,0.12)',
          border: '1px solid rgba(217, 119, 6, 0.25)'
        }}
      >
        {/* Top Gold & Emerald Gradient Accent Line */}
        <div style={{
          height: '5px',
          background: 'linear-gradient(90deg, #f59e0b 0%, #fbbf24 50%, #059669 100%)'
        }} />

        {/* Brand Header — Logo on left, Invoice pill on right */}
        <div style={{
          padding: '18px 22px 14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#ffffff',
          borderBottom: '1px solid #f1f5f9'
        }}>
          <div>
            <img
              src="/siteLogo.png"
              alt="CJS Designs"
              crossOrigin="anonymous"
              style={{ maxHeight: '46px', maxWidth: '180px', objectFit: 'contain', display: 'block' }}
              onError={(e) => {
                if (e.target.src !== window.location.origin + '/logo.svg') {
                  e.target.src = '/logo.svg';
                }
              }}
            />
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{
              display: 'inline-block',
              background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
              border: '1px solid #fcd34d',
              borderRadius: '20px',
              padding: '3px 12px',
              fontSize: '0.72rem',
              fontWeight: 800,
              color: '#92400e',
              letterSpacing: '0.08em'
            }}>
              INVOICE
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '3px', fontWeight: 600 }}>
              {invoice.date}
            </div>
          </div>
        </div>

        {/* Invoice Metadata Bar */}
        <div style={{
          background: '#f8fafc',
          padding: '8px 22px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #f1f5f9'
        }}>
          <div>
            <span style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', marginRight: '6px' }}>Invoice:</span>
            <span style={{ fontWeight: 800, fontSize: '0.92rem', color: '#b45309', fontFamily: 'monospace' }}>#{invoice.id}</span>
          </div>
          <span style={{
            display: 'inline-block',
            padding: '2px 10px',
            borderRadius: '12px',
            fontSize: '0.7rem',
            fontWeight: 800,
            letterSpacing: '0.05em',
            background: isPaid ? '#ecfdf5' : '#fffbeb',
            color: isPaid ? '#047857' : '#b45309',
            border: isPaid ? '1px solid #a7f3d0' : '1px solid #fde68a'
          }}>
            {isPaid ? '✓ PAID' : '● PAYMENT PENDING'}
          </span>
        </div>

        {/* Card Body */}
        <div style={{ padding: '16px 22px 18px' }}>
          {/* Bill To Customer Box */}
          <div style={{
            background: '#ffffff',
            borderRadius: '10px',
            padding: '10px 14px',
            marginBottom: '14px',
            border: '1px solid #e2e8f0',
            borderLeft: '4px solid #f59e0b'
          }}>
            <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700, marginBottom: '2px' }}>
              BILL TO
            </div>
            <div style={{ fontWeight: 800, fontSize: '1rem', color: '#0f172a' }}>
              {invoice.customer}
            </div>
            {getCustomerPhone() && (
              <div style={{ fontSize: '0.76rem', color: '#64748b', marginTop: '2px' }}>
                📞 {getCustomerPhone()}
              </div>
            )}
          </div>

          {/* Service + Design Image Row */}
          <div style={{
            display: 'flex',
            gap: '14px',
            alignItems: 'center',
            marginBottom: '16px',
            background: '#fafaf9',
            border: '1px solid #f0eee9',
            borderRadius: '12px',
            padding: '12px'
          }}>
            <img
              src={orderImage}
              alt="Design Artwork"
              crossOrigin="anonymous"
              style={{
                width: '88px',
                height: '88px',
                objectFit: 'cover',
                borderRadius: '10px',
                border: hasCustomImage ? '2px solid #f59e0b' : '1px dashed #cbd5e1',
                background: '#0f172a',
                flexShrink: 0,
                boxShadow: '0 3px 10px rgba(0,0,0,0.1)'
              }}
              onError={(e) => {
                if (e.target.src !== window.location.origin + '/placeholder-design.svg') {
                  e.target.src = '/placeholder-design.svg';
                }
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 800, fontSize: '0.98rem', color: '#0f172a', marginBottom: '3px' }}>
                {invoice.serviceType}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#57534e', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {(invoice.description || '').replace(/\s*\(AI Order:.*?\)/, '').trim() || 'Custom embroidery craft & precision thread work'}
              </div>
              {invoice.totalStitches > 0 && (
                <div style={{ marginTop: '6px' }}>
                  <span style={{ fontSize: '0.68rem', fontWeight: 700, background: '#ecfdf5', color: '#047857', padding: '1px 7px', borderRadius: '4px', border: '1px solid #a7f3d0' }}>
                    {invoice.totalStitches.toLocaleString()} Stitches
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Total Amount Highlight Banner */}
          <div style={{
            background: 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)',
            border: '1.5px solid #fcd34d',
            borderRadius: '12px',
            padding: '14px 18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 4px 14px rgba(217,119,6,0.1)'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#92400e', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                Total Amount
              </div>
              <div style={{ fontSize: '0.72rem', color: isPaid ? '#047857' : '#b45309', fontWeight: 700, marginTop: '2px' }}>
                {isPaid ? 'Payment Cleared' : 'Pending Payment'}
              </div>
            </div>
            <div style={{ fontWeight: 900, fontSize: '1.65rem', color: '#78350f', letterSpacing: '-0.02em' }}>
              ₹{parseCurrency(invoice.grossTotal).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
        </div>

        {/* Card Footer */}
        <div style={{
          background: '#f8fafc',
          borderTop: '1px solid #e2e8f0',
          padding: '11px 22px',
          textAlign: 'center',
          fontSize: '0.74rem',
          color: '#64748b',
          fontWeight: 500
        }}>
          <span>📞 {config.studio_phone || '+91 8289897413'}</span>
          <span style={{ margin: '0 8px', color: '#cbd5e1' }}>•</span>
          <span>New Kerala Nagar, Cochin, Kerala</span>
          <div style={{ fontSize: '0.68rem', color: '#b45309', fontWeight: 600, marginTop: '3px' }}>
            ✨ Thank you for choosing CJS Designs
          </div>
        </div>
      </div>
    </div>
  );
}
