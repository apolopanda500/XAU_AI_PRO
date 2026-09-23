import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type TabType =
  | 'dashboard'
  | 'portfolio'
  | 'market'
  | 'robot'
  | 'history'
  | 'system'
  | 'settings'
  | 'strategy-tester'
  | 'risk'
  | 'alert'
    | 'analytics'
  | 'calendar'
  | 'ai';

export type ThemeName = 'dark' | 'xau_dark' | 'btc_dark' | 'light' | 'ocean_dark' | 'emerald_dark' | 'rose_dark' | 'violet_dark';

export interface Quote {
  broker?: string;
  market?: string;
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
  received_at?: string;
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

export interface Settings {
  pinEnabled: boolean;
  pinCode: string;
  theme: ThemeName;
  animations: boolean;
  soundEnabled: boolean;
  notifications: boolean;
  autoScroll: boolean;
  precision: number;
  refreshInterval: number;
  dashboardAutoRefresh: boolean;
  marketAutoRefresh: boolean;
  historyAutoRefresh: boolean;
  dashboardRefreshMs: number;
  marketRefreshMs: number;
  historyRefreshMs: number;
  mt5Path: string;
  mt5AutoConnect: boolean;
  aiEnabled: boolean;
  aiModel: string;
  aiInterval: number;
  slackWebhook: string;
  slackActive: boolean;
  telegramToken: string;
  telegramChatId: string;
  telegramActive: boolean;
  discordWebhook: string;
  discordActive: boolean;
}

export const DEFAULT_MARKET_WATCHLIST = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY'];

const normalizeSymbols = (symbols: string[]): string[] => [...new Set(
  symbols.map((symbol) => String(symbol ?? '').trim().toUpperCase()).filter(Boolean),
)].slice(0, 24);

const quoteKey = (quote: Quote): string => [
  String(quote.broker ?? '').trim().toLowerCase(),
  String(quote.market ?? '').trim().toLowerCase(),
  String(quote.symbol ?? '').trim().toUpperCase(),
].join(':');

export const DEFAULT_SETTINGS: Settings = {
  pinEnabled: false,
  pinCode: '',
  theme: 'xau_dark',
  animations: true,
  soundEnabled: true,
  notifications: true,
  autoScroll: true,
  precision: 2,
  refreshInterval: 1000,
  dashboardAutoRefresh: true,
  marketAutoRefresh: true,
  historyAutoRefresh: true,
  dashboardRefreshMs: 5000,
  marketRefreshMs: 5000,
  historyRefreshMs: 10000,
  mt5Path: '',
  // MT5 nunca e iniciado pelo app; a conexao deve ser explicitamente acionada pelo usuario.
  mt5AutoConnect: false,
  aiEnabled: true,
  aiModel: 'xau-pro-v2',
  aiInterval: 60,
  slackWebhook: '',
  slackActive: false,
  telegramToken: '',
  telegramChatId: '',
  telegramActive: false,
  discordWebhook: '',
  discordActive: false,
};

interface AppState {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  quotes: Quote[];
  setQuotes: (quotes: Quote[]) => void;
  addQuote: (quote: Quote) => void;
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  // Lista de interesse do usuário. Persiste mesmo que nenhuma corretora esteja conectada.
  marketWatchlist: string[];
  setMarketWatchlist: (symbols: string[]) => void;
  // Símbolos que o painel de mercado quer receber em tempo real (watchlist + seleção).
  // Vazio = usa DEFAULT_SYMBOLS do protocolo.
  subscribeSymbols: string[];
  setSubscribeSymbols: (symbols: string[]) => void;
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
  settings: Settings;
  setSettings: (patch: Partial<Settings>) => void;
  resetSettings: () => void;
  onboardingDone: boolean;
  completeOnboarding: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      activeTab: 'portfolio',
      setActiveTab: (tab) => set({ activeTab: tab }),
      quotes: [],
      setQuotes: (quotes) => set({ quotes }),
      addQuote: (quote) =>
        set((state) => ({
          quotes: [...state.quotes.filter((q) => quoteKey(q) !== quoteKey(quote)), quote],
        })),
      // O produto é universal; XAUUSD é apenas uma opção do catálogo.
      selectedSymbol: '',
      setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
      marketWatchlist: DEFAULT_MARKET_WATCHLIST,
      setMarketWatchlist: (symbols) => set({ marketWatchlist: normalizeSymbols(symbols) }),
      subscribeSymbols: [],
      setSubscribeSymbols: (symbols) => set({ subscribeSymbols: normalizeSymbols(symbols) }),
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
      settings: DEFAULT_SETTINGS,
      setSettings: (patch) => set((state) => ({ settings: { ...state.settings, ...patch } })),
      resetSettings: () => set({ settings: DEFAULT_SETTINGS }),
      onboardingDone: false,
      completeOnboarding: () => set({ onboardingDone: true }),
    }),
    {
      name: 'xau-ai-pro',
      partialize: (state) => ({
        activeTab: state.activeTab,
        selectedSymbol: state.selectedSymbol,
        marketWatchlist: state.marketWatchlist,
        subscribeSymbols: state.subscribeSymbols,
        settings: state.settings,
        sidebarOpen: state.sidebarOpen,
        onboardingDone: state.onboardingDone,
      }),
      // Mescla defaults com settings persistidos (garante chaves novas apos atualizacao)
      merge: (persisted, current) => {
        const p = (persisted ?? {}) as Partial<AppState>;
        return {
          ...current,
          ...p,
          // Mantem a navegacao acessivel apos a troca do asset da marca.
          sidebarOpen: true,
          marketWatchlist: normalizeSymbols(p.marketWatchlist ?? current.marketWatchlist),
          subscribeSymbols: normalizeSymbols(p.subscribeSymbols ?? current.subscribeSymbols),
          // Compatibilidade segura: versoes antigas podiam persistir auto-connect=true.
          // A inicializacao do MT5 exige acao explicita do usuario.
          settings: { ...DEFAULT_SETTINGS, ...(p.settings ?? {}), marketAutoRefresh: true, mt5AutoConnect: false },
        } as AppState;
      },
    },
  ),
);
