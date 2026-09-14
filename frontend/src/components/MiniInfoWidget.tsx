/**
 * MiniInfoWidget — Widget compacto de informações rápidas
 * Aparece no topo das abas: calendário resumido + notícias + hashrate
 */

import React, { useState, useEffect } from 'react';

interface EventoCalendario {
  hora: string;
  pais: string;
  impacto: 'alto' | 'medio' | 'baixo';
  titulo: string;
}

interface Noticia {
  titulo: string;
  fonte: string;
  tempo: string;
  sentimento: 'bullish' | 'bearish' | 'neutral';
}

const EVENTOS_MOCK: EventoCalendario[] = [];

const NOTICIAS_MOCK: Noticia[] = [];
/* legado removido: dados sintéticos não são exibidos em produção.
  { titulo: 'Fed mantém taxas estáveis', fonte: 'Reuters', tempo: '5min', sentimento: 'bullish' },
  { titulo: 'Ouro sobe com tensão geopolítica', fonte: 'Bloomberg', tempo: '12min', sentimento: 'bullish' },
  { titulo: 'Bitcoin testa resistência', fonte: 'CoinDesk', tempo: '30min', sentimento: 'neutral' },
];

*/
export const MiniInfoWidget: React.FC = () => {
  const [eventos] = useState<EventoCalendario[]>(EVENTOS_MOCK);
  const [noticias] = useState<Noticia[]>(NOTICIAS_MOCK);
  const [proximoEvento, setProximoEvento] = useState<EventoCalendario | null>(null);

  useEffect(() => {
    const agora = new Date();
    const horaAtual = agora.getHours() * 60 + agora.getMinutes();
    
    const proximo = eventos.find(e => {
      const [h, m] = e.hora.split(':').map(Number);
      return h * 60 + m > horaAtual;
    });
    
    setProximoEvento(proximo || eventos[0]);
  }, [eventos]);

  const corImpacto = (impacto: string) => {
    switch (impacto) {
      case 'alto': return '#ef4444';
      case 'medio': return '#f59e0b';
      case 'baixo': return '#6b7280';
      default: return '#6b7280';
    }
  };

  const iconeSentimento = (sentimento: string) => {
    switch (sentimento) {
      case 'bullish': return '▲';
      case 'bearish': return '▼';
      default: return '─';
    }
  };

  const corSentimento = (sentimento: string) => {
    switch (sentimento) {
      case 'bullish': return '#22c55e';
      case 'bearish': return '#ef4444';
      default: return '#6b7280';
    }
  };

  return (
    <div className="mini-info-widget">
      {/* Próximo evento do calendário */}
      {proximoEvento && (
        <div className="mini-item mini-evento">
          <span className="mini-label">PRÓXIMO EVENTO</span>
          <div className="mini-evento-info">
            <span className="mini-hora">{proximoEvento.hora}</span>
            <span className="mini-pais">{proximoEvento.pais}</span>
            <span 
              className="mini-impacto"
              style={{ backgroundColor: corImpacto(proximoEvento.impacto) }}
            >
              {proximoEvento.impacto.toUpperCase()}
            </span>
            <span className="mini-titulo">{proximoEvento.titulo}</span>
          </div>
        </div>
      )}

      {/* Notícias rápidas */}
      <div className="mini-item mini-noticias">
        <span className="mini-label">ÚLTIMAS NOTÍCIAS</span>
        <div className="mini-noticias-lista">
          {noticias.slice(0, 2).map((n, i) => (
            <div key={i} className="mini-noticia">
              <span className="mini-sentimento" style={{ color: corSentimento(n.sentimento) }}>
                {iconeSentimento(n.sentimento)}
              </span>
              <span className="mini-noticia-titulo">{n.titulo}</span>
              <span className="mini-tempo">{n.tempo}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Status de mineração */}
      <div className="mini-item mini-mining">
        <span className="mini-label">MINING</span>
        <div className="mini-mining-info">
          <span className="mini-hash">⛏️ 142.5 MH/s</span>
          <span className="mini-temp ok">62°C</span>
          <span className="mini-leds">
            {Array.from({ length: 5 }).map((_, i) => (
              <span key={i} className="mini-led on" />
            ))}
          </span>
        </div>
      </div>
    </div>
  );
};

export default MiniInfoWidget;
