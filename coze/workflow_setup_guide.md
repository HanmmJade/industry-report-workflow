# Coze 工作流详细搭建步骤指南

> 本文档提供手把手的Coze工作流搭建教程，帮助您从零开始搭建10节点行业月报自动化工作流。

---

## 一、前置准备

### 1.1 注册 Coze 账号

1. 访问 [coze.cn](https://coze.cn)（国内版）或 [coze.com](https://coze.com)（海外版）
2. 使用手机号或邮箱注册账号
3. 完成实名认证（如需使用高级功能）

### 1.2 了解工作流概念

**工作流（Workflow）** vs **单Bot模式**：

| 特性 | 单Bot模式 | 工作流模式 |
|------|----------|-----------|
| 架构 | 一个Bot + 多段Prompt | 多个节点串联/并行 |
| 数据流 | 依赖Prompt传递 | 显式节点间传递 |
| 代码执行 | 无 | 代码节点可执行Python |
| 调试难度 | 较高 | 各节点独立可测 |
| 适用场景 | 简单问答 | 复杂流程自动化 |

### 1.3 所需工具

- Coze 账号（免费版即可开始）
- 基础编程知识（Python/JSON）
- 浏览器（推荐Chrome）

---

## 二、创建工作流项目

### 2.1 进入工作流编辑器

1. 登录 Coze 平台
2. 点击左侧菜单 **"工作流"** 或 **"Workflow"**
3. 点击 **"创建工作流"** 按钮

### 2.2 填写基本信息

```
工作流名称：industry_report_monthly
描述：行业月报自动化生成工作流
```

### 2.3 工作流画布

创建后会进入工作流画布界面：

```
┌─────────────────────────────────────────────────────────────┐
│  [工具栏]                                                   │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                   │
│  │开始 │ │LLM  │ │代码 │ │结束 │ │...  │  ← 从左侧拖拽节点  │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌────────────┐                                            │
│   │            │                                            │
│   │  画布区域   │  ← 拖拽节点到此处，用线连接                 │
│   │            │                                            │
│   └────────────┘                                            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [属性面板]  ← 选中节点后显示配置项                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、节点详细搭建步骤

### 节点1：开始节点（接收用户输入）

**功能**：接收用户输入的行业和时间参数

#### 配置步骤：

1. 从左侧节点列表拖拽 **"开始"** 节点到画布
2. 点击节点，在右侧属性面板配置 **输入变量**：

```
变量名：industry
类型：String
描述：行业名称（如：光伏、锂电、新能源汽车）
默认值：光伏

变量名：time_period
类型：String  
描述：时间周期（如：2026年3月）
默认值：当前月份

变量名：data_types
类型：Array[String]
描述：数据类型（domestic/global/competitor/news）
默认值：["domestic", "global", "competitor", "news"]
```

#### 输出配置：

此节点无需输出配置，数据直接传递给下游节点。

---

### 节点2：LLM节点 - 国内数据搜集

**功能**：搜集国内行业数据

#### 配置步骤：

1. 拖拽 **"大模型"** 节点到画布，放在开始节点下方
2. 用线连接：开始 → 国内数据搜集

#### 输入配置（从开始节点接收）：

```
industry: {{industry}}
time_period: {{time_period}}
```

#### 模型选择：

```
模型：Coze默认 / GPT-4 / Kimi（根据您的套餐选择）
温度：0.7
```

#### Prompt 配置：

将以下内容粘贴到 **用户提示** 框：

```markdown
## 任务
请搜集 {{time_period}} 期间，中国 {{industry}} 行业的核心数据。

## 数据要求

请搜集以下类型的数据（越多越好）：

### 1. 产能与产量数据
- 新增装机/产能数据
- 产量数据（按产品类型分类）
- 产能利用率

### 2. 价格数据
- 产品价格走势
- 原材料价格

### 3. 进出口数据
- 出口量/出口额
- 进口量/进口额

## 数据格式要求

每个数据点必须包含：
- indicator: 指标名称
- value: 数值（含单位，如"891万kW"）
- unit: 单位
- time_period: 数据周期（如"{{time_period}}"）
- source_name: 来源机构名称
- source_url: 原文链接
- publish_date: 发布日期（YYYY-MM-DD格式）
- notes: 备注说明

## 重要提示

1. **必须注明预测值**：如果数据是预测值，在notes中说明"⚠️此为预测值"
2. **必须标注数据口径**：如"出货量/装车量/销量"
3. **优先官方来源**：国家能源局、国家统计局、行业协会 > 第三方咨询机构
4. **多源交叉验证**：尽量提供2个以上来源进行交叉验证

## 输出格式

请以JSON数组格式输出，示例：
```json
[
  {
    "indicator": "光伏电池装机量",
    "value": "891万kW（8.91GW）",
    "unit": "万千瓦",
    "time_period": "{{time_period}}",
    "source_name": "国家能源局",
    "source_url": "https://www.nea.gov.cn/xxx",
    "publish_date": "2026-04-23",
    "notes": "推算值：1-3月累计减去1-2月累计得出",
    "is_forecast": false
  }
]
```
```

#### 插件配置（启用联网搜索）：

1. 在节点配置中找到 **"插件"** 或 **"工具"** 选项
2. 启用 **"联网搜索"** 插件
3. 配置搜索次数限制（如：每次调用搜索3-5次）

#### 输出配置：

```
输出变量名：domestic_data
类型：JSON/String（根据模型输出格式选择）
```

---

### 节点3：LLM节点 - 国际数据搜集

**功能**：搜集国际行业数据

#### 配置步骤：

1. 拖拽 **"大模型"** 节点，与节点2并行放置
2. 用线连接：开始 → 国际数据搜集

#### Prompt 配置：

```markdown
## 任务
请搜集 {{time_period}} 期间，全球 {{industry}} 行业的核心数据。

## 数据要求

### 1. 全球市场规模
- 全球新增装机/产能
- 市场规模及增速

### 2. 区域市场数据
- 主要区域市场（欧洲、北美、亚太等）数据
- 各区域市场份额

### 3. 国际企业动态
- 国际龙头企业市场份额
- 重要国际并购/合作

## 数据格式要求

每个数据点必须包含：
- indicator: 指标名称
- value: 数值（含单位）
- unit: 单位
- time_period: 数据周期
- region: 地区（如"全球"、"欧洲"等）
- source_name: 来源机构名称（如BNEF、IEA、SNE Research）
- source_url: 原文链接
- publish_date: 发布日期

## 重要提示

1. **标注数据口径**：出货量/装车量/销量必须区分
2. **区分预测值**：BNEF、IEA等机构的预测数据必须标注
3. **使用国际权威来源**：BNEF、IEA PVPS、SNE Research、EVtank等

## 输出格式

请以JSON数组格式输出。
```

#### 输出配置：

```
输出变量名：global_data
类型：JSON/String
```

---

### 节点4：LLM节点 - 竞争对手动态

**功能**：搜集行业竞争对手动态

#### 配置步骤：

1. 拖拽 **"大模型"** 节点
2. 用线连接：开始 → 竞争对手动态

#### Prompt 配置：

```markdown
## 任务
请搜集 {{time_period}} 期间，{{industry}} 行业主要竞争对手的重要动态。

## 动态类型

请关注以下类型的动态：

1. **IPO/上市**：企业递表、上市、过会等
2. **融资/投资**：融资事件、投资项目、定增等
3. **技术突破**：新技术发布、专利获批、研发进展等
4. **产能扩张**：新建产能、扩产计划、工厂投产等
5. **战略合作**：合作协议、战略签约、并购等
6. **财务表现**：财报发布、业绩预告、营收数据等

## 重点关注企业（可适当扩展）

- 宁德时代、比亚迪、隆基绿能、通威股份、阳光电源
- 及其他行业头部企业

## 数据格式要求

每个动态必须包含：
- company_name: 公司名称
- stock_code: 股票代码（如有）
- event_type: 动态类型
- title: 动态标题
- description: 详细描述
- event_date: 事件日期
- source_name: 来源机构
- source_url: 原文链接
- publish_date: 发布日期

## 重要提示

1. **注明信息来源**：财联社、港交所公告、企业公告等
2. **核实信息真实性**：优先采信官方公告
3. **关注时间节点**：确保是 {{time_period}} 期间的动态

## 输出格式

请以JSON数组格式输出。
```

#### 输出配置：

```
输出变量名：competitor_events
类型：JSON/String
```

---

### 节点5：LLM节点 - 行业资讯

**功能**：搜集行业重要资讯

#### 配置步骤：

1. 拖拽 **"大模型"** 节点
2. 用线连接：开始 → 行业资讯

#### Prompt 配置：

```markdown
## 任务
请搜集 {{time_period}} 期间，{{industry}} 行业的重要资讯。

## 资讯类型

1. **政策动态**：政府政策、行业规划、补贴政策等
2. **行业趋势**：市场趋势、技术路线、发展展望等
3. **技术进展**：新技术突破、研发成果等
4. **市场动态**：重大项目、市场变化等

## 数据格式要求

每条资讯必须包含：
- title: 资讯标题
- category: 资讯分类
- summary: 摘要（100字以内）
- source_name: 来源媒体
- url: 原文链接
- publish_date: 发布日期

## 重要提示

1. **优先权威媒体**：新华社、人民日报、行业权威媒体
2. **关注时效性**：确保是 {{time_period}} 期间的最新资讯
3. **避免低质量来源**：谨慎使用自媒体、匿名来源

## 输出格式

请以JSON数组格式输出。
```

#### 输出配置：

```
输出变量名：industry_news
类型：JSON/String
```

---

### 节点6：代码节点 - 数据合并

**功能**：将4个LLM节点输出的数据进行标准化合并

#### 配置步骤：

1. 拖拽 **"代码"** 节点到画布（在节点2-5下方）
2. 用线并行连接：节点2、3、4、5 → 节点6

#### 代码实现：

将以下代码粘贴到代码节点的 **代码输入框**：

```python
# -*- coding: utf-8 -*-
"""
Coze代码节点 - 数据合并与标准化
"""

import json
import re
from typing import List, Dict, Any, Optional


def generate_id(data_type: str, index: int) -> str:
    """生成唯一ID"""
    prefix_map = {
        "domestic": "DOM",
        "global": "GLO",
        "competitor": "COMP",
        "news": "NEWS"
    }
    prefix = prefix_map.get(data_type, "UNK")
    return f"{prefix}_{index:04d}"


def normalize_data_point(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """标准化单个数据点"""
    normalized = {
        "data_type": data_type,
        "_id": data.get("_id") or generate_id(data_type, 0),
        "indicator": data.get("indicator") or data.get("title") or "",
        "value": data.get("value") or data.get("description") or "",
        "unit": data.get("unit") or "",
        "time_period": data.get("time_period") or data.get("event_date") or data.get("date") or "",
        "source": {
            "name": data.get("source_name") or data.get("source") or "未知",
            "url": data.get("source_url") or data.get("url") or "",
            "publish_date": data.get("publish_date") or ""
        },
        "cross_validation": data.get("cross_validation") or [],
        "notes": data.get("notes") or "",
        "is_forecast": _check_forecast(data),
        "raw_data": data
    }
    return normalized


def _check_forecast(data: Dict[str, Any]) -> bool:
    """检查是否为预测值"""
    notes = data.get("notes", "") or ""
    value = data.get("value", "") or ""
    forecast_keywords = ["预计", "预测", "forecast", "预期", "estimate"]
    for keyword in forecast_keywords:
        if keyword.lower() in notes.lower() or keyword.lower() in value.lower():
            return True
    return False


def merge_data(
    domestic_data=None,
    global_data=None,
    competitor_events=None,
    industry_news=None
) -> Dict[str, Any]:
    """合并和标准化数据"""
    domestic_data = domestic_data or []
    global_data = global_data or []
    competitor_events = competitor_events or []
    industry_news = industry_news or []
    
    # 解析JSON字符串（如果输入是字符串）
    if isinstance(domestic_data, str):
        try:
            domestic_data = json.loads(domestic_data)
        except:
            domestic_data = []
    
    all_data = []
    
    # 标准化国内数据
    for i, item in enumerate(domestic_data):
        if isinstance(item, dict):
            normalized = normalize_data_point(item, "domestic")
            normalized["_id"] = f"DOM_{i+1:04d}"
            all_data.append(normalized)
    
    # 标准化国际数据
    if isinstance(global_data, str):
        try:
            global_data = json.loads(global_data)
        except:
            global_data = []
    for i, item in enumerate(global_data):
        if isinstance(item, dict):
            normalized = normalize_data_point(item, "global")
            normalized["_id"] = f"GLO_{i+1:04d}"
            all_data.append(normalized)
    
    # 标准化竞对动态
    if isinstance(competitor_events, str):
        try:
            competitor_events = json.loads(competitor_events)
        except:
            competitor_events = []
    for i, item in enumerate(competitor_events):
        if isinstance(item, dict):
            normalized = normalize_data_point(item, "competitor")
            normalized["_id"] = f"COMP_{i+1:04d}"
            all_data.append(normalized)
    
    # 标准化行业资讯
    if isinstance(industry_news, str):
        try:
            industry_news = json.loads(industry_news)
        except:
            industry_news = []
    for i, item in enumerate(industry_news):
        if isinstance(item, dict):
            normalized = normalize_data_point(item, "news")
            normalized["_id"] = f"NEWS_{i+1:04d}"
            all_data.append(normalized)
    
    return {
        "all_data": all_data,
        "summary": {
            "total": len(all_data),
            "domestic": len(domestic_data) if isinstance(domestic_data, list) else 0,
            "global": len(global_data) if isinstance(global_data, list) else 0,
            "competitor": len(competitor_events) if isinstance(competitor_events, list) else 0,
            "news": len(industry_news) if isinstance(industry_news, list) else 0
        }
    }


# Coze代码节点入口函数
def main(params):
    """
    Coze代码节点入口
    params 包含从上游节点传入的所有变量
    """
    result = merge_data(
        domestic_data=params.get("domestic_data"),
        global_data=params.get("global_data"),
        competitor_events=params.get("competitor_events"),
        industry_news=params.get("industry_news")
    )
    return result
```

#### 输入配置：

```
domestic_data: {{节点2的输出}}
global_data: {{节点3的输出}}
competitor_events: {{节点4的输出}}
industry_news: {{节点5的输出}}
```

#### 输出配置：

```
输出变量名：merged_result
类型：JSON/String
```

---

### 节点7：代码节点 - 数据校验

**功能**：对合并后的数据进行校验，检测问题

#### 配置步骤：

1. 拖拽 **"代码"** 节点
2. 用线连接：节点6 → 节点7

#### 代码实现：

```python
# -*- coding: utf-8 -*-
"""
Coze代码节点 - 校验引擎
"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple


FORECAST_KEYWORDS = [
    "预计", "预期", "预测", "估计", "展望",
    "将达", "将至", "将为", "有望", "约",
    "forecast", "prediction", "expected", "outlook"
]


def parse_time_period(period_str: str) -> Optional[Tuple[datetime, datetime]]:
    """解析时间周期"""
    match = re.match(r'(\d{4})年(\d{1,2})月', period_str)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        period_start = datetime(year, month, 1)
        if month == 12:
            period_end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = datetime(year, month + 1, 1) - timedelta(days=1)
        return period_start, period_end
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """解析日期"""
    formats = ["%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d", "%Y.%m.%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return None


def check_time_consistency(data: Dict, target_period: str) -> Tuple[bool, Optional[str]]:
    """检查时间一致性"""
    period_info = parse_time_period(target_period)
    if not period_info:
        return True, None
    
    period_start, period_end = period_info
    source = data.get("source", {})
    publish_date_str = source.get("publish_date", "")
    
    if not publish_date_str or publish_date_str in ["-", "待查", "未知"]:
        return False, "⚠️发布时间待查，无法判断时间一致性"
    
    publish_date = parse_date(publish_date_str)
    if not publish_date:
        return True, None
    
    if publish_date <= period_end:
        if data.get("is_forecast"):
            return True, None
        return False, f"⚠️时间异常：{publish_date_str}发布的{target_period}数据，实际数据应于{period_end.strftime('%Y-%m-%d')}之后发布"
    
    return True, None


def check_forecast_label(data: Dict) -> Tuple[bool, Optional[str]]:
    """检查预测值标注"""
    if data.get("is_forecast"):
        return True, None
    
    value = data.get("value", "")
    notes = data.get("notes", "")
    
    for keyword in FORECAST_KEYWORDS:
        if keyword.lower() in value.lower() or keyword.lower() in notes.lower():
            return False, "⚠️未标注为预测值"
    
    if "~" in value:
        return False, "⚠️数值含预测特征符（~），建议明确标注"
    
    return True, None


def validate_all(all_data: List[Dict], time_period: str = "") -> Dict[str, Any]:
    """批量校验所有数据"""
    validation_results = []
    issue_summary = {"time_issue": 0, "forecast_issue": 0, "conflict": 0}
    
    for data in all_data:
        issues = []
        
        # 时间一致性检查
        is_valid, msg = check_time_consistency(data, time_period)
        if not is_valid:
            issues.append(msg)
            issue_summary["time_issue"] += 1
        
        # 预测值标注检查
        is_valid, msg = check_forecast_label(data)
        if not is_valid:
            issues.append(msg)
            issue_summary["forecast_issue"] += 1
        
        validation_results.append({
            "data_id": data.get("_id"),
            "is_valid": len(issues) == 0,
            "issues": issues
        })
    
    return {
        "validation_results": validation_results,
        "issue_summary": issue_summary,
        "valid_count": sum(1 for r in validation_results if r["is_valid"]),
        "invalid_count": sum(1 for r in validation_results if not r["is_valid"])
    }


def main(params):
    """Coze代码节点入口"""
    merged_result = params.get("merged_result", {})
    
    if isinstance(merged_result, str):
        try:
            merged_result = json.loads(merged_result)
        except:
            return {"validation_results": [], "issue_summary": {}}
    
    all_data = merged_result.get("all_data", [])
    time_period = params.get("time_period", "")
    
    result = validate_all(all_data, time_period)
    return result
```

#### 输入配置：

```
merged_result: {{节点6的输出}}
time_period: {{开始节点的time_period}}
```

#### 输出配置：

```
输出变量名：validation_output
类型：JSON/String
```

---

### 节点8：代码节点 - 可信度分级

**功能**：对数据进行可信度分级

#### 配置步骤：

1. 拖拽 **"代码"** 节点
2. 用线连接：节点7 → 节点8

#### 代码实现：

```python
# -*- coding: utf-8 -*-
"""
Coze代码节点 - 可信度分级引擎
"""

import json
from typing import List, Dict, Any


TYPICAL_A_SOURCES = [
    "国家能源局", "国家统计局", "中国汽车工业协会", "中国汽车动力电池产业创新联盟",
    "BNEF", "IEA", "IEA PVPS", "SNE Research", "CPIA", "证监会", "EVtank",
    "Benchmark Minerals", "Ember", "乘联会"
]

TYPICAL_B_SOURCES = [
    "InfoLink", "Mysteel", "大东时代智库", "ICC鑫椤资讯", "数字新能源DNE",
    "财联社", "界面新闻", "证券时报", "券商研究报告", "PV Magazine", "GGII"
]


def get_base_grade(source_name: str) -> str:
    """根据来源确定基础评级"""
    if not source_name:
        return "D"
    
    source_lower = source_name.lower()
    
    for typical in TYPICAL_A_SOURCES:
        if typical.lower() in source_lower:
            return "A"
    
    for typical in TYPICAL_B_SOURCES:
        if typical.lower() in source_lower:
            return "B"
    
    return "B"


def has_cross_validation(data: Dict) -> tuple:
    """检查交叉验证"""
    cross_sources = data.get("cross_validation", [])
    if not cross_sources:
        return False, 0, 0
    
    grade_a_count = sum(1 for s in cross_sources if get_base_grade(s) == "A")
    return len(cross_sources) > 0, len(cross_sources), grade_a_count


def grade_data_point(data: Dict, validation_result: Dict = None) -> Dict:
    """对单个数据点评级"""
    source = data.get("source", {})
    source_name = source.get("name", "来源不明")
    
    base_grade = get_base_grade(source_name)
    has_cv, cv_count, cv_grade_a_count = has_cross_validation(data)
    
    final_grade = base_grade
    grade_reason_parts = [f"来源：{source_name}"]
    
    if base_grade == "A":
        grade_reason_parts.append("来源为A级机构")
    elif base_grade == "B":
        grade_reason_parts.append("来源为B级机构")
    
    if has_cv:
        if cv_grade_a_count >= 2:
            final_grade = "A"
            grade_reason_parts.append(f"✓ 获{cv_grade_a_count}个A级来源验证，升级至A级")
        elif cv_count >= 1 and base_grade == "B":
            grade_reason_parts.append(f"✓ 获{cv_count}个来源验证")
    
    if validation_result and not validation_result.get("is_valid"):
        issues = validation_result.get("issues", [])
        if any("预测" in issue for issue in issues):
            final_grade = "C"
            grade_reason_parts.append("⚠️预测值未标注，降级至C级")
    
    return {
        "data_id": data.get("_id"),
        "final_grade": final_grade,
        "base_grade": base_grade,
        "grade_reason": "；".join(grade_reason_parts)
    }


def grade_all(all_data: List[Dict], validation_results: List[Dict]) -> Dict[str, Any]:
    """批量评级"""
    grading_results = []
    grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
    
    validation_map = {r["data_id"]: r for r in validation_results}
    
    for data in all_data:
        data_id = data.get("_id")
        validation_result = validation_map.get(data_id, {})
        
        result = grade_data_point(data, validation_result)
        grading_results.append(result)
        
        grade = result.get("final_grade", "D")
        if grade in grade_distribution:
            grade_distribution[grade] += 1
    
    total = len(all_data) if all_data else 1
    grade_percentages = {
        grade: round(count / total * 100, 1)
        for grade, count in grade_distribution.items()
    }
    
    return {
        "grading_results": grading_results,
        "grade_distribution": grade_distribution,
        "grade_percentages": grade_percentages
    }


def main(params):
    """Coze代码节点入口"""
    merged_result = params.get("merged_result", {})
    validation_output = params.get("validation_output", {})
    
    if isinstance(merged_result, str):
        try:
            merged_result = json.loads(merged_result)
        except:
            merged_result = {}
    
    if isinstance(validation_output, str):
        try:
            validation_output = json.loads(validation_output)
        except:
            validation_output = {}
    
    all_data = merged_result.get("all_data", [])
    validation_results = validation_output.get("validation_results", [])
    
    result = grade_all(all_data, validation_results)
    return result
```

#### 输入配置：

```
merged_result: {{节点6的输出}}
validation_output: {{节点7的输出}}
```

#### 输出配置：

```
输出变量名：grading_output
类型：JSON/String
```

---

### 节点9：LLM节点 - 报告生成

**功能**：基于分级结果生成最终报告

#### 配置步骤：

1. 拖拽 **"大模型"** 节点
2. 用线连接：节点8 → 节点9

#### Prompt 配置：

```markdown
## 任务

基于以下数据质量分析结果，生成行业月报。

## 输入数据

### 汇总信息
{{grading_output.summary}}

### 可信度分布
- A级数据：{{grading_output.grade_distribution.A}}条 ({{grading_output.grade_percentages.A}}%)
- B级数据：{{grading_output.grade_distribution.B}}条 ({{grading_output.grade_percentages.B}}%)
- C级数据：{{grading_output.grade_distribution.C}}条 ({{grading_output.grade_percentages.C}}%)
- D级数据：{{grading_output.grade_distribution.D}}条 ({{grading_output.grade_percentages.D}}%)

### 校验问题汇总
- 时间问题：{{validation_output.issue_summary.time_issue}}条
- 预测值标注问题：{{validation_output.issue_summary.forecast_issue}}条

## 报告要求

### 结构要求

1. **报告摘要**：概括本期数据整体质量
2. **核心数据**：列出A级高可信度数据
3. **数据问题**：列出主要数据问题和待验证项
4. **建议**：给出后续行动建议

### 格式要求

- 使用Markdown格式
- 数据问题需标注⚠️
- 预测值需标注⚠️预测值
- 每个数据点注明来源

### 重要提示

1. **高可信优先**：重点展示A级数据
2. **透明披露**：如实反映数据质量问题
3. **可追溯**：每个结论注明数据来源

## 输出

请生成完整的Markdown格式报告。
```

#### 输出配置：

```
输出变量名：final_report
类型：String（文本）
```

---

### 节点10：结束节点

**功能**：输出最终报告

#### 配置步骤：

1. 拖拽 **"结束"** 节点到画布末尾
2. 用线连接：节点9 → 结束节点

#### 输出配置：

```
输出变量名：report
类型：String
值：{{节点9的输出}}
```

---

## 四、节点连接关系图

```
                    ┌─────────────────────────────────────┐
                    │                                     │
    ┌──────────┐    │   ┌─────────────┐                  │
    │  节点1    │    │   │  节点2       │                  │
    │  开始     │────┼──▶│  国内数据搜集 │                  │
    └──────────┘    │   └─────────────┘                  │
                    │   ┌─────────────┐                  │
                    │   │  节点3       │                  │
                    │   │  国际数据搜集 │                  │
                    │   └─────────────┘                  │
                    │   ┌─────────────┐                  │
                    │   │  节点4       │                  │
                    │   │  竞对动态    │──────┐          │
                    │   └─────────────┘      │          │
                    │   ┌─────────────┐      │          │
                    │   │  节点5       │      │          │
                    │   │  行业资讯    │──────┤          │
                    │   └─────────────┘      │          │
                    │          │            │          │
                    │          └────────────┼──────────┼──▶ 节点6 (数据合并)
                    │                         │          │          │
                    │                         └──────────┴──▶ 节点7 (校验)
                    │                                              │
                    │                                              │
                    │                                              └──▶ 节点8 (分级)
                    │                                                   │
                    │                                                   │
                    │                                                   └──▶ 节点9 (报告生成)
                    │                                                        │
                    │                                                        │
                    │                                                        └──▶ 节点10 (结束)
                    └─────────────────────────────────────────────────────────┘
```

### 连接说明

| 起点 | 终点 | 连接类型 | 说明 |
|------|------|---------|------|
| 节点1 (开始) | 节点2-5 | 串行/并行 | 同时传递industry/time_period参数 |
| 节点2,3,4,5 | 节点6 | 并行 | 数据汇入合并节点 |
| 节点6 | 节点7 | 串行 | 传递合并后的数据 |
| 节点7 | 节点8 | 串行 | 传递校验结果 |
| 节点8 | 节点9 | 串行 | 传递分级结果 |
| 节点9 | 节点10 | 串行 | 输出最终报告 |

---

## 五、测试与发布

### 5.1 本地测试

1. 点击工作流画布右上角的 **"试运行"** 按钮
2. 在弹出的对话框中填写测试参数：

```
industry: "光伏"
time_period: "2026年3月"
data_types: ["domestic", "global", "competitor", "news"]
```

3. 点击 **"开始运行"** 观察各节点执行情况
4. 检查各节点的输入输出是否符合预期

### 5.2 常见测试问题

**问题1：JSON解析失败**
- 检查上游LLM节点的输出格式
- 在代码节点添加异常处理

**问题2：变量未定义**
- 检查节点连接的变量名是否正确
- 确认输入配置中变量映射正确

**问题3：数据为空**
- 检查LLM节点的Prompt是否足够清晰
- 确认联网搜索插件已启用

### 5.3 正式发布

1. 测试通过后，点击 **"发布"** 按钮
2. 填写发布信息：
   - 版本号：v1.0.0
   - 更新说明：初始版本
3. 选择发布范围（个人/团队/公开）
4. 点击确认发布

### 5.4 发布后使用

1. 创建Bot，关联工作流
2. 在Bot配置中选择刚发布的工作流
3. 配置Bot的开场白和用户提示
4. 发布Bot到所需渠道（Discord/Telegram/飞书等）

---

## 六、常见问题（FAQ）

### Q1: 如何添加更多数据源？

在对应的LLM节点Prompt中添加新的数据源要求，例如：
```
## 数据来源扩展
除上述来源外，也可参考：
- 中国有色金属工业协会
- 行业上市公司公告
```

### Q2: 如何处理API调用失败？

在代码节点中添加重试逻辑：
```python
def call_with_retry(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(1)  # 重试前等待
```

### Q3: 如何支持更多行业？

1. 在开始节点添加industry参数
2. 修改各LLM节点的Prompt模板，使用`{{industry}}`变量
3. 在代码节点中添加行业特定的处理逻辑

### Q4: 如何定时自动执行？

1. 使用Coze的定时任务功能
2. 或通过API调用触发工作流执行
3. 配置webhook接收外部触发

### Q5: 代码节点的执行超时如何处理？

- 精简代码逻辑
- 分批处理大数据
- 使用异步调用
- 设置合理的超时时间

---

## 七、进阶技巧

### 7.1 缓存优化

对于不常变化的数据（如行业背景），可以在开始节点添加缓存逻辑：
```python
CACHE_KEY = f"industry_background_{industry}"
cached = cache_get(CACHE_KEY)
if cached:
    return cached
# ... 获取新数据后存入缓存
cache_set(CACHE_KEY, data, ttl=86400)  # 24小时过期
```

### 7.2 并发优化

多个独立数据源可以同时调用：
```python
import asyncio

async def fetch_all():
    tasks = [
        fetch_domestic(),
        fetch_global(),
        fetch_news()
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 7.3 错误恢复

关键节点添加备用方案：
```python
try:
    result = primary_source()
except Exception as e:
    print(f"主数据源失败: {e}")
    result = backup_source()  # 使用备用数据源
```

---

## 八、参考资源

- [Coze工作流官方文档](https://www.coze.cn/docs)
- [Coze API参考](https://www.coze.cn/docs/api)
- 项目源码：[coze/workflow_nodes/](workflow_nodes/)

---

*本文档最后更新：2026年5月*
