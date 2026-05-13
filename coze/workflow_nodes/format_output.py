# -*- coding: utf-8 -*-
"""
Coze代码节点 - 输出格式化

此文件可直接粘贴到Coze代码节点中运行
纯Python实现，仅使用内置库
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional


# 可信度等级颜色映射
GRADE_COLORS = {
    "A": "🟢",
    "B": "🔵",
    "C": "🟡",
    "D": "🔴"
}

GRADE_NAMES = {
    "A": "高可信",
    "B": "较可信",
    "C": "待验证",
    "D": "存疑"
}


def format_grade(grade: str) -> str:
    """
    格式化等级显示
    
    Args:
        grade: 等级字母
    
    Returns:
        格式化后的字符串
    """
    color = GRADE_COLORS.get(grade, "⚪")
    name = GRADE_NAMES.get(grade, "未知")
    return f"{color}**{grade}级**({name})"


def generate_markdown_report(
    all_data: List[Dict] = None,
    grading_results: List[Dict] = None,
    grading_stats: Dict = None,
    validation_results: List[Dict] = None,
    time_period: str = ""
) -> str:
    """
    生成Markdown报告
    
    Args:
        all_data: 所有数据
        grading_results: 评级结果
        grading_stats: 统计信息
        validation_results: 校验结果
        time_period: 时间周期
    
    Returns:
        Markdown格式报告
    """
    all_data = all_data or []
    grading_results = grading_results or []
    grading_stats = grading_stats or {}
    validation_results = validation_results or []
    
    lines = []
    
    # 1. 报告头部
    lines.append("# 行业月报数据质量报告")
    lines.append("")
    lines.append(f"> **数据周期：** {time_period or '未指定'}")
    lines.append(f"> **生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> **数据条目数：** {len(all_data)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 2. 可信度分布
    if grading_stats:
        lines.append("## 一、可信度分布统计")
        lines.append("")
        lines.append("| 等级 | 数量 | 占比 |")
        lines.append("|------|------|------|")
        
        distribution = grading_stats.get("grade_distribution", {})
        percentages = grading_stats.get("grade_percentages", {})
        
        for grade in ["A", "B", "C", "D"]:
            count = distribution.get(grade, 0)
            pct = percentages.get(grade, 0)
            color = GRADE_COLORS.get(grade, "⚪")
            name = GRADE_NAMES.get(grade, grade)
            lines.append(f"| {color} {grade}级({name}) | {count} | {pct}% |")
        
        lines.append("")
        
        # 可视化条形图
        total = grading_stats.get("total", 1)
        lines.append("**分布可视化：**")
        for grade in ["A", "B", "C", "D"]:
            pct = percentages.get(grade, 0)
            bars = "█" * int(pct / 5)
            lines.append(f"{GRADE_COLORS.get(grade, '⚪')} {grade}级: {bars} {pct}%")
        lines.append("")
    
    # 3. 校验统计
    if validation_results:
        lines.append("## 二、校验统计")
        lines.append("")
        
        valid_count = sum(1 for v in validation_results if v.get("is_valid", True))
        pass_rate = round(valid_count / len(validation_results) * 100, 2) if validation_results else 0
        
        lines.append(f"- **校验通过率：** {pass_rate}%")
        lines.append(f"- **校验通过数量：** {valid_count}/{len(validation_results)}")
        lines.append("")
        
        # 异常统计
        issue_counts = {}
        for v in validation_results:
            for issue in v.get("issues", []):
                issue_type = issue.get("type", "unknown")
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        if issue_counts:
            lines.append("### 常见异常")
            lines.append("")
            for issue_type, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
                type_name = {
                    "time_inconsistency": "时间不一致",
                    "forecast_unlabeled": "预测值未标注",
                    "conflict": "数据冲突",
                    "url_invalid": "URL无效"
                }.get(issue_type, issue_type)
                lines.append(f"- **{type_name}：** {count}条")
            lines.append("")
    
    # 4. 详细数据
    lines.append("## 三、详细数据")
    lines.append("")
    
    # 构建评级映射
    grade_map = {}
    if grading_results:
        for g in grading_results:
            grade_map[g.get("data_id")] = g
    
    # 按类型分组
    data_by_type = {}
    for d in all_data:
        data_type = d.get("data_type", "unknown")
        if data_type not in data_by_type:
            data_by_type[data_type] = []
        data_by_type[data_type].append(d)
    
    type_names = {
        "domestic": "国内行业数据",
        "global": "国际行业数据",
        "competitor": "竞争对手动态",
        "news": "行业资讯"
    }
    
    for data_type, items in data_by_type.items():
        type_name = type_names.get(data_type, data_type)
        lines.append(f"### {type_name}（{len(items)}条）")
        lines.append("")
        lines.append("| 指标 | 数值 | 来源 | 评级 | 说明 |")
        lines.append("|------|------|------|------|------|")
        
        for item in items:
            indicator = item.get("indicator", "")[:20]
            value = item.get("value", "")[:15]
            source = item.get("source", {}).get("name", "未知")[:15]
            
            data_id = item.get("_id", "")
            grade_info = grade_map.get(data_id, {})
            grade = grade_info.get("grade", "?")
            grade_display = format_grade(grade) if grade != "?" else "⚪?"
            
            notes = item.get("notes", "") or ""
            if len(notes) > 20:
                notes = notes[:20] + "..."
            
            lines.append(f"| {indicator} | {value} | {source} | {grade_display} | {notes} |")
        
        lines.append("")
    
    # 5. 升级建议汇总
    if grading_results:
        upgrade_items = []
        for g in grading_results:
            if g.get("upgrade_suggestions"):
                for suggestion in g["upgrade_suggestions"]:
                    data_id = g.get("data_id", "")
                    upgrade_items.append(f"- **[{data_id}]** {suggestion}")
        
        if upgrade_items:
            lines.append("## 四、升级建议")
            lines.append("")
            lines.append("> 以下数据建议提升可信度等级：")
            lines.append("")
            for item in upgrade_items[:10]:  # 最多显示10条
                lines.append(item)
            lines.append("")
    
    # 6. 脚注
    lines.append("---")
    lines.append("")
    lines.append("*本报告由行业月报自动化工作流生成*")
    lines.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return "\n".join(lines)


def generate_summary(
    grading_stats: Dict = None,
    validation_results: List[Dict] = None
) -> str:
    """
    生成摘要信息
    
    Args:
        grading_stats: 评级统计
        validation_results: 校验结果
    
    Returns:
        摘要文本
    """
    parts = []
    
    if grading_stats:
        total = grading_stats.get("total", 0)
        a_count = grading_stats.get("grade_distribution", {}).get("A", 0)
        a_pct = grading_stats.get("grade_percentages", {}).get("A", 0)
        
        parts.append(f"共{total}条数据，")
        parts.append(f"A级{a_count}条（{a_pct}%）")
    
    if validation_results:
        valid_count = sum(1 for v in validation_results if v.get("is_valid", True))
        parts.append(f"校验通过{valid_count}条")
    
    return "，".join(parts) if parts else "无数据"


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
        report_content = generate_markdown_report(
            all_data=args.get("all_data"),
            grading_results=args.get("grading_results"),
            grading_stats=args.get("grading_stats"),
            validation_results=args.get("validation_results"),
            time_period=args.get("time_period", "")
        )
        
        summary = generate_summary(
            grading_stats=args.get("grading_stats"),
            validation_results=args.get("validation_results")
        )
        
        return {
            "success": True,
            "report_content": report_content,
            "summary": summary
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "report_content": f"# 报告生成失败\n\n错误：{str(e)}",
            "summary": "报告生成失败"
        }


# 测试
if __name__ == "__main__":
    test_stats = {
        "total": 5,
        "grade_distribution": {"A": 3, "B": 1, "C": 1, "D": 0},
        "grade_percentages": {"A": 60, "B": 20, "C": 20, "D": 0}
    }
    
    report = generate_markdown_report(
        all_data=[
            {
                "_id": "DOM_0001",
                "data_type": "domestic",
                "indicator": "光伏电池装机量",
                "value": "891万kW",
                "source": {"name": "国家能源局"},
                "notes": ""
            }
        ],
        grading_results=[
            {
                "data_id": "DOM_0001",
                "grade": "A",
                "grade_reason": "A级来源",
                "upgrade_suggestions": []
            }
        ],
        grading_stats=test_stats,
        time_period="2026年3月"
    )
    
    print(report)
