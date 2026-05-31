# Launch Gemy — the Coralboard greeting robot — in an interactive window.
#   powershell -ExecutionPolicy Bypass -File windows\demos\greet-demo.ps1
#   (or from repo root: .\greet-demo.ps1)

param(
    [string]$Sensitivity = "medium",
    [switch]$NoSpeech,
    [switch]$NoVision
)

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

foreach ($f in @("greeter.py", "hat.py")) {
    $local = Join-RobotPath "board", "python", $f
    if (Test-Path $local) { & adb push $local "/home/root/$f" | Out-Null }
}

Write-Host "Waiting for board..."
& adb wait-for-device

& (Join-RobotPath "windows", "setup", "cleanup-board.ps1")

$py   = "/home/root/sl2610-examples/.venv/bin/python3"
$opts = "--sensitivity $Sensitivity --cooldown 1"
if ($NoSpeech) { $opts += " --no-speech" }
if ($NoVision) { $opts += " --no-vision" }
$cmd = "$py -u /home/root/greeter.py $opts"

Write-Host "Starting Gemy (sensitivity=$Sensitivity)."
Write-Host "Try: 'Gemy' (signature hello), hello, funny, nice, mean, or anything else."
Write-Host "Watch this window: [ears] heard: ... -> gemy|greet|funny|nice|mean|neutral"
Write-Host "(Speech model loads first, then camera - wait for [ears] listening.)"
& adb shell -t "$cmd"
