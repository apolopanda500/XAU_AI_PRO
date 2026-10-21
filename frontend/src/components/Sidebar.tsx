import { useAppStore, type TabType } from '../hooks/useAppStore';
import { QuantumIcon, type IconName } from './QuantumIcon';
/*
  `APP_VERSION` SAIU DAQUI (06/10/2026).

  O rodape escrevia `Versao 1.2.4` em texto e o dono mandou trocar o texto
  inteiro pelo simbolo. A versao continua numa fonte de verdade — `src/version.ts`,
  gerado de `Docs/version.json`, e lido por `DeclaracoesConfianca` e pelo
  bootstrap. Tirar do rodape nao tirou do produto.
*/

const ITEMS: Array<[TabType, string, IconName]> = [
  // Operar concentra o posto de operação: automático ON/OFF, posições ao vivo,
  // ordem manual, sinal do modelo, EA e copiloto. As abas Mercado,
  // Inteligência Artificial e Risco saíram de fora de propósito.
  ['robot', 'ROBÔ', 'robot'],
  ['portfolio', 'Carteira', 'wallet'],

  // Performance & Analytics foi fundida no Histórico.
  ['history', 'Histórico', 'history'],
  ['calendar', 'Calendário', 'calendar'],

  // VIPS REMOVIDO DA NAVEGACAO (05/10/2026)
  // ==========================================
  // O dono pediu para remover: "ok abas vips nao funcionar qualquer remover
  // deletar".
  //
  // A tela lia `/api/vip/progress`, que mede volume por `audit.jsonl`. Em
  // 05/10/2026 a medicao era IMPOSSIVEL: o `audit_log` nao gravava `volume`, e
  // todo evento de ordem era descartado na leitura. Depois de corrigido o
  // produtor, a escada sobe por volume REAL de operacao — que nao e a mesma
  // coisa que nivel de conta da corretora, e o nome "VIPS" prometia a segunda.
  //
  // DEIXA DE EXISTIR: a aba, o `VipsTab.tsx`, o teste, o CSS, o icone e a rota
  // do tipo de aba. O backend (`vip_progress`, `metas_vip`, `/api/acesso`)
  // CONTINUA no lugar: ele e lido pelo `plano_gate` e pelo `acesso`, e apagar
  // la quebraria o portao de plano que o resto do app usa.
  //
  // A rota do tipo fica valida no store para quem tiver `'vips'` gravado no
  // `localStorage`; sem entrada na lista, ela nunca aparece.

  ['system', 'Sistema', 'system'],
  ['settings', 'Configuração', 'settings'],
];

export default function Sidebar() {
  const active = useAppStore((state) =>
    state.activeTab === 'dashboard' ? 'portfolio' : state.activeTab,
  );
  const setActive = useAppStore((state) => state.setActiveTab);
  const open = useAppStore((state) => state.sidebarOpen);
  const setOpen = useAppStore((state) => state.setSidebarOpen);
  return (
    <aside className={`sidebar ${open ? '' : 'collapsed'}`} aria-label="Navegação principal">
      <div className="brand">
        <img className="brand-mark brand-image" src="/xau-ai-pro-mark.png" alt="XAU AI PRO" />
        {open && <span className="brand-name">XAU AI PRO</span>}
        <button
          type="button"
          className="btn ghost sm collapse-btn"
          title={open ? 'Recolher' : 'Expandir'}
          aria-label={open ? 'Recolher menu' : 'Expandir menu'}
          onClick={() => setOpen(!open)}
        >
          {open ? '‹' : '›'}
        </button>
      </div>
      <nav className="nav-list">
        {ITEMS.map(([key, label, icon]) => (
          <button
            key={key}
            type="button"
            className={`nav-item ${active === key ? 'active' : ''}`}
            aria-label={label}
            aria-current={active === key ? 'page' : undefined}
            onClick={() => setActive(key)}
            title={label}
          >
            <QuantumIcon name={icon} size={24} glow={active === key} />
            {open && <span className="nav-label">{label}</span>}
          </button>
        ))}
      </nav>
      {/*
        O CARIMBO NO RODAPE (06/10/2026)
        ================================
        MEDIDO no app instalado: o rodape escrevia `XAU AI PRO · Operacao
        segura` e `Versao 1.2.4` em texto. O dono pediu para sair o texto e
        ficar o simbolo.

        A RAZAO DE O TEXTO SER PREJUDICIAL NAO ESTETICA
        ================================================
        `Operacao segura` e um rotulo sobre o que o app FAZ, e o app nao tem o
        que sustentar a frase: enquanto a ordem pelo grafico nao existia, o
        `Auto` desligado ficava sem SL/TP e a tela dizia `AUTO NAO`. Um rotulo
        que promete protecao que a tela nao mostra e pior que rotulo nenhum — o
        operador acredita que esta protegido e nao esta. E a regra do AGENTS.md
        9: um controle que nada mede e enfeite.

        A imagem e a MESMA do topo (`/xau-ai-pro-mark.png`). Duas copias do mesmo
        arquivo em dois lugares da tela seria duas coisas para atualizar, e a
        segunda envelhece sem ninguem perceber.

        `alt` com o nome e o que o leitor de tela le: uma imagem sem `alt` some
        da navegacao por leitor de tela, e o rodape ficaria sem nada.
      */}
      {open && (
        <div className="sidebar-footer">
          <img className="sidebar-stamp" src="/xau-ai-pro-mark.png" alt="XAU AI PRO" />
        </div>
      )}
    </aside>
  );
}
