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
        """从东方财富获取股票列表（使用 datacenter API，只获取 A 股最新数据）"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://data.eastmoney.com/'
        }
        
        all_data = []
        page = 1
        max_pages = 15  # 最多请求15页，约7500条，足够覆盖所有A股
        
        # 使用 datacenter-web API，筛选 A 股（SECURITY_TYPE_CODE=058001001）+ 最新数据（ISNEW=1）
        while page <= max_pages:
            url = f'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=SECURITY_CODE,SECURITY_NAME_ABBR&filter=(ISNEW="1")(SECURITY_TYPE_CODE="058001001")&pageSize=500&pageNumber={page}&sortColumns=SECURITY_CODE&sortTypes=1'
            try:
                r = requests.get(url, timeout=15, headers=headers)
                if r.status_code == 200:
                    result = r.json().get('result', {})
                    data = result.get('data', [])
                    if not data:
                        break
                    all_data.extend(data)
                    # 检查是否还有更多页
                    total = result.get('count', 0)
                    if len(all_data) >= total:
                        break
                    page += 1
                else:
                    break
            except Exception as e:
                print(f"API请求失败: {e}")
                break
        
        if all_data:
            df = pd.DataFrame(all_data)
            # 转换列名
            df = df.rename(columns={
                'SECURITY_CODE': 'symbol',
                'SECURITY_NAME_ABBR': 'name',
                'TRADE_MARKET_CODE': 'market'
            })
            df['industry'] = ''
            df['symbol'] = df['symbol'].astype(str).str.strip()
            df['name'] = df['name'].astype(str).str.strip()
            df['label'] = df['symbol'] + " | " + df['name']
            df['name_lower'] = df['name'].str.lower()
            df['search'] = df['symbol'].str.lower() + " " + df['name_lower']
            return df[['symbol', 'name', 'industry', 'label', 'name_lower', 'search']]
        
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
        """获取风险相关数据（使用 datacenter-web API）"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://data.eastmoney.com/'
        }
        snap = {}
        anns = []
        
        try:
            # 使用 datacenter-web API 获取财务/基本面快照
            url = f'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE="{code}")&pageSize=1'
            r1 = requests.get(url, timeout=settings.api.request_timeout, headers=headers)
            
            if r1.status_code == 200:
                data = r1.json().get('result', {}).get('data', [])
                if data:
                    item = data[0]
                    # 转换为与原来接口类似的格式（f字段）
                    snap = {
                        'f58': item.get('SECURITY_NAME_ABBR', ''),  # 股票名称
                        'f167': 0,  # 市盈率（该接口无此字段，后续从别处补充）
                        'f116': item.get('TOTAL_OPERATE_INCOME', 0),  # 营业总收入代替总市值
                        'f127': item.get('YSTZ', 0),  # 营收同比增速
                        'f186': item.get('WEIGHTAVG_ROE', 0),  # 加权ROE
                        'f114': item.get('SJLTZ', 0),  # 净利润同比
                        'f117': item.get('XSMLL', 0),  # 毛利率
                        # 额外保存原始数据供后续使用
                        '_basic_eps': item.get('BASIC_EPS', 0),  # 每股收益
                        '_bps': item.get('BPS', 0),  # 每股净资产
                        '_industry': item.get('PUBLISHNAME', ''),  # 所属行业
                    }
            
            # 公告扫描（该接口通常仍可用）
            try:
                r2 = requests.get(
                    f"{settings.api.eastmoney_announcement_url}?sr=-1&page_size={settings.announcement_limit}&page_index=1&stock_list={code}",
                    timeout=settings.api.request_timeout,
                    headers=headers
                )
                if r2.status_code == 200:
                    anns = r2.json().get('data', {}).get('list', []) or []
            except Exception:
                anns = []
            
            return snap, anns
        except Exception as e:
            print(f"fetch_risk_data error: {e}")
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
