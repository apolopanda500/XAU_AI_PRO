; XAU AI PRO - limpeza segura durante atualização NSIS.
; Escopo deliberadamente limitado ao diretório de instalação do app.
; Não tocar em APPDATA, credenciais, logs, dados do usuário, MT5 ou EA.

!macro NSIS_HOOK_PREINSTALL
  ; Remove somente recursos regeneráveis/empacotados do app.
  ; Não encerra processos globais por nome: a UI encerra apenas os filhos que iniciou.
  ; O instalador copiará novamente os diretórios atuais logo depois.
  RMDir /r "$INSTDIR\bridge"
  RMDir /r "$INSTDIR\core"
  Delete "$INSTDIR\mt5-gateway.exe"
  Delete "$INSTDIR\xau-ai-pro-core.exe"
  Delete "$INSTDIR\XAU_AI_PRO.exe"
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ; Não encerra processos globais por nome durante a desinstalação.
  ; O aplicativo encerra os processos filhos registrados ao ser fechado.
  ;
  ; O atalho da Área de Trabalho é removido aqui porque o Windows não o faz
  ; sozinho. Sem esta linha, atualizar o app deixaria um .lnk apontando para
  ; um executável que já não existe — o duplo clique daria "o sistema não
  ; pode encontrar o arquivo especificado".
  Delete "$DESKTOP\XAU AI PRO.lnk"
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ; Cria o atalho na Área de Trabalho e no Menu Iniciar.
  ;
  ; POR QUE ISTO AQUI E NÃO NO tauri.conf.json
  ; A chave `bundle.shortcut` NÃO EXISTE no Tauri v2. Ela foi tentada em
  ; 01/10/2026 e o `cargo test` do Tauri recusou com "unknown field
  ; `shortcut`" — nem `WindowsConfig` nem `WixConfig` nem `NsisConfig` têm
  ; campo de atalho (verificado no schema de tauri-utils 2.9.3). O Tauri v2
  ; não expõe essa opção; o caminho suportado é o hook NSIS, que já era usado
  ; aqui para a limpeza na atualização.
  ;
  ; `CreateShortCut` é o comando nativo do NSIS e não depende de nada
  ; externo. `$DESKTOP` e `$SMPROGRAMS` são resolvidos pelo próprio
  ; instalador para as pastas corretas do usuário, incluindo o OneDrive
  ; quando o Windows redireciona a Área de Trabalho.
  CreateShortCut "$DESKTOP\XAU AI PRO.lnk" "$INSTDIR\XAU AI PRO.exe"
  CreateDirectory "$SMPROGRAMS\XAU AI PRO"
  CreateShortCut "$SMPROGRAMS\XAU AI PRO\XAU AI PRO.lnk" "$INSTDIR\XAU AI PRO.exe"
  CreateShortCut "$SMPROGRAMS\XAU AI PRO\Desinstalar.lnk" "$INSTDIR\uninstall.exe"
!macroend
