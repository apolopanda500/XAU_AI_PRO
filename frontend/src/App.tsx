import React from 'react';
import { useAppStore, TabType } from './hooks/useAppStore';
import { useTheme } from './hooks/useTheme';
import { useCoreBootstrap } from './hooks/useCoreBootstrap';
import { useMarketWebSocket } from './hooks/useMarketWebSocket';
import AuthGate from './components/AuthGate';
import QuantumBackground from './components/QuantumBackground';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import DashboardTab from './components/tabs/DashboardTab';
import MarketTab from './components/tabs/MarketTab';
import RobotTab from './components/tabs/RobotTab';
import HistoryTab from './components/tabs/HistoryTab';
import EconomicCalendarTab from './components/tabs/EconomicCalendarTab';
import SystemMonitorTab from './components/tabs/SystemMonitorTab';
import SettingsTab from './components/tabs/SettingsTab';
import StrategyTesterTab from './components/tabs/StrategyTesterTab';
import MiniInfoWidget from './components/MiniInfoWidget';

const TAB_COMPONENTS: Record<TabType, React.ReactNode> = {
  dashboard: <DashboardTab />,
  market: <MarketTab />,
  robot: <RobotTab />,
  history: <HistoryTab />,
  calendar: <EconomicCalendarTab />,
  system: <SystemMonitorTab />,
  settings: <SettingsTab />,
  'strategy-tester': <StrategyTesterTab />,
};

export default function App() {
  const activeTab = useAppStore((s) => s.activeTab);
  useTheme();
  useCoreBootstrap();
  useMarketWebSocket();

  return (
    <>
      {/* Camada de fundo quântico com partículas e linhas de energia */}
      <QuantumBackground density={60} speed={1} />
      <AuthGate>
        <div className="app-shell">
          <Sidebar />
          <main className="main">
            <TopNav />
            <MiniInfoWidget />
            <section className="content">{TAB_COMPONENTS[activeTab] ?? TAB_COMPONENTS.dashboard}</section>
          </main>
        </div>
      </AuthGate>
    </>
  );
}

