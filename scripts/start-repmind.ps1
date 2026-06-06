$ErrorActionPreference = 'Stop'

# 基于脚本目录反推仓库根目录，避免依赖外部启动时的当前工作目录。
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$requiredPaths = @(
    (Join-Path $repoRoot 'package.json'),
    (Join-Path $repoRoot 'backend'),
    (Join-Path $repoRoot 'scripts')
)

# 提前校验最小仓库结构，避免在错误目录中继续执行后续启动逻辑。
foreach ($path in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "RepMind 工作区不完整，缺少路径：$path"
    }
}

Set-Location -LiteralPath $repoRoot

$frontendUrl = 'http://127.0.0.1:5173'
$backendHealthUrl = 'http://127.0.0.1:8000/api/health'
$killScript = Join-Path $repoRoot 'scripts\kill-repmind.ps1'
$logDir = Join-Path $repoRoot 'tests\reports\local-launch'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$frontendLog = Join-Path $logDir "frontend-$timestamp.log"
$frontendErrorLog = Join-Path $logDir "frontend-$timestamp.err.log"
$backendLog = Join-Path $logDir "backend-$timestamp.log"
$backendErrorLog = Join-Path $logDir "backend-$timestamp.err.log"
$backendProcess = $null
$frontendProcess = $null

function Stop-LaunchProcesses {
    param(
        [System.Diagnostics.Process[]]$Processes
    )

    # 失败清理只回收本次拉起且仍存活的子进程，避免留下半启动状态。
    foreach ($process in $Processes) {
        if ($null -eq $process) {
            continue
        }

        try {
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction Stop
            }
        } catch {
            Write-Warning "清理启动子进程失败 PID=$($process.Id) Error=$($_.Exception.Message)"
        }
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [System.Diagnostics.Process]$Process,
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

    # 轮询健康地址时同时观察后台进程是否提前退出，便于把失败定位到对应日志。
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            throw "$Name 进程已提前退出，请查看日志。"
        }

        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "$Name 在 ${TimeoutSeconds}s 内未就绪：$Url"
}

# 启动器只做最小依赖断言，缺少任一命令时立即失败，避免留下半启动状态。
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw '缺少依赖：node'
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw '缺少依赖：npm'
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw '缺少依赖：uv'
}

if (-not (Test-Path -LiteralPath $killScript)) {
    throw "缺少旧进程清理脚本：$killScript"
}

if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

& $killScript

try {
    # 后台启动显式绑定工作目录和日志重定向，避免路径中包含引号时命令拼接失效。
    $backendProcess = Start-Process -FilePath 'uv' -ArgumentList @(
        'run',
        'python',
        '-m',
        'backend.run_dev_server'
    ) -WorkingDirectory $repoRoot `
      -RedirectStandardOutput $backendLog `
      -RedirectStandardError $backendErrorLog `
      -WindowStyle Hidden `
      -PassThru

    $frontendProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList @(
        'run',
        'dev',
        '--',
        '--host',
        '127.0.0.1',
        '--port',
        '5173',
        '--strictPort'
    ) -WorkingDirectory $repoRoot `
      -RedirectStandardOutput $frontendLog `
      -RedirectStandardError $frontendErrorLog `
      -WindowStyle Hidden `
      -PassThru

    Wait-HttpReady -Url $backendHealthUrl -Process $backendProcess -Name '后端'
    Wait-HttpReady -Url $frontendUrl -Process $frontendProcess -Name '前端'

    Start-Process $frontendUrl
} catch {
    Stop-LaunchProcesses -Processes @($backendProcess, $frontendProcess)
    throw
}
