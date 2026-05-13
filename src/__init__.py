# -*- coding: utf-8 -*-
"""
行业月报自动化工作流 - Python包

提供数据搜集、校验、分级、报告生成的全链路自动化能力
"""

__version__ = "1.0.0"
__author__ = "HanmmJade"

from .data_models import (
    DomesticDataPoint,
    GlobalDataPoint,
    CompetitorEvent,
    IndustryNews,
    ValidationResult,
    ValidationIssue,
    GradingResult,
    GradingStats,
    CredibilityGrade,
    PipelineContext
)

from .data_sources import DataSourceManager, get_source_manager

from .validator import DataValidator

from .grader import CredibilityGrader

from .pipeline import IndustryReportPipeline, run_pipeline, run_demo

from .report_generator import ReportGenerator

__all__ = [
    # 数据模型
    "DomesticDataPoint",
    "GlobalDataPoint",
    "CompetitorEvent",
    "IndustryNews",
    "ValidationResult",
    "ValidationIssue",
    "GradingResult",
    "GradingStats",
    "CredibilityGrade",
    "PipelineContext",
    # 管理器
    "DataSourceManager",
    "get_source_manager",
    "DataValidator",
    "CredibilityGrader",
    # Pipeline
    "IndustryReportPipeline",
    "run_pipeline",
    "run_demo",
    # 报告生成
    "ReportGenerator",
]
