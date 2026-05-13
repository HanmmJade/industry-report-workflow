# -*- coding: utf-8 -*-
"""
Coze代码节点 - 可信度分级引擎

此文件可直接粘贴到Coze代码节点中运行
纯Python实现，仅使用内置库
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional


# 典型A级来源
TYPICAL_A_SOURCES = [
    "国家能源局", "国家统计局", "中国汽车工业协会", "中国汽车动力电池产业创新联盟",
    "BNEF", "IEA", "IEA PVPS", "SNE Research", "CPIA",
    "Nature", "Science", "证监会", "交易所", "EVtank",
    "Benchmark Minerals", "Ember", "MarkLines", "Fraunhofer"
]

# 典型B级来源
TYPICAL_B_SOURCES = [
    "InfoLink", "Mysteel", "大东时代智库", "ICC鑫椤资讯", "数字新能源DNE",
    "财联社", "界面新闻", "证券时报", "券商研究报告",
    "激光制造网", "PV Magazine", "GGII"
]

# 典型C级来源
TYPICAL_C_SOURCES = [
    "公众号", "自媒体", "专家博客", "普通行业媒体"
]


def get_base_grade(source_name: str) -> str:
    """
    根据来源名称确定基础评级
    
    Args:
        source_name: 来源名称
    
    Returns:
        基础评级 (A/B/C/D)
    """
    if not source_name:
        return "D"
    
    source_lower = source_name.lower()
    
    # 检查A级
    for typical in TYPICAL_A_SOURCES:
        if typical.lower() in source_lower:
            return "A"
    
    # 检查B级
    for typical in TYPICAL_B_SOURCES:
        if typical.lower() in source_lower:
            return "B"
    
    # 检查C级
    for typical in TYPICAL_C_SOURCES:
        if typical.lower() in source_lower:
            return "C"
    
    # 默认B级
    return "B"


def has_cross_validation(data: Dict) -> tuple:
    """
    检查是否有交叉验证
    
    Args:
        data: 数据点
    
    Returns:
        (是否有验证, 验证数量, A级验证数量)
    """
    cross_sources = data.get("cross_validation", [])
    
    if not cross_sources:
        return False, 0, 0
    
    grade_a_count = 0
    for source in cross_sources:
        if isinstance(source, str) and get_base_grade(source) == "A":
            grade_a_count += 1
    
    return len(cross_sources) > 0, len(cross_sources), grade_a_count


def grade_data_point(data: Dict, validation_result: Optional[Dict] = None) -> Dict:
    """
    对单个数据点执行可信度评级
    
    Args:
        data: 数据点
        validation_result: 校验结果
    
    Returns:
        评级结果
    """
    data_id = data.get("_id", "unknown")
    
    # 获取来源名称
    source = data.get("source", {})
    source_name = source.get("name", "来源不明")
    
    # 1. 确定基础评级
    base_grade = get_base_grade(source_name)
    
    # 2. 检查交叉验证
    has_cv, cv_count, cv_grade_a_count = has_cross_validation(data)
    
    # 3. 计算最终评级
    final_grade = base_grade
    grade_reason_parts = [f"来源：{source_name}"]
    upgrade_suggestions = []
    downgrade_reasons = []
    
    # 基础评级说明
    if base_grade == "A":
        grade_reason_parts.append("来源为A级机构")
    elif base_grade == "B":
        grade_reason_parts.append("来源为B级机构")
    elif base_grade == "C":
        grade_reason_parts.append("来源为C级机构")
    else:
        grade_reason_parts.append("⚠️来源不明")
    
    # 交叉验证调整
    if has_cv:
        if cv_grade_a_count >= 2:
            final_grade = "A"
            grade_reason_parts.append(f"✓ 获{cv_grade_a_count}个A级来源交叉验证，升级至A级")
        elif cv_grade_a_count == 1 and base_grade == "B":
            grade_reason_parts.append(f"✓ 获1个A级来源验证，保持B级")
        elif cv_count >= 1 and base_grade == "C":
            final_grade = "B"
            grade_reason_parts.append(f"✓ 获{cv_count}个来源验证，升级至B级")
    else:
        if base_grade == "A":
            upgrade_suggestions.append("建议增加至少1个A级来源进行交叉验证以提升可信度")
        elif base_grade == "B":
            upgrade_suggestions.append("建议增加交叉验证来源")
    
    # 校验异常处理
    if validation_result:
        issues = validation_result.get("issues", [])
        
        # 严重问题
        if not validation_result.get("is_valid", True):
            if final_grade == "A":
                final_grade = "B"
                downgrade_reasons.append("校验异常降级")
                grade_reason_parts.append("⚠️校验异常，降一级")
            elif final_grade == "B":
                final_grade = "C"
                downgrade_reasons.append("校验异常降级")
                grade_reason_parts.append("⚠️校验异常，降一级")
        
        # 具体异常
        for issue in issues:
            issue_type = issue.get("type", "")
            
            if issue_type == "time_inconsistency":
                downgrade_reasons.append(f"时间不一致")
                grade_reason_parts.append(f"⚠️{issue.get('message', '')}")
            
            elif issue_type == "forecast_unlabeled":
                downgrade_reasons.append("预测值未标注")
                if final_grade == "A":
                    final_grade = "C"
                    grade_reason_parts.append("⚠️预测值误标为实际值，降级至C级")
            
            elif issue_type == "conflict":
                if issue.get("severity") == "error":
                    final_grade = "D"
                    downgrade_reasons.append("数据冲突")
                    grade_reason_parts.append("⚠️数据冲突严重，降级至D级")
    
    # 特殊标记处理
    notes = data.get("notes", "") or ""
    if "暂未找到" in notes or "待验证" in notes:
        if final_grade in ["A", "B"]:
            final_grade = "C"
            grade_reason_parts.append("⚠️数据待验证，降级至C级")
    
    if "来源不明" in notes:
        final_grade = "D"
        grade_reason_parts.append("⚠️来源不明，定级D级")
    
    # 生成升级建议
    if not upgrade_suggestions:
        if final_grade == "B" and not has_cv:
            upgrade_suggestions.append("建议增加交叉验证来源以升级至A级")
        elif final_grade == "C":
            upgrade_suggestions.append("建议获取官方数据或权威机构确认以提升可信度")
    
    return {
        "data_id": data_id,
        "grade": final_grade,
        "base_grade": base_grade,
        "grade_reason": "；".join(grade_reason_parts),
        "upgrade_suggestions": upgrade_suggestions,
        "downgrade_reasons": downgrade_reasons,
        "has_cross_validation": has_cv,
        "validation_sources_count": cv_count,
        "validation_sources_grade_a": cv_grade_a_count,
        "grading_timestamp": datetime.now().isoformat()
    }


def grade_batch(all_data: List[Dict], validation_results: List[Dict] = None) -> Dict[str, Any]:
    """
    批量评级
    
    Args:
        all_data: 所有数据
        validation_results: 校验结果
    
    Returns:
        评级结果和统计
    """
    if not all_data:
        return {
            "grading_results": [],
            "stats": {
                "total": 0,
                "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0},
                "grade_percentages": {"A": 0, "B": 0, "C": 0, "D": 0}
            }
        }
    
    # 构建校验结果映射
    validation_map = {}
    if validation_results:
        for vr in validation_results:
            validation_map[vr.get("data_id")] = vr
    
    # 批量评级
    grading_results = []
    grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
    
    for data in all_data:
        data_id = data.get("_id")
        validation_result = validation_map.get(data_id)
        
        result = grade_data_point(data, validation_result)
        grading_results.append(result)
        
        # 统计
        grade = result["grade"]
        grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
    
    # 计算百分比
    total = len(grading_results)
    grade_percentages = {}
    if total > 0:
        for grade, count in grade_distribution.items():
            grade_percentages[grade] = round(count / total * 100, 2)
    
    stats = {
        "total": total,
        "grade_distribution": grade_distribution,
        "grade_percentages": grade_percentages
    }
    
    return {
        "grading_results": grading_results,
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
        validation_results = args.get("validation_results", [])
        
        result = grade_batch(all_data, validation_results)
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "grading_results": [],
            "stats": {}
        }


# 测试
if __name__ == "__main__":
    test_data = [
        {
            "_id": "DOM_0001",
            "indicator": "光伏电池装机量",
            "value": "891万kW",
            "source": {"name": "国家能源局"},
            "cross_validation": ["数字新能源DNE"],
            "is_forecast": False
        },
        {
            "_id": "DOM_0002",
            "indicator": "光伏组件排产量",
            "value": "~47GW",
            "source": {"name": "InfoLink"},
            "cross_validation": [],
            "is_forecast": False
        }
    ]
    
    result = grade_batch(test_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
