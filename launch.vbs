Option Explicit

Dim shell, fso, projectDir, pythonwPath, pathValue, pathEntries, pathEntry
Dim command, i

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = projectDir

' Сначала используем Python из виртуального окружения проекта.
pythonwPath = projectDir & "\.venv\Scripts\pythonw.exe"

' Если виртуальное окружение ещё не создано, ищем pythonw.exe в PATH.
If Not fso.FileExists(pythonwPath) Then
    pythonwPath = ""
    pathValue = shell.ExpandEnvironmentStrings("%PATH%")
    pathEntries = Split(pathValue, ";")

    For i = 0 To UBound(pathEntries)
        pathEntry = Replace(Trim(pathEntries(i)), """", "")
        If Len(pathEntry) > 0 Then
            If fso.FileExists(pathEntry & "\pythonw.exe") Then
                pythonwPath = pathEntry & "\pythonw.exe"
                Exit For
            End If
        End If
    Next
End If

If Len(pythonwPath) = 0 Then
    MsgBox "Не найден Python (pythonw.exe)." & vbCrLf & vbCrLf & _
           "Сначала создайте виртуальное окружение и установите зависимости:" & vbCrLf & _
           "py -3 -m venv .venv" & vbCrLf & _
           ".venv\Scripts\python.exe -m pip install -r requirements.txt", _
           vbCritical, "WEB-Constructor — запуск невозможен"
Else
    command = """" & pythonwPath & """ """ & projectDir & "\main.py"""
    shell.Run command, 0, False
End If

Set fso = Nothing
Set shell = Nothing
