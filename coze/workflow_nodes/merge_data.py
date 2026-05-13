# -*- coding: utf-8 -*-
"""
Coze代码节点 - 数据合并与标准化

此文件可直接粘贴到Coze代码节点中运行
纯Python实现，仅使用内置库
"""

import json
import re
from typing import List, Dict, Any, Optional


def generate_id(data_type: str, index: int) -> str:
    """
    生成唯一ID
    
    Args:
        data_type: 数据类型
        index: 序号
    
    Returns:
        唯一ID字符串
    """
    prefix_map = {
        "domestic": "DOM",
        "global": "GLO",
        "competitor": "COMP",
        "news": "NEWS"
    }
    prefix = prefix_map.get(data_type, "UNK")
    return f"{prefix}_{index:04d}"


def normalize_data_point(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """
    标准化单个数据点
    
    Args:
        data: 原始数据
        data_type: 数据类型
    
    Returns:
        标准化后的数据
    """
    normalized = {
        "data_type": data_type,
        "_id": data.get("_id") or generate_id(data_type, 0),
        "indicator": data.get("indicator") or data.get("title") or "",
        "value": data.get("value") or data.get("description") or "",
        "unit": data.get("unit") or "",
        "time_period": data.get("time_period") or data.get("event_date") or data.get("date") or "",
        "source": {
            "name": data.get("source_name") or data.get("source") or data.get("信息来源") or "未知",
            "url": data.get("source_url") or data.get("信源URL") or data.get("url") or "",
            "publish_date": data.get("publish_date") or data.get("日期") or ""
        },
        "cross_validation": data.get("cross_validation") or [],
        "notes": data.get("notes") or data.get("备注") or "",
        "is_forecast": _check_forecast(data),
        "raw_data": data  # 保留原始数据
    }
    
    return normalized


def _check_forecast(data: Dict[str, Any]) -> bool:
    """
    检查是否为预测值
    
    Args:
        data: 数据字典
    
    Returns:
        是否为预测值
    """
    notes = data.get("notes", "") or data.get("备注", "") or ""
    value = data.get("value", "") or ""
    
    forecast_keywords = ["预计", "预测", "forecast", "预期", "estimate"]
    
    for keyword in forecast_keywords:
        if keyword in notes.lower() or keyword in value.lower():
            return True
    
    return False


def check_duplicates(all_data: List[Dict]) -> List[Dict]:
    """
    检测重复数据
    
    Args:
        all_data: 所有数据
    
    Returns:
        重复数据列表
    """
    seen = {}
    duplicates = []
    
    for item in all_data:
        key = f"{item.get('indicator', '')}_{item.get('value', '')}_{item.get('source', {}).get('name', '')}"
        
        if key in seen:
            duplicates.append({
                "original": seen[key],
                "duplicate": item
            })
        else:
            seen[key] = item
    
    return duplicates


def merge_data(
    domestic_data: List[Dict] = None,
    global_data: List[Dict] = None,
    competitor_events: List[Dict] = None,
    industry_news: List[Dict] = None
) -> Dict[str, Any]:
    """
    合并和标准化数据
    
    Args:
        domestic_data: 国内数据
        global_data: 国际数据
        competitor_events: 竞争对手动态
        industry_news: 行业资讯
    
    Returns:
        合并结果，包含all_data, summary, duplicates
    """
    # 初始化
    domestic_data = domestic_data or []
    global_data = global_data or []
    competitor_events = competitor_events or []
    industry_news = industry_news or []
    
    all_data = []
    
    # 标准化国内数据
    for i, item in enumerate(domestic_data):
        normalized = normalize_data_point(item, "domestic")
        normalized["_id"] = f"DOM_{i+1:04d}"
        all_data.append(normalized)
    
    # 标准化国际数据
    for i, item in enumerate(global_data):
        normalized = normalize_data_point(item, "global")
        normalized["_id"] = f"GLO_{i+1:04d}"
        all_data.append(normalized)
    
    # 标准化竞争对手动态
    for i, item in enumerate(competitor_events):
        normalized = normalize_data_point(item, "competitor")
        normalized["_id"] = f"COMP_{i+1:04d}"
        all_data.append(normalized)
    
    # 标准化行业资讯
    for i, item in enumerate(industry_news):
        normalized = normalize_data_point(item, "news")
        normalized["_id"] = f"NEWS_{i+1:04d}"
        all_data.append(normalized)
    
    # 检测重复
    duplicates = check_duplicates(all_data)
    
    # 生成统计摘要
    summary = {
        "total": len(all_data),
        "domestic_count": len(domestic_data),
        "global_count": len(global_data),
        "competitor_count": len(competitor_events),
        "news_count": len(industry_news),
        "duplicate_count": len(duplicates)
    }
    
    return {
        "all_data": all_data,
        "summary": summary,
        "duplicates": duplicates
    }


# Coze代码节点入口
def handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coze代码节点处理函数
    
    Args:
        args: 输入参数（包含domestic_data, global_data等）
    
    Returns:
        处理结果
    """
    try:
        result = merge_data(
            domestic_data=args.get("domestic_data"),
            global_data=args.get("global_data"),
            competitor_events=args.get("competitor_events"),
            industry_news=args.get("industry_news")
        )
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "all_data": [],
            "summary": {"total": 0},
            "duplicates": []
        }


# 测试
if __name__ == "__main__":
    # 测试数据
    test_domestic = [
        {
            "indicator": "光伏电池装机量",
            "value": "891万kW",
            "unit": "万千瓦",
            "source_name": "国家能源局",
            "publish_date": "2026-04-23"
        }
    ]
    
    result = merge_data(domestic_data=test_domestic)
    print(json.dumps(result, ensure_ascii=False, indent=2))
