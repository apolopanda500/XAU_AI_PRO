import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { useAppStore, type TabType } from './hooks/useAppStore';
import { useTheme } from './hooks/useTheme';
import { useCoreBootstrap } from './hooks/useCoreBootstrap';
import { useMarketWebSocket } from './hooks/useMarketWebSocket';
import AuthGate from './components/AuthGate';
import QuantumBackground from './components/QuantumBackground';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import PortfolioHomeClean from './components/tabs/PortfolioHomeSafe';
import MarketTab from './components/tabs/MarketTab';
import RobotTableCommands from './components/RobotAssetTableFixed';
import RobotCommandActions from './components/RobotCommandActions';
import GuardianManager from './components/GuardianManager';
import DemoOrderPanel from './components/DemoOrderPanel';
import UniversalLiveTerminal from './components/UniversalLiveTerminalLatest';
import HistoryTab from './components/tabs/HistoryTab';
import SystemMonitorUniversalTab from './components/SystemHealthOnly';
import SettingsTab from './components/SettingsCoreSimple';
import SubscriptionPanel from './components/SubscriptionPanel';
import ExitAppButton from './components/ExitAppButton';
import ConnectedDevicesPanel from './components/ConnectedDevicesPanel';
import SystemStartupSync from './components/SystemStartupSync';
import ConnectionManager from './components/ConnectionSettings';
import StrategyTesterTab from './components/tabs/StrategyTesterTab';
import RiskTab from './components/tabs/RiskTab';
import AlertTab from './components/tabs/AlertTab';
import AIControlTab from './components/tabs/AIControlTab';
import AnalyticsTab from './components/tabs/AnalyticsTab';
import EconomicCalendarTab from './components/tabs/EconomicCalendarTab';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

function renderActiveTab(tab: TabType): ReactNode {
  switch (tab) {
    case 'portfolio': return <PortfolioHomeClean />;
    case 'market': return <MarketTab />;
    case 'robot': return <><RobotTableCommands /><RobotCommandActions /><DemoOrderPanel /><GuardianManager /><UniversalLiveTerminal /></>;
    case 'history': return <HistoryTab />;
    case 'system': return <SystemMonitorUniversalTab />;
    case 'settings': return <><ConnectionManager /><ConnectedDevicesPanel /><SubscriptionPanel /><SettingsTab /><ExitAppButton /></>;
    case 'strategy-tester': return <StrategyTesterTab />;
    case 'risk': return <RiskTab />;
    case 'alert': return <AlertTab />;
    case 'analytics': return <AnalyticsTab />;
    case 'calendar': return <EconomicCalendarTab />;
    case 'ai': return <AIControlTab />;
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
    <SystemStartupSync />
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
  </>;
}
