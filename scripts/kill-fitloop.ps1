$ErrorActionPreference = 'Stop'

$newScriptPath = Join-Path $PSScriptRoot 'kill-repmind.ps1'

if (-not (Test-Path -LiteralPath $newScriptPath)) {
    Write-Error "未找到新版停服脚本：$newScriptPath"
}

# 兼容旧入口：保留 kill-fitloop.ps1，内部统一转发到新版 RepMind 脚本。
& $newScriptPath
exit $LASTEXITCODE
