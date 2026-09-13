import { useState, useEffect } from 'react';

export interface Theme {
  bg: string;
  bgSecondary: string;
  panel: string;
  card: string;
  cardHover: string;
  border: string;
  borderAccent: string;
  primary: string;
  primaryHover: string;
  accent: string;
  success: string;
  danger: string;
  warning: string;
  text: string;
  textSecondary: string;
  textMuted: string;
  bid: string;
  ask: string;
}

const darkTheme: Theme = {
  bg: '#0a0b0e',
  bgSecondary: '#0d1117',
  panel: '#101720',
  card: '#151d28',
  cardHover: '#1a2635',
  border: '#243244',
  borderAccent: '#00c6fb',
  primary: '#00c6fb',
  primaryHover: '#33d4ff',
  accent: '#ff8c00',
  success: '#00c853',
  danger: '#ff3d57',
  warning: '#ffb300',
  text: '#f0f2f5',
  textSecondary: '#9ca9bd',
  textMuted: '#68778c',
  bid: '#00c853',
  ask: '#ff3d57',
};

const xauTheme: Theme = {
  bg: '#0c0a05',
  bgSecondary: '#12100a',
  panel: '#18150e',
  card: '#221e14',
  cardHover: '#2a2519',
  border: '#3a3220',
  borderAccent: '#ffc94d',
  primary: '#ffc94d',
  primaryHover: '#ffe08a',
  accent: '#ff7300',
  success: '#4ade80',
  danger: '#ff4d6a',
  warning: '#ffb347',
  text: '#f5f0e8',
  textSecondary: '#c2b89e',
  textMuted: '#7a7060',
  bid: '#4ade80',
  ask: '#ff4d6a',
};

const btcTheme: Theme = {
  bg: '#070b0f',
  bgSecondary: '#0d1420',
  panel: '#121c2e',
  card: '#162236',
  cardHover: '#1d2c44',
  border: '#253553',
  borderAccent: '#00e676',
  primary: '#00e676',
  primaryHover: '#69f0ae',
  accent: '#ffd740',
  success: '#00e676',
  danger: '#ff5252',
  warning: '#ffd740',
  text: '#eef4ff',
  textSecondary: '#90a4c4',
  textMuted: '#54688d',
  bid: '#00e676',
  ask: '#ff5252',
};

const themes: Record<string, Theme> = { dark: darkTheme, xau_dark: xauTheme, btc_dark: btcTheme };

export function useTheme(themeName: string = 'dark') {
  const [currentTheme, setCurrentTheme] = useState<Theme>(themes[themeName] || darkTheme);

  useEffect(() => {
    setCurrentTheme(themes[themeName] || darkTheme);
  }, [themeName]);

  return { theme: currentTheme, setTheme: setCurrentTheme };
}
