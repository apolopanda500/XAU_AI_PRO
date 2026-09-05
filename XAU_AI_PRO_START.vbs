' XAU AI PRO - inicializador silencioso da GUI instalada
Option Explicit

Dim shell, fso, root, exe
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
exe = fso.BuildPath(root, "XAU_AI_PRO.exe")

If fso.FileExists(exe) Then
    shell.CurrentDirectory = root
    shell.Run Chr(34) & exe & Chr(34), 0, False
End If