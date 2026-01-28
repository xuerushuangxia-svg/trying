"""
应用配置和常量定义
"""
from dataclasses import dataclass
from typing import List, Dict

# 风险关键词配置
RISK_KEYWORDS: Dict[str, List[str]] = {
    'legal': ['立案', '调查', '违法', '告知书', '处罚'],
    'regulatory': ['监管', '问询函', '警示函', '整改'],
    'financing': ['转融通', '出借', '融券'],
    'abnormal': ['异动']
}

# API 配置
@dataclass
class APIConfig:
    """API 配置"""
    eastmoney_stock_list_url: str = "https://push2.eastmoney.com/api/qt/clist/get"
    eastmoney_stock_detail_url: str = "https://push2.eastmoney.com/api/qt/stock/get"
    eastmoney_announcement_url: str = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    request_timeout: int = 10
    cache_ttl: int = 600  # 10 分钟


@dataclass
class Settings:
    """应用设置"""
    app_title: str = "XUE 风险全维度穿透终端"
    default_stock_code: str = "600519"
    search_limit: int = 200
    announcement_limit: int = 50
    pb_warning_threshold: float = 8.0
    api: APIConfig = None
    
    def __post_init__(self):
        if self.api is None:
            self.api = APIConfig()


# 全局设置实例
settings = Settings()
