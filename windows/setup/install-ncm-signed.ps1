$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$log = Join-RobotPath "logs", "ncm-setup.log"
function Log($msg) { "$(Get-Date -Format o) $msg" | Tee-Object -FilePath $log -Append }

$drvDir  = Join-RobotPath "drivers", "ncm", "coral-ncm-drv"
$inf     = Join-Path $drvDir "coral-ncm.inf"
$cat     = Join-Path $drvDir "coral-ncm.cat"

Log "=== Signed NCM driver install ==="

# 1. Build catalog over the driver folder
try {
    if (Test-Path $cat) { Remove-Item $cat -Force }
    New-FileCatalog -Path $drvDir -CatalogFilePath $cat -CatalogVersion 2.0 -ErrorAction Stop | Out-Null
    Log "Catalog created: $cat (exists=$(Test-Path $cat))"
} catch {
    Log "New-FileCatalog failed: $_"
    return
}

# 2. Create / reuse self-signed code-signing cert
$subject = "CN=CoralNCM Driver Signing"
$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -eq $subject } | Select-Object -First 1
if (-not $cert) {
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
        -CertStoreLocation Cert:\LocalMachine\My -KeyUsage DigitalSignature `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3") -ErrorAction Stop
    Log "Created cert thumbprint=$($cert.Thumbprint)"
} else {
    Log "Reusing cert thumbprint=$($cert.Thumbprint)"
}

# 3. Trust the cert (Root + TrustedPublisher) so Windows accepts the package
foreach ($store in @("Root","TrustedPublisher")) {
    try {
        $s = New-Object System.Security.Cryptography.X509Certificates.X509Store($store,"LocalMachine")
        $s.Open("ReadWrite")
        $s.Add($cert)
        $s.Close()
        Log "Added cert to LocalMachine\$store"
    } catch { Log "Add to $store failed: $_" }
}

# 4. Sign the catalog
try {
    $res = Set-AuthenticodeSignature -FilePath $cat -Certificate $cert -ErrorAction Stop
    Log "Catalog signature status: $($res.Status)"
} catch { Log "Sign catalog failed: $_" }

# 5. Add+install driver package (binds to matching CDC NCM device)
pnputil /add-driver $inf /install 2>&1 | ForEach-Object { Log $_ }

Start-Sleep -Seconds 3
pnputil /scan-devices 2>&1 | Out-Null
Start-Sleep -Seconds 2

Get-PnpDevice | Where-Object { $_.InstanceId -match "VID_1D6B&PID_0104&MI_00" } | ForEach-Object {
    Log "Device: $($_.FriendlyName) Status=$($_.Status) Problem=$($_.Problem)"
}
Get-NetAdapter | ForEach-Object { Log "Adapter: $($_.Name) | $($_.InterfaceDescription) | $($_.Status)" }

# 6. Enable Internet Connection Sharing: active internet -> UsbNcm adapter
try {
    $netShare = New-Object -ComObject HNetCfg.HNetShare
    $publicConn = $null; $privateConn = $null
    foreach ($conn in @($netShare.EnumEveryConnection())) {
        $props = $netShare.NetConnectionProps($conn)
        Log "Conn: $($props.Name) | Device=$($props.DeviceName)"
        if ($props.DeviceName -match "UsbNcm|NCM Host|NCM") { $privateConn = $conn }
        elseif ($props.DeviceName -notmatch "Virtual|Loopback|Hyper-V|VMware|VirtualBox|UsbNcm|NCM"
                -and -not $publicConn) { $publicConn = $conn }
    }
    if ($publicConn -and $privateConn) {
        $pubCfg = $netShare.INetSharingConfigurationForINetConnection($publicConn)
        if ($pubCfg.SharingEnabled) { $pubCfg.DisableSharing(); Start-Sleep 1; $pubCfg = $netShare.INetSharingConfigurationForINetConnection($publicConn) }
        $privCfg = $netShare.INetSharingConfigurationForINetConnection($privateConn)
        if ($privCfg.SharingEnabled) { $privCfg.DisableSharing(); Start-Sleep 1 }
        $pubCfg.EnableSharing(0)   # 0 = ICSSHARINGTYPE_PUBLIC
        $privCfg = $netShare.INetSharingConfigurationForINetConnection($privateConn)
        $privCfg.EnableSharing(1)  # 1 = ICSSHARINGTYPE_PRIVATE
        Log "ICS enabled: public=$($netShare.NetConnectionProps($publicConn).Name) private=$($netShare.NetConnectionProps($privateConn).Name)"
    } else {
        Log "ICS deferred: public=$([bool]$publicConn) private=$([bool]$privateConn)"
    }
} catch { Log "ICS setup error: $_" }

Log "=== Done ==="
