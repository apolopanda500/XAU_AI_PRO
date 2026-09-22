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
!macroend
