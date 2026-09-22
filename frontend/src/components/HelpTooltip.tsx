// Componente de tooltip de ajuda para XAU AI PRO
// Help tooltip component

import React from 'react';

interface HelpTooltipProps {
  text: string;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

export function HelpTooltip({ 
  text, 
  children, 
  position = 'top',
  className = '' 
}: HelpTooltipProps) {
  const positionStyle = {
    top: 'bottom: 100%; left: 50%; transform: translateX(-50%);',
    bottom: 'top: 100%; left: 50%; transform: translateX(-50%);',
    left: 'right: 100%; top: 50%; transform: translateY(-50%);',
    right: 'left: 100%; top: 50%; transform: translateY(-50%);',
  }[position];

  return (
    <span className={`help-tooltip ${className}`}>
      {children}
      <span 
        className="help-tooltip-icon" 
        style={{ position: 'relative' }}
      >
        ?
        <span 
          className="help-tooltip-text"
          style={{
            position: 'absolute',
            [position === 'top' || position === 'bottom' ? 'left' : 'top']: '50%',
            transform: positionStyle.split(';')[1],
            display: 'none',
          }}
        >
          {text}
        </span>
      </span>
      <style>{`
        .help-tooltip {
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .help-tooltip-icon {
          cursor: help;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: var(--panel2);
          color: var(--muted);
          font-size: 10px;
          font-weight: bold;
          border: 1px solid var(--border);
          position: relative;
        }
        .help-tooltip-icon:hover .help-tooltip-text {
          display: block;
        }
        .help-tooltip-text {
          position: absolute;
          z-index: 1000;
          background: var(--panel);
          color: var(--text);
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 12px;
          line-height: 1.4;
          white-space: normal;
          width: max-content;
          max-width: 280px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          border: 1px solid var(--border);
        }
        .help-tooltip-icon:hover .help-tooltip-text {
          display: block;
        }
        .help-tooltip-icon .help-tooltip-text::after {
          content: '';
          position: absolute;
          ${position === 'top' ? 'bottom: -6px; top: auto; left: 50%; margin-left: -6px; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid var(--border);' : ''}
          ${position === 'bottom' ? 'top: -6px; bottom: auto; left: 50%; margin-left: -6px; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 6px solid var(--border);' : ''}
        }
      `}</style>
    </span>
  );
}

export default HelpTooltip;
