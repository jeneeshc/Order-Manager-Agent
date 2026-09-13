import React, { useState, useEffect } from 'react';
import { Lock, Unlock, ShieldCheck, KeyRound, Sparkles } from 'lucide-react';
import { storageService } from '../../services/storageService';

export default function PinLockScreen({ onUnlock }) {
  const [pin, setPin] = useState('');
  const [isShaking, setIsShaking] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showChangePin, setShowChangePin] = useState(false);
  const [currentPinInput, setCurrentPinInput] = useState('');
  const [newPinInput, setNewPinInput] = useState('');
  const [confirmPinInput, setConfirmPinInput] = useState('');
  const [changeSuccess, setChangeSuccess] = useState('');

  const handleKeyPress = (num) => {
    setPin((prev) => {
      if (prev.length >= 4) return prev;
      const nextPin = prev + num;
      if (nextPin.length === 4) {
        setTimeout(() => verify(nextPin), 40);
      }
      return nextPin;
    });
  };


  const handleBackspace = () => {
    setPin(prev => prev.slice(0, -1));
    setErrorMessage('');
  };

  const handleClear = () => {
    setPin('');
    setErrorMessage('');
  };

  const verify = (codeToTest) => {
    if (storageService.verifyPin(codeToTest)) {
      setErrorMessage('');
      onUnlock();
    } else {
      setIsShaking(true);
      setErrorMessage('Incorrect PIN. Please try again.');
      setTimeout(() => {
        setIsShaking(false);
        setPin('');
      }, 500);
    }
  };

  // Allow physical keyboard typing
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (showChangePin) return;
      if (e.key >= '0' && e.key <= '9') {
        handleKeyPress(e.key);
      } else if (e.key === 'Backspace') {
        handleBackspace();
      } else if (e.key === 'Escape') {
        handleClear();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pin, showChangePin]);

  const handleChangePinSubmit = (e) => {
    e.preventDefault();
    setChangeSuccess('');
    if (!storageService.verifyPin(currentPinInput)) {
      alert('Current PIN is incorrect.');
      return;
    }
    if (newPinInput.length !== 4 || !/^\d{4}$/.test(newPinInput)) {
      alert('New PIN must be exactly 4 numeric digits.');
      return;
    }
    if (newPinInput !== confirmPinInput) {
      alert('New PIN and Confirm PIN do not match.');
      return;
    }
    storageService.setPin(newPinInput);
    setChangeSuccess('PIN successfully updated!');
    setTimeout(() => {
      setShowChangePin(false);
      setCurrentPinInput('');
      setNewPinInput('');
      setConfirmPinInput('');
      setChangeSuccess('');
    }, 1200);
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at center, #111827 0%, #080c14 100%)',
      padding: '24px'
    }}>
      <div className={`glass-panel ${isShaking ? 'shake' : ''}`} style={{
        width: '100%',
        maxWidth: '380px',
        padding: '36px 28px',
        textAlign: 'center',
        border: '1px solid var(--border-gold)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7)'
      }}>
        {/* Brand Logo & Header */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{
            maxWidth: '220px',
            margin: '0 auto 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(255, 255, 255, 0.95)',
            padding: '10px 18px',
            borderRadius: '16px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)'
          }}>
            <img src="/siteLogo.png" alt="CJS Designs" style={{ maxWidth: '100%', height: 'auto' }} />
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
            Accounting & Management
          </p>
        </div>

        {/* PIN Indicators */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '16px',
          margin: '28px 0 16px'
        }}>
          {[0, 1, 2, 3].map((idx) => {
            const filled = pin.length > idx;
            return (
              <div
                key={idx}
                style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  background: filled
                    ? 'linear-gradient(135deg, var(--accent-gold) 0%, #d97706 100%)'
                    : 'rgba(255, 255, 255, 0.1)',
                  border: filled ? '2px solid #fbbf24' : '2px solid rgba(255, 255, 255, 0.2)',
                  boxShadow: filled ? '0 0 14px rgba(245, 158, 11, 0.6)' : 'none',
                  transform: filled ? 'scale(1.15)' : 'scale(1)',
                  transition: 'all 0.18s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
                }}
              />
            );
          })}
        </div>

        {/* Error / Status Text */}
        <div style={{ minHeight: '22px', marginBottom: '20px' }}>
          {errorMessage ? (
            <span style={{ fontSize: '0.82rem', color: 'var(--accent-rose)', fontWeight: 600 }}>
              {errorMessage}
            </span>
          ) : (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Enter your 4-digit PIN
            </span>
          )}
        </div>

        {/* Keypad Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '12px',
          maxWidth: '280px',
          margin: '0 auto 24px'
        }}>
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', '0', '⌫'].map((item) => {
            const isClear = item === 'C';
            const isBackspace = item === '⌫';
            const isNumber = !isClear && !isBackspace;

            return (
              <button
                key={item}
                type="button"
                onClick={() => {
                  if (isClear) handleClear();
                  else if (isBackspace) handleBackspace();
                  else handleKeyPress(item);
                }}
                style={{
                  height: '58px',
                  background: isNumber
                    ? 'rgba(255, 255, 255, 0.05)'
                    : 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '16px',
                  color: isClear ? 'var(--accent-rose)' : isBackspace ? 'var(--accent-gold)' : 'var(--text-primary)',
                  fontSize: isNumber ? '1.4rem' : '1rem',
                  fontFamily: isNumber ? 'var(--font-heading)' : 'var(--font-body)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.25)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = isNumber ? 'rgba(255, 255, 255, 0.05)' : 'rgba(255, 255, 255, 0.02)';
                  e.currentTarget.style.borderColor = 'var(--border-subtle)';
                }}
                onMouseDown={(e) => {
                  e.currentTarget.style.transform = 'scale(0.92)';
                }}
                onMouseUp={(e) => {
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                {item}
              </button>
            );
          })}
        </div>

        {/* Bottom Quick Links */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '0.8rem' }}>
          <button
            type="button"
            className="btn btn-ghost"
            style={{ fontSize: '0.78rem', padding: '4px 8px' }}
            onClick={() => setShowChangePin(true)}
          >
            <KeyRound size={14} />
            <span>Change PIN</span>
          </button>
        </div>
      </div>

      {/* Change PIN Modal */}
      {showChangePin && (
        <div className="modal-overlay" onClick={() => setShowChangePin(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <KeyRound size={20} style={{ color: 'var(--accent-gold)' }} />
                <h3>Update Security PIN</h3>
              </div>
              <button className="btn btn-ghost" onClick={() => setShowChangePin(false)}>✕</button>
            </div>
            <form onSubmit={handleChangePinSubmit}>
              <div className="modal-body">
                {changeSuccess && (
                  <div style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(16, 185, 129, 0.15)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    color: '#34d399',
                    marginBottom: '16px',
                    fontSize: '0.88rem'
                  }}>
                    {changeSuccess}
                  </div>
                )}
                <div className="input-group">
                  <label className="input-label">Current PIN</label>
                  <input
                    type="password"
                    maxLength={4}
                    className="input-field"
                    placeholder="Enter existing PIN"
                    value={currentPinInput}
                    onChange={(e) => setCurrentPinInput(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">New 4-Digit PIN</label>
                  <input
                    type="password"
                    maxLength={4}
                    className="input-field"
                    placeholder="e.g. 5678"
                    value={newPinInput}
                    onChange={(e) => setNewPinInput(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Confirm New PIN</label>
                  <input
                    type="password"
                    maxLength={4}
                    className="input-field"
                    placeholder="Re-enter new PIN"
                    value={confirmPinInput}
                    onChange={(e) => setConfirmPinInput(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowChangePin(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save New PIN
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
