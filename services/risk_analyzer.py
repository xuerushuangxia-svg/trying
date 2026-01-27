"""
风险分析模块 - 负责分析股票风险
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import pandas as pd

from config.settings import RISK_KEYWORDS, settings


@dataclass
class RiskAssessment:
    """风险评估结果"""
    has_legal_risk: bool = False
    has_regulatory_risk: bool = False
    has_st_risk: bool = False
    has_financing_risk: bool = False
    has_abnormal_activity: bool = False
    is_high_frequency: bool = False
    pb_value: float = 0.0
    pe_value: Optional[float] = None
    market_value: Optional[float] = None
    
    @property
    def legal_status(self) -> str:
        if self.has_legal_risk:
            return "status-red"
        elif self.has_regulatory_risk:
            return "status-yellow"
        return "status-green"
    
    @property
    def frequency_status(self) -> str:
        return "status-yellow" if self.is_high_frequency else "status-green"
    
    @property
    def valuation_status(self) -> str:
        return "status-red" if self.pb_value > settings.pb_warning_threshold else "status-green"
    
    @property
    def financing_status(self) -> str:
        return "status-red" if self.has_financing_risk else "status-green"


class RiskAnalyzer:
    """风险分析器"""
    
    def __init__(self):
        self.keywords = RISK_KEYWORDS
    
    def analyze(self, snap: Dict[str, Any], anns: List[Dict]) -> RiskAssessment:
        """
        分析风险并返回评估结果
        
        Args:
            snap: 股票快照数据
            anns: 公告列表
            
        Returns:
            RiskAssessment: 风险评估结果
        """
        assessment = RiskAssessment()
        
        # 合并公告标题用于关键词检测
        anns = anns or []
        ann_text = "".join([a.get('title', '') for a in anns if isinstance(a, dict)])
        
        # 法律风险检测
        assessment.has_legal_risk = any(k in ann_text for k in self.keywords['legal'])
        
        # 监管风险检测
        assessment.has_regulatory_risk = any(k in ann_text for k in self.keywords['regulatory'])
        
        # 转融通风险检测
        assessment.has_financing_risk = any(k in ann_text for k in self.keywords['financing'])
        
        # 异动检测
        assessment.has_abnormal_activity = any(k in ann_text for k in self.keywords['abnormal'])
        
        # 高频公告检测
        assessment.is_high_frequency = len(anns) > 40
        
        # PB 值计算
        try:
            assessment.pb_value = float(snap.get('f167') or 0) / 100.0
        except Exception:
            assessment.pb_value = 0.0
        
        # PE 值计算
        try:
            pe_raw = snap.get('f43')
            assessment.pe_value = float(pe_raw) if pe_raw not in (None, '') else None
        except Exception:
            assessment.pe_value = None
        
        # 市值计算
        try:
            mkt_raw = snap.get('f116')
            assessment.market_value = float(mkt_raw) if mkt_raw not in (None, '') else None
        except Exception:
            assessment.market_value = None
        
        # ST 风险检测
        stock_name = str(snap.get('f58', ''))
        is_st_name = "ST" in stock_name
        try:
            is_negative_profit = float(snap.get('f114') or 0) < 0 if snap.get('f114') is not None else False
        except Exception:
            is_negative_profit = False
        assessment.has_st_risk = is_st_name or is_negative_profit
        
        return assessment
    
    def extract_partners(self, comp_text: str) -> List[str]:
        """从公司简介中提取合作方"""
        comp_text = str(comp_text) if comp_text else ""
        if not comp_text or comp_text == "None":
            return []
        
        partners = []
        matches = re.findall(r'(与|和|及)([^，。；]{2,40})(合作|参股|共同|投资)', comp_text)
        for m in matches:
            partners.append(m[1].strip())
        
        return partners
    
    def detect_institutional_holders(self, holders: pd.DataFrame) -> pd.DataFrame:
        """检测机构类持股"""
        if holders is None or holders.empty:
            return pd.DataFrame()
        
        inst_mask = holders['holder_name'].astype(str).str.contains(
            '有限|公司|基金|证券|资产', na=False
        )
        return holders[inst_mask]


# 全局风险分析器实例
risk_analyzer = RiskAnalyzer()
