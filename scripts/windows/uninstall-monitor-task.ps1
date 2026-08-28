[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$TaskName = 'Windows Health Monitor',
    [string]$InstallDir = (Join-Path $env:ProgramData 'WindowsHealthMonitor'),
    [switch]$RemoveData
)

$ErrorActionPreference = 'Stop'

if ($PSCmdlet.ShouldProcess($TaskName, 'Stop and unregister background monitor')) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
}

if ($RemoveData -and (Test-Path -LiteralPath $InstallDir)) {
    $resolved = (Resolve-Path -LiteralPath $InstallDir).Path
    $programData = (Resolve-Path -LiteralPath $env:ProgramData).Path
    if (-not $resolved.StartsWith($programData, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove data outside ProgramData: $resolved"
    }
    if ($PSCmdlet.ShouldProcess($resolved, 'Remove monitor runtime, logs, and crash archives')) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
