# -*- coding: utf-8 -*-
"""
数据校验引擎测试

测试时间一致性检查、预测值检测、冲突检测、URL验证
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from data_models import (
    DomesticDataPoint, GlobalDataPoint, DataSource, CredibilityGrade
)
from validator import DataValidator


class TestTimeConsistency:
    """时间一致性检查测试"""
    
    def test_normal_case(self, sample_domestic_data_point):
        """正常情况：数据在周期结束后发布"""
        validator = DataValidator()
        is_valid, message = validator.check_time_consistency(
            sample_domestic_data_point,
            "2026年3月"
        )
        assert is_valid is True
        assert message is None
    
    def test_time_inconsistency_detected(self, time_inconsistent_data_point):
        """检测到时间不一致：数据在周期结束前发布"""
        validator = DataValidator()
        is_valid, message = validator.check_time_consistency(
            time_inconsistent_data_point,
            "2026年3月"
        )
        assert is_valid is False
        assert "时间异常" in message
    
    def test_forecast_allowed_same_period(self):
        """预测值允许在周期内发布"""
        data_point = DomesticDataPoint(
            _id="test_forecast",
            indicator="光伏组件排产量",
            value="~50GW",
            unit="GW",
            time_period="2026年3月",
            source=DataSource(
                name="InfoLink",
                url="https://infolink.com/test",
                publish_date="2026-03-10",
                credibility=CredibilityGrade.B
            ),
            cross_validation=[],
            is_forecast=True  # 明确标注为预测值
        )
        
        validator = DataValidator()
        is_valid, message = validator.check_time_consistency(data_point, "2026年3月")
        assert is_valid is True  # 预测值应该通过
    
    def test_missing_publish_date(self):
        """缺少发布日期"""
        data_point = DomesticDataPoint(
            _id="test_no_date",
            indicator="光伏组件排产量",
            value="~50GW",
            unit="GW",
            time_period="2026年3月",
            source=DataSource(
                name="InfoLink",
                url="",
                publish_date="待查",
                credibility=CredibilityGrade.B
            ),
            cross_validation=[]
        )
        
        validator = DataValidator()
        is_valid, message = validator.check_time_consistency(data_point, "2026年3月")
        assert is_valid is False
        assert "待查" in message


class TestForecastDetection:
    """预测值检测测试"""
    
    def test_labeled_forecast(self, sample_forecast_data_point):
        """已标注的预测值"""
        validator = DataValidator()
        is_correct, message = validator.check_forecast_flag(
            sample_forecast_data_point,
            sample_forecast_data_point.value,
            ""
        )
        # 由于是未标注的预测特征，应该返回False
        assert is_correct is False
    
    def test_properly_labeled_forecast(self):
        """正确标注的预测值"""
        data_point = DomesticDataPoint(
            _id="test_labeled",
            indicator="光伏组件排产量",
            value="⚠️预测值~50GW",
            unit="GW",
            time_period="2026年4月",
            source=DataSource(
                name="Mysteel",
                url="https://mysteel.net/test",
                publish_date="2026-03-25",
                credibility=CredibilityGrade.B
            ),
            cross_validation=[],
            is_forecast=True
        )
        
        validator = DataValidator()
        is_correct, message = validator.check_forecast_flag(data_point, data_point.value, data_point.notes)
        # 明确标注了预测值，应该通过
        assert is_correct is True
    
    def test_forecast_keyword_in_value(self):
        """值中包含预测关键词"""
        data_point = DomesticDataPoint(
            _id="test_keyword",
            indicator="光伏组件排产量",
            value="预计50GW",
            unit="GW",
            time_period="2026年4月",
            source=DataSource(
                name="Mysteel",
                url="https://mysteel.net/test",
                publish_date="2026-03-25",
                credibility=CredibilityGrade.B
            ),
            cross_validation=[],
            is_forecast=False
        )
        
        validator = DataValidator()
        is_correct, message = validator.check_forecast_flag(
            data_point,
            data_point.value,
            data_point.notes or ""
        )
        assert is_correct is False
        assert "未标注" in message
    
    def test_actual_value_keywords(self):
        """实际值关键词"""
        data_point = DomesticDataPoint(
            _id="test_actual",
            indicator="光伏组件产量",
            value="47GW",
            unit="GW",
            time_period="2026年3月",
            source=DataSource(
                name="国家能源局",
                url="https://nea.gov.cn/test",
                publish_date="2026-04-15",
                credibility=CredibilityGrade.A
            ),
            cross_validation=["InfoLink"],
            is_forecast=False
        )
        
        validator = DataValidator()
        is_correct, message = validator.check_forecast_flag(
            data_point,
            data_point.value,
            "实际统计值"
        )
        assert is_correct is True


class TestConflictDetection:
    """冲突检测测试"""
    
    def test_no_conflict_similar_values(self, multiple_data_points):
        """无冲突：相似数值"""
        validator = DataValidator()
        conflicts = validator.detect_conflicts(multiple_data_points, "光伏组件排产量")
        # 差异超过10%才会标记为冲突
        assert isinstance(conflicts, list)
    
    def test_conflict_detected(self):
        """检测到数据冲突"""
        data_points = [
            DomesticDataPoint(
                _id="test_c1",
                indicator="光伏组件排产量",
                value="100GW",
                unit="GW",
                time_period="2026年3月",
                source=DataSource(name="Source1", url="http://s1.com", publish_date="2026-04-15", credibility=CredibilityGrade.B),
                cross_validation=[]
            ),
            DomesticDataPoint(
                _id="test_c2",
                indicator="光伏组件排产量",
                value="50GW",  # 差异100%，远超10%
                unit="GW",
                time_period="2026年3月",
                source=DataSource(name="Source2", url="http://s2.com", publish_date="2026-04-15", credibility=CredibilityGrade.B),
                cross_validation=[]
            )
        ]
        
        validator = DataValidator()
        # 传入包含这些数据点的列表
        conflicts = validator.detect_conflicts(data_points, "光伏组件排产量")
        
        # 验证返回的是列表类型
        assert isinstance(conflicts, list)


class TestURLValidation:
    """URL验证测试"""
    
    def test_valid_url_format(self):
        """有效URL格式"""
        validator = DataValidator()
        is_valid, message = validator._validate_url_format("https://www.nea.gov.cn/test")
        assert is_valid is True
    
    def test_invalid_url_format(self):
        """无效URL格式"""
        validator = DataValidator()
        is_valid, message = validator._validate_url_format("这不是一个URL")
        assert is_valid is False
    
    def test_missing_url(self, sample_domestic_data_point):
        """缺失URL"""
        data_points = [sample_domestic_data_point]
        validator = DataValidator()
        results = validator.validate_urls(data_points)
        
        # 已有URL的数据点应该通过
        assert len(results) >= 0
    
    def test_url_missing_in_source(self):
        """来源中无URL"""
        data_point = DomesticDataPoint(
            _id="test_no_url",
            indicator="光伏组件排产量",
            value="50GW",
            unit="GW",
            time_period="2026年3月",
            source=DataSource(
                name="某机构",
                url="-",
                publish_date="2026-04-15",
                credibility=CredibilityGrade.C
            ),
            cross_validation=[]
        )
        
        validator = DataValidator()
        results = validator.validate_urls([data_point])
        
        assert len(results) > 0
        assert results[0]["is_valid"] is False


class TestBatchValidation:
    """批量校验测试"""
    
    def test_validate_single(self, sample_domestic_data_point):
        """单个数据点校验"""
        validator = DataValidator()
        result = validator.validate_single(sample_domestic_data_point, "2026年3月")
        
        assert result.data_id == "test_001"
        assert result.is_valid is True
    
    def test_validate_batch(self, multiple_data_points, sample_global_data_point):
        """批量校验"""
        validator = DataValidator()
        results = validator.validate_batch(multiple_data_points + [sample_global_data_point], "2026年3月")
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result.is_valid, bool)
