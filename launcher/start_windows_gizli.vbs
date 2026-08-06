' Siyah komut penceresi GOSTERMEDEN baslatir (masaustu kisayolu icin ideal).
' Kisayol hedefi olarak bu dosyayi kullan; simge olarak logonu atarsin.
Set fso = CreateObject("Scripting.FileSystemObject")
klasor = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("Wscript.Shell")
sh.Run """" & klasor & "\start_windows.bat""", 0, False
