# -*- coding: utf-8 -*-
"""
数据模型模块 - 定义行业月报系统的核心数据结构

包含 DomesticDataPoint, GlobalDataPoint, CompetitorEvent, IndustryNews,
ValidationResult, CredibilityGrade 等数据类
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class CredibilityGrade(Enum):
    """可信度等级枚举"""
    A = "A"      # 高可信：官方+第三方交叉验证
    B = "B"      # 较可信：权威机构单来源
    C = "C"      # 待验证：行业媒体单来源
    D = "D"      # 存疑：来源不明或数据冲突
    UNKNOWN = "UNKNOWN"  # 未知等级


class DataType(Enum):
    """数据类型枚举"""
    HISTORICAL = "历史数据"      # 实际发生的统计数据
    FORECAST = "预测值"          # 未来预估数据
    ESTIMATED = "估算值"         # 基于部分数据的推算


class DynamicType(Enum):
    """竞争对手动态类型"""
    IPO = "IPO/上市"
    FINANCING = "融资/投资"
    TECH_BREAKTHROUGH = "技术突破"
    PRODUCTION_EXPAND = "产能扩张"
    STRATEGIC_COOP = "战略合作"
    GOVERNANCE = "公司治理"
    FINANCIAL = "财务表现"
    NEW_PRODUCT = "新产品"


class NewsCategory(Enum):
    """行业资讯分类"""
    IPO_FINANCING = "IPO/融资/上市"
    NEW_PRODUCT_TECH = "新产品/技术突破"
    PRODUCTION_EXPAND = "产能扩张/投资"
    STRATEGIC_MERGER = "战略合作/并购"
    RESEARCH_PROGRESS = "科研进展"
    APPLICATION_BREAKTHROUGH = "应用场景突破"
    POLICY_DYNAMIC = "政策动态"
    INDUSTRY_TREND = "行业趋势"


@dataclass
class DataSource:
    """数据来源"""
    name: str                           # 来源名称
    url: str                            # 原文链接
    publish_date: str                   # 发布日期 (YYYY-MM-DD)
    credibility: CredibilityGrade      # 预评级


@dataclass
class DomesticDataPoint:
    """
    国内行业数据点
    
    对应 prompt/01_domestic_data.md 中的数据字段要求
    """
    # 核心字段
    indicator: str                      # 指标名称
    value: str                          # 数据值（含单位）
    unit: str                           # 单位
    time_period: str                    # 数据周期，如 "2026年3月"
    
    # 来源信息
    source: DataSource                  # 主数据来源
    cross_validation: List[str] = field(default_factory=list)  # 交叉验证来源
    
    # 元数据
    is_forecast: bool = False           # 是否为预测值
    forecast_note: Optional[str] = None # 预测值备注
    is_estimated: bool = False          # 是否为估算值
    is_calculated: bool = False         # 是否为推算值（如1-3月累计-1-2月）
    calculation_note: Optional[str] = None  # 推算备注
    
    # 扩展字段
    notes: Optional[str] = None         # 补充说明
    yoy_change: Optional[str] = None    # 同比变化
    mom_change: Optional[str] = None    # 环比变化
    
    # 内部使用
    _id: Optional[str] = None           # 内部ID


@dataclass
class GlobalDataPoint:
    """
    国际/全球行业数据点
    
    对应 prompt/02_global_data.md 中的数据字段要求
    """
    # 核心字段
    indicator: str                      # 指标名称
    value: str                          # 数据值（含单位）
    unit: str                            # 单位
    time_period: str                    # 数据周期，如 "2025年"
    
    # 来源信息
    source: DataSource                  # 主数据来源
    cross_validation: List[str] = field(default_factory=list)  # 交叉验证来源
    
    # 国际数据特有字段
    yoy_change: Optional[str] = None    # 同比变化
    statistical_caliber: Optional[str] = None  # 统计口径说明
    
    # 元数据
    is_forecast: bool = False           # 是否为预测值
    forecast_note: Optional[str] = None # 预测值备注
    geographic_scope: Optional[str] = None  # 地理范围（全球/地区）
    
    # 扩展字段
    notes: Optional[str] = None         # 补充说明
    
    # 内部使用
    _id: Optional[str] = None            # 内部ID


@dataclass
class CompetitorEvent:
    """
    竞争对手动态事件
    
    对应 prompt/03_competitor_dynamics.md 中的数据字段要求
    """
    # 公司信息
    company_name: str                   # 公司名称
    dynamic_type: DynamicType          # 动态类型
    title: str                         # 事件简述
    description: str                   # 详细描述
    event_date: str                    # 事件发生日期 (YYYY-MM-DD)
    source: DataSource                 # 信息来源
    
    # 可选字段
    stock_code: Optional[str] = None    # 股票代码
    cross_validation: List[str] = field(default_factory=list)  # 交叉验证来源
    
    # 扩展字段（用于不同类型事件的特定信息）
    details: Dict[str, Any] = field(default_factory=dict)  # 扩展详情
    
    # 内部使用
    _id: Optional[str] = None          # 内部ID


@dataclass
class IndustryNews:
    """
    行业资讯
    
    对应 prompt/04_industry_news.md 中的数据字段要求
    """
    # 核心字段
    category: NewsCategory              # 资讯类别
    title: str                         # 资讯标题
    date: str                          # 事件发生日期
    description: str                   # 详细内容
    
    # 来源信息
    source: DataSource                 # 信息来源
    cross_validation: List[str] = field(default_factory=list)  # 交叉验证来源
    
    # 技术类资讯特有字段
    technical_indicators: Optional[Dict[str, str]] = None  # 技术指标
    application_scenario: Optional[str] = None              # 应用场景
    
    # 扩展字段
    details: Dict[str, Any] = field(default_factory=dict)  # 扩展详情
    
    # 内部使用
    _id: Optional[str] = None          # 内部ID


@dataclass
class ValidationIssue:
    """校验异常项"""
    issue_type: str                     # 异常类型：time_inconsistency, forecast_unlabeled, conflict, url_invalid
    severity: str                        # 严重程度：error, warning, info
    message: str                         # 异常描述
    details: Optional[Dict[str, Any]] = None  # 详细信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ValidationResult:
    """
    数据校验结果
    
    包含原始数据、校验状态和异常原因
    """
    # 关联的数据
    data_id: str                        # 数据点ID
    data_type: str                       # 数据类型：domestic, global, competitor, news
    
    # 校验状态
    is_valid: bool                       # 是否通过校验
    issues: List[ValidationIssue] = field(default_factory=list)  # 异常列表
    
    # 校验详情
    time_consistency_passed: bool = True        # 时间一致性检查
    forecast_label_correct: bool = True         # 预测值标注正确
    no_conflict: bool = True                    # 无数据冲突
    url_accessible: bool = True                 # URL可访问
    
    # 附加信息
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    validator_version: str = "1.0.0"
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """添加异常项"""
        self.issues.append(issue)
        if issue.severity == "error":
            self.is_valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data_id": self.data_id,
            "data_type": self.data_type,
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "time_consistency_passed": self.time_consistency_passed,
            "forecast_label_correct": self.forecast_label_correct,
            "no_conflict": self.no_conflict,
            "url_accessible": self.url_accessible,
            "validation_timestamp": self.validation_timestamp,
            "validator_version": self.validator_version
        }


@dataclass
class GradingResult:
    """
    可信度评级结果
    
    包含评级等级、评级理由、升降级建议
    """
    # 关联的数据
    data_id: str                        # 数据点ID
    
    # 评级结果
    grade: CredibilityGrade              # 最终评级
    base_grade: CredibilityGrade        # 基础评级（基于来源）
    
    # 评级依据
    grade_reason: str                    # 定级理由
    upgrade_suggestions: List[str] = field(default_factory=list)   # 升级建议
    downgrade_reasons: List[str] = field(default_factory=list)    # 降级原因
    
    # 评级因素
    has_cross_validation: bool = False  # 是否有交叉验证
    validation_sources_count: int = 0    # 交叉验证来源数量
    validation_sources_grade_a: int = 0  # 验证来源中A级数量
    
    # 附加信息
    grading_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    grader_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data_id": self.data_id,
            "grade": self.grade.value if isinstance(self.grade, CredibilityGrade) else self.grade,
            "base_grade": self.base_grade.value if isinstance(self.base_grade, CredibilityGrade) else self.base_grade,
            "grade_reason": self.grade_reason,
            "upgrade_suggestions": self.upgrade_suggestions,
            "downgrade_reasons": self.downgrade_reasons,
            "has_cross_validation": self.has_cross_validation,
            "validation_sources_count": self.validation_sources_count,
            "validation_sources_grade_a": self.validation_sources_grade_a,
            "grading_timestamp": self.grading_timestamp,
            "grader_version": self.grader_version
        }


@dataclass
class GradingStats:
    """批量评级统计"""
    total_count: int = 0                # 总数量
    grade_distribution: Dict[str, int] = field(default_factory=lambda: {"A": 0, "B": 0, "C": 0, "D": 0, "UNKNOWN": 0})
    grade_percentages: Dict[str, float] = field(default_factory=lambda: {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "UNKNOWN": 0.0})
    
    # 验证统计
    validation_pass_count: int = 0      # 校验通过数量
    validation_pass_rate: float = 0.0   # 校验通过率
    
    # 常见问题
    common_issues: Dict[str, int] = field(default_factory=dict)  # 常见异常统计
    common_downgrades: Dict[str, int] = field(default_factory=dict)  # 常见降级原因
    
    def calculate_percentages(self) -> None:
        """计算百分比"""
        if self.total_count > 0:
            for grade in self.grade_distribution:
                self.grade_percentages[grade] = round(
                    self.grade_distribution[grade] / self.total_count * 100, 2
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_count": self.total_count,
            "grade_distribution": self.grade_distribution,
            "grade_percentages": self.grade_percentages,
            "validation_pass_count": self.validation_pass_count,
            "validation_pass_rate": round(self.validation_pass_rate * 100, 2),
            "common_issues": self.common_issues,
            "common_downgrades": self.common_downgrades
        }


@dataclass
class PipelineContext:
    """
    Pipeline执行上下文
    
    用于在阶段间传递状态
    """
    # 输入参数
    industry: str                        # 行业名称
    time_period: str                     # 时间范围
    data_types: List[str]                # 数据类型列表
    
    # 中间结果
    domestic_data: List[DomesticDataPoint] = field(default_factory=list)
    global_data: List[GlobalDataPoint] = field(default_factory=list)
    competitor_events: List[CompetitorEvent] = field(default_factory=list)
    industry_news: List[IndustryNews] = field(default_factory=list)
    
    # 校验结果
    validation_results: List[ValidationResult] = field(default_factory=list)
    
    # 评级结果
    grading_results: List[GradingResult] = field(default_factory=list)
    grading_stats: Optional[GradingStats] = None
    
    # 输出
    report_content: Optional[str] = None  # 最终报告内容
    report_path: Optional[str] = None     # 报告文件路径
    
    # 执行状态
    current_stage: str = "init"          # 当前阶段
    errors: List[str] = field(default_factory=list)  # 错误列表
    stage_results: Dict[str, bool] = field(default_factory=dict)  # 各阶段执行结果
    
    def add_error(self, stage: str, error: str) -> None:
        """添加错误"""
        self.errors.append(f"[{stage}] {error}")
        self.stage_results[stage] = False
    
    def set_stage_success(self, stage: str) -> None:
        """标记阶段成功"""
        self.current_stage = stage
        self.stage_results[stage] = True
    
    def get_all_data_points(self) -> List:
        """获取所有数据点"""
        all_data = []
        all_data.extend([(d._id, d, "domestic") for d in self.domestic_data if d._id])
        all_data.extend([(d._id, d, "global") for d in self.global_data if d._id])
        all_data.extend([(d._id, d, "competitor") for d in self.competitor_events if d._id])
        all_data.extend([(d._id, d, "news") for d in self.industry_news if d._id])
        return all_data
