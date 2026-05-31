# AI 教练页面 UI 重构设计文档

> 版本：v2.1 · 日期：2026-05-31  
> 范围：`src/tabs/CoachTab.jsx` 及其所有子组件的完整重写

---

## 一、问题诊断

### 当前页面的核心缺陷

| 问题 | 根本原因 | 影响 |
|---|---|---|
| 页面可无限向下滚动，滑到空白 | 缺少高度约束，消息容器没有 `flex: 1 + overflow: hidden` 组合 | 用户迷失方向，无法正常阅读内容 |
| 底部输入框不固定 | 输入区没有 `flex-shrink: 0`，被消息增多后挤出视口 | 用户无法输入，功能失效 |
| 滚动条混乱，分不清哪层在滚 | 多层元素都有默认滚动行为，未明确禁用外层 | 操作体验割裂 |
| 整体布局僵硬 | 缺少高度令人愉悦的空间节奏、过渡动画和组件层次感 | 产品气质低 |

---

## 二、布局架构（核心修复）

### 2.1 正确的 CSS 层次

聊天页面的布局规则只有一条：**高度从顶到底严格分配，只有消息列表区允许内部滚动。**

```
html, body { height: 100%; overflow: hidden; }   ← 彻底禁止 body 滚动

.app {                                             ← 最外层
  display: flex;
  height: 100vh;
  overflow: hidden;                               ← 禁止外层产生滚动
}

.chat-main {                                       ← 主聊天区
  display: flex;
  flex-direction: column;
  height: 100%;                                   ← 撑满父容器
  overflow: hidden;                               ← 禁止自身滚动
}

  .chat-topbar { flex-shrink: 0; }               ← 顶部栏，不可压缩

  .messages-scroll {                              ← 唯一滚动区域
    flex: 1;                                      ← 占据剩余全部空间
    overflow-y: auto;                             ← 只在这里允许滚动
    overflow-x: hidden;
  }

  .input-area { flex-shrink: 0; }                ← 输入区，不可压缩，始终在底部
```

### 2.2 三栏整体结构

```
┌──────────────────────────────────────────────────────────┐
│  nav-sidebar (220px)  │  chat-sidebar (230px)  │  chat-main (flex: 1)  │
│                       │                         │                       │
│  RepMind 主导航        │  对话历史列表            │  ┌─── topbar ────────┐  │
│  · 我的档案           │  (独立内部滚动)          │  │ 对话标题 + 操作    │  │
│  · 训练计划           │                         │  └───────────────────┘  │
│  · 今日日志           │                         │                       │
│  · AI 教练 ✓          │                         │  ┌─── messages-scroll ┐  │
│                       │                         │  │                    │  │
│                       │                         │  │  消息气泡列表      │  │
│                       │                         │  │  (唯一滚动区)      │  │
│                       │                         │  │                    │  │
│                       │                         │  └────────────────────┘  │
│                       │                         │                       │
│  底部状态栏           │                         │  ┌─── input-area ────┐  │
│                       │                         │  │ 固定底部输入框    │  │
└──────────────────────────────────────────────────────────┘
                              全部 height: 100vh, overflow: hidden
```

---

## 三、组件结构

### 3.1 文件组织

```
src/
  tabs/
    CoachTab.jsx                   ← 顶层协调，管理状态和事件
  components/
    coach/
      CoachLayout.jsx              ← 三栏布局外壳（新建）
      ChatSidebar.jsx              ← 对话历史侧栏（重写）
      ChatTopbar.jsx               ← 对话顶部栏（新建）
      MessageList.jsx              ← 消息列表和滚动容器（重写核心）
      MessageBubble.jsx            ← 单条消息气泡（重写）
      AdoptCard.jsx                ← 采纳建议卡片（保留，微调样式）
      Composer.jsx                 ← 底部输入框（重写）
      EmptyState.jsx               ← 空对话欢迎页（新建）
```

### 3.2 CoachTab.jsx — 状态协调

```jsx
function CoachTab({ chatHistory, dailyLog, onChatHistoryChange, ... }) {
  const [draft, setDraft] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [activeSessionId, setActiveSessionId] = useState(null)

  // 所有业务逻辑保持不变（requestCoachReply, handleSubmit 等）
  // CoachTab 只负责数据和事件，不承担任何布局职责

  return (
    <CoachLayout
      sidebar={<ChatSidebar chatHistory={chatHistory} ... />}
      topbar={<ChatTopbar ... />}
      messages={
        <MessageList
          chatHistory={chatHistory}
          streamingText={streamingText}
          isSending={isSending}
        />
      }
      composer={
        <Composer
          draft={draft}
          onDraftChange={setDraft}
          onSubmit={handleSubmit}
          isSending={isSending}
          errorMessage={errorMessage}
        />
      }
    />
  )
}
```

### 3.3 CoachLayout.jsx — 布局外壳

```jsx
function CoachLayout({ sidebar, topbar, messages, composer }) {
  return (
    // 关键：这里不渲染到 section 里，直接是 flex 容器
    // 父级 AppShell 已保证高度约束
    <div className="flex h-full overflow-hidden">
      {/* 对话历史侧栏 */}
      <div className="w-[230px] shrink-0 flex flex-col h-full overflow-hidden border-r border-fitloop-line bg-[#f0f3fd]">
        {sidebar}
      </div>

      {/* 主聊天区 */}
      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0 bg-fitloop-panel">
        {/* 顶部栏：不可被压缩 */}
        <div className="shrink-0 h-14 border-b border-fitloop-line/70 flex items-center px-7">
          {topbar}
        </div>

        {/* 消息列表：唯一的滚动区域 */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          {messages}
        </div>

        {/* 输入区：不可被压缩，固定在底部 */}
        <div className="shrink-0 border-t border-fitloop-line/70 px-7 py-4">
          {composer}
        </div>
      </div>
    </div>
  )
}
```

**注意：** `CoachTab` 父级（`AppShell`）已经是 `h-screen overflow-hidden` 的正确容器，所以 `CoachLayout` 内只需 `h-full` 即可。如果 `AppShell` 的 `section` 包裹层有问题，需要同步检查确保高度约束链路完整。

---

## 四、关键组件实现

### 4.1 MessageList.jsx — 核心滚动容器

```jsx
import { useEffect, useRef } from 'react'

function MessageList({ chatHistory, streamingText, isSending, suggestionCards, onSuggestionClick }) {
  const scrollRef = useRef(null)
  const isEmpty = chatHistory.length === 0

  // 新消息或流式文字更新时，自动滚到底部
  useEffect(() => {
    if (!scrollRef.current || isEmpty) return
    const el = scrollRef.current
    // 只在用户接近底部时才自动滚动，避免打断主动向上翻阅
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
    if (isNearBottom || isSending) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight
      })
    }
  }, [chatHistory, streamingText, isSending, isEmpty])

  if (isEmpty) {
    return (
      // 空状态不用 overflow，直接 flex 居中
      <div className="h-full flex items-center justify-center px-7">
        <EmptyState onSuggestionClick={onSuggestionClick} />
      </div>
    )
  }

  return (
    // 这里是页面中唯一的 overflow-y: auto
    // 不设置 min-height，避免产生空白撑开区域
    <div
      ref={scrollRef}
      className="h-full overflow-y-auto overflow-x-hidden px-0 py-8"
      style={{ scrollbarGutter: 'stable' }}
    >
      {/* 内容宽度限制：只限制内容，不限制滚动容器 */}
      <div className="max-w-[720px] mx-auto px-7 flex flex-col gap-5">
        {chatHistory.map((msg, i) => (
          <MessageBubble key={`${msg.role}-${i}`} message={msg} />
        ))}

        {/* 流式回复气泡 */}
        {isSending && (
          <MessageBubble
            message={{ role: 'assistant', content: streamingText || '正在整理上下文...' }}
            isStreaming
          />
        )}

        {/* 滚动锚点，无需高度 */}
        <div aria-hidden="true" />
      </div>
    </div>
  )
}
```

**关键点：**
- `scrollRef` 附加在 `overflow-y: auto` 的元素上，而不是内部的 `div`
- `max-w-[720px] mx-auto` 只限制内容宽度，不影响滚动容器本身
- 滚动区域内部的最后一个 `div` 作为锚点，不设高度，避免空白

### 4.2 MessageBubble.jsx

```jsx
function MessageBubble({ message, isStreaming = false }) {
  const isUser = message.role === 'user'

  return (
    <article className={`flex gap-3 items-start ${isUser ? 'flex-row-reverse' : ''}`}>

      {/* 头像 */}
      <div className={`
        w-8 h-8 rounded-full shrink-0 flex items-center justify-center
        text-xs font-bold mt-0.5
        ${isUser
          ? 'bg-gradient-to-br from-indigo-100 to-blue-200 text-indigo-600'
          : 'bg-fitloop-orange/10 text-fitloop-orange border border-fitloop-orange/20'
        }
      `}>
        {isUser ? '我' : 'R'}
      </div>

      {/* 消息体 */}
      <div className={`flex-1 min-w-0 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* 发送者 + 时间 */}
        <p className="text-[11px] text-slate-400 mb-1.5">
          {isUser ? '我' : 'RepMind'}
          <span className="ml-2 text-fitloop-line">{formatTime()}</span>
        </p>

        {/* 气泡 */}
        <div className={`
          max-w-[600px] px-4 py-3 rounded-2xl text-sm leading-7 text-slate-800
          ${isUser
            ? 'bg-fitloop-orange/8 border border-fitloop-orange/20'
            : 'bg-fitloop-canvas border border-fitloop-line'
          }
          ${isStreaming ? 'after:content-["▋"] after:ml-0.5 after:animate-pulse after:text-fitloop-orange' : ''}
        `}>
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* 操作按钮（hover 时显示） */}
        {!isUser && !isStreaming && (
          <div className="flex gap-1 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <MsgActionButton icon="copy">复制</MsgActionButton>
            <MsgActionButton icon="refresh">重新生成</MsgActionButton>
          </div>
        )}

        {/* 采纳卡片（如果有 suggestion） */}
        {message.suggestion && (
          <AdoptCard card={buildAdoptCardModel(message.suggestion)} />
        )}
      </div>
    </article>
  )
}
```

### 4.3 Composer.jsx — 底部输入框

```jsx
function Composer({ draft, onDraftChange, onSubmit, isSending, errorMessage }) {
  const textareaRef = useRef(null)

  // 自动伸缩高度
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [draft])

  function handleKeyDown(e) {
    // Enter 发送，Shift+Enter 换行
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit(e)
    }
  }

  return (
    // 这个 div 由父级 CoachLayout 提供 shrink-0 约束，此处不重复设置
    <div className="max-w-[720px] mx-auto w-full">
      <div className={`
        rounded-[22px] border bg-fitloop-panel
        shadow-[0_4px_24px_rgba(30,40,80,0.09)]
        transition-shadow duration-200
        ${isSending
          ? 'border-fitloop-line'
          : 'border-fitloop-line hover:border-fitloop-orange/40 focus-within:border-fitloop-orange focus-within:shadow-[0_0_0_4px_rgba(109,94,252,0.10),0_4px_24px_rgba(30,40,80,0.09)]'
        }
      `}>
        <textarea
          ref={textareaRef}
          className="
            w-full min-h-[48px] max-h-[160px]
            resize-none bg-transparent border-0 outline-none
            text-sm leading-6 text-slate-800 placeholder:text-slate-400
            px-5 pt-4 pb-2 font-sans
          "
          placeholder="Ask RepMind..."
          value={draft}
          onChange={e => onDraftChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          rows={1}
        />

        <div className="flex items-center justify-between px-3 pb-3">
          {/* 左侧：模型标识 */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-fitloop-canvas border border-fitloop-line rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-fitloop-orange" />
            <span className="text-xs font-medium text-slate-500">deepseek-v4-flash</span>
          </div>

          {/* 右侧：操作按钮 */}
          <div className="flex items-center gap-1.5">
            {/* 发送按钮 */}
            <button
              onClick={onSubmit}
              disabled={!draft.trim() || isSending}
              className="
                w-9 h-9 rounded-full bg-fitloop-orange text-white
                flex items-center justify-center
                transition-all duration-150
                hover:brightness-110 hover:scale-105
                disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100
              "
              aria-label="发送消息"
            >
              {isSending ? <LoadingSpinner /> : <SendIcon />}
            </button>
          </div>
        </div>
      </div>

      {/* 错误提示 */}
      {errorMessage && (
        <p className="mt-2 px-4 py-2.5 rounded-xl bg-red-50 border border-red-200 text-sm text-red-600 leading-6" role="alert">
          {errorMessage}
        </p>
      )}

      {/* 底部说明 */}
      <p className="text-center text-[11px] text-slate-400 mt-2">
        AI 教练基于你的本地数据作答 · 不上传到服务器
      </p>
    </div>
  )
}
```

### 4.4 ChatSidebar.jsx — 对话历史

```jsx
function ChatSidebar({ chatHistory, onNewChat, onSelectSession, activeSessionId }) {
  const sessions = buildSessionList(chatHistory)  // 按日期分组

  return (
    // 父级已提供 h-full overflow-hidden，这里只管内部布局
    <div className="flex flex-col h-full">
      {/* 固定头部 */}
      <div className="shrink-0 px-4 pt-4 pb-3 border-b border-fitloop-line/60">
        <p className="text-[11px] font-bold tracking-widest text-slate-400 uppercase mb-3">AI 教练</p>
        <button
          onClick={onNewChat}
          className="
            w-full flex items-center justify-center gap-2
            py-2 rounded-xl bg-fitloop-orange text-white
            text-sm font-semibold transition-all hover:brightness-110
          "
        >
          <PlusIcon size={14} />
          新建对话
        </button>
      </div>

      {/* 历史列表：这里独立滚动 */}
      <div
        className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5"
        style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--rm-border) transparent' }}
      >
        {sessions.map(group => (
          <div key={group.label}>
            <p className="px-2 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
              {group.label}
            </p>
            {group.items.map(session => (
              <button
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                className={`
                  w-full text-left px-3 py-2 rounded-xl text-sm transition-all
                  truncate leading-5
                  ${session.id === activeSessionId
                    ? 'bg-white text-slate-700 font-medium border border-fitloop-line shadow-sm'
                    : 'text-slate-500 hover:bg-white/70 hover:text-slate-700'
                  }
                `}
              >
                {session.title}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
```

### 4.5 EmptyState.jsx — 空状态欢迎页

```jsx
function EmptyState({ onSuggestionClick }) {
  const suggestions = [
    { label: '恢复分析', text: '分析今天的训练恢复状况' },
    { label: '营养检查', text: '帮我检查本周蛋白质摄入' },
    { label: '强度优化', text: '优化今天深蹲的训练强度' },
    { label: '容量评估', text: '评估一下这周的总体训练容量' },
  ]

  return (
    // 注意：EmptyState 不设置 overflow，由父级 MessageList 保证高度
    <div className="flex flex-col items-center text-center max-w-lg mx-auto">
      <div className="
        w-14 h-14 rounded-2xl bg-fitloop-orange/10 border-2 border-fitloop-orange/20
        flex items-center justify-center
        text-fitloop-orange text-xl font-black mb-5
      ">
        R
      </div>

      <h1 className="text-2xl font-bold text-slate-800 mb-2">
        Hello, I'm <span className="text-fitloop-orange">RepMind</span>
      </h1>
      <p className="text-sm text-slate-500 leading-6 mb-8">
        基于你的档案、训练计划和今日数据，为你提供专业健身建议。
      </p>

      <div className="grid grid-cols-2 gap-2.5 w-full">
        {suggestions.map(s => (
          <button
            key={s.text}
            onClick={() => onSuggestionClick(s.text)}
            className="
              text-left p-3.5 rounded-xl
              bg-white border border-fitloop-line
              text-sm text-slate-700 leading-5
              transition-all hover:border-fitloop-orange/30
              hover:bg-fitloop-orange/5 hover:shadow-sm
            "
          >
            <span className="block text-[10px] font-bold text-fitloop-orange uppercase tracking-wide mb-1">
              {s.label}
            </span>
            {s.text}
          </button>
        ))}
      </div>
    </div>
  )
}
```

---

## 五、AppShell 集成检查

`CoachTab` 在 `AppShell` 里被渲染到 `section.fitloop-shell__content` 中，需要确认高度链路完整：

```jsx
// AppShell.jsx — 主内容区
<div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-4 sm:p-5 lg:p-6">
  <section className="fitloop-shell__content min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
    {children}
  </section>
</div>
```

**问题：** `section.fitloop-shell__content` 上有 `overflow-y: auto`，这会让 CoachTab 的内容可以向外推动。

**修复方案：** 在 CoachTab 中检测到 coach 页面时，给 `section` 添加 `overflow: hidden` 覆盖，或者让 `AppShell` 支持 `noPadding` prop：

```jsx
// 方案 A：AppShell 支持 coach 模式（推荐）
function AppShell({ activeTabId, children, ... }) {
  const isCoach = activeTabId === 'coach'

  return (
    <main className="flex h-screen overflow-hidden ...">
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden ...">
        <section className={`
          fitloop-shell__content min-h-0 flex-1
          ${isCoach
            ? 'overflow-hidden p-0'          // coach 页：无内边距，无滚动
            : 'overflow-y-auto p-4 sm:p-5'   // 其他页：正常滚动和内边距
          }
        `}>
          {children}
        </section>
      </div>
    </main>
  )
}

// 方案 B：CoachTab 自身撑满（简单但略有 hack 感）
// 给 CoachTab 的根元素加上负 margin 来抵消父级 padding
// 不推荐，容易出现边缘对不齐的问题
```

**推荐采用方案 A。**

---

## 六、颜色与样式规范

### 6.1 颜色 token 使用（对应项目现有体系）

| 场景 | Tailwind 类 / CSS 变量 | 值 |
|---|---|---|
| 主强调色 | `text-fitloop-orange` / `bg-fitloop-orange` | `#6d5efc` |
| 强调色浅底 | `bg-fitloop-orange/10` | `rgba(109,94,252,0.10)` |
| 强调色描边 | `border-fitloop-orange/30` | `rgba(109,94,252,0.30)` |
| 面板底色 | `bg-fitloop-panel` | `#ffffff` |
| 页面底色 | `bg-fitloop-canvas` / `bg-fitloop-ink` | `#f8fafc` |
| 边框 | `border-fitloop-line` | `#d7def0` |
| 主文字 | `text-slate-800` | `#182033` |
| 次要文字 | `text-slate-500` | `#5f6b85` |
| 辅助文字 | `text-slate-400` | `#7f8aa3` |

### 6.2 气泡样式区分

```
用户消息：bg-fitloop-orange/8 + border-fitloop-orange/20
         浅蓝紫底，贴近主色但不刺眼

AI 消息：bg-fitloop-canvas + border-fitloop-line
         冷白底，与面板区分，安静阅读感

流式输出：在 AI 气泡末尾加 ::after 伪元素光标
         content: "▋", color: var(--rm-accent), animation: pulse
```

### 6.3 输入框聚焦状态

```css
/* 正常状态 */
border: 1.5px solid var(--rm-border);
box-shadow: 0 4px 24px rgba(30,40,80,0.09);

/* hover */
border-color: rgba(109,94,252,0.35);

/* focus-within */
border-color: var(--rm-accent);
box-shadow: 0 0 0 4px rgba(109,94,252,0.10), 0 4px 24px rgba(30,40,80,0.09);
```

---

## 七、滚动行为规范

### 7.1 自动滚动到底部的条件

不应该无条件地在每次消息更新时都强制滚到底部——如果用户正在向上翻看历史，强制滚动会造成体验打断。

```javascript
function shouldAutoScroll(scrollEl) {
  const { scrollHeight, scrollTop, clientHeight } = scrollEl
  // 距底部 120px 以内才触发自动滚动
  return scrollHeight - scrollTop - clientHeight < 120
}

useEffect(() => {
  if (!scrollRef.current) return
  if (isSending || shouldAutoScroll(scrollRef.current)) {
    requestAnimationFrame(() => {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    })
  }
}, [chatHistory, streamingText])
```

### 7.2 消息列表滚动条样式

```css
/* 对应 .messages-scroll */
scrollbar-gutter: stable;     /* 防止滚动条出现时页面内容抖动 */
scrollbar-width: thin;
scrollbar-color: #d7def0 transparent;

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(215,222,240,0.9);
  border-radius: 99px;
  border: 1px solid transparent;
  background-clip: padding-box;
}
```

### 7.3 侧栏历史列表的滚动

历史列表在 `chat-sidebar` 内部有自己的独立滚动区，与主消息区完全隔离，互不干扰：

```css
.chat-history-list {
  flex: 1;
  overflow-y: auto;
  /* 使用 thin 滚动条，与主区域视觉区分 */
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}
```

---

## 八、状态管理

### 8.1 状态定义

```javascript
// CoachTab 中管理的状态
const [draft, setDraft] = useState('')
const [isSending, setIsSending] = useState(false)
const [streamingText, setStreamingText] = useState('')
const [errorMessage, setErrorMessage] = useState('')

// 对话历史（来自 prop，父级 App 管理持久化）
// chatHistory: Array<{ role: 'user' | 'assistant', content: string }>
```

### 8.2 发送流程

```
用户点击发送
  ↓
validateInput()           // 非空检查，AI 前置条件检查（coachGuard）
  ↓ 通过
setIsSending(true)
setStreamingText('')
setDraft('')
onChatHistoryChange([...chatHistory, userMessage])
  ↓
requestCoachReplyStream() // 优先流式
  onText: (fullText) => setStreamingText(getVisibleStreamText(fullText))
  ↓ 失败
requestCoachReply()       // 降级普通请求
  ↓
onChatHistoryChange([...history, assistantMessage])
setIsSending(false)
setStreamingText('')
  ↓ 出错
setErrorMessage(error.message)
setIsSending(false)
```

### 8.3 流式文本显示

```javascript
// 从流式全文中剥离 JSON 段，只展示可读文本
function getVisibleStreamText(fullText) {
  const markerIndex = fullText.indexOf('---JSON---')
  if (markerIndex === -1) return fullText
  return fullText.slice(0, markerIndex).trimEnd()
}
```

---

## 九、响应式适配

### 9.1 宽屏（≥1200px）

- 三列完整展示（主导航 + 对话历史 + 主聊天区）
- 消息内容最大宽度 720px 居中

### 9.2 中屏（768px - 1200px）

```jsx
// 隐藏 chat-sidebar（对话历史），保留主导航和聊天区
<div className="hidden lg:flex w-[230px] ...">
  <ChatSidebar />
</div>
```

### 9.3 窄屏（< 768px）

```jsx
// 主导航收缩为底部 Tab Bar（已有实现）
// chat-sidebar 完全隐藏
// 消息内容满宽（去掉 max-w 限制）
<div className="messages-inner px-4 max-w-none">
```

---

## 十、验证检查清单

实现完成后，依次验证以下场景：

### 布局与滚动
- [ ] 打开 AI 教练页，页面 `body` 不出现纵向滚动条
- [ ] 发送 20+ 条消息后，消息列表正常滚动，页面本身不滚动
- [ ] 消息增多时，底部输入框始终固定在视口底部，不被推走
- [ ] 对话历史侧栏的滚动和消息区的滚动互不影响
- [ ] 浏览器缩小到 60% 高度，布局不崩溃

### 输入框
- [ ] 短文字时输入框高度 ~48px
- [ ] 输入多行长文字时，输入框自动增高，最高 160px 后出现内部滚动
- [ ] Enter 发送，Shift+Enter 换行
- [ ] 发送中（isSending）时输入框和按钮禁用

### 消息气泡
- [ ] 用户消息右对齐，AI 消息左对齐，间距一致
- [ ] AI 消息 hover 时出现操作按钮（复制、重新生成）
- [ ] 流式输出时光标闪烁，消息气泡末尾追加内容

### 采纳卡片
- [ ] AI 返回 `---JSON---` 建议时，在对应消息下方渲染采纳卡片
- [ ] 点击"采纳并更新计划"后，卡片消失，切换到训练计划页可见更新
- [ ] 点击"忽略"后卡片消失

### 空状态
- [ ] 新建对话后显示欢迎页和建议问题
- [ ] 点击建议问题填充到输入框

---

## 十一、与现有代码的差异对比

| 位置 | 现有实现 | 新实现 |
|---|---|---|
| `CoachTab.jsx` | 混合布局和业务逻辑 | 只负责状态，布局全部下移 |
| `CoachConversationPanel.jsx` | 整体 `section`，无高度约束 | 拆分为 `CoachLayout` + `MessageList` |
| 滚动容器 | 混乱，多层都有 overflow | 只有 `MessageList` 的根元素有 `overflow-y: auto` |
| 输入框定位 | 依赖文档流，消息多了会被推走 | `flex-shrink: 0`，父容器 `flex-direction: column + overflow: hidden` |
| AppShell 集成 | coach 页接受 `p-4` 内边距和 `overflow-y: auto` | coach 页特殊处理，移除内边距和外层滚动 |
| 空状态 | 在 `CoachConversationPanel` 内部条件渲染 | 独立 `EmptyState` 组件，由 `MessageList` 控制展示 |

---

*文档末尾 — 如有实现疑问，优先对照第二节（布局架构）检查高度链路是否完整。*
