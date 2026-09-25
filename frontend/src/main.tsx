import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { invoke } from '@tauri-apps/api/core';
import { queryClient } from './hooks/queries';
import { isMobileRuntime } from './lib/api';
import { installGatewayAuth, isTauri } from './lib/tauri';
import App from './App';
import './theme/global.css';
import './theme/market.css';

import './theme/asset-icons.css';
import './theme/exit.css';
import './theme/history-compact.css';
import './theme/portfolio-balance.css';
import './theme/dashboard-clean.css';
import './theme/robot-asset-table.css';
import './theme/robot-ticket.css';
import './theme/robot-quick.css';
import './theme/robot-terminal.css';
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
  metaViewport.setAttribute('content', 'width=device-width, initial-scale=1.0');
}

const root = document.getElementById('root');

async function waitForGateway() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    let retry = true;
    try {
      const response = await fetch('http://127.0.0.1:9001/api/health', {
        signal: AbortSignal.timeout(2000),
      });
      if (response.status === 401) {
        retry = false;
        throw new Error('gateway local nao autenticado');
      }
      const payload = await response.json() as {
        ok?: boolean;
        source?: string;
        gateway_build?: string;
      };
      if (response.ok && payload.ok === true
        && payload.source === 'mt5_gateway'
        && payload.gateway_build === 'xau-ai-pro-1.2.3-universal-20260918') return;
      retry = false;
      throw new Error('identidade do gateway local invalida');
    } catch (error) {
      if (!retry) throw error;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 500));
  }
  throw new Error('gateway local indisponivel');
}

async function bootstrap() {
  if (isTauri() && !isMobileRuntime()) {
    const token = await invoke<string>('gateway_token_command');
    if (!/^[a-f0-9]{64}$/.test(token)) throw new Error('token de sessao invalido');
    installGatewayAuth(token);
    await waitForGateway();
  }
  if (!root) throw new Error('elemento raiz indisponivel');
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>,
  );
}

void bootstrap().catch(() => {
  if (root) root.textContent = 'Falha ao inicializar o ambiente local seguro.';
});



