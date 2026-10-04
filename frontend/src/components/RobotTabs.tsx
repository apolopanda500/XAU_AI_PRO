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
import AcompanharModelos from './AcompanharModelos';
import MesaXM from './MesaXM';
import RiskTab from './tabs/RiskTab';
import UniversalLiveTerminal from './UniversalLiveTerminal';
import '../theme/robot-subtabs.css';
// Densidade das tabelas do Histórico, aplicada também às do Robô (M3).
import '../theme/history-grid.css';

const ROTULOS: Record<RobotSub, string> = {
  operar: 'Operar',
};

const RESUMOS: Record<RobotSub, string> = {
  operar: 'Operação automática, terminal e posições abertas — só o que o operador precisa ver.',
};

function Secao({ nome, children }: { nome: string; children: ReactNode }) {
  return <ErrorBoundary nome={nome}>{children}</ErrorBoundary>;
}

export default function RobotTabs() {
  const sub = useAppStore((s) => s.robotSub);
  const setSub = useAppStore((s) => s.setRobotSub);

  // ORDEM DA MESA, E O QUE FICOU (2026-09-30)
  // ==============================================
  // O dono pediu: *"operacao automatica, terminal, posicoes abertas so isso
  // mais bem configurado e com botoes melhorados"*.
  //
  // Antes eram quatro blocos, nesta ordem:
  //   1. automatico  — AutoEnginePanel
  //   2. posicoes    — UniversalLiveTerminal
  //   3. ordem manual — OrderPanel
  //   4. guardian    — GuardianManager
  //
  // Saem (3) e (4):
  //   - **Ordem manual**: tinha o seletor de corretora/mercado DUPLICADO (o
  //     `OrderPanel` mantem o proprio `Broker` e `MERCADOS`), o que fazia a
  //     tela afirmar uma corretora e o motor operar outra. Era a origem de
  //     "escolhi Binance e a ordem foi para o MT5".
  //   - **Guardian**: protecao e trailing ficam legiveis no terminal ao vivo e
  //     no EA; dentro do Robô eram um bloco de configuracao que o operador
  //     rarely revisava e que competia visually com o motor.
  //
  // Ficam (1) e (2), que sao as duas leituras que o operador precisa
  // continuamente: o que o motor esta fazendo e o que esta aberto agora.
  const paineis: Record<RobotSub, ReactNode> = {
    operar: (
      <>
        <Secao nome="Mesa XM MT5">
          <MesaXM />
        </Secao>
        <Secao nome="Operação automática">
          <AutoEnginePanel />
        </Secao>
        <Secao nome="Acompanhar modelos">
          <AcompanharModelos />
        </Secao>
        <Secao nome="Posições ao vivo">
          <UniversalLiveTerminal />
        </Secao>
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
