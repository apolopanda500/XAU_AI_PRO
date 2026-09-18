import { useEffect } from 'react';
import { useAppStore } from './useAppStore';

export type ThemeName = 'dark' | 'xau_dark' | 'btc_dark' | 'light' | 'ocean_dark' | 'emerald_dark' | 'rose_dark' | 'violet_dark';

export const THEMES: { id: ThemeName; label: string; desc: string }[] = [
  { id: 'dark', label: 'Dark (Padrao)', desc: 'Azul elétrico' },
  { id: 'xau_dark', label: 'XAU Dark', desc: 'Dourado' },
  { id: 'btc_dark', label: 'BTC Dark', desc: 'Laranja' },
  { id: 'light', label: 'Light', desc: 'Claro' },
  { id: 'ocean_dark', label: 'Ocean Dark', desc: 'Ciano profundo' },
  { id: 'emerald_dark', label: 'Emerald Dark', desc: 'Verde esmeralda' },
  { id: 'rose_dark', label: 'Rose Dark', desc: 'Rosé' },
  { id: 'violet_dark', label: 'Violet Dark', desc: 'Violeta' },
];

const VALID: ThemeName[] = [...THEMES.map((t) => t.id)];

export function normalizeTheme(name: string): ThemeName {
  return (VALID.includes(name as ThemeName) ? name : 'dark') as ThemeName;
}

const WALLPAPER_CLASSES: Record<ThemeName, string> = {
  dark: 'wallpaper-quantum',
  xau_dark: 'wallpaper-xau',
  btc_dark: 'wallpaper-btc',
  light: 'wallpaper-quantum',
  ocean_dark: 'wallpaper-quantum',
  emerald_dark: 'wallpaper-quantum',
  rose_dark: 'wallpaper-quantum',
  violet_dark: 'wallpaper-quantum',
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
