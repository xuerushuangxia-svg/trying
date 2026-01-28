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
    
    # 通达信风险关注板块相关
    in_risk_board: bool = False          # 是否在风险警示板块
    risk_type: Optional[str] = None      # 风险类型
    concept_boards: List[str] = None     # 所属概念板块
    has_risk_concept: bool = False       # 是否有风险概念
    
    # 新增：详细风险标签
    risk_tags: List[Dict] = None         # 风险标签列表
    risk_details: List[str] = None       # 风险详情列表
    critical_risks: List[str] = None     # 严重风险（ST/*ST）
    high_risks: List[str] = None         # 高风险（业绩预亏等）
    medium_risks: List[str] = None       # 中等风险（质押、解禁等）
    info_risks: List[str] = None         # 提示信息
    
    # 触发监管相关
    regulatory_count: int = 0            # 监管公告数量
    has_inquiry: bool = False            # 是否有问询函
    has_warning: bool = False            # 是否有警示函
    has_punishment: bool = False         # 是否有处罚
    has_rectification: bool = False      # 是否有整改
    regulatory_announcements: List[Dict] = None  # 监管公告列表
    
    def __post_init__(self):
        if self.concept_boards is None:
            self.concept_boards = []
        if self.regulatory_announcements is None:
            self.regulatory_announcements = []
        if self.risk_tags is None:
            self.risk_tags = []
        if self.risk_details is None:
            self.risk_details = []
        if self.critical_risks is None:
            self.critical_risks = []
        if self.high_risks is None:
            self.high_risks = []
        if self.medium_risks is None:
            self.medium_risks = []
        if self.info_risks is None:
            self.info_risks = []
    
    @property
    def legal_status(self) -> str:
        if self.has_legal_risk:
            return "status-red"
        elif self.has_regulatory_risk:
            return "status-yellow"
        return "status-green"
    
    @property
    def risk_board_status(self) -> str:
        """风险关注板块状态"""
        if self.critical_risks or self.in_risk_board:
            return "status-red"
        elif self.high_risks:
            return "status-red"
        elif self.medium_risks or self.has_risk_concept:
            return "status-yellow"
        elif self.info_risks:
            return "status-yellow"
        return "status-green"
    
    @property
    def regulatory_status(self) -> str:
        """触发监管状态"""
        if self.has_punishment:
            return "status-red"
        elif self.has_inquiry or self.has_warning or self.has_rectification:
            return "status-yellow"
        elif self.regulatory_count > 0:
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
