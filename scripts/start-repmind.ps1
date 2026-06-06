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
Write-Host "RepMind quick launcher root: $repoRoot"
