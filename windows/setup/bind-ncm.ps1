. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$log = Join-RobotPath "logs", "ncm-setup.log"
function Log($msg) { "$(Get-Date -Format o) $msg" | Tee-Object -FilePath $log -Append }

Log "=== Force-binding UsbNcm driver to CDC NCM device ==="

$source = @"
using System;
using System.Runtime.InteropServices;

public static class DrvBind
{
    const int SPDIT_CLASSDRIVER = 0x00000004;
    const int DI_ENUMSINGLEINF  = 0x00010000;

    [StructLayout(LayoutKind.Sequential)]
    public struct SP_DEVINFO_DATA {
        public uint cbSize;
        public Guid ClassGuid;
        public uint DevInst;
        public IntPtr Reserved;
    }

    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct SP_DRVINFO_DATA {
        public uint cbSize;
        public uint DriverType;
        public IntPtr Reserved;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string Description;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string MfgName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string ProviderName;
        public System.Runtime.InteropServices.ComTypes.FILETIME DriverDate;
        public ulong DriverVersion;
    }

    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct SP_DEVINSTALL_PARAMS {
        public uint cbSize;
        public uint Flags;
        public uint FlagsEx;
        public IntPtr hwndParent;
        public IntPtr InstallMsgHandler;
        public IntPtr InstallMsgHandlerContext;
        public IntPtr FileQueue;
        public IntPtr ClassInstallReserved;
        public uint Reserved;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=260)] public string DriverPath;
    }

    [DllImport("setupapi.dll", SetLastError=true)]
    static extern IntPtr SetupDiCreateDeviceInfoList(IntPtr ClassGuid, IntPtr hwndParent);

    [DllImport("setupapi.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool SetupDiOpenDeviceInfo(IntPtr DeviceInfoSet, string DeviceInstanceId, IntPtr hwndParent, int Flags, ref SP_DEVINFO_DATA did);

    [DllImport("setupapi.dll", SetLastError=true, CharSet=CharSet.Unicode, EntryPoint="SetupDiGetDeviceInstallParamsW")]
    static extern bool SetupDiGetDeviceInstallParams(IntPtr DeviceInfoSet, ref SP_DEVINFO_DATA did, ref SP_DEVINSTALL_PARAMS p);

    [DllImport("setupapi.dll", SetLastError=true, CharSet=CharSet.Unicode, EntryPoint="SetupDiSetDeviceInstallParamsW")]
    static extern bool SetupDiSetDeviceInstallParams(IntPtr DeviceInfoSet, ref SP_DEVINFO_DATA did, ref SP_DEVINSTALL_PARAMS p);

    [DllImport("setupapi.dll", SetLastError=true)]
    static extern bool SetupDiBuildDriverInfoList(IntPtr DeviceInfoSet, ref SP_DEVINFO_DATA did, uint DriverType);

    [DllImport("setupapi.dll", SetLastError=true, CharSet=CharSet.Unicode, EntryPoint="SetupDiEnumDriverInfoW")]
    static extern bool SetupDiEnumDriverInfo(IntPtr DeviceInfoSet, ref SP_DEVINFO_DATA did, uint DriverType, uint MemberIndex, ref SP_DRVINFO_DATA drv);

    [DllImport("setupapi.dll", SetLastError=true, CharSet=CharSet.Unicode, EntryPoint="SetupDiSetSelectedDriverW")]
    static extern bool SetupDiSetSelectedDriver(IntPtr DeviceInfoSet, ref SP_DEVINFO_DATA did, ref SP_DRVINFO_DATA drv);

    [DllImport("setupapi.dll", SetLastError=true)]
    static extern bool SetupDiDestroyDeviceInfoList(IntPtr DeviceInfoSet);

    [DllImport("newdev.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool DiInstallDevice(IntPtr hParent, IntPtr lpInfoSet, ref SP_DEVINFO_DATA did, ref SP_DRVINFO_DATA drv, uint Flags, out bool NeedReboot);

    public static string Bind(string instanceId, string infPath, string wantDesc)
    {
        IntPtr set = SetupDiCreateDeviceInfoList(IntPtr.Zero, IntPtr.Zero);
        if (set == IntPtr.Zero || set == new IntPtr(-1))
            return "FAIL CreateDeviceInfoList err=" + Marshal.GetLastWin32Error();

        try {
            SP_DEVINFO_DATA did = new SP_DEVINFO_DATA();
            did.cbSize = (uint)Marshal.SizeOf(typeof(SP_DEVINFO_DATA));
            if (!SetupDiOpenDeviceInfo(set, instanceId, IntPtr.Zero, 0, ref did))
                return "FAIL OpenDeviceInfo err=" + Marshal.GetLastWin32Error();

            SP_DEVINSTALL_PARAMS p = new SP_DEVINSTALL_PARAMS();
            p.cbSize = (uint)Marshal.SizeOf(typeof(SP_DEVINSTALL_PARAMS));
            p.Flags = DI_ENUMSINGLEINF;
            p.DriverPath = infPath;
            if (!SetupDiSetDeviceInstallParams(set, ref did, ref p))
                return "FAIL SetInstallParams cbSize=" + p.cbSize + " err=" + Marshal.GetLastWin32Error();

            if (!SetupDiBuildDriverInfoList(set, ref did, SPDIT_CLASSDRIVER))
                return "FAIL BuildDriverInfoList err=" + Marshal.GetLastWin32Error();

            SP_DRVINFO_DATA drv = new SP_DRVINFO_DATA();
            drv.cbSize = (uint)Marshal.SizeOf(typeof(SP_DRVINFO_DATA));
            bool found = false;
            string seen = "";
            for (uint i = 0; SetupDiEnumDriverInfo(set, ref did, SPDIT_CLASSDRIVER, i, ref drv); i++) {
                seen += "[" + drv.Description + "] ";
                if (drv.Description != null && drv.Description.IndexOf(wantDesc, StringComparison.OrdinalIgnoreCase) >= 0) {
                    found = true;
                    break;
                }
                drv.cbSize = (uint)Marshal.SizeOf(typeof(SP_DRVINFO_DATA));
            }
            if (!found)
                return "FAIL driver '" + wantDesc + "' not found in INF. Saw: " + seen;

            if (!SetupDiSetSelectedDriver(set, ref did, ref drv))
                return "FAIL SetSelectedDriver err=" + Marshal.GetLastWin32Error();

            bool reboot;
            if (!DiInstallDevice(IntPtr.Zero, set, ref did, ref drv, 0, out reboot))
                return "FAIL DiInstallDevice err=" + Marshal.GetLastWin32Error();

            return "OK installed '" + drv.Description + "' reboot=" + reboot;
        }
        finally {
            SetupDiDestroyDeviceInfoList(set);
        }
    }
}
"@

Add-Type -TypeDefinition $source -Language CSharp

$dev = Get-PnpDevice | Where-Object { $_.InstanceId -match "VID_1D6B&PID_0104&MI_00" } | Select-Object -First 1
if (-not $dev) { Log "ERROR: CDC NCM device not found"; exit 1 }
Log "Device: $($dev.FriendlyName) Status=$($dev.Status) Instance=$($dev.InstanceId)"

$inf = "C:\Windows\System32\DriverStore\FileRepository\usbncm.inf_amd64_9957a38c3d2283ed\usbncm.inf"
Log "INF: $inf"

$res = [DrvBind]::Bind($dev.InstanceId, $inf, "UsbNcm Host Device")
Log "Bind result: $res"

Start-Sleep -Seconds 3
Get-PnpDevice | Where-Object { $_.InstanceId -match "VID_1D6B&PID_0104&MI_00" } | ForEach-Object {
    Log "After: $($_.FriendlyName) Status=$($_.Status) Problem=$($_.Problem)"
}
Get-NetAdapter | ForEach-Object { Log "Adapter: $($_.Name) | $($_.InterfaceDescription) | $($_.Status)" }

Log "=== Done bind phase ==="
