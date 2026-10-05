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
import AcompanharModelos from './AcompanharModelos';
import MesaXM from './MesaXM';
import RobotModelPanel from './RobotModelPanel';
import UniversalLiveTerminal from './UniversalLiveTerminal';
import '../theme/robot-subtabs.css';
// Densidade das tabelas do Histórico, aplicada também às do Robô (M3).
import '../theme/history-grid.css';

// Duas sub-abas, uma responsabilidade cada (2026-10-04). Antes era tudo
// empilhado num scroll so — a aba ficava poluida. Automacao fundida na
// Mesa (mesmo LOTE/SL/TP, AUTO SIM/NAO): dois paineis mandando no motor
// era comando repetido.
//
//   Mesa       → comandos simples + lista de modelos + AUTO
//   Acompanhar → grafico ao vivo: opere no grafico e veja os modelos
//
// O Mini Terminal continua sempre visivel no fim: e conferencia, nao
// comando — ali se ve as posicoes e a conta em qualquer sub-aba.
//
// OS PAINEIS NAO SAO DESMONTADOS: as sub-abas escondem com `hidden`, sem
// deixar de renderizar. Desmontar jogaria fora a conversa, a selecao de
// ativo e qualquer leitura em andamento.
const ROTULOS: Record<RobotSub, string> = {
  mesa: 'Mesa',
  acompanhar: 'Acompanhar',
};

const RESUMOS: Record<RobotSub, string> = {
  mesa: 'Comandos, modelos e AUTO — tudo do motor num lugar só.',
  acompanhar: 'Gráfico ao vivo: opere no gráfico e veja os modelos decidindo.',
};

function Secao({ nome, children }: { nome: string; children: ReactNode }) {
  return <ErrorBoundary nome={nome}>{children}</ErrorBoundary>;
}

export default function RobotTabs() {
  const sub = useAppStore((s) => s.robotSub);
  const setSub = useAppStore((s) => s.setRobotSub);

  const paineis: Record<RobotSub, ReactNode> = {
    mesa: (
      <>
        <Secao nome="Mesa XM MT5">
          <MesaXM />
        </Secao>
        <Secao nome="Modelos e sinais">
          <RobotModelPanel />
        </Secao>
      </>
    ),
    acompanhar: (
      <Secao nome="Acompanhar modelos">
        <AcompanharModelos />
      </Secao>
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

      <Secao nome="Posições ao vivo">
        <UniversalLiveTerminal />
      </Secao>
    </main>
  );
}
