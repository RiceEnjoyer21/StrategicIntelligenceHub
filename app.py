import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import google.generativeai as genai
from analyzer import process_data, generate_insights, ask_ai_assistant, create_pdf_report
from config import get_api_key

st.set_page_config(page_title="Strategic Insight Engine", page_icon="🏢", layout="wide")

# Persistent State
if 'history' not in st.session_state: st.session_state.history = []
if 'analysis' not in st.session_state: st.session_state.analysis = None
if 'api_key' not in st.session_state: st.session_state.api_key = get_api_key()
if 'api_verified' not in st.session_state: st.session_state.api_verified = False
if 'available_models' not in st.session_state: st.session_state.available_models = []
if 'selected_model' not in st.session_state: st.session_state.selected_model = None

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .chapter-header { background: #0f172a; color: white; padding: 1.2rem 2.5rem; border-radius: 16px; margin: 2rem 0 1rem 0; font-weight: 700; }
    .metric-card { background: white; padding: 24px; border-radius: 20px; border: 1px solid #f1f5f9; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

def kpi_card(label, value):
    st.markdown(f"""<div class="metric-card"><div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">{label}</div><div style="font-size:1.8rem; color:#0f172a; font-weight:800;">{value}</div></div>""", unsafe_allow_html=True)

def render_list(data_list):
    if not data_list: return
    if isinstance(data_list, str): data_list = [data_list]
    for item in data_list:
        if "Risk" in str(item) or "Warning" in str(item): st.warning(item)
        else: st.info(item)

def main():
    st.title("🛰️ Strategic Intelligence Hub")
    
    with st.sidebar:
        st.header("🔑 Authentication")
        user_key = st.text_input("Gemini API Key", value=st.session_state.api_key or "", type="password")
        if st.button("Verify & List Models", use_container_width=True):
            try:
                genai.configure(api_key=user_key)
                # Filter out experimental/restricted models that cause 429s
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                blacklist = ["2.5-pro"]
                st.session_state.available_models = [m for m in models if not any(b in m for b in blacklist)]
                st.session_state.api_verified, st.session_state.api_key = True, user_key
                st.success("API_KEY_VALID")
            except Exception as e: st.error(f"API Error: {str(e)}")
        
        if st.session_state.api_verified and st.session_state.available_models:
            st.divider()
            st.header("🤖 Model Selection")
            st.session_state.selected_model = st.selectbox("Choose AI Model", st.session_state.available_models, 
                                                           index=0 if "flash" in str(st.session_state.available_models[0]).lower() else 0)
            st.caption("Flash models are recommended for Free Tier stability.")

        st.divider()
        st.header("📂 Data Center")
        uploaded_file = st.file_uploader("Business Dataset (CSV)", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            target = st.selectbox("Strategic Target", df.select_dtypes(include='number').columns)
            if st.button("🚀 Execute Analysis", use_container_width=True):
                st.cache_data.clear()
                analytics, df_ts = process_data(df, target)
                # Pass the selected model to the engine
                insights, err = generate_insights(analytics, st.session_state.api_key, model_override=st.session_state.selected_model) if st.session_state.api_verified else (None, "Key not verified")
                st.session_state.analysis = (analytics, df_ts, insights, err)
                st.session_state.history.append({"time": time.strftime("%H:%M"), "target": target, "growth": analytics['overview']['growth']})

        if st.session_state.history:
            st.divider(); st.header("📜 History")
            for h in reversed(st.session_state.history): st.markdown(f"**{h['time']}**: {h['target']} ({h['growth']}%)")

    if st.session_state.analysis:
        analytics, df_ts, insights, ai_err = st.session_state.analysis
        ov = analytics.get('overview', {})
        
        st.markdown("<div class='chapter-header'>CHAPTER 1: BUSINESS OVERVIEW & KPI DASHBOARD</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("Total Value", f"${ov.get('total', 0):,.0f}")
        with c2: kpi_card("Growth Rate", f"{ov.get('growth', 0)}%")
        with c3: kpi_card("Data Rows", ov.get('rows', 0))
        with c4: kpi_card("Target Metric", ov.get('target', 'N/A'))

        st.markdown("<div class='chapter-header'>CHAPTER 2: PERFORMANCE PULSE</div>", unsafe_allow_html=True)
        ps = analytics.get('pulse', {})
        st.info(f"Market Trajectory: **{ps.get('trend')}** | Anomalies Detected: **{ps.get('anomalies_count')}**")

        st.markdown("<div class='chapter-header'>CHAPTER 3: VISUAL ANALYTICS LAYER</div>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["📉 Trend & Distribution", "📈 Cumulative Growth", "🧬 Correlation Map"])
        with t1:
            col_t1, col_t2 = st.columns(2)
            with col_t1: st.plotly_chart(px.line(df_ts, x=analytics.get('time_axis'), y=ov.get('target')), use_container_width=True)
            with col_t2: st.plotly_chart(px.histogram(df_ts, x=ov.get('target')), use_container_width=True)
        with t2: st.plotly_chart(px.area(df_ts, x=analytics.get('time_axis'), y="Cumulative"), use_container_width=True)
        with t3:
            num_df = df_ts.select_dtypes(include='number')
            if len(num_df.columns) > 1: st.plotly_chart(px.imshow(num_df.corr(), text_auto=True), use_container_width=True)

        st.markdown("<div class='chapter-header'>CHAPTER 4: AI INSIGHTS ENGINE (DETAILED)</div>", unsafe_allow_html=True)
        if insights:
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                st.subheader("💡 Key Insights")
                render_list(insights.get('key_insights', []))
            with col_i2:
                st.subheader("🔮 Forecasting Narrative")
                render_list(insights.get('forecasting_narrative', []))
        else: st.error(f"AI Connection Blocked: {ai_err}")

        st.markdown("<div class='chapter-header'>CHAPTER 5: STRATEGIC ADVICE & RISK ASSESSMENT</div>", unsafe_allow_html=True)
        if insights:
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.subheader("🚀 Detailed Recommendations")
                render_list(insights.get('strategic_advice_detailed', []))
            with col_s2:
                st.subheader("⚠️ Risk Assessment")
                render_list(insights.get('risk_assessment', []))
        
        st.markdown("<div class='chapter-header'>CHAPTER 6: FORECASTING & MODEL AUDIT</div>", unsafe_allow_html=True)
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            if analytics.get('forecast'):
                hist_vals = df_ts[ov.get('target')].tolist()
                full_vals = hist_vals + analytics['forecast']
                full_axis = list(range(len(full_vals)))
                fig_f = go.Figure()
                fig_f.add_trace(go.Scatter(x=full_axis[:len(hist_vals)], y=hist_vals, name="Historical", line=dict(color='#0f172a')))
                fig_f.add_trace(go.Scatter(x=full_axis[len(hist_vals)-1:], y=[hist_vals[-1]] + analytics['forecast'], name="Forecast", line=dict(color='#3b82f6', dash='dot')))
                st.plotly_chart(fig_f, use_container_width=True)
        with col_f2:
            st.subheader("📊 Evaluation Metrics")
            ml = analytics.get('ml', {})
            st.markdown(f"**Confidence:** `{ml.get('confidence', 0)*100:.1f}%` | **R²:** `{ml.get('r2', 0)}`")

        st.markdown("<div class='chapter-header'>CHAPTER 7: COMPREHENSIVE STRATEGIC CONCLUSION</div>", unsafe_allow_html=True)
        if insights: st.markdown(f"""<div style="background:white; padding:30px; border-radius:15px; border:1px solid #e2e8f0;">{insights.get('comprehensive_conclusion', 'N/A')}</div>""", unsafe_allow_html=True)
        
        st.divider()
        pdf = create_pdf_report(analytics, insights if insights else {})
        st.download_button("📥 Download PDF Report", data=bytes(pdf), file_name="Executive_Audit.pdf")

    else: st.markdown("<div style='text-align: center; padding: 150px;'><h1>🛰️ Hub Offline</h1><p>Ingest data to begin the structured sequence.</p></div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
