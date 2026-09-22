// Botão com auto-click e refresh corrigidos
// Auto-click button with refresh fix

import { useState, useCallback, useRef, useEffect } from 'react';

interface AutoButtonProps {
  label: string;
  onClick: () => void | Promise<void>;
  autoRefresh?: boolean;
  refreshInterval?: number;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'ghost' | 'danger' | 'warn';
  icon?: string;
  helpText?: string;
  onResult?: (success: boolean, message: string) => void;
}

export default function AutoButton({
  label,
  onClick,
  autoRefresh = false,
  refreshInterval = 5000,
  disabled = false,
  loading = false,
  variant = 'primary',
  icon = '',
  helpText,
  onResult,
}: AutoButtonProps) {
  const [localLoading, setLocalLoading] = useState(false);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const onClickRef = useRef(onClick);
  const timerRef = useRef<number>();

  useEffect(() => {
    onClickRef.current = onClick;
  }, [onClick]);

  const handleClick = useCallback(async () => {
    if (disabled || localLoading) return;

    setLocalLoading(true);
    setResultMessage(null);

    try {
      await onClickRef.current();
      setResultMessage('✅ Executado!');
      onResult?.(true, 'Executado!');
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Erro';
      setResultMessage(`❌ ${message}`);
      onResult?.(false, message);
    } finally {
      setLocalLoading(false);
    }
  }, [disabled, localLoading, onClickRef, onResult]);

  // Auto-refresh com tratamento de erros
  useEffect(() => {
    if (!autoRefresh || disabled) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    // Executar imediatamente
    handleClick();

    timerRef.current = window.setInterval(() => {
      handleClick();
    }, refreshInterval);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [autoRefresh, disabled, refreshInterval, handleClick]);

  const variantClass = {
    primary: 'primary',
    ghost: 'ghost',
    danger: 'danger',
    warn: 'warn',
  }[variant];

  return (
    <div className={`auto-button-container ${variantClass}`}>
      <button
        className={`btn ${variantClass} ${localLoading ? 'loading' : ''}`}
        onClick={handleClick}
        disabled={disabled || localLoading}
      >
        {icon && <span className="btn-icon">{icon}</span>}
        {label}
        {localLoading && <span className="btn-loading">...</span>}
      </button>

      {resultMessage && (
        <div className={`auto-button-result ${resultMessage.startsWith('❌') ? 'error' : 'success'}`}>
          {resultMessage}
        </div>
      )}

      {helpText && (
        <div className="auto-button-help">
          <small>{helpText}</small>
        </div>
      )}

      {autoRefresh && (
        <div className="auto-button-indicator">
          <span className="indicator-dot" />
          <small>Auto</small>
        </div>
      )}

      <style>{`
        .auto-button-container {
          display: inline-flex;
          flex-direction: column;
          gap: 4px;
        }
        .auto-button-container .btn {
          min-width: 120px;
        }
        .auto-button-container .btn-loading {
          animation: dots 1.5s infinite;
        }
        @keyframes dots {
          0%, 20% { opacity: 0; }
          40% { opacity: 1; }
          100% { opacity: 1; }
        }
        .auto-button-result {
          font-size: 11px;
          min-height: 16px;
          transition: opacity 0.3s;
        }
        .auto-button-result.success {
          color: var(--ok);
        }
        .auto-button-result.error {
          color: var(--danger);
        }
        .auto-button-help {
          font-size: 10px;
          color: var(--muted);
          margin-top: 2px;
        }
        .auto-button-indicator {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 10px;
          color: var(--ok);
        }
        .auto-button-indicator .indicator-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--ok);
          animation: pulse 2s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
