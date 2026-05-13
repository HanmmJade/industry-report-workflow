# -*- coding: utf-8 -*-
"""
Coze代码节点 - 校验引擎

此文件可直接粘贴到Coze代码节点中运行
纯Python实现，仅使用内置库
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple


# 预测值关键词
FORECAST_KEYWORDS = [
    "预计", "预期", "预测", "估计", "展望",
    "将达", "将至", "将为", "有望", "约",
    "forecast", "prediction", "expected", "outlook"
]

# 实际值关键词
ACTUAL_KEYWORDS = ["实际", "统计", "累计", "实际值", "actual", "正式发布"]


def parse_time_period(period_str: str) -> Optional[Tuple[datetime, datetime]]:
    """
    解析时间周期字符串
    
    Args:
        period_str: 时间周期，如 "2026年3月"
    
    Returns:
        (周期开始, 周期结束) 或 None
    """
    # 年月格式：2026年3月
    import re
    match = re.match(r'(\d{4})年(\d{1,2})月', period_str)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        period_start = datetime(year, month, 1)
        # 月末
        if month == 12:
            period_end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = datetime(year, month + 1, 1) - timedelta(days=1)
        return period_start, period_end
    
    # 年份格式：2025年
    match = re.match(r'(\d{4})年', period_str)
    if match:
        year = int(match.group(1))
        period_start = datetime(year, 1, 1)
        period_end = datetime(year, 12, 31)
        return period_start, period_end
    
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串
    
    Returns:
        datetime对象或None
    """
    formats = ["%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d", "%Y.%m.%d"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def check_time_consistency(data: Dict, target_period: str) -> Tuple[bool, Optional[str]]:
    """
    检查时间一致性
    
    Args:
        data: 数据点
        target_period: 目标周期
    
    Returns:
        (是否一致, 异常信息)
    """
    period_info = parse_time_period(target_period)
    if not period_info:
        return True, None
    
    period_start, period_end = period_info
    
    # 获取发布日期
    source = data.get("source", {})
    publish_date_str = source.get("publish_date", "")
    
    if not publish_date_str or publish_date_str in ["-", "待查", "未知"]:
        return False, "⚠️发布时间待查，无法判断时间一致性"
    
    # 解析发布日期
    publish_date = parse_date(publish_date_str)
    if not publish_date:
        return True, None
    
    # 检查：发布日期必须在周期结束后
    if publish_date <= period_end:
        if data.get("is_forecast"):
            return True, None
        return False, f"⚠️时间异常：{publish_date_str}发布的{target_period}数据，实际数据应于{period_end.strftime('%Y-%m-%d')}之后发布"
    
    return True, None


def check_forecast_label(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    检查预测值标注
    
    Args:
        data: 数据点
    
    Returns:
        (标注是否正确, 异常信息)
    """
    if data.get("is_forecast"):
        return True, None
    
    value = data.get("value", "")
    notes = data.get("notes", "")
    
    # 检查是否包含预测关键词
    for keyword in FORECAST_KEYWORDS:
        if keyword.lower() in value.lower() or keyword.lower() in notes.lower():
            return False, "⚠️未标注为预测值"
    
    # 检查是否包含~等预测特征符
    if "~" in value and any(unit in value for unit in ["GW", "GWh", "万辆", "万kW"]):
        return False, "⚠️数值含预测特征符（~），建议明确标注"
    
    return True, None


def detect_conflicts(all_data: List[Dict], indicator: str, threshold: float = 10.0) -> List[Dict]:
    """
    检测数据冲突
    
    Args:
        all_data: 所有数据
        indicator: 指标名称
        threshold: 差异阈值百分比
    
    Returns:
        冲突列表
    """
    import re
    
    # 筛选同指标数据
    same_indicator = [d for d in all_data 
                     if d.get("indicator") == indicator]
    
    if len(same_indicator) < 2:
        return []
    
    # 提取数值
    values = []
    for d in same_indicator:
        value_str = d.get("value", "")
        nums = re.findall(r'[\d.]+', value_str)
        if nums:
            try:
                value = float(nums[0])
                source_name = d.get("source", {}).get("name", "未知")
                values.append({
                    "source": source_name,
                    "value": value,
                    "raw_value": value_str,
                    "data_id": d.get("_id")
                })
            except ValueError:
                continue
    
    if len(values) < 2:
        return []
    
    # 检测差异
    conflicts = []
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            v1, v2 = values[i]["value"], values[j]["value"]
            if v1 == 0 or v2 == 0:
                continue
            
            diff_percent = abs(v1 - v2) / max(v1, v2) * 100
            
            if diff_percent > threshold:
                conflicts.append({
                    "indicator": indicator,
                    "source1": values[i]["source"],
                    "value1": values[i]["raw_value"],
                    "source2": values[j]["source"],
                    "value2": values[j]["raw_value"],
                    "diff_percent": round(diff_percent, 2),
                    "severity": "error" if diff_percent > 20 else "warning"
                })
    
    return conflicts


def validate_data(data: Dict, target_period: str, all_data: List[Dict] = None) -> Dict:
    """
    校验单个数据点
    
    Args:
        data: 数据点
        target_period: 目标周期
        all_data: 所有数据（用于冲突检测）
    
    Returns:
        校验结果
    """
    data_id = data.get("_id", "unknown")
    
    result = {
        "data_id": data_id,
        "is_valid": True,
        "issues": [],
        "time_consistency_passed": True,
        "forecast_label_correct": True,
        "no_conflict": True,
        "validation_timestamp": datetime.now().isoformat()
    }
    
    # 1. 时间一致性检查
    if target_period:
        time_ok, time_msg = check_time_consistency(data, target_period)
        if not time_ok:
            result["time_consistency_passed"] = False
            result["is_valid"] = False
            result["issues"].append({
                "type": "time_inconsistency",
                "severity": "error",
                "message": time_msg
            })
    
    # 2. 预测值标注检查
    forecast_ok, forecast_msg = check_forecast_label(data)
    if not forecast_ok:
        result["forecast_label_correct"] = False
        result["issues"].append({
            "type": "forecast_unlabeled",
            "severity": "warning",
            "message": forecast_msg
        })
    
    # 3. URL检查
    source = data.get("source", {})
    url = source.get("url", "")
    if url and url not in ["-", "⚠️暂未找到"]:
        if not url.startswith("http"):
            result["issues"].append({
                "type": "url_invalid",
                "severity": "warning",
                "message": f"URL格式可能无效: {url}"
            })
    
    return result


def validate_batch(all_data: List[Dict], target_period: str = "") -> Dict[str, Any]:
    """
    批量校验
    
    Args:
        all_data: 所有数据
        target_period: 目标周期
    
    Returns:
        校验结果和统计
    """
    if not all_data:
        return {
            "validation_results": [],
            "stats": {
                "total": 0,
                "valid_count": 0,
                "pass_rate": 0,
                "issue_counts": {}
            }
        }
    
    # 批量校验
    validation_results = []
    for data in all_data:
        result = validate_data(data, target_period, all_data)
        validation_results.append(result)
    
    # 统计
    valid_count = sum(1 for r in validation_results if r["is_valid"])
    issue_counts = {}
    for r in validation_results:
        for issue in r["issues"]:
            issue_type = issue["type"]
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
    
    stats = {
        "total": len(validation_results),
        "valid_count": valid_count,
        "pass_rate": round(valid_count / len(validation_results) * 100, 2) if validation_results else 0,
        "issue_counts": issue_counts
    }
    
    return {
        "validation_results": validation_results,
        "stats": stats
    }


# Coze代码节点入口
def handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coze代码节点处理函数
    
    Args:
        args: 输入参数
    
    Returns:
        处理结果
    """
    try:
        all_data = args.get("all_data", [])
        time_period = args.get("time_period", "")
        
        result = validate_batch(all_data, time_period)
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "validation_results": [],
            "stats": {}
        }


# 测试
if __name__ == "__main__":
    test_data = [
        {
            "_id": "DOM_0001",
            "indicator": "光伏电池装机量",
            "value": "891万kW",
            "unit": "万千瓦",
            "source": {"name": "国家能源局", "publish_date": "2026-04-23"},
            "is_forecast": False
        },
        {
            "_id": "DOM_0002",
            "indicator": "光伏组件排产量",
            "value": "~47GW",
            "source": {"name": "InfoLink", "publish_date": "2026-04-15"},
            "is_forecast": False
        }
    ]
    
    result = validate_batch(test_data, "2026年3月")
    print(json.dumps(result, ensure_ascii=False, indent=2))
