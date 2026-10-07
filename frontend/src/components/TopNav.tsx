import React, { useEffect, useMemo } from 'react';
import { useAppStore } from '../hooks/useAppStore';
import { useEaRuntime } from '../hooks/queries';
import QuantumClock from './QuantumClock';

// A navegacao vive em Sidebar.tsx (ITEMS). Este arquivo usava declarar um
// TABS proprio com 4 entradas que nunca eram renderizadas — uma terceira lista
// de abas que divergia da Sidebar conforme as abas eram adicionadas.

export default function TopNav() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const setRobotStatus = useAppStore((s) => s.setRobotStatus);
  const ea = useEaRuntime();
  const hb = ea.data?.ea_heartbeat;

  /*
    "EA: Desconectado" ERA UM TEXTO FIXO, E O EA ESTAVA RODANDO (05/10/2026).

    MEDIDO: `useAppStore.ts:309` nasce com `robotStatus: 'Desconectado'`, e o
    único lugar que escreve nesse campo é `useAICommunication` — que nunca é
    chamado. Então o cabeçalho mostrava o padrão de fábrica.

    Enquanto isso, o heartbeat real (lido do disco) dizia:
        state RUNNING · autotrading true · login 391773676
        server XMGlobal-MT5 14 · symbol ETHUSD · write_count 19027

    Um rótulo que afirma o contrário do que está medido é pior que rótulo
    nenhum: o operador vai ao terminal conferir e perde a confiança na tela
    inteira. Por isso o texto agora vem de `/api/ea/status`, e a distinção que
    importa é **sem sinal há N**, e não "desconectado" — o EA pode estar vivo
    com o heartbeat velho, que é outra coisa e exige outra ação.
  */
  const robotStatus = useMemo(() => {
    if (ea.isLoading) return 'lendo…';
    if (!ea.data) return 'sem leitura';
    if (hb?.live === true) {
      const par = hb.symbol ? `${hb.symbol}${hb.timeframe ? ` ${hb.timeframe}` : ''}` : '';
      return `no gráfico${par ? ` · ${par}` : ''}`;
    }
    const idade = hb?.age_sec ?? hb?.file_age_sec;
    if (hb?.state) {
      return idade != null
        ? `${hb.state} · sem sinal há ${Math.round(idade)}s`
        : hb.state;
    }
    return 'sem sinal';
  }, [ea.isLoading, ea.data, hb]);

  useEffect(() => {
    setRobotStatus(robotStatus);
  }, [robotStatus, setRobotStatus]);

  return (
    <header className="topbar">
      <div className="topnav-status">
        <span className="status">
          <i className={`dot ${wsConnected ? 'on' : ''}`} /> WS {wsConnected ? 'Online' : 'Offline'}
        </span>
        <span className="status">🤖 AI: {aiStatus}</span>
        <span className="status">EA: {robotStatus}</span>
        <QuantumClock compact showSeconds={false} showDate={false} />
      </div>
    </header>
  );
}
