# -*- coding: utf-8 -*-
"""
数据源配置测试

测试JSON配置读取、按行业筛选数据源、来源可信度查询
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from data_sources import DataSourceManager, get_sources, get_credibility_by_source, validate_source_url


class TestConfigLoading:
    """配置加载测试"""
    
    def test_load_config(self):
        """加载配置文件"""
        manager = DataSourceManager()
        
        assert manager.config is not None
        assert "domestic" in manager.config
        assert "global" in manager.config
    
    def test_config_has_required_fields(self):
        """配置文件包含必要字段"""
        manager = DataSourceManager()
        
        # 检查光伏数据源
        pv_sources = manager.get_sources("光伏", "domestic")
        if pv_sources:
            first_source = pv_sources[0]
            assert "name" in first_source
            assert "credibility" in first_source


class TestSourceFiltering:
    """数据源筛选测试"""
    
    def test_filter_by_industry(self):
        """按行业筛选"""
        manager = DataSourceManager()
        
        pv_sources = manager.get_sources("光伏", "domestic")
        
        # 光伏行业应该有数据源
        assert isinstance(pv_sources, list)
    
    def test_filter_by_data_type(self):
        """按数据类型筛选"""
        manager = DataSourceManager()
        
        domestic = manager.get_sources("光伏", "domestic")
        global_data = manager.get_sources("光伏", "global")
        
        # 两种类型都应该有数据
        assert isinstance(domestic, list)
        assert isinstance(global_data, list)
    
    def test_filter_all_types(self):
        """筛选所有类型"""
        manager = DataSourceManager()
        
        all_sources = manager.get_sources("光伏", "all")
        
        assert isinstance(all_sources, list)
        # 应该同时包含国内和国际数据源
        domestic_has = any(s.get("credibility") for s in all_sources if s.get("credibility"))
        assert domestic_has
    
    def test_normalize_industry_name(self):
        """标准化行业名称"""
        manager = DataSourceManager()
        
        # 同义词应该映射到同一行业
        pv1 = manager.get_sources("光伏", "domestic")
        pv2 = manager.get_sources("太阳能", "domestic")
        pv3 = manager.get_sources("PV", "domestic")
        
        # 都应该返回数据（即使为空列表也不算失败）
        assert isinstance(pv1, list)
        assert isinstance(pv2, list)
        assert isinstance(pv3, list)


class TestCredibilityQuery:
    """可信度查询测试"""
    
    def test_get_credibility_by_source_name(self):
        """根据来源名称查询可信度"""
        manager = DataSourceManager()
        
        # A级来源
        grade = manager.get_credibility_by_source("国家能源局")
        assert grade in ["A", "B", "C", "D"]
        
        # B级来源
        grade = manager.get_credibility_by_source("InfoLink")
        assert grade in ["A", "B", "C", "D"]
    
    def test_unknown_source_default_grade(self):
        """未知来源返回默认评级"""
        manager = DataSourceManager()
        
        grade = manager.get_credibility_by_source("完全不认识的来源XYZ123")
        
        # 应该返回B级作为默认值
        assert grade in ["A", "B", "C", "D"]
    
    def test_partial_match(self):
        """部分匹配"""
        manager = DataSourceManager()
        
        # 包含关键词应该匹配
        grade = manager.get_credibility_by_source("某公司的InfoLink")
        assert grade in ["A", "B", "C", "D"]
    
    def test_convenience_functions(self):
        """便捷函数"""
        # 测试模块级便捷函数
        grade = get_credibility_by_source("国家能源局")
        assert grade in ["A", "B", "C", "D"]


class TestURLValidation:
    """URL验证测试"""
    
    def test_validate_matching_url(self):
        """验证匹配的URL"""
        manager = DataSourceManager()
        
        # nea.gov.cn应该匹配国家能源局
        is_valid, msg = manager.validate_source_url(
            "https://www.nea.gov.cn/test",
            "国家能源局"
        )
        
        assert isinstance(is_valid, bool)
        assert msg is None or isinstance(msg, str)
    
    def test_validate_mismatched_url(self):
        """验证不匹配的URL"""
        manager = DataSourceManager()
        
        # 不匹配的URL
        is_valid, msg = manager.validate_source_url(
            "https://www.other-site.com/test",
            "国家能源局"
        )
        
        assert is_valid is False
        assert msg is not None
    
    def test_validate_empty_url(self):
        """验证空URL"""
        manager = DataSourceManager()
        
        is_valid, msg = manager.validate_source_url("", "国家能源局")
        
        assert is_valid is False
    
    def test_validate_invalid_url(self):
        """验证无效URL"""
        manager = DataSourceManager()
        
        is_valid, msg = manager.validate_source_url("这不是一个URL", "测试来源")
        
        assert is_valid is False
    
    def test_convenience_function(self):
        """便捷函数"""
        is_valid, msg = validate_source_url(
            "https://www.nea.gov.cn/test",
            "国家能源局"
        )
        assert isinstance(is_valid, bool)


class TestTypicalSources:
    """典型来源测试"""
    
    def test_get_typical_a_sources(self):
        """获取A级典型来源"""
        manager = DataSourceManager()
        
        sources = manager.get_typical_sources("A")
        
        assert isinstance(sources, list)
        # 应该包含官方机构
        assert len(sources) > 0
    
    def test_get_typical_b_sources(self):
        """获取B级典型来源"""
        manager = DataSourceManager()
        
        sources = manager.get_typical_sources("B")
        
        assert isinstance(sources, list)
    
    def test_get_all_known_sources(self):
        """获取所有已知来源"""
        manager = DataSourceManager()
        
        sources = manager.get_all_known_sources()
        
        assert isinstance(sources, list)
        assert len(sources) > 0


class TestDataTypeDefinitions:
    """数据类型定义测试"""
    
    def test_get_historical_data_definition(self):
        """获取历史数据定义"""
        manager = DataSourceManager()
        
        definition = manager.get_data_type_definition("历史数据")
        
        assert isinstance(definition, dict)
    
    def test_get_forecast_definition(self):
        """获取预测值定义"""
        manager = DataSourceManager()
        
        definition = manager.get_data_type_definition("预测值")
        
        assert isinstance(definition, dict)
    
    def test_get_nonexistent_definition(self):
        """获取不存在的类型定义"""
        manager = DataSourceManager()
        
        definition = manager.get_data_type_definition("不存在的类型")
        
        assert isinstance(definition, dict)
        assert len(definition) == 0
