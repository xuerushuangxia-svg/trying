"""
数据服务模块 - 负责从各数据源获取股票数据（使用东方财富免费接口）
"""
import requests
import pandas as pd
import difflib
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any

from config.settings import settings


class DataService:
    """数据服务类，提供股票数据获取功能"""
    
    def __init__(self):
        self._index_cache: Optional[pd.DataFrame] = None
        self._search_cache: Dict[str, pd.DataFrame] = {}
    
    def load_full_index(self) -> pd.DataFrame:
        """
        加载全量股票索引
        从东方财富拉取
        """
        if self._index_cache is not None:
            return self._index_cache
        
        # 尝试东方财富接口
        df = self._fetch_from_eastmoney()
        if df is not None and not df.empty:
            self._index_cache = df
            return df
        
        return pd.DataFrame()
    
    def _fetch_from_eastmoney(self) -> Optional[pd.DataFrame]:
        """从东方财富获取股票列表"""
        url = f"{settings.api.eastmoney_stock_list_url}?pn=1&pz=6000&po=1&np=1&fields=f12,f14,f100&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        try:
            r = requests.get(url, timeout=settings.api.request_timeout)
            if r.status_code == 200:
                data = r.json().get('data', {}).get('diff', [])
                df = pd.DataFrame(data)
                if not df.empty:
                    return self._normalize_index_df(df)
        except Exception:
            pass
        return None
    
    def _normalize_index_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """规范化索引 DataFrame"""
        cols = df.columns.tolist()
        if len(cols) >= 3:
            mapping = {cols[0]: 'symbol', cols[1]: 'name', cols[2]: 'industry'}
            df = df.rename(columns=mapping)
        
        for c in ['symbol', 'name']:
            if c not in df.columns:
                df[c] = ""
        
        df['industry'] = df.get('industry', '').fillna('').astype(str)
        df['symbol'] = df['symbol'].astype(str).str.strip()
        df['name'] = df['name'].astype(str).str.strip()
        df['label'] = df['symbol'] + " | " + df['name'] + " (" + df['industry'] + ")"
        df['name_lower'] = df['name'].str.lower()
        df['search'] = df['symbol'].str.lower() + " " + df['name_lower']
        
        return df[['symbol', 'name', 'industry', 'label', 'name_lower', 'search']]
    
    def search_stocks(self, query: str, limit: int = 50) -> pd.DataFrame:
        """
        搜索股票
        - 优先匹配以 query 开头的代码或名称
        - 若无结果，使用包含匹配
        - 若仍无结果，使用 difflib 做近似匹配
        """
        df = self.load_full_index()
        q = (query or "").strip().lower()
        
        if df is None or df.empty or q == "":
            return df.head(limit) if df is not None else pd.DataFrame()
        
        # 检查缓存
        cache_key = f"{q}::{df.shape[0]}::{limit}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        # startswith 优先
        mask_start = df['symbol'].str.lower().str.startswith(q) | df['name_lower'].str.startswith(q)
        res = df[mask_start]
        if not res.empty:
            result = res.head(limit)
            self._search_cache[cache_key] = result
            return result
        
        # contains
        mask_contains = df['search'].str.contains(q, na=False)
        res = df[mask_contains]
        if not res.empty:
            result = res.head(limit)
            self._search_cache[cache_key] = result
            return result
        
        # difflib 近似匹配
        names = df['name'].tolist()
        syms = df['symbol'].tolist()
        close = difflib.get_close_matches(query, names, n=limit, cutoff=0.6)
        close_sym = difflib.get_close_matches(query, syms, n=limit, cutoff=0.6)
        candidates = df[df['name'].isin(close) | df['symbol'].isin(close_sym)]
        if not candidates.empty:
            result = candidates.head(limit)
            self._search_cache[cache_key] = result
            return result
        
        return pd.DataFrame()
    
    def fetch_risk_data(self, code: str) -> Tuple[Optional[Dict], Optional[List]]:
        """获取风险相关数据"""
        m_id = "1." + code if code.startswith("6") else "0." + code
        try:
            # 财务/基本面快照
            r1 = requests.get(
                f"{settings.api.eastmoney_stock_detail_url}?secid={m_id}&fields=f58,f43,f170,f167,f116,f127,f186,f114,f115,f117",
                timeout=settings.api.request_timeout
            )
            snap = r1.json().get('data', {}) if r1.status_code == 200 else {}
            
            # 公告扫描
            r2 = requests.get(
                f"{settings.api.eastmoney_announcement_url}?sr=-1&page_size={settings.announcement_limit}&page_index=1&stock_list={code}",
                timeout=settings.api.request_timeout
            )
            anns = r2.json().get('data', {}).get('list', []) if r2.status_code == 200 else []
            
            return snap, anns
        except Exception:
            return None, None
    
    def fetch_extra_details(self, code: str) -> Dict[str, Any]:
        """获取额外详情（公司、股东、财务指标）- 使用东方财富接口"""
        em_code = f"SH{code}" if code.startswith("6") else f"SZ{code}"
        out = {"company": None, "holders": None, "float_holders": None, "fina": None}
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://emweb.securities.eastmoney.com/'
        }
        
        # 获取公司概况
        try:
            url = f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax?code={em_code}"
            r = requests.get(url, headers=headers, timeout=settings.api.request_timeout)
            if r.status_code == 200:
                data = r.json()
                # 解析公司基本信息 - 使用正确的大写字段名
                jbzl = data.get('jbzl', [{}])[0] if data.get('jbzl') else {}
                if jbzl:
                    out["company"] = pd.DataFrame([{
                        'reg_name': jbzl.get('ORG_NAME', jbzl.get('SECURITY_NAME_ABBR', '')),
                        'chairman': jbzl.get('CHAIRMAN', jbzl.get('LEGAL_PERSON', '')),
                        'main_business': jbzl.get('BUSINESS_SCOPE', ''),
                        'introduction': jbzl.get('ORG_PROFILE', ''),
                        'province': jbzl.get('PROVINCE', ''),
                        'city': jbzl.get('ADDRESS', '')
                    }])
        except Exception:
            pass
        
        # 获取十大股东
        try:
            url = f"https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code={em_code}"
            r = requests.get(url, headers=headers, timeout=settings.api.request_timeout)
            if r.status_code == 200:
                data = r.json()
                # 十大股东 - 使用正确的大写字段名
                sdgd = data.get('sdgd', [])
                if sdgd:
                    holders_list = []
                    for item in sdgd:
                        holders_list.append({
                            'holder_name': item.get('HOLDER_NAME', ''),
                            'hold_ratio': item.get('HOLD_NUM_RATIO', ''),
                            'hold_amount': item.get('HOLD_NUM', '')
                        })
                    if holders_list:
                        out["holders"] = pd.DataFrame(holders_list)
                
                # 十大流通股东
                sdltgd = data.get('sdltgd', [])
                if sdltgd:
                    float_holders_list = []
                    for item in sdltgd:
                        float_holders_list.append({
                            'holder_name': item.get('HOLDER_NAME', ''),
                            'hold_ratio': item.get('HOLD_NUM_RATIO', ''),
                            'hold_amount': item.get('HOLD_NUM', '')
                        })
                    if float_holders_list:
                        out["float_holders"] = pd.DataFrame(float_holders_list)
        except Exception:
            pass
        
        # 获取财务分析数据 - 使用 datacenter 接口
        try:
            secucode = f"{code}.SH" if code.startswith("6") else f"{code}.SZ"
            url = f"https://datacenter.eastmoney.com/securities/api/data/get?type=RPT_F10_FINANCE_MAINFINADATA&sty=APP_F10_MAINFINADATA&quoteColumns=&filter=(SECUCODE=\"{secucode}\")&p=1&ps=6&sr=-1&st=REPORT_DATE"
            r = requests.get(url, headers=headers, timeout=settings.api.request_timeout)
            if r.status_code == 200:
                data = r.json()
                items = data.get('result', {}).get('data', [])
                
                if items:
                    fina_list = []
                    for item in items[:6]:
                        fina_list.append({
                            'end_date': item.get('REPORT_DATE_NAME', ''),
                            'roe': item.get('ROEJQ', ''),
                            'netprofit_yoy': item.get('PARENTNETPROFITTZ', ''),
                            'business_income_yoy': item.get('TOTALOPERATEREVETZ', ''),
                            'basic_eps': item.get('EPSJB', ''),
                            'total_oper_rev': item.get('TOTALOPERATEREVE', ''),
                            'npta': item.get('PARENTNETPROFIT', '')
                        })
                    if fina_list:
                        out["fina"] = pd.DataFrame(fina_list)
        except Exception:
            pass
        
        return out


# 全局数据服务实例
data_service = DataService()
