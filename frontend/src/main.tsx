import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './hooks/queries';
import App from './App';
import './theme/global.css';
import './theme/asset-icons.css';
import './theme/exit.css';
import './theme/history-compact.css';
import './theme/portfolio-balance.css';
import './theme/dashboard-clean.css';
import './theme/robot-asset-table.css';
import './theme/robot-ticket.css';
import './theme/robot-quick.css';
import './theme/robot-terminal-compact.css';
import './theme/robot-terminal-clean.css';
import './theme/robot-terminal-dedup.css';
import './theme/robot-no-warnings.css';
import './theme/robot-clean-messages.css';
import './theme/quantum.css';
import './theme/wallpapers.css';
import './theme/mining.css';
import './theme/clock.css';
import './theme/mini-info.css';
import './theme/level1.css';
import './theme/guardian.css';


// Ajusta para Tauri (mobile viewport)
const metaViewport = document.querySelector('meta[name="viewport"]');
if (metaViewport) {
  metaViewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);







