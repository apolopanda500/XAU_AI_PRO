/**
 * Componente de Aba do Calendário Econômico
 * XAU AI PRO - Exibe eventos econômicos com filtros e countdown
 */

import React, { useState, useMemo, useEffect } from 'react';
import { useEconomicData } from '../../hooks/useEconomicData';
import { apiBase } from '../../lib/api';
import '../../theme/calendar.css';
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

export type DiaCalendario = {
  /** yyyy-mm-dd — serve de key e garante ordem estável. */
  chave: string;
  /** "Hoje"/"Amanhã"/"Ontem" quando cabe, senão vazio. */
  relato: string;
  /** Data por extenso, em minúsculas (o CSS deixa a inicial maiúscula). */
  data: string;
  eventos: EconomicEvent[];
};

/**
 * Agrupa os eventos por dia e ordena DO BAIXO PARA O ALTO.
 *
 * Antes o agrupamento usava a ordem de chegada da API, que vem agrupada por
 * país/fonte: o dia 29 aparecia antes do 28 e o rótulo de dia subia fora de
 * ordem na rolagem. Aqui os eventos são ordenados por horário primeiro —
 * daí a ordem dos dias e a ordem deles dentro do dia caem sozinhas.
 */
export function agruparPorDia(
  eventos: EconomicEvent[],
  agora: Date = new Date(),
): DiaCalendario[] {
  const ordenados = [...eventos].sort((a, b) => a.horario.getTime() - b.horario.getTime());
  const grupos = new Map<string, DiaCalendario>();

  for (const evento of ordenados) {
    const d = evento.horario;
    const chave = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    let dia = grupos.get(chave);
    if (!dia) {
      dia = {
        chave,
        relato: relatoDia(d, agora),
        data: d.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' }),
        eventos: [],
      };
      grupos.set(chave, dia);
    }
    dia.eventos.push(evento);
  }

  return [...grupos.values()];
}

function relatoDia(d: Date, agora: Date): string {
  const meioNoite = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const dias = Math.round((meioNoite(d) - meioNoite(agora)) / 86_400_000);
  if (dias === 0) return 'Hoje';
  if (dias === 1) return 'Amanhã';
  if (dias === -1) return 'Ontem';
  return '';
}

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

function EventoRow({ evento, passado }: { evento: EconomicEvent; passado: boolean }) {
  const horaFormatada = evento.horario.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return (
    <div className={`cal-row${passado ? ' passado' : ''}`}>
      <span className="cal-row-time">{horaFormatada}</span>
      <span className="cal-row-flag" title={evento.nomePais}>{evento.bandeira}</span>
      <div className="cal-row-title">
        <strong>{evento.titulo}</strong>
        <span className="cal-row-note">
          <span className={`cal-impact ${evento.impacto}`}>{LABELS_IMPACTO[evento.impacto]}</span>
          {evento.divulgado ? ' divulgado' : ''}
        </span>
      </div>
      <span className="num muted">{evento.anterior ?? '—'}</span>
      <span className="num">{evento.consenso ?? '—'}</span>
      <span className="num" style={evento.real ? { color: 'var(--success, #34d399)' } : undefined}>{evento.real ?? '—'}</span>
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

  // Dias em ordem crescente, eventos em ordem crescente dentro de cada dia.
  const dias = useMemo(() => agruparPorDia(eventos), [eventos]);

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
    // Este bloco chamava um LLM EXTERNO na Vercel
    // (xau-ai-pro-api-apolopanda500.vercel.app/api/chat) e ainda montava o
    // contexto com campos que a agenda real nao devolve (titulo, anterior,
    // consenso, real) — os eventos usam title/note/impact/when. Resultado:
    // chamada paga a um servico de terceiros com contexto vazio.
    // Agora usa o copiloto local, que tem intencao `agenda` e le a mesma
    // agenda real do gateway.
    const contexto = eventos.slice(0, 40).map((evento) => ({
      quando: evento.horario.toISOString(), titulo: evento.titulo,
      moeda: evento.codigoPais, impacto: evento.impacto,
      consenso: evento.consenso, anterior: evento.anterior, real: evento.real,
    }));
    try {
      const response = await fetch(`${apiBase()}/api/copilot/perguntar`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pergunta: copilotPrompt,
          contexto: { eventos: contexto, fonte: 'agenda economica real do app' },
        }),
        signal: AbortSignal.timeout(15000),
      });
      const data = await response.json() as { resposta?: string; reply?: string; error?: string };
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setCopilotReply(data.resposta || data.reply || 'O copiloto não retornou uma análise.');
    } catch (error) { setCopilotError(error instanceof Error ? error.message : 'Copiloto indisponível'); }
    finally { setCopilotLoading(false); }
  };

  if (erro) {
    return (
      <div className="card compact-card cal-copilot" role="alert">
        <h3>Erro ao carregar o calendário</h3>
        <p className="hint">{erro}</p>
        <button className="btn sm ghost" type="button" onClick={refreshManual}>Tentar novamente</button>
      </div>
    );
  }

  return (
    <div className="calendar-tab">
      <div className="cal-head">
        <div>
          <h2>Calendário Econômico</h2>
          <span className="cal-head-count">{totalEventos} eventos</span>
        </div>
        <div className="cal-head-actions">
          {ultimaAtualizacao && <span className="muted">Atualizado {ultimaAtualizacao.toLocaleTimeString('pt-BR')}</span>}
          <button className="btn xs ghost" type="button" onClick={refreshManual} disabled={carregando}>
            {carregando ? 'Atualizando…' : 'Atualizar'}
          </button>
        </div>
      </div>

      {proximoEventoAlto && <CountdownEvento evento={proximoEventoAlto} />}

      <div className="cal-filters">
        <div className="cal-filter-row">
          <span className="cal-filter-label">País</span>
          {PAISES_SUPORTADOS.map((pais) => (
            <button key={pais.codigo} type="button" onClick={() => togglePais(pais.codigo)}
              className={`cal-chip ${filtro.paises.includes(pais.codigo) ? 'on' : ''}`}>
              {pais.bandeira} {pais.nome}
            </button>
          ))}
        </div>
        <div className="cal-filter-row">
          <span className="cal-filter-label">Impacto</span>
          {(['alto', 'medio', 'baixo'] as ImpactLevel[]).map((impacto) => (
            <button key={impacto} type="button" onClick={() => toggleImpacto(impacto)}
              className={`cal-chip ${filtro.impactos.includes(impacto) ? 'on' : ''}`}>
              {LABELS_IMPACTO[impacto]}
            </button>
          ))}
          {(filtro.paises.length > 0 || filtro.impactos.length > 0) && (
            <button className="cal-chip cal-chip-clear" type="button" onClick={limparFiltros}>Limpar</button>
          )}
        </div>
      </div>

      <div className="card compact-card cal-copilot">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <div>
            <h3>Copiloto econômico</h3>
            <span className="muted">Responde só com os eventos reais carregados</span>
          </div>
          <span className="chip warn">Somente leitura</span>
        </div>
        <div className="cal-copilot-row">
          <input
            value={copilotPrompt}
            onChange={(event) => setCopilotPrompt(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void consultarCopiloto(); } }}
            placeholder="Pergunte sobre risco, volatilidade ou agenda…"
          />
          <button className="btn sm primary" type="button" onClick={() => void consultarCopiloto()} disabled={copilotLoading || !eventos.length}>
            {copilotLoading ? 'Analisando…' : 'Analisar'}
          </button>
        </div>
        {copilotError && <div className="hint neg" role="alert" style={{ marginTop: 8 }}>Copiloto indisponível: {copilotError}</div>}
        {copilotReply && <div className="cal-copilot-reply">{copilotReply}</div>}
        <p className="hint" style={{ margin: '8px 0 0' }}>O copiloto não envia ordens, não altera o EA e não movimenta ativos.</p>
      </div>

      <div className="cal-columns">
        <span className="num">Hora</span>
        <span></span>
        <span>Evento</span>
        <span className="num">Anterior</span>
        <span className="num">Consenso</span>
        <span className="num">Real</span>
      </div>

      <div className="cal-body">
        {carregando && eventos.length === 0 ? (
          <div className="cal-state">Carregando eventos…</div>
        ) : dias.length === 0 ? (
          <div className="cal-state">Nenhum evento encontrado.</div>
        ) : (
          dias.map((dia) => (
            <div key={dia.chave} className="cal-day">
              <div className="cal-day-label">
                {dia.relato && <span className={`cal-day-badge ${dia.relato.toLowerCase()}`}>{dia.relato}</span>}
                <span className="cal-day-data">{dia.data}</span>
                <span className="cal-day-count">
                  {dia.eventos.length} {dia.eventos.length === 1 ? 'evento' : 'eventos'}
                </span>
              </div>
              {dia.eventos.map((evento) => (
                <EventoRow
                  key={evento.id}
                  evento={evento}
                  passado={evento.horario.getTime() < Date.now()}
                />
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default EconomicCalendarTab;
