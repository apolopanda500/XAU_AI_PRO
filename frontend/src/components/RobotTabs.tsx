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
import RobotModelPanel from './RobotModelPanel';
import AutoEnginePanel from './AutoEnginePanel';
import OrderPanel from './OrderPanel';
import EAPanel from './EAPanel';
import RiskTab from './tabs/RiskTab';
import GuardianManager from './GuardianManager';
import RobotAssetTable from './RobotAssetTableFixed';
import CopilotPanel from './CopilotPanel';
import UniversalLiveTerminal from './UniversalLiveTerminalLatest';
import '../theme/robot-subtabs.css';
// Densidade das tabelas do Histórico, aplicada também às do Robô (M3).
import '../theme/history-grid.css';

const ROTULOS: Record<RobotSub, string> = {
  sinal: 'Sinal',
  automacao: 'Automação',
  mesa: 'Mesa',
  ea: 'EA',
  copiloto: 'Copiloto',
};

const RESUMOS: Record<RobotSub, string> = {
  sinal: 'Ativo com cotação, modelo treinado e previsão do próximo candle.',
  automacao: 'Motor automático, limites de risco e proteção de posição.',
  mesa: 'Ticket manual à mão: volume, SL, TP e a parada de emergência.',
  ea: 'Expert Advisors no terminal: inventário, heartbeat e comandos.',
  copiloto: 'Conversa com o analista e achados sobre o código do EA.',
};

function Secao({ nome, children }: { nome: string; children: ReactNode }) {
  return <ErrorBoundary nome={nome}>{children}</ErrorBoundary>;
}

export default function RobotTabs() {
  const sub = useAppStore((s) => s.robotSub);
  const setSub = useAppStore((s) => s.setRobotSub);

  const paineis: Record<RobotSub, ReactNode> = {
    sinal: (
      <>
        <Secao nome="Modelo e sinal"><RobotModelPanel /></Secao>
        <Secao nome="Ativos da corretora"><RobotAssetTable /></Secao>
      </>
    ),
    automacao: (
      <>
        <Secao nome="Operação automática"><AutoEnginePanel /></Secao>
        <Secao nome="Risco"><RiskTab /></Secao>
        <Secao nome="Guardian"><GuardianManager /></Secao>
      </>
    ),
    mesa: <Secao nome="Execução"><OrderPanel /></Secao>,
    ea: <Secao nome="Expert Advisors"><EAPanel /></Secao>,
    copiloto: <Secao nome="Copiloto"><CopilotPanel /></Secao>,
  };

  return (
    <main className="robot-page">
      <div className="page-head">
        <div>
          <span className="eyebrow">OPERAÇÃO</span>
          <h1>Robô</h1>
          <span className="muted">{RESUMOS[sub]}</span>
        </div>
        <div className="btn-row robot-subtabs" role="tablist" aria-label="Seções do Robô">
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

      <ErrorBoundary nome="Mini Terminal"><UniversalLiveTerminal /></ErrorBoundary>
    </main>
  );
}
