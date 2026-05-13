# -*- coding: utf-8 -*-
"""
数据源配置模块 - 读取和管理数据源配置

提供 get_sources(), get_credibility_by_source(), validate_source_url() 方法
"""

import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class DataSourceManager:
    """
    数据源管理器
    
    负责加载配置、按条件筛选数据源、查询可信度等级、验证URL
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化数据源管理器
        
        Args:
            config_path: 配置文件路径，默认使用项目根目录下的 rules/data_sources.json
        """
        if config_path is None:
            # 查找项目根目录
            current_dir = Path(__file__).parent.parent
            config_path = current_dir / "rules" / "data_sources.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 构建来源名称到可信度的映射（快速查询）
        self._source_credibility_map = self._build_source_map()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _build_source_map(self) -> Dict[str, str]:
        """构建来源名称到可信度的快速映射"""
        source_map = {}
        
        # 国内数据源
        for industry, sources in self.config.get("domestic", {}).items():
            for source in sources:
                name = source.get("name", "")
                credibility = source.get("credibility", "B")
                source_map[name] = credibility
        
        # 国际数据源
        for industry, sources in self.config.get("global", {}).items():
            for source in sources:
                name = source.get("name", "")
                credibility = source.get("credibility", "B")
                source_map[name] = credibility
        
        # 按可信度分类的来源
        for grade, descriptions in self.config.get("sources_by_credibility", {}).items():
            for desc in descriptions:
                # 描述可能包含机构名，提取关键部分
                source_map[desc] = grade
        
        return source_map
    
    def get_sources(self, industry: str, data_type: str = "all") -> List[Dict[str, Any]]:
        """
        获取指定行业和数据类型的数据源
        
        Args:
            industry: 行业名称（光伏/锂电/新能源汽车）
            data_type: 数据类型（domestic/global/all）
        
        Returns:
            数据源列表
        """
        results = []
        
        # 标准化行业名称
        industry = self._normalize_industry(industry)
        
        # 获取国内数据源
        if data_type in ["domestic", "all"]:
            domestic_sources = self.config.get("domestic", {}).get(industry, [])
            results.extend(domestic_sources)
        
        # 获取国际数据源
        if data_type in ["global", "all"]:
            global_sources = self.config.get("global", {}).get(industry, [])
            results.extend(global_sources)
        
        return results
    
    def _normalize_industry(self, industry: str) -> str:
        """标准化行业名称"""
        industry_mapping = {
            "光伏": "光伏",
            "太阳能": "光伏",
            "PV": "光伏",
            "锂电": "锂电",
            "锂电池": "锂电",
            "动力电池": "锂电",
            "新能源汽车": "新能源汽车",
            "新能源车": "新能源汽车",
            "电动车": "新能源汽车",
            "EV": "新能源汽车"
        }
        return industry_mapping.get(industry, industry)
    
    def get_credibility_by_source(self, source_name: str) -> str:
        """
        根据来源名称获取预评级
        
        Args:
            source_name: 来源名称
        
        Returns:
            可信度等级（A/B/C/D），未找到返回B（默认）
        """
        # 精确匹配
        if source_name in self._source_credibility_map:
            return self._source_credibility_map[source_name]
        
        # 模糊匹配 - 检查来源名是否包含关键字
        source_lower = source_name.lower()
        for known_source, credibility in self._source_credibility_map.items():
            known_lower = known_source.lower()
            # 短名称精确匹配
            if len(known_source) < 5 and known_source in source_name:
                return credibility
            # 长名称包含匹配
            if len(known_source) > 5 and known_lower in source_lower:
                return credibility
        
        # 默认返回B级
        return "B"
    
    def validate_source_url(self, url: str, source_name: str) -> Tuple[bool, Optional[str]]:
        """
        验证URL是否匹配配置的来源pattern
        
        Args:
            url: 待验证的URL
            source_name: 来源名称
        
        Returns:
            (是否匹配, 异常信息)
        """
        if not url or url == "-" or url.startswith("⚠️"):
            return False, "URL缺失或无效"
        
        # 查找该来源的url_pattern
        url_pattern = self._get_source_url_pattern(source_name)
        
        if not url_pattern:
            # 如果没有配置pattern，进行通用验证
            return self._validate_url_format(url)
        
        # 检查URL是否包含配置的pattern
        if url_pattern.lower() in url.lower():
            return True, None
        else:
            return False, f"URL不匹配来源 {source_name} 的域名配置"
    
    def _get_source_url_pattern(self, source_name: str) -> Optional[str]:
        """获取来源的URL pattern"""
        # 在所有数据源中查找
        for category in ["domestic", "global"]:
            for industry, sources in self.config.get(category, {}).items():
                for source in sources:
                    if source.get("name") == source_name:
                        return source.get("url_pattern")
        return None
    
    def _validate_url_format(self, url: str) -> Tuple[bool, Optional[str]]:
        """验证URL格式"""
        # URL格式正则
        url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
            r'(?::\d+)?'  # 端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if url_pattern.match(url):
            return True, None
        else:
            return False, "URL格式无效"
    
    def get_data_type_definition(self, data_type: str) -> Dict[str, Any]:
        """
        获取数据类型定义
        
        Args:
            data_type: 数据类型（历史数据/预测值/估算值）
        
        Returns:
            类型定义
        """
        return self.config.get("data_type_definitions", {}).get(data_type, {})
    
    def get_credibility_upgrade_rules(self) -> List[Dict[str, Any]]:
        """获取可信度升级规则"""
        return self.config.get("credibility_upgrade_rules", [])
    
    def get_credibility_degrade_rules(self) -> List[Dict[str, Any]]:
        """获取可信度降级规则"""
        return self.config.get("credibility_degrade_rules", [])
    
    def get_typical_sources(self, grade: str) -> List[str]:
        """
        获取指定等级对应的典型来源
        
        Args:
            grade: 可信度等级（A/B/C/D）
        
        Returns:
            典型来源列表
        """
        # 从配置中获取
        sources = self.config.get("sources_by_credibility", {}).get(grade, [])
        
        # 也从各行业数据源中收集
        for category in ["domestic", "global"]:
            for industry, source_list in self.config.get(category, {}).items():
                for source in source_list:
                    if source.get("credibility") == grade:
                        name = source.get("name")
                        if name and name not in sources:
                            sources.append(name)
        
        return sources
    
    def get_all_known_sources(self) -> List[str]:
        """获取所有已知来源名称"""
        sources = []
        
        for category in ["domestic", "global"]:
            for industry, source_list in self.config.get(category, {}).items():
                for source in source_list:
                    name = source.get("name")
                    if name and name not in sources:
                        sources.append(name)
        
        return sorted(sources)


# 模块级单例
_instance: Optional[DataSourceManager] = None


def get_source_manager(config_path: Optional[str] = None) -> DataSourceManager:
    """
    获取数据源管理器单例
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        DataSourceManager实例
    """
    global _instance
    if _instance is None:
        _instance = DataSourceManager(config_path)
    return _instance


# 便捷函数
def get_sources(industry: str, data_type: str = "all") -> List[Dict[str, Any]]:
    """获取指定行业和数据类型的数据源"""
    return get_source_manager().get_sources(industry, data_type)


def get_credibility_by_source(source_name: str) -> str:
    """根据来源名称获取预评级"""
    return get_source_manager().get_credibility_by_source(source_name)


def validate_source_url(url: str, source_name: str) -> Tuple[bool, Optional[str]]:
    """验证URL是否匹配配置的来源"""
    return get_source_manager().validate_source_url(url, source_name)
