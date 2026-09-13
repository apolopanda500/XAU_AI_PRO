import React from 'react';
import { useAppStore } from '../../hooks/useAppStore';

export const Dashboard: React.FC = () => {
  const { quotes, account, positions, wsConnected } = useAppStore();

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, fontWeight: 'bold', marginBottom: 16 }}>
        XAU AI PRO ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Trading Dashboard
      </h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <Card title="Status WS" value={wsConnected ? 'ÃƒÂ°Ã…Â¸Ã…Â¸Ã‚Â¢ Conectado' : 'ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´ Desconectado'} />
        <Card title="Saldo" value={account ? `$${account.balance.toFixed(2)}` : '---'} />
        <Card title="Equity" value={account ? `$${account.equity.toFixed(2)}` : '---'} />
        <Card title="PosiÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes" value={positions.length.toString()} />
      </div>

      <h2 style={{ fontSize: 18, marginBottom: 12 }}>CotaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes em Tempo Real</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        {quotes.map((q) => (
          <QuoteCard key={q.symbol} quote={q} />
        ))}
      </div>
    </div>
  );
};

const Card: React.FC<{ title: string; value: string }> = ({ title, value }) => (
  <div style={{ background: '#151d28', border: '1px solid #243244', borderRadius: 8, padding: 16 }}>
    <div style={{ fontSize: 12, color: '#9ca9bd', marginBottom: 4 }}>{title}</div>
    <div style={{ fontSize: 20, fontWeight: 'bold' }}>{value}</div>
  </div>
);

const QuoteCard: React.FC<{ quote: any }> = ({ quote }) => (
  <div style={{ background: '#151d28', border: '1px solid #243244', borderRadius: 8, padding: 12 }}>
    <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{quote.symbol}</div>
    <div style={{ fontSize: 18, color: '#00c6fb' }}>{quote.last?.toFixed(2)}</div>
    <div style={{ fontSize: 12, color: '#9ca9bd' }}>
      Bid: {quote.bid?.toFixed(2)} | Ask: {quote.ask?.toFixed(2)}
    </div>
    <div style={{ fontSize: 12, color: quote.change_pct >= 0 ? '#00c853' : '#ff3d57' }}>
      {quote.change_pct >= 0 ? '+' : ''}{quote.change_pct?.toFixed(2)}%
    </div>
  </div>
);







