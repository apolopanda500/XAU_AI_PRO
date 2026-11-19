// Secao retratil generica do app: botao Minimizar/Expandir no cabecalho,
// preferencia persistida em localStorage por `id` (e NAO global - um painel
// minimizado nao fecha todos).
//
// POR QUÊ
// ======
// A tela de Planos e a aba Confianca cresciam sem controle vertical no
// celular; a opcao de recolher libera espaco pro conteudo principal sem
// remover nada do DOM, so desmonta os filhos quando fechada (default aberta
// para nao mudar o comportamento atual).
import React, { useState } from 'react';

export default function CollapsibleSection({
  id,
  title,
  badge,
  defaultOpen = true,
  children,
}: {
  id: string;
  title: string;
  badge?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const storageKey = `xau_panel_open_${id}`;
  const [isOpen, setIsOpen] = useState<boolean>(() => {
    try {
      const saved = typeof window !== 'undefined' ? window.localStorage.getItem(storageKey) : null;
      return saved === null ? defaultOpen : saved === '1';
    } catch {
      return defaultOpen;
    }
  });

  const toggle = () => {
    setIsOpen((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(storageKey, next ? '1' : '0');
      } catch {
        // localStorage indisponivel: o toggle continua valido na sessao.
      }
      return next;
    });
  };

  return (
    <section className="collapsible-section" aria-label={title}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          padding: '8px 12px',
          background: 'var(--panel-2, rgba(255, 255, 255, 0.03))',
          borderBottom: isOpen ? '1px solid var(--border, rgba(255, 255, 255, 0.1))' : 'none',
          borderRadius: 'var(--radius, 10px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span aria-hidden="true" style={{ color: 'var(--accent, #f59e0b)', fontWeight: 800, fontSize: 12 }}>
            {isOpen ? '▼' : '▶'}
          </span>
          <strong style={{ fontSize: 12.5, letterSpacing: '0.03em' }}>{title}</strong>
          {badge && (
            <span
              className="chip"
              style={{ fontSize: 10.5, padding: '2px 8px', borderRadius: 999 }}
            >
              {badge}
            </span>
          )}
        </div>
        <button
          type="button"
          className="btn ghost xs"
          aria-expanded={isOpen}
          aria-label={isOpen ? `Minimizar ${title}` : `Expandir ${title}`}
          onClick={toggle}
        >
          {isOpen ? 'Minimizar' : 'Expandir'}
        </button>
      </div>
      {isOpen && <div className="collapsible-body">{children}</div>}
    </section>
  );
}
