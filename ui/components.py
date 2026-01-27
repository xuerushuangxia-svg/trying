"""
UI 组件模块 - 封装 Streamlit UI 组件
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

from services.risk_analyzer import RiskAssessment
from utils.helpers import fmt_num, fmt_pct


class UIComponents:
    """UI 组件类"""
    
    @staticmethod
    def render_legal_compliance_card(assessment: RiskAssessment):
        """渲染立案调查与监管合规卡片"""
        status = assessment.legal_status
        
        if assessment.has_legal_risk:
            conclusion = "检出立案告知书，涉嫌信披违规，建议规避"
            analysis = "立案意味着实质性利空，易导致阴跌。"
        elif assessment.has_regulatory_risk:
            conclusion = "检测到监管问询，警惕财务水分"
            analysis = "监管环境平稳。"
        else:
            conclusion = "合规记录良好"
            analysis = "监管环境平稳。"
        
        st.markdown(f"""<div class="report-card {status}">
            <div class="risk-title">🚨 1-2. 立案调查与监管合规</div>
            <div class="detail-text">
                <span class="logic-tag">语义识别判定</span><br/>
                <b>结论：</b>{conclusion}<br/>
                <b>分析：</b>系统扫描近 50 条公告，识别出其合规信用等级。{analysis}
            </div>
        </div>""", unsafe_allow_html=True)
    
    @staticmethod
    def render_frequency_card(assessment: RiskAssessment, ann_text: str):
        """渲染频发风险与异动触发卡片"""
        status = assessment.frequency_status
        
        freq_msg = "近期公告发布过于频发，可能存在掩盖重大不利。" if assessment.is_high_frequency else "发布节奏平稳。"
        abnormal_msg = "已触发异常波动自查，投机氛围浓厚，随时面临监管降温。" if assessment.has_abnormal_activity else "暂无股价异动触发记录。"
        
        st.markdown(f"""<div class="report-card {status}">
            <div class="risk-title">⚠️ 3-4. 频发风险与异动触发</div>
            <div class="detail-text">
                <span class="logic-tag">公告密度与异动信号</span><br/>
                <b>判定：</b>{freq_msg}<br/>
                <b>股价异动：</b>{abnormal_msg}
            </div>
        </div>""", unsafe_allow_html=True)
    
    @staticmethod
    def render_valuation_card(assessment: RiskAssessment):
        """渲染商誉、产品技术与退市预警卡片"""
        status = assessment.valuation_status
        
        pb_msg = f"当前 PB 为 {assessment.pb_value:.2f}。"
        if assessment.pb_value > 8:
            pb_msg += "溢价极高，警惕商誉爆雷风险。"
        else:
            pb_msg += "估值处于合理安全区间。"
        
        profit_msg = "ROE或PE为负，经营持续性存疑，面临退市风险。" if assessment.has_st_risk else "盈利稳健，远离退市红线。"
        
        st.markdown(f"""<div class="report-card {status}">
            <div class="risk-title">📊 5-7. 商誉、产品技术与退市预警</div>
            <div class="detail-text">
                <span class="logic-tag">估值与资产穿透</span><br/>
                <b>商誉预警：</b>{pb_msg}<br/>
                <b>盈利能力：</b>{profit_msg}
            </div>
        </div>""", unsafe_allow_html=True)
    
    @staticmethod
    def render_financing_card(assessment: RiskAssessment):
        """渲染转融通与解禁风险卡片"""
        status = assessment.financing_status
        
        financing_msg = "检出股东参与转融通证券出借，空头抛压大。" if assessment.has_financing_risk else "近期未见大比例出借记录。"
        
        st.markdown(f"""<div class="report-card {status}">
            <div class="risk-title">🐻 8. 转融通与解禁风险</div>
            <div class="detail-text">
                <span class="logic-tag">筹码出借监控</span><br/>
                <b>转融通压力：</b>{financing_msg}<br/>
                <b>炒股人视角：</b>转融通余额增加意味着机构在做空，股价易跌难涨。
            </div>
        </div>""", unsafe_allow_html=True)
    
    @staticmethod
    def render_company_info(comp: Optional[pd.DataFrame], snap: Dict[str, Any]):
        """渲染企业基本信息"""
        with st.expander("企业基本信息与主营（点击展开）", expanded=True):
            if comp is not None and not comp.empty:
                row = comp.iloc[0].to_dict()
                st.write(f"**登记名称**: {row.get('reg_name', '-')}")
                st.write(f"**法定代表/负责人**: {row.get('chairman', '-')}")
                st.write(f"**地区**: {row.get('province', '')}{('·' + row.get('city')) if row.get('city') else ''}")
                st.write("**主营业务**:")
                st.write(row.get('main_business') or snap.get('f186') or "暂无披露")
                st.write("**公司简介**:")
                st.write(row.get('introduction') or "暂无详细介绍")
            else:
                st.write("无法从 tushare 获取公司详细信息，回退显示 EastMoney 快照：")
                st.write(snap.get('f186') or "暂无披露")
    
    @staticmethod
    def render_holders_info(holders: Optional[pd.DataFrame], float_holders: Optional[pd.DataFrame], institutions: Optional[pd.DataFrame]):
        """渲染投资人/股东信息"""
        st.subheader("👥 投资人 / 主要股东")
        
        if holders is not None and not holders.empty:
            try:
                hdf = holders.copy()
                if 'holder_name' in hdf.columns and 'hold_ratio' in hdf.columns:
                    hdf_display = hdf[['holder_name', 'hold_ratio']].rename(
                        columns={'holder_name': '投资人名称', 'hold_ratio': '持股比例(%)'}
                    )
                else:
                    hdf_display = hdf
                st.table(hdf_display.head(10))
            except Exception:
                st.write("股东数据存在非标准字段，原始数据：")
                st.write(holders.head(10))
        elif float_holders is not None and not float_holders.empty:
            st.subheader("十大流通股东（回退）")
            st.table(float_holders[['holder_name', 'hold_ratio']].rename(
                columns={'holder_name': '投资人名称', 'hold_ratio': '持股比例(%)'}
            ).head(10))
        else:
            st.info("未获取到十大股东信息。若需精确投资人名单，请确保 Tushare Token 有权访问相关接口或网络可访问东方财富。")
        
        # 机构持股
        if institutions is not None and not institutions.empty:
            st.caption("检测到的机构/企业型投资人（可能为战略合作或重要机构持股）")
            st.write(institutions[['holder_name', 'hold_ratio']].rename(
                columns={'holder_name': '名称', 'hold_ratio': '持股比例(%)'}
            ).head(6))
    
    @staticmethod
    def render_financial_snapshot(assessment: RiskAssessment, fina: Optional[pd.DataFrame]):
        """渲染基本面快照"""
        st.subheader("📈 基本面快照（近年财务指标）")
        
        # 估值快照
        st.write("**估值快照（来源：EastMoney 快照）**")
        cols = st.columns(3)
        with cols[0]:
            mkt_display = f"{assessment.market_value / 1e8:.2f}" if assessment.market_value else "—"
            st.metric("市值（亿）", mkt_display)
        with cols[1]:
            pe_display = f"{assessment.pe_value:.2f}" if assessment.pe_value else "—"
            st.metric("PE（TTM）", pe_display)
        with cols[2]:
            pb_display = f"{assessment.pb_value:.2f}" if assessment.pb_value else "—"
            st.metric("PB", pb_display)
        
        st.write("---")
        
        # 财务指标表格
        if fina is not None and not fina.empty:
            UIComponents._render_fina_table(fina)
        else:
            st.info("未能获取到 fina_indicator 数据。若需更多财务期表请确保 Tushare Token 有相应权限。")
    
    @staticmethod
    def _render_fina_table(fina: pd.DataFrame):
        """渲染财务指标表格"""
        df_f = fina.copy()
        
        # 识别报告期列
        date_col = None
        for cand in ['end_date', 'report_date', 'ann_date', 'pub_date']:
            if cand in df_f.columns:
                date_col = cand
                break
        if date_col is None:
            date_col = df_f.columns[0]
        
        # 列映射
        mapping = {
            date_col: "报告期",
            'total_oper_rev': "营业收入",
            'business_income_yoy': "收入同比",
            'npta': "归母净利润",
            'netprofit_yoy': "净利同比",
            'roe': "ROE",
            'basic_eps': "每股收益",
            'roe_avg': "平均ROE"
        }
        
        want = [k for k in mapping.keys() if k in df_f.columns]
        display_cols = [date_col] + [c for c in want if c != date_col][:6]
        view = df_f[display_cols].head(6).copy()
        view = view.rename(columns=mapping)
        
        # 格式化数值
        for col in view.columns:
            if any(x in col.lower() for x in ['同比', 'yoy', 'roe']):
                view[col] = view[col].apply(lambda v: fmt_pct(v) if pd.notna(v) else "-")
            else:
                view[col] = view[col].apply(lambda v: fmt_num(v) if pd.notna(v) else "-")
        
        st.write("最近若干期财务指标：")
        st.dataframe(view.set_index("报告期"))
        
        # 关键指标高亮
        sample = df_f.iloc[0].to_dict()
        highlights = []
        if 'roe' in sample:
            highlights.append(("ROE", fmt_pct(sample.get('roe'))))
        if 'netprofit_yoy' in sample:
            highlights.append(("净利同比", fmt_pct(sample.get('netprofit_yoy'))))
        if 'business_income_yoy' in sample:
            highlights.append(("收入同比", fmt_pct(sample.get('business_income_yoy'))))
        if 'npta' in sample:
            highlights.append(("归母净利润", fmt_num(sample.get('npta'))))
        if 'basic_eps' in sample:
            highlights.append(("基本每股收益", fmt_num(sample.get('basic_eps'))))
        
        if highlights:
            st.write("关键财务指标：")
            for k, v in highlights:
                st.write(f"- **{k}**: {v}")
    
    @staticmethod
    def render_partners(partners: List[str]):
        """渲染合作公司信息"""
        with st.expander("🔗 合作公司 / 参股及业务伙伴（若有公开披露）"):
            if partners:
                st.write("自动解析到的可能合作方（需人工核验）:")
                for p in partners:
                    st.write(f"- {p}")
            else:
                st.write("未从公开简介中解析到明确的合作方。若需要精确合作/参股关系，请使用公司年报/披露或企业关系数据库进行查询。")
    
    @staticmethod
    def render_peer_recommendations(index_df: pd.DataFrame, industry: str, target_code: str):
        """渲染同行业推荐"""
        st.markdown("---")
        st.subheader("💡 智能关联推荐 (同行业风险对标分析)")
        
        if not index_df.empty and industry:
            peers = index_df[index_df['industry'] == industry].head(5)
            if not peers.empty:
                cols = st.columns(4)
                count = 0
                for _, row in peers.iterrows():
                    if row['symbol'] == target_code:
                        continue
                    if count >= 4:
                        break
                    with cols[count]:
                        st.info(f"**{row['name']}**\n\n{row['symbol']}")
                    count += 1
