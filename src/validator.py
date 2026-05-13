# -*- coding: utf-8 -*-
"""
数据校验引擎 - 执行数据质量检查

包含：
- check_time_consistency: 时间一致性检查
- check_forecast_flag: 预测值检测
- detect_conflicts: 数据冲突检测
- validate_urls: URL可访问性验证
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import asdict

# 条件导入requests（可选，用于URL验证）
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from data_models import (
    DomesticDataPoint, GlobalDataPoint, CompetitorEvent, IndustryNews,
    ValidationResult, ValidationIssue, CredibilityGrade
)
from data_sources import get_source_manager


class DataValidator:
    """
    数据校验引擎
    
    执行时间一致性检查、预测值标注检测、数据冲突检测、URL验证
    """
    
    # 预测值关键词（中文）
    FORECAST_KEYWORDS_CN = [
        "预计", "预期", "预测", "估计", "展望",
        "将达", "将至", "将为", "有望", "约"
    ]
    
    # 预测值关键词（英文）
    FORECAST_KEYWORDS_EN = [
        "forecast", "prediction", "expected", "outlook",
        "prospect", "estimate", "projected"
    ]
    
    # 实际值关键词
    ACTUAL_KEYWORDS = [
        "实际", "统计", "累计", "实际值", "actual",
        "recorded", "reported", "正式发布", "数据显示"
    ]
    
    def __init__(self, rules_path: Optional[str] = None):
        """
        初始化校验引擎
        
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
        
        # 已检测的冲突（用于跨数据点检测）
        self._detected_conflicts: Dict[str, List[Dict]] = {}
    
    def _load_rules(self) -> Dict[str, Any]:
        """加载规则配置"""
        if not self.rules_path.exists():
            # 返回默认规则
            return self._get_default_rules()
        
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """获取默认规则"""
        return {
            "time_consistency_rules": {
                "monthly_data": {"description": "月度数据", "rule": "发布日期需在月末之后"},
                "quarterly_data": {"description": "季度数据", "rule": "发布日期需在季度末之后"},
                "yearly_data": {"description": "年度数据", "rule": "发布日期需在年度之后"}
            },
            "forecast_detection_rules": {
                "forecast_keywords": self.FORECAST_KEYWORDS_CN + self.FORECAST_KEYWORDS_EN,
                "actual_keywords": self.ACTUAL_KEYWORDS
            },
            "conflict_detection_rules": {
                "numerical_conflict": {"threshold_percent": 10}
            }
        }
    
    def check_time_consistency(self, data_point: Any, target_period: str) -> Tuple[bool, Optional[str]]:
        """
        检查时间一致性
        
        规则：数据的发布时间必须在数据周期结束之后
        
        Args:
            data_point: 数据点对象
            target_period: 目标数据周期，如 "2026年3月"
        
        Returns:
            (是否一致, 异常信息)
        """
        # 解析目标周期
        period_info = self._parse_time_period(target_period)
        if not period_info:
            return True, None  # 无法解析，跳过检查
        
        period_start, period_end = period_info
        
        # 获取发布日期
        publish_date_str = getattr(data_point, 'source', None)
        if publish_date_str and hasattr(publish_date_str, 'publish_date'):
            publish_date_str = publish_date_str.publish_date
        elif isinstance(publish_date_str, dict):
            publish_date_str = publish_date_str.get('publish_date')
        
        if not publish_date_str or publish_date_str in ["-", "待查", "未知"]:
            return False, "⚠️发布时间待查，无法判断时间一致性"
        
        # 解析发布日期
        publish_date = self._parse_date(publish_date_str)
        if not publish_date:
            return True, None  # 无法解析日期，跳过
        
        # 检查：发布日期必须在周期结束后
        if publish_date <= period_end:
            # 如果数据明确标注为预测值，也允许
            if getattr(data_point, 'is_forecast', False):
                return True, None
            
            return False, f"⚠️时间异常：{publish_date_str}发布的{target_period}数据，实际数据应于{period_end.strftime('%Y-%m-%d')}之后发布"
        
        return True, None
    
    def _parse_time_period(self, period_str: str) -> Optional[Tuple[datetime, datetime]]:
        """
        解析时间周期字符串
        
        Args:
            period_str: 时间周期，如 "2026年3月"、"2025年"、"2026Q1"
        
        Returns:
            (周期开始, 周期结束) 或 None
        """
        # 年月格式：2026年3月
        match = re.match(r'(\d{4})年(\d{1,2})月', period_str)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            period_start = datetime(year, month, 1)
            # 月末
            if month == 12:
                period_end = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = datetime(year, month + 1, 1) - timedelta(days=1)
            return period_start, period_end
        
        # 年份格式：2025年
        match = re.match(r'(\d{4})年', period_str)
        if match:
            year = int(match.group(1))
            period_start = datetime(year, 1, 1)
            period_end = datetime(year, 12, 31)
            return period_start, period_end
        
        # 季度格式：2026Q1
        match = re.match(r'(\d{4})Q([1-4])', period_str)
        if match:
            year, quarter = int(match.group(1)), int(match.group(2))
            quarter_starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
            quarter_ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
            s_month, s_day = quarter_starts[quarter]
            e_month, e_day = quarter_ends[quarter]
            period_start = datetime(year, s_month, s_day)
            period_end = datetime(year, e_month, e_day)
            return period_start, period_end
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
        
        Returns:
            datetime对象或None
        """
        formats = [
            "%Y-%m-%d",
            "%Y年%m月%d日",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%Y-%m",
            "%Y年%m月"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def check_forecast_flag(self, data_point: Any, value: str, notes: str = "") -> Tuple[bool, Optional[str]]:
        """
        检测是否为预测值，并检查标注是否正确
        
        Args:
            data_point: 数据点对象
            value: 数据值字符串
            notes: 备注字段
        
        Returns:
            (标注是否正确, 异常信息)
        """
        # 已经是预测值标注
        if getattr(data_point, 'is_forecast', False):
            return True, None
        
        # 检查值中是否包含预测关键词
        value_lower = value.lower() if value else ""
        notes_combined = (notes or "").lower()
        
        has_forecast_keyword = False
        for keyword in self.FORECAST_KEYWORDS_CN + self.FORECAST_KEYWORDS_EN:
            if keyword.lower() in value_lower or keyword.lower() in notes_combined:
                has_forecast_keyword = True
                break
        
        # 检查是否包含实际值关键词
        has_actual_keyword = False
        for keyword in self.ACTUAL_KEYWORDS:
            if keyword.lower() in notes_combined:
                has_actual_keyword = True
                break
        
        # 基于日期判断
        source = getattr(data_point, 'source', None)
        if source and hasattr(source, 'publish_date'):
            publish_date_str = source.publish_date
            period = getattr(data_point, 'time_period', "")
            if period:
                period_info = self._parse_time_period(period)
                if period_info:
                    _, period_end = period_info
                    publish_date = self._parse_date(publish_date_str)
                    if publish_date and publish_date <= period_end:
                        # 发布日在周期结束前，很可能是预测
                        if not has_forecast_keyword and not has_actual_keyword:
                            return False, f"⚠️强制标注预测值：发布日期{publish_date_str}在{period}结束前，且未标注预测"
        
        # 如果是预测值关键词但未标注
        if has_forecast_keyword and not has_actual_keyword:
            return False, "⚠️未标注为预测值"
        
        # 如果有明显预测特征（~、约等）但未标注
        if re.search(r'[~≈≈]', value) and not has_actual_keyword:
            if "GW" in value or "GWh" in value or "万辆" in value:
                return False, "⚠️数值含预测特征符（~），建议明确标注"
        
        return True, None
    
    def detect_conflicts(self, data_points: List[Any], indicator: str) -> List[Dict[str, Any]]:
        """
        检测同一指标的多源数据冲突
        
        Args:
            data_points: 数据点列表
            indicator: 指标名称
        
        Returns:
            冲突信息列表
        """
        conflicts = []
        
        # 筛选同指标数据点
        same_indicator = [dp for dp in data_points 
                         if getattr(dp, 'indicator', '') == indicator or 
                         (hasattr(dp, 'title') and indicator in getattr(dp, 'title', ''))]
        
        if len(same_indicator) < 2:
            return conflicts
        
        # 提取数值进行对比
        values = []
        for dp in same_indicator:
            value_str = getattr(dp, 'value', '')
            # 尝试提取数值
            nums = re.findall(r'[\d.]+', value_str)
            if nums:
                try:
                    value = float(nums[0])
                    values.append({
                        'source': getattr(dp, 'source', None),
                        'value': value,
                        'raw_value': value_str,
                        'data_point': dp
                    })
                except ValueError:
                    continue
        
        if len(values) < 2:
            return conflicts
        
        # 检测数值差异
        threshold = self.rules.get("conflict_detection_rules", {}).get("numerical_conflict", {}).get("threshold_percent", 10)
        
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                v1, v2 = values[i]['value'], values[j]['value']
                if v1 == 0 or v2 == 0:
                    continue
                
                diff_percent = abs(v1 - v2) / max(v1, v2) * 100
                
                if diff_percent > threshold:
                    source1 = values[i]['source']
                    source2 = values[j]['source']
                    source1_name = source1.name if source1 and hasattr(source1, 'name') else str(source1)
                    source2_name = source2.name if source2 and hasattr(source2, 'name') else str(source2)
                    
                    conflicts.append({
                        'indicator': indicator,
                        'source1': source1_name,
                        'value1': values[i]['raw_value'],
                        'source2': source2_name,
                        'value2': values[j]['raw_value'],
                        'diff_percent': round(diff_percent, 2),
                        'threshold': threshold,
                        'severity': 'error' if diff_percent > 20 else 'warning'
                    })
        
        return conflicts
    
    def validate_urls(self, data_points: List[Any]) -> List[Dict[str, Any]]:
        """
        检查URL格式和可访问性
        
        Args:
            data_points: 数据点列表
        
        Returns:
            URL验证结果列表
        """
        results = []
        
        for dp in data_points:
            source = getattr(dp, 'source', None)
            if not source:
                continue
            
            url = source.url if hasattr(source, 'url') else source.get('url', '')
            
            if not url or url in ["-", "⚠️暂未找到", "待查"]:
                results.append({
                    'data_id': getattr(dp, '_id', 'unknown'),
                    'source': getattr(source, 'name', 'unknown'),
                    'url': url,
                    'is_valid': False,
                    'reason': 'URL缺失'
                })
                continue
            
            # 格式验证
            url_valid, format_msg = self._validate_url_format(url)
            
            if not url_valid:
                results.append({
                    'data_id': getattr(dp, '_id', 'unknown'),
                    'source': getattr(source, 'name', 'unknown'),
                    'url': url,
                    'is_valid': False,
                    'reason': format_msg
                })
                continue
            
            # 可访问性验证（可选，需要requests库）
            if HAS_REQUESTS:
                accessible, access_msg = self._check_url_accessible(url)
                results.append({
                    'data_id': getattr(dp, '_id', 'unknown'),
                    'source': getattr(source, 'name', 'unknown'),
                    'url': url,
                    'is_valid': accessible,
                    'reason': access_msg
                })
            else:
                results.append({
                    'data_id': getattr(dp, '_id', 'unknown'),
                    'source': getattr(source, 'name', 'unknown'),
                    'url': url,
                    'is_valid': True,
                    'reason': '格式正确（需安装requests库进行可访问性检查）'
                })
        
        return results
    
    def _validate_url_format(self, url: str) -> Tuple[bool, str]:
        """验证URL格式"""
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if url_pattern.match(url):
            return True, "格式正确"
        return False, "URL格式无效"
    
    def _check_url_accessible(self, url: str, timeout: int = 5) -> Tuple[bool, str]:
        """
        检查URL是否可访问
        
        Args:
            url: URL地址
            timeout: 超时时间（秒）
        
        Returns:
            (是否可访问, 状态信息)
        """
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return True, "✅可访问"
            elif response.status_code == 403:
                return True, "🔐需登录"
            elif response.status_code == 404:
                return False, "❌链接失效(404)"
            else:
                return True, f"⚠️状态码{response.status_code}"
        except requests.exceptions.Timeout:
            return False, f"❌超时({timeout}s)"
        except requests.exceptions.ConnectionError:
            return False, "❌连接失败"
        except Exception as e:
            return True, f"⚠️检查异常: {str(e)[:20]}"
    
    def validate_single(self, data_point: Any, target_period: str = "") -> ValidationResult:
        """
        对单个数据点执行完整校验
        
        Args:
            data_point: 数据点对象
            target_period: 目标数据周期
        
        Returns:
            ValidationResult对象
        """
        data_id = getattr(data_point, '_id', 'unknown')
        data_type = self._get_data_type(data_point)
        
        result = ValidationResult(
            data_id=data_id,
            data_type=data_type,
            is_valid=True
        )
        
        # 1. 时间一致性检查
        if target_period:
            time_ok, time_msg = self.check_time_consistency(data_point, target_period)
            if not time_ok:
                result.time_consistency_passed = False
                result.add_issue(ValidationIssue(
                    issue_type="time_inconsistency",
                    severity="error",
                    message=time_msg,
                    details={"target_period": target_period}
                ))
        
        # 2. 预测值标注检查
        value = getattr(data_point, 'value', '')
        notes = getattr(data_point, 'notes', '') or ''
        forecast_ok, forecast_msg = self.check_forecast_flag(data_point, value, notes)
        if not forecast_ok:
            result.forecast_label_correct = False
            result.add_issue(ValidationIssue(
                issue_type="forecast_unlabeled",
                severity="warning",
                message=forecast_msg,
                details={"value": value}
            ))
        
        # 3. URL验证
        source = getattr(data_point, 'source', None)
        if source:
            url = getattr(source, 'url', '') or ''
            if url and url not in ["-", "⚠️暂未找到"]:
                url_valid, url_msg = self._validate_url_format(url)
                if not url_valid:
                    result.url_accessible = False
                    result.add_issue(ValidationIssue(
                        issue_type="url_invalid",
                        severity="warning",
                        message=f"URL无效: {url_msg}",
                        details={"url": url}
                    ))
        
        return result
    
    def validate_batch(self, data_points: List[Any], target_period: str = "") -> List[ValidationResult]:
        """
        批量校验数据点
        
        Args:
            data_points: 数据点列表
            target_period: 目标数据周期
        
        Returns:
            ValidationResult列表
        """
        results = []
        
        # 按指标分组进行冲突检测
        indicators = set()
        for dp in data_points:
            indicator = getattr(dp, 'indicator', '') or getattr(dp, 'title', '') or 'unknown'
            indicators.add(indicator)
        
        # 检测所有冲突
        all_conflicts = []
        for indicator in indicators:
            conflicts = self.detect_conflicts(data_points, indicator)
            all_conflicts.extend(conflicts)
        
        # 对每个数据点执行校验
        for dp in data_points:
            result = self.validate_single(dp, target_period)
            
            # 添加冲突信息
            data_id = getattr(dp, '_id', 'unknown')
            dp_conflicts = [c for c in all_conflicts 
                           if c['source1'] == getattr(dp, 'source', None) or
                           c['source2'] == getattr(dp, 'source', None)]
            
            if dp_conflicts:
                result.no_conflict = False
                for conflict in dp_conflicts:
                    result.add_issue(ValidationIssue(
                        issue_type="conflict",
                        severity=conflict['severity'],
                        message=f"数据冲突: {conflict['source1']}({conflict['value1']}) vs {conflict['source2']}({conflict['value2']})，差异{conflict['diff_percent']}%",
                        details=conflict
                    ))
            
            results.append(result)
        
        return results
    
    def _get_data_type(self, data_point: Any) -> str:
        """获取数据点类型"""
        type_map = {
            DomesticDataPoint: "domestic",
            GlobalDataPoint: "global",
            CompetitorEvent: "competitor",
            IndustryNews: "news"
        }
        for cls, dtype in type_map.items():
            if isinstance(data_point, cls):
                return dtype
        return "unknown"


# 便捷函数
def check_time_consistency(data_point: Any, target_period: str) -> Tuple[bool, Optional[str]]:
    """检查时间一致性"""
    return DataValidator().check_time_consistency(data_point, target_period)


def check_forecast_flag(data_point: Any, value: str, notes: str = "") -> Tuple[bool, Optional[str]]:
    """检测预测值标注"""
    return DataValidator().check_forecast_flag(data_point, value, notes)


def detect_conflicts(data_points: List[Any], indicator: str) -> List[Dict[str, Any]]:
    """检测数据冲突"""
    return DataValidator().detect_conflicts(data_points, indicator)


def validate_urls(data_points: List[Any]) -> List[Dict[str, Any]]:
    """验证URL"""
    return DataValidator().validate_urls(data_points)
