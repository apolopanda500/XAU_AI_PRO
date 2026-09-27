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
import AutoEnginePanel from './components/AutoEnginePanel';
import RobotModelPanel from './components/RobotModelPanel';
import CopilotPanel from './components/CopilotPanel';
import RobotAssetTable from './components/RobotAssetTableFixed';
import GuardianManager from './components/GuardianManager';
import DemoOrderPanel from './components/DemoOrderPanel';
import UniversalLiveTerminal from './components/UniversalLiveTerminalLatest';
import HistoryTab from './components/tabs/HistoryTab';
import SystemHealth from './components/SystemHealthOnly';
import SettingsCore from './components/SettingsCoreSimple';
import ExitAppButton from './components/ExitAppButton';
import RiskTab from './components/tabs/RiskTab';
import AnalyticsTab from './components/tabs/AnalyticsTab';
import EconomicCalendarTab from './components/tabs/EconomicCalendarTab';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

function renderActiveTab(tab: TabType): ReactNode {
  switch (tab) {
    case 'portfolio': return <PortfolioHome />;
    // Ordem pensada para o uso: primeiro o que orienta a decisão (modelo e
    // operação automática), depois o que executa (ordem), depois o resultado
    // (risco e posições). O Mini Terminal fica NO FIM de propósito: ele é
    // conferência, não comando. No meio da aba ele empurrava a gestão para
    // baixo da dobra e o operador lia o resultado antes de decidir.
    case 'robot': return <><RobotModelPanel /><AutoEnginePanel /><DemoOrderPanel /><RiskTab /><GuardianManager /><RobotAssetTable /><CopilotPanel /><UniversalLiveTerminal /></>;
    // Performance & Analytics foi fundida no Histórico: as duas telas
    // analisam a mesma coisa — as operações realizadas.
    case 'history': return <><HistoryTab /><AnalyticsTab /></>;
    case 'system': return <SystemHealth />;
    case 'settings': return <><SettingsCore /><ExitAppButton /></>;
    case 'calendar': return <EconomicCalendarTab />;
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
