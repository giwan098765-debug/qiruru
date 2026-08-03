import sys
import time
import sqlite3
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import FinanceDataReader as fdr
import google.generativeai as genai
import streamlit as st

# 💥 [최상단 필수] Streamlit 설정은 코드 가장 처음에 위치해야 합니다.
st.set_page_config(
    page_title="PRO QUANT 스윙 트레이더",
    page_icon="🔥",
    layout="wide"
)

# --- [DB 초기화] ---
DB_FILE = "rec_history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS my_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_name TEXT,
        ticker TEXT,
        entry_price REAL,
        entry_date TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- [기본 자산 목록] ---
ASSETS = {
    "₩ 국내 주식": {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS",
        "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
        "셀트리온": "068270.KS", "KB금융": "105560.KS", "NAVER": "035420.KS"
    },
    "💲 미국 주식": {
        "엔비디아": "NVDA", "애플": "AAPL", "마이크로소프트": "MSFT",
        "아마존": "AMZN", "알파벳(구글)": "GOOGL", "메타": "META", "테슬라": "TSLA"
    },
    "🪙 암호화폐(코인)": {
        "비트코인": "BTC-KRW", "이더리움": "ETH-KRW", "리플": "XRP-KRW", "솔라나": "SOL-KRW"
    }
}

# --- [데이터 수집 함수] ---
@st.cache_data(ttl=1800)
def get_stock_data(ticker):
    try:
        if ticker.endswith('-KRW'):
            coin_symbol = ticker.split('-')[0]
            url = "https://api.upbit.com/v1/candles/days"
            res = requests.get(url, params={"market": f"KRW-{coin_symbol}", "count": 200}, timeout=5)
            if res.status_code == 200:
                df = pd.DataFrame(res.json()).iloc[::-1].reset_index(drop=True)
                df = df.rename(columns={'candle_date_time_kst': 'Date', 'opening_price': 'Open',
                                        'high_price': 'High', 'low_price': 'Low',
                                        'trade_price': 'Close', 'candle_acc_trade_volume': 'Volume'})
                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        clean_ticker = ticker.split('.')[0]
        if ticker.endswith('.KS') or ticker.endswith('.KQ') or clean_ticker.isdigit():
            df = fdr.DataReader(clean_ticker, start='2024-01-01').reset_index()
            df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        df = yf.download(ticker, period="1y", progress=False).reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception:
        return None

# --- [메인 레이아웃] ---
st.title("🔥 PRO QUANT 스윙 트레이더")

st.sidebar.markdown("### 🔍 종목 탐색기")
sector = st.sidebar.radio("📁 섹터 선택", list(ASSETS.keys()))

selected_name = st.sidebar.selectbox("🎯 종목명", list(ASSETS[sector].keys()))
safe_ticker = ASSETS[sector][selected_name]

api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password")

if safe_ticker:
    df = get_stock_data(safe_ticker)
    if df is not None and not df.empty:
        # 차트 그리기
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
                            subplot_titles=(f"[{selected_name}] 주가 및 이동평균선", "거래량"))

        fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'],
                                     low=df['Low'], close=df['Close'], name="주가"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MA5'], line=dict(color='#FF1493', width=1), name="5일선"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], line=dict(color='#00E676', width=1.5), name="20일선"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MA60'], line=dict(color='#AB47BC', width=2), name="60일선"), row=1, col=1)
        
        fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name="거래량"), row=2, col=1)

        fig.update_layout(template="plotly_dark", height=600, showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # AI 브리핑
        if api_key:
            if st.button("🔍 Gemini AI 차트 분석 듣기"):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    curr_p = df['Close'].iloc[-1]
                    prompt = f"종목: {selected_name}, 현재가: {curr_p}. 이 종목의 단기 스윙 전략을 3줄로 핵심만 요약해줘."
                    res = model.generate_content(prompt)
                    st.success(res.text)
                except Exception as e:
                    st.error(f"AI 분석 중 오류 발생: {e}")
    else:
        st.warning("데이터를 불러오는 중입니다. 잠시 후 다시 시도해 주세요.")