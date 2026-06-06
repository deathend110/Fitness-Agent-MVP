# Local Quick Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 RepMind 增加一个 Windows 本地一键快捷启动入口，支持从任意位置双击触发、自动启动前后端并打开默认浏览器。

**Architecture:** 采用 `start-repmind.bat` 作为双击入口，实际启动编排集中到 `scripts/start-repmind.ps1`。PowerShell 脚本负责解析仓库根目录、检查依赖、清理旧进程、后台拉起前后端、轮询服务健康状态、打开浏览器并在单窗口中输出日志与失败提示。

**Tech Stack:** Windows Batch、PowerShell 7/Windows PowerShell、Node 内置测试、现有 Vite/FastAPI 启动命令、README/ARCHITECTURE 文档同步

---

## File Structure

- Create: `start-repmind.bat`
  - Windows 双击入口，只负责基于脚本相对路径调用 PowerShell 启动器。
- Create: `scripts/start-repmind.ps1`
  - 本地快捷启动主逻辑，负责仓库根目录解析、依赖检查、进程清理、服务拉起、健康轮询、浏览器打开和日志输出。
- Create: `tests/localLaunch.test.js`
  - 启动脚本的源码契约测试，锁定入口路径解析、依赖检查、日志目录、健康轮询和浏览器打开逻辑。
- Modify: `README.md`
  - 增加一键启动入口、依赖前提、双击使用方式、日志位置和停止方式。
- Modify: `ARCHITECTURE.md`
  - 增加本地快捷启动脚本在仓库中的职责说明，以及它与现有 `kill-repmind.ps1`、前后端启动链路的关系。

## Task 1: 搭建双击入口和路径解析骨架

**Files:**
- Create: `tests/localLaunch.test.js`
- Create: `start-repmind.bat`
- Create: `scripts/start-repmind.ps1`
- Test: `tests/localLaunch.test.js`

- [ ] **Step 1: 写入口骨架的失败测试**

```js
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
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `node --test tests/localLaunch.test.js`

Expected: FAIL，报 `start-repmind.bat` 或 `scripts/start-repmind.ps1` 不存在。

- [ ] **Step 3: 写最小入口实现**

`start-repmind.bat`

```bat
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\start-repmind.ps1"
```

`scripts/start-repmind.ps1`

```powershell
$ErrorActionPreference = 'Stop'

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$requiredPaths = @(
    (Join-Path $repoRoot 'package.json'),
    (Join-Path $repoRoot 'backend'),
    (Join-Path $repoRoot 'scripts')
)

foreach ($path in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "RepMind 工作区不完整，缺少路径：$path"
    }
}

Set-Location -LiteralPath $repoRoot
Write-Host "RepMind quick launcher root: $repoRoot"
```

- [ ] **Step 4: 再次运行测试并确认通过**

Run: `node --test tests/localLaunch.test.js`

Expected: PASS，`2` 个测试全部通过。

- [ ] **Step 5: 提交入口骨架**

```bash
git add tests/localLaunch.test.js start-repmind.bat scripts/start-repmind.ps1
git commit -m "新增本地快捷启动入口骨架"
```

## Task 2: 补齐依赖检查、旧进程清理和服务启动编排

**Files:**
- Modify: `tests/localLaunch.test.js`
- Modify: `scripts/start-repmind.ps1`
- Test: `tests/localLaunch.test.js`

- [ ] **Step 1: 为启动编排补失败测试**

在 `tests/localLaunch.test.js` 追加以下测试：

```js
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
```

- [ ] **Step 2: 运行测试并确认按预期失败**

Run: `node --test tests/localLaunch.test.js`

Expected: FAIL，新加断言找不到依赖检查、日志目录、`Start-Process` 或健康轮询代码。

- [ ] **Step 3: 写最小启动编排实现**

将 `scripts/start-repmind.ps1` 扩展为：

```powershell
$ErrorActionPreference = 'Stop'

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$requiredPaths = @(
    (Join-Path $repoRoot 'package.json'),
    (Join-Path $repoRoot 'backend'),
    (Join-Path $repoRoot 'scripts')
)

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
$backendLog = Join-Path $logDir "backend-$timestamp.log"

function Assert-Dependency {
    param(
        [string]$CommandName
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "缺少依赖：$CommandName"
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [System.Diagnostics.Process]$Process,
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

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

Assert-Dependency node
Assert-Dependency npm
Assert-Dependency uv

if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

& $killScript

$backendCommand = "& { Set-Location '$repoRoot'; uv run python -m backend.run_dev_server *>> '$backendLog' }"
$frontendCommand = "& { Set-Location '$repoRoot'; npm run dev -- --host 127.0.0.1 --port 5173 --strictPort *>> '$frontendLog' }"

$backendProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-Command', $backendCommand
) -WindowStyle Hidden -PassThru

$frontendProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-Command', $frontendCommand
) -WindowStyle Hidden -PassThru

Wait-HttpReady -Url $backendHealthUrl -Process $backendProcess -Name '后端'
Wait-HttpReady -Url $frontendUrl -Process $frontendProcess -Name '前端'

Start-Process $frontendUrl
```

- [ ] **Step 4: 运行测试并确认通过**

Run: `node --test tests/localLaunch.test.js`

Expected: PASS，所有启动器源码契约测试通过。

- [ ] **Step 5: 提交启动编排逻辑**

```bash
git add tests/localLaunch.test.js scripts/start-repmind.ps1
git commit -m "补齐本地快捷启动编排逻辑"
```

## Task 3: 补齐成功提示、日志尾随和项目文档

**Files:**
- Modify: `tests/localLaunch.test.js`
- Modify: `scripts/start-repmind.ps1`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Test: `tests/localLaunch.test.js`

- [ ] **Step 1: 为成功提示、日志尾随和文档同步写失败测试**

在 `tests/localLaunch.test.js` 追加：

```js
test('start-repmind.ps1 会打印成功摘要、日志位置和 stop:all 提示，并持续尾随日志', () => {
  const source = fs.readFileSync(
    new URL('../scripts/start-repmind.ps1', import.meta.url),
    'utf8',
  )

  assert.match(source, /Write-Host\s+"RepMind 已启动"/)
  assert.match(source, /Write-Host\s+"前端：\$frontendUrl"/)
  assert.match(source, /Write-Host\s+"后端健康检查：\$backendHealthUrl"/)
  assert.match(source, /Write-Host\s+"停止服务：npm run stop:all"/)
  assert.match(source, /Get-Content\s+-Path\s+@?\(\$backendLog,\s*\$frontendLog\)\s+-Wait/)
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `node --test tests/localLaunch.test.js`

Expected: FAIL，当前脚本还没有成功摘要和日志尾随输出。

- [ ] **Step 3: 完成启动器收口并同步 README**

在 `scripts/start-repmind.ps1` 末尾补上：

```powershell
Write-Host ''
Write-Host 'RepMind 已启动'
Write-Host "前端：$frontendUrl"
Write-Host "后端健康检查：$backendHealthUrl"
Write-Host "前端日志：$frontendLog"
Write-Host "后端日志：$backendLog"
Write-Host '停止服务：npm run stop:all'
Write-Host ''
Write-Host '以下开始持续输出启动日志，按 Ctrl+C 可关闭当前窗口。'

Get-Content -Path @($backendLog, $frontendLog) -Wait
```

在 `README.md` 的“启动”章节追加：

```md
一键快捷启动（Windows）：

```powershell
.\start-repmind.bat
```

说明：

- 支持从仓库根目录双击，或通过桌面快捷方式从任意位置触发
- 依赖本机已安装 `node`、`npm`、`uv`
- 启动成功后会自动打开默认浏览器到 `http://127.0.0.1:5173`
- 启动器窗口会持续输出前后端日志
- 如需停止当前项目相关本地进程，可执行 `npm run stop:all`
```
```

- [ ] **Step 4: 同步 ARCHITECTURE 文档**

在 `ARCHITECTURE.md` 的脚本/运行说明位置补充：

```md
## 本地快捷启动

- [start-repmind.bat](start-repmind.bat)
  - Windows 双击入口
  - 只负责基于脚本相对路径调用 PowerShell 启动器

- [scripts/start-repmind.ps1](scripts/start-repmind.ps1)
  - 负责解析仓库根目录、检查 `node / npm / uv`、调用 `kill-repmind.ps1` 清理旧进程
  - 负责后台启动 Vite 与 FastAPI、轮询 `http://127.0.0.1:5173` 和 `http://127.0.0.1:8000/api/health`
  - 服务就绪后自动打开默认浏览器，并在单个启动器窗口中持续输出日志
```

- [ ] **Step 5: 运行测试并做本地快捷启动验收**

Run: `node --test tests/localLaunch.test.js`

Expected: PASS，新增启动器源码契约测试全部通过。

Run: `.\start-repmind.bat`

Expected:

- 当前窗口先打印仓库路径、依赖检查和启动状态
- 默认浏览器自动打开 `http://127.0.0.1:5173`
- 当前窗口继续输出前后端日志

Run: `npm run stop:all`

Expected: 项目相关 node/python/uv 进程被清理。

- [ ] **Step 6: 提交文档与验收收口**

```bash
git add tests/localLaunch.test.js scripts/start-repmind.ps1 README.md ARCHITECTURE.md
git commit -m "补充本地快捷启动文档与验收说明"
```
