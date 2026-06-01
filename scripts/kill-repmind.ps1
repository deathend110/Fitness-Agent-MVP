$ErrorActionPreference = 'Stop'

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$processNames = @('node.exe', 'python.exe', 'pythonw.exe', 'uv.exe')
$matchPatterns = @(
    '*RepMind*',
    "*$projectRoot*"
)

function Test-ProjectProcess {
    param(
        [string]$ExecutablePath,
        [string]$CommandLine
    )

    foreach ($candidate in @($ExecutablePath, $CommandLine)) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        foreach ($pattern in $matchPatterns) {
            if ($candidate -like $pattern) {
                return $true
            }
        }
    }

    return $false
}

function Get-ProjectProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -in $processNames -and (
                Test-ProjectProcess -ExecutablePath $_.ExecutablePath -CommandLine $_.CommandLine
            )
        } |
        Sort-Object ProcessId
}

$projectProcesses = @(Get-ProjectProcesses)

if (-not $projectProcesses.Count) {
    Write-Host 'No RepMind node/python/uv processes were found.'
    exit 0
}

Write-Host 'Stopping these RepMind-related processes:'
$projectProcesses |
    Select-Object ProcessId, Name, CommandLine |
    Format-Table -AutoSize

$stoppedIds = @()
foreach ($processInfo in $projectProcesses) {
    try {
        Stop-Process -Id $processInfo.ProcessId -Force -ErrorAction Stop
        $stoppedIds += $processInfo.ProcessId
    } catch {
        Write-Warning "Failed to stop PID=$($processInfo.ProcessId) Name=$($processInfo.Name) Error=$($_.Exception.Message)"
    }
}

Start-Sleep -Milliseconds 800

$remainingProcesses = @(Get-ProjectProcesses)

if ($remainingProcesses.Count) {
    Write-Warning 'Some matching processes are still running:'
    $remainingProcesses |
        Select-Object ProcessId, Name, CommandLine |
        Format-Table -AutoSize
    exit 1
}

if ($stoppedIds.Count) {
    Write-Host "Stopped $($stoppedIds.Count) RepMind-related process(es)."
    exit 0
}

Write-Warning 'No matching process could be stopped. Check permissions or process state.'
exit 1
