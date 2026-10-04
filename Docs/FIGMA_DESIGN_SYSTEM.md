# Design System do XAU AI PRO na Figma — roteiro de montagem

> Este documento diz **exatamente** o que criar na Figma para o app passar a
> gerar o CSS a partir dela. Os valores sao os **reais do código**, medidos em
> `frontend/src/theme/global.css` em 04/10/2026 — nada aqui é sugestão.

## Como isso funciona

```
Figma (fonte)  ->  scripts/sincronizar_figma.py  ->  figma-tokens.css  ->  app
```

O script **só escreve o que existe na Figma**. O que não estiver lá continua
vindo do `global.css`. Então dá para montar aos poucos, sem quebrar nada.

Comandos:

```powershell
.\.venv\Scripts\python.exe scripts\sincronizar_figma.py            # mostra o que leu
.\.venv\Scripts\python.exe scripts\sincronizar_figma.py --aplicar  # gera o CSS
.\.venv\Scripts\python.exe scripts\sincronizar_figma.py --verificar # CI: diverge?
```

## Estado medido hoje (04/10/2026)

| Leitura | Resultado |
|---|---|
| Identidade | Henrique Carvalho |
| Arquivo | XAU AI PRO |
| Componentes publicados | **0** |
| Estilos publicados | **0** |
| Variáveis | **bloqueado** — exige plano Professional |

Ou seja: o arquivo existe e é acessível, mas **não há design system dentro**.

## Passo 1 — Estilos de cor (funciona no plano atual)

Vá em **Styles → + → Color**. Crie estes nomes **exatos** (o script casa pelo
nome). São os papéis, não os valores por tema:

| Nome do estilo | Papel no CSS | Onde é usado |
|---|---|---|
| `bg` | fundo da app | fundo geral |
| `panel` | painel | cartão, seção |
| `panel2` | painel elevado | hover, tabela zebra |
| `border` | borda | divisória, contorno |
| `text` | texto principal | leitura |
| `muted` | texto secundário | rótulo, legenda |
| `primary` | cor de ação | botão primário, aba ativa |
| `primary-contrast` | texto sobre `primary` | botão primário |
| `ok` | positivo | lucro, conectado |
| `warn` | atenção | latência média |
| `danger` | negativo | perda, offline |

Valores do tema `dark` (o padrão atual) para você não ter que adivinhar:

```
bg               #0f1420      primary          #4f7cff
panel            #161d2d      primary-contrast #ffffff
panel2           #1c2437      ok               #22c55e
border           #26314a      warn             #eab308
text             #e8ecf5      danger           #ef4444
muted            #8b94ab
```

## Passo 2 — Componentes (funciona no plano atual)

Crie como **Component** e depois **Publish** (botão no canto superior direito).

| Componente | Por que |
|---|---|
| `Botao/Primario` | ação principal, alvo de 44px |
| `Botao/Perigo` | parar motor, fechar posição |
| `Botao/Fantasma` | ação secundária |
| `Chip/Status` | DEMO/REAL, conectado, EA viva |
| `Tabela/Cabecalho` | linha de cabeçalho fixa ao rolar |
| `Tabela/Linha` | linha com `--row-h-normal` |
| `Painel` | cartão com borda e raio |
| `Medidor/Latencia` | barra + número em ms |

## Passo 3 — Variáveis (exige plano Professional)

Vá em **Variables → +** e crie com estes nomes. O script converte
`cor/dark/bg` em `--bg` no `:root` e `--bg` dentro de `[data-theme="dark"]`.

**Cor** (uma variável por papel, com modos por tema):

```
cor/dark/bg          cor/xau/bg        cor/btc/bg       cor/light/bg
cor/dark/panel       cor/xau/panel     cor/btc/panel    cor/light/panel
... e o mesmo para panel2, border, text, muted, primary, primary-contrast
```

Os 8 modos do projeto e seus valores reais:

| Token | dark | xau | btc | light | ocean | emerald | rose | violet |
|---|---|---|---|---|---|---|---|---|
| `bg` | #0f1420 | #14100a | #0c0f14 | #f3f5f9 | #07141f | #071510 | #16070c | #0e0a1a |
| `panel` | #161d2d | #1d1810 | #13171f | #ffffff | #0d1c2b | #0d2019 | #220d15 | #171029 |
| `panel2` | #1c2437 | #241d13 | #191f2a | #f7f9fc | #122535 | #122a20 | #2b1220 | #1e1536 |
| `border` | #26314a | #3a2f1c | #2a3140 | #dbe2ec | #1d3a52 | #1d4434 | #471f30 | #2e2153 |
| `text` | #e8ecf5 | #f5ecd8 | #eef2f7 | #1c2433 | #e3f1fb | #e2f7ec | #f9e8ee | #ece6fa |
| `muted` | #8b94ab | #a89a7d | #93a0b4 | #5d6b82 | #7fa5c0 | #7db8a0 | #c08a9c | #a394cf |
| `primary` | #4f7cff | #f0b90b | #f7931a | #3554d1 | #22d3ee | #34d399 | #fb7185 | #a78bfa |
| `primary-contrast` | #ffffff | #1d1810 | #0c0f14 | #ffffff | #07141f | #071510 | #16070c | #0e0a1a |

**Número** (espaçamento e densidade — já existem no CSS):

```
espaco/1 = 4     espaco/2 = 8     espaco/3 = 12
espaco/4 = 16    espaco/5 = 24    espaco/6 = 32

densidade/linha-compacta   = 28
densidade/linha-normal     = 36
densidade/linha-confortavel = 44

alvo/minimo = 32
raio/painel = 10
raio/pequeno = 6
```

## Passo 4 — Publicar

Estilos e componentes **precisam estar publicados** para a API devolver. Sem
o *Publish*, a API responde 0 mesmo com tudo criado.

## O que NÃO depende da Figma

Estas partes já funcionam sem plano pago e sem Figma:

- **MCP remoto** (`mcp.figma.com`, por OAuth) — a IA lê o design system por ele
- Tokens de **densidade**, **alvo de clique** e **foco** já estão no CSS
- A **barra de latência** ao vivo, com tokens próprios

---

_Documento de roteiro. Medido em 04/10/2026 com a chave do dono._