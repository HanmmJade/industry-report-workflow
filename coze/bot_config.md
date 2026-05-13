# Coze Bot 配置说明

> 本文档详细说明如何在 Coze 平台配置行业月报自动化 Bot，包括工作流设计、节点配置、Prompt设置等。

---

## 一、Bot 功能概述

### 1.1 核心功能

| 功能 | 说明 |
|------|------|
| **行业数据搜集** | 自动搜集光伏、锂电、新能源汽车等行业的国内/国际数据 |
| **动态信息追踪** | 追踪竞争对手的IPO、融资、技术突破等战略动态 |
| **数据交叉验证** | 对搜集的数据进行多源交叉验证 |
| **可信度评估** | 按照A/B/C/D标准评估数据可信度 |
| **报告自动生成** | 输出符合标准格式的行业月报 |

### 1.2 Bot 命名建议

```
推荐名称：
- 行业月报助手
- 行业数据分析师
- 投资研究助手

Bot简介：
专注于行业数据搜集与验证的AI助手，帮助投资研究人员快速获取高质量的行业数据。
```

---

## 二、工作流设计

### 2.1 工作流结构

```
┌─────────────────────────────────────────────────────────────┐
│                      工作流概览                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [用户输入] → [数据搜集] → [数据校验] → [可信度评估] → [报告生成]  │
│      ↓           ↓              ↓              ↓           ↓     │
│   行业/时间   国内数据       时间一致性    来源权威性    Markdown   │
│   选择       国际数据       预测值区分    交叉验证      Excel      │
│              竞争对手       数据冲突检测  综合定级      JSON       │
│              行业资讯                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 节点配置

#### 节点1：用户输入处理

```yaml
节点名称：用户输入处理
节点类型：开始节点

输入参数：
  - industry: string      # 行业（光伏/锂电/新能源汽车/激光）
  - time_period: string   # 时间范围（2026年3月/2026Q1）
  - data_type: string[]  # 数据类型（可多选）
                          # - domestic: 国内数据
                          # - global: 国际数据
                          # - competitor: 竞争对手动态
                          # - news: 行业资讯

输出参数：
  - industry
  - time_period
  - data_type
  - processing_plan
```

#### 节点2：数据搜集

```yaml
节点名称：数据搜集引擎
节点类型：LLM节点

模型选择：推荐使用 Claude 3.5 / GPT-4o
Temperature: 0.3  # 较低随机性，保证数据准确性

系统Prompt：
---
你是一个专业的行业数据分析师。请根据用户输入的参数，搜集相关行业数据。

数据搜集规则：
1. 优先使用官方来源（政府、行业协会、交易所）
2. 注明数据发布时间
3. 区分预测值和实际值
4. 提供可访问的URL

输入参数：{industry}, {time_period}, {data_type}

请调用相应的Prompt模板进行数据搜集：
- 国内数据 → prompts/01_domestic_data.md
- 国际数据 → prompts/02_global_data.md
- 竞争对手动态 → prompts/03_competitor_dynamics.md
- 行业资讯 → prompts/04_industry_news.md
---

输出参数：
  - raw_data: object  # 原始数据集合
  - data_count: number # 数据条目数
  - missing_sources: string[] # 未找到的数据源
```

#### 节点3：数据校验

```yaml
节点名称：数据校验引擎
节点类型：LLM节点 / 代码节点

校验规则：
  - 时间一致性检查
  - 预测值/实际值区分
  - 数据冲突检测
  - URL可访问性检查

代码示例（Python）：
```python
def validate_data(raw_data):
    validated_data = []
    issues = []
    
    for item in raw_data:
        # 时间一致性检查
        if not check_time_consistency(item):
            item['warning'] = '⚠️时间异常'
            issues.append(f"时间问题: {item['indicator']}")
        
        # 预测值检测
        if is_forecast(item) and not item.get('forecast_flag'):
            item['forecast_flag'] = True
            item['warning'] = '⚠️已标注为预测值'
        
        validated_data.append(item)
    
    return validated_data, issues
```

输出参数：
  - validated_data: object  # 校验后的数据
  - issues: string[]        # 发现的问题
  - issue_count: number      # 问题数量
```

#### 节点4：可信度评估

```yaml
节点名称：可信度评估引擎
节点类型：LLM节点

评估规则：参考 rules/credibility_rules.json

Prompt模板：
---
请对以下数据进行可信度评估，按照A/B/C/D四级标准评级。

评级标准：
- A级：官方来源 + 至少一个第三方交叉验证
- B级：权威机构单来源
- C级：行业媒体单来源
- D级：来源不明或数据冲突

请输出：
1. 每个数据项的评级
2. 评级理由
3. 如需调整评级，说明原因

数据：{validated_data}
---

输出参数：
  - graded_data: object   # 带可信度标注的数据
  - grade_distribution: object  # 各级别分布统计
  - upgrade_notes: string[]    # 升级说明
  - degrade_notes: string[]    # 降级说明
```

#### 节点5：报告生成

```yaml
节点名称：报告生成器
节点类型：LLM节点

输出格式：Markdown

Prompt模板：
---
请将以下经过校验和评估的数据整理成行业月报格式。

报告结构：
1. 数据汇总表（带可信度标注）
2. 可信度统计（各级别占比）
3. 重点关注项
4. 待验证项
5. 数据质量说明

数据：{graded_data}

格式要求：
- 使用Markdown表格
- 关键数据用**粗体**标注
- 问题数据用⚠️标注
- 提供可访问的URL
---

输出参数：
  - report: string        # Markdown格式报告
  - summary_stats: object # 汇总统计
```

---

## 三、完整工作流配置示例

### 3.1 工作流 YAML 配置

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

### 3.2 触发方式

| 方式 | 配置 | 说明 |
|------|------|------|
| **对话触发** | 用户输入行业和时间 | 最常用的方式 |
| **定时触发** | 每月固定时间 | 自动生成月报 |
| **API触发** | 外部系统调用 | 集成到其他系统 |

---

## 四、发布指引

### 4.1 Bot 发布设置

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

### 4.2 发布渠道

| 渠道 | 适用场景 | 配置 |
|------|----------|------|
| 扣子平台 | 内部使用/测试 | 默认配置 |
| 飞书 | 企业内部协作 | 配置飞书机器人 |
| 企业微信 | 企业内部协作 | 配置企业微信应用 |
| 钉钉 | 企业内部协作 | 配置钉钉机器人 |

### 4.3 权限设置

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

## 五、使用示例

### 5.1 用户对话示例

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

### 5.2 输出质量控制

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

## 六、常见问题

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
