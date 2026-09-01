' XAU AI PRO - Slack Watcher (inicializacao automatica do Windows)
' Roda oculto (sem janela) usando pythonw do venv do projeto
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\.venv\Scripts\pythonw.exe"" ""C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\Ultimate\slack_watcher.py""", 0, False