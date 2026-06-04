# 自定义力量周期计划第一版设计

## 背景

当前项目已经具备周期计划模式的基础运行时能力：

- 活动周期记录 `active_cycle_plan`
- 周快照记录 `cycle_week_snapshot`
- 当前激活来源 `plan_source_state`
- 下游统一消费 `effectiveWeeklyPlan`

现有实现已经支持预制力量模板，例如 `Candito 6 周`、`Madcow 5x5`、`Texas Method`。  
下一步需求不是继续扩展预制模板，而是引入“用户手动定义的纯力量周期计划”。

本设计只覆盖第一版自定义力量周期计划，目标是：

- 满足纯力量周期计划的手动定义需求
- 保持当前周期计划运行时骨架不变
- 控制实现复杂度，避免把逻辑耦进现有 preset 分支
- 为后续扩展保留明确边界

## 目标

第一版支持用户手动创建一份“纯力量周期计划”，并接入现有周期计划模式。

用户可定义：

- 周期基础信息
- 主项 TM 快照
- 周总数
- 每周 7 天计划结构
- 主项动作每周的 `sets / reps / %TM`
- 变式辅助与孤立辅助动作的静态配置

系统可完成：

- 校验与保存自定义力量计划定义
- 根据定义一次性生成全部周快照
- 将当前周投影为现有 `effectiveWeeklyPlan`
- 沿用当前“当前周 override / 手动推进周次 / 停止周期”的执行逻辑

## 非目标

第一版明确不做以下能力：

- 非 7 天微周期
- AMRAP
- 基于训练表现的自动修正
- 双重递增
- 辅助动作自动替换 / 过滤策略
- AI 模型创建或维护自定义周期计划
- 通用公式系统
- 图形化周期编排器

## 核心范围

### 1. 计划类型

第一版只支持：

- `custom_strength`

语义上它表示：

- 纯力量导向
- 主项按 `%TM` 递进
- 辅助动作静态配置

### 2. 周期单位

第一版固定：

- 一个周期单元 = 7 天

用户可定义：

- `totalWeeks`

即计划总周数由用户输入，例如 `4 / 6 / 8` 周。

### 3. 动作层级

第一版支持三类动作：

- `main`
- `variation`
- `accessory`

规则如下：

- `main`：允许按 `%TM` 递进
- `variation`：第一版只允许静态配置
- `accessory`：第一版只允许静态配置

### 4. TM 快照

第一版只给主项配置 TM：

- `squat`
- `bench`
- `deadlift`
- `ohp`

只有实际被主项动作引用的 lift 才要求 TM 必填。

### 5. 主项推进方式

第一版主项只支持：

- 用户按周手填 `sets / reps / %TM`

系统据此：

- 按主项 TM 计算绝对重量
- 以最小配重片规则取整
- 输出兼容现有系统的 `weeklyPlan` 快照结构

## 架构边界

### 周期生命周期层

复用现有：

- `backend/plans/cycle_service.py`
- `backend/api/cycle_plans.py`

职责：

- 创建活动周期
- 推进周次
- 停止周期
- 保存当前周 override
- 切换计划来源

约束：

- 不在这里写入“自定义力量计划每周如何生成”的规则

### 自定义力量定义层

新增模块：

- `backend/plans/custom_strength_definition.py`

职责：

- 定义 `custom_strength` 数据结构
- 做 normalize / validate
- 约束动作分类与字段合法性

约束：

- 不负责生成周快照
- 不负责数据库生命周期

### 自定义力量生成层

新增模块：

- `backend/plans/custom_strength_engine.py`

职责：

- 读取 definition
- 编译为多周 `weeklyPlan`
- 只输出标准快照，不直接操作数据库

约束：

- 不和 `cycle_engine.py` 的 preset 分支混写

### 统一消费层

继续复用现有：

- `backend/agent/active_plan.py`
- `src/tabs/PlanTab.jsx`
- `src/tabs/TodayTab.jsx`
- `src/tabs/CoachTab.jsx`

职责：

- 继续只消费 `effectiveWeeklyPlan`

约束：

- 下游不需要理解它是 preset 还是 custom strength

## 文件边界

### 建议新增

后端：

- `backend/plans/custom_strength_definition.py`
- `backend/plans/custom_strength_engine.py`
- `backend/tests/test_custom_strength_definition.py`
- `backend/tests/test_custom_strength_engine.py`

前端：

- `src/components/plan-settings/CustomStrengthPlanEditor.jsx`
- `src/components/plan-settings/CustomStrengthWeekEditor.jsx`
- `src/components/plan-settings/CustomStrengthMainLiftEditor.jsx`
- `src/utils/customStrengthPlanForm.js`
- `tests/customStrengthPlanForm.test.js`

### 只允许轻改

后端：

- `backend/plans/cycle_service.py`
- `backend/api/cycle_plans.py`
- `backend/schemas/__init__.py`

前端：

- `src/tabs/PlanTab.jsx`
- `src/components/plan-settings/PlanSettingsPanel.jsx`
- `src/api/backendClient.js`

### 不应继续塞复杂逻辑

- `backend/plans/cycle_engine.py`
- `backend/plans/preset_library.py`
- `src/tabs/PlanTab.jsx`

## 数据结构设计

### 活动周期主记录

继续复用 `active_cycle_plan`：

- `preset_key = "custom_strength"`
- `goal = "strength"`
- `base_lifts` 保存主项 TM 快照
- `config` 保存完整 definition

第一版不单独新建 `custom_strength_plan` 表。

### definition 结构

建议结构如下：

```json
{
  "planType": "custom_strength",
  "name": "四周力量周期",
  "startDate": "2026-06-08",
  "totalWeeks": 4,
  "mainLifts": {
    "squat": { "tm": 180 },
    "bench": { "tm": 125 },
    "deadlift": { "tm": 220 },
    "ohp": { "tm": 75 }
  },
  "weeks": [
    {
      "weekIndex": 1,
      "days": [
        {
          "dayIndex": 1,
          "label": "周一",
          "type": "lower_strength",
          "exercises": []
        }
      ]
    }
  ]
}
```

### 动作结构

主项动作：

```json
{
  "id": "tmp-week1-day1-squat",
  "name": "Back Squat",
  "category": "main",
  "progression": {
    "mode": "percent_tm",
    "liftKey": "squat",
    "percentTm": 0.75
  },
  "prescription": {
    "sets": 5,
    "reps": 5
  },
  "notes": ""
}
```

变式辅助：

```json
{
  "id": "tmp-week1-day1-pause-squat",
  "name": "Pause Squat",
  "category": "variation",
  "referenceLift": "squat",
  "progression": {
    "mode": "static"
  },
  "prescription": {
    "sets": 3,
    "reps": 6
  },
  "loadText": "中等重量",
  "notes": ""
}
```

孤立辅助：

```json
{
  "id": "tmp-week1-day1-leg-curl",
  "name": "Leg Curl",
  "category": "accessory",
  "progression": {
    "mode": "static"
  },
  "prescription": {
    "sets": 3,
    "reps": 12
  },
  "loadText": "RPE 8",
  "notes": ""
}
```

约束：

- 只有 `main` 允许 `percent_tm`
- `variation / accessory` 第一版只能 `static`

### 快照输出结构

生成完成后，仍然必须落成当前系统兼容的 `weeklyPlan` 结构，写入：

- `cycle_week_snapshot.generated_plan`

definition 与 generated plan 必须分离：

- definition 用于编辑与再生成
- generated plan 用于执行与下游消费

## 前端页面范围

第一版建议提供一个克制的自定义力量计划创建编辑器，不做复杂编排器。

### 区块一：基础信息

- 计划名称
- 开始日期
- 总周数
- 说明文本（可选）

### 区块二：主项 TM

- 深蹲 TM
- 卧推 TM
- 硬拉 TM
- OHP TM

### 区块三：周计划定义

按“周”为单位展开：

- 第 1 周
- 第 2 周
- …

每周固定 7 天：

- 每天先选训练类型
- 每天维护动作列表

动作新增时先选类别：

- 主项
- 变式辅助
- 孤立辅助

不同类别展示不同字段：

- 主项：动作名、主项引用、`%TM`、`sets`、`reps`
- 变式辅助：动作名、参考主项、`sets`、`reps`、`loadText`
- 孤立辅助：动作名、`sets`、`reps`、`loadText`

### 区块四：摘要与创建

- 计划摘要
- 缺失字段提示
- 创建周期计划按钮

## 验证策略

### 后端

`test_custom_strength_definition.py` 至少覆盖：

- 缺少 `planType`
- 引用了主项但缺少 TM
- `variation / accessory` 非法使用 `%TM`
- 周数与周定义不一致

`test_custom_strength_engine.py` 至少覆盖：

- 主项 `%TM` 正确换算为 `loadRef`
- 多周正确生成
- 辅助动作静态保留
- 输出结构兼容当前 `weeklyPlan`

### 前端

`tests/customStrengthPlanForm.test.js` 至少覆盖：

- 草稿默认值
- 表单到 payload 的映射
- 主项字段和辅助字段分流

页面源码约束测试至少覆盖：

- `PlanSettingsPanel` 能挂载自定义力量计划入口
- `PlanTab` 仍只做入口编排，不承接大段定义逻辑

## 后续扩展路径

后续可按以下顺序扩展，不推翻第一版：

1. 编辑效率增强
  - 复制上一周
  - 整周快捷填充
  - 常用主项周模板快捷插入

2. 非 7 天微周期
  - 扩展 definition 和 engine，不改下游消费口径

3. AMRAP 与简单反馈
  - 新增 AMRAP 标记与简单修正规则

4. 辅助动作规则化
  - 变式辅助支持更强约束
  - 动作过滤 / 替换策略

## 结论

第一版自定义力量周期计划应当：

- 复用现有周期运行时骨架
- 独立出自定义力量定义层与生成层
- 将复杂度锁在新模块中
- 保持下游统一消费 `effectiveWeeklyPlan`

这样可以在不显著破坏当前结构的前提下，获得足够的扩展性和可维护性。
