$WshShell = New-Object -comObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")

$Shortcut1 = $WshShell.CreateShortcut("$Desktop\XTOBE Ai - Personal.lnk")
$Shortcut1.TargetPath = "powershell.exe"
$Shortcut1.Arguments = '-NoExit -Command Write-Host "XTOBE Ai - Your Personal Agent" -ForegroundColor Cyan; ollama run XTOBE'
$Shortcut1.WorkingDirectory = "$env:USERPROFILE\XTOBE"
$Shortcut1.IconLocation = "powershell.exe,0"
$Shortcut1.Save()

$Shortcut2 = $WshShell.CreateShortcut("$Desktop\XTOBE Ai - Production.lnk")
$Shortcut2.TargetPath = "powershell.exe"
$Shortcut2.Arguments = '-NoExit -Command Write-Host "XTOBE Ai - Production Center" -ForegroundColor Yellow; ollama run XTOBE'
$Shortcut2.WorkingDirectory = "$env:USERPROFILE\XTOBE"
$Shortcut2.IconLocation = "powershell.exe,0"
$Shortcut2.Save()

Write-Host "ICONS CREATED" -ForegroundColor Green
