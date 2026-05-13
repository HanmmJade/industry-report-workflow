# Coze工作流编排方案

> 本文档描述如何在Coze平台上使用"工作流模式"（而非单Agent纯Prompt）搭建行业月报自动化系统。

---

## 一、工作流 vs 单Agent模式对比

| 维度 | 单Agent模式（当前） | 工作流模式（推荐） |
|------|-------------------|------------------|
| **架构** | 一个Bot + 多段Prompt | 多个节点串联 |
| **数据流** | 全靠Prompt传递 | 显式节点间传递 |
| **执行确定性** | 依赖LLM理解 | 规则引擎执行 |
| **错误处理** | Prompt兜底 | 分层校验 |
| **可维护性** | Prompt分散难管理 | 节点职责清晰 |
| **扩展性** | 需改Prompt | 增删节点即可 |
| **代码执行** | 无 | 代码节点可执行Python |

**结论**：对于"搜集→校验→分级→输出"这类结构化流程，工作流模式更合适。

---

## 二、工作流设计（10节点）

### 节点概览

```
┌─────────────┐
│  节点1:开始  │
│  用户输入    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  并行执行（2~5节点）                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│  │节点2    │ │节点3    │ │节点4    │ │节点5    │         │
│  │国内数据 │ │国际数据 │ │竞对动态 │ │行业资讯 │         │
│  │搜集     │ │搜集     │ │搜集     │ │搜集     │         │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘         │
└──────┼────────────┼────────────┼────────────┼────────────┘
       └────────────┴────────────┴────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  串行执行（6~9节点）                                      │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐                     │
│  │节点6│→ │节点7│→ │节点8│→ │节点9│                     │
│  │合并 │  │校验 │  │分级 │  │生成 │                     │
│  └─────┘  └─────┘  └─────┘  └─────┘                     │
└──────────────────────────────────────────────────────────┘
                     │
                     ▼
            ┌─────────────┐
            │  节点10:结束│
            │  输出报告  │
            └─────────────┘
```

---

### 节点1：开始节点

**功能**：接收用户输入

**输入参数**：
- `industry`: 行业名称（光伏/锂电/新能源汽车）
- `time_period`: 时间范围（如：2026年3月）
- `data_types`: 数据类型数组（domestic/global/competitor/news）

**输出参数**：
- `industry`: 行业名称
- `time_period`: 时间范围
- `data_types`: 数据类型数组

**错误处理**：
- 缺少参数时使用默认值（光伏、当前月份、全部类型）

---

### 节点2：LLM节点 - 国内数据搜集

**输入参数**：
- `industry`: 从节点1来
- `time_period`: 从节点1来

**处理逻辑**：
- 使用 `prompts/01_domestic_data.md` 中的Prompt
- 联网搜索搜集国内行业数据
- 输出结构化JSON

**输出参数**：
- `domestic_data`: JSON数组，每个元素包含：
  ```json
  {
    "indicator": "指标名称",
    "value": "数值",
    "unit": "单位",
    "time_period": "2026年3月",
    "source_name": "国家能源局",
    "source_url": "URL",
    "publish_date": "2026-04-23",
    "cross_validation": ["数字新能源DNE"],
    "notes": "备注"
  }
  ```

**Prompt模板**：
```
[使用prompts/01_domestic_data.md中的内容]
```

**错误处理**：
- 搜集失败时返回空数组，并在错误信息中记录

---

### 节点3：LLM节点 - 国际数据搜集

**输入参数**：
- `industry`: 从节点1来
- `time_period`: 从节点1来

**处理逻辑**：
- 使用 `prompts/02_global_data.md` 中的Prompt
- 联网搜索搜集国际行业数据
- 输出结构化JSON

**输出参数**：
- `global_data`: JSON数组

**错误处理**：
- 同节点2

---

### 节点4：LLM节点 - 竞争对手动态搜集

**输入参数**：
- `industry`: 从节点1来
- `time_period`: 从节点1来

**处理逻辑**：
- 使用 `prompts/03_competitor_dynamics.md` 中的Prompt
- 联网搜索搜集竞对动态
- 输出结构化JSON

**输出参数**：
- `competitor_events`: JSON数组

**错误处理**：
- 同节点2

---

### 节点5：LLM节点 - 行业资讯搜集

**输入参数**：
- `industry`: 从节点1来
- `time_period`: 从节点1来

**处理逻辑**：
- 使用 `prompts/04_industry_news.md` 中的Prompt
- 联网搜索搜集行业资讯
- 输出结构化JSON

**输出参数**：
- `industry_news`: JSON数组

**错误处理**：
- 同节点2

---

### 节点6：代码节点 - 数据合并与标准化

**输入参数**：
- `domestic_data`: 从节点2来
- `global_data`: 从节点3来
- `competitor_events`: 从节点4来
- `industry_news`: 从节点5来

**处理逻辑**：
- 合并4个数据源
- 统一数据格式
- 生成唯一ID
- 检查重复

**输出参数**：
- `all_data`: 合并后的数据数组
- `summary`: 统计摘要（各类型数量）
- `duplicates`: 重复数据列表

**错误处理**：
- 部分数据为空时继续处理，使用空数组
- 格式错误时记录并跳过

**代码文件**：`coze/workflow_nodes/merge_data.py`

---

### 节点7：代码节点 - 校验引擎

**输入参数**：
- `all_data`: 从节点6来
- `time_period`: 从节点1来

**处理逻辑**：
- 时间一致性检查（发布日期在数据周期之后）
- 预测值标注检测（未标注则强制标注）
- 数据冲突检测（同指标多源数据>10%差异）

**输出参数**：
- `validation_results`: 校验结果数组，每个元素包含：
  ```json
  {
    "data_id": "xxx",
    "is_valid": true/false,
    "issues": [
      {
        "type": "time_inconsistency",
        "severity": "error/warning",
        "message": "描述"
      }
    ]
  }
  ```
- `validation_stats`: 统计信息

**错误处理**：
- 校验过程出错时返回空结果，继续后续流程

**代码文件**：`coze/workflow_nodes/validate.py`

---

### 节点8：代码节点 - 可信度分级

**输入参数**：
- `all_data`: 从节点6来
- `validation_results`: 从节点7来

**处理逻辑**：
- 读取 `rules/credibility_rules.json` 中的规则
- 根据来源、交叉验证、校验结果执行评级
- 输出A/B/C/D等级及理由

**输出参数**：
- `grading_results`: 评级结果数组，每个元素包含：
  ```json
  {
    "data_id": "xxx",
    "grade": "A/B/C/D",
    "grade_reason": "评级理由",
    "upgrade_suggestions": ["建议1", "建议2"]
  }
  ```
- `grading_stats`: 统计分布

**错误处理**：
- 无法评级时默认C级

**代码文件**：`coze/workflow_nodes/grade.py`

---

### 节点9：LLM节点 - 报告生成

**输入参数**：
- `all_data`: 从节点6来
- `validation_results`: 从节点7来
- `grading_results`: 从节点8来
- `grading_stats`: 从节点8来
- `time_period`: 从节点1来

**处理逻辑**：
- 根据结构化数据生成Markdown报告
- 包含：数据表格、可信度分布、异常说明、复核建议

**输出参数**：
- `report_content`: Markdown格式报告
- `report_stats`: 报告统计信息

**Prompt模板**：
```
你是一个专业的行业月报编辑。根据以下结构化数据，生成一份标准的Markdown格式行业月报：

数据周期：{time_period}
可信度分布：
{grading_stats}

数据详情：
{grading_results}

校验异常：
{validation_results}

请生成完整的Markdown报告，包括：
1. 报告头部（标题、时间、统计摘要）
2. 数据表格（按类型分组）
3. 可信度分布图表
4. 校验异常说明
5. 复核建议

报告要求：
- 保持数据原样，不编造
- 明确标注预测值
- 冲突数据分开列出
- 使用表格提高可读性
```

**错误处理**：
- 生成失败时返回简化版本

---

### 节点10：结束节点

**输入参数**：
- `report_content`: 从节点9来
- `grading_stats`: 从节点8来
- `validation_summary`: 从节点7来

**输出**：
- 最终报告文本
- 统计摘要

---

## 三、节点间数据传递

### 变量映射

| 源节点 | 输出变量 | 目标节点 | 输入变量 |
|--------|---------|---------|---------|
| 节点1 | industry | 2,3,4,5,7,9 | industry, time_period |
| 节点1 | time_period | 2,3,4,5,7,9 | time_period |
| 节点1 | data_types | 2,3,4,5 | data_types |
| 节点2 | domestic_data | 6 | domestic_data |
| 节点3 | global_data | 6 | global_data |
| 节点4 | competitor_events | 6 | competitor_events |
| 节点5 | industry_news | 6 | industry_news |
| 节点6 | all_data | 7,8,9 | all_data |
| 节点6 | summary | 9 | summary |
| 节点7 | validation_results | 8,9 | validation_results |
| 节点7 | validation_stats | 9 | validation_stats |
| 节点8 | grading_results | 9 | grading_results |
| 节点8 | grading_stats | 9,10 | grading_stats |
| 节点9 | report_content | 10 | report_content |

---

## 四、并行与串行策略

### 并行执行（节点2~5）

- 4个LLM节点可以并行执行
- 各自独立搜集不同类型数据
- 不相互依赖

### 串行执行（节点6~9）

- 节点6必须等2~5全部完成
- 节点7必须等节点6完成
- 节点8必须等节点7完成
- 节点9必须等节点8完成

---

## 五、错误处理策略

### 分层错误处理

1. **节点级错误**：单个节点失败不影响其他节点
2. **阶段级错误**：校验失败仍可生成报告（带警告）
3. **全局错误**：严重错误时输出简化报告

### 降级策略

| 异常情况 | 处理方式 |
|---------|---------|
| 节点2~5某节点失败 | 使用空数组，其他节点继续 |
| 节点6合并失败 | 返回原始数据 |
| 节点7校验失败 | 标记所有数据为"未校验" |
| 节点8分级失败 | 默认C级 |
| 节点9生成失败 | 输出简化文本 |

---

## 六、Coze工作流配置

参见：`coze/workflow_config.json`
