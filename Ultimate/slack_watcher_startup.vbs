' XAU AI PRO - Slack Watcher (inicializacao automatica do Windows)
' Roda oculto (sem janela) usando pythonw do venv do projeto
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\Micro\Downloads\XAU_AI_PRO\.venv\Scripts\pythonw.exe"" ""C:\Users\Micro\Downloads\XAU_AI_PRO\Ultimate\slack_watcher.py""", 0, False