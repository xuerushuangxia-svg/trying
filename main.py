"""
XUE 风险全维度穿透终端 - 主程序入口
"""
import streamlit as st

from config.settings import settings
from services.data_service import data_service
from services.risk_analyzer import risk_analyzer
from ui.styles import CUSTOM_CSS
from ui.components import UIComponents


def setup_page():
    """设置页面配置"""
    st.set_page_config(page_title=settings.app_title, layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_sidebar() -> str:
    """渲染侧边栏并返回选中的股票代码"""
    st.sidebar.title("📡 穿透控制中心")
    
    # 加载股票索引
    index_df = data_service.load_full_index()
    
    # 搜索输入
    query = st.sidebar.text_input(
        "输入代码或名称搜索（回车即筛选）", 
        value=settings.default_stock_code
    )
    
    # 搜索结果
    results = data_service.search_stocks(query, limit=settings.search_limit) if index_df is not None else None
    
    if results is not None and not results.empty:
        options = results['label'].tolist()
        # 尝试找到精确匹配项
        default_idx = 0
        try:
            default_idx = next(
                i for i, lab in enumerate(options) 
                if lab.lower().startswith(query.lower())
            )
        except StopIteration:
            default_idx = 0
        
        selected = st.sidebar.selectbox(
            "搜索/联想 A 股代码或名称", 
            options, 
            index=default_idx
        )
        target_code = selected.split(" | ")[0]
    else:
        target_code = st.sidebar.text_input(
            "未找到候选，请手动输入代码", 
            value=settings.default_stock_code
        )
    
    return target_code, index_df


def render_risk_report(target_code: str, index_df):
    """渲染风险报告"""
    # 获取数据
    snap, anns = data_service.fetch_risk_data(target_code)
    extras = data_service.fetch_extra_details(target_code)
    
    if not snap:
        st.error("🚨 信号解调失败：物理链路由于网络环境限制而阻塞。请检查东方财富网是否可以正常打开。")
        return
    
    # 分析风险
    anns = anns or []
    assessment = risk_analyzer.analyze(snap, anns)
    ann_text = "".join([a.get('title', '') for a in anns if isinstance(a, dict)])
    
    # 渲染标题
    stock_name = snap.get('f58', '')
    st.title(f"🔍 {stock_name} ({target_code}) 深度风险穿透报告")
    
    # 第一排：监管、合规与异动
    c1, c2 = st.columns(2)
    with c1:
        UIComponents.render_legal_compliance_card(assessment)
    with c2:
        UIComponents.render_frequency_card(assessment, ann_text)
    
    # 第二排：资产质量与 ST 退市
    c3, c4 = st.columns(2)
    with c3:
        UIComponents.render_valuation_card(assessment)
    with c4:
        UIComponents.render_financing_card(assessment)
    
    # 企业背景部分
    st.markdown("---")
    st.subheader("🏛️ 企业背景 / 合作公司 / 投资人 / 基本面")
    
    comp = extras.get("company")
    UIComponents.render_company_info(comp, snap)
    
    # 两列布局：投资人和基本面
    col_a, col_b = st.columns(2)
    
    with col_a:
        holders = extras.get("holders")
        float_holders = extras.get("float_holders")
        institutions = risk_analyzer.detect_institutional_holders(holders)
        UIComponents.render_holders_info(holders, float_holders, institutions)
    
    with col_b:
        fina = extras.get("fina")
        UIComponents.render_financial_snapshot(assessment, fina)
    
    # 合作公司
    comp_text = None
    if comp is not None and not comp.empty:
        comp_text = comp.iloc[0].get('main_business') or comp.iloc[0].get('introduction')
    if not comp_text:
        comp_text = snap.get('f186') or ""
    partners = risk_analyzer.extract_partners(comp_text)
    UIComponents.render_partners(partners)
    
    # 同行业推荐
    industry = snap.get('f127')
    UIComponents.render_peer_recommendations(index_df, industry, target_code)


def main():
    """主函数"""
    setup_page()
    target_code, index_df = render_sidebar()
    render_risk_report(target_code, index_df)


if __name__ == "__main__":
    main()
