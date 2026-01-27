"""
工具函数模块
"""
import pandas as pd
from typing import Any, Callable, Optional

import streamlit as st


def get_cache_decorator(ttl: Optional[int] = None) -> Callable:
    """
    获取缓存装饰器，兼容不同版本的 Streamlit
    """
    if hasattr(st, "cache_data"):
        return st.cache_data(ttl=ttl)
    else:
        return st.cache


def fmt_num(x: Any) -> str:
    """格式化数字"""
    try:
        if pd.isna(x):
            return "-"
        x = float(x)
        if abs(x) >= 1e4:
            return f"{x:,.0f}"
        return f"{x:,.2f}"
    except Exception:
        return str(x)


def fmt_pct(x: Any) -> str:
    """格式化百分比"""
    try:
        if pd.isna(x):
            return "-"
        v = float(x)
        # 若为 0~1 小数，认为是小数表示，乘 100 显示为百分比
        if abs(v) < 5 and abs(v) <= 1.5:
            return f"{v * 100:.2f}%"
        return f"{v:.2f}%"
    except Exception:
        return str(x)
