import subprocess, win32com.client, os
from pathlib import Path

Desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
shell = win32com.client.Dispatch("WScript.Shell")

# 1. XTOBE Ai Personal
s1 = shell.CreateShortcut(str(Desktop / "XTOBE Ai - Personal.lnk"))
s1.TargetPath = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
s1.Arguments = '-NoExit -Command Write-Host "XTOBE Ai - Your Personal Agent" -ForegroundColor Cyan; ollama run XTOBE'
s1.WorkingDirectory = r"C:\Users\Nishan\XTOBE"
s1.IconLocation = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe,0"
s1.Save()

# 2. Production
s2 = shell.CreateShortcut(str(Desktop / "XTOBE Ai - Production.lnk"))
s2.TargetPath = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
s2.Arguments = '-NoExit -Command Write-Host "XTOBE Ai - Production Center" -ForegroundColor Yellow; ollama run XTOBE'
s2.WorkingDirectory = r"C:\Users\Nishan\XTOBE"
s2.IconLocation = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe,0"
s2.Save()

print(f"Shortcuts created in {Desktop}")
print("  - XTOBE Ai - Personal.lnk")
print("  - XTOBE Ai - Production.lnk")
