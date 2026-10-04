# Folha de estilos para a Figma

> **GERADA.** Fonte: `frontend/src/theme/global.css`. Gerador: `scripts/gerar_folha_figma.py`.

> Nao edite a mao: se o CSS mudar, rode o gerador de novo.


## Como criar na Figma

1. No arquivo, abra **Styles** (o icone de pincel) e clique em **+**.
2. Crie uma **Variable collection** chamada `Cor`.
3. Crie uma variavel por papel, com os modos na ordem:

   | Variavel | dark | xau | btc | light | ocean | emerald | rose | violet |
   |---|---|---|---|---|---|---|---|---|
   | `bg` | #0f1420 | #14100a | #0c0f14 | #f3f5f9 | #07141f | #071510 | #16070c | #0e0a1a |
   | `panel` | #161d2d | #1d1810 | #13171f | #ffffff | #0d1c2b | #0d2019 | #220d15 | #171029 |
   | `panel2` | #1c2437 | #241d13 | #191f2a | #f7f9fc | #122535 | #122a20 | #2b1220 | #1e1536 |
   | `border` | #26314a | #3a2f1c | #2a3140 | #dbe2ec | #1d3a52 | #1d4434 | #471f30 | #2e2153 |
   | `text` | #e8ecf5 | #f5ecd8 | #eef2f7 | #1c2433 | #e3f1fb | #e2f7ec | #f9e8ee | #ece6fa |
   | `muted` | #8b94ab | #a89a7d | #93a0b4 | #5d6b82 | #7fa5c0 | #7db8a0 | #c08a9c | #a394cf |
   | `primary` | #4f7cff | #f0b90b | #f7931a | #3554d1 | #22d3ee | #34d399 | #fb7185 | #a78bfa |
   | `primary-contrast` | #ffffff | #1d1810 | #0c0f14 | #ffffff | #07141f | #071510 | #16070c | #0e0a1a |
   | `ok` | #22c55e | #4ade80 | #22c55e | #1a7f37 | #2dd4bf | #34d399 | #fb7185 | #a78bfa |
   | `warn` | #eab308 | #fbbf24 | #fbbf24 | #b26a00 | #fbbf24 | #fbbf24 | #fda4af | #c4b5fd |
   | `danger` | #ef4444 | #f87171 | #ef4444 | #c93b34 | #f87171 | #f87171 | #fb7185 | #f87171 |

## Espacamento e densidade (variaveis `NUMBER`)

| Variavel | Valor | Onde e usado |
|---|---|---|
| `raio/painel` | 10px | cantos do painel |
| `raio/pequeno` | 6px | botao e chip |
| `space/1` | 4px | gap minimo |
| `space/2` | 8px | gap pequeno |
| `space/3` | 12px | gap medio |
| `space/4` | 16px | gap grande |
| `space/5` | 24px | separacao de bloco |
| `space/6` | 32px | separacao de secao |
| `densidade/linha-compacta` | 28px | linha de tabela densa |
| `densidade/linha-normal` | 36px | linha de tabela normal |
| `densidade/linha-confortavel` | 44px | linha de tabela com folga |
| `alvo/minimo` | 32px | altura minima de botao |

## O que o gerador faz com isto

```powershell
.\.venv\Scripts\python.exe scripts\sincronizar_figma.py --aplicar
```

Ele gera `frontend/src/theme/figma-tokens.css`, que o `main.tsx` importa **por ultimo** — e por isso que o valor da Figma vence o CSS manual.

