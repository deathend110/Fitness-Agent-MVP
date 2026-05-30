# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。当前阶段聚焦一条最小但完整的核心闭环：

用户档案 -> 周训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 一键采纳并写回训练计划

项目目标不是一次做成完整商用产品，而是优先保证这条链路可运行、可演示、可验证。

## 当前可演示能力

- 录入用户基础档案、训练目标与三大项 1RM
- 维护一周训练计划
- 记录今日日志，包括体重、热量、蛋白质、睡眠、疲劳度、训练完成情况与备注
- 在今日日志页展示近 14 天体重趋势
- 导出与导入本地 JSON 备份
- 在 AI 教练发送消息前自动注入最新档案、计划与日志上下文
- 解析 AI 回复中的结构化建议
- 渲染建议采纳卡片，并在用户确认后写回训练计划

## 当前 MVP 边界

- 所有数据仅保存在浏览器 `localStorage`
- 当前没有后端、数据库、账号系统或多端同步
- AI 建议采纳目前只支持对已有动作的已有字段执行 `update`
- 当前不支持通过 AI 直接新增动作、删除动作或重排整周计划
- AI 教练要求档案中至少具备姓名、当前体重、训练目标和深蹲 1RM，才允许发起请求

## 环境要求

- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本

## 安装与运行

安装依赖：

```bash
npm install
```

启动开发环境：

```bash
npm run dev
```

默认访问地址通常为：

```text
http://localhost:5173/
```

本地预览生产构建：

```bash
npm run build
npm run preview
```

## API Key 配置

本项目的 AI 教练能力通过 DeepSeek 原生 OpenAI 格式接口实现。在项目根目录创建 `.env` 文件：

```bash
VITE_DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
```

说明：

- 未配置 API Key 时，除 AI 教练外的本地功能仍可使用
- 修改 `.env` 后需要重启开发服务器
- 不要提交真实 API Key

仓库中提供了 `.env.example` 作为参考。

## 测试命令

运行全量自动化测试：

```bash
npm test
```

按模块快速验证时，可使用以下命令：

```bash
node --test tests/deepseek.test.js
node --test tests/dailyLog.test.js
node --test tests/prompt.test.js
node --test tests/promptPreview.test.js
node --test tests/chatHistory.test.js tests/coachChat.test.js
node --test tests/coachGuard.test.js
node --test tests/aiResponse.test.js
node --test tests/adoptCard.test.js
node --test tests/adoptPlan.test.js
node --test tests/dataTransfer.test.js
node --test tests/weightChart.test.js
node --test tests/weeklyPlan.test.js tests/todayPlan.test.js
node --test tests/displayFormat.test.js
```

前端构建验证：

```bash
npm run build
```

最小验收记录见 [docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)。

## 数值显示说明

- `src/utils/calc.js` 统一提供重量、百分比、组数、次数、RPE 的展示格式化函数
- 重量默认保留到 1 位小数并自动去掉无意义尾零，例如 `97.25 -> 97.3kg`、`80 -> 80kg`
- 挂钩 `1RM * 百分比` 的训练重量会保留应有的小数结果，例如 `150 * 0.75 -> 112.5kg`
- 百分比统一显示为整数百分比，例如 `0.75 -> 75%`
- 组数与次数统一按整数展示，RPE 统一保留 1 位小数
- `今日训练摘要`、`训练计划卡片`、`建议采纳卡片`、`体重趋势图` 共用同一套显示规则，避免不同页面展示不一致

## Demo 操作路径

建议按下面这条路径演示：

1. 打开首页，确认可以正常进入四个主标签页。
2. 进入“我的档案”，填写基础信息、训练目标与三大项 1RM。
3. 进入“训练计划”，确认至少有一天包含具体动作。
4. 进入“今日日志”，填写当天体重、热量、蛋白质、睡眠、疲劳度、训练完成情况与备注。
5. 点击保存，确认摘要区显示最新内容与体重趋势。
6. 切换到“AI 教练”，展开上下文预览，确认其中包含档案、周计划、近 7/14 天日志摘要与当日 TDEE 信息。
7. 输入一个训练调整问题并发送，观察聊天消息、加载状态与错误提示。
8. 当 AI 回复包含 `---JSON---` 结构化建议时，确认页面出现建议采纳卡片。
9. 先点击“忽略”，确认卡片可被移除。
10. 再次触发一条带结构化建议的回复，点击“采纳并更新计划”。
11. 返回“训练计划”，确认对应日期、对应动作的字段已更新。
12. 最后可补充演示一个失败场景，例如 AI 返回不存在动作名的建议，此时页面应提示失败且原计划不被修改。

## 本地存储说明

当前项目使用以下 `localStorage` 键保存数据：

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

说明：

- 刷新页面后，已保存数据会从本地恢复
- 更换浏览器、清空浏览器数据或使用无痕模式时，这些数据可能丢失
- 这些数据不会自动上传，也不会自动同步到其他设备
- 当前版本支持手动导出 JSON 备份，并在需要时手动导入恢复

## 项目结构概览

```text
src/
  api/          DeepSeek 调用封装
  components/   复用 UI 组件
  tabs/         四个主功能页
  utils/        计划、日志、prompt、存储等业务工具
tests/          Node 原生测试
docs/           课程文档、计划与验证记录
task/           迭代任务拆分与执行清单
```

更完整的模块职责、数据流和 `localStorage` 结构说明见 [ARCHITECTURE.md](/g:/VSCODE-G/Fitness Agent MVP/ARCHITECTURE.md)。

## 2026-05-30 默认数据更新

- 应用启动默认值已经改为空白结构，首次打开页面不会再自动灌入演示档案、训练计划、日志或聊天记录。
- 测试和离线验证如需样例数据，请使用 `src/utils/defaultData.js` 中单独保留的 `demo*` fixture。
- 本次版本会在浏览器端执行一次性 `localStorage` 迁移，首次进入新版时自动重置以下键为新的空白结构：
  - `fitloop_profile`
  - `fitloop_weeklyPlan`
  - `fitloop_dailyLog`
  - `fitloop_chatHistory`
- 迁移完成后会写入 `fitloop_storageVersion = "v2-empty-defaults"`，后续再次打开应用不会重复覆盖用户已填写的数据。
