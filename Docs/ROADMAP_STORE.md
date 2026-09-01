# 🏪 Roadmap — Distribuição em Lojas Oficiais (XAU AI PRO)

## Estado atual (v1.3.2)
- Instalador Windows (Inno Setup): `XAU_AI_PRO_Setup.exe` (~175 MB)
- Distribuição direta via GitHub Releases + CI automático (`build-installer.yml`)
- Auto-atualização embutida no app (aba Integrações → Atualizações)
- Modelos de IA por download sob demanda (GitHub Releases)

## Fase A — Microsoft Store (caminho mais curto, recomendado primeiro)
> App desktop Windows é aceito na Microsoft Store via empacotamento MSIX.

1. **Empacotamento MSIX**
   - Ferramenta: MSIX Packaging Tool (gratuita) ou `msix` via CI
   - Empacotar o resultado do instalador (mesmos arquivos do Inno Setup)
   - Identidade: `Publisher` deve bater com certificado da conta Microsoft Partner Center
2. **Conta Microsoft Partner Center**
   - Taxa única: ~US$ 19 (individual) / ~US$ 99 (empresa)
   - Verificação de identidade (CNPJ/CPF)
3. **Requisitos de revisão da Microsoft**
   - App não pode exigir admin para instalar (já atendido: `PrivilegesRequired=lowest`)
   - Deve desinstalar limpo (o Inno Setup já gera uninstaller — validar)
   - Sem download de código executável em runtime (⚠️ atenção: a auto-atualização
     baixa o Setup — na versão Store, a atualização é gerenciada pela própria Store;
     desabilitar o updater quando instalado via MSIX: detectar via identidade de pacote)
4. **Trading/financeiro**: apps de trading não têm restrição na MS Store,
   mas recomenda-se disclaimer de risco na listagem

**Esforço estimado: 2–4 semanas** (a maior parte é burocracia/certificado)

## Fase B — Play Store (Android) — app companheiro, não o desktop
> A Play Store não aceita apps Windows. O caminho é um app Android companheiro
> que conecta no mesmo backend/MT5 da nuvem.

1. **Escopo do app Android (MVP)**
   - Dashboard: saldo, posições abertas, resultados do robô (leitura)
   - Notificações push (Slack já existe; trocar por FCM)
   - Login na mesma conta do app desktop
2. **Tecnologia recomendada**
   - Compartilhar backend: FastAPI (`Python/backend/api.py`) já existe → publicar na Vercel
   - App: Flutter ou React Native (um código para Android+iOS no futuro)
3. **Requisitos Play Store**
   - Conta Google Play Console: US$ 25 (única vez)
   - Política de Privacidade (obrigatória) + classificações de conteúdo
   - Apps financeiros: documentação adicional nos últimos anos da Google
4. **MVP estimado: 4–8 semanas**

## Fase C — Outros canais
- **Steam (eventual)**: apps de produtividade/trading raramente; não recomendado
- **Site próprio + assinatura**: já funcional hoje via Releases (atual) —
  modelo de licença mensal/aluguel pode usar keys validadas no backend

## Decisões de produto ligadas ao modelo mensal
| Item | Como funciona hoje | Ação futura |
|------|--------------------|-------------|
| Versão | `VERSION` + `Tools/bump_version.py` | bump mensal: `--minor` = novo ciclo |
| Build | Tag `v*` → CI builds Setup | nada a fazer |
| Atualização | App baixa Setup do release | na Store: usar updater da loja |
| Licença | Livre | backend valida assinatura/aluguel (`decision/licensing`) |
