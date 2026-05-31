# Create / update desktop shortcut for Gemy Control Center (web dashboard).
. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")

$hub     = Join-RobotPath "windows", "hub", "coralboard-hub.ps1"
$root    = Get-RobotRepoRoot
$iconIco = Join-RobotPath "windows", "hub", "assets", "gemy.ico"
$iconPng = Join-RobotPath "windows", "hub", "assets", "gemy-logo.png"

if (-not (Test-Path -LiteralPath $hub)) {
    Write-Host "ERROR: Hub launcher missing: $hub" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $iconIco)) {
    if (Test-Path -LiteralPath $iconPng) {
        Add-Type -AssemblyName System.Drawing
        $bmp = New-Object System.Drawing.Bitmap($iconPng)
        $resized = New-Object System.Drawing.Bitmap($bmp, 256, 256)
        $hIcon = [System.Drawing.Icon]::FromHandle($resized.GetHicon())
        $fs = [System.IO.File]::Open($iconIco, [System.IO.FileMode]::Create)
        $hIcon.Save($fs)
        $fs.Close()
        $resized.Dispose(); $bmp.Dispose(); $hIcon.Dispose()
        Write-Host "Built icon: $iconIco"
    } else {
        Write-Host "WARNING: No gemy.ico - add windows\hub\assets\gemy-logo.png and re-run." -ForegroundColor Yellow
    }
}

$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop "Gemy Control Center.lnk"
$legacy  = Join-Path $desktop "Coralboard Control Center.lnk"
if (Test-Path -LiteralPath $legacy) {
    Remove-Item -LiteralPath $legacy -Force -ErrorAction SilentlyContinue
}

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnkPath)
$sc.TargetPath       = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$sc.Arguments        = "-NoProfile -ExecutionPolicy Bypass -File `"$hub`""
$sc.WorkingDirectory = $root
if (Test-Path -LiteralPath $iconIco) {
    $sc.IconLocation = "$iconIco,0"
} else {
    $sc.IconLocation = "$env:SystemRoot\System32\imageres.dll,109"
}
$sc.Description = "Open Gemy Control Center in your browser (Coralboard lab)"
# 7 = minimized - browser is the main UI; server stays in taskbar
$sc.WindowStyle = 7
$sc.Save()

if (Test-Path -LiteralPath $lnkPath) {
    Write-Host ""
    Write-Host "Desktop shortcut updated:" -ForegroundColor Green
    Write-Host "  $lnkPath"
    Write-Host "  Target:  coralboard-hub.ps1 (web dashboard)"
    Write-Host "  Repo:    $root"
    if (Test-Path -LiteralPath $iconIco) {
        Write-Host "  Icon:    $iconIco"
    }
} else {
    Write-Host "Failed to create shortcut." -ForegroundColor Red
    exit 1
}
