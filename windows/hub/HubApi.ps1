# Gemy Control Center - API logic (used by HubServer.ps1).
# Dot-source after Repo.ps1, BoardHealth.ps1, GemyFeatures.ps1.

$script:HubActivity = [System.Collections.Generic.List[object]]::new()
$script:HubActivityMax = 200
$script:HubLastHealth = $null

function Add-HubActivity {
    param(
        [string]$Message,
        [ValidateSet('info', 'ok', 'warn', 'error')]
        [string]$Level = 'info'
    )
    $entry = @{
        time    = (Get-Date).ToString('HH:mm:ss')
        level   = $Level
        message = $Message
    }
    $script:HubActivity.Add($entry) | Out-Null
    while ($script:HubActivity.Count -gt $script:HubActivityMax) {
        $script:HubActivity.RemoveAt(0)
    }
    return $entry
}

function Get-HubActivityLog {
    return @($script:HubActivity)
}

function Get-BootAutostartHint {
    param($health)
    if ($health.BootAutostart) { return 'Starts on power-on' }
    if (Get-Command Get-GemyBootAutostartEnabled -ErrorAction SilentlyContinue) {
        if (Get-GemyBootAutostartEnabled) { return 'Will enable on next sync' }
        return 'OFF (feature flag - USER button still works)'
    }
    return 'OFF'
}

function ConvertTo-HubHealthDto {
    param($health)
    $bootHint = Get-BootAutostartHint $health
    $bootDesired = $false
    if (Get-Command Get-GemyBootAutostartEnabled -ErrorAction SilentlyContinue) {
        $bootDesired = [bool](Get-GemyBootAutostartEnabled)
    }

    $checks = @(
        @{
            id     = 'adb'
            label  = 'ADB tools'
            ok     = [bool]$health.AdbOnPath
            detail = if ($health.AdbOnPath) { 'adb on PATH' } else { 'Install Android platform-tools' }
        },
        @{
            id     = 'ncm'
            label  = 'USB network driver'
            ok     = [bool]$health.NcmDriver
            detail = if ($health.NcmDriver) { 'Host USB network ready' } else { 'Install once when prompted (admin)' }
        },
        @{
            id     = 'board'
            label  = 'Board on ADB'
            ok     = [bool]$health.BoardConnected
            detail = if ($health.BoardConnected) {
                if ($health.Usb0Ip) { "Connected - usb0 $($health.Usb0Ip)" } else { 'Connected - no usb0 IP yet' }
            } else { 'Plug USB-C data cable, wait ~20s for boot' }
        }
    )

    if ($health.BoardConnected) {
        $checks += @(
            @{
                id     = 'scripts'
                label  = 'Gemy scripts'
                ok     = [bool]$health.GemyScripts
                detail = if ($health.GemyScripts) { 'greeter.py on board' } else { 'Will sync on refresh' }
            },
            @{
                id     = 'venv'
                label  = 'Speech stack'
                ok     = [bool]$health.SpeechVenv
                detail = if ($health.SpeechVenv) { 'sl2610-examples venv ready' } else { 'Need sl2610-examples on board' }
            },
            @{
                id     = 'boot'
                label  = 'Boot autostart'
                ok     = [bool]$health.BootAutostart
                detail = $bootHint
            }
        )
    } else {
        $checks += @(
            @{ id = 'scripts'; label = 'Gemy scripts'; ok = $false; detail = 'Connect board to sync' },
            @{ id = 'venv'; label = 'Speech stack'; ok = $false; detail = 'Connect board to check' },
            @{ id = 'boot'; label = 'Boot autostart'; ok = $false; detail = 'Connect board to check' }
        )
    }

    $status = 'offline'
    $statusText = 'Board not on ADB'
    if ($health.BoardConnected) {
        $status = 'ready'
        $statusText = if ($health.Usb0Ip) { "Connected - $($health.Usb0Ip)" } else { 'Connected - ready to start Gemy' }
    } elseif (-not $health.AdbOnPath) {
        $status = 'setup'
        $statusText = 'Install ADB tools on this PC'
    }

    return @{
        status            = $status
        statusText        = $statusText
        adbOnPath         = [bool]$health.AdbOnPath
        ncmDriver         = [bool]$health.NcmDriver
        boardConnected    = [bool]$health.BoardConnected
        gemyScripts       = [bool]$health.GemyScripts
        speechVenv        = [bool]$health.SpeechVenv
        bootAutostart     = [bool]$health.BootAutostart
        bootAutostartWant = $bootDesired
        usb0Ip            = $health.Usb0Ip
        checks            = $checks
    }
}

function Get-HubHealthDto {
    $health = Get-BoardHealth
    $script:HubLastHealth = $health
    return ConvertTo-HubHealthDto $health
}

function Invoke-HubRefresh {
    param([switch]$OfferDriverInstall)

    Add-HubActivity 'Checking connection and board setup...'
    $health = Get-BoardHealth

    if ($OfferDriverInstall -and -not $health.NcmDriver) {
        Add-HubActivity 'USB network driver not detected - use Install driver if needed.' 'warn'
    }

    if ($health.BoardConnected) {
        Add-HubActivity 'Syncing latest Gemy scripts (safe to repeat)...'
        $sync = Sync-BoardGemyFiles -Quiet
        $lvl = if ($sync.Ok) { 'ok' } else { 'error' }
        Add-HubActivity $sync.Message $lvl
        if (-not $sync.Ok) {
            $health = Get-BoardHealth
            $script:HubLastHealth = $health
            return @{ ok = $false; health = (ConvertTo-HubHealthDto $health); message = $sync.Message }
        }
        $health = Get-BoardHealth
    }

    $script:HubLastHealth = $health
    $dto = ConvertTo-HubHealthDto $health
    Add-HubActivity "Status: $($dto.statusText)" $(if ($dto.status -eq 'ready') { 'ok' } else { 'info' })
    return @{ ok = $true; health = $dto }
}

function Invoke-HubInstallDriver {
    Add-HubActivity 'Starting USB network driver install (admin prompt)...' 'info'
    $r = Install-NcmDriverIfMissing -Quiet
    $lvl = if ($r.Ok) { 'ok' } elseif ($r.Skipped) { 'warn' } else { 'error' }
    Add-HubActivity $r.Message $lvl
    $refresh = Invoke-HubRefresh
    return @{ ok = $r.Ok; skipped = [bool]$r.Skipped; message = $r.Message; health = $refresh.health }
}

function Invoke-HubStartGemy {
    param([switch]$NoVision)

    $h = Get-BoardHealth
    if (-not $h.BoardConnected) {
        Add-HubActivity 'Cannot start - board not on ADB.' 'error'
        return @{ ok = $false; message = 'Board not on ADB. Plug USB-C and refresh.' }
    }
    if (-not $h.GemyScripts) {
        Add-HubActivity 'Syncing scripts before launch...'
        $sync = Sync-BoardGemyFiles -Quiet
        Add-HubActivity $sync.Message $(if ($sync.Ok) { 'ok' } else { 'error' })
        if (-not $sync.Ok) {
            return @{ ok = $false; message = $sync.Message }
        }
    }

    $path = Join-RobotPath @('windows', 'demos', 'greet-demo.ps1')
    if (-not (Test-Path -LiteralPath $path)) {
        Add-HubActivity "Missing greet-demo.ps1" 'error'
        return @{ ok = $false; message = 'Missing greet-demo.ps1' }
    }

    $wd = Get-RobotRepoRoot
    $args = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-File', $path)
    if ($NoVision) { $args += '-NoVision' }
    Start-Process powershell -WorkingDirectory $wd -ArgumentList $args | Out-Null

    $label = if ($NoVision) { 'Gemy (voice + keyword moods)' } else { 'Gemy (camera + keyword moods)' }
    Add-HubActivity "Launched $label - see PowerShell window for [ears] listening." 'ok'
    return @{
        ok      = $true
        message = "Launched $label. Wait for [ears] listening, then speak."
    }
}

function Invoke-HubHatPanel {
    $path = Join-RobotPath @('windows', 'demos', 'hat-gui.ps1')
    if (-not (Test-Path -LiteralPath $path)) {
        Add-HubActivity 'Missing hat-gui.ps1' 'error'
        return @{ ok = $false; message = 'Missing hat-gui.ps1' }
    }
    Start-Process powershell -WorkingDirectory (Get-RobotRepoRoot) -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-File', $path) | Out-Null
    Add-HubActivity 'Opened HAT test panel (separate window).' 'ok'
    return @{ ok = $true; message = 'Opened HAT test panel' }
}

function Invoke-HubCleanup {
    $cleanupPath = Join-RobotPath 'windows', 'setup', 'cleanup-board.ps1'
    if (-not (Test-Path -LiteralPath $cleanupPath)) {
        Add-HubActivity 'Missing cleanup-board.ps1' 'error'
        return @{ ok = $false; message = 'Missing cleanup-board.ps1' }
    }

    Add-HubActivity 'Stopping demos and turning buzzer off...'
    & powershell -NoProfile -ExecutionPolicy Bypass -File $cleanupPath 2>&1 | ForEach-Object {
        $line = "$_".Trim()
        if ($line) { Add-HubActivity $line }
    }
    Add-HubActivity 'Board cleanup finished.' 'ok'
    $refresh = Invoke-HubRefresh
    return @{ ok = $true; message = 'Cleanup done'; health = $refresh.health }
}

function Get-HubBoardLog {
    param([int]$Lines = 80)
    if (-not (Test-BoardAdbConnected)) {
        return @{ ok = $false; lines = @(); message = 'Board not connected' }
    }
    $n = [Math]::Max(10, [Math]::Min(500, $Lines))
    $out = Invoke-AdbShell "tail -n $n /home/root/gemy.log 2>/dev/null || echo '(no gemy.log yet)'"
    if ($null -eq $out) {
        return @{ ok = $false; lines = @(); message = 'ADB timed out reading log' }
    }
    $split = @($out -split "`n")
    return @{ ok = $true; lines = $split; message = $null }
}

function Get-HubBoardProcesses {
    if (-not (Test-BoardAdbConnected)) {
        return @{ ok = $false; processes = @(); message = 'Board not connected' }
    }
    $out = Invoke-AdbShell "ps aux 2>/dev/null | grep -E 'greeter|gemy-boot|gemy-watcher|moonshine' | grep -v grep || true"
    $lines = @($out -split "`n" | Where-Object { $_.Trim() })
    return @{ ok = $true; processes = $lines }
}
