# Skill 功能设计分析与实现方案

## Context

用户希望添加 skill 模块，目标有两个：
1. **稳定性约束**：通过 skill 进一步约束 AI 教练在调用计划修改卡时的行为
2. **个性化教练**：根据训练目标（增肌/减脂/力量/耐力）切换不同教练风格

当前架构中：教练角色硬编码在 `STABLE_SYSTEM_PROMPT`，工具选择仅靠 `PLAN_PROPOSAL_REQUEST_MARKERS` 关键词匹配，无任何动态化机制。

---

## 核心问题回答

### 可执行脚本能做吗？

**不推荐，也不必要。**

"Skill 附带可执行脚本"在 LangChain / AutoGPT 等框架里的含义是：skill 能调用预定义函数。
这层能力在当前后端**已经存在**——`ToolRegistry` 里的工具（`get_profile`、`propose_plan_change` 等）就是 skill 的"可执行脚本"层。

真正的"用户自定义脚本"（上传 Python/JS 在服务器执行）需要沙箱隔离（RestrictedPython 或 subprocess + 权限隔离），引入安全漏洞面，实现成本高，且与当前需求不匹配。

**结论：skill 的"可执行"部分 = 控制哪些工具可用 + 控制工具调用策略，当前架构完全可以做到。**

### Skill 是不是只是预设提示词？

不完全是。Skill 实际上是两层的叠加：

| 层 | 内容 | 当前难度 |
|---|---|---|
| **Prompt 层** | 教练风格、专项哲学、约束规则 | 低 |
| **Tool 层** | 哪些工具可用、tool_choice 策略 | 低-中 |

两层合起来，skill 比"预设提示词"更强——它同时约束语言行为和工具行为。

---

## 实现复杂度评估

### 方案 A：Prompt-Only Skill（纯提示层）

**复杂度：低（1-2天）**

做法：
- 新增 `SkillConfig` 数据结构，含 `name`、`display_name`、`system_prompt_addon` 字段
- 内置 3-4 个 skill（`general`、`strength`、`fat_loss`、`endurance`）
- 在 `PromptAssembler.assemble()` 中新增 `coach_skill` 段（priority=5，紧跟 stable_system_prompt 之后）
- Profile 或 ChatSession 存储当前激活的 skill id

修改文件：
- `backend/agent/prompt_templates.py` — 新增各 skill 的提示文本
- `backend/agent/context_manager.py` — assemble() 增加 skill_addon 段注入
- `backend/db/models.py` — Profile 增加 `coach_skill` 字段（或 ChatSession）
- API 层透传 skill 参数

**缺点**：无法约束工具调用行为，仅影响语言输出风格。

---

### 方案 B：Prompt + Tool Filter Skill（推荐）

**复杂度：中（3-5天）**

在方案 A 基础上，skill 额外携带工具约束配置：

```python
@dataclass
class SkillConfig:
    name: str                              # "strength_focus"
    display_name: str                      # "力量专项教练"
    prompt_addon: str                      # 注入 system prompt 的额外段落
    allowed_tools: set[str] | None = None  # None = 全部允许；指定 = 白名单
    force_tool_choice: str | None = None   # 覆盖默认 tool_choice 策略
    extra_proposal_markers: list[str] = field(default_factory=list)  # 扩展触发词
```

修改文件（在方案 A 基础上追加）：
- `backend/agent/tool_calling.py` — `ToolRegistry` 增加 `filter_by_skill()` 方法
- `backend/agent/tool_choice.py` — `resolve_tool_choice_for_request()` 接受 skill 配置覆盖
- `backend/agent/chat_session.py` — `run_tool_calling_chat()` 接收并应用 skill_config

关键扩展点（无需大改）：
- `PromptAssembler.assemble()` 已有按优先级插段的机制，新增一段不破坏现有顺序
- `ToolRegistry` 已有 `_tools` dict，filter 只需要包装一层
- `PLAN_PROPOSAL_REQUEST_MARKERS` 可以和 skill 的 `extra_proposal_markers` 合并

---

### 方案 C：可执行脚本 Skill

**复杂度：高（2-3周）+ 安全风险，不推荐**

需要 Python sandbox（RestrictedPython / Pyodide）、权限模型、脚本版本管理。
当前需求用方案 B 完全覆盖，无必要引入。

---

## 推荐实现路径（方案 B）

### 内置 Skill 示例

```python
BUILTIN_SKILLS = {
    "general": SkillConfig(
        name="general",
        display_name="通用健身教练",
        prompt_addon="",  # 不添加额外约束，使用基础 STABLE_SYSTEM_PROMPT
    ),
    "strength_focus": SkillConfig(
        name="strength_focus",
        display_name="力量专项教练",
        prompt_addon="""
教练专项：力量增长
- 优先保障大重量动作（深蹲/硬拉/卧推）的技术和渐进超负荷
- 建议修改计划时，自动附带负重和 RPE 的调整依据
- 恢复周期和疲劳管理优先于单次训练量
""",
        extra_proposal_markers=["力量计划", "渐进超负荷"],
    ),
    "fat_loss": SkillConfig(
        name="fat_loss",
        display_name="减脂教练",
        prompt_addon="""
教练专项：体脂管理
- 建议时结合 TDEE 热量缺口与训练强度平衡
- 有氧与抗阻训练比例建议需明确说明
- 不建议单纯依靠大幅削减饮食，需配合合理训练量
""",
    ),
}
```

### 数据流

```
用户请求
  → chat.py 从 Profile/Session 读取 skill_id
  → 加载 SkillConfig
  → PromptAssembler.assemble(skill_config=skill_config)
       → 插入 skill_addon 段（priority=5）
  → ToolRegistry.filter_by_skill(skill_config)
       → 过滤工具白名单（如有）
  → resolve_tool_choice_for_request(skill_config=skill_config)
       → 合并 extra_proposal_markers
  → ToolLoopOrchestrator.run(...)
```

### 与现有稳定性加固的关系

本次已完成的 Literal 约束 + 错误提示 是**兜底防线**（schema 层）。
Skill 是**上层引导层**（prompt + tool 策略层）。
两者互补，不冲突：
- Skill prompt_addon 告诉模型"在力量专项里如何用工具"
- Literal 约束确保即使模型理解偏差，也会被 Pydantic 拦截并给出纠偏提示

---

## 关键文件清单

| 文件 | 改动 |
|---|---|
| `backend/agent/prompt_templates.py` | 新增各 skill 的 prompt_addon 文本 + `SkillConfig` dataclass |
| `backend/agent/context_manager.py` | `assemble()` 增加 `coach_skill` 可选参数和段注入 |
| `backend/agent/tool_calling.py` | `ToolRegistry.filter_by_skill()` 方法 |
| `backend/agent/tool_choice.py` | `resolve_tool_choice_for_request()` 接受 skill 触发词扩展 |
| `backend/agent/chat_session.py` | `run_tool_calling_chat()` 透传 skill_config |
| `backend/db/models.py` | `Profile` 新增 `coach_skill` (String, nullable) |
| `backend/api/chat.py` | 从 profile 读取并传递 skill_config |

---

## 验证方式

1. 单元测试：`test_context_manager.py` 新增带 skill_config 的 assemble() 断言
2. 单元测试：`test_tool_calling.py` 新增 `filter_by_skill()` 白名单测试
3. 集成测试：`test_chat_tool_loop.py` 验证不同 skill 下 tool_choice 策略差异
4. 手动验收：切换 skill 后系统提示段在 debug 输出中可见

---

## 实现工作量估算

| 步骤 | 估算 |
|---|---|
| SkillConfig 定义 + 内置 skill 文本编写 | 2-3 小时 |
| PromptAssembler 注入 + context_manager 改动 | 2-3 小时 |
| ToolRegistry filter + tool_choice 扩展 | 2-3 小时 |
| DB 迁移 + API 透传 | 1-2 小时 |
| 测试补全 | 2-3 小时 |
| **合计** | **~9-14 小时** |
