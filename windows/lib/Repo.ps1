# Shared repo-root resolution for Windows launchers.
# Dot-source from any script under windows/:  . (Join-Path $PSScriptRoot "..\lib\Repo.ps1")

function Get-RobotRepoRoot {
    param([string]$StartDir)
    if (-not $StartDir) {
        # Prefer the script that dot-sourced us (hub, demos, setup), not this file's folder.
        $caller = Get-PSCallStack | Select-Object -Skip 1 | Where-Object { $_.ScriptName } | Select-Object -First 1
        $StartDir = if ($caller -and $caller.ScriptName) {
            Split-Path $caller.ScriptName -Parent
        } elseif ($PSScriptRoot) {
            $PSScriptRoot
        } else {
            (Get-Location).Path
        }
    }
    $d = $StartDir
    for ($i = 0; $i -lt 8; $i++) {
        if (Test-Path (Join-Path $d "board\python")) {
            return (Resolve-Path $d).Path
        }
        $parent = Split-Path $d -Parent
        if (-not $parent -or $parent -eq $d) { break }
        $d = $parent
    }
    throw "Robot repo root not found (expected board\python). Started from: $StartDir"
}

function Join-RobotPath {
  <#
    Build a path under the repo root.
    Join-RobotPath windows setup cleanup-board.ps1
    Join-RobotPath @("windows", "setup", "cleanup-board.ps1")
  #>
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [object[]]$RemainingArgs
    )

    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($arg in $RemainingArgs) {
        if ($null -eq $arg) { continue }
        if ($arg -is [System.Array]) {
            foreach ($item in $arg) {
                if ($null -ne $item -and "$item".Length -gt 0) { $parts.Add([string]$item) }
            }
        } else {
            $parts.Add([string]$arg)
        }
    }

    if ($parts.Count -eq 0) {
        return Get-RobotRepoRoot
    }

    $p = Get-RobotRepoRoot
    foreach ($part in $parts) {
        $p = Join-Path $p $part
    }
    return $p
}

function Import-RobotRepo {
    param([string]$ScriptRoot = $PSScriptRoot)
    $script:RobotRepoRoot = Get-RobotRepoRoot -StartDir $ScriptRoot
}

# Run adb without treating progress on stderr as a terminating error (needed when $ErrorActionPreference = Stop).
function Invoke-Adb {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AdbArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & adb @AdbArgs 2>&1
        return @{ ExitCode = $LASTEXITCODE; Output = @($out) }
    } finally {
        $ErrorActionPreference = $prev
    }
}
