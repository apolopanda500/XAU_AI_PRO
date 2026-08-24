# XAU AI PRO — Interface de Desktop & Automação

## ✨ Executável (2 cliques)
Compilado com PyInstaller (onefile), gera **`Ultimate/dist/XAU_AI_PRO_App.exe`** (~12 MB).
Abra com duplo clique — abre a GUI completa sem precisar de Python instalado.

```
Ultimate/dist/XAU_AI_PRO_App.exe
```

## Nova interface desktop (login + mercado em tempo real)
Tela de login, **11 abas**, login com hash SHA-256, mercado ao vivo (MT5/yfinance),
predições, conexão de API keys, integração MT5/Robô, treinamento, **assistente IA,
ferramentas do dia a dia, integrações externas, memória de pensamentos**, configurações.

**Uso (desenvolvimento):**
```
cd C:\Users\Micro\Downloads\XAU_AI_PRO\Ultimate
python run_app.py
```

**Login padrão:** `admin` / `admin`
(crie novos usuários na tela de login com *Cadastrar* ou na aba Configurações)

### Funcionalidades adicionadas
- **Wallpaper animado no login**: fundo com símbolos de criptomoedas, robôs IA e
  partículas animadas. Pode ser desativado em Configurações → Interface.
- **5 temas visuais**: dark, light, cyberpunk, crypto, midnight.
  Aba Configurações → "Tema" → "Aplicar tema".
- **Lembrar sessão**: checkbox na tela de login (auto-login ao abrir o app).
- **Aba MT5 / Robô**: conectar/desconectar/testar o terminal MT5, iniciar/parar/verificar
  o robô EA XAU AI PRO, tudo sincronizado com a conta logada.
- **Auto-treinamento agendado**: aba Treinamento → "Auto-treinamento" com intervalo
  em minutos (roda em segundo plano) + relatório automático em `Reports/`.
- **Sincronização MT5**: o módulo `mt5_integration.py` reusa a sessão logada do
  terminal (sem pedir senha) para obter conta, posições e status do robô.
- **Assistente IA com memória**: aba "Assistente IA" — converse com o assistente,
  o histórico fica salvo no SQLite. Suporta LiteLLM Proxy (porta 4000) e fallback
  local. É possível exportar a conversa para arquivo.
- **Ferramentas do dia a dia**: aba "Ferramentas" — calculadora de lote,
  relógio mundial, status das sessões de Forex e calendário econômico resumido.
- **Integrações externas**: aba "Integrações" — GitHub (listar repos), Figma
  (listar projetos) e Brave Search (busca web). Tokens salvos em `config.json`.
- **Memória / pensamentos**: aba "Memória" — salve ideias, estratégias e notas
  diárias no banco SQLite, com tags e exclusão.

## Launcher de serviços (versão antiga, corrigida)
Sobe backend (8000), dashboard Streamlit (8501) e abre o navegador.
Os erros agora vão para `Logs/backend.log` e `Logs/dashboard.log` (não mais invisíveis).

```
python launcher.py
```

## Scripts de automação ("auto-approve")
Os scripts abaixo executam o fluxo **treinar → predizer → validar → relatório**
sem intervenção manual:

```
# Executa uma vez e grava Reports/auto_approve_<data>.json
python auto_engine.py

# Executa em loop contínuo (atualiza predições periodicamente)
python auto_watch.py

# Agendador do Windows (roda a cada X minutos) - execute como Admin
instalar_agendador.bat
```

Os relatórios ficam em `Reports/auto_approve_*.json`.

## API Backend (FastAPI)
```
python ../Python/backend/api.py        # http://127.0.0.1:8000/docs
```
Endpoints: `/`, `/prediction/{symbol}`, `/predictions`, `/account`,
`/market/live`, `/market/live/{symbol}`, `/login`, `/train`, `/predict`.

## Arquivos novos nesta entrega (em Ultimate/)
| Arquivo | Função |
|---|---|
| `run_app.py` | Entry point da GUI |
| `gui.py` | Interface desktop (login + 11 abas + tema + MT5 + IA) |
| `config_store.py` | Config, API keys e autenticação (hash) |
| `market_live.py` | Cotações em tempo real (MT5 + yfinance) |
| `mt5_integration.py` | Bridge MT5 (conta, posições, robô) |
| `themes.py` | Engine de temas (5 temas) |
| `wallpaper.py` | Wallpaper animado de cripto/IA |
| `assistant.py` | Assistente IA com memória persistente |
| `daily_tools.py` | Calculadora de lote, relógio mundial, calendário |
| `integrations.py` | Clientes GitHub, Figma e Brave Search |
| `auto_engine.py` | Auto-approve (treinar→predizer→validar→relatório) |
| `auto_watch.py` | Loop contínuo do auto-approve |
| `launcher.py` | Launcher de serviços corrigido |
| `instalar_agendador.bat` | Cria tarefa agendada do Windows |
| `launcher.spec` | Spec do PyInstaller (onefile) |

## Próximos passos para a IA ficar confiável
O dataset real tem **apenas 72 amostras** (13–21/07, 6 símbolos). O `train.py`
exige **mínimo de 500 amostras** para gerar modelo — então hoje **não há
treinamento válido**. É preciso rodar o EA em **demo** por algumas semanas
para acumular dados, depois rodar `Treinar modelos` na GUI.
