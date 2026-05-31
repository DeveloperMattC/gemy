param([string]$Sensitivity = "medium")

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

$local = Join-RobotPath "board", "python", "wave_detect.py"
if (Test-Path $local) { & adb push $local /home/root/wave_detect.py | Out-Null }

Write-Host "Waiting for board..."
& adb wait-for-device

$py  = "/home/root/sl2610-examples/.venv/bin/python3"
$cmd = "$py /home/root/wave_detect.py --sensitivity $Sensitivity"

Write-Host "Starting wave detector (legacy; no voice). For Gemy use greet-demo.ps1."
& adb shell -t "$cmd"
