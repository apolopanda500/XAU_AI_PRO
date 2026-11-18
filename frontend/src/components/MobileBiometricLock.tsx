import React, { useState } from 'react';

interface MobileBiometricLockProps {
  onUnlocked: () => void;
}

export const MobileBiometricLock: React.FC<MobileBiometricLockProps> = ({ onUnlocked }) => {
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleBiometricAuth = async () => {
    setBusy(true);
    setError('');
    try {
      if (typeof window !== 'undefined' && window.PublicKeyCredential) {
        const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        if (available) {
          const challenge = new Uint8Array(32);
          crypto.getRandomValues(challenge);
          await navigator.credentials.get({
            publicKey: {
              challenge,
              timeout: 30000,
              userVerification: 'required',
              rpId: window.location.hostname || undefined,
              user: {
                id: new Uint8Array(16),
                name: 'xau-ai-pro',
                displayName: 'XAU AI PRO',
              },
              pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
            } as any,
          });
          onUnlocked();
          return;
        }
      }
      setError('Biometria não configurada neste aparelho. Use o PIN rápido.');
    } catch {
      setError('Autenticação biométrica cancelada ou indisponível. Use o PIN.');
    } finally {
      setBusy(false);
    }
  };

  const handlePinSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const savedPin = localStorage.getItem('xau_mobile_pin') || '2026';
    if (pin === savedPin) {
      onUnlocked();
    } else {
      setError('PIN incorreto.');
      setPin('');
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: '#070b14',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        color: '#f8fafc',
      }}
    >
      <div style={{ maxWidth: '340px', width: '100%', textAlign: 'center' }}>
        <div style={{ fontSize: '32px', marginBottom: '8px' }}>🛡️</div>
        <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#f59e0b', margin: 0 }}>XAU AI PRO — COFRE MÓVEL</h2>
        <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '20px' }}>
          Confirme sua identidade para acessar a telemetria e o risco da conta
        </p>

        <button
          type="button"
          disabled={busy}
          onClick={() => void handleBiometricAuth()}
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: '10px',
            background: '#f59e0b',
            color: '#000',
            fontWeight: 800,
            border: 'none',
            marginBottom: '16px',
            cursor: busy ? 'default' : 'pointer',
          }}
        >
          {busy ? 'Verificando...' : 'Desbloquear com Digital / Face'}
        </button>

        <form onSubmit={handlePinSubmit} style={{ display: 'flex', gap: '8px' }}>
          <input
            type="password"
            inputMode="numeric"
            maxLength={6}
            placeholder="PIN de acesso"
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              background: '#0f172a',
              border: '1px solid #334155',
              color: '#fff',
              textAlign: 'center',
              letterSpacing: '4px',
            }}
          />
          <button
            type="submit"
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              background: '#1e293b',
              color: '#38bdf8',
              border: '1px solid #334155',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Entrar
          </button>
        </form>

        {error && <p style={{ color: '#f87171', fontSize: '12px', marginTop: '12px' }}>{error}</p>}
      </div>
    </div>
  );
};

export default MobileBiometricLock;
