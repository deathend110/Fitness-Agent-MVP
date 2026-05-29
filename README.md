# FitLoop MVP

FitLoop 是一个本地运行的 AI 健身教练 + 训练记录软件，用于课程设计中的 Agent-based MVP 展示。当前目标是跑通“用户档案 -> 训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 一键采纳写回计划”的最小闭环。

当前已完成 Task 1.3：新增 `src/utils/calc.js`，统一抽出日期、动作重量、BMR、训练消耗和 TDEE 相关计算，`PlanTab` 与 `TodayTab` 已接入这套工具函数。

## 环境要求

- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本
- DeepSeek API Key（后续 AI 教练功能需要）

## 安装命令

```bash
npm install
```

## 运行命令

```bash
npm run dev
```

启动后访问终端输出的本地地址，通常为 `http://localhost:5173/`。

## 构建命令

```bash
npm run build
```

## API Key 配置

在项目根目录创建 `.env` 文件并写入：

```bash
VITE_DEEPSEEK_API_KEY=你的DeepSeek_API_Key
```

`.env` 不应提交真实 API Key。

## 当前本地数据

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

这些数据统一通过 `src/utils/storage.js` 读写；当 localStorage 为空时，会回退到 `src/utils/defaultData.js` 中的默认数据。

## 计算工具说明

`src/utils/calc.js` 当前提供：

- `getTodayKey()`：返回与 `weeklyPlan` 对齐的英文星期键
- `getTodayStr()`：返回 `YYYY-MM-DD`
- `getExerciseKg()`：兼容 `ref1RM + pct` 和固定 `kg`
- `calcBMR()`：按 Mifflin-St Jeor 公式计算基础代谢
- `calcTrainingKcal()`：按 `kg * sets * reps * 0.1` 计算训练消耗
- `calcTDEE()`：汇总今日训练和热量上下文，返回对象结构供页面或 prompt 按需解构

## 测试/验证命令

当前项目还没有单独的测试框架，先使用最小验证命令：

```bash
npm run build
node --input-type=module -e "import { getExerciseKg, calcTrainingKcal, calcTDEE } from './src/utils/calc.js'; console.log('75% squat =', getExerciseKg({ ref1RM: 'squat', pct: 0.75 }, { squat: 120 })); console.log('fixed kg =', getExerciseKg({ kg: 80 }, {})); console.log('rest kcal =', calcTrainingKcal([], { squat: 120 })); console.log(JSON.stringify(calcTDEE({ basic: { sex: 'male', age: 23, height: 178, weight: 82.1 }, oneRM: { squat: 120 } }, { Friday: { type: 'rest', exercises: [] } }, {}), null, 2));"
node --input-type=module -e "import { loadStorage } from './src/utils/storage.js'; global.window = { localStorage: { getItem: () => '{bad json}', setItem: () => {} } }; console.log(JSON.stringify(loadStorage('fitloop_profile', { ok: true })));"
```

## Demo 操作路径

1. 打开首页，查看 4 个主 Tab。
2. 在“我的档案”查看默认用户档案与 1RM。
3. 在“训练计划”查看动作重量是否按百分比或固定 kg 正确展示。
4. 在“今日日志”查看今天日期、今日计划和日志摘要是否正确匹配。
5. 在“AI 教练”查看后续对话与上下文注入的预留位置。

## 当前状态

- 已完成 Vite + React + Tailwind CSS 基础骨架
- 已完成 4 个主 Tab 页面切换
- 已接入 `src/utils/storage.js` 和 `src/utils/defaultData.js`
- 已新增 `src/utils/calc.js`
- 已将 `PlanTab` / `TodayTab` 的重复日期与重量计算逻辑接入统一计算工具
- 后续开发继续对齐 `docs/plan.md`、`docs/fitness_coach_mvp_spec.md` 和课程文档推进
