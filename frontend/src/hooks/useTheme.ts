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

const WALLPAPER_CLASSES: Record<ThemeName, string> = {
  dark: 'wallpaper-quantum',
  xau_dark: 'wallpaper-xau',
  btc_dark: 'wallpaper-btc',
  light: 'wallpaper-quantum',
};

/**
 * Aplica o tema no <html> via data-theme e a classe de wallpaper no <body>.
 */
export function useTheme() {
  const themeName = useAppStore((s) => s.settings.theme) as string;

  useEffect(() => {
    const normalized = normalizeTheme(themeName);
    document.documentElement.setAttribute('data-theme', normalized);
    const body = document.body;
    Object.values(WALLPAPER_CLASSES).forEach((cls) => body.classList.remove(cls));
    body.classList.add(WALLPAPER_CLASSES[normalized]);
  }, [themeName]);
}

/** Le uma variavel CSS do tema atual (util para canvas, ex: graficos). */
export function cssVar(name: string, fallback = ''): string {
  if (typeof window === 'undefined') return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  return value || fallback;
}
