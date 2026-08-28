[CmdletBinding()]
param(
    [string]$TaskName = 'Windows Health Monitor',
    [string]$InstallDir = (Join-Path $env:ProgramData 'WindowsHealthMonitor')
)

$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
$statusPath = Join-Path $InstallDir 'status.json'
$status = if (Test-Path -LiteralPath $statusPath) {
    Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
} else {
    $null
}
$lastTaskResultHex = '0x{0:X8}' -f ([uint32]$taskInfo.LastTaskResult)
$heartbeatAgeSeconds = if ($null -ne $status -and $null -ne $status.last_iteration_at) {
    [math]::Round(
        ([DateTimeOffset]::Now - [DateTimeOffset]::Parse($status.last_iteration_at)).TotalSeconds,
        1
    )
} else {
    $null
}

[pscustomobject]@{
    TaskName = $task.TaskName
    TaskState = $task.State
    LastTaskResult = $taskInfo.LastTaskResult
    LastTaskResultHex = $lastTaskResultHex
    LastRunTime = $taskInfo.LastRunTime
    NextRunTime = $taskInfo.NextRunTime
    MonitorVersion = $status.version
    MonitorPid = $status.pid
    MonitorStartedAt = $status.started_at
    LastIterationAt = $status.last_iteration_at
    HeartbeatAgeSeconds = $heartbeatAgeSeconds
    LastError = $status.last_error
    CrashArchiveStatus = $status.crash_archive_status
}
