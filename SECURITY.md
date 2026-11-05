# Política de Segurança — XAU AI PRO

## Versões suportadas

Só a versão publicada mais recente recebe correções de segurança. A versão
corrente está no arquivo [`VERSION`](VERSION) e em [`Docs/version.json`](Docs/version.json).

| Versão | Suportada |
| --- | --- |
| `1.2.x` (mais recente) | :white_check_mark: |
| anteriores | :x: |

## Como reportar uma vulnerabilidade

**Não abra issue pública para falhas de segurança.** Use o canal privado:

1. GitHub → aba **Security** → **Report a vulnerability**
   (<https://github.com/apolopanda500/XAU_AI_PRO/security/advisories/new>), ou
2. e-mail para o mantenedor indicado no perfil
   <https://github.com/apolopanda500>.

Inclua, quando possível: versão afetada, passos para reproduzir, impacto e uma
prova de conceito mínima. Não inclua dados de conta, tokens, chaves de API ou
informação de clientes.

## O que esperar

| Etapa | Prazo alvo |
| --- | --- |
| Confirmação de recebimento | até 5 dias úteis |
| Avaliação inicial e severidade | até 10 dias úteis |
| Correção ou mitigação | conforme severidade, comunicada no aviso |

Você será informado quando a correção for publicada, e creditado no aviso
privado se assim desejar.

## Escopo

Estão no escopo: o gateway local (`backend/`), o núcleo Rust (`core/`), a
interface (`frontend/`, `app/`), o Expert Advisor (`MQL5/`) e os scripts de
build e instalação (`scripts/`, `installer/`).

Fora do escopo: má configuração do terminal MetaTrader 5, credenciais da
corretora, serviços de terceiros (GitHub, GitLab, corretoras) e engenharia
social.

## Regras que não mudam

- Nenhum saque, transferência ou movimentação de fundos para fora da corretora,
  em nenhuma camada. Há teste automatizado que reprova essa regressão.
- O gateway é *fail-closed*: sem token de sessão válido, toda chamada é recusada
  com `401`.
- Segredos nunca são versionados. A varredura de segredos (gitleaks) roda no CI
  sobre o histórico completo.
