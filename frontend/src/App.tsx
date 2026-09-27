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
import SubscriptionPanel from './components/SubscriptionPanel';
import ExitAppButton from './components/ExitAppButton';
import ConnectedDevicesPanel from './components/ConnectedDevicesPanel';
import ConnectionSettings from './components/ConnectionSettings';
import RiskTab from './components/tabs/RiskTab';
import AlertTab from './components/tabs/AlertTab';
import AnalyticsTab from './components/tabs/AnalyticsTab';
import EconomicCalendarTab from './components/tabs/EconomicCalendarTab';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

function renderActiveTab(tab: TabType): ReactNode {
  switch (tab) {
    case 'portfolio': return <PortfolioHome />;
    // Robô é o posto de operação: sinal do modelo, operação automática, ordem
    // manual, posições ao vivo, gestão por posição, EA e o copiloto que explica
    // tudo isso. Mercado, Inteligência Artificial e Risco saíram de abas
    // próprias e vieram para cá — a inferência só tem utilidade quando o
    // comando para agir na sequência está no mesmo lugar.
    case 'robot': return <><RobotModelPanel /><AutoEnginePanel /><DemoOrderPanel /><UniversalLiveTerminal /><RiskTab /><CopilotPanel /><GuardianManager /><RobotAssetTable /></>;
    // Performance & Analytics foi fundida no Histórico: as duas telas
    // analisam a mesma coisa — as operações realizadas.
    case 'history': return <><HistoryTab /><AnalyticsTab /></>;
    case 'system': return <SystemHealth />;
    case 'settings': return <><ConnectionSettings /><ConnectedDevicesPanel /><SubscriptionPanel /><SettingsCore /><ExitAppButton /></>;
    case 'alert': return <AlertTab />;
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
