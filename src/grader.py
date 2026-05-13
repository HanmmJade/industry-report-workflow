# -*- coding: utf-8 -*-
"""
可信度分级引擎 - 根据规则引擎执行A/B/C/D评级

包含：
- grade_data_point: 单个数据点评级
- grade_all: 批量评级及统计
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from data_models import (
    DomesticDataPoint, GlobalDataPoint, CompetitorEvent, IndustryNews,
    ValidationResult, GradingResult, GradingStats, CredibilityGrade
)
from data_sources import get_source_manager


class CredibilityGrader:
    """
    可信度分级引擎
    
    根据来源权威性、交叉验证、校验结果执行A/B/C/D评级
    """
    
    # 典型A级来源
    TYPICAL_A_SOURCES = [
        "国家能源局", "国家统计局", "中国汽车工业协会", "中国汽车动力电池产业创新联盟",
        "BNEF", "IEA", "IEA PVPS", "SNE Research", "CPIA",
        "Nature", "Science", "证监会", "交易所", "EVtank",
        "Benchmark Minerals", "Ember", "MarkLines"
    ]
    
    # 典型B级来源
    TYPICAL_B_SOURCES = [
        "InfoLink", "Mysteel", "大东时代智库", "ICC鑫椤资讯",
        "财联社", "界面新闻", "证券时报", "券商研究报告",
        "激光制造网", "PV Magazine", "GGII", "数字新能源DNE"
    ]
    
    # 典型C级来源
    TYPICAL_C_SOURCES = [
        "普通行业媒体", "公众号", "自媒体", "专家博客"
    ]
    
    def __init__(self, rules_path: Optional[str] = None):
        """
        初始化分级引擎
        
        Args:
            rules_path: 规则配置文件路径
        """
        if rules_path is None:
            current_dir = Path(__file__).parent.parent
            rules_path = current_dir / "rules" / "credibility_rules.json"
        
        self.rules_path = Path(rules_path)
        self.rules = self._load_rules()
        
        # 数据源管理器
        self.source_manager = get_source_manager()
    
    def _load_rules(self) -> Dict[str, Any]:
        """加载规则配置"""
        if not self.rules_path.exists():
            return self._get_default_rules()
        
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """获取默认规则"""
        return {
            "grade_definitions": {
                "A": {
                    "name": "高可信",
                    "weight": 1.0,
                    "typical_sources": self.TYPICAL_A_SOURCES
                },
                "B": {
                    "name": "较可信",
                    "weight": 0.75,
                    "typical_sources": self.TYPICAL_B_SOURCES
                },
                "C": {
                    "name": "待验证",
                    "weight": 0.5,
                    "typical_sources": self.TYPICAL_C_SOURCES
                },
                "D": {
                    "name": "存疑",
                    "weight": 0.25,
                    "typical_sources": []
                }
            },
            "cross_validation_rules": {
                "enabled": True,
                "multi_source_bonus": 0.25,
                "threshold_percent": 10
            }
        }
    
    def get_base_grade(self, source_name: str) -> CredibilityGrade:
        """
        根据来源名称确定基础评级
        
        Args:
            source_name: 来源名称
        
        Returns:
            基础可信度等级
        """
        # 标准化来源名称
        source_lower = source_name.lower()
        
        # 检查A级
        for typical in self.TYPICAL_A_SOURCES:
            if typical.lower() in source_lower or source_lower in typical.lower():
                return CredibilityGrade.A
        
        # 检查B级
        for typical in self.TYPICAL_B_SOURCES:
            if typical.lower() in source_lower or source_lower in typical.lower():
                return CredibilityGrade.B
        
        # 检查C级
        for typical in self.TYPICAL_C_SOURCES:
            if typical.lower() in source_lower:
                return CredibilityGrade.C
        
        # 从配置中获取
        config_grade = self.source_manager.get_credibility_by_source(source_name)
        grade_map = {"A": CredibilityGrade.A, "B": CredibilityGrade.B, 
                    "C": CredibilityGrade.C, "D": CredibilityGrade.D}
        return grade_map.get(config_grade, CredibilityGrade.B)
    
    def has_cross_validation(self, data_point: Any) -> Tuple[bool, int, int]:
        """
        检查是否有交叉验证
        
        Args:
            data_point: 数据点对象
        
        Returns:
            (是否有交叉验证, 验证来源总数, A级验证来源数)
        """
        cross_sources = getattr(data_point, 'cross_validation', []) or []
        
        if not cross_sources:
            return False, 0, 0
        
        grade_a_count = 0
        for source in cross_sources:
            if isinstance(source, str):
                if self.get_base_grade(source) == CredibilityGrade.A:
                    grade_a_count += 1
        
        return len(cross_sources) > 0, len(cross_sources), grade_a_count
    
    def grade_data_point(self, data_point: Any, validation_result: Optional[ValidationResult] = None) -> GradingResult:
        """
        对单个数据点执行可信度评级
        
        Args:
            data_point: 数据点对象
            validation_result: 校验结果（可选）
        
        Returns:
            GradingResult对象
        """
        data_id = getattr(data_point, '_id', 'unknown')
        
        # 获取来源名称
        source = getattr(data_point, 'source', None)
        if source:
            source_name = getattr(source, 'name', '') or (source.get('name') if isinstance(source, dict) else '')
        else:
            source_name = '来源不明'
        
        # 1. 确定基础评级
        base_grade = self.get_base_grade(source_name)
        
        # 2. 检查交叉验证
        has_cv, cv_count, cv_grade_a_count = self.has_cross_validation(data_point)
        
        # 3. 计算最终评级
        final_grade = base_grade
        grade_reason_parts = []
        upgrade_suggestions = []
        downgrade_reasons = []
        
        # 评级理由
        grade_reason_parts.append(f"来源：{source_name}")
        
        # 3.1 基础评级
        if base_grade == CredibilityGrade.A:
            grade_reason_parts.append("来源为A级机构")
        elif base_grade == CredibilityGrade.B:
            grade_reason_parts.append("来源为B级机构")
        elif base_grade == CredibilityGrade.C:
            grade_reason_parts.append("来源为C级机构")
        else:
            grade_reason_parts.append("⚠️来源不明")
        
        # 3.2 交叉验证调整
        if has_cv:
            if cv_grade_a_count >= 2:
                # 2个及以上A级来源验证 -> 升A
                final_grade = CredibilityGrade.A
                grade_reason_parts.append(f"✓ 获{cv_grade_a_count}个A级来源交叉验证，升级至A级")
            elif cv_grade_a_count == 1 and base_grade == CredibilityGrade.B:
                # 1个A级来源验证，保持B级
                grade_reason_parts.append(f"✓ 获1个A级来源验证，保持B级")
            elif cv_count >= 1 and base_grade == CredibilityGrade.C:
                # C级+任意验证 -> 升B
                final_grade = CredibilityGrade.B
                grade_reason_parts.append(f"✓ 获{cv_count}个来源验证，升级至B级")
        else:
            if base_grade == CredibilityGrade.A:
                upgrade_suggestions.append("建议增加至少1个A级来源进行交叉验证以提升可信度")
            elif base_grade == CredibilityGrade.B:
                upgrade_suggestions.append("建议增加交叉验证来源")
        
        # 3.3 校验异常降级
        if validation_result:
            if not validation_result.is_valid:
                # 校验未通过，降级
                if final_grade == CredibilityGrade.A:
                    final_grade = CredibilityGrade.B
                    downgrade_reasons.append("校验异常降级")
                    grade_reason_parts.append("⚠️校验异常，降一级")
                elif final_grade == CredibilityGrade.B:
                    final_grade = CredibilityGrade.C
                    downgrade_reasons.append("校验异常降级")
                    grade_reason_parts.append("⚠️校验异常，降一级")
            
            # 检查具体异常
            for issue in validation_result.issues:
                if issue.issue_type == "time_inconsistency":
                    downgrade_reasons.append(f"时间不一致: {issue.message}")
                    if final_grade.value != "D":
                        grade_reason_parts.append(f"⚠️{issue.message}")
                
                elif issue.issue_type == "forecast_unlabeled":
                    downgrade_reasons.append(f"预测值未标注: {issue.message}")
                    if final_grade == CredibilityGrade.A:
                        final_grade = CredibilityGrade.C
                        grade_reason_parts.append("⚠️预测值误标为实际值，降级至C级")
                
                elif issue.issue_type == "conflict":
                    # 严重冲突降级至D
                    final_grade = CredibilityGrade.D
                    downgrade_reasons.append(f"数据冲突: {issue.message}")
                    grade_reason_parts.append(f"⚠️数据冲突严重，降级至D级")
        
        # 4. 处理特殊标记
        notes = getattr(data_point, 'notes', '') or ''
        if "暂未找到" in notes or "待验证" in notes:
            if final_grade.value in ["A", "B"]:
                final_grade = CredibilityGrade.C
                grade_reason_parts.append("⚠️数据待验证，降级至C级")
        
        if "来源不明" in notes:
            final_grade = CredibilityGrade.D
            grade_reason_parts.append("⚠️来源不明，定级D级")
        
        # 5. 组装评级理由
        grade_reason = "；".join(grade_reason_parts)
        
        # 6. 生成升级建议
        if final_grade == CredibilityGrade.B and not has_cv:
            upgrade_suggestions.append("建议增加交叉验证来源以升级至A级")
        if final_grade == CredibilityGrade.C:
            upgrade_suggestions.append("建议获取官方数据或权威机构确认以提升可信度")
        
        return GradingResult(
            data_id=data_id,
            grade=final_grade,
            base_grade=base_grade,
            grade_reason=grade_reason,
            upgrade_suggestions=upgrade_suggestions,
            downgrade_reasons=downgrade_reasons,
            has_cross_validation=has_cv,
            validation_sources_count=cv_count,
            validation_sources_grade_a=cv_grade_a_count
        )
    
    def grade_all(self, data_points: List[Any], validation_results: Optional[List[ValidationResult]] = None) -> Tuple[List[GradingResult], GradingStats]:
        """
        批量评级
        
        Args:
            data_points: 数据点列表
            validation_results: 校验结果列表（可选）
        
        Returns:
            (GradingResult列表, GradingStats统计)
        """
        # 构建校验结果映射
        validation_map = {}
        if validation_results:
            for vr in validation_results:
                validation_map[vr.data_id] = vr
        
        # 执行评级
        grading_results = []
        stats = GradingStats()
        
        # 统计各类异常
        issue_stats: Dict[str, int] = {}
        downgrade_stats: Dict[str, int] = {}
        
        for dp in data_points:
            data_id = getattr(dp, '_id', 'unknown')
            validation_result = validation_map.get(data_id)
            
            result = self.grade_data_point(dp, validation_result)
            grading_results.append(result)
            
            # 统计
            grade_key = result.grade.value if isinstance(result.grade, CredibilityGrade) else str(result.grade)
            stats.grade_distribution[grade_key] = stats.grade_distribution.get(grade_key, 0) + 1
            
            # 校验通过统计
            if validation_result and validation_result.is_valid:
                stats.validation_pass_count += 1
            
            # 异常统计
            if validation_result:
                for issue in validation_result.issues:
                    issue_type = issue.issue_type
                    issue_stats[issue_type] = issue_stats.get(issue_type, 0) + 1
            
            # 降级原因统计
            for reason in result.downgrade_reasons:
                key = reason.split(':')[0] if ':' in reason else reason
                downgrade_stats[key] = downgrade_stats.get(key, 0) + 1
        
        # 计算统计
        stats.total_count = len(grading_results)
        stats.calculate_percentages()
        stats.validation_pass_rate = stats.validation_pass_count / stats.total_count if stats.total_count > 0 else 0
        stats.common_issues = issue_stats
        stats.common_downgrades = downgrade_stats
        
        return grading_results, stats


# 便捷函数
def grade_data_point(data_point: Any, validation_result: Optional[ValidationResult] = None) -> GradingResult:
    """对单个数据点执行可信度评级"""
    return CredibilityGrader().grade_data_point(data_point, validation_result)


def grade_all(data_points: List[Any], validation_results: Optional[List[ValidationResult]] = None) -> Tuple[List[GradingResult], GradingStats]:
    """批量评级"""
    return CredibilityGrader().grade_all(data_points, validation_results)
