import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

test('start-repmind.bat 会通过脚本相对路径调用 PowerShell 启动器', () => {
  const source = fs.readFileSync(new URL('../start-repmind.bat', import.meta.url), 'utf8')

  assert.match(source, /@echo off/i)
  assert.match(source, /set\s+"SCRIPT_DIR=%~dp0"/i)
  assert.match(
    source,
    /powershell(?:\.exe)?\s+-NoProfile\s+-ExecutionPolicy\s+Bypass\s+-File\s+"%SCRIPT_DIR%scripts\\start-repmind\.ps1"/i,
  )
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
