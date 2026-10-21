import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { useAppStore, type TabType } from './hooks/useAppStore';
import { useTheme } from './hooks/useTheme';
import { useCoreBootstrap } from './hooks/useCoreBootstrap';
import { useMarketWebSocket } from './hooks/useMarketWebSocket';
import AuthGate from './components/AuthGate';
import UserSessionGate from './components/auth/UserSessionGate';
import QuantumBackground from './components/QuantumBackground';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import PortfolioHome from './components/tabs/PortfolioHomeSafe';
import RobotTabs from './components/RobotTabs';
import HistoryTab from './components/tabs/HistoryTab';
import SystemHealth from './components/SystemHealthOnly';
import SettingsCore from './components/SettingsCore';
import ExitAppButton from './components/ExitAppButton';
import EconomicCalendarTab from './components/tabs/EconomicCalendarTab';
import StatusBar from './components/StatusBar';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

function renderActiveTab(tab: TabType): ReactNode {
  switch (tab) {
    case 'portfolio':
      return <PortfolioHome />;
    // A aba Operar tem quatro sub-abas (Operar | Sinal | EA | Copiloto) e
    // abre na primeira: motor automatico, posicoes ao vivo e ordem manual.
    // Cada painel segue dentro da sua barreira de erro: um painel que
    // falhasse desmontava a arvore React inteira e a aba ficava branca - o
    // usuario perdia o app sem saber qual era o culpado.
    case 'robot':
      return <RobotTabs />;
    // Performance & Analytics foi fundida no Histórico: as duas telas
    // analisam a mesma coisa — as operações realizadas.
    case 'history':
      return <HistoryTab />;
    case 'system':
      return <SystemHealth />;
    case 'settings':
      return (
        <>
          <SettingsCore />
          <ExitAppButton />
        </>
      );
    case 'calendar':
      return <EconomicCalendarTab />;
    // VIPS REMOVIDO (05/10/2026): "abas vips nao funcionar qualquer remover
    // deletar". O `case` some junto com a aba.
    //
    // Fica um commentario porque `'vips'` CONTINUA no tipo `TabType`: quem
    // tiver essa aba gravada no `localStorage` ainda gera o `case`, e sem ele a
    // tela apareceria VAZIA — que e pior que mostrar que a aba nao existe.
    case 'vips':
      return <AbaRemovida nome="VIPS" />;
    default:
      return null;
  }
}

/**
 * Aba removida que alguém ainda tenha gravada.
 *
 * POR QUE EXISTE E POR QUE NÃO É TELA VAZIA
 * ===========================================
 * Quem usou a versão anterior tem `'vips'` no `localStorage`. Sem um `case`,
 * `renderActiveTab` devolve `null` e a área de conteúdo fica VAZIA: sem texto,
 * sem botão, sem explicação. O operador clica em uma aba que existia e recebe
 * uma página em branco, e o defeito parece ser "o app quebrou".
 *
 * Aqui a tela diz o que aconteceu e oferece voltar. É a diferença entre
 * "removido" e "quebrado".
 */
function AbaRemovida({ nome }: { nome: string }) {
  const setActiveTab = useAppStore((state) => state.setActiveTab);
  return (
    <main className="page-head">
      <div>
        <span className="eyebrow">INDISPONÍVEL</span>
        <h1>{nome}</h1>
        <span className="muted">Esta aba foi removida do aplicativo.</span>
      </div>
      <div className="btn-row">
        <button type="button" className="btn primary" onClick={() => setActiveTab('robot')}>
          Ir para o Robô
        </button>
      </div>
    </main>
  );
}

export default function App() {
  const activeTab = useAppStore((state) =>
    state.activeTab === 'dashboard' ? 'portfolio' : state.activeTab,
  );
  const setActiveTab = useAppStore((state) => state.setActiveTab);
  const contentRef = useRef<HTMLElement | null>(null);
  const scrollByTab = useRef<Record<string, number>>({});
  useTheme();
  useCoreBootstrap();
  const { applySubscriptions } = useMarketWebSocket();
  const subscribeSymbols = useAppStore((state) => state.subscribeSymbols);
  useEffect(() => {
    applySubscriptions(subscribeSymbols);
  }, [applySubscriptions, subscribeSymbols]);
  useKeyboardShortcuts(setActiveTab);

  useLayoutEffect(() => {
    const content = contentRef.current;
    if (!content) return undefined;
    content.scrollTop = scrollByTab.current[activeTab] ?? 0;
    const remember = () => {
      scrollByTab.current[activeTab] = content.scrollTop;
    };
    content.addEventListener('scroll', remember, { passive: true });
    return () => content.removeEventListener('scroll', remember);
  }, [activeTab]);

  return (
    <>
      {/*
        Fundo animated: 30 fps, DPR ate 1,5 e pausa fora do foco (05/10/2026).
        A densidade cai de 60 para 34 porque o custo por quadro e O(n^2) — as
        linhas de energia comparam todo par de particula. 60 particulas sao
        1770 comparacoes por quadro; 34 sao 561, um terco, e o campo visual
        continua cheio. Quem quiser o campo cheio antigo e so voltar a 60.
      */}
      <QuantumBackground density={34} speed={1} />
      <UserSessionGate>
        <AuthGate>
          <div className="app-shell">
            <Sidebar />
            <main className="main">
              <TopNav />
              <section ref={contentRef} className="content">
                {renderActiveTab(activeTab)}
              </section>
              {/* Barra de rodapé do app: ativo, timeframe e latência por
                  corretora. Fica DEPOIS de `.content`, fora do scroll, para
                  não subir e descer com a rolagem — e no lado direito, como no
                  MT5. Antes a latência ficava dentro da Mesa, o que a duplicava
                  por aba e a escondia de quem não estava no Robô. */}
              <StatusBar />
            </main>
          </div>
        </AuthGate>
      </UserSessionGate>
    </>
  );
}
