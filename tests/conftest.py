# -*- coding: utf-8 -*-
"""
pytest配置和共享fixture
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from dataclasses import replace

from data_models import (
    DomesticDataPoint, GlobalDataPoint, DataSource, ValidationResult,
    ValidationIssue, CredibilityGrade
)


@pytest.fixture
def sample_source():
    """示例数据源"""
    return DataSource(
        name="国家能源局",
        url="https://www.nea.gov.cn/test",
        publish_date="2026-04-23",
        credibility=CredibilityGrade.A
    )


@pytest.fixture
def sample_domestic_data_point(sample_source):
    """示例国内数据点"""
    return DomesticDataPoint(
        _id="test_001",
        indicator="光伏电池装机量",
        value="891万kW（8.91GW）",
        unit="万千瓦",
        time_period="2026年3月",
        source=sample_source,
        cross_validation=["数字新能源DNE"],
        is_forecast=False
    )


@pytest.fixture
def sample_forecast_data_point(sample_source):
    """示例预测数据点（未标注）"""
    return DomesticDataPoint(
        _id="test_002",
        indicator="光伏组件排产量",
        value="~47GW",
        unit="GW",
        time_period="2026年3月",
        source=DataSource(
            name="Mysteel",
            url="https://mysteel.net/test",
            publish_date="2026-03-10",
            credibility=CredibilityGrade.B
        ),
        cross_validation=[],
        is_forecast=False  # 未标注为预测值
    )


@pytest.fixture
def sample_global_data_point():
    """示例国际数据点"""
    return GlobalDataPoint(
        _id="test_glo_001",
        indicator="全球光伏新增装机量",
        value="~697",
        unit="GW",
        time_period="2025年",
        source=DataSource(
            name="BNEF",
            url="https://www.bnef.com/test",
            publish_date="2025-03-13",
            credibility=CredibilityGrade.A
        ),
        cross_validation=["IEA PVPS", "Ember智库"],
        is_forecast=True
    )


@pytest.fixture
def sample_validation_result():
    """示例校验结果"""
    return ValidationResult(
        data_id="test_001",
        data_type="domestic",
        is_valid=True
    )


@pytest.fixture
def multiple_data_points(sample_domestic_data_point, sample_forecast_data_point):
    """多个数据点用于冲突检测"""
    # 创建同指标但不同值的数据点
    data_point_1 = replace(sample_domestic_data_point, _id="test_003", value="47GW")
    data_point_2 = replace(sample_forecast_data_point, _id="test_004", value="39.34GW")
    
    return [data_point_1, data_point_2]


@pytest.fixture
def time_inconsistent_data_point():
    """时间不一致的数据点（3月数据在3月10日发布）"""
    return DomesticDataPoint(
        _id="test_time_001",
        indicator="光伏组件排产量",
        value="45GW",
        unit="GW",
        time_period="2026年3月",
        source=DataSource(
            name="Mysteel",
            url="https://mysteel.net/test",
            publish_date="2026-03-10",  # 3月10日发布3月数据
            credibility=CredibilityGrade.B
        ),
        cross_validation=[],
        is_forecast=False
    )
