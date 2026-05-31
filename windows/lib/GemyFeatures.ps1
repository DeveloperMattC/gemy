# Gemy feature flags — single switchboard for repo-wide behavior.
# Dot-source after Repo.ps1:  . (Join-Path ... "GemyFeatures.ps1")
#
# Boot autostart: Gemy runs greeter.py ~30s after every power-on.
# OFF by default while tuning; USER button + Control Center still work.
#
# Turn ON later (pick one):
#   1. Set $script:GemyBootAutostart = $true below
#   2. Or env:  $env:GEMY_BOOT_AUTOSTART = "1"
#   3. Or:      install-gemy-standalone.ps1 -ForceBootAutostart

# FEATURE FLAG — boot autostart (change to $true when ready)
$script:GemyBootAutostart = $false

function Get-GemyBootAutostartEnabled {
    if ($env:GEMY_BOOT_AUTOSTART -eq "1") { return $true }
    if ($env:GEMY_BOOT_AUTOSTART -eq "0") { return $false }
    return [bool]$script:GemyBootAutostart
}

function Sync-GemyBootAutostartOnBoard {
    param([switch]$Quiet)
    $enableScript = Join-RobotPath "windows", "setup", "enable-gemy-autostart.ps1"
    if (-not (Test-Path -LiteralPath $enableScript)) {
        return @{ Ok = $false; Message = "Missing $enableScript" }
    }
    if (Get-GemyBootAutostartEnabled) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $enableScript -Quiet -EnableOnly 2>&1 | Out-Null
        return @{ Ok = $true; Message = "Boot autostart enabled on board." }
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $enableScript -Quiet -Disable 2>&1 | Out-Null
    return @{ Ok = $true; Message = "Boot autostart disabled on board (feature flag)." }
}
