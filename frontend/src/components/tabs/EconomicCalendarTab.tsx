/**
 * Componente de Aba do Calendário Econômico
 * XAU AI PRO - Exibe eventos econômicos com filtros e countdown
 */

import React, { useState, useMemo, useEffect } from 'react';
import { useEconomicData } from '../../hooks/useEconomicData';
import {
  EconomicEvent,
  FiltroCalendario,
  ImpactLevel,
  PAISES_SUPORTADOS,
  CORES_IMPACTO,
} from './types';

const LABELS_IMPACTO: Record<ImpactLevel, string> = {
  baixo: 'Baixo',
  medio: 'Médio',
  alto: 'Alto',
};

const CORES_BADGE: Record<ImpactLevel, { bg: string; text: string }> = {
  baixo: { bg: '#374151', text: '#9ca3af' },
  medio: { bg: '#78350f', text: '#fbbf24' },
  alto: { bg: '#7f1d1d', text: '#fca5a5' },
};

function CountdownEvento({ evento }: { evento: EconomicEvent }) {
  const [tempoRestante, setTempoRestante] = useState<string>('');

  useEffect(() => {
    const atualizarCountdown = () => {
      const agora = new Date().getTime();
      const eventoTime = new Date(evento.horario).getTime();
      const diff = eventoTime - agora;

      if (diff <= 0) {
        setTempoRestante('AO VIVO');
        return;
      }

      const horas = Math.floor(diff / (1000 * 60 * 60));
      const minutos = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const segundos = Math.floor((diff % (1000 * 60)) / 1000);

      if (horas > 24) {
        const dias = Math.floor(horas / 24);
        setTempoRestante(`${dias}d ${horas % 24}h`);
      } else {
        setTempoRestante(
          `${horas.toString().padStart(2, '0')}:${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`
        );
      }
    };

    atualizarCountdown();
    const intervalo = setInterval(atualizarCountdown, 1000);
    return () => clearInterval(intervalo);
  }, [evento.horario]);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px',
      background: 'linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%)',
      borderRadius: '8px', marginBottom: '16px', border: '1px solid #991b1b',
      animation: 'pulse 2s infinite',
    }}>
      <span style={{ background: '#ef4444', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700, letterSpacing: '0.5px' }}>
        ALTO IMPACTO
      </span>
      <span style={{ color: '#fca5a5', fontSize: '12px' }}>
        {evento.bandeira} {evento.titulo}
      </span>
      <span style={{ marginLeft: 'auto', fontFamily: 'monospace', fontSize: '16px', fontWeight: 700, color: '#fca5a5', letterSpacing: '1px' }}>
        {tempoRestante}
      </span>
    </div>
  );
}

function EventoRow({ evento }: { evento: EconomicEvent }) {
  const corImpacto = CORES_IMPACTO[evento.impacto];
  const corBadge = CORES_BADGE[evento.impacto];
  const horaFormatada = evento.horario.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '60px 40px 1fr 100px 80px 80px 80px',
      gap: '10px', padding: '10px 12px',
      backgroundColor: evento.divulgado ? '#111827' : '#1f2937',
      borderRadius: '6px', borderLeft: `3px solid ${corImpacto}`,
      alignItems: 'center', fontSize: '12px',
    }}>
      <span style={{ fontFamily: 'monospace', color: '#d1d5db', fontWeight: 600 }}>
        {horaFormatada}
      </span>
      <span style={{ fontSize: '18px', textAlign: 'center' }}>{evento.bandeira}</span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <span style={{ color: '#f3f4f6', fontWeight: 500 }}>{evento.titulo}</span>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span style={{ backgroundColor: corBadge.bg, color: corBadge.text, padding: '1px 6px', borderRadius: '3px', fontSize: '9px', fontWeight: 700 }}>
            {LABELS_IMPACTO[evento.impacto].toUpperCase()}
          </span>
          {evento.divulgado && (
            <span style={{ backgroundColor: '#064e3b', color: '#34d399', padding: '1px 6px', borderRadius: '3px', fontSize: '9px', fontWeight: 600 }}>
              DIVULGADO
            </span>
          )}
        </div>
      </div>
      <span style={{ color: '#9ca3af', textAlign: 'center' }}>{evento.anterior ?? '-'}</span>
      <span style={{ color: '#d1d5db', textAlign: 'center', fontWeight: 500 }}>{evento.consenso ?? '-'}</span>
      <span style={{ color: evento.real ? '#34d399' : '#6b7280', textAlign: 'center', fontWeight: evento.real ? 600 : 400 }}>
        {evento.real ?? '-'}
      </span>
    </div>
  );
}

export function EconomicCalendarTab() {
  const [copilotPrompt, setCopilotPrompt] = useState('Quais eventos podem aumentar a volatilidade do XAUUSD e quais cuidados devo tomar?');
  const [copilotReply, setCopilotReply] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [copilotError, setCopilotError] = useState('');
  const [filtro, setFiltro] = useState<FiltroCalendario>({
    paises: [], impactos: [], dataInicio: null, dataFim: null,
  });

  const { eventos, carregando, erro, ultimaAtualizacao, proximoEventoAlto, refreshManual, totalEventos } = useEconomicData(filtro);

  const eventosPorData = useMemo(() => {
    const grupos: Record<string, EconomicEvent[]> = {};
    eventos.forEach((evento) => {
      const dataKey = evento.horario.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
      if (!grupos[dataKey]) grupos[dataKey] = [];
      grupos[dataKey].push(evento);
    });
    return grupos;
  }, [eventos]);

  const togglePais = (codigo: string) => {
    setFiltro((prev) => ({
      ...prev,
      paises: prev.paises.includes(codigo) ? prev.paises.filter((p) => p !== codigo) : [...prev.paises, codigo],
    }));
  };

  const toggleImpacto = (impacto: ImpactLevel) => {
    setFiltro((prev) => ({
      ...prev,
      impactos: prev.impactos.includes(impacto) ? prev.impactos.filter((i) => i !== impacto) : [...prev.impactos, impacto],
    }));
  };

  const limparFiltros = () => { setFiltro({ paises: [], impactos: [], dataInicio: null, dataFim: null }); };

  const consultarCopiloto = async () => {
    if (!copilotPrompt.trim() || !eventos.length) return;
    setCopilotLoading(true); setCopilotError('');
    const contexto = eventos.slice(0, 40).map((evento) => ({
      horario: evento.horario.toISOString(), pais: evento.codigoPais, impacto: evento.impacto,
      titulo: evento.titulo, anterior: evento.anterior, consenso: evento.consenso, real: evento.real,
    }));
    try {
      const base = 'https://xau-ai-pro-api-apolopanda500.vercel.app';
      const response = await fetch(`${base}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: `Analise somente os eventos econômicos reais abaixo para um trader de XAUUSD. Não dê ordem de compra/venda, não invente números e deixe claro quando não houver evidência. Pergunta: ${copilotPrompt}\nEventos: ${JSON.stringify(contexto)}` }),
        signal: AbortSignal.timeout(30000),
      });
      const data = await response.json() as { reply?: string; error?: string };
      if (!response.ok) throw new Error(data.error || `IA HTTP ${response.status}`);
      setCopilotReply(data.reply || 'A IA não retornou uma análise.');
    } catch (error) { setCopilotError(error instanceof Error ? error.message : 'Copiloto indisponível'); }
    finally { setCopilotLoading(false); }
  };

  if (erro) {
    return (
      <div style={{ padding: '20px', color: '#fca5a5', textAlign: 'center' }}>
        <p>Erro ao carregar calendário: {erro}</p>
        <button onClick={refreshManual}>Tentar novamente</button>
      </div>
    );
  }

  return (
    <div className="calendar-tab" style={{ display: 'flex', flexDirection: 'column', height: '100%', color: '#f3f4f6', fontSize: '13px' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #374151', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>📅 Calendário Econômico</h2>
          <span style={{ color: '#9ca3af', fontSize: '11px' }}>{totalEventos} eventos</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {ultimaAtualizacao && (
            <span style={{ color: '#6b7280', fontSize: '10px' }}>Atualizado: {ultimaAtualizacao.toLocaleTimeString('pt-BR')}</span>
          )}
          <button onClick={refreshManual} disabled={carregando} style={{ padding: '4px 10px', backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '4px', color: '#d1d5db', cursor: carregando ? 'not-allowed' : 'pointer', fontSize: '11px' }}>
            {carregando ? '⏳' : '🔄'} Refresh
          </button>
        </div>
      </div>

      {proximoEventoAlto && <CountdownEvento evento={proximoEventoAlto} />}

      <div style={{ padding: '10px 16px', borderBottom: '1px solid #374151', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ color: '#9ca3af', fontSize: '11px', minWidth: '40px' }}>País:</span>
          {PAISES_SUPORTADOS.map((pais) => (
            <button key={pais.codigo} onClick={() => togglePais(pais.codigo)} style={{
              padding: '3px 8px', backgroundColor: filtro.paises.includes(pais.codigo) ? '#2563eb' : '#1f2937',
              border: `1px solid ${filtro.paises.includes(pais.codigo) ? '#3b82f6' : '#374151'}`,
              borderRadius: '4px', color: '#d1d5db', cursor: 'pointer', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px',
            }}>
              {pais.bandeira} {pais.nome}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: '#9ca3af', fontSize: '11px', minWidth: '40px' }}>Impacto:</span>
          {(['alto', 'medio', 'baixo'] as ImpactLevel[]).map((impacto) => (
            <button key={impacto} onClick={() => toggleImpacto(impacto)} style={{
              padding: '3px 8px',
              backgroundColor: filtro.impactos.includes(impacto) ? CORES_IMPACTO[impacto] : '#1f2937',
              border: `1px solid ${CORES_IMPACTO[impacto]}`,
              borderRadius: '4px',
              color: filtro.impactos.includes(impacto) ? '#000' : '#d1d5db',
              cursor: 'pointer', fontSize: '11px', fontWeight: 600,
            }}>
              {LABELS_IMPACTO[impacto]}
            </button>
          ))}
          {(filtro.paises.length > 0 || filtro.impactos.length > 0) && (
            <button onClick={limparFiltros} style={{ padding: '3px 8px', backgroundColor: 'transparent', border: '1px solid #6b7280', borderRadius: '4px', color: '#9ca3af', cursor: 'pointer', fontSize: '10px', marginLeft: 'auto' }}>
              ✕ Limpar
            </button>
          )}
        </div>
      </div>

      <div className="card" style={{ margin: '12px 16px', padding: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <div><h3 style={{ margin: 0 }}>Copiloto econômico</h3><span className="muted" style={{ fontSize: 11 }}>IA contextual baseada apenas nos eventos reais carregados</span></div>
          <span className="chip warn">Somente análise</span>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <input value={copilotPrompt} onChange={(event) => setCopilotPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void consultarCopiloto(); } }} placeholder="Pergunte sobre risco, volatilidade ou agenda..." style={{ flex: 1 }} />
          <button className="btn sm primary" type="button" onClick={() => void consultarCopiloto()} disabled={copilotLoading || !eventos.length}>{copilotLoading ? 'Analisando...' : 'Analisar'}</button>
        </div>
        {copilotError && <div className="hint neg" role="alert" style={{ marginTop: 8 }}>Copiloto indisponível: {copilotError}</div>}
        {copilotReply && <div className="placeholder" style={{ marginTop: 10, whiteSpace: 'pre-wrap', textAlign: 'left', alignItems: 'flex-start' }}>{copilotReply}</div>}
        <div className="hint" style={{ marginTop: 8 }}>A IA não envia ordens, não altera o EA e não movimenta ativos. Chaves permanecem no backend.</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '60px 40px 1fr 100px 80px 80px 80px', gap: '10px', padding: '8px 12px', backgroundColor: '#111827', borderBottom: '1px solid #374151', fontSize: '10px', fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase' }}>
        <span>Hora</span><span></span><span>Evento</span>
        <span style={{ textAlign: 'center' }}>Anterior</span>
        <span style={{ textAlign: 'center' }}>Consenso</span>
        <span style={{ textAlign: 'center' }}>Real</span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {carregando && eventos.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100px', color: '#6b7280' }}>
            Carregando eventos...
          </div>
        ) : Object.entries(eventosPorData).length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100px', color: '#6b7280' }}>
            Nenhum evento encontrado.
          </div>
        ) : (
          Object.entries(eventosPorData).map(([data, eventosData]) => (
            <div key={data}>
              <div style={{ padding: '6px 0', color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'capitalize', borderBottom: '1px solid #374151', marginBottom: '6px' }}>
                {data}
              </div>
              {eventosData.map((evento) => (
                <EventoRow key={evento.id} evento={evento} />
              ))}
            </div>
          ))
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.85; }
        }
      `}</style>
    </div>
  );
}

export default EconomicCalendarTab;
