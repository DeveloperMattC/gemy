. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")

$hub     = Join-RobotPath "windows", "hub", "coralboard-hub.ps1"
$root    = Get-RobotRepoRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop "Coralboard Control Center.lnk"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnkPath)
$sc.TargetPath       = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$sc.Arguments        = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -STA -File `"$hub`""
$sc.WorkingDirectory = $root
$sc.IconLocation     = "$env:SystemRoot\System32\imageres.dll,109"
$sc.Description      = "Open the Coralboard demos control center"
$sc.WindowStyle      = 7
$sc.Save()

if (Test-Path $lnkPath) { Write-Host "Created shortcut: $lnkPath" }
else { Write-Host "Failed to create shortcut." }
