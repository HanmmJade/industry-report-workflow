# -*- coding: utf-8 -*-
"""
工作流Pipeline - 串联5个阶段的行业月报生成流程

包含：
- IndustryReportPipeline: 主流程类
- run_demo(): 演示方法
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from data_models import (
    DomesticDataPoint, GlobalDataPoint, CompetitorEvent, IndustryNews,
    DataSource, ValidationResult, GradingResult, GradingStats,
    PipelineContext, CredibilityGrade
)
from data_sources import DataSourceManager
from validator import DataValidator
from grader import CredibilityGrader
from report_generator import ReportGenerator


class IndustryReportPipeline:
    """
    行业月报生成Pipeline
    
    串联5个阶段：
    1. understand_requirement: 解析需求
    2. collect_data: 收集数据
    3. validate: 数据校验
    4. grade: 可信度分级
    5. format_output: 生成报告
    """
    
    def __init__(self):
        """初始化Pipeline"""
        self.source_manager = DataSourceManager()
        self.validator = DataValidator()
        self.grader = CredibilityGrader()
        self.report_generator = ReportGenerator()
        
        # 上下文
        self.context: Optional[PipelineContext] = None
    
    def understand_requirement(self, query: str) -> Dict[str, Any]:
        """
        阶段1：理解需求
        
        解析用户输入，提取行业、时间、数据类型
        
        Args:
            query: 用户查询，如 "光伏 2026年3月 国内数据+竞对动态"
        
        Returns:
            解析后的需求字典
        """
        requirement = {
            "industry": None,
            "time_period": None,
            "data_types": []
        }
        
        # 解析行业
        industries = ["光伏", "锂电", "新能源汽车", "新能源车"]
        for ind in industries:
            if ind in query:
                requirement["industry"] = ind
                break
        
        # 如果没找到，尝试同义词
        if not requirement["industry"]:
            if "太阳能" in query or "PV" in query:
                requirement["industry"] = "光伏"
            elif "电池" in query or "电动车" in query or "EV" in query:
                requirement["industry"] = "锂电"
        
        # 解析时间
        time_patterns = [
            r'(\d{4})年(\d{1,2})月',  # 2026年3月
            r'(\d{4})年',            # 2025年
            r'(\d{4})Q([1-4])',     # 2026Q1
        ]
        for pattern in time_patterns:
            match = re.search(pattern, query)
            if match:
                if "Q" in pattern:
                    requirement["time_period"] = f"{match.group(1)}Q{match.group(2)}"
                else:
                    requirement["time_period"] = match.group(0)
                break
        
        # 解析数据类型
        type_mapping = {
            "国内": ["domestic"],
            "国内数据": ["domestic"],
            "国际": ["global"],
            "国际数据": ["global"],
            "竞对": ["competitor"],
            "竞争对手": ["competitor"],
            "动态": ["competitor"],
            "资讯": ["news"],
            "新闻": ["news"],
            "行业资讯": ["news"]
        }
        
        for keyword, types in type_mapping.items():
            if keyword in query:
                for t in types:
                    if t not in requirement["data_types"]:
                        requirement["data_types"].append(t)
        
        # 如果没指定，默认全部
        if not requirement["data_types"]:
            requirement["data_types"] = ["domestic", "global", "competitor", "news"]
        
        return requirement
    
    def collect_data(self, requirement: Dict[str, Any]) -> PipelineContext:
        """
        阶段2：收集数据
        
        返回模拟数据（实际搜集靠LLM+搜索，这里提供数据标准化接口）
        
        Args:
            requirement: 解析后的需求
        
        Returns:
            PipelineContext，包含收集的数据
        """
        context = PipelineContext(
            industry=requirement["industry"] or "光伏",
            time_period=requirement["time_period"] or datetime.now().strftime("%Y年%m月"),
            data_types=requirement["data_types"]
        )
        
        industry = context.industry
        period = context.time_period
        
        # 收集国内数据
        if "domestic" in context.data_types:
            context.domestic_data = self._collect_domestic_data(industry, period)
        
        # 收集国际数据
        if "global" in context.data_types:
            context.global_data = self._collect_global_data(industry, period)
        
        # 收集竞争对手动态
        if "competitor" in context.data_types:
            context.competitor_events = self._collect_competitor_events(industry, period)
        
        # 收集行业资讯
        if "news" in context.data_types:
            context.industry_news = self._collect_industry_news(industry, period)
        
        context.set_stage_success("collect_data")
        return context
    
    def _collect_domestic_data(self, industry: str, period: str) -> List[DomesticDataPoint]:
        """收集国内数据（模拟）"""
        # 模拟数据，实际使用时应通过LLM搜集
        return []
    
    def _collect_global_data(self, industry: str, period: str) -> List[GlobalDataPoint]:
        """收集国际数据（模拟）"""
        return []
    
    def _collect_competitor_events(self, industry: str, period: str) -> List[CompetitorEvent]:
        """收集竞争对手动态（模拟）"""
        return []
    
    def _collect_industry_news(self, industry: str, period: str) -> List[IndustryNews]:
        """收集行业资讯（模拟）"""
        return []
    
    def validate(self, context: PipelineContext) -> PipelineContext:
        """
        阶段3：数据校验
        
        Args:
            context: Pipeline上下文
        
        Returns:
            更新后的上下文
        """
        all_data = context.get_all_data_points()
        
        if not all_data:
            context.set_stage_success("validate")
            return context
        
        # 批量校验
        data_points = [item[1] for item in all_data]
        validation_results = self.validator.validate_batch(data_points, context.time_period)
        
        context.validation_results = validation_results
        context.set_stage_success("validate")
        
        return context
    
    def grade(self, context: PipelineContext) -> PipelineContext:
        """
        阶段4：可信度分级
        
        Args:
            context: Pipeline上下文
        
        Returns:
            更新后的上下文
        """
        all_data = context.get_all_data_points()
        
        if not all_data:
            context.grading_results = []
            context.grading_stats = GradingStats()
            context.set_stage_success("grade")
            return context
        
        data_points = [item[1] for item in all_data]
        grading_results, stats = self.grader.grade_all(data_points, context.validation_results)
        
        context.grading_results = grading_results
        context.grading_stats = stats
        context.set_stage_success("grade")
        
        return context
    
    def format_output(self, context: PipelineContext) -> PipelineContext:
        """
        阶段5：生成报告
        
        Args:
            context: Pipeline上下文
        
        Returns:
            更新后的上下文
        """
        # 生成Markdown报告
        report_content = self.report_generator.generate_markdown_report(
            context.grading_results,
            context.grading_stats
        )
        
        context.report_content = report_content
        context.set_stage_success("format_output")
        
        # 保存报告
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        context.report_path = str(report_path)
        
        return context
    
    def run(self, query: str) -> PipelineContext:
        """
        执行完整Pipeline
        
        Args:
            query: 用户查询
        
        Returns:
            PipelineContext
        """
        try:
            # 阶段1：理解需求
            requirement = self.understand_requirement(query)
            
            # 阶段2：收集数据
            context = self.collect_data(requirement)
            
            # 阶段3：校验
            context = self.validate(context)
            
            # 阶段4：分级
            context = self.grade(context)
            
            # 阶段5：输出
            context = self.format_output(context)
            
            return context
            
        except Exception as e:
            if self.context:
                self.context.add_error("pipeline", str(e))
            raise
    
    def run_with_data(self, data: Dict[str, Any], time_period: str) -> PipelineContext:
        """
        使用外部数据运行Pipeline
        
        Args:
            data: 外部数据字典
            time_period: 数据周期
        
        Returns:
            PipelineContext
        """
        context = PipelineContext(
            industry=data.get("industry", "光伏"),
            time_period=time_period,
            data_types=["domestic", "global", "competitor", "news"]
        )
        
        # 解析外部数据
        # TODO: 实现外部数据解析逻辑
        
        # 执行校验和分级
        context = self.validate(context)
        context = self.grade(context)
        context = self.format_output(context)
        
        return context
    
    @staticmethod
    def run_demo() -> PipelineContext:
        """
        运行演示流程
        
        使用output/example_output.md中的真实数据做演示
        
        Returns:
            PipelineContext
        """
        # 加载示例数据
        example_path = Path(__file__).parent.parent / "output" / "example_output.md"
        
        if not example_path.exists():
            raise FileNotFoundError(f"示例文件不存在: {example_path}")
        
        with open(example_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析示例数据创建模拟数据点
        pipeline = IndustryReportPipeline()
        context = PipelineContext(
            industry="光伏",
            time_period="2026年3月",
            data_types=["domestic", "global", "competitor", "news"]
        )
        
        # 创建模拟国内数据点
        domestic_data = [
            DomesticDataPoint(
                _id="dom_001",
                indicator="光伏电池装机量",
                value="891万kW（8.91GW）",
                unit="万千瓦",
                time_period="2026年3月",
                source=DataSource(
                    name="国家能源局",
                    url="https://www.nea.gov.cn/20260427/4b751e59b0d7463a95f74096fed83e14/c.html",
                    publish_date="2026-04-23",
                    credibility=CredibilityGrade.A
                ),
                cross_validation=["数字新能源DNE", "银河证券研报"],
                is_forecast=False,
                notes="推算值：1-3月累计4139万kW减去1-2月累计3248万kW得出"
            ),
            DomesticDataPoint(
                _id="dom_002",
                indicator="光伏组件排产量",
                value="~47GW",
                unit="GW",
                time_period="2026年3月",
                source=DataSource(
                    name="InfoLink",
                    url="https://xueqiu.com/2316661451/384044556",
                    publish_date="2026-04-15",
                    credibility=CredibilityGrade.B
                ),
                cross_validation=["Mysteel", "索比光伏网"],
                is_forecast=False,
                notes="退税窗口驱动3月增产"
            ),
            DomesticDataPoint(
                _id="dom_003",
                indicator="动力电池装车量",
                value="56.5",
                unit="GWh",
                time_period="2026年3月",
                source=DataSource(
                    name="中国汽车动力电池产业创新联盟",
                    url="https://www.cbcie.com/cobalt/news/content/2158712.html",
                    publish_date="2026-04-16",
                    credibility=CredibilityGrade.A
                ),
                cross_validation=["东方财富网", "新浪微博"],
                is_forecast=False,
                notes="环比+114.9%，同比-0.1%"
            )
        ]
        context.domestic_data = domestic_data
        
        # 创建模拟国际数据点
        global_data = [
            GlobalDataPoint(
                _id="glo_001",
                indicator="全球光伏新增装机量",
                value="~697",
                unit="GW",
                time_period="2025年",
                source=DataSource(
                    name="BNEF",
                    url="https://www.pv-magazine.com/2025/03/13/bloombergnef-expects-up-to-700-gw-of-new-solar-in-2025/",
                    publish_date="2025-03-13",
                    credibility=CredibilityGrade.A
                ),
                cross_validation=["IEA PVPS", "Ember智库"],
                yoy_change="+16%",
                is_forecast=True,
                notes="BNEF预测2025年装机量，IEA PVPS报告608-698GW"
            )
        ]
        context.global_data = global_data
        
        # 创建模拟竞争对手动态
        competitor_events = [
            CompetitorEvent(
                _id="comp_001",
                company_name="某激光设备公司",
                stock_code="300776.SZ",
                dynamic_type="IPO",
                title="递表港交所",
                description="正式向港交所主板递交上市申请书，由中金公司担任独家保荐人",
                event_date="2026-04-20",
                source=DataSource(
                    name="财联社",
                    url="https://finance.sina.com.cn/cj/2026-04-21/doc-inhvhezh4966000.shtml",
                    publish_date="2026-04-21",
                    credibility=CredibilityGrade.B
                ),
                cross_validation=["港交所官网", "格隆汇"]
            )
        ]
        context.competitor_events = competitor_events
        
        # 创建模拟行业资讯
        industry_news = [
            IndustryNews(
                _id="news_001",
                category="NEWS",
                title="浙江大学发布万通道3D纳米激光直写光刻机",
                date="2026-04-10",
                description="成功研发万通道3D纳米激光直写光刻机，加工精度达亚30纳米",
                source=DataSource(
                    name="中国新闻网",
                    url="http://www.news.zju.edu.cn/2026/0422/c5217a3155014/pagem.htm",
                    publish_date="2026-04-10",
                    credibility=CredibilityGrade.A
                ),
                cross_validation=["浙江大学官网"]
            )
        ]
        context.industry_news = industry_news
        
        # 执行校验
        context = pipeline.validate(context)
        
        # 执行分级
        context = pipeline.grade(context)
        
        # 生成报告
        context = pipeline.format_output(context)
        
        return context


# 便捷函数
def run_pipeline(query: str) -> PipelineContext:
    """运行Pipeline"""
    return IndustryReportPipeline().run(query)


def run_demo() -> PipelineContext:
    """运行演示"""
    return IndustryReportPipeline.run_demo()
