import { useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { invoke } from '@tauri-apps/api/core';

export default function ExitAppButton() {
  const [closing, setClosing] = useState(false);
  const exit = async () => {
    if (closing) return;
    setClosing(true);
    try { await invoke('exit_app'); } catch { try { await getCurrentWindow().close(); } catch { setClosing(false); } }
  };
  return <div className="card compact-card exit-app-card"><button type="button" className="btn danger exit-app-button" onClick={() => void exit()} disabled={closing}>{closing ? 'Fechando…' : '⏻ Sair do aplicativo'}</button></div>;
}
