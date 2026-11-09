Option Explicit
Dim shell, fso, projectDir, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = projectDir
' pythonw.exe запускает приложение без консольного окна.
command = "pythonw.exe """ & projectDir & "\main.py"""
shell.Run command, 0, False
Set fso = Nothing
Set shell = Nothing
