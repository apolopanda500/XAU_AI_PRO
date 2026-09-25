# XAU AI PRO — produto verificável antes de venda

**Data:** 23/09/2026. **Estado:** em desenvolvimento; não aprovado para operar dinheiro real nem para anúncio como produto pronto.

## Escopo que o código permite afirmar hoje

| Objetivo | Estado verificável | Condição para anunciar |
|---|---|---|
| Conta MT5 do usuário | Gateway consulta a conta conectada ao terminal local; não é integração certificada com todas as corretoras MT5 | Testar cada servidor, símbolo, lote, modo de preenchimento, hedge/netting e falhas em DEMO |
| EA do usuário | Bridge própria recebe heartbeat/posições; não existe protocolo universal comprovado para EAs de terceiros | Definir adaptador opt-in, identificação do EA e autorização explícita; nunca assumir controle de EA externo |
| Binance e MEXC | Adaptadores presentes para algumas leituras/mercados | Matriz de cobertura por mercado, permissões, respostas e reconciliação; nenhuma alegação de suporte irrestrito |
| Modelos treinados/importados | Há pipeline e metadados de modelo, mas o histórico de deals não identifica um modelo com atribuição auditável | Vincular `model_id`/versão/hash de decisão a intenção, ordem, deal, conta e intervalo; reconciliar após reinício |
| PnL/trades por modelo | **Indisponível** com a evidência atual; PnL da conta não é PnL do modelo | Calcular somente trades fechados atribuídos, separar custos, entradas/parciais, depósitos e moedas; mostrar lacunas de atribuição |
| Copiloto de IA | Proposta futura; previsões não substituem confirmação do terminal nem controles de risco | Iniciar somente leitura com fonte, horário, incerteza e explicação; nenhum envio automático de ordem |
| Conta REAL | Rotas de ordem REAL agora recusam incondicionalmente; não há liberação por variável de ambiente | Projetar idempotência persistente, reconciliação e autorização operacional independente; testar integralmente em DEMO antes de considerar implementação REAL |

## Avanço de segurança em 23/09/2026

- `/api/universal/order`, `/close`, `/modify` e `/cancel` aceitam somente prévia: `execute=true` retorna bloqueio nos gateways HTTP e FastAPI, sem chamar adaptadores de execução.
- `/api/real/order` permanece bloqueado mesmo com `XAU_ENABLE_REAL_ORDERS=1`. A antiga prevenção de duplicatas apenas em memória não era suficiente para dinheiro real.
- Testes automatizados usam simulações e verificam que nem o roteador universal nem a interface MT5 são chamados nos caminhos bloqueados. Nenhuma ordem foi enviada.
- **Próximo bloqueador:** auditar execução DEMO e EA, persistir identificadores de intenção/ordem/deal/conta e tratar resposta incerta como pendente de reconciliação. O bloqueio das rotas não resolve esses itens.
- O log de intenções não interpreta mais ausência de evidência ou coincidência de `magic`/símbolo/horário como prova de execução ou falha: resultados incertos continuam pendentes, inclusive após reinício e após 24 horas. Ainda não há correlação exclusiva com ordem/deal/conta nem prevenção persistente de duplicatas nas rotas DEMO/EA; não repetir tentativas incertas automaticamente.
- A fila offline não reenvia comandos automaticamente: entradas novas são registradas para revisão manual e entradas `pending` herdadas são imobilizadas antes de chamar qualquer runner. A resposta `queued` significa somente registro, não agendamento nem execução. A reconciliação manual permanece necessária.

## Prioridades de implementação

1. **Segurança:** unificar a política de execução entre EA e gateway; autenticação local, identidade de conta, idempotência persistente e reconciliação de resultados desconhecidos; falhar fechado em leitura indisponível. Testar rede interrompida, reinício e requisição duplicada.
2. **Compatibilidade:** publicar uma matriz por capacidade (leitura, DEMO, proteção, ordens pendentes, fechamento); detectar símbolos e restrições do servidor em tempo de execução. Não prometer “todas as corretoras/ativos”.
3. **Modelos:** registrar proveniência dos dados e modelos, separar backtest, DEMO e REAL, impedir importação insegura sem avaliação dos formatos e da origem. Nunca executar modelo importado como código confiável por padrão.
4. **Resultados:** implementar atribuição verificável antes de exibir PnL por modelo; valores ausentes devem aparecer como **indisponíveis**, não como zero ou estimativa de lucro.
5. **Distribuição:** validar PyInstaller/Inno e Tauri/NSIS/MSI separadamente em Windows limpo; assinar com certificado público legítimo, publicar SHA-256, verificar antivírus e instalação/desinstalação. Certificado autoassinado é apenas para desenvolvimento.
6. **Antivírus/SmartScreen:** nenhum fornecedor permite prometer “0 vírus/0 alerta” universal. Microsoft SmartScreen usa reputação de arquivo, URL, certificado e histórico de downloads; assinatura Authenticode e scans reduzem risco, mas não garantem ausência de aviso. Falsos positivos devem ser submetidos ao portal da Microsoft. Upload público para multi-engine pode expor binário; use opção privada/enterprise quando aplicável.

## Portão de release

Exigir testes Python, frontend, Core Rust e Tauri concluídos; compilação do EA efetivamente usado; cenários de falha em DEMO; auditoria de dependências e segredos; hashes e assinaturas dos binários exatos; termos e política de privacidade adequados. Nenhum teste isolado autoriza dinheiro real. Comunicações comerciais devem distinguir funcionalidades implementadas, planejadas e não validadas e não prometer retorno financeiro ou nota “10/10”.

Referências operacionais atuais: Microsoft documenta SmartScreen como proteção baseada em reputação; a própria Microsoft informa que apps sem reputação podem exibir aviso mesmo quando assinados. A submissão de falsos positivos deve ser feita como desenvolvedor de software no portal de Security Intelligence/Defender. VirusTotal possui fluxo de private scanning; não subir artefatos proprietários automaticamente no serviço público sem decisão explícita.

**Organização:** preservar diretórios e dados existentes até mapear referências, retenção, backup e rastreabilidade. Limpar apenas artefatos temporários gerados e comprovadamente dispensáveis, nunca histórico de trading, modelos ou EAs por suposição.