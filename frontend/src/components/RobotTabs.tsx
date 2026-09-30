// Aba Robô organizada em sub-abas.
//
// O QUE MUDOU
// ===========
// A aba devolvia um fragmento com oito ErrorBoundary empilhados: Modelo,
// Automação, Ordem, Risco, Guardian, Ativos, Copiloto e Mini Terminal, todos
// num único scroll. Era uma página sem hierarquia — nada dizia onde uma
// responsabilidade terminava e a outra começava.
//
// A versão seguinte fez cinco seções (Modelo & Sinal | Operação | Ordem |
// Ativos | Copiloto) e aí apareceram dois problemas: Ordem e Ativos falavam do
// mesmo ativo escolhido em telas separadas, e o operador via a mesma ordem de
// botões repetida em painéis diferentes.
//
// Agora são cinco (Sinal | Automação | Mesa | EA | Copiloto):
//
//   Sinal      → qual ativo usar, qual modelo roda e o que ele prevê
//   Automação  → se o motor está ligado, com que limites e sobre qual par
//   Mesa       → mandar ordem à mão e a parada de emergência
//   EA         → o que existe no terminal MT5, o que o heartbeat reporta e
//                os comandos do Expert Advisor
//   Copiloto   → conversa e achados do EA
//
// E o Mini Terminal continua sempre visível no fim: ele é conferência, não
// comando — é ali que se vê o motor rodando, as posições e a conta.
//
// OS PAINÉIS NÃO SÃO DESMONTADOS
// ===============================
// As sub-abas escondem com `hidden`, sem deixar de renderizar. Desmontar
// jogaria fora a conversa do Copiloto (estado local em useState), a seleção
// de ativo e qualquer leitura em andamento.
import type { ReactNode } from 'react';
import { useAppStore, ROBOT_SUBS, type RobotSub } from '../hooks/useAppStore';
import ErrorBoundary from './ErrorBoundary';
import AutoEnginePanel from './AutoEnginePanel';
import OrderPanel from './OrderPanel';
import RiskTab from './tabs/RiskTab';
import GuardianManager from './GuardianManager';
import UniversalLiveTerminal from './UniversalLiveTerminal';
import '../theme/robot-subtabs.css';
// Densidade das tabelas do Histórico, aplicada também às do Robô (M3).
import '../theme/history-grid.css';

const ROTULOS: Record<RobotSub, string> = {
  operar: 'Operar',
};

const RESUMOS: Record<RobotSub, string> = {
  operar: 'Automático, posições e ordem manual — a mesa inteira num lugar só.',
};

function Secao({ nome, children }: { nome: string; children: ReactNode }) {
  return <ErrorBoundary nome={nome}>{children}</ErrorBoundary>;
}

export default function RobotTabs() {
  const sub = useAppStore((s) => s.robotSub);
  const setSub = useAppStore((s) => s.setRobotSub);

  // UMA ABA SO PARA OPERAR (2026-09-29).
  //
  // "Sinal" e "EA" saíram como sub-abas porque separadas obrigavam o operador a
  // trocar de tela para responder "qual ativo e modelo?" e "quanto posso
  // arriscar?" — duas perguntas que precisam da MESMA resposta, na mesma hora.
  //
  // O `RiskTab` saiu daqui por outro motivo: ele trazia a PARADA DE
  // EMERGENCIA, que ja existia tambem no `OrderPanel`. Dois botoes de corte
  // na mesma tela, em lados opostos, e o risco real de o operador clicar no
  // errado. A parada de emergencia continua no `OrderPanel` (que e onde se
  // envia a ordem) e no risco, mas como leitura — o corte de verdade e o
  // botao unico do OrderPanel.
  //
  // Ordem da mesa, na sequencia em que se opera:
  //   1. automatico  — liga o motor e escolhe ativo/modelo
  //   2. posições    — o que esta aberto agora (conferencia, sempre visivel)
  //   3. ordem       — compra/venda a mao
  //   4. guardian    — protecao e trailing
  const paineis: Record<RobotSub, ReactNode> = {
    operar: (
      <>
        <Secao nome="Operação automática"><AutoEnginePanel /></Secao>
        <Secao nome="Posições ao vivo"><UniversalLiveTerminal /></Secao>
        <Secao nome="Ordem manual"><OrderPanel /></Secao>
        <Secao nome="Guardian"><GuardianManager /></Secao>
      </>
    ),
  };

  return (
    <main className="robot-page">
      <div className="page-head">
        <div>
          <span className="eyebrow">OPERAÇÃO</span>
          <h1>ROBÔ</h1>
          <span className="muted">{RESUMOS[sub]}</span>
        </div>
        <div className="btn-row robot-subtabs" role="tablist" aria-label="Seções de operação">
          {ROBOT_SUBS.map((id) => (
            <button
              key={id}
              type="button"
              role="tab"
              id={`robot-tab-${id}`}
              aria-controls={`robot-panel-${id}`}
              aria-selected={sub === id}
              className="btn"
              onClick={() => setSub(id)}
            >
              {ROTULOS[id]}
            </button>
          ))}
        </div>
      </div>

      {ROBOT_SUBS.map((id) => (
        <div
          key={id}
          className="robot-subpanel"
          role="tabpanel"
          id={`robot-panel-${id}`}
          aria-labelledby={`robot-tab-${id}`}
          hidden={sub !== id}
        >
          {paineis[id]}
        </div>
      ))}
    </main>
  );
}
