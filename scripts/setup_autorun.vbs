Dim fso, shell, basePath, batPath, vbsPath, startupPath

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

basePath = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(basePath, "run_bot.bat")
vbsPath = fso.BuildPath(basePath, "run_bot.vbs")

' Создание батника для запуска бота
Dim batFile
Set batFile = fso.CreateTextFile(batPath, True)
batFile.WriteLine "@echo off"
batFile.WriteLine "cd /d """ & basePath & """"
batFile.WriteLine "python bot.py"
batFile.Close

' Создание скрипта VBS для запуска батника скрытно
Dim runFile
Set runFile = fso.CreateTextFile(vbsPath, True)
runFile.WriteLine "Set WshShell = CreateObject(""WScript.Shell"")"
runFile.WriteLine "WshShell.Run chr(34) & """ & batPath & """ & chr(34), 0"
runFile.WriteLine "Set WshShell = Nothing"
runFile.Close

' Копирование VBS в каталог автозагрузки
startupPath = shell.SpecialFolders("Startup")
fso.CopyFile vbsPath, fso.BuildPath(startupPath, "run_bot.vbs"), True

MsgBox "Автозапуск настроен. При следующем входе в систему бот запустится автоматически.", vbInformation
