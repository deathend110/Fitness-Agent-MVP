import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

test('start-repmind.bat 会通过脚本相对路径调用 PowerShell 启动器', () => {
  const source = fs.readFileSync(new URL('../start-repmind.bat', import.meta.url), 'utf8')

  assert.match(source, /@echo off/i)
  assert.match(source, /set\s+"SCRIPT_DIR=%~dp0"/i)
  assert.match(
    source,
    /"%SystemRoot%\\System32\\WindowsPowerShell\\v1\.0\\powershell\.exe"\s+-NoProfile\s+-ExecutionPolicy\s+Bypass\s+-File\s+"%SCRIPT_DIR%scripts\\start-repmind\.ps1"/i,
  )
  assert.match(source, /exit\s+\/b\s+%ERRORLEVEL%/i)
})

test('start-repmind.ps1 会基于自身路径反推出仓库根目录并切换工作目录', () => {
  const source = fs.readFileSync(
    new URL('../scripts/start-repmind.ps1', import.meta.url),
    'utf8',
  )

  assert.match(source, /\$repoRoot\s*=\s*\[System\.IO\.Path\]::GetFullPath\(\(Join-Path \$PSScriptRoot '\.\.'\)\)/)
  assert.match(source, /Set-Location\s+-LiteralPath\s+\$repoRoot/)
  assert.match(source, /package\.json/)
  assert.match(source, /backend/)
  assert.match(source, /scripts/)
})

test('start-repmind.ps1 会检查 node、npm、uv 依赖并调用 kill-repmind 清理旧进程', () => {
  const source = fs.readFileSync(
    new URL('../scripts/start-repmind.ps1', import.meta.url),
    'utf8',
  )

  assert.match(source, /Get-Command\s+node\s+-ErrorAction\s+SilentlyContinue/)
  assert.match(source, /Get-Command\s+npm\s+-ErrorAction\s+SilentlyContinue/)
  assert.match(source, /Get-Command\s+uv\s+-ErrorAction\s+SilentlyContinue/)
  assert.match(source, /kill-repmind\.ps1/)
  assert.match(source, /&\s+\$killScript/)
})

test('start-repmind.ps1 会创建本地启动日志目录并后台拉起前后端', () => {
  const source = fs.readFileSync(
    new URL('../scripts/start-repmind.ps1', import.meta.url),
    'utf8',
  )

  assert.match(source, /tests[\\\/]reports[\\\/]local-launch/)
  assert.match(source, /Start-Process\s+-FilePath\s+'powershell(?:\.exe)?'/i)
  assert.match(source, /uv run python -m backend\.run_dev_server/)
  assert.match(source, /npm run dev -- --host 127\.0\.0\.1 --port 5173 --strictPort/)
})

test('start-repmind.ps1 会轮询前后端地址并在成功后打开默认浏览器', () => {
  const source = fs.readFileSync(
    new URL('../scripts/start-repmind.ps1', import.meta.url),
    'utf8',
  )

  assert.match(source, /http:\/\/127\.0\.0\.1:8000\/api\/health/)
  assert.match(source, /http:\/\/127\.0\.0\.1:5173/)
  assert.match(source, /Invoke-WebRequest/)
  assert.match(source, /Start-Process\s+\$frontendUrl/)
})
