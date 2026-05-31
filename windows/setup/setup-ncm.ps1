. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$log = Join-RobotPath "logs", "ncm-setup.log"
function Log($msg) { "$(Get-Date -Format o) $msg" | Tee-Object -FilePath $log -Append }

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class NewDev {
    [DllImport("newdev.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool UpdateDriverForPlugAndPlayDevices(
        IntPtr hwndParent,
        string HardwareId,
        string FullInfPath,
        uint InstallFlags,
        out bool bRebootRequired);
}
"@

Log "Starting Coralboard NCM setup..."

$driverInf = "C:\Windows\System32\DriverStore\FileRepository\usbncm.inf_amd64_9957a38c3d2283ed\usbncm.inf"
$hardwareId = "USB\VID_1D6B&PID_0104&MI_00"
$installFlags = 0x00000001 -bor 0x00000004  # FORCE | NONINTERACTIVE

Log "Assigning UsbNcm driver from: $driverInf"
Log "Hardware ID: $hardwareId"

$reboot = $false
$result = [NewDev]::UpdateDriverForPlugAndPlayDevices([IntPtr]::Zero, $hardwareId, $driverInf, $installFlags, [ref]$reboot)
$err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
Log "UpdateDriverForPlugAndPlayDevices result=$result lastError=$err rebootRequired=$reboot"

Start-Sleep -Seconds 3
pnputil /scan-devices 2>&1 | ForEach-Object { Log $_ }
Start-Sleep -Seconds 2

Get-PnpDevice | Where-Object { $_.FriendlyName -match "NCM|UsbNcm" } | ForEach-Object {
    Log "PnP: $($_.FriendlyName) Status=$($_.Status) Problem=$($_.Problem)"
}

Get-NetAdapter | ForEach-Object {
    Log "Adapter: $($_.Name) | $($_.InterfaceDescription) | $($_.Status)"
}

try {
    $netShare = New-Object -ComObject HNetCfg.HNetShare
    $publicConn = $null
    $privateConn = $null

    foreach ($conn in @($netShare.EnumEveryConnection())) {
        $props = $netShare.NetConnectionProps($conn)
        Log "Connection: $($props.Name) | Device=$($props.DeviceName)"
        if ($props.DeviceName -match "UsbNcm|NCM Host|NCM") { $privateConn = $conn }
        elseif ($props.DeviceName -notmatch "Virtual|Loopback|Hyper-V|VMware|VirtualBox|UsbNcm|NCM"
                -and -not $publicConn) { $publicConn = $conn }
    }

    if ($publicConn -and $privateConn) {
        $publicCfg = $netShare.INetSharingConfigurationForINetConnection($publicConn)
        if ($publicCfg.SharingEnabled) {
            Log "ICS already enabled; toggling..."
            $publicCfg.DisableSharing()
            Start-Sleep -Seconds 1
            $publicCfg = $netShare.INetSharingConfigurationForINetConnection($publicConn)
        }
        $publicCfg.EnableSharing(0, $privateConn, "")
        Log "ICS enabled: public=$($netShare.NetConnectionProps($publicConn).Name) private=$($netShare.NetConnectionProps($privateConn).Name)"
    } else {
        Log "ICS skipped: could not find both adapters (public=$([bool]$publicConn) private=$([bool]$privateConn))"
    }
} catch {
    Log "ICS setup failed: $_"
}

Log "Done."
