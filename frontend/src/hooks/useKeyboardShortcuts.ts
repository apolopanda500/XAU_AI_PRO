import { useEffect } from 'react';
import type { TabType } from './useAppStore';

export function useKeyboardShortcuts(setActiveTab: (tab: TabType) => void) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
      if ((event.ctrlKey || event.metaKey) && event.key === ',') { event.preventDefault(); setActiveTab('settings'); }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'r') { event.preventDefault(); window.dispatchEvent(new CustomEvent('xau-refresh')); }
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'x') { event.preventDefault(); window.dispatchEvent(new CustomEvent('xau-emergency-request')); }
    };
    window.addEventListener('keydown', onKeyDown); return () => window.removeEventListener('keydown', onKeyDown);
  }, [setActiveTab]);
}
