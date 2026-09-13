import { useEffect } from 'react';
import { useAppStore } from './useAppStore';

export type ThemeName = 'dark' | 'xau_dark' | 'btc_dark' | 'light';

export const THEMES: { id: ThemeName; label: string }[] = [
  { id: 'dark', label: 'Dark (Padrao)' },
  { id: 'xau_dark', label: 'XAU Dark' },
  { id: 'btc_dark', label: 'BTC Dark' },
  { id: 'light', label: 'Light' },
];

const VALID: ThemeName[] = ['dark', 'xau_dark', 'btc_dark', 'light'];

export function normalizeTheme(name: string): ThemeName {
  return (VALID.includes(name as ThemeName) ? name : 'dark') as ThemeName;
}

/**
 * Aplica o tema selecionado no elemento raiz via atributo data-theme.
 * As variaveis CSS (--bg, --primary, etc.) sao definidas no global.css.
 */
export function useTheme() {
  const themeName = useAppStore((s) => s.settings.theme) as string;

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', normalizeTheme(themeName));
  }, [themeName]);
}

/** Le uma variavel CSS do tema atual (util para canvas, ex: graficos). */
export function cssVar(name: string, fallback = ''): string {
  if (typeof window === 'undefined') return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  return value || fallback;
}
