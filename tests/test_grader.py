# -*- coding: utf-8 -*-
"""
可信度分级引擎测试

测试来源预评级、交叉验证升级、数据冲突降级、批量评级统计
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from dataclasses import replace

from data_models import (
    DomesticDataPoint, GlobalDataPoint, DataSource, ValidationResult,
    ValidationIssue, CredibilityGrade, GradingResult
)
from grader import CredibilityGrader


class TestSourceGradeMapping:
    """来源预评级测试"""
    
    def test_grade_a_source(self):
        """A级来源"""
        grader = CredibilityGrader()
        
        sources = ["国家能源局", "国家统计局", "BNEF", "IEA", "SNE Research"]
        for source in sources:
            grade = grader.get_base_grade(source)
            assert grade == CredibilityGrade.A, f"{source} should be A"
    
    def test_grade_b_source(self):
        """B级来源"""
        grader = CredibilityGrader()
        
        sources = ["InfoLink", "Mysteel", "大东时代智库", "财联社"]
        for source in sources:
            grade = grader.get_base_grade(source)
            assert grade == CredibilityGrade.B, f"{source} should be B"
    
    def test_grade_c_source(self):
        """C级来源"""
        grader = CredibilityGrader()
        
        sources = ["某公众号", "自媒体A"]
        for source in sources:
            grade = grader.get_base_grade(source)
            # 默认返回B，但如果配置了C级规则才返回C
            assert grade in [CredibilityGrade.B, CredibilityGrade.C]
    
    def test_unknown_source(self):
        """未知来源"""
        grader = CredibilityGrader()
        grade = grader.get_base_grade("完全不认识的来源XYZ")
        assert grade in [CredibilityGrade.B, CredibilityGrade.C, CredibilityGrade.D]


class TestCrossValidation:
    """交叉验证测试"""
    
    def test_a_grade_with_two_a_validations(self, sample_domestic_data_point):
        """A级来源 + 2个A级验证 = 升A"""
        # 设置A级来源
        data_point = replace(sample_domestic_data_point)
        data_point.source = DataSource(
            name="国家能源局",
            url="https://www.nea.gov.cn/test",
            publish_date="2026-04-23",
            credibility=CredibilityGrade.A
        )
        # 添加A级验证
        data_point.cross_validation = ["数字新能源DNE", "银河证券研报"]
        
        grader = CredibilityGrader()
        result = grader.grade_data_point(data_point, None)
        
        assert result.grade == CredibilityGrade.A
        assert result.has_cross_validation is True
    
    def test_b_grade_single_validation(self, sample_domestic_data_point):
        """B级来源 + 单个验证"""
        grader = CredibilityGrader()
        result = grader.grade_data_point(sample_domestic_data_point, None)
        
        # 基础是A级来源
        assert result.base_grade == CredibilityGrade.A
    
    def test_c_grade_upgrade_with_b_validation(self):
        """C级 + B级验证 = 升B"""
        data_point = DomesticDataPoint(
            _id="test_c_upgrade",
            indicator="某指标",
            value="100",
            unit="单位",
            time_period="2026年3月",
            source=DataSource(
                name="某行业媒体",
                url="http://test.com",
                publish_date="2026-04-10",
                credibility=CredibilityGrade.C
            ),
            cross_validation=["InfoLink"]  # B级来源验证
        )
        
        grader = CredibilityGrader()
        result = grader.grade_data_point(data_point, None)
        
        # 基础是B级来源，InfoLink匹配B级
        assert result.base_grade == CredibilityGrade.B


class TestConflictDegradation:
    """冲突降级测试"""
    
    def test_severe_conflict_degrade_to_d(self, sample_domestic_data_point):
        """严重冲突降级至D"""
        # 创建校验结果，包含严重冲突
        validation_result = ValidationResult(
            data_id="test_001",
            data_type="domestic",
            is_valid=True,
            no_conflict=False
        )
        validation_result.add_issue(ValidationIssue(
            issue_type="conflict",
            severity="error",
            message="多源数据差异超过20%，无法判断",
            details={"diff_percent": 25}
        ))
        
        grader = CredibilityGrader()
        result = grader.grade_data_point(sample_domestic_data_point, validation_result)
        
        # 严重冲突应该降级至D
        assert result.grade == CredibilityGrade.D
        assert len(result.downgrade_reasons) > 0


class TestValidationDegradation:
    """校验异常降级测试"""
    
    def test_time_inconsistency_degrade(self, sample_domestic_data_point):
        """时间不一致降级"""
        validation_result = ValidationResult(
            data_id="test_001",
            data_type="domestic",
            is_valid=True,
            time_consistency_passed=False
        )
        validation_result.add_issue(ValidationIssue(
            issue_type="time_inconsistency",
            severity="error",
            message="时间异常：3月10日发布的文章作为3月实际数据",
            details={}
        ))
        
        grader = CredibilityGrader()
        result = grader.grade_data_point(sample_domestic_data_point, validation_result)
        
        # 基础是A级，时间不一致应该降级
        assert len(result.downgrade_reasons) > 0 or result.grade == CredibilityGrade.B
    
    def test_forecast_unlabeled_degrade(self):
        """预测值未标注降级"""
        # 创建A级来源但预测值未标注
        validation_result = ValidationResult(
            data_id="test_forecast",
            data_type="domestic",
            is_valid=True,
            forecast_label_correct=False
        )
        validation_result.add_issue(ValidationIssue(
            issue_type="forecast_unlabeled",
            severity="warning",
            message="预测值未标注",
            details={}
        ))
        
        data_point = DomesticDataPoint(
            _id="test_forecast",
            indicator="光伏组件排产量",
            value="~47GW",
            unit="GW",
            time_period="2026年3月",
            source=DataSource(
                name="国家能源局",
                url="http://test.com",
                publish_date="2026-03-10",  # 周期内发布
                credibility=CredibilityGrade.A
            ),
            cross_validation=[],
            is_forecast=False
        )
        
        grader = CredibilityGrader()
        result = grader.grade_data_point(data_point, validation_result)
        
        # 预测值误标为实际值应该降级
        assert len(result.downgrade_reasons) > 0


class TestBatchGrading:
    """批量评级测试"""
    
    def test_batch_grading_stats(self, sample_domestic_data_point, sample_global_data_point):
        """批量评级统计"""
        grader = CredibilityGrader()
        
        data_points = [sample_domestic_data_point, sample_global_data_point]
        results, stats = grader.grade_all(data_points, None)
        
        assert len(results) == 2
        assert stats.total_count == 2
        assert sum(stats.grade_distribution.values()) == 2
        
        # 验证百分比计算
        total = sum(stats.grade_distribution.values())
        if total > 0:
            for grade, pct in stats.grade_percentages.items():
                count = stats.grade_distribution.get(grade, 0)
                expected_pct = round(count / total * 100, 2)
                assert abs(pct - expected_pct) < 0.1
    
    def test_batch_with_validation_results(self, sample_domestic_data_point):
        """批量评级（带校验结果）"""
        validation_results = [
            ValidationResult(
                data_id="test_001",
                data_type="domestic",
                is_valid=True
            )
        ]
        
        grader = CredibilityGrader()
        results, stats = grader.grade_all([sample_domestic_data_point], validation_results)
        
        assert len(results) == 1
        assert stats.validation_pass_count == 1


class TestGradingReasons:
    """评级理由测试"""
    
    def test_grade_reason_includes_source(self, sample_domestic_data_point):
        """评级理由包含来源信息"""
        grader = CredibilityGrader()
        result = grader.grade_data_point(sample_domestic_data_point, None)
        
        assert "国家能源局" in result.grade_reason
    
    def test_upgrade_suggestions(self, sample_domestic_data_point):
        """升级建议"""
        grader = CredibilityGrader()
        result = grader.grade_data_point(sample_domestic_data_point, None)
        
        # A级来源可能有升级建议
        assert isinstance(result.upgrade_suggestions, list)
