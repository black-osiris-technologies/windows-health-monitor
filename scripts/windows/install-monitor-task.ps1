[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$TaskName = 'Windows Health Monitor',
    [string]$InstallDir = (Join-Path $env:ProgramData 'WindowsHealthMonitor'),
    [string]$PythonExe,
    [int]$IntervalSeconds = 60,
    [int]$GpuIntervalSeconds = 300,
    [int]$RetentionDays = 30,
    [int]$StartupLookbackHours = 72,
    [int]$StartupDelayMinutes = 2,
    [switch]$ArchiveCrashDumps,
    [string]$CrashDumpArchiveDir,
    [int]$CrashDumpRetention = 2
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this installer from an elevated PowerShell session.'
    }
}

function Protect-InstallDirectory {
    param([string]$Path)

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $system = ([Security.Principal.SecurityIdentifier]'S-1-5-18').Translate(
        [Security.Principal.NTAccount]
    ).Value
    $administrators = ([Security.Principal.SecurityIdentifier]'S-1-5-32-544').Translate(
        [Security.Principal.NTAccount]
    ).Value
    $inheritance = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    $propagation = [Security.AccessControl.PropagationFlags]::None
    $allow = [Security.AccessControl.AccessControlType]::Allow
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        $system, 'FullControl', $inheritance, $propagation, $allow
    ))
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        $administrators, 'FullControl', $inheritance, $propagation, $allow
    ))
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        $identity, 'Modify', $inheritance, $propagation, $allow
    ))
    Set-Acl -LiteralPath $Path -AclObject $acl
}

Assert-Administrator

if ($IntervalSeconds -lt 10) {
    throw 'IntervalSeconds must be at least 10 seconds.'
}
if ($GpuIntervalSeconds -lt $IntervalSeconds) {
    throw 'GpuIntervalSeconds must be greater than or equal to IntervalSeconds.'
}
if (
    $RetentionDays -lt 1 -or
    $StartupLookbackHours -lt 1 -or
    $StartupDelayMinutes -lt 0 -or
    $CrashDumpRetention -lt 1
) {
    throw 'Retention and startup lookback values must be positive.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = (Get-Command python.exe -ErrorAction Stop).Source
}
$PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
$pythonVersion = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or [version]$pythonVersion -lt [version]'3.11') {
    throw "Python 3.11 or newer is required; resolved version: $pythonVersion"
}

if (-not $PSCmdlet.ShouldProcess($TaskName, "Install and start background monitor")) {
    return
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Protect-InstallDirectory -Path $InstallDir

$venvDir = Join-Path $InstallDir 'venv'
if (-not (Test-Path -LiteralPath (Join-Path $venvDir 'Scripts\python.exe'))) {
    & $PythonExe -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to create the monitor virtual environment.'
    }
}

$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$venvPythonw = Join-Path $venvDir 'Scripts\pythonw.exe'
$sitePackages = & $venvPython -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($sitePackages)) {
    throw 'Failed to resolve the virtual environment site-packages directory.'
}
$sourcePackage = Join-Path $repoRoot 'src\windows_health_monitor'
$installedPackage = Join-Path $sitePackages 'windows_health_monitor'
$stagedPackage = Join-Path $sitePackages 'windows_health_monitor.new'
$backupPackage = Join-Path $sitePackages 'windows_health_monitor.previous'
foreach ($path in @($stagedPackage, $backupPackage)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}
Copy-Item -LiteralPath $sourcePackage -Destination $stagedPackage -Recurse -Force
Get-ChildItem -LiteralPath $stagedPackage -Directory -Filter '__pycache__' -Recurse |
    Remove-Item -Recurse -Force

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existingTask -and $existingTask.State -eq 'Running') {
    Stop-ScheduledTask -TaskName $TaskName
    $stopDeadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 250
        $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    } while (
        $null -ne $existingTask -and
        $existingTask.State -eq 'Running' -and
        (Get-Date) -lt $stopDeadline
    )
    if ($null -ne $existingTask -and $existingTask.State -eq 'Running') {
        Remove-Item -LiteralPath $stagedPackage -Recurse -Force
        throw "Timed out while stopping scheduled task: $TaskName"
    }
}

if (Test-Path -LiteralPath $installedPackage) {
    Move-Item -LiteralPath $installedPackage -Destination $backupPackage
}
try {
    Move-Item -LiteralPath $stagedPackage -Destination $installedPackage
} catch {
    if (Test-Path -LiteralPath $backupPackage) {
        Move-Item -LiteralPath $backupPackage -Destination $installedPackage
    }
    throw
}
if (Test-Path -LiteralPath $backupPackage) {
    Remove-Item -LiteralPath $backupPackage -Recurse -Force
}

$outputDir = Join-Path $InstallDir 'logs'
$statusFile = Join-Path $InstallDir 'status.json'
$arguments = @(
    '-m', 'windows_health_monitor', 'monitor',
    '--interval', $IntervalSeconds,
    '--gpu-interval', $GpuIntervalSeconds,
    '--output-dir', $outputDir,
    '--retention-days', $RetentionDays,
    '--startup-lookback-hours', $StartupLookbackHours,
    '--status-file', $statusFile
)
if ($ArchiveCrashDumps) {
    if ([string]::IsNullOrWhiteSpace($CrashDumpArchiveDir)) {
        $CrashDumpArchiveDir = Join-Path $InstallDir 'crash-dumps'
    }
    $arguments += @(
        '--crash-dump-archive-dir', $CrashDumpArchiveDir,
        '--crash-dump-retention', $CrashDumpRetention
    )
}
$argumentString = ($arguments | ForEach-Object {
    '"{0}"' -f ([string]$_).Replace('"', '\"')
}) -join ' '

$action = New-ScheduledTaskAction `
    -Execute $venvPythonw `
    -Argument $argumentString `
    -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -AtStartup
if ($StartupDelayMinutes -gt 0) {
    $trigger.Delay = "PT${StartupDelayMinutes}M"
}
$principal = New-ScheduledTaskPrincipal `
    -UserId 'SYSTEM' `
    -LogonType ServiceAccount `
    -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -Priority 7

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Low-overhead local diagnostics with durable Windows event and crash evidence.' `
    -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

$startDeadline = (Get-Date).AddSeconds(10)
do {
    Start-Sleep -Milliseconds 250
    $startedTask = Get-ScheduledTask -TaskName $TaskName
} while ($startedTask.State -ne 'Running' -and (Get-Date) -lt $startDeadline)
if ($startedTask.State -ne 'Running') {
    $lastResult = (Get-ScheduledTaskInfo -TaskName $TaskName).LastTaskResult
    throw "Scheduled task did not start (state=$($startedTask.State), result=$lastResult)."
}

[pscustomobject]@{
    TaskName = $TaskName
    InstallDirectory = $InstallDir
    LogDirectory = $outputDir
    StatusFile = $statusFile
    CrashDumpArchive = if ($ArchiveCrashDumps) { $CrashDumpArchiveDir } else { 'Disabled' }
}
