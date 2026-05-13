# -*- coding: utf-8 -*-
"""
Pipeline测试

测试完整pipeline运行、阶段间状态传递、错误处理
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from dataclasses import replace

from data_models import (
    DomesticDataPoint, GlobalDataPoint, DataSource, CredibilityGrade, PipelineContext
)
from pipeline import IndustryReportPipeline


class TestRequirementParsing:
    """需求解析测试"""
    
    def test_parse_industry(self):
        """解析行业"""
        pipeline = IndustryReportPipeline()
        
        result = pipeline.understand_requirement("光伏 2026年3月")
        assert result["industry"] == "光伏"
    
    def test_parse_time_period(self):
        """解析时间周期"""
        pipeline = IndustryReportPipeline()
        
        result = pipeline.understand_requirement("光伏 2026年3月")
        assert "2026" in result["time_period"]
        assert "3" in result["time_period"]
    
    def test_parse_data_types(self):
        """解析数据类型"""
        pipeline = IndustryReportPipeline()
        
        result = pipeline.understand_requirement("光伏 国内数据 竞对动态")
        assert "domestic" in result["data_types"]
        assert "competitor" in result["data_types"]
    
    def test_default_data_types(self):
        """默认数据类型"""
        pipeline = IndustryReportPipeline()
        
        result = pipeline.understand_requirement("光伏 2026年3月")
        # 默认应该包含所有类型
        assert len(result["data_types"]) > 0


class TestPipelineStages:
    """Pipeline阶段测试"""
    
    def test_collect_data_creates_context(self):
        """收集数据阶段创建上下文"""
        pipeline = IndustryReportPipeline()
        requirement = {
            "industry": "光伏",
            "time_period": "2026年3月",
            "data_types": ["domestic"]
        }
        
        context = pipeline.collect_data(requirement)
        
        assert isinstance(context, PipelineContext)
        assert context.industry == "光伏"
        assert context.time_period == "2026年3月"
        assert context.stage_results.get("collect_data") is True
    
    def test_validate_updates_results(self):
        """校验阶段更新结果"""
        pipeline = IndustryReportPipeline()
        
        # 创建带数据的上下文
        context = PipelineContext(
            industry="光伏",
            time_period="2026年3月",
            data_types=["domestic"]
        )
        
        # 添加模拟数据点
        context.domestic_data = [
            DomesticDataPoint(
                _id="test_001",
                indicator="光伏电池装机量",
                value="891万kW",
                unit="万千瓦",
                time_period="2026年3月",
                source=DataSource(
                    name="国家能源局",
                    url="https://www.nea.gov.cn/test",
                    publish_date="2026-04-23",
                    credibility=CredibilityGrade.A
                ),
                cross_validation=["数字新能源DNE"]
            )
        ]
        
        context = pipeline.validate(context)
        
        assert isinstance(context.validation_results, list)
        assert context.stage_results.get("validate") is True
    
    def test_grade_updates_results(self):
        """分级阶段更新结果"""
        pipeline = IndustryReportPipeline()
        
        context = PipelineContext(
            industry="光伏",
            time_period="2026年3月",
            data_types=["domestic"]
        )
        
        # 添加模拟数据点
        context.domestic_data = [
            DomesticDataPoint(
                _id="test_001",
                indicator="光伏电池装机量",
                value="891万kW",
                unit="万千瓦",
                time_period="2026年3月",
                source=DataSource(
                    name="国家能源局",
                    url="https://www.nea.gov.cn/test",
                    publish_date="2026-04-23",
                    credibility=CredibilityGrade.A
                ),
                cross_validation=["数字新能源DNE"]
            )
        ]
        
        context = pipeline.grade(context)
        
        assert isinstance(context.grading_results, list)
        assert context.grading_stats is not None
        assert context.stage_results.get("grade") is True
    
    def test_format_output_generates_report(self):
        """输出阶段生成报告"""
        pipeline = IndustryReportPipeline()
        
        context = PipelineContext(
            industry="光伏",
            time_period="2026年3月",
            data_types=["domestic"]
        )
        
        # 添加模拟数据点
        context.domestic_data = [
            DomesticDataPoint(
                _id="test_001",
                indicator="光伏电池装机量",
                value="891万kW",
                unit="万千瓦",
                time_period="2026年3月",
                source=DataSource(
                    name="国家能源局",
                    url="https://www.nea.gov.cn/test",
                    publish_date="2026-04-23",
                    credibility=CredibilityGrade.A
                ),
                cross_validation=["数字新能源DNE"]
            )
        ]
        
        context = pipeline.grade(context)
        context = pipeline.format_output(context)
        
        assert context.report_content is not None
        assert len(context.report_content) > 0
        assert "行业月报" in context.report_content


class TestPipelineIntegration:
    """Pipeline集成测试"""
    
    def test_full_pipeline_run(self):
        """完整Pipeline运行"""
        pipeline = IndustryReportPipeline()
        
        context = pipeline.run("光伏 2026年3月 国内数据")
        
        assert isinstance(context, PipelineContext)
        assert context.industry == "光伏"
        # 检查上下文中的stage_results
        for stage, success in context.stage_results.items():
            assert success is True
    
    def test_empty_data_handling(self):
        """空数据处理"""
        pipeline = IndustryReportPipeline()
        
        # 不添加任何数据
        context = PipelineContext(
            industry="光伏",
            time_period="2026年3月",
            data_types=["domestic"]
        )
        
        context = pipeline.validate(context)
        context = pipeline.grade(context)
        context = pipeline.format_output(context)
        
        # 应该仍然能生成报告（虽然为空）
        assert context.report_content is not None


class TestPipelineErrors:
    """Pipeline错误处理测试"""
    
    def test_invalid_query_handling(self):
        """无效查询处理"""
        pipeline = IndustryReportPipeline()
        
        # 使用无法解析的查询
        requirement = pipeline.understand_requirement("")
        
        # 应该使用默认值
        assert requirement["industry"] is None  # 无法解析
        assert len(requirement["data_types"]) > 0  # 但有默认类型
    
    def test_context_error_tracking(self):
        """上下文错误追踪"""
        context = PipelineContext(
            industry="光伏",
            time_period="2026年3月",
            data_types=["domestic"]
        )
        
        # 添加错误
        context.add_error("test_stage", "测试错误")
        
        assert len(context.errors) == 1
        assert "test_stage" in context.errors[0]


class TestDemo:
    """演示测试"""
    
    def test_run_demo(self):
        """运行演示"""
        # 注意：这个测试需要example_output.md文件存在
        # 如果文件不存在，会抛出FileNotFoundError
        
        example_path = Path(__file__).parent.parent / "output" / "example_output.md"
        
        if example_path.exists():
            context = IndustryReportPipeline.run_demo()
            
            assert isinstance(context, PipelineContext)
            assert len(context.domestic_data) > 0
            assert context.grading_stats is not None
        else:
            pytest.skip("示例文件不存在")
