import { create } from 'zustand';

export type TabType =
  | 'dashboard'
  | 'market'
  | 'positions'
  | 'robot'
  | 'charts'
  | 'tools'
  | 'integrations'
  | 'settings'
  | 'strategy-tester'
  | 'robot-vision';

export interface Quote {
  symbol: string;
  price: number;
  bid: number;
  ask: number;
  last: number;
  volume: number;
  high: number;
  low: number;
  change: number;
  change_pct: number;
  spread: number;
  digits: number;
  point: number;
  timestamp: string;
  source: string;
}

export interface AccountInfo {
  login: string;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  leverage: string;
  server: string;
  currency: string;
  profit: number;
  trade_allowed: boolean;
}

export interface Position {
  ticket: number;
  symbol: string;
  side: string;
  volume: number;
  open_price: number;
  current_price: number;
  sl?: number;
  tp?: number;
  profit: number;
  swap: number;
  commission: number;
  open_time: string;
  magic: number;
  comment: string;
}

export interface Order {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  price: number;
  sl: number;
  tp: number;
  deviation: number;
  type_time: string;
  type_filling: string;
  comment: string;
}

export interface SystemState {
  status: string;
  uptime_sec: number;
  ws_clients: number;
  mt5_connected: boolean;
  ai_enabled: boolean;
  ai_age_sec: number;
  recent_events: number;
}

export interface AppState {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  quotes: Quote[];
  setQuotes: (quotes: Quote[]) => void;
  addQuote: (quote: Quote) => void;
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  connected: boolean;
  setConnected: (connected: boolean) => void;
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
  account: AccountInfo | null;
  setAccount: (account: AccountInfo | null) => void;
  positions: Position[];
  setPositions: (positions: Position[]) => void;
  orders: Order[];
  setOrders: (orders: Order[]) => void;
  systemState: SystemState | null;
  setSystemState: (state: SystemState) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  robotStatus: string;
  setRobotStatus: (status: string) => void;
  magicNumber: number;
  setMagicNumber: (magic: number) => void;
  aiStatus: string;
  setAiStatus: (status: string) => void;
  predictions: Record<string, any>;
  setPredictions: (predictions: Record<string, any>) => void;
  settings: Record<string, any>;
  setSettings: (settings: Record<string, any>) => void;
}

const initialSettings = {
  theme: 'xau_dark',
  animations: true,
  soundEnabled: true,
  notifications: true,
  autoScroll: true,
  precision: 2,
  refreshInterval: 1000,
  mt5Path: '',
  mt5AutoConnect: true,
  aiEnabled: true,
  aiModel: 'xau-pro-v2',
  aiInterval: 60,
};

export const useAppStore = create<AppState>((set, get) => ({
  activeTab: 'dashboard',
  setActiveTab: (tab) => set({ activeTab: tab }),
  quotes: [],
  setQuotes: (quotes) => set({ quotes }),
  addQuote: (quote) =>
    set((state) => {
      const filtered = state.quotes.filter((q) => q.symbol !== quote.symbol);
      return { quotes: [...filtered, quote] };
    }),
  selectedSymbol: 'XAUUSD',
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  connected: false,
  setConnected: (connected) => set({ connected }),
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
  account: null,
  setAccount: (account) => set({ account }),
  positions: [],
  setPositions: (positions) => set({ positions }),
  orders: [],
  setOrders: (orders) => set({ orders }),
  systemState: null,
  setSystemState: (state) => set({ systemState: state }),
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  robotStatus: 'Desconectado',
  setRobotStatus: (status) => set({ robotStatus: status }),
  magicNumber: 2026001,
  setMagicNumber: (magic) => set({ magicNumber: magic }),
  aiStatus: 'Inativo',
  setAiStatus: (status) => set({ aiStatus: status }),
  predictions: {},
  setPredictions: (predictions) => set({ predictions }),
  settings: initialSettings,
  setSettings: (settings) =>
    set((state) => ({ settings: { ...state.settings, ...settings } })),
}));
