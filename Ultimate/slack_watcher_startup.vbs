' XAU AI PRO - Slack Watcher (inicializacao automatica do Windows)
' Roda oculto (sem janela) usando pythonw do venv do projeto
Set WshShell = CreateObject("WScript.Shell")
Set FileSystem = CreateObject("Scripting.FileSystemObject")
ProjectDir = FileSystem.GetParentFolderName(FileSystem.GetParentFolderName(WScript.ScriptFullName))
PythonExe = ProjectDir & "\.venv\Scripts\pythonw.exe"
WatcherScript = ProjectDir & "\Ultimate\slack_watcher.py"
WshShell.Run """" & PythonExe & """ """ & WatcherScript & """", 0, False
