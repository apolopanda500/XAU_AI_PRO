import { useEffect } from 'react';
import { useAppStore } from './useAppStore';

export type ThemeName =
  | 'dark'
  | 'dourado_dark'
  | 'light'
  | 'ocean_dark'
  | 'emerald_dark'
  | 'rose_dark';

export const THEMES: { id: ThemeName; label: string; desc: string }[] = [
  { id: 'dark', label: 'Dark (Padrao)', desc: 'Violeta profundo' },
  { id: 'dourado_dark', label: 'Dourado', desc: 'Fundo escuro com brilho dourado' },
  { id: 'light', label: 'Light', desc: 'Claro' },
  { id: 'ocean_dark', label: 'Ocean Dark', desc: 'Ciano profundo' },
  { id: 'emerald_dark', label: 'Emerald Dark', desc: 'Verde esmeralda' },
  { id: 'rose_dark', label: 'Rose Dark', desc: 'Rosé' },
];

const VALID: ThemeName[] = [...THEMES.map((t) => t.id)];

/**
 * Migracao dos IDs ANTIGOS, que tinham nome de ativo (09/10/2026).
 *
 * MEDIDO: os dois temas se chamavam `xau_dark` e `btc_dark` - apelidos de cor
 * com nome de ativo, que e o que a regra "nenhum nome de ativo no codigo"
 * proibe. `dourado_dark` herdou o papel de `xau_dark`. `laranja_dark` foi
 * removido em 13/11/2026, `btc_dark` migra para `dark`, e `violet_dark` foi
 * fundido com `dark` no mesmo dia (13/11/2026): quem tinha violet ve o tema
 * dark, e o mapa migra o ID para nao quebrar a preferencia salva.
 *
 * Sem este mapa, quem ja tinha escolhido um dos dois veria o tema voltar para
 * `dark` na proxima abertura: a preferencia esta no `localStorage` com o ID
 * velho, e `normalizeTheme` reprova o que nao conhece. Migrar e o oposto de
 * perder a escolha do operador por causa de uma limpeza de nome.
 */
const ANTIGOS: Record<string, ThemeName> = {
  xau_dark: 'dourado_dark',
  btc_dark: 'dark',
  laranja_dark: 'dark',
  violet_dark: 'dark',
};

export function normalizeTheme(name: string): ThemeName {
  const migrado = ANTIGOS[name] ?? name;
  return (VALID.includes(migrado as ThemeName) ? migrado : 'dark') as ThemeName;
}

const WALLPAPER_CLASSES: Record<ThemeName, string> = {
  dark: 'wallpaper-quantum',
  dourado_dark: 'wallpaper-dourado',
  light: 'wallpaper-quantum',
  ocean_dark: 'wallpaper-quantum',
  emerald_dark: 'wallpaper-quantum',
  rose_dark: 'wallpaper-quantum',
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
