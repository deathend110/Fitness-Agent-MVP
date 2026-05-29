# FitLoop MVP

FitLoop 是一个本地运行的 AI 健身教练 + 训练记录 MVP，用于课程中的 Agent-based 演示。

## 项目简介
- 前端：Vite + React + Tailwind CSS
- 数据：localStorage
- AI 接口：DeepSeek OpenAI 兼容格式

## 环境要求
- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本

## 安装命令
```bash
npm install
```

## 运行命令
```bash
npm run dev
```

默认地址通常是 `http://localhost:5173/`

## API Key 配置
在项目根目录创建 `.env`：
```bash
VITE_DEEPSEEK_API_KEY=你的DeepSeek_API_Key
```

不要提交真实 API Key。

## 测试命令
```bash
npm run build
```

## Demo 操作路径
1. 打开首页。
2. 切到「训练计划」。
3. 观察页面下方的「动作编辑演示」。
4. 百分比模式里可看到「深蹲 75% 4 组 6 次」的对象预览。
5. 固定重量模式里可看到「罗马尼亚硬拉 80kg 3 组 10 次」的对象预览。
6. 切到「我的档案」「今日日志」「AI 教练」继续查看联动数据。

## 本地数据
- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

