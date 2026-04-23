import pandas as pd
import google.generativeai as genai
import json
import time
import logging
import streamlit as st
from config import MODEL_NAME, TEMPERATURE, COST_PER_INPUT_TOKEN, COST_PER_OUTPUT_TOKEN
import os
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score, f1_score
from fpdf import FPDF
import base64
import textwrap
import re

os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("app_runtime")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler("logs/app_runtime.log")
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(fh)

def get_valid_model(api_key):
    """Identifies the best available Gemini model while avoiding restricted models like 2.5-pro."""
    try:
        genai.configure(api_key=api_key)
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # EXCLUSION LIST: Some experimental models (like 2.5-pro) have '0' quota for free users
        blacklist = ["2.5-pro"]
        safe_models = [m for m in available if not any(b in m for b in blacklist)]
        
        # Priority 1: Flash 1.5 variants (Most reliable for Free Tier)
        flash_priority = ["1.5-flash-latest", "1.5-flash-002", "1.5-flash-001", "1.5-flash"]
        for p in flash_priority:
            match = [m for m in safe_models if p in m]
            if match: return match[0]
            
        # Priority 2: Flash 1.0 or other Flash variants
        flash_any = [m for m in safe_models if "flash" in m.lower()]
        if flash_any: return flash_any[0]
        
        # Priority 3: Pro 1.5 stable (if available)
        pro_priority = ["1.5-pro-latest", "1.5-pro"]
        for p in pro_priority:
            match = [m for m in safe_models if p in m]
            if match: return match[0]
            
        if safe_models: return safe_models[0]
        return "models/gemini-1.5-flash"
    except Exception as e:
        logger.error(f"Discovery Error: {str(e)}")
        return "models/gemini-1.5-flash"

@st.cache_data(show_spinner=False)
def process_data(df_raw: pd.DataFrame, target_col: str = None) -> tuple[dict, pd.DataFrame]:
    df = df_raw.copy().fillna(0)
    num_df = df.select_dtypes(include='number')
    if num_df.empty: raise ValueError("No numeric data found.")
    if not target_col or target_col not in num_df.columns: target_col = num_df.columns[0]
    
    mean, std = df[target_col].mean(), df[target_col].std()
    anomalies = df[np.abs(df[target_col] - mean) > (2 * std)] if std > 0 else pd.DataFrame()
    
    X = num_df.drop(columns=[target_col])
    X = X[[c for c in X.columns if 'id' not in c.lower() and X[c].nunique() > 1]]
    y = df[target_col]
    
    ml = {"confidence": 0.0, "reason": "Insufficient data"}
    if not X.empty and len(df) > 5:
        rf = RandomForestRegressor(n_estimators=50, random_state=42)
        rf.fit(X, y)
        y_pred = rf.predict(X)
        r2 = rf.score(X, y)
        ml = {
            "confidence": round(min(max(r2, 0.0), 0.999), 3),
            "r2": round(float(r2), 3),
            "mae": round(float(mean_absolute_error(y, y_pred)), 2),
            "rmse": round(float(np.sqrt(mean_squared_error(y, y_pred))))
        }

    date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'year', 'month'])]
    time_axis = date_cols[0] if date_cols else df.columns[0]
    df_ts = df.copy()
    if date_cols:
        try:
            df[time_axis] = pd.to_datetime(df[time_axis])
            df_ts = df.set_index(time_axis).resample('ME').sum().reset_index()
        except: pass

    df_ts['Cumulative'] = df_ts[target_col].cumsum()
    growth = 0
    if len(df_ts) > 1:
        start, end = df_ts[target_col].iloc[0], df_ts[target_col].iloc[-1]
        growth = round(((end - start) / start * 100), 2) if start != 0 else 0
        
    forecast = []
    if len(df_ts) > 2:
        z = np.polyfit(np.arange(len(df_ts)), df_ts[target_col].values, 1)
        p = np.poly1d(z)
        forecast = [round(float(p(len(df_ts)+i)), 2) for i in range(3)]

    analytics = {
        "overview": {"rows": len(df), "cols": len(df.columns), "target": target_col, "total": round(float(y.sum()), 2), "growth": growth},
        "pulse": {"anomalies_count": len(anomalies), "trend": "Upward" if growth > 5 else ("Downward" if growth < -5 else "Stable")},
        "ml": ml,
        "forecast": forecast,
        "time_axis": str(time_axis)
    }
    return analytics, df_ts

def generate_insights(metrics: dict, api_key: str, model_override: str = None) -> tuple[dict, str]:
    try:
        genai.configure(api_key=api_key)
        # Use override if provided, else use discovery
        target_model = model_override if model_override else get_valid_model(api_key)
        model = genai.GenerativeModel(target_model, generation_config={"response_mime_type": "application/json"})
        prompt = f"Act as a Strategist. Data: {json.dumps(metrics)}. JSON: key_insights, forecasting_narrative, strategic_advice_detailed, risk_assessment, comprehensive_conclusion."
        resp = model.generate_content(prompt)
        res = json.loads(resp.text)
        
        for key in ["key_insights", "forecasting_narrative", "strategic_advice_detailed", "risk_assessment"]:
            if isinstance(res.get(key), str): res[key] = [res[key]]
        return res, "Success"
    except Exception as e:
        return {"key_insights": [f"AI Error: {str(e)}"]}, str(e)

def ask_ai_assistant(query: str, context: dict, api_key: str, model_override: str = None):
    try:
        genai.configure(api_key=api_key)
        target_model = model_override if model_override else get_valid_model(api_key)
        model = genai.GenerativeModel(target_model)
        resp = model.generate_content(f"Context: {json.dumps(context)}\nQuestion: {query}")
        return resp.text
    except Exception as e: return f"Offline: {str(e)}"

def create_pdf_report(analytics, insights):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "EXECUTIVE STRATEGIC AUDIT", ln=True, align="C")
    sections = [
        ("1. Overview", f"Growth: {analytics['overview']['growth']}%, Total: {analytics['overview']['total']}"),
        ("2. Insights", "\n".join(insights.get('key_insights', []))),
        ("3. Conclusion", insights.get('comprehensive_conclusion', 'N/A'))
    ]
    for t, c in sections:
        pdf.set_font("helvetica", "B", 12); pdf.cell(0, 10, t, ln=True)
        pdf.set_font("helvetica", "", 10); pdf.multi_cell(0, 7, str(c))
    return pdf.output()
