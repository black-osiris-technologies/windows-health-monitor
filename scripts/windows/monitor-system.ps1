param(
    [int]$IntervalSeconds = 10,
    [string]$OutputDir = ".\monitor-logs",
    [int]$RetentionDays = 3
)

$ErrorActionPreference = "SilentlyContinue"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
Add-Type -AssemblyName Microsoft.VisualBasic

$currentHour = $null
$metricsPath = $null
$eventsPath = $null
$errorsPath = Join-Path $OutputDir "monitor-errors.log"
$cpuCount = [Environment]::ProcessorCount
$lastTotalCpu = $null
$lastSampleTime = $null

function Set-LogFiles {
    $hour = Get-Date -Format "yyyyMMdd-HH"
    if ($script:currentHour -eq $hour) {
        return
    }

    $script:currentHour = $hour
    $script:metricsPath = Join-Path $OutputDir "metrics-$hour.csv"
    $script:eventsPath = Join-Path $OutputDir "events-$hour.log"

    if (-not (Test-Path -LiteralPath $script:metricsPath)) {
        "Timestamp,CpuPercent,AvailableMB,DiskReadMBps,DiskWriteMBps,GpuTempC,GpuUtilPercent,GpuMemoryUsedMB,TopCpuProcesses" |
            Out-File -FilePath $script:metricsPath -Encoding utf8
    }

    if ($RetentionDays -gt 0) {
        $cutoff = (Get-Date).AddDays(-$RetentionDays)
        Get-ChildItem -LiteralPath $OutputDir -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $cutoff -and $_.Name -match "^(metrics|events)-" } |
            Remove-Item -Force
    }
}

function Get-TotalProcessCpuSeconds {
    $sum = 0.0
    Get-Process | ForEach-Object {
        if ($_.CPU) {
            $sum += $_.CPU
        }
    }
    return $sum
}

Set-LogFiles
Write-Host "Logging metrics to $OutputDir, rotating hourly, retaining $RetentionDays days."
Write-Host "Press Ctrl+C to stop."

while ($true) {
    try {
        $now = Get-Date
        Set-LogFiles

        $totalCpu = Get-TotalProcessCpuSeconds
        $cpuPercent = ""
        if ($null -ne $lastTotalCpu -and $null -ne $lastSampleTime) {
            $elapsed = ($now - $lastSampleTime).TotalSeconds
            if ($elapsed -gt 0) {
                $cpuPercent = [math]::Round((($totalCpu - $lastTotalCpu) / ($elapsed * $cpuCount)) * 100, 2)
            }
        }
        $lastTotalCpu = $totalCpu
        $lastSampleTime = $now

        $info = [Microsoft.VisualBasic.Devices.ComputerInfo]::new()
        $availableMb = [math]::Round($info.AvailablePhysicalMemory / 1MB, 0)

        $diskRead = 0.0
        $diskWrite = 0.0
        Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk |
            Where-Object { $_.Name -ne "_Total" } |
            ForEach-Object {
                $diskRead += $_.DiskReadBytesPersec
                $diskWrite += $_.DiskWriteBytesPersec
            }
        $diskReadMbps = [math]::Round($diskRead / 1MB, 2)
        $diskWriteMbps = [math]::Round($diskWrite / 1MB, 2)

        $gpuTemp = ""
        $gpuUtil = ""
        $gpuMem = ""
        $nvidia = & "$env:WINDIR\system32\nvidia-smi.exe" --query-gpu=temperature.gpu,utilization.gpu,memory.used --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -eq 0 -and $nvidia) {
            $parts = $nvidia.Split(",").Trim()
            if ($parts.Count -ge 3) {
                $gpuTemp = $parts[0]
                $gpuUtil = $parts[1]
                $gpuMem = $parts[2]
            }
        }

        $top = Get-Process |
            Sort-Object CPU -Descending |
            Select-Object -First 5 |
            ForEach-Object { "$($_.ProcessName):$([math]::Round($_.CPU,1))" }
        $topText = ($top -join " | ").Replace('"', "'")

        $line = '"{0}",{1},{2},{3},{4},{5},{6},{7},"{8}"' -f `
            $now.ToString("yyyy-MM-dd HH:mm:ss"),
            $cpuPercent,
            $availableMb,
            $diskReadMbps,
            $diskWriteMbps,
            $gpuTemp,
            $gpuUtil,
            $gpuMem,
            $topText

        Add-Content -Path $metricsPath -Value $line

        Get-WinEvent -FilterHashtable @{LogName="System"; StartTime=$now.AddSeconds(-$IntervalSeconds)} |
            Where-Object {
                $_.ProviderName -match "nvlddmkm|Display|Kernel-Power|Kernel-Processor-Power|disk|Ntfs|USB|stor|WHEA"
            } |
            ForEach-Object {
                Add-Content -Path $eventsPath -Value ("[{0}] {1} {2} {3}: {4}" -f $_.TimeCreated, $_.ProviderName, $_.Id, $_.LevelDisplayName, ($_.Message -replace "\s+", " "))
            }
    } catch {
        Add-Content -Path $errorsPath -Value ("[{0}] {1}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $_.Exception.Message)
    }

    Start-Sleep -Seconds $IntervalSeconds
}
