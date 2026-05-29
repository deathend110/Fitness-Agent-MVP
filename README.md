# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。它聚焦一条最小但完整的演示闭环：

用户档案 -> 周训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 一键采纳并写回训练计划

当前版本的目标不是做完整商用产品，而是保证这条核心链路可运行、可演示、可验证，方便助教和同学快速上手。

## 这次交付能演示什么

- 录入用户基础档案、训练目标和三大项 1RM
- 维护一周训练计划
- 录入今日日志，包括体重、热量、蛋白质、睡眠、疲劳度、训练完成情况和训练备注
- 在今日日志页展示近 14 天体重趋势图，辅助观察短期变化
- 导出和导入 JSON 备份，降低 localStorage 丢失风险
- 在 AI 教练发送消息前，自动注入最新的档案、计划和日志上下文
- 展示本次发送前的上下文预览
- 解析 AI 回复中的结构化训练建议
- AI 回复优先使用流式输出，流式失败时自动降级为普通回复
- 在页面中渲染“建议采纳卡片”
- 用户点击采纳后，将建议写回对应日期的训练计划

## 当前 MVP 边界

- 所有数据只保存在浏览器 `localStorage`
- 本地数据**不会自动云同步**
- 当前没有后端、数据库、账号系统或多端同步能力
- AI 建议采纳目前只支持对**已有动作的已有字段**做 `update`
- 当前不支持通过 AI 建议新增动作、删除动作或自动生成完整新计划

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

默认访问地址通常是：

```text
http://localhost:5173/
```

如需本地预览生产构建，可使用：

```bash
npm run build
npm run preview
```

## API Key 配置

本项目的 AI 教练能力通过 DeepSeek 原生 OpenAI 格式接口实现。

在项目根目录创建 `.env` 文件：

```bash
VITE_DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
```

说明：

- 未配置 API Key 时，除 AI 教练外的本地功能仍可使用
- 修改 `.env` 后需要重启开发服务器
- 不要提交真实 API Key

仓库中提供了 `.env.example` 作为参考。

## 测试命令

运行当前全部自动化测试：

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
node --test tests/aiResponse.test.js
node --test tests/adoptCard.test.js
node --test tests/adoptPlan.test.js
node --test tests/dataTransfer.test.js
node --test tests/weightChart.test.js
node --test tests/weeklyPlan.test.js tests/todayPlan.test.js
```

前端构建验证：

```bash
npm run build
```

已记录的最小验证结果可参考 [docs/verification.md](/g:/VSCODE-G/Fitness%20Agent%20MVP/docs/verification.md)。

## Demo 操作路径

下面这条路径更适合课堂演示，从“能录数据”一路走到“AI 建议写回计划”。

1. 打开首页，确认应用可正常进入四个主标签页。
2. 进入“我的档案”，填写或确认基础信息、训练目标和三大项 1RM。
3. 进入“训练计划”，确认本周计划中至少有一天包含具体动作。
4. 进入“今日日志”，填写当天体重、热量、蛋白质、睡眠、疲劳度、训练完成情况和训练备注。
5. 点击保存，确认右侧摘要区域已显示最新内容。
6. 切换到“AI 教练”，先展开“当前上下文预览”，确认其中包含档案、周计划、近 7/14 天日志摘要和当日 TDEE 估算。
7. 输入一个训练调整问题并发送，观察聊天消息和加载状态。
8. 当 AI 回复中包含 `---JSON---` 结构化建议时，确认页面下方出现建议采纳卡片。
9. 先点击“忽略”，确认卡片可以被移除。
10. 再触发一次带结构化建议的回复，点击“采纳并更新计划”。
11. 回到“训练计划”，确认对应日期、对应动作的字段已经更新。
12. 最后可补充演示一个失败场景：让 AI 返回不存在动作名的建议，确认页面提示失败且原计划不被修改。

## 本地存储说明

当前项目使用以下 `localStorage` 键保存数据：

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

说明：

- 刷新页面后，已保存数据会从本地恢复
- 更换浏览器、清空浏览器数据或使用无痕模式时，这些数据可能丢失
- 这些数据不会自动上传，也不会自动同步到别的设备
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
```

更完整的模块职责、数据流和 localStorage 结构说明见 [ARCHITECTURE.md](/g:/VSCODE-G/Fitness%20Agent%20MVP/ARCHITECTURE.md)。
