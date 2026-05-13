# Coze Bot 配置说明

> 本文档详细说明如何在 Coze 平台配置行业月报自动化 Bot，包括工作流设计、节点配置、Prompt设置等。

---

## 一、工作流模式搭建指南（推荐）

> **重要更新**：强烈推荐使用工作流模式（Workflow）而非单Agent模式。
> 工作流模式具有更强的可维护性、可扩展性和执行确定性。

### 1.1 为什么选择工作流模式？

| 维度 | 单Agent模式 | 工作流模式 |
|------|------------|-----------|
| **架构** | 一个Bot + 多段Prompt | 10节点串联 |
| **数据流** | 全靠Prompt传递 | 显式节点间传递 |
| **代码执行** | 无 | 代码节点可执行Python |
| **规则执行** | 依赖LLM理解 | 规则引擎执行 |
| **调试** | 难以定位问题 | 节点级调试 |
| **扩展性** | 需改Prompt | 增删节点即可 |

### 1.2 工作流节点速览

```
节点1（开始）：用户输入行业/时间
     ↓ 并行
节点2-5（LLM）：国内/国际/竞对/资讯搜集
     ↓ 串行
节点6（代码）：数据合并与标准化
节点7（代码）：校验引擎
节点8（代码）：可信度分级
节点9（LLM）：报告生成
     ↓
节点10（结束）：输出报告
```

### 1.3 快速搭建步骤

1. **创建工作流**：在Coze工作流编辑器中创建新工作流
2. **配置节点**：按 `coze/workflow_config.json` 添加10个节点
3. **导入代码**：将 `coze/workflow_nodes/` 中的代码粘贴到对应代码节点
4. **连接节点**：按配置连接各节点
5. **测试运行**：使用示例数据测试

详细设计文档：[workflow_design.md](workflow_design.md)

---

## 二、单Agent模式配置（备选）

> 如果无法使用工作流模式，可采用单Agent模式。

### 2.1 Bot 功能概述

| 功能 | 说明 |
|------|------|
| **行业数据搜集** | 自动搜集光伏、锂电、新能源汽车等行业的国内/国际数据 |
| **动态信息追踪** | 追踪竞争对手的IPO、融资、技术突破等战略动态 |
| **数据交叉验证** | 对搜集的数据进行多源交叉验证 |
| **可信度评估** | 按照A/B/C/D标准评估数据可信度 |
| **报告自动生成** | 输出符合标准格式的行业月报 |

### 2.2 Bot 命名建议

```
推荐名称：
- 行业月报助手
- 行业数据分析师
- 投资研究助手

Bot简介：
专注于行业数据搜集与验证的AI助手，帮助投资研究人员快速获取高质量的行业数据。
```

---

## 三、工作流节点配置（工作流模式）

### 3.1 节点1：用户输入处理

```yaml
节点名称：用户输入处理
节点类型：开始节点

输入参数：
  - industry: string      # 行业（光伏/锂电/新能源汽车/激光）
  - time_period: string   # 时间范围（2026年3月/2026Q1）
  - data_type: string[]  # 数据类型
                          # - domestic: 国内数据
                          # - global: 国际数据
                          # - competitor: 竞争对手动态
                          # - news: 行业资讯

输出参数：
  - industry
  - time_period
  - data_type
```

### 3.2 节点2-5：数据搜集（LLM节点，并行）

```yaml
节点名称：国内/国际/竞对/资讯数据搜集
节点类型：LLM节点
模型选择：Claude 3.5 / GPT-4o
Temperature: 0.3

输入参数：
  - industry: 来自节点1
  - time_period: 来自节点1

代码文件：coze/workflow_nodes/merge_data.py
```

### 3.3 节点6：数据合并（代码节点）

```yaml
节点名称：数据合并与标准化
节点类型：代码节点
代码文件：coze/workflow_nodes/merge_data.py

输入参数：
  - domestic_data: 来自节点2
  - global_data: 来自节点3
  - competitor_events: 来自节点4
  - industry_news: 来自节点5

输出参数：
  - all_data: 合并后数据数组
  - summary: 统计摘要
```

### 3.4 节点7：校验引擎（代码节点）

```yaml
节点名称：数据校验引擎
节点类型：代码节点
代码文件：coze/workflow_nodes/validate.py

输入参数：
  - all_data: 来自节点6
  - time_period: 来自节点1

校验规则：
  - 时间一致性检查
  - 预测值标注检测
  - 数据冲突检测

输出参数：
  - validation_results: 校验结果数组
  - validation_stats: 统计信息
```

### 3.5 节点8：可信度分级（代码节点）

```yaml
节点名称：可信度分级引擎
节点类型：代码节点
代码文件：coze/workflow_nodes/grade.py

输入参数：
  - all_data: 来自节点6
  - validation_results: 来自节点7

输出参数：
  - grading_results: 评级结果数组
  - grading_stats: 统计分布
```

### 3.6 节点9：报告生成（LLM节点）

```yaml
节点名称：报告生成
节点类型：LLM节点
代码文件：coze/workflow_nodes/format_output.py

输入参数：
  - all_data: 来自节点6
  - validation_results: 来自节点7
  - grading_results: 来自节点8
  - grading_stats: 来自节点8
  - time_period: 来自节点1

输出参数：
  - report_content: Markdown报告
```

### 3.7 节点10：结束

```yaml
节点名称：结束
节点类型：结束节点

输出：
  - final_report: 最终报告
  - stats: 统计信息
```

---

## 四、完整工作流配置示例

### 4.1 工作流 YAML 配置

```yaml
name: industry-report-workflow
description: 行业月报自动化数据搜集与校验工作流

nodes:
  - id: start
    type: start
    name: 开始
    output:
      - industry
      - time_period
      - data_type

  - id: data_collection
    type: llm
    name: 数据搜集
    input:
      - industry: start.industry
      - time_period: start.time_period
      - data_type: start.data_type
    prompt_file: prompts/data_collection.md
    model: claude-3-5-sonnet
    temperature: 0.3
    output:
      - raw_data
      - data_count

  - id: validation
    type: code
    name: 数据校验
    input:
      - raw_data: data_collection.raw_data
    script: scripts/validate.py
    output:
      - validated_data
      - issues

  - id: credibility
    type: llm
    name: 可信度评估
    input:
      - validated_data: validation.validated_data
    prompt_file: prompts/credibility_assessment.md
    model: claude-3-5-sonnet
    temperature: 0.1
    output:
      - graded_data
      - grade_distribution

  - id: report
    type: llm
    name: 报告生成
    input:
      - graded_data: credibility.graded_data
      - grade_distribution: credibility.grade_distribution
    prompt_file: prompts/report_generation.md
    model: claude-3-5-sonnet
    temperature: 0.2
    output:
      - report

  - id: end
    type: end
    name: 结束
    input:
      - report: report.report
```

### 4.2 触发方式

| 方式 | 配置 | 说明 |
|------|------|------|
| **对话触发** | 用户输入行业和时间 | 最常用的方式 |
| **定时触发** | 每月固定时间 | 自动生成月报 |
| **API触发** | 外部系统调用 | 集成到其他系统 |

---

## 五、发布指引

### 5.1 Bot 发布设置

```yaml
基础信息：
  - Bot名称：行业月报助手
  - Bot简介：行业数据搜集与验证AI助手
  - 图标：建议使用数据分析/报告相关图标

功能设置：
  - 语音播报：关闭
  - 识别语音输入：关闭
  - 连续对话：开启
  - 推荐问题：预设常见问题

高级设置：
  - 上下文窗口：选择较大窗口（支持长报告）
  - 记忆功能：开启（记录用户偏好）
```

### 5.2 发布渠道

| 渠道 | 适用场景 | 配置 |
|------|----------|------|
| 扣子平台 | 内部使用/测试 | 默认配置 |
| 飞书 | 企业内部协作 | 配置飞书机器人 |
| 企业微信 | 企业内部协作 | 配置企业微信应用 |
| 钉钉 | 企业内部协作 | 配置钉钉机器人 |

### 5.3 权限设置

```yaml
访问权限：
  - 团队内可见
  - 开启分享链接（可选）
  
数据权限：
  - 允许访问外部网络（必需）
  - 允许文件上传（用于模板）
  - 允许文件下载（用于报告导出）
```

---

## 六、使用示例

### 6.1 用户对话示例

```
用户：
请帮我搜集2026年3月光伏行业的数据，包括装机量、产量和组件排产数据。

Bot：
# 2026年3月光伏行业数据

## 国内数据汇总

| 指标 | 数据 | 单位 | 来源 | 可信度 |
|------|------|------|------|--------|
| 光伏电池装机量 | 891万kW（8.91GW） | 万千瓦 | 国家能源局 | 🟢A级 |
| 光伏电池产量 | 7162.1万kW | 万千瓦 | 国家统计局 | 🟢A级 |
| 光伏组件排产量 | ~47GW | GW | InfoLink | 🔵B级 |

## 可信度统计
- 🟢A级：2项（67%）
- 🔵B级：1项（33%）

## 注意事项
⚠️ 光伏组件排产数据为InfoLink单来源，建议关注后续交叉验证

## 数据来源
- 国家能源局：https://www.nea.gov.cn/...
- 国家统计局：https://www.stats.gov.cn/...
- InfoLink：https://infolink.com/...
```

### 6.2 输出质量控制

```yaml
输出质量检查清单：
□ 是否所有数据都标注了来源？
□ 是否区分了预测值和实际值？
□ 是否提供了可访问的URL？
□ 可信度评级是否符合标准？
□ 是否标注了待验证项？

输出前检查：
1. 数量检查：数据条目是否完整
2. 格式检查：表格格式是否正确
3. 链接检查：URL是否可访问
4. 标注检查：⚠️标注是否到位
```

---

## 七、常见问题

### Q1: 如何处理数据源缺失？

```markdown
A：当找不到权威数据时，应：
1. 显式标注"⚠️暂未找到权威数据"
2. 尝试提供替代参考来源
3. 说明缺失原因
4. 不编造或估算数据
```

### Q2: 如何处理多源数据冲突？

```markdown
A：当发现数据冲突时，应：
1. 保留所有来源及数值
2. 分析差异原因（预测值？口径不同？）
3. 明确建议采用的数据
4. 标注为"⚠️数据冲突，待核实"
```

### Q3: 如何提高A级数据占比？

```markdown
A：提高A级数据占比的方法：
1. 优先使用官方数据源
2. 主动寻找交叉验证来源
3. 区分预测值和实际值
4. 及时更新失效链接
5. 对低可信度数据持续跟踪验证
```

### Q4: 工作流模式和单Agent模式如何选择？

```markdown
A：推荐使用工作流模式的场景：
1. 需要代码节点执行规则引擎
2. 多个数据源需要并行搜集
3. 需要明确的阶段间数据传递
4. 需要节点级调试能力

可使用单Agent模式的场景：
1. 快速原型验证
2. 简单场景不需要复杂流程
3. 团队对Prompt工程更熟悉
```

---

## 八、相关文档

| 文档 | 说明 |
|------|------|
| [workflow_design.md](workflow_design.md) | 工作流设计详细文档 |
| [workflow_config.json](workflow_config.json) | 工作流配置文件 |
| [system-prompt.md](system-prompt.md) | System Prompt模板 |
| [../prompts/01_domestic_data.md](../prompts/01_domestic_data.md) | 国内数据搜集Prompt |
| [../rules/credibility_rules.json](../rules/credibility_rules.json) | 可信度评估规则 |
| [../rules/data_sources.json](../rules/data_sources.json) | 数据源配置 |
