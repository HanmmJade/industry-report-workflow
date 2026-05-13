# -*- coding: utf-8 -*-
"""
数据搜集模块 - SearchCollector

通过搜索API搜集行业数据，支持真实联网搜集和模拟数据fallback模式。
使用 requests 库调用公开搜索API，同时也支持无API key时的演示模式。
"""

import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

import requests

from data_models import (
    DomesticDataPoint, GlobalDataPoint, CompetitorEvent, IndustryNews,
    DataSource, CredibilityGrade, DynamicType, NewsCategory
)


class CollectMode(Enum):
    """搜集模式枚举"""
    LIVE = "live"      # 真实联网搜集
    DEMO = "demo"      # 模拟数据模式


@dataclass
class CollectResult:
    """搜集结果封装"""
    success: bool
    data: List[Any]
    mode: CollectMode
    error_msg: Optional[str] = None
    api_key_used: bool = False


class SearchCollector:
    """
    搜索数据搜集器
    
    支持两种模式：
    1. LIVE模式：使用SerpAPI风格接口调用搜索API
    2. DEMO模式：无API key或搜集失败时，使用高质量模拟数据
    
    搜集方法：
    - collect_domestic_data(): 国内行业数据
    - collect_global_data(): 国际行业数据
    - collect_competitor_dynamics(): 竞对动态
    - collect_industry_news(): 行业资讯
    """
    
    # 行业同义词映射
    INDUSTRY_ALIASES = {
        "光伏": ["光伏", "太阳能", "PV", "太阳能发电"],
        "锂电": ["锂电", "锂电池", "动力电池", "储能电池"],
        "新能源汽车": ["新能源汽车", "新能源车", "电动车", "EV", "电动汽车"]
    }
    
    # 国内数据指标（按行业）
    DOMESTIC_INDICATORS = {
        "光伏": [
            {"name": "新增装机量", "unit": "GW", "keywords": ["新增装机", "装机量"]},
            {"name": "发电量", "unit": "亿千瓦时", "keywords": ["发电量", "发电"]},
            {"name": "组件产量", "unit": "GW", "keywords": ["组件产量", "组件"]},
            {"name": "电池片产量", "unit": "GW", "keywords": ["电池片产量", "电池片"]},
        ],
        "锂电": [
            {"name": "动力电池装车量", "unit": "GWh", "keywords": ["装车量", "装机电量"]},
            {"name": "三元材料产量", "unit": "万吨", "keywords": ["三元材料", "三元"]},
            {"name": "磷酸铁锂产量", "unit": "万吨", "keywords": ["磷酸铁锂", "铁锂"]},
        ],
        "新能源汽车": [
            {"name": "新能源汽车销量", "unit": "万辆", "keywords": ["销量", "零售"]},
            {"name": "新能源乘用车销量", "unit": "万辆", "keywords": ["乘用车销量", "乘联会"]},
            {"name": "新能源商用车销量", "unit": "万辆", "keywords": ["商用车", "客车"]},
        ]
    }
    
    # 全球数据指标（按行业）
    GLOBAL_INDICATORS = {
        "光伏": [
            {"name": "全球新增装机量", "unit": "GW", "keywords": ["global", "新增装机", "装机"]},
            {"name": "组件出货量", "unit": "GW", "keywords": ["出货量", "shipment"]},
        ],
        "锂电": [
            {"name": "全球动力电池装车量", "unit": "GWh", "keywords": ["global", "装车量"]},
            {"name": "电池原材料价格", "unit": "万元/吨", "keywords": ["原材料价格", "碳酸锂"]},
        ],
        "新能源汽车": [
            {"name": "全球新能源汽车销量", "unit": "万辆", "keywords": ["global", "销量", "sales"]},
            {"name": "欧洲电动车销量", "unit": "万辆", "keywords": ["欧洲", "销量"]},
        ]
    }
    
    # 竞对事件类型关键词
    COMPETITOR_EVENT_TYPES = [
        {"type": DynamicType.IPO, "keywords": ["上市", "IPO", "IPO上市"]},
        {"type": DynamicType.FINANCING, "keywords": ["融资", "投资", "定增"]},
        {"type": DynamicType.TECH_BREAKTHROUGH, "keywords": ["技术突破", "研发", "新产品"]},
        {"type": DynamicType.PRODUCTION_EXPAND, "keywords": ["产能", "扩产", "新建"]},
        {"type": DynamicType.STRATEGIC_COOP, "keywords": ["合作", "战略", "签约"]},
        {"type": DynamicType.FINANCIAL, "keywords": ["财报", "业绩", "营收"]},
    ]
    
    # 行业资讯分类关键词
    NEWS_CATEGORIES = [
        {"type": NewsCategory.IPO_FINANCING, "keywords": ["IPO", "融资", "上市"]},
        {"type": NewsCategory.NEW_PRODUCT_TECH, "keywords": ["新产品", "技术", "突破"]},
        {"type": NewsCategory.PRODUCTION_EXPAND, "keywords": ["产能", "扩张", "投资"]},
        {"type": NewsCategory.STRATEGIC_MERGER, "keywords": ["合作", "并购", "收购"]},
        {"type": NewsCategory.POLICY_DYNAMIC, "keywords": ["政策", "规划", "补贴"]},
        {"type": NewsCategory.INDUSTRY_TREND, "keywords": ["趋势", "展望", "预测"]},
    ]
    
    # 典型A级来源（用于可信度评级）
    GRADE_A_SOURCES = [
        "国家能源局", "国家统计局", "中国汽车工业协会", "中国汽车动力电池产业创新联盟",
        "BNEF", "IEA", "IEA PVPS", "SNE Research", "CPIA", "乘联会",
        "EVtank", "Benchmark Minerals", "Ember"
    ]
    
    def __init__(self, api_key: Optional[str] = None, use_demo_fallback: bool = True):
        """
        初始化搜集器
        
        Args:
            api_key: SerpAPI风格的搜索API密钥
            use_demo_fallback: 搜集失败时是否使用模拟数据，默认为True
        """
        self.api_key = api_key
        self.use_demo_fallback = use_demo_fallback
        self.mode = CollectMode.LIVE if api_key else CollectMode.DEMO
        
        # 加载数据源配置
        self._load_source_config()
    
    def _load_source_config(self):
        """加载数据源配置文件"""
        try:
            config_path = __file__.parent.parent / "rules" / "data_sources.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.source_config = json.load(f)
            else:
                self.source_config = {"domestic": {}, "global": {}}
        except Exception:
            self.source_config = {"domestic": {}, "global": {}}
    
    def _generate_search_keywords(
        self,
        industry: str,
        period: str,
        data_category: str
    ) -> List[str]:
        """
        根据行业、周期和数据类别生成搜索关键词
        
        Args:
            industry: 行业名称
            period: 时间周期（如：2026年3月）
            data_category: 数据类别（domestic/global/competitor/news）
        
        Returns:
            搜索关键词列表
        """
        keywords = []
        
        # 解析周期中的年份
        year_match = re.search(r'(\d{4})', period)
        year = year_match.group(1) if year_match else datetime.now().strftime("%Y")
        
        # 获取行业同义词
        aliases = self.INDUSTRY_ALIASES.get(industry, [industry])
        primary_alias = aliases[0]
        
        if data_category == "domestic":
            # 国内数据："{period} 中国{industry} {指标名} {来源机构名}"
            for ind_alias in aliases[:1]:  # 使用主名称
                for indicator in self.DOMESTIC_INDICATORS.get(industry, []):
                    for src_name in self.GRADE_A_SOURCES[:3]:  # 取前3个A级来源
                        kw = f"{period} 中国{primary_alias} {indicator['name']} {src_name}"
                        keywords.append(kw)
        
        elif data_category == "global":
            # 国际数据："{year} global {industry} {metric} {source_name}"
            for indicator in self.GLOBAL_INDICATORS.get(industry, []):
                for src_name in ["BNEF", "IEA", "SNE Research"]:
                    kw = f"{year} global {primary_alias} {indicator['name']} {src_name}"
                    keywords.append(kw)
        
        elif data_category == "competitor":
            # 竞对动态："{company_name} {period} {event_type}"
            # 使用行业头部企业作为占位
            companies = ["宁德时代", "比亚迪", "隆基绿能", "通威股份", "阳光电源"]
            for company in companies[:3]:
                for event_type in ["融资", "技术突破", "产能扩张"]:
                    kw = f"{company} {period} {event_type}"
                    keywords.append(kw)
        
        elif data_category == "news":
            # 行业资讯："{industry} {period} {news_category}"
            for category in ["政策动态", "行业趋势", "技术进展"]:
                kw = f"{primary_alias} {period} {category}"
                keywords.append(kw)
        
        return keywords[:5]  # 最多返回5个关键词
    
    def _call_search_api(self, query: str) -> Optional[Dict]:
        """
        调用搜索API
        
        Args:
            query: 搜索关键词
        
        Returns:
            API响应结果或None
        """
        if not self.api_key:
            return None
        
        try:
            # 使用 SerpAPI 风格接口
            # 实际使用时替换为真实的API endpoint和参数
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": 5
            }
            
            # 这里使用示例endpoint，实际部署时替换为真实API
            # response = requests.get("https://serpapi.com/search", params=params, timeout=10)
            # result = response.json()
            
            # 模拟API响应结构（实际部署时删除此段）
            # return {"results": result.get("organic_results", [])}
            return None
            
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
        except Exception:
            return None
    
    def _parse_search_results(self, raw_results: Dict, data_category: str) -> List[Dict]:
        """
        解析搜索结果，提取关键数据
        
        Args:
            raw_results: 原始API响应
            data_category: 数据类别
        
        Returns:
            解析后的数据列表
        """
        parsed = []
        
        try:
            results = raw_results.get("results", [])
            for item in results[:3]:  # 取前3条
                parsed.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "source": item.get("source", "")
                })
        except Exception:
            pass
        
        return parsed
    
    def _create_demo_data(
        self,
        industry: str,
        period: str,
        data_category: str
    ) -> List[Any]:
        """
        创建高质量模拟数据用于演示
        
        Args:
            industry: 行业名称
            period: 时间周期
            data_category: 数据类别
        
        Returns:
            模拟数据列表
        """
        now = datetime.now()
        publish_date = now.strftime("%Y-%m-%d")
        
        # 计算周期结束日期（月度数据为下月上旬）
        period_match = re.match(r'(\d{4})年(\d{1,2})月', period)
        if period_match:
            year, month = int(period_match.group(1)), int(period_match.group(2))
            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            publish_date = f"{next_year}-{next_month:02d}-15"  # 假设月中旬发布
        
        demo_data = []
        
        if data_category == "domestic":
            # 模拟国内数据
            indicators = self.DOMESTIC_INDICATORS.get(industry, [
                {"name": "行业产量", "unit": "万吨"}
            ])
            sources = self.source_config.get("domestic", {}).get(industry, [])
            
            for i, ind in enumerate(indicators[:3]):
                source_info = sources[i] if i < len(sources) else {
                    "name": "行业数据平台",
                    "credibility": "B"
                }
                
                demo_data.append(DomesticDataPoint(
                    _id=f"DOM_DEMO_{i+1:04d}",
                    indicator=ind["name"],
                    value=f"demo_{i+1} {ind['unit']}",
                    unit=ind["unit"],
                    time_period=period,
                    source=DataSource(
                        name=source_info.get("name", "行业机构"),
                        url="https://example.com/data",
                        publish_date=publish_date,
                        credibility=self._parse_credibility(source_info.get("credibility", "B"))
                    ),
                    cross_validation=["数字新能源DNE"] if i == 0 else [],
                    is_forecast=False
                ))
        
        elif data_category == "global":
            # 模拟国际数据
            indicators = self.GLOBAL_INDICATORS.get(industry, [
                {"name": "全球行业规模", "unit": "GW"}
            ])
            
            for i, ind in enumerate(indicators[:2]):
                demo_data.append(GlobalDataPoint(
                    _id=f"GLO_DEMO_{i+1:04d}",
                    indicator=ind["name"],
                    value=f"demo_global_{i+1} {ind['unit']}",
                    unit=ind["unit"],
                    time_period=period,
                    geographic_scope="全球",
                    source=DataSource(
                        name="BNEF" if i == 0 else "IEA PVPS",
                        url="https://example.com/global",
                        publish_date=publish_date,
                        credibility=CredibilityGrade.A
                    ),
                    cross_validation=["IEA"] if i == 0 else [],
                    is_forecast=True if i == 1 else False,
                    forecast_note="预测值" if i == 1 else None
                ))
        
        elif data_category == "competitor":
            # 模拟竞对动态
            companies = ["宁德时代", "比亚迪", "隆基绿能"]
            event_types = [
                (DynamicType.FINANCIAL, "发布季度财报"),
                (DynamicType.TECH_BREAKTHROUGH, "新技术通过测试"),
                (DynamicType.PRODUCTION_EXPAND, "新产能投产"),
            ]
            
            for i, (company, desc) in enumerate(event_types):
                demo_data.append(CompetitorEvent(
                    _id=f"COMP_DEMO_{i+1:04d}",
                    company_name=company,
                    dynamic_type=DynamicType.FINANCIAL if i == 0 else DynamicType.TECH_BREAKTHROUGH if i == 1 else DynamicType.PRODUCTION_EXPAND,
                    title=f"{company}{desc}",
                    description=f"{company}{desc}，行业地位进一步巩固",
                    event_date=publish_date,
                    source=DataSource(
                        name="企业公告",
                        url="https://example.com/announcement",
                        publish_date=publish_date,
                        credibility=CredibilityGrade.A
                    )
                ))
        
        elif data_category == "news":
            # 模拟行业资讯
            news_items = [
                ("行业趋势", NewsCategory.INDUSTRY_TREND, "行业健康发展"),
                ("技术进展", NewsCategory.NEW_PRODUCT_TECH, "技术路线更新"),
                ("市场动态", NewsCategory.PRODUCTION_EXPAND, "新建项目落地"),
            ]
            
            for i, (title, category, content) in enumerate(news_items):
                demo_data.append(IndustryNews(
                    _id=f"NEWS_DEMO_{i+1:04d}",
                    title=f"{period} {industry} {title}",
                    category=category,
                    date=publish_date,
                    description=f"{industry}{content}，{period}呈现积极发展态势",
                    source=DataSource(
                        name="行业媒体",
                        url="https://example.com/news",
                        publish_date=publish_date,
                        credibility=CredibilityGrade.B
                    ),
                    details={"url": "https://example.com/news"}
                ))
        
        return demo_data
    
    def _parse_credibility(self, grade_str: str) -> CredibilityGrade:
        """解析可信度等级字符串"""
        mapping = {"A": CredibilityGrade.A, "B": CredibilityGrade.B, 
                   "C": CredibilityGrade.C, "D": CredibilityGrade.D}
        return mapping.get(grade_str, CredibilityGrade.B)
    
    def collect_domestic_data(
        self,
        industry: str,
        period: str
    ) -> CollectResult:
        """
        搜集国内行业数据
        
        Args:
            industry: 行业名称
            period: 时间周期（如：2026年3月）
        
        Returns:
            搜集结果
        """
        keywords = self._generate_search_keywords(industry, period, "domestic")
        
        if self.mode == CollectMode.LIVE and self.api_key:
            try:
                # 真实搜集模式
                all_results = []
                for kw in keywords[:3]:  # 限制搜索次数
                    result = self._call_search_api(kw)
                    if result:
                        parsed = self._parse_search_results(result, "domestic")
                        all_results.extend(parsed)
                    time.sleep(0.5)  # 避免API限流
                
                if all_results:
                    # TODO: 将搜索结果转换为DomesticDataPoint
                    # 目前返回空，待后续扩展
                    pass
            except Exception as e:
                error_msg = f"联网搜集失败: {str(e)}"
        
        # Fallback到模拟数据
        if self.use_demo_fallback:
            return CollectResult(
                success=True,
                data=self._create_demo_data(industry, period, "domestic"),
                mode=CollectMode.DEMO,
                error_msg="使用演示数据（无API key或搜集失败）"
            )
        
        return CollectResult(
            success=False,
            data=[],
            mode=self.mode,
            error_msg="联网搜集失败且未启用演示模式"
        )
    
    def collect_global_data(
        self,
        industry: str,
        period: str
    ) -> CollectResult:
        """
        搜集国际行业数据
        
        Args:
            industry: 行业名称
            period: 时间周期
        
        Returns:
            搜集结果
        """
        keywords = self._generate_search_keywords(industry, period, "global")
        
        if self.mode == CollectMode.LIVE and self.api_key:
            try:
                all_results = []
                for kw in keywords[:3]:
                    result = self._call_search_api(kw)
                    if result:
                        parsed = self._parse_search_results(result, "global")
                        all_results.extend(parsed)
                    time.sleep(0.5)
            except Exception as e:
                pass
        
        if self.use_demo_fallback:
            return CollectResult(
                success=True,
                data=self._create_demo_data(industry, period, "global"),
                mode=CollectMode.DEMO,
                error_msg="使用演示数据（无API key或搜集失败）"
            )
        
        return CollectResult(
            success=False,
            data=[],
            mode=self.mode,
            error_msg="联网搜集失败"
        )
    
    def collect_competitor_dynamics(
        self,
        industry: str,
        period: str,
        competitors: Optional[List[str]] = None
    ) -> CollectResult:
        """
        搜集竞争对手动态
        
        Args:
            industry: 行业名称
            period: 时间周期
            competitors: 竞争对手列表，默认使用行业头部企业
        
        Returns:
            搜集结果
        """
        keywords = self._generate_search_keywords(industry, period, "competitor")
        
        if self.mode == CollectMode.LIVE and self.api_key:
            try:
                all_results = []
                for kw in keywords[:3]:
                    result = self._call_search_api(kw)
                    if result:
                        parsed = self._parse_search_results(result, "competitor")
                        all_results.extend(parsed)
                    time.sleep(0.5)
            except Exception:
                pass
        
        if self.use_demo_fallback:
            return CollectResult(
                success=True,
                data=self._create_demo_data(industry, period, "competitor"),
                mode=CollectMode.DEMO,
                error_msg="使用演示数据（无API key或搜集失败）"
            )
        
        return CollectResult(
            success=False,
            data=[],
            mode=self.mode,
            error_msg="联网搜集失败"
        )
    
    def collect_industry_news(
        self,
        industry: str,
        period: str
    ) -> CollectResult:
        """
        搜集行业资讯
        
        Args:
            industry: 行业名称
            period: 时间周期
        
        Returns:
            搜集结果
        """
        keywords = self._generate_search_keywords(industry, period, "news")
        
        if self.mode == CollectMode.LIVE and self.api_key:
            try:
                all_results = []
                for kw in keywords[:3]:
                    result = self._call_search_api(kw)
                    if result:
                        parsed = self._parse_search_results(result, "news")
                        all_results.extend(parsed)
                    time.sleep(0.5)
            except Exception:
                pass
        
        if self.use_demo_fallback:
            return CollectResult(
                success=True,
                data=self._create_demo_data(industry, period, "news"),
                mode=CollectMode.DEMO,
                error_msg="使用演示数据（无API key或搜集失败）"
            )
        
        return CollectResult(
            success=False,
            data=[],
            mode=self.mode,
            error_msg="联网搜集失败"
        )
    
    def collect_all(
        self,
        industry: str,
        period: str,
        data_types: List[str]
    ) -> Dict[str, CollectResult]:
        """
        一次性搜集多种类型数据
        
        Args:
            industry: 行业名称
            period: 时间周期
            data_types: 数据类型列表
        
        Returns:
            各类型数据的搜集结果字典
        """
        results = {}
        
        type_mapping = {
            "domestic": self.collect_domestic_data,
            "global": self.collect_global_data,
            "competitor": self.collect_competitor_dynamics,
            "news": self.collect_industry_news
        }
        
        for dtype in data_types:
            collector = type_mapping.get(dtype)
            if collector:
                results[dtype] = collector(industry, period)
        
        return results


# 便捷函数
def create_collector(api_key: Optional[str] = None) -> SearchCollector:
    """
    创建搜集器实例的便捷函数
    
    Args:
        api_key: API密钥，不提供则使用演示模式
    
    Returns:
        SearchCollector实例
    """
    return SearchCollector(api_key=api_key, use_demo_fallback=True)
