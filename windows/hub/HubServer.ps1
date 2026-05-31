# Gemy Control Center - local web UI (http://127.0.0.1:PORT/)
param(
    [int]$Port = 0,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$HubRoot = $PSScriptRoot
. (Join-Path $HubRoot '..\lib\Repo.ps1')
$script:RobotRepoRoot = Get-RobotRepoRoot
. (Join-Path $script:RobotRepoRoot 'windows\lib\BoardHealth.ps1')
$gf = Join-Path $script:RobotRepoRoot 'windows\lib\GemyFeatures.ps1'
if (Test-Path -LiteralPath $gf) { . $gf }
. (Join-Path $HubRoot 'HubApi.ps1')

$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')

$WwwRoot = Join-Path $HubRoot 'www'

function Find-HubPort {
    param([int]$Preferred = 8765)
    if ($Port -gt 0) { return $Port }
    foreach ($p in @($Preferred) + (8766..8775)) {
        try {
            $l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $p)
            $l.Start()
            $l.Stop()
            return $p
        } catch { continue }
    }
    throw 'No free port found for Control Center (8765-8775).'
}

function Write-JsonResponse {
    param($Context, $Object, [int]$StatusCode = 200)
    $json = $Object | ConvertTo-Json -Depth 8 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $res = $Context.Response
    $res.StatusCode = $StatusCode
    $res.ContentType = 'application/json; charset=utf-8'
    $res.ContentLength64 = $bytes.Length
    $res.OutputStream.Write($bytes, 0, $bytes.Length)
    $res.Close()
}

function Write-TextResponse {
    param($Context, [string]$Body, [string]$ContentType, [int]$StatusCode = 200)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Body)
    $res = $Context.Response
    $res.StatusCode = $StatusCode
    $res.ContentType = $ContentType
    $res.ContentLength64 = $bytes.Length
    $res.OutputStream.Write($bytes, 0, $bytes.Length)
    $res.Close()
}

function Write-BytesResponse {
    param($Context, [byte[]]$Bytes, [string]$ContentType, [int]$StatusCode = 200)
    $res = $Context.Response
    $res.StatusCode = $StatusCode
    $res.ContentType = $ContentType
    $res.ContentLength64 = $Bytes.Length
    $res.OutputStream.Write($Bytes, 0, $Bytes.Length)
    $res.Close()
}

function Read-RequestJson {
    param($Context)
    $req = $Context.Request
    if ($req.HttpMethod -ne 'POST' -and $req.HttpMethod -ne 'PUT') { return @{} }
    $reader = New-Object System.IO.StreamReader($req.InputStream, $req.ContentEncoding)
    $raw = $reader.ReadToEnd()
    $reader.Close()
    if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
    try { return ($raw | ConvertFrom-Json) } catch { return @{} }
}

function Get-StaticMime([string]$Path) {
    switch ([System.IO.Path]::GetExtension($Path).ToLowerInvariant()) {
        '.html' { return 'text/html; charset=utf-8' }
        '.css'  { return 'text/css; charset=utf-8' }
        '.js'   { return 'application/javascript; charset=utf-8' }
        '.svg'  { return 'image/svg+xml' }
        '.png'  { return 'image/png' }
        '.ico'  { return 'image/x-icon' }
        default { return 'application/octet-stream' }
    }
}

function Serve-StaticFile {
    param($Context, [string]$RelPath)
    $safe = $RelPath.TrimStart('/') -replace '\.\.', ''
    if ([string]::IsNullOrWhiteSpace($safe)) { $safe = 'index.html' }
    $full = Join-Path $WwwRoot $safe
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        Write-TextResponse $Context 'Not found' 'text/plain' 404
        return
    }
    $bytes = [System.IO.File]::ReadAllBytes($full)
    Write-BytesResponse $Context $bytes (Get-StaticMime $full)
}

function Invoke-HubRoute {
    param($Context)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $req = $Context.Request
    $path = $req.Url.AbsolutePath.TrimEnd('/')
    if ([string]::IsNullOrEmpty($path)) { $path = '/' }

    try {
        switch -Regex ($path) {
            '^/$' {
                Serve-StaticFile $Context 'index.html'
                return
            }
            '^/api/health$' {
                if ($req.HttpMethod -ne 'GET') { break }
                Write-JsonResponse $Context @{ ok = $true; health = (Get-HubHealthDto); activity = (Get-HubActivityLog) }
                return
            }
            '^/api/activity$' {
                if ($req.HttpMethod -ne 'GET') { break }
                Write-JsonResponse $Context @{ ok = $true; activity = (Get-HubActivityLog) }
                return
            }
            '^/api/refresh$' {
                if ($req.HttpMethod -ne 'POST') { break }
                $r = Invoke-HubRefresh
                Write-JsonResponse $Context @{ ok = $r.ok; health = $r.health; activity = (Get-HubActivityLog) }
                return
            }
            '^/api/install-driver$' {
                if ($req.HttpMethod -ne 'POST') { break }
                $r = Invoke-HubInstallDriver
                Write-JsonResponse $Context @{
                    ok = $r.ok; skipped = $r.skipped; message = $r.message
                    health = $r.health; activity = (Get-HubActivityLog)
                }
                return
            }
            '^/api/start-gemy$' {
                if ($req.HttpMethod -ne 'POST') { break }
                $body = Read-RequestJson $Context
                $noVision = $false
                $noGemmaMood = $false
                if ($body.PSObject.Properties['noVision']) { $noVision = [bool]$body.noVision }
                if ($body.PSObject.Properties['noGemmaMood']) { $noGemmaMood = [bool]$body.noGemmaMood }
                $r = Invoke-HubStartGemy -NoVision:$noVision -NoGemmaMood:$noGemmaMood
                Write-JsonResponse $Context @{
                    ok = $r.ok; message = $r.message
                    health = (Get-HubHealthDto); activity = (Get-HubActivityLog)
                }
                return
            }
            '^/api/hat-panel$' {
                if ($req.HttpMethod -ne 'POST') { break }
                $r = Invoke-HubHatPanel
                Write-JsonResponse $Context @{
                    ok = $r.ok; message = $r.message; activity = (Get-HubActivityLog)
                }
                return
            }
            '^/api/cleanup$' {
                if ($req.HttpMethod -ne 'POST') { break }
                $r = Invoke-HubCleanup
                Write-JsonResponse $Context @{
                    ok = $r.ok; message = $r.message
                    health = $r.health; activity = (Get-HubActivityLog)
                }
                return
            }
            '^/api/board-log$' {
                if ($req.HttpMethod -ne 'GET') { break }
                $lines = 80
                $q = $req.QueryString['lines']
                if ($q) { [void][int]::TryParse($q, [ref]$lines) }
                $r = Get-HubBoardLog -Lines $lines
                Write-JsonResponse $Context $r
                return
            }
            '^/api/board-processes$' {
                if ($req.HttpMethod -ne 'GET') { break }
                $r = Get-HubBoardProcesses
                Write-JsonResponse $Context $r
                return
            }
            default {
                if ($path -match '^/(index\.html|styles\.css|app\.js|favicon\.ico)$') {
                    Serve-StaticFile $Context ($path.TrimStart('/'))
                    return
                }
            }
        }
        Write-TextResponse $Context 'Not found' 'text/plain' 404
    } catch {
        Write-JsonResponse $Context @{
            ok = $false; error = $_.Exception.Message; activity = (Get-HubActivityLog)
        } 500
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

$listenPort = Find-HubPort
$prefix = "http://127.0.0.1:$listenPort/"
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($prefix)

Add-HubActivity 'Gemy Control Center (web) starting...'

try {
    $listener.Start()
} catch {
    Write-Host "Failed to bind $prefix - try closing another Control Center window." -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

$url = "http://127.0.0.1:$listenPort/"
Write-Host ""
Write-Host "  Gemy Control Center" -ForegroundColor Cyan
Write-Host "  $url" -ForegroundColor Green
Write-Host "  Leave this window open while using the dashboard. Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $url | Out-Null
}

while ($listener.IsListening) {
    try {
        $ctx = $listener.GetContext()
        Invoke-HubRoute $ctx
    } catch {
        if ($listener.IsListening) {
            Write-Host "Request error: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}
