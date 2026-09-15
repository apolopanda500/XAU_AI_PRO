import React from 'react';
import { useAppStore } from '../hooks/useAppStore';

/** Indicador alimentado pelo WebSocket persistente do Core; sem polling. */
export const MiniInfoWidget: React.FC = () => {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const quotes = useAppStore((s) => s.quotes);
  const lastQuote = quotes.reduce((latest, quote) => !latest || quote.timestamp > latest.timestamp ? quote : latest, quotes[0]);
  const connected = wsConnected && Boolean(lastQuote);
  return <div className="mini-info-widget"><div className="mini-item"><span className="mini-label">FONTE DE MERCADO</span><span className={connected ? 'pos' : 'neg'}>{connected ? 'MT5 conectado · dados reais' : 'MT5 aguardando conexão'}</span>{lastQuote && <span className="muted">{lastQuote.symbol} atualizado {new Date(lastQuote.timestamp).toLocaleTimeString('pt-BR')}</span>}</div></div>;
};

export default MiniInfoWidget;
