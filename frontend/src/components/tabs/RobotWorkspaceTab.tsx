import RobotTab from './RobotTab';
import InventoryPanel from '../InventoryPanel';
import PortfolioTab from './PortfolioTab';
import OrderBookPanel from '../OrderBookPanel';

/** Terminal operacional universal para MT5, MEXC e Binance. */
export default function RobotWorkspaceTab() {
  return <div className="robot-workspace"><div className="card robot-live-banner"><div><strong>Terminal Operacional Universal</strong><span className="muted"> MT5 · MEXC · Binance · múltiplos ativos e contas</span></div><div className="btn-row"><span className="chip ok">Dados reais</span><span className="chip warn">Execução protegida</span></div></div><RobotTab /><InventoryPanel /></div>;
}
