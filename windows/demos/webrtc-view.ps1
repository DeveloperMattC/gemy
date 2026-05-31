param([string]$Source = "test")

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

$script = "/home/root/webrtc-stream.sh"
$local  = Join-RobotPath "board", "shell", "webrtc-stream.sh"

if (Test-Path $local) {
    $c = [IO.File]::ReadAllText($local)
    [IO.File]::WriteAllText($local, ($c -replace "`r`n", "`n"))
    & adb push $local $script | Out-Null
    & adb shell "chmod +x $script" | Out-Null
}

if ($Source -eq "stop") {
    & adb shell "sh $script stop"
    Write-Host "Stopped the WebRTC stream on the board."
    return
}

Write-Host "Starting WebRTC stream on the board (source: $Source) ..."
$out = & adb shell "sh $script start $Source"
$out | ForEach-Object { Write-Host $_ }

$ip = (& adb shell "ip -4 addr show usb0 2>/dev/null | sed -n 's/.*inet \([0-9.]*\).*/\1/p' | head -n 1").Trim()
if ($ip) {
    $url = "http://${ip}:8090/"
    Write-Host "Opening $url"
    Start-Process $url
} else {
    Write-Host "Could not read usb0 IP. On board run: udhcpc -i usb0"
}
