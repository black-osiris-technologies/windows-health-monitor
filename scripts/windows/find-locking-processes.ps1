param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$source = @"
using System;
using System.Runtime.InteropServices;

public static class RestartManager
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RM_UNIQUE_PROCESS
    {
        public int dwProcessId;
        public System.Runtime.InteropServices.ComTypes.FILETIME ProcessStartTime;
    }

    public enum RM_APP_TYPE
    {
        RmUnknownApp = 0,
        RmMainWindow = 1,
        RmOtherWindow = 2,
        RmService = 3,
        RmExplorer = 4,
        RmConsole = 5,
        RmCritical = 1000
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct RM_PROCESS_INFO
    {
        public RM_UNIQUE_PROCESS Process;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
        public string strAppName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
        public string strServiceShortName;
        public RM_APP_TYPE ApplicationType;
        public uint AppStatus;
        public uint TSSessionId;
        [MarshalAs(UnmanagedType.Bool)]
        public bool bRestartable;
    }

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmStartSession(out uint pSessionHandle, int dwSessionFlags, string strSessionKey);

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmRegisterResources(uint pSessionHandle, uint nFiles, string[] rgsFilenames, uint nApplications, RM_UNIQUE_PROCESS[] rgApplications, uint nServices, string[] rgsServiceNames);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmGetList(uint dwSessionHandle, out uint pnProcInfoNeeded, ref uint pnProcInfo, [In, Out] RM_PROCESS_INFO[] rgAffectedApps, ref uint lpdwRebootReasons);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmEndSession(uint pSessionHandle);
}
"@

Add-Type -TypeDefinition $source -ErrorAction SilentlyContinue

$resolved = (Resolve-Path -LiteralPath $Path).Path
$files = if (Test-Path -LiteralPath $resolved -PathType Container) {
    Get-ChildItem -LiteralPath $resolved -Recurse -Force -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
} else {
    @($resolved)
}

if (-not $files -or $files.Count -eq 0) {
    $files = @($resolved)
}

$session = 0
$key = [Guid]::NewGuid().ToString()
$result = [RestartManager]::RmStartSession([ref]$session, 0, $key)
if ($result -ne 0) {
    throw "RmStartSession failed: $result"
}

try {
    foreach ($chunk in @($files | ForEach-Object -Begin { $batch = @() } -Process {
        $batch += $_
        if ($batch.Count -ge 100) {
            ,$batch
            $batch = @()
        }
    } -End {
        if ($batch.Count -gt 0) { ,$batch }
    })) {
        [void][RestartManager]::RmRegisterResources($session, [uint32]$chunk.Count, [string[]]$chunk, 0, $null, 0, $null)
    }

    $needed = 0
    $count = 0
    $reasons = 0
    [void][RestartManager]::RmGetList($session, [ref]$needed, [ref]$count, $null, [ref]$reasons)

    if ($needed -eq 0) {
        return
    }

    $count = $needed
    $processInfo = New-Object RestartManager+RM_PROCESS_INFO[] $count
    $result = [RestartManager]::RmGetList($session, [ref]$needed, [ref]$count, $processInfo, [ref]$reasons)
    if ($result -ne 0) {
        throw "RmGetList failed: $result"
    }

    $processInfo |
        Select-Object -First $count |
        ForEach-Object {
            $proc = Get-Process -Id $_.Process.dwProcessId -ErrorAction SilentlyContinue
            [PSCustomObject]@{
                ProcessId = $_.Process.dwProcessId
                AppName = $_.strAppName
                ProcessName = $proc.ProcessName
                MainWindowTitle = $proc.MainWindowTitle
                Path = $proc.Path
            }
        }
}
finally {
    [void][RestartManager]::RmEndSession($session)
}
