# -*- coding: utf-8 -*-
"""
数据搜集模块测试

测试 SearchCollector 类的各项功能：
- 关键词生成逻辑
- 模拟数据fallback
- 数据标准化输出
- 无效输入处理
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from datetime import datetime

from collector import (
    SearchCollector, CollectResult, CollectMode,
    create_collector
)
from data_models import (
    DomesticDataPoint, GlobalDataPoint, CompetitorEvent, IndustryNews,
    DataSource, CredibilityGrade
)


class TestKeywordGeneration:
    """测试关键词生成逻辑"""
    
    def test_generate_domestic_keywords(self):
        """测试国内数据关键词生成"""
        collector = SearchCollector()
        keywords = collector._generate_search_keywords("光伏", "2026年3月", "domestic")
        
        assert len(keywords) > 0
        # 检查关键词包含行业和周期信息
        for kw in keywords[:3]:
            assert "光伏" in kw or "太阳能" in kw
            assert "2026" in kw or "3月" in kw
    
    def test_generate_global_keywords(self):
        """测试国际数据关键词生成"""
        collector = SearchCollector()
        keywords = collector._generate_search_keywords("光伏", "2026年3月", "global")
        
        assert len(keywords) > 0
        # 检查关键词包含global和国际来源
        for kw in keywords[:3]:
            assert "global" in kw.lower() or "BNEF" in kw or "IEA" in kw
    
    def test_generate_competitor_keywords(self):
        """测试竞对动态关键词生成"""
        collector = SearchCollector()
        keywords = collector._generate_search_keywords("光伏", "2026年3月", "competitor")
        
        assert len(keywords) > 0
        # 检查包含公司名称
        companies = ["宁德时代", "比亚迪", "隆基绿能", "通威股份", "阳光电源"]
        has_company = any(any(c in kw for c in companies) for kw in keywords)
        assert has_company
    
    def test_generate_news_keywords(self):
        """测试行业资讯关键词生成"""
        collector = SearchCollector()
        keywords = collector._generate_search_keywords("光伏", "2026年3月", "news")
        
        assert len(keywords) > 0
        # 检查包含行业和资讯类型
        for kw in keywords[:3]:
            assert "光伏" in kw or "太阳能" in kw
    
    def test_keyword_limit(self):
        """测试关键词数量限制"""
        collector = SearchCollector()
        keywords = collector._generate_search_keywords("光伏", "2026年3月", "domestic")
        
        # 最多返回5个关键词
        assert len(keywords) <= 5


class TestMockDataFallback:
    """测试模拟数据fallback机制"""
    
    def test_demo_mode_without_api_key(self):
        """测试无API key时使用演示模式"""
        collector = SearchCollector(api_key=None, use_demo_fallback=True)
        
        assert collector.mode == CollectMode.DEMO
        assert collector.api_key is None
    
    def test_live_mode_with_api_key(self):
        """测试有API key时使用联网模式"""
        collector = SearchCollector(api_key="test_key_123", use_demo_fallback=True)
        
        assert collector.mode == CollectMode.LIVE
        assert collector.api_key == "test_key_123"
    
    def test_collect_domestic_returns_mock_data(self):
        """测试国内数据搜集返回模拟数据"""
        collector = SearchCollector(use_demo_fallback=True)
        result = collector.collect_domestic_data("光伏", "2026年3月")
        
        assert result.success is True
        assert len(result.data) > 0
        assert result.mode == CollectMode.DEMO
        assert "演示数据" in (result.error_msg or "")
    
    def test_collect_global_returns_mock_data(self):
        """测试国际数据搜集返回模拟数据"""
        collector = SearchCollector(use_demo_fallback=True)
        result = collector.collect_global_data("光伏", "2026年3月")
        
        assert result.success is True
        assert len(result.data) > 0
        assert result.mode == CollectMode.DEMO
    
    def test_collect_competitor_returns_mock_data(self):
        """测试竞对动态搜集返回模拟数据"""
        collector = SearchCollector(use_demo_fallback=True)
        result = collector.collect_competitor_dynamics("光伏", "2026年3月")
        
        assert result.success is True
        assert len(result.data) > 0
        assert result.mode == CollectMode.DEMO
    
    def test_collect_news_returns_mock_data(self):
        """测试行业资讯搜集返回模拟数据"""
        collector = SearchCollector(use_demo_fallback=True)
        result = collector.collect_industry_news("光伏", "2026年3月")
        
        assert result.success is True
        assert len(result.data) > 0
        assert result.mode == CollectMode.DEMO


class TestDataStandardization:
    """测试数据标准化输出"""
    
    def test_domestic_data_structure(self):
        """测试国内数据类型结构"""
        collector = SearchCollector()
        result = collector.collect_domestic_data("光伏", "2026年3月")
        
        assert isinstance(result, CollectResult)
        assert isinstance(result.data, list)
        
        if result.data:
            item = result.data[0]
            assert isinstance(item, DomesticDataPoint)
            # 检查必要字段
            assert hasattr(item, 'indicator')
            assert hasattr(item, 'value')
            assert hasattr(item, 'unit')
            assert hasattr(item, 'time_period')
            assert hasattr(item, 'source')
    
    def test_global_data_structure(self):
        """测试国际数据类型结构"""
        collector = SearchCollector()
        result = collector.collect_global_data("光伏", "2026年3月")
        
        if result.data:
            item = result.data[0]
            assert isinstance(item, GlobalDataPoint)
            assert hasattr(item, 'indicator')
            assert hasattr(item, 'geographic_scope')  # 使用正确的字段名
    
    def test_competitor_data_structure(self):
        """测试竞对动态数据类型结构"""
        collector = SearchCollector()
        result = collector.collect_competitor_dynamics("光伏", "2026年3月")
        
        if result.data:
            item = result.data[0]
            assert isinstance(item, CompetitorEvent)
            assert hasattr(item, 'company_name')
            assert hasattr(item, 'dynamic_type')  # 使用正确的字段名
    
    def test_news_data_structure(self):
        """测试行业资讯数据类型结构"""
        collector = SearchCollector()
        result = collector.collect_industry_news("光伏", "2026年3月")
        
        if result.data:
            item = result.data[0]
            assert isinstance(item, IndustryNews)
            assert hasattr(item, 'title')
            assert hasattr(item, 'category')
    
    def test_datasource_has_credibility(self):
        """测试数据源包含可信度评级"""
        collector = SearchCollector()
        result = collector.collect_domestic_data("光伏", "2026年3月")
        
        if result.data:
            item = result.data[0]
            assert hasattr(item.source, 'credibility')
            assert isinstance(item.source.credibility, CredibilityGrade)


class TestInvalidInputHandling:
    """测试无效输入处理"""
    
    def test_unknown_industry_uses_default(self):
        """测试未知行业使用默认处理"""
        collector = SearchCollector()
        # 应该不会抛出异常，而是使用通用处理
        result = collector.collect_domestic_data("未知行业XYZ", "2026年3月")
        
        assert isinstance(result, CollectResult)
        assert result.success is True
    
    def test_empty_period_uses_current(self):
        """测试空周期使用当前时间"""
        collector = SearchCollector()
        result = collector.collect_domestic_data("光伏", "")
        
        assert isinstance(result, CollectResult)
        assert result.success is True
    
    def test_invalid_period_format(self):
        """测试无效周期格式"""
        collector = SearchCollector()
        result = collector.collect_domestic_data("光伏", "invalid_period")
        
        assert isinstance(result, CollectResult)
        # 应该仍能返回数据（使用通用处理）
        assert result.success is True
    
    def test_collect_all_with_empty_types(self):
        """测试搜集所有类型时处理空类型"""
        collector = SearchCollector()
        result = collector.collect_all("光伏", "2026年3月", [])
        
        assert isinstance(result, dict)
        # 空类型应该不返回任何结果
        assert len(result) == 0


class TestConvenienceFunction:
    """测试便捷函数"""
    
    def test_create_collector_without_key(self):
        """测试创建无API key的搜集器"""
        collector = create_collector()
        
        assert isinstance(collector, SearchCollector)
        assert collector.api_key is None
        assert collector.use_demo_fallback is True
    
    def test_create_collector_with_key(self):
        """测试创建有API key的搜集器"""
        collector = create_collector(api_key="test_key")
        
        assert isinstance(collector, SearchCollector)
        assert collector.api_key == "test_key"


class TestIndustryMapping:
    """测试行业映射"""
    
    def test_lithium_industry_keywords(self):
        """测试锂电行业关键词"""
        collector = SearchCollector()
        keywords = collector._generate_search_keywords("锂电", "2026年3月", "domestic")
        
        assert len(keywords) > 0
        # 应该包含锂电相关指标
        all_kw = " ".join(keywords)
        assert "锂电" in all_kw or "电池" in all_kw
    
    def test_ev_industry_keywords(self):
        """测试新能源汽车行业关键词"""
        collector = SearchCollector()
        keywords = collector._generate_search_keywords("新能源汽车", "2026年3月", "domestic")
        
        assert len(keywords) > 0


class TestCollectResult:
    """测试CollectResult数据类"""
    
    def test_collect_result_success(self):
        """测试成功结果"""
        result = CollectResult(
            success=True,
            data=[],
            mode=CollectMode.DEMO
        )
        
        assert result.success is True
        assert result.error_msg is None
        assert result.api_key_used is False
    
    def test_collect_result_failure(self):
        """测试失败结果"""
        result = CollectResult(
            success=False,
            data=[],
            mode=CollectMode.LIVE,
            error_msg="API调用失败",
            api_key_used=True
        )
        
        assert result.success is False
        assert result.error_msg == "API调用失败"
        assert result.api_key_used is True


class TestSourceConfigLoading:
    """测试数据源配置加载"""
    
    def test_load_source_config(self):
        """测试加载数据源配置"""
        collector = SearchCollector()
        
        # 配置应该已加载
        assert hasattr(collector, 'source_config')
        assert isinstance(collector.source_config, dict)
    
    def test_collector_handles_missing_config(self):
        """测试处理缺失配置文件"""
        # 创建一个没有配置文件的搜集器
        collector = SearchCollector()
        
        # 应该使用空配置而非崩溃
        assert collector.source_config is not None
