import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { normalizeSymbols } from '../lib/constants';

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
  | 'ai'
  | 'vips';

export type ThemeName =
  | 'dark'
  | 'xau_dark'
  | 'btc_dark'
  | 'light'
  | 'ocean_dark'
  | 'emerald_dark'
  | 'rose_dark'
  | 'violet_dark';

// Sub-aba ativa dentro da aba Operar. Persiste para que sair e voltar nao
// empurre o operador de volta para o topo da pilha.
//
// OPERAR PRIMEIRO
// ===============
// O app e um desk de operacao: o operador abre para operar. A primeira
// sub-aba e "Operar" e junta o que a mao usa todo dia — o ON/OFF do motor
// automatico, as posicoes ao vivo (Mini Terminal) e a mesa de ordem manual.
// As pecas sao as mesmas telas de sempre, apenas reunidas: nenhum componente
// novo, nenhuma funcao nova.
//   Operar   → automatico ligado?, posicoes abertas, comprar/vender a mercado
//   Sinal    → qual ativo usar, qual modelo roda e o que ele prevê
//   EA       → o que existe no terminal MT5, heartbeat e comandos
//   Copiloto → conversa e achados do EA
// A aba ROBÔ virou UMA SÓ em 2026-09-29.
//
// Antes: 'operar' | 'sinal' | 'ea' (+ 'copiloto', removido por nao ser IA — o
// `backend/copilot.py` classifica a pergunta por regex e devolve template).
// Separar "Sinal" e "EA" obrigava o operador a trocar de tela para responder
// "qual ativo e modelo?" e "quanto posso arriscar?" — duas perguntas que
// precisam da mesma resposta na mesma hora.
//
// O tipo continua com um unico valor porque o `localStorage` de quem usou as
// versoes antigas ainda guarda 'sinal'/'ea'; `LEGADO_ROBOT_SUB` mapeia tudo
// para 'operar', entao ninguem fica preso numa aba que nao existe mais.
export type RobotSub = 'mesa' | 'acompanhar';
export const ROBOT_SUBS: RobotSub[] = ['mesa', 'acompanhar'];

// Nomes antigos persistidos no localStorage de quem usou as versoes de quatro
// e cinco sub-abas. TODOS caem em 'operar', que e a unica aba que existe
// agora: sem este mapa, trocar de versao deixaria o operador preso num
// `robotSub` que nao e mais valido e a tela apareceria vazia.
// Exportado porque o teste de RobotTabs fixa a correspondencia.
export const LEGADO_ROBOT_SUB: Record<string, RobotSub> = {
  modelo: 'mesa',
  ativos: 'mesa',
  sinal: 'acompanhar',
  ea: 'mesa',
  copiloto: 'acompanhar',
  operacao: 'mesa',
  operar: 'mesa',
  ordem: 'mesa',
  automacao: 'mesa',
  auto: 'mesa',
  mesa: 'mesa',
  risco: 'mesa',
  guardian: 'mesa',
};

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
  telegramToken: string;
  telegramChatId: string;
  telegramActive: boolean;
  discordWebhook: string;
  discordActive: boolean;
}

// Watchlist e normalizacao vem de lib/constants.ts (fonte unica). Antes eram
// listas locais duplicadas que comecavam em BTCUSDT.
// Nao ha mais watchlist fixa no codigo. A lista nasce vazia e o operador
// escolhe o que assinar; DEFAULT_MARKET_WATCHLIST fica como alias vazio
// para nao quebrar consumidores antigos.
export const DEFAULT_MARKET_WATCHLIST: readonly string[] = [];

const quoteKey = (quote: Quote): string =>
  [
    String(quote.broker ?? '')
      .trim()
      .toLowerCase(),
    String(quote.market ?? '')
      .trim()
      .toLowerCase(),
    String(quote.symbol ?? '')
      .trim()
      .toUpperCase(),
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
  robotSub: RobotSub;
  setRobotSub: (sub: RobotSub) => void;
  // Lista de interesse do usuário. Persiste mesmo que nenhuma corretora esteja conectada.
  marketWatchlist: string[];
  setMarketWatchlist: (symbols: string[]) => void;
  // Símbolos que o painel de mercado quer receber em tempo real (watchlist + seleção).
  // Vazio = o Core nao recebe assinatura ate o operador escolher.
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
      activeTab: 'robot',
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
      // A aba ROBO abre na Mesa; as sub-abas dividem o espaco.
      robotSub: 'mesa',
      setRobotSub: (sub) => set({ robotSub: sub }),
      marketWatchlist: [],
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
        robotSub: state.robotSub,
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
          settings: {
            ...DEFAULT_SETTINGS,
            ...(p.settings ?? {}),
            marketAutoRefresh: true,
            mt5AutoConnect: false,
          },
          // Valor persistido de uma versao antiga ou corrompido cai na primeira
          // sub-aba; os nomes da versao de cinco viram os quatro novos.
          robotSub: (() => {
            const salvo = String(p.robotSub ?? '');
            const legado = LEGADO_ROBOT_SUB[salvo] as RobotSub | undefined;
            if (legado) return legado;
            return ROBOT_SUBS.includes(salvo as RobotSub) ? (salvo as RobotSub) : 'mesa';
          })(),
        } as AppState;
      },
    },
  ),
);
