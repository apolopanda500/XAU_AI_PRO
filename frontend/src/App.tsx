import React, { useLayoutEffect, useRef } from 'react';
import { useAppStore, TabType } from './hooks/useAppStore';
import { useTheme } from './hooks/useTheme';
import { useCoreBootstrap } from './hooks/useCoreBootstrap';
import { useMarketWebSocket } from './hooks/useMarketWebSocket';
import AuthGate from './components/AuthGate';
import QuantumBackground from './components/QuantumBackground';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import PortfolioHomeClean from './components/tabs/PortfolioHomeSafe';
import UniversalLiveTerminal from './components/UniversalLiveTerminalLatest';
import RobotTableCommands from './components/RobotAssetTableFixed';
import RobotCommandActions from './components/RobotCommandActions';
import MarketTab from './components/tabs/MarketTab';
import RobotTab from './components/tabs/RobotWorkspaceTab';
import HistoryTab from './components/tabs/HistoryTab';
import SystemMonitorUniversalTab from './components/SystemHealthOnly';
import SettingsTab from './components/SettingsCoreSimple';
import ExitAppButton from './components/ExitAppButton';
import ConnectedDevicesPanel from './components/ConnectedDevicesPanel';
import AppIdentity from './components/AppIdentity';
import SystemStartupSync from './components/SystemStartupSync';
import ConnectionManager from './components/ConnectionSettings';
import StrategyTesterTab from './components/tabs/StrategyTesterTab';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

const TAB_COMPONENTS: Partial<Record<TabType, React.ReactNode>> = {
  portfolio: <PortfolioHomeClean />,
  market: <MarketTab />,
  robot: <><RobotTableCommands /><RobotCommandActions /><UniversalLiveTerminal /></>,
  history: <HistoryTab />,
  system: <SystemMonitorUniversalTab />,
  settings: <><ConnectionManager /><ConnectedDevicesPanel /><SettingsTab /><ExitAppButton /></>,
  'strategy-tester': <StrategyTesterTab />,
};

export default function App() {
  const activeTab = useAppStore((s) => s.activeTab === 'dashboard' ? 'portfolio' : s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const contentRef = useRef<HTMLElement | null>(null);
  const scrollByTab = useRef<Record<string, number>>({});
  useTheme();
  useCoreBootstrap();
  useMarketWebSocket();
  useKeyboardShortcuts(setActiveTab);

  useLayoutEffect(() => {
    const content = contentRef.current;
    if (!content) return;
    const remember = () => { scrollByTab.current[activeTab] = content.scrollTop; };
    content.addEventListener('scroll', remember, { passive: true });
    return () => content.removeEventListener('scroll', remember);
  }, [activeTab]);

  return (
    <>
      {/* Camada de fundo quântico com partículas e linhas de energia */}
      <QuantumBackground density={60} speed={1} />
      <SystemStartupSync />
      <AuthGate>
        <div className="app-shell">
          <Sidebar />
          <main className="main">
            <TopNav />
            <section ref={contentRef} className="content">
              {Object.entries(TAB_COMPONENTS).map(([tab, content]) => <div key={tab} style={{ display: activeTab === tab ? 'block' : 'none' }}>{content}</div>)}
            </section>
          </main>
        </div>
      </AuthGate>
    </>
  );
}
