# Board + host health checks and idempotent setup (safe to run every launch).
# Dot-source after Repo.ps1 and GemyFeatures.ps1.

if (-not (Get-Command Invoke-Adb -ErrorAction SilentlyContinue)) {
    . (Join-Path $PSScriptRoot "Repo.ps1")
}

function Test-AdbOnPath {
    try {
        $null = Get-Command adb -ErrorAction Stop
        return $true
    } catch { return $false }
}

function Get-AdbDeviceLines {
    if (-not (Test-AdbOnPath)) { return @() }
    try {
        return @(& adb devices 2>&1 | Select-Object -Skip 1 | Where-Object { $_ -match "\S" })
    } catch { return @() }
}

function Test-BoardAdbConnected {
    $lines = Get-AdbDeviceLines
    return @($lines | Where-Object { $_ -match "`tdevice\s*$" }).Count -gt 0
}

function Test-NcmHostReady {
    try {
        $ncm = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object {
            $_.Status -eq 'Up' -and (
                ($_.InterfaceDescription -match 'UsbNcm|NCM Host|NCM') -or
                ($_.Name -match 'NCM')
            )
        } | Select-Object -First 1
        if ($ncm) { return $true }
        $dev = Get-PnpDevice -ErrorAction SilentlyContinue | Where-Object {
            $_.InstanceId -match 'VID_1D6B&PID_0104' -and $_.Status -eq 'OK'
        } | Select-Object -First 1
        return ($null -ne $dev)
    } catch { return $false }
}

function Invoke-AdbShell([string]$Command, [int]$TimeoutSec = 25) {
    if (-not (Test-BoardAdbConnected)) { return $null }
    $job = Start-Job -ScriptBlock {
        param($cmd)
        & adb shell $cmd 2>&1 | Out-String
    } -ArgumentList $Command
    $done = Wait-Job $job -Timeout $TimeoutSec
    if (-not $done) {
        Stop-Job $job -Force -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
        return $null
    }
    $out = (Receive-Job $job) -join "`n"
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    return $out.Trim()
}

function Test-BoardGemyScripts {
    $out = Invoke-AdbShell "test -f /home/root/greeter.py && test -f /home/root/hat.py && test -f /home/root/gemma_mood.py && echo ok"
    return ($out -match '\bok\b')
}

function Test-BoardSpeechVenv {
    $out = Invoke-AdbShell "test -x /home/root/sl2610-examples/.venv/bin/python3 && echo ok"
    return ($out -match '\bok\b')
}

function Test-BoardAutostartEnabled {
    $out = Invoke-AdbShell "systemctl is-enabled gemy-autostart.service 2>/dev/null"
    return ($out -match 'enabled')
}

function Get-BoardUsb0Ip {
    $out = Invoke-AdbShell "ip -4 addr show usb0 2>/dev/null | sed -n 's/.*inet \([0-9.]*\).*/\1/p' | head -n 1"
    if ($out -match '(\d+\.\d+\.\d+\.\d+)') { return $Matches[1] }
    return $null
}

function Get-BoardHealth {
    $adbPath = Test-AdbOnPath
    $connected = $false
    if ($adbPath) { $connected = Test-BoardAdbConnected }

    $health = [ordered]@{
        AdbOnPath       = $adbPath
        NcmDriver       = Test-NcmHostReady
        BoardConnected  = $connected
        GemyScripts     = $false
        SpeechVenv      = $false
        BootAutostart   = $false
        UsbInternet     = $false
        Usb0Ip          = $null
    }

    if ($connected) {
        $health.GemyScripts = Test-BoardGemyScripts
        $health.SpeechVenv = Test-BoardSpeechVenv
        $health.BootAutostart = Test-BoardAutostartEnabled
        $ip = Get-BoardUsb0Ip
        $health.Usb0Ip = $ip
        $health.UsbInternet = [bool]$ip
    }

    return [pscustomobject]$health
}

function Sync-BoardGemyFiles {
    param([switch]$Quiet)

    function Say([string]$m) { if (-not $Quiet) { Write-Host $m } }

    if (-not (Test-BoardAdbConnected)) {
        return @{ Ok = $false; Message = "Board not connected on ADB." }
    }

    & adb wait-for-device 2>$null | Out-Null
    $push = @(
        @("board", "python", "greeter.py"),
        @("board", "python", "hat.py"),
        @("board", "python", "gemma_mood.py"),
        @("board", "python", "gemma_mood_worker.py"),
        @("board", "python", "gemy-watcher.py"),
        @("board", "shell", "gemy-boot.sh")
    )
    foreach ($parts in $push) {
        $local = Join-RobotPath @parts
        $name = $parts[-1]
        if (-not (Test-Path -LiteralPath $local)) {
            return @{ Ok = $false; Message = "Missing repo file: $local" }
        }
        $push = Invoke-Adb push $local "/home/root/$name"
        if ($push.ExitCode -ne 0) {
            $detail = ($push.Output | Out-String).Trim()
            return @{ Ok = $false; Message = "adb push failed: $name ($detail)" }
        }
        Say "  synced $name"
    }

    if (Get-Command Sync-GemyBootAutostartOnBoard -ErrorAction SilentlyContinue) {
        $boot = Sync-GemyBootAutostartOnBoard -Quiet
        if (-not $boot.Ok) {
            return @{ Ok = $false; Message = $boot.Message }
        }
        $bootMsg = $boot.Message
    } else {
        $bootMsg = "scripts synced (boot autostart unchanged)"
    }

    return @{ Ok = $true; Message = "Board scripts up to date. $bootMsg" }
}

function Install-NcmDriverIfMissing {
    param([switch]$Quiet)

    if (Test-NcmHostReady) {
        return @{ Ok = $true; Message = "USB network driver already installed."; Skipped = $true }
    }

    $script = Join-RobotPath "windows", "setup", "install-ncm-signed.ps1"
    if (-not (Test-Path -LiteralPath $script)) {
        return @{ Ok = $false; Message = "Missing: $script" }
    }

    if (-not $Quiet) {
        $ans = [System.Windows.Forms.MessageBox]::Show(
            "The Coralboard USB network driver is not installed yet.`n`n" +
            "Windows will ask for admin approval once (not every time).`n`nInstall now?",
            "Gemy setup",
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Question)
        if ($ans -ne [System.Windows.Forms.DialogResult]::Yes) {
            return @{ Ok = $false; Message = "USB driver install skipped."; Skipped = $true }
        }
    }

    try {
        $p = Start-Process powershell -Verb RunAs -Wait -PassThru -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $script)
        if ($p.ExitCode -eq 0 -or (Test-NcmHostReady)) {
            return @{ Ok = $true; Message = "USB network driver installed." }
        }
        return @{ Ok = $false; Message = "Driver install finished (exit $($p.ExitCode)). Plug USB-C and refresh." }
    } catch {
        return @{ Ok = $false; Message = $_.Exception.Message }
    }
}

function Repair-BoardEnvironment {
    param(
        [switch]$InstallDriver,
        [switch]$SyncFiles,
        [switch]$Quiet
    )

    $log = [System.Collections.Generic.List[string]]::new()

    if ($InstallDriver -and -not (Test-NcmHostReady)) {
        $r = Install-NcmDriverIfMissing -Quiet:$Quiet
        $log.Add($r.Message)
        if (-not $r.Ok -and -not $r.Skipped) {
            return @{ Ok = $false; Log = $log }
        }
    }

    if (-not (Test-BoardAdbConnected)) {
        if (-not (Test-NcmHostReady)) {
            $log.Add("Plug in USB-C after driver install, wait ~20s, then refresh.")
        } else {
            $log.Add("Board not on ADB - plug in USB-C and wait for boot.")
        }
        return @{ Ok = $false; Log = $log }
    }

    if ($SyncFiles) {
        $r = Sync-BoardGemyFiles -Quiet:$Quiet
        $log.Add($r.Message)
        if (-not $r.Ok) { return @{ Ok = $false; Log = $log } }
    }

    return @{ Ok = $true; Log = $log }
}
