import React from 'react';
import { useAppStore, TabType } from './hooks/useAppStore';
import { useTheme } from './hooks/useTheme';
import { useCoreBootstrap } from './hooks/useCoreBootstrap';
import { useMarketWebSocket } from './hooks/useMarketWebSocket';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import DashboardTab from './components/tabs/DashboardTab';
import MarketTab from './components/tabs/MarketTab';
import PositionsTab from './components/tabs/PositionsTab';
import RobotTab from './components/tabs/RobotTab';
import ChartsTab from './components/tabs/ChartsTab';
import ToolsTab from './components/tabs/ToolsTab';
import IntegrationsTab from './components/tabs/IntegrationsTab';
import SettingsTab from './components/tabs/SettingsTab';
import StrategyTesterTab from './components/tabs/StrategyTesterTab';
import RobotVisionTab from './components/tabs/RobotVisionTab';

const TAB_COMPONENTS: Record<TabType, React.ReactNode> = {
  dashboard: <DashboardTab />,
  market: <MarketTab />,
  positions: <PositionsTab />,
  robot: <RobotTab />,
  charts: <ChartsTab />,
  tools: <ToolsTab />,
  integrations: <IntegrationsTab />,
  settings: <SettingsTab />,
  'strategy-tester': <StrategyTesterTab />,
  'robot-vision': <RobotVisionTab />,
};

export default function App() {
  const activeTab = useAppStore((s) => s.activeTab);
  useTheme();
  useCoreBootstrap();
  useMarketWebSocket();

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <TopNav />
        <section className="content">{TAB_COMPONENTS[activeTab] ?? TAB_COMPONENTS.dashboard}</section>
      </main>
    </div>
  );
}