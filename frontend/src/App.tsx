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
import VipsTab from './components/VipsTab';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

function renderActiveTab(tab: TabType): ReactNode {
  switch (tab) {
    case 'portfolio': return <PortfolioHome />;
    // A aba Operar tem quatro sub-abas (Operar | Sinal | EA | Copiloto) e
    // abre na primeira: motor automatico, posicoes ao vivo e ordem manual.
    // Cada painel segue dentro da sua barreira de erro: um painel que
    // falhasse desmontava a arvore React inteira e a aba ficava branca - o
    // usuario perdia o app sem saber qual era o culpado.
    case 'robot': return <RobotTabs />;
    // Performance & Analytics foi fundida no Histórico: as duas telas
    // analisam a mesma coisa — as operações realizadas.
    case 'history': return <HistoryTab />;
    case 'system': return <SystemHealth />;
    case 'settings': return <><SettingsCore /><ExitAppButton /></>;
    case 'calendar': return <EconomicCalendarTab />;
    // VIPS: progressao por volume, medida no audit.jsonl real. Fica separada
    // do plano (Free/VIP/VIPS) porque sao coisas diferentes: o plano e
    // preferencia local, o nivel aqui e conquistado operando.
    case 'vips': return <VipsTab />;
    default: return null;
  }
}

export default function App() {
  const activeTab = useAppStore((state) => state.activeTab === 'dashboard' ? 'portfolio' : state.activeTab);
  const setActiveTab = useAppStore((state) => state.setActiveTab);
  const contentRef = useRef<HTMLElement | null>(null);
  const scrollByTab = useRef<Record<string, number>>({});
  useTheme();
  useCoreBootstrap();
  const { applySubscriptions } = useMarketWebSocket();
  const subscribeSymbols = useAppStore((state) => state.subscribeSymbols);
  useEffect(() => { applySubscriptions(subscribeSymbols); }, [applySubscriptions, subscribeSymbols]);
  useKeyboardShortcuts(setActiveTab);

  useLayoutEffect(() => {
    const content = contentRef.current;
    if (!content) return undefined;
    content.scrollTop = scrollByTab.current[activeTab] ?? 0;
    const remember = () => { scrollByTab.current[activeTab] = content.scrollTop; };
    content.addEventListener('scroll', remember, { passive: true });
    return () => content.removeEventListener('scroll', remember);
  }, [activeTab]);

  return <>
    <QuantumBackground density={60} speed={1} />
    <UserSessionGate>
      <AuthGate>
        <div className="app-shell">
          <Sidebar />
          <main className="main">
            <TopNav />
            <section ref={contentRef} className="content">
              {renderActiveTab(activeTab)}
            </section>
          </main>
        </div>
      </AuthGate>
    </UserSessionGate>
  </>;
}
