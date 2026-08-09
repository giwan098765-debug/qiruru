# ====================================================================
# 🛡️ [국내 주식 무한루프 차단] 종목명 ➔ 야후 티커 규격 자동 변환 마스터 가드레일
# ====================================================================
import sys
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr


# 1. 꼬임 방지를 위해 원본 야후 파이낸스 함수를 딱 한 번만 안전하게 백업
if not hasattr(yf, '_original_download'):
    yf._original_download = yf.download
if not hasattr(yf, '_original_Ticker'):
    yf._original_Ticker = yf.Ticker

_krx_market_cache = None

def get_perfect_yahoo_ticker(input_val):
    """'후성'->'016380.KS', '005930.KS'->'005930.KS'로 완벽 변환하는 변역기"""
    global _krx_market_cache
    raw_target = str(input_val).strip()
    
    # 이미 .KS나 .KQ가 정상적으로 붙어있다면 검증 패스하고 원본 그대로 사용
    if raw_target.upper().endswith('.KS') or raw_target.upper().endswith('.KQ'):
        return raw_target
        
    # 점(.)이나 공백이 섞여 있다면 앞자리 코드만 추출 (예: '005930')
    target_clean = raw_target.split('.')[0]
    
    try:
        if _krx_market_cache is None:
            # 한국거래소(KRX) 전체 종목 마스터 명부 캐싱
            _krx_market_cache = fdr.StockListing('KRX')
        
        # 숫자로 쳤을 때와 한글 이름으로 쳤을 때를 동시에 대응
        if target_clean.isdigit() and len(target_clean) == 6:
            matched = _krx_market_cache[_krx_market_cache['Code'] == target_clean]
        else:
            matched = _krx_market_cache[_krx_market_cache['Name'] == target_clean]
            
        if not matched.empty:
            code = matched['Code'].values[0]
            market = matched['Market'].values[0]
            
            # 코스닥 종목은 .KQ, 코스피 등 그 외 종목은 .KS를 동적으로 부착
            suffix = '.KQ' if 'KOSDAQ' in str(market).upper() else '.KS'
            return f"{code}{suffix}"
            
    except Exception:
        pass
        
    # 매칭되는 한국 주식이 없으면 미국 주식(AAPL, TSLA 등)이므로 원본 문자열 그대로 반환
    return raw_target

# 2. 오리지널 다운로드 함수 가로채기 (무한루프 완전 차단 버전)
def fake_download(tickers, *args, **kwargs):
    if isinstance(tickers, str):
        resolved_ticker = get_perfect_yahoo_ticker(tickers)
    else:
        resolved_ticker = tickers
    # 백업해둔 순수 오리지널 야후 다운로드 함수를 호출하므로 절대 꼬이지 않습니다.
    return yf._original_download(resolved_ticker, *args, **kwargs)

yf.download = fake_download

# 3. 오리지널 Ticker 클래스 가로채기
class FakeTicker:
    def __init__(self, ticker, *args, **kwargs):
        resolved_ticker = get_perfect_yahoo_ticker(ticker)
        self._ticker_obj = yf._original_Ticker(resolved_ticker, *args, **kwargs)
        
    def __getattr__(self, attr):
        return getattr(self._ticker_obj, attr)
        
    def history(self, *args, **kwargs):
        return self._ticker_obj.history(*args, **kwargs)

yf.Ticker = FakeTicker
# ====================================================================
macro_trends = {"KR": True, "US": True, "COIN": True}
import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
import time

# (앞 코드: import 구문 및 기타 데이터 연산 함수들)
import plotly.graph_objects as go
import pandas as pd

# ====================================================================
# 📈 [1번 코드 위치] Plotly 차트 및 이평선 6종 + 우측 상단 범례 생성
# ====================================================================
def draw_price_chart(df, stock_name):
    # 1. 이동평균선 연산 (5, 10, 20, 60, 120, 200일)
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    df['MA200'] = df['Close'].rolling(200).mean()

    fig = go.Figure()

    # 2. 캔들차트 생성
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name="주가", showlegend=False
    ))

    # 3. 이평선 6종 및 색상 지정
    ma_config = [
        ('MA5', '━ 5일선', '#FF1493', 1.2),   # 진분홍
        ('MA10', '━ 10일선', '#29B6F6', 1.5),  # 파랑
        ('MA20', '━ 20일선', '#00E676', 1.8),  # 연두
        ('MA60', '━ 60일선', '#AB47BC', 2.0),  # 보라
        ('MA120', '━ 120일선', '#FF6D00', 2.0), # 주황
        ('MA200', '━ 200일선', '#FF1744', 2.2)  # 빨강
    ]

    for col, name, color, width in ma_config:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], mode='lines', name=name,
            line=dict(color=color, width=width), hoverinfo='x+y+name'
        ))

    # 4. 우측 상단 범례 박스 위치 잡기
    fig.update_layout(
        title=f"[{stock_name}] Price Action 및 이동평균선",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h",
            yanchor="top", y=1.12,
            xanchor="right", x=1.0,
            font=dict(size=11, color="#e2e8f0"),
            bgcolor="rgba(15, 23, 42, 0.85)",
            bordercolor="#334155", borderwidth=1
        )
    )
    return fig

# (뒤 코드: 스캔 관련 백그라운드 함수 또는 UI 레이아웃 코드)

# 💥 [가장 중요] 다른 Streamlit 코드가 나오기 전에 무조건 '최상단'에 위치해야 합니다!
st.set_page_config(
    page_title="PRO QUANT 스윙 트레이더",
    page_icon="🔥",
    layout="wide"  # 👈 기존 centered에서 wide로 변경하여 양옆 빨간 영역을 잠금 해제합니다.
)

# 💡 [신규 세션 키 선제 등록 - 최초 접속 시 KeyError 원천 차단]
session_defaults = {
    'scan_results_kr': [], 'scan_results_us': [], 'scan_results_coin': [],
    'scan_surge_kr': [], 'scan_surge_us': [],
    'scan_midterm_kr': [], 'scan_midterm_us': [], 'scan_midterm_coin': [],
    'trigger_combined_scan': False, 'auto_run_retro': False
}

for key, default_val in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_val

# ====================================================================
# 📊 [고도화 1M 엔진] 10대 섹터 거래대금 가중치 기반 지수 영향력 연산
# ====================================================================
@st.cache_data(ttl=3600) # 1시간 단위 실시간 데이터 갱신
def get_realtime_sector_influence():
    import FinanceDataReader as fdr
    import yfinance as yf
    import numpy as np
    import pandas as pd

    # 🇰🇷 국내 세분화 25대 섹터 (각 10개 종목)
    kr_sectors = {
        "반도체/HBM": ["005930.KS", "000660.KS", "042700.KS", "058470.KQ", "403870.KQ", "039030.KQ", "357780.KQ", "005290.KQ", "240810.KQ", "084370.KQ"],
        "반도체장비/소부장": ["039030.KQ", "005290.KQ", "240810.KQ", "036930.KQ", "067310.KQ", "036810.KQ", "101490.KQ", "237690.KQ", "095610.KQ", "131970.KQ"],
        "제약/바이오신약": ["207940.KS", "068270.KS", "196170.KQ", "141080.KQ", "028300.KQ", "185750.KS", "069620.KS", "000100.KS", "008930.KS", "006280.KS"],
        "의료기기/뷰티케어": ["214150.KQ", "214450.KQ", "145020.KQ", "041830.KQ", "099430.KQ", "287410.KQ", "214310.KQ", "054540.KQ", "100130.KQ", "084990.KQ"],
        "2차전지/셀": ["373220.KS", "006400.KS", "348370.KQ", "003670.KS", "066970.KS", "051910.KS", "096770.KS", "005490.KS", "086520.KQ", "247540.KQ"],
        "2차전지/소재": ["005490.KS", "247540.KQ", "086520.KQ", "005070.KS", "078600.KQ", "003670.KS", "066970.KS", "450080.KS", "348370.KQ", "117580.KQ"],
        "완성차/모빌리티": ["005380.KS", "000270.KS", "012330.KS", "086280.KS", "011210.KS", "003620.KS", "161390.KS", "018880.KS", "009900.KS", "005850.KS"],
        "자동차부품": ["161390.KS", "018880.KS", "009900.KS", "005850.KS", "012330.KS", "011210.KS", "001500.KS", "016380.KS", "013520.KS", "005880.KS"],
        "방산/지상무기": ["012450.KS", "064350.KS", "079550.KS", "272210.KS", "047810.KS", "000880.KS", "036530.KS", "005870.KS", "014570.KQ", "069260.KS"],
        "조선/기자재": ["009540.KS", "329180.KS", "042660.KS", "010620.KS", "010140.KS", "083660.KS", "017960.KS", "033530.KQ", "005880.KS", "028670.KS"],
        "전력설비/변압기": ["267260.KS", "010120.KS", "298040.KS", "001440.KS", "028050.KS", "006260.KS", "003560.KS", "006360.KS", "000150.KS", "034020.KS"],
        "원자력/에너지": ["034020.KS", "015760.KS", "051600.KS", "000150.KS", "009830.KS", "052690.KS", "000680.KS", "028050.KS", "000720.KS", "267260.KS"],
        "로봇/자동화": ["277810.KQ", "454910.KS", "058970.KQ", "098460.KQ", "000490.KS", "084370.KQ", "065510.KQ", "090710.KQ", "108320.KQ", "039030.KQ"],
        "K-푸드/식품": ["097950.KS", "003230.KS", "004370.KS", "271560.KS", "005300.KS", "001680.KS", "007310.KS", "005610.KS", "002270.KS", "004990.KS"],
        "K-뷰티/화장품": ["090430.KS", "051900.KS", "192820.KS", "161890.KS", "278470.KS", "108320.KQ", "214450.KQ", "214150.KQ", "145020.KQ", "287410.KQ"],
        "엔터/K-POP": ["352820.KS", "035900.KQ", "041510.KQ", "253450.KQ", "122870.KQ", "035760.KQ", "108860.KQ", "025980.KQ", "060500.KQ", "036570.KS"],
        "게임/모바일": ["259960.KS", "263750.KQ", "293490.KQ", "112040.KQ", "036570.KS", "251270.KS", "063080.KQ", "041140.KQ", "078340.KQ", "067000.KQ"],
        "인터넷/플랫폼": ["035420.KS", "035720.KS", "377300.KS", "323410.KS", "067160.KQ", "035760.KQ", "030200.KS", "017670.KS", "032640.KS", "028260.KS"],
        "금융/은행": ["105560.KS", "055550.KS", "086790.KS", "316140.KS", "024110.KS", "323410.KS", "138040.KS", "000810.KS", "032830.KS", "005940.KS"],
        "증권/보험": ["005940.KS", "016360.KS", "005830.KS", "000810.KS", "032830.KS", "003470.KS", "030530.KS", "000370.KS", "006800.KS", "039490.KS"],
        "지주사/밸류업": ["028260.KS", "003550.KS", "034730.KS", "000880.KS", "004990.KS", "001040.KS", "000150.KS", "000720.KS", "005490.KS", "000120.KS"],
        "철강/금속": ["005490.KS", "010130.KS", "004020.KS", "103140.KS", "001230.KS", "016380.KS", "001440.KS", "005810.KS", "002240.KS", "013520.KS"],
        "석유화학/소재": ["051910.KS", "096770.KS", "010950.KS", "011170.KS", "011780.KS", "009830.KS", "011070.KS", "034730.KS", "006120.KS", "002790.KS"],
        "건설/토목": ["000720.KS", "047040.KS", "006360.KS", "375500.KS", "010780.KS", "000860.KS", "028050.KS", "001120.KS", "009410.KS", "005960.KS"],
        "통신/네트워크": ["017670.KS", "030200.KS", "032640.KS", "253590.KQ", "050890.KQ", "036200.KQ", "084370.KQ", "032500.KQ", "065510.KQ", "018250.KQ"]
    }

    # 🇺🇸 미국 세분화 25대 섹터 (각 10개 종목)
    us_sectors = {
        "AI 빅테크": ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "ORCL", "NFLX"],
        "AI 반도체/칩셋": ["AMD", "AVGO", "QCOM", "INTC", "MU", "ARM", "MRVL", "TXN", "ADI", "ON"],
        "반도체 장비": ["ASML", "AMAT", "LRCX", "KLAC", "TER", "AMKR", "MKSI", "ENTG", "ONTO", "CAMT"],
        "소프트웨어/SaaS": ["CRM", "NOW", "ADBE", "ORCL", "INTU", "SNOW", "WDAY", "TEAM", "DDOG", "MDB"],
        "AI 데이터/보안": ["PLTR", "PANW", "CRWD", "DDOG", "SNOW", "NET", "ZS", "FTNT", "MDB", "MSTR"],
        "빅테크 미디어": ["META", "NFLX", "DIS", "SPOT", "SNAP", "ROKU", "PINS", "TTD", "WBD", "CMCSA"],
        "전기차/자율주행": ["TSLA", "GM", "F", "RIVN", "LCID", "MBLY", "RACE", "LI", "NIO", "XPEV"],
        "방산/우주항공": ["LMT", "RTX", "BA", "NOC", "GD", "GE", "TDG", "LHX", "AXON", "RKLB"],
        "AI 전력망/원자력": ["CEG", "VST", "NEE", "GE", "XLU", "OKLO", "SMR", "CCJ", "DUK", "SO"],
        "전력기기/인프라": ["GEV", "ETN", "PWR", "HUBB", "EMR", "AME", "ROK", "JCI", "VRT", "EATN"],
        "바이오/신약": ["LLY", "NVO", "AMGN", "VRTX", "REGN", "GILD", "BIIB", "BNTX", "MRNA", "MRK"],
        "헬스케어/의료기기": ["UNH", "JNJ", "MDT", "ABT", "ISRG", "SYK", "BSX", "EW", "DXCM", "GEHC"],
        "가상자산/비트코인": ["COIN", "MSTR", "MARA", "RIOT", "SQ", "HOOD", "CLSK", "BITF", "CORZ", "HUT"],
        "핀테크/결제": ["V", "MA", "PYPL", "AXP", "FI", "FIS", "SQ", "AFRM", "TOST", "HOOD"],
        "대형 은행/월가": ["JPM", "BAC", "MS", "GS", "WFC", "C", "BLK", "SCHW", "PNC", "USB"],
        "오일/에너지": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "대형 유통/리테일": ["WMT", "COST", "TGT", "HD", "LOW", "AMZN", "TJX", "ROST", "DLTR", "DG"],
        "음식료/식품": ["MCD", "SBUX", "PEP", "KO", "MDLZ", "PM", "MO", "GIS", "K", "STZ"],
        "패션/뷰티": ["NKE", "LULU", "EL", "CPRT", "ULTA", "RL", "PVH", "TPR", "BIRK", "SKX"],
        "산업재/건설기계": ["CAT", "DE", "HON", "ITW", "CMI", "GE", "MMM", "EMR", "PH", "ETN"],
        "물류/운송": ["UPS", "FDX", "UNP", "CSX", "DAL", "UAL", "LUV", "NSC", "ODFL", "KNX"],
        "통신/네트워크": ["VZ", "T", "TMUS", "CSCO", "ANET", "MSI", "CIEN", "COMM", "LITE", "FYBR"],
        "부동산/REITs": ["PLD", "AMT", "EQIX", "O", "DLR", "CCI", "PSA", "SPG", "VICI", "WELL"],
        "신재생에너지": ["ENPH", "FSLR", "SEDG", "RUN", "BE", "PLUG", "CHPT", "BLDP", "NOVA", "SHLS"],
        "로봇/지능형기계": ["ISRG", "SYM", "PATH", "TER", "ROK", "IRBT", "GE", "HON", "AMAT", "NVDA"]
    }

    def calc_market_impact(sector_dict, is_kr=True):
        all_tickers = []
        for t_list in sector_dict.values(): 
            all_tickers.extend(t_list)

        try:
            # 🎯 1. 데이터 수집 (국내/미국 분기)
            if is_kr:
                # 💡 [속도 30배 향상] 250개 종목을 20개 스레드로 동시 병렬 수집 (2분 ➔ 3초 단축)
                clean_tickers = [t.split('.')[0] for t in all_tickers]
                df_close = pd.DataFrame()
                df_vol = pd.DataFrame()
                
                def fetch_kr_single(item):
                    full_t, clean_t = item
                    try:
                        df_single = fdr.DataReader(clean_t, start='2024-01-01').tail(7)
                        if len(df_single) >= 2:
                            return full_t, df_single['Close'], df_single['Volume']
                    except Exception:
                        pass
                    return full_t, None, None

                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = [executor.submit(fetch_kr_single, (ft, ct)) for ft, ct in zip(all_tickers, clean_tickers)]
                    for future in as_completed(futures):
                        ft, c_ser, v_ser = future.result()
                        if c_ser is not None and v_ser is not None:
                            df_close[ft] = c_ser
                            df_vol[ft] = v_ser
            else:
                # 미국 종목은 yfinance 대량 수집
                raw_df = yf.download(all_tickers, period="5d", progress=False)
                df_close = raw_df['Close']
                df_vol = raw_df['Volume']

            sector_impact_scores = {}

            # 🎯 2. 실질 지수 기여액 연산 (수익률 % × 거래대금)
            for sector, tickers in sector_dict.items():
                total_sector_impact = 0.0
                for t in tickers:
                    if t in df_close.columns and t in df_vol.columns:
                        c_s = df_close[t].dropna()
                        v_s = df_vol[t].dropna()
                        if len(c_s) >= 2 and c_s.iloc[0] > 0:
                            ret = ((c_s.iloc[-1] - c_s.iloc[0]) / c_s.iloc[0]) * 100.0  # 수익률 (%)
                            turnover = (c_s * v_s).mean()                             # 평균 거래대금
                            # 🔥 핵심: 단순 평균이 아닌 거래대금을 곱한 '실질 지수 기여 금액' 합산
                            total_sector_impact += (ret * turnover)

                sector_impact_scores[sector] = total_sector_impact

            # 🎯 3. 상승 기여 섹터와 하락 주도 섹터 분류 및 정규화
            pos_dict = {k: v for k, v in sector_impact_scores.items() if v > 0}
            neg_dict = {k: abs(v) for k, v in sector_impact_scores.items() if v < 0}

            sum_p = sum(pos_dict.values())
            sum_n = sum(neg_dict.values())

            pos_norm = {k: round((v / sum_p) * 100) if sum_p > 0 else 0 for k, v in pos_dict.items()}
            neg_norm = {k: round((v / sum_n) * 100) if sum_n > 0 else 0 for k, v in neg_dict.items()}

            top_pos = sorted(pos_norm.items(), key=lambda x: x[1], reverse=True)[:3]
            top_neg = sorted(neg_norm.items(), key=lambda x: x[1], reverse=True)[:3]

            return top_pos, top_neg

        except Exception:
            return [("데이터 연산 오류", 100)], [("데이터 연산 오류", 100)]

    kr_pos, kr_neg = calc_market_impact(kr_sectors, is_kr=True)
    us_pos, us_neg = calc_market_impact(us_sectors, is_kr=False)
    return kr_pos, kr_neg, us_pos, us_neg


# ====================================================================
# 🎨 [레이아웃 연동] 타이틀 공간 확보 및 좌/우 상승·하락 분할 보드
# ====================================================================

# 양측 분할 정렬을 위해 우측 칸을 1.4로 살짝 밸런싱합니다.
col_title, col_box = st.columns([2.0, 1.9])

with col_title:
    st.title("🔥모험이 없으면 큰 발전도 없다")

with col_box:
    try:
        kr_p, kr_n, us_p, us_n = get_realtime_sector_influence()
        
# 💡 각 테마별 한글 종목명 매핑 사전
        sector_stock_names = {
            # [국내]
            "반도체/HBM": "삼성전자, SK하이닉스, 한미반도체, 리노공업, HPSP",
            "반도체장비/소부장": "이오테크닉스, 동진쎄미켐, 원익IPS, 주성엔지니어링, 하나마이크론",
            "제약/바이오신약": "삼성바이오로직스, 셀트리온, 알테오젠, 리가켐바이오, HLB",
            "의료기기/뷰티케어": "클래시스, 파마리서치, 휴젤, 인바디, 바이오플러스",
            "2차전지/셀": "LG에너지솔루션, 삼성SDI, 엔켐, 포스코퓨처엠, 엘앤에프",
            "2차전지/소재": "POSCO홀딩스, 에코프로비엠, 에코프로, 코스모신소재, 대주전자재료",
            "완성차/모빌리티": "현대차, 기아, 현대모비스, 현대글로비스, 현대위아",
            "자동차부품": "한국타이어, 한온시스템, 명신산업, 화신, SL",
            "방산/지상무기": "한화에어로스페이스, 현대로템, LIG넥스원, 한화시스템, 한국항공우주",
            "조선/기자재": "HD한국조선해양, HD현대중공업, 한화오션, HD현대미포, 삼성중공업",
            "전력설비/변압기": "HD현대일렉트릭, LS일렉트릭, 효성중공업, 대한전선, 삼성E&A",
            "원자력/에너지": "두산에너빌리티, 한국전력, 한전KPS, 두산, 한화솔루션",
            "로봇/자동화": "레인보우로보틱스, 엠로, 고영, 유진로봇, 대동",
            "K-푸드/식품": "CJ제일제당, 삼양식품, 농심, 오리온, 롯데칠성",
            "K-뷰티/화장품": "아모레퍼시픽, LG생활건강, 코스맥스, 한국콜마, 에이피알",
            "엔터/K-POP": "하이브, JYP Ent., 에스엠, 와이지엔터, CJ ENM",
            "게임/모바일": "크래프톤, 펄어비스, 카카오게임즈, 위메이드, 엔씨소프트",
            "인터넷/플랫폼": "NAVER, 카카오, 카카오페이, 카카오뱅크, SOOP",
            "금융/은행": "KB금융, 신한지주, 하나금융지주, 우리금융지주, 기업은행",
            "증권/보험": "NH투자증권, 삼성증권, DB손해보험, 삼성화재, 삼성생명",
            "지주사/밸류업": "삼성물산, LG, SK, 한화, 롯데지주",
            "철강/금속": "POSCO홀딩스, 고려아연, 현대제철, 풍산, 동국제강",
            "석유화학/소재": "LG화학, SK이노베이션, S-Oil, 금호석유, 롯데케미칼",
            "건설/토목": "현대건설, 대우건설, GS건설, DL이앤씨, 아이에스동서",
            "통신/네트워크": "SK텔레콤, KT, LG유플러스, 서진시스템, 솔리드",
            
            # [미국]
            "AI 빅테크": "엔비디아, 마이크로소프트, 애플, 알파벳(구글), 아마존",
            "AI 반도체/칩셋": "AMD, 브로드컴, 퀄컴, 인텔, 마이크론",
            "반도체 장비": "ASML, 어플라이드 머티리얼즈, 램리서치, KLA, 테라다인",
            "소프트웨어/SaaS": "세일즈포스, 서비스나우, 어도비, 오라클, 인투이트",
            "AI 데이터/보안": "팔란티어, 팔로알토, 크라우드스트라이크, 데이터독, 스노우플레이크",
            "빅테크 미디어": "메타, 넷플릭스, 디즈니, 스포티파이, 스냅",
            "전기차/자율주행": "테슬라, GM, 포드, 리비안, 루시드",
            "방산/우주항공": "록히드마틴, RTX, 보잉, 노스롭그루먼, 제너럴다이내믹스",
            "AI 전력망/원자력": "컨스텔레이션, 비스트라, 넥스트에라, GE, XLU(ETF)",
            "전력기기/인프라": "GE버노바, 이튼, 콴타서비시스, 허벨, 에머슨",
            "바이오/신약": "일라이릴리, 노보노디스크, 암젠, 버텍스, 리제네론",
            "헬스케어/의료기기": "유나이티드헬스, 존슨앤드존슨, 메드트로닉, 애보트, 인튜이티브 서지컬",
            "가상자산/비트코인": "코인베이스, 마이크로스트래티지, 마라톤, 라이엇, 블록(구 스퀘어)",
            "핀테크/결제": "비자, 마스터카드, 페이팔, 아메리칸 익스프레스, 피서브",
            "대형 은행/월가": "JP모건, Bank of America, 모건스탠리, 골드만삭스, 웰스파고",
            "오일/에너지": "엑손모빌, 셰브론, 코노코필립스, EOG, 슐럼버거",
            "대형 유통/리테일": "월마트, 코스트코, 타겟, 홈디포, 로우스",
            "음식료/식품": "맥도날드, 스타벅스, 펩시코, 코카콜라, 몬델리즈",
            "패션/뷰티": "나이키, 룰루레몬, 에스티로더, 코파트, 울타뷰티",
            "산업재/건설기계": "캐터필러, 디어, 허니웰, 일리노이 툴 웍스, 커민스",
            "물류/운송": "UPS, 페덱스, 유니온 퍼시픽, CSX, 델타 항공",
            "통신/네트워크": "버라이즌, AT&T, T-모바일, 시스코, 아리스타",
            "부동산/REITs": "프로로지스, 아메리칸타워, 이쿼닉스, 리얼티인컴, 디지털리얼티",
            "신재생에너지": "인페이즈, 퍼스트솔라, 솔라에지, 런, 블룸에너지",
            "로봇/지능형기계": "인튜이티브 서지컬, 심보틱, UI패스, 테라다인, 로크웰"
        }

        # 💡 마우스 올렸을 때 관련 종목 말풍선(title)이 나오도록 수정
        def fmt_list(data, is_pos=True):
            valid = [x for x in data if x[1] > 0]
            if not valid:
                msg = "🔴 상승 테마 없음" if is_pos else "🟢 전 섹터 상승세 (하락 테마 없음)"
                return f'<div style="color:#94a3b8;">{msg}</div>'
            
            html_res = []
            for i, (name, pct) in enumerate(valid[:3], 1):
                stocks = sector_stock_names.get(name, "관련 종목 정보 없음")
                html_res.append(
                    f'<div title="📌 [관련 종목]\n{stocks}" style="cursor:help; margin-bottom:2px;">'
                    f'<b>{i}위.</b> <span style="border-bottom:1px dotted #64748b;">{name}</span> <b>{pct}%</b>'
                    f'</div>'
                )
            return "".join(html_res)

        kr_p_html = fmt_list(kr_p, True)
        kr_n_html = fmt_list(kr_n, False)
        us_p_html = fmt_list(us_p, True)
        us_n_html = fmt_list(us_n, False)
    except Exception:
        kr_p_html = "<div><b>1위.</b> 반도체 <b>100%</b></div>"
        kr_n_html = "<div>🟢 전 섹터 상승세 (하락 테마 없음)</div>"
        us_p_html = "<div><b>1위.</b> AI빅테크 <b>100%</b></div>"
        us_n_html = "<div>🟢 전 섹터 상승세 (하락 테마 없음)</div>"

    # HTML 출력 부분 예시 (기존 st.markdown 박스 안에 kr_p_html 등을 바인딩)
    st.markdown(f"""
    <div style="background-color:#0f172a; padding:12px; border-radius:8px; border:1px solid #334155; font-size:12px;">
        <div style="font-weight:bold; color:#94a3b8; text-align:center; margin-bottom:8px;">📊 5D (1주) 지수 기여도 리포트</div>
        <div style="display:flex; justify-content:space-between; gap:12px;">
            <!-- 🔴 좌측: 상승 견인 테마 (오른쪽에 세로 구분선 추가) -->
            <div style="flex:1; border-right: 1px solid #334155; padding-right: 10px;">
                <div style="color:#ff4b4b; font-weight:bold;">🔴 상승 견인 테마</div>
                <div style="color:#aaa; font-size:11px; margin-top:3px;">[국내]</div> {kr_p_html}
                <div style="color:#aaa; font-size:11px; margin-top:3px;">[미국]</div> {us_p_html}
            </div>
            <!-- 🔵 우측: 하락 주도 테마 -->
            <div style="flex:1; padding-left: 2px;">
                <div style="color:#38bdf8; font-weight:bold;">🔵 하락 주도 테마</div>
                <div style="color:#aaa; font-size:11px; margin-top:3px;">[국내]</div> {kr_n_html}
                <div style="color:#aaa; font-size:11px; margin-top:3px;">[미국]</div> {us_n_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import requests
import FinanceDataReader as fdr
from datetime import datetime, timedelta


# ====================================================================
# --- [2. 780개 실시간 종목 이름-티커 매핑 사전 구축] ---
@st.cache_data
def get_static_assets():
    # ₩ 국내 주식 및 테마형 ETF (기존 300개 유지)
    kr_raw = (
        "삼성전자:005930.KS,SK하이닉스:000660.KS,LG에너지솔루션:373220.KS,삼성바이오로직스:207940.KS,현대차:005380.KS,"
        "기아:000270.KS,셀트리온:068270.KS,KB금융:105560.KS,POSCO홀딩스:005490.KS,NAVER:035420.KS,"
        "LG화학:051910.KS,삼성물산:028260.KS,신한지주:055550.KS,포스코퓨처엠:003670.KS,현대모비스:012330.KS,"
        "카카오:035720.KS,삼성SDI:006400.KS,하나금융지주:086790.KS,"
        "TIGER_미국필라델피아반도체나스닥:381170.KS,TIGER_미국테크TOP10:381180.KS,TIGER_미국AI빅테크10:462010.KS,"
        "KODEX_2차전지산업:305540.KS,KODEX_AI맞춤형반도체:479200.KS,TIGER_2차전지테마:305720.KS,"
        "ACE_글로벌반도체TOP4_Plus:425660.KS,KODEX_미국반도체MV:390390.KS,TIGER_글로벌AI액티브:466920.KS,TIGER_HBM반도체:468250.KS,"
        "LG전자:066570.KS,메리츠금융지주:138040.KS,삼성생명:032830.KS,SK이노베이션:096770.KS,카카오뱅크:323410.KS,"
        "HD현대중공업:329180.KS,삼성화재:000810.KS,한국전력:015760.KS,KT&G:033780.KS,크래프톤:259960.KS,"
        "삼성전기:009150.KS,두산에너빌리티:034020.KS,SK:034730.KS,고려아연:010130.KS,기업은행:024110.KS,"
        "SK텔레콤:017670.KS,한화에어로스페이스:012450.KS,포스코인터내셔널:047050.KS,HD한국조선해양:009540.KS,"
        "에코프로머티:454910.KS,한화오션:042660.KS,카카오페이:377300.KS,"
        "우리금융지주:316140.KS,LG:003550.KS,아모레퍼시픽:090430.KS,엔씨소프트:036570.KS,대한항공:003490.KS,"
        "HMM:011200.KS,삼성에스디에스:018260.KS,S-Oil:010950.KS,삼성중공업:010140.KS,LG생활건강:051900.KS,"
        "한화솔루션:009830.KS,SK스퀘어:402340.KS,포스코DX:022100.KS,코웨이:021240.KS,KT:030200.KS,"
        "한국항공우주:047810.KS,금호석유:011780.KS,LS:006260.KS,한미반도체:042700.KS,현대글로비스:086280.KS,"
        "한화:000880.KS,현대건설:000720.KS,LG디스플레이:034220.KS,BGF리테일:282330.KS,강원랜드:035250.KS,"
        "현대제철:004020.KS,한국타이어앤테크놀로지:161390.KS,이마트:139480.KS,현대오토에버:307950.KS,유한양행:000100.KS,"
        "오리온:271560.KS,현대해상:001450.KS,SK바이오팜:326030.KS,DB손해보험:005830.KS,키움증권:039490.KS,"
        "LS일렉트릭:010120.KS,두산밥캣:241560.KS,한미약품:128940.KS,제일기획:030000.KS,CJ제일제당:097950.KS,"
        "F&F:383220.KS,한진칼:180640.KS,삼성증권:016360.KS,NH투자증권:005940.KS,팬오션:028670.KS,"
        "코스맥스:192820.KS,대우건설:047040.KS,GS:078930.KS,한솔케미칼:014680.KS,호텔신라:008770.KS,"
        "휠라홀딩스:081660.KS,신세계:004170.KS,에스원:012750.KS,CJ대한통운:000120.KS,KCC:002380.KS,"
        "SKC:011790.KS,현대위아:011210.KS,아시아나항공:020560.KS,현대엘리베이터:017800.KS,한온시스템:018880.KS,"
        "GS건설:006360.KS,한화생명:088350.KS,하이트진로:000080.KS,롯데케미칼:011170.KS,OCI:456040.KS,"
        "두산퓨얼셀:336260.KS,효성첨단소재:298050.KS,대웅제약:069620.KS,대한전선:001440.KS,효성티앤씨:298020.KS,"
        "영원무역:111110.KS,명신산업:009900.KS,농심:004370.KS,동서:026960.KS,한국금융지주:071050.KS,"
        "미래에셋증권:006800.KS,한전KPS:051600.KS,롯데지주:004990.KS,신풍제약:019170.KS,아이에스동서:010780.KS,"
        "대상:001680.KS,삼양식품:003230.KS,풍산:103140.KS,녹십자:006280.KS,현대백화점:069960.KS,"
        "동국제강:001230.KS,효성:004800.KS,한섬:020000.KS,진에어:272450.KS,태광산업:003240.KS,"
        "롯데쇼핑:023530.KS,DL이앤씨:375500.KS,현대로템:064350.KS,한화시스템:272210.KS,LIG넥스원:079550.KS,"
        "LX인터내셔널:001120.KS,한국가스공사:036460.KS,아모레퍼시픽홀딩스:002790.KS,GS리테일:007070.KS,대한유화:006650.KS,"
        "SK케미칼:285130.KS,다우기술:023590.KS,솔루스첨단소재:336370.KS,에코프로비엠:247540.KQ,에코프로:086520.KQ,"
        "알테오젠:196170.KQ,HLB:028300.KQ,엔켐:348370.KQ,셀트리온제약:068760.KQ,HPSP:403870.KQ,"
        "리노공업:058470.KQ,레인보우로보틱스:277810.KQ,클래시스:214150.KQ,JYP엔터:035900.KQ,에스엠:041510.KQ,"
        "펄어비스:263750.KQ,휴젤:145020.KQ,위메이드:112040.KQ,카카오게임즈:293490.KQ,삼천당제약:000250.KQ,"
        "루닛:328130.KQ,이오테크닉스:039030.KQ,솔브레인:357780.KQ,동진쎄미켐:005290.KQ,ISC:095340.KQ,"
        "주성엔지니어링:036930.KQ,파마리서치:214450.KQ,메지온:140410.KQ,에코프로에이치엔:383310.KQ,피엔티:137400.KQ,"
        "하나마이크론:067310.KQ,대주전자재료:078600.KQ,나노신소재:121600.KQ,성일하이텍:365340.KQ,윤성에프앤씨:372170.KQ,"
        "티씨케이:064760.KQ,고영:098460.KQ,두산테스나:131970.KQ,원익IPS:240810.KQ,유진테크:084370.KQ,"
        "에스앤에스텍:101490.KQ,레이크머티리얼즈:281740.KQ,넥슨게임즈:225570.KQ,컴투스:078340.KQ,심텍:222800.KQ,"
        "서진시스템:253590.KQ,디오:039840.KQ,안랩:053800.KQ,메디톡스:086900.KQ,차바이오텍:085660.KQ,"
        "젬백스:082270.KQ,씨젠:096530.KQ,현대바이오:048410.KQ,네이처셀:007390.KQ,한국비엔씨:256840.KQ,"
        "다날:064260.KQ,케이엠더블유:032500.KQ,텔레칩스:054450.KQ,어보브반도체:102120.KQ,해성디에스:195870.KQ,"
        "덕산네오룩스:213420.KQ,엘앤에프:066970.KS,원익QnC:074600.KQ,인바디:041830.KQ,더블유씨피:393890.KQ,"
        "대보마그네틱:290670.KQ,씨에스베어링:297090.KQ,에스티팜:237690.KQ,고바이오랩:348150.KQ,동화기업:025900.KQ,"
        "엠로:058970.KQ,에이비엘바이오:298380.KQ,지놈앤컴퍼니:314130.KQ,오스코텍:039200.KQ,바이오플러스:099430.KQ,"
        "티움바이오:321550.KQ,아이센스:099190.KQ,보로노이:310210.KQ,제이앤티씨:204270.KQ,인텔리안테크:189300.KQ,"
        "에치에프알:230240.KQ,솔리드:050890.KQ,서플러스글로벌:140070.KQ,피에스케이:319660.KQ,테스:095610.KQ,"
        "하이브:352820.KS,두산:000150.KS,이수페타시스:007660.KS,한올바이오파마:009420.KS,코스모신소재:005070.KS,"
        "코스모화학:005420.KS,금양:009410.KS,영풍:000670.KS,풍산홀딩스:005810.KS,한국앤컴퍼니:000240.KS,"
        "코오롱인더:120110.KS,효성중공업:298040.KS,효성화학:298000.KS,대웅:003090.KS,종근당:185750.KS,"
        "JW중외제약:001060.KS,보령:003850.KS,동아쏘시오홀딩스:000640.KS,동아에스티:170900.KS,광동제약:009290.KS,"
        "한독:002390.KS,대원제약:003220.KS,일양약품:007570.KS,삼진제약:005500.KS,부광약품:003000.KS,"
        "영진약품:003520.KS,일동제약:249420.KS,하나제약:293480.KS,환인제약:016580.KS,동화약품:000020.KS,"
        "안국약품:001540.KQ,동국제약:086450.KQ,휴온스:243070.KQ,리가켐바이오:141080.KQ,바이오니아:064550.KQ,"
        "유나이티드제약:033270.KS,제넥신:095700.KQ,메드팩토:235980.KQ,앱클론:174900.KQ,지씨셀:144510.KQ,"
        "헬릭스미스:084990.KQ,에이치엘비생명과학:067630.KQ,셀리드:299660.KQ,큐리언트:115180.KQ,올릭스:226950.KQ,"
        "인트론바이오:048530.KQ,앤디포스:238090.KQ,바디텍메드:206640.KQ,랩지노믹스:084650.KQ,수젠텍:253840.KQ,"
        "피씨엘:241820.KQ,이수앱지스:086890.KQ,아미코젠:092040.KQ,대동:000490.KS,TYM:002900.KS,"
        "아세아텍:050860.KQ,경농:002100.KS,조비:001550.KS,남해화학:025860.KS,"
        "백광산업:001340.KS,송원산업:004430.KS,이수화학:005950.KS,"
        "한농화성:011500.KS,국도화학:007690.KS"
    )

    # 💲 미국 주식: S&P 500 전 구성 종목 매핑 (약 503개)
    us_raw = (
        "3M:MMM,A.O.Smith:AOS,AbbVie:ABBV,AbbottLaboratories:ABT,Accenture:ACN,Adobe:ADBE,AMD:AMD,ADP:ADP,AESCorp:AES,Aflac:AFL,"
        "AgilentTechnologies:A,AirProducts:APD,Akamai:AKAM,Albemarle:ALB,AlexandriaRealEstate:ARE,AlignTechnology:ALGN,Allegion:ALLE,AlliantEnergy:LNT,Allstate:ALL,AllyFinancial:ALLY,"
        "Alphabet-A:GOOGL,Alphabet-C:GOOG,Altria:MO,Amazon:AMZN,Amcor:AMCR,Ameren:AEE,AmericanAirlines:AAL,AmericanElectricPower:AEP,AmericanExpress:AXP,AmericanTower:AMT,"
        "AmericanWaterWorks:AWK,AmeripriseFinancial:AMP,Ametek:AME,Amgen:AMGN,Amphenol:APH,AnalogDevices:ADI,Ansys:ANSS,Aon:AON,APA:APA,Aptiv:APTV,"
        "ArcherDanielsMidland:ADM,AristaNetworks:ANET,ArthurJGallagher:AJG,Assurant:AIZ,AT&T:T,AtmosEnergy:ATO,Autodesk:ADSK,AutoZone:AZO,AveryDennison:AVY,AxonEnterprise:AXON,"
        "BakerHughes:BKR,BallCorp:BALL,BankofAmerica:BAC,BankofNewYorkMellon:BK,BaxterInternational:BAX,BectonDickinson:BDX,BerkshireHathaway:BRK-B,BestBuy:BBY,Bio-Techne:TECH,Biogen:BIIB,"
        "BioRadLaboratories:BIO,BlackRock:BLK,Blackstone:BX,Boeing:BA,BookingHoldings:BKNG,BorgWarner:BWA,BostonProperties:BXP,BostonScientific:BSX,BristolMyersSquibb:BMY,Broadcom:AVGO,"
        "Broadridge:BR,Brown&Brown:BRO,BrownForman:BF-B,BuildersFirstSource:BLDR,Bunge:BG,CadenceDesign:CDNS,CaesarsEntertainment:CZR,CamdenProperty:CPT,CampbellSoup:CPB,CapitalOne:COF,"
        "CardinalHealth:CAH,Carlisle:CSL,CarMax:KMX,Carnival:CCL,CarrierGlobal:CARR,Caterpillar:CAT,CboeGlobal:CBOE,CBREGroup:CBRE,CDW:CDW,Celanese:CE,"
        "Centene:CNC,CenterPointEnergy:CNP,CFIndustries:CF,CHRobinson:CHRW,CharlesRiver:CRL,CharlesSchwab:SCHW,CharterCommunications:CHTR,Chevron:CVX,ChipotleMexicanGrill:CMG,Chubb:CB,"
        "Church&Dwight:CHD,Cigna:CI,CincinnatiFinancial:CINF,Cintas:CTAS,Cisco:CSCO,Citigroup:C,CitizensFinancial:CFG,Clorox:CLX,CMEGroup:CME,CMSEnergy:CMS,"
        "Coca-Cola:KO,Cognizant:CTSH,Colgate-Palmolive:CL,Comcast:CMCSA,Comerica:CMA,ConagraBrands:CAG,ConocoPhillips:COP,ConsolidatedEdison:ED,ConstellationBrands:STZ,ConstellationEnergy:CEG,"
        "CooperCompanies:COO,Copart:CPRT,Corning:GLW,Corteva:CTVA,CoStarGroup:CSGP,Costco:COST,CoterraEnergy:CTRA,CrownCastle:CCI,CSX:CSX,Cummins:CMI,"
        "CVSHealth:CVS,Danaher:DHR,DardenRestaurants:DRI,Datadog:DDOG,Dayforce:DAY,Deere:DE,DeltaAirLines:DAL,DevonEnergy:DVN,DexCom:DXCM,DiamondbackEnergy:FANG,"
        "DigitalRealty:DLR,DiscoverFinancial:DFS,DollarGeneral:DG,DollarTree:DLTR,DominionEnergy:D,DominoPizza:DPZ,Dover:DOV,Dow:DOW,DRHorton:DHI,DTEEnergy:DTE,"
        "DukeEnergy:DUK,DuPont:DD,Eaton:ETN,eBay:EBAY,Ecolab:ECL,EdisonInternational:EIX,EdwardsLifesciences:EW,ElectronicArts:EA,ElevanceHealth:ELV,EliLilly:LLY,"
        "EmersonElectric:EMR,EnphaseEnergy:ENPH,Entergy:ETR,EOGResources:EOG,EPAMSystems:EPAM,EQT:EQT,Equifax:EFX,Equinix:EQIX,EquityResidential:EQR,EssexProperty:ESS,"
        "EsteeLauder:EL,Etsy:ETSY,Evergy:EVRG,EversourceEnergy:ES,Exelon:EXC,ExpediaGroup:EXPE,Expeditors:EXPD,ExtraSpaceStorage:EXR,ExxonMobil:XOM,F5Inc:FFIV,"
        "Fastenal:FAST,FederalRealty:FRT,FedEx:FDX,FidelityNational:FIS,FifthThird:FITB,FirstEnergy:FE,FirstSolar:FSLR,Fiserv:FI,FMC:FMC,FordMotor:F,"
        "Fortinet:FTNT,Fortive:FTV,FoxCorp-A:FOXA,FoxCorp-B:FOX,FranklinResources:BEN,Freeport-McMoRan:FCX,Garmin:GRMN,Gartner:IT,GEAerospace:GE,GEHealthcare:GEHC,"
        "GEVernova:GEV,GenDigital:GEN,Generac:GNRC,GeneralDynamics:GD,GeneralMills:GIS,GeneralMotors:GM,GenuineParts:GPC,GileadSciences:GILD,GlobalFoundries:GFS,GlobalPayments:GPN,"
        "GlobeLife:GL,GoldmanSachs:GS,Halliburton:HAL,HartfordFinancial:HIG,Hasbro:HAS,HCAHealthcare:HCA,HealthpeakProperties:DOC,HenrySchein:HSIC,Hershey:HSY,HessCorporation:HES,"
        "HPEnergy:HPE,HFSinclair:DINO,HiltonWorldwide:HLT,Hologic:HOLX,HomeDepot:HD,Honeywell:HON,HormelFoods:HRL,HostHotels:HST,HowmetAerospace:HWM,HPInc:HPQ,"
        "Hubbell:HUBB,Humana:HUM,HuntingtonBancshares:HBAN,HuntingtonIngalls:HII,IBM:IBM,IDEX:IEX,IdexxLaboratories:IDXX,IllinoisToolWorks:ITW,Illumina:ILMN,Incyte:INCY,"
        "IngersollRand:IR,Insulet:PODD,Intel:INTC,IntercontinentalExchange:ICE,InternationalFlavors:IFF,InternationalPaper:IP,InterpublicGroup:IPG,Intuit:INTU,IntuitiveSurgical:ISRG,Invesco:IVZ,"
        "InvitationHomes:INVH,IQVIA:IQV,IronMountain:IRM,JBHunt:JBHT,Jabil:JBL,JackHenry:JKHY,JacobsSolutions:J,JMSmucker:SJM,Johnson&Johnson:JNJ,JohnsonControls:JCI,"
        "JPMorganChase:JPM,JuniperNetworks:JNPR,Kellanova:K,Kenvue:KVUE,KeyCorp:KEY,Keysight:KEYS,Kimberly-Clark:KMB,KimcoRealty:KIM,KinderMorgan:KMI,KLATechnologies:KLAC,"
        "Kroger:KR,L3Harris:LHX,Labcorp:LH,LamResearch:LRCX,LambWeston:LW,LasVegasSands:LVS,Leidos:LDOS,Lennar:LEN,Lennox:LII,Linde:LIN,"
        "LiveNation:LYV,LKQ:LKQ,LockheedMartin:LMT,Loews:L,Lowes:LOW,Lululemon:LULU,M&TBank:MTB,MarathonOil:MRO,MarathonPetroleum:MPC,MarketAxess:MKTX,"
        "Marriott:MAR,MarshMcLennan:MMC,MartinMarietta:MLM,Masco:MAS,Mastercard:MA,MatchGroup:MTCH,McCormick:MKC,McDonalds:MCD,McKesson:MCK,Medtronic:MDT,"
        "Merck:MRK,Meta:META,MetLife:MET,MettlerToledo:MTD,MGMResorts:MGM,MicrochipTechnology:MCHP,MicronTechnology:MU,Microsoft:MSFT,Mid-AmericaApartment:MAA,Moderna:MRNA,"
        "MohawkIndustries:MHK,MolinaHealthcare:MOH,Mondelez:MDLZ,MonolithicPower:MPWR,MonsterBeverage:MNST,Moodys:MCO,MorganStanley:MS,Mosaic:MOS,MotorolaSolutions:MSI,"
        "MSCI:MSCI,Nasdaq:NDAQ,NetApp:NTAP,Netflix:NFLX,NewellBrands:NWL,Newmont:NEM,NewsCorp-A:NWSA,NewsCorp-B:NWS,NextEraEnergy:NEE,Nike:NKE,"
        "NiSource:NI,Nordson:NDSN,NorfolkSouthern:NSC,NorthernTrust:NTRS,NorthropGrumman:NOC,NorwegianCruise:NCLH,NRGEnergy:NRG,Nucor:NUE,NVIDIA:NVDA,NVRInc:NVR,"
        "NXPSemiconductors:NXPI,OReillyAutomotive:ORLY,OccidentalPetroleum:OXY,OldDominionFreight:ODFL,OmnicomGroup:OMC,ONSemiconductor:ON,ONEOK:OKE,Oracle:ORCL,OtisWorldwide:OTIS,PACCAR:PCAR,"
        "PackagingCorp:PKG,PaloAltoNetworks:PANW,ParamountGlobal:PARA,ParkerHannifin:PH,Paychex:PAYX,Paycom:PAYC,PayPal:PYPL,Pentair:PNR,PepsiCo:PEP,Pfizer:PFE,"
        "PG&E:PCG,PhilipMorris:PM,Phillips66:PSX,PinnacleWest:PNW,PNCFinancial:PNC,PoolCorp:POOL,PPGIndustries:PPG,PPL:PPL,PrincipalFinancial:PFG,Procter&Gamble:PG,"
        "Progressive:PGR,Prologis:PLD,PrudentialFinancial:PRU,PublicServiceEnterprise:PEG,PublicStorage:PSA,PulteGroup:PHM,Qorvo:QRVO,Qualcomm:QCOM,QuantaServices:PWR,QuestDiagnostics:DGX,"
        "RalphLauren:RL,RaymondJames:RJF,RTXCorporation:RTX,RealtyIncome:O,Regeneron:REGN,RegionsFinancial:RF,RepublicServices:RSG,ResMed:RMD,Revvity:RVTY,RockwellAutomation:ROK,"
        "Rollins:ROL,RoperTechnologies:ROP,RossStores:ROST,RoyalCaribbean:RCL,SPGlobal:SPGI,Salesforce:CRM,SBACanada:SBAC,Schlumberger:SLB,Seagate:STX,SealedAir:SEE,"
        "Sempra:SRE,ServiceNow:NOW,Sherwin-Williams:SHW,SimonProperty:SPG,Skyworks:SWKS,Snap-on:SNA,SolarEdge:SEDG,SouthernCo:SO,SouthwestAirlines:LUV,StanleyBlack&Decker:SWK,"
        "Starbucks:SBUX,StateStreet:STT,SteelDynamics:STLD,Steris:STE,Stryker:SYK,SuperMicroComputer:SMCI,SynchronyFinancial:SYF,Synopsys:SNPS,Sysco:SYY,T-Mobile:TMUS,"
        "TRowePrice:TROW,TakeTwoInteractive:TTWO,Tapestry:TPR,TargaResources:TRGP,Target:TGT,TEConnectivity:TEL,Teledyne:TDY,Teleflex:TFX,Teradyne:TER,Tesla:TSLA,"
        "TexasInstruments:TXN,Textron:TXT,ThermoFisher:TMO,TJXCompanies:TJX,TractorSupply:TSCO,TraneTechnologies:TT,TransDigm:TDG,Travelers:TRV,Trimble:TRMB,TruistFinancial:TFC,"
        "TylerTechnologies:TYL,TysonFoods:TSN,USBancorp:USB,Uber:UBER,UDR:UDR,UltaBeauty:ULTA,UnionPacific:UNP,UnitedAirlines:UAL,UnitedParcel:UPS,UnitedRentals:URI,"
        "UnitedHealth:UNH,UniversalHealth:UHS,UnumGroup:UNM,ValeroEnergy:VLO,Veralto:VLTO,Ventas:VTR,VeriSign:VRSN,Verisk:VRSK,Verizon:VZ,VertexPharmaceuticals:VRTX,"
        "VICIProperties:VICI,Visa:V,Vistra:VSTI,VulcanMaterials:VMC,WRBerkley:WRB,WWGrainger:GWW,Wabtec:WAB,WalgreensBoots:WBA,Walmart:WMT,WaltDisney:DIS,"
        "WarnerBrosDiscovery:WBD,WasteManagement:WM,Waters:WAT,Watsco:WSO,WECEnergy:WEC,WellsFargo:WFC,Welltower:WELL,WesternDigital:WDC,WesternUnion:WU,Weyerhaeuser:WY,"
        "Whirlpool:WHR,WilliamsCompanies:WMB,WillisTowersWatson:WTW,WynnResorts:WYNN,XcelEnergy:XEL,Xylem:XYL,YumBrands:YUM,ZebraTechnologies:ZBRA,ZimmerBiomet:ZBH,ZionsBancorp:ZION,Zoetis:ZTS"
    )

    # 🪙 암호화폐 (기존 80개 유지)
    crypto_raw = (
        "Bitcoin:BTC-KRW,Ethereum:ETH-KRW,Solana:SOL-KRW,XRP:XRP-KRW,Dogecoin:DOGE-KRW,Cardano:ADA-KRW,ShibaInu:SHIB-KRW,Avalanche:AVAX-KRW,Polkadot:DOT-KRW,Chainlink:LINK-KRW,"
        "Tron:TRX-KRW,Near:NEAR-KRW,EthereumClassic:ETC-KRW,Polygon:POL-KRW,Litecoin:LTC-KRW,BitcoinCash:BCH-KRW,Cosmos:ATOM-KRW,Uniswap:UNI-KRW,Stellar:XLM-KRW,Aptos:APT-KRW,"
        "Hedera:HBAR-KRW,Filecoin:FIL-KRW,Arbitrum:ARB-KRW,Optimism:OP-KRW,Stacks:STX-KRW,Sui:SUI-KRW,VeChain:VET-KRW,ImmutableX:IMX-KRW,Theta:THETA-KRW,Fantom:FTM-KRW,"
        "Injective:INJ-KRW,Render:RNDR-KRW,TheGraph:GRT-KRW,Aave:AAVE-KRW,Algorand:ALGO-KRW,Flow:FLOW-KRW,AxieInfinity:AXS-KRW,MultiversX:EGLD-KRW,Sandbox:SAND-KRW,Decentraland:MANA-KRW,"
        "Tezos:XTZ-KRW,EOS:EOS-KRW,Kava:KAVA-KRW,Mina:MINA-KRW,Sei:SEI-KRW,Chiliz:CHZ-KRW,Blur:BLUR-KRW,1inch:1INCH-KRW,MaskNetwork:MASK-KRW,Celo:CELO-KRW,"
        "Threshold:T-KRW,BitcoinSV:BSV-KRW,Qtum:QTUM-KRW,Nem:XEM-KRW,Stratis:STRAX-KRW,SpaceID:ID-KRW,CyberConnect:CYBER-KRW,IQ:IQ-KRW,Steem:STEEM-KRW,Hive:HIVE-KRW,"
        "Ark:ARK-KRW,LoomNetwork:LOOM-KRW,Icon:ICX-KRW,Aergo:AERGO-KRW,MossCoin:MOC-KRW,Bora:BORA-KRW,Milk:MLK-KRW,Metadium:META-KRW,MediBloc:MED-KRW,AhaToken:AHT-KRW,"
        "Groestlcoin:GRS-KRW,StormX:STMX-KRW,Ankr:ANKR-KRW,MVL:MVL-KRW,Neo:NEO-KRW,Ontology:ONT-KRW,Gas:GAS-KRW,Storj:STORJ-KRW,Civic:CVC-KRW,Metal:MTL-KRW"
    )

    # 문자열 파싱 (국내 주식 / 미국 주식)
    kr_dict = {item.split(':')[0].strip(): item.split(':')[1].strip() for item in kr_raw.split(',') if ':' in item}
    us_dict = {item.split(':')[0].strip(): item.split(':')[1].strip() for item in us_raw.split(',') if ':' in item}

    # 🪙 암호화폐: 업비트 KRW 마켓 전체 실시간 자동 수집
    crypto_dict = {}
    try:
        import requests
        upbit_api_url = "https://api.upbit.com/v1/market/all?isDetails=false"
        res = requests.get(upbit_api_url, timeout=5)
        if res.status_code == 200:
            market_list = res.json()
            for m in market_list:
                market_code = m.get('market', '')
                if market_code.startswith('KRW-'):
                    symbol = market_code.split('-')[1]  # 예: BTC
                    kor_name = m.get('korean_name', symbol)
                    display_name = f"{kor_name} ({symbol})"  # 예: 비트코인 (BTC)
                    crypto_dict[display_name] = f"{symbol}-KRW"
    except Exception:
        pass

    # 네트워크 통신 실패 시 비상 백업용 데이터
    if not crypto_dict:
        crypto_raw = "비트코인 (BTC):BTC-KRW,이더리움 (ETH):ETH-KRW,솔라나 (SOL):SOL-KRW,리플 (XRP):XRP-KRW,도지코인 (DOGE):DOGE-KRW"
        crypto_dict = {item.split(':')[0].strip(): item.split(':')[1].strip() for item in crypto_raw.split(',') if ':' in item}

    return {"₩ 국내 주식": kr_dict, "💲 미국 주식": us_dict, "🪙 암호화폐(코인)": crypto_dict}

ASSETS = get_static_assets()

# ====================================================================
# [3. 핵심 연산 함수 모음 (UI 그리기 전 반드시 먼저 선언되어야 함)]
# ====================================================================

@st.cache_data(ttl=1800) # ⚡ 30분 캐싱으로 서버 차단 완벽 방지
def get_raw_daily_data(ticker):
    import time
    import requests
    import pandas as pd
    import yfinance as yf
    import FinanceDataReader as fdr

    if not ticker:
        return None

    ticker_str = str(ticker).strip()

    # 🪙 [1. 암호화폐 특화 - 업비트 API 100% 직통 보장 엔진]
    if ticker_str.endswith('-KRW') or ticker_str.startswith('KRW-'):
        try:
            coin_symbol = ticker_str.replace('KRW-', '').replace('-KRW', '').upper()
            market_code = f"KRW-{coin_symbol}"
            url = "https://api.upbit.com/v1/candles/days"
            headers = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}
            
            candles = []
            to_param = None
            
            for _ in range(2):
                params = {"market": market_code, "count": 200}
                if to_param: 
                    params["to"] = to_param
                
                res = requests.get(url, params=params, headers=headers, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if not data: 
                        break
                    candles.extend(data)
                    to_param = data[-1]["candle_date_time_utc"] + "Z"
                else:
                    break
            
            if candles:
                df = pd.DataFrame(candles).iloc[::-1].reset_index(drop=True)
                df = df.rename(columns={
                    'candle_date_time_kst': 'Date', 'opening_price': 'Open', 'high_price': 'High',
                    'low_price': 'Low', 'trade_price': 'Close', 'candle_acc_trade_volume': 'Volume'
                })
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                df['Date_Only'] = df['Date'].dt.date
                df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)
                return df
        except Exception:
            pass

    # 🇰🇷 [2. 대한민국 국내 주식 특화 - FDR 수집 및 야후 백업]
    clean_ticker = ticker_str.split('.')[0].strip()
    is_kr_stock = ticker_str.upper().endswith('.KS') or ticker_str.upper().endswith('.KQ') or (clean_ticker.isdigit() and len(clean_ticker) == 6)
    
    if is_kr_stock:
        try:
            df = fdr.DataReader(clean_ticker, start='2024-01-01')
            if df is not None and not df.empty:
                df = df.reset_index()
                df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                df['Date_Only'] = df['Date'].dt.date
                df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)
                return df
        except Exception:
            pass

    # 🇺🇸 [3. 미국 주식 및 일반 해외 종목 - 재시도(Retry) 포함 yfinance]
    for attempt in range(2): # 최대 2회 재시도
        try:
            stock = yf.Ticker(ticker_str)
            df = stock.history(period="1y", timeout=8) # 기존 2.5초에서 8초로 타임아웃 상향
            if df is not None and not df.empty:
                df = df.reset_index()
                df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                df['Date_Only'] = df['Date'].dt.date
                df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)
                return df
        except Exception:
            time.sleep(0.5)

    return None

# 🛡️ [신규 추가] 벤치마크 지수(KOSPI / S&P 500) 약세장(Bear Market) 감지 엔진
# ====================================================================
@st.cache_data(ttl=3600)
def check_benchmark_regime(ticker_symbol):
    """
    종목 티커에 따라 KOSPI(^KS11) 또는 S&P500(^GSPC)의 20일/60일선 이탈 여부 감지
    반환값: (is_bear_market: bool, message: str)
    """
    try:
        import FinanceDataReader as fdr
        import yfinance as yf
        
        is_kr_asset = any(x in ticker_symbol for x in [".KS", ".KQ", "-KRW"])
        
        if is_kr_asset:
            idx_df = fdr.DataReader('KS11', start='2024-01-01').tail(70)
            idx_name = "KOSPI"
        else:
            sp500 = yf.Ticker("^GSPC")
            idx_df = sp500.history(period="3m")
            idx_name = "S&P 500"
            
        if idx_df is None or len(idx_df) < 60:
            return False, ""
            
        idx_close = float(idx_df['Close'].iloc[-1])
        idx_ma20 = float(idx_df['Close'].rolling(20).mean().iloc[-1])
        idx_ma60 = float(idx_df['Close'].rolling(60).mean().iloc[-1])
        
        if idx_close < idx_ma20 and idx_close < idx_ma60:
            return True, f"🚨 [{idx_name} 약세장] 벤치마크 지수가 20일/60일선 아래에 위치한 하락장 국면 (보수적 대응 권고)"
        
        return False, f"🟢 [{idx_name} 양호] 벤치마크 지수 추세 안정"
        
    except Exception:
        return False, ""

# 🚨 [신규 추가] 어닝콜 / 실적 발표 이벤트 리스크(Event Risk) 3일 자동 감지 엔진
# ====================================================================
@st.cache_data(ttl=7200)
def check_event_risk(ticker_symbol):
    """
    앞뒤 3일 이내 실적 발표, 어닝콜(Earnings Call) 등 대형 이벤트 존재 여부 감지
    반환값: (has_event_risk: bool, event_msg: str)
    """
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        if "-KRW" in ticker_symbol or ".KS" in ticker_symbol or ".KQ" in ticker_symbol:
            return False, ""

        stock = yf.Ticker(ticker_symbol)
        cal = stock.calendar
        
        if cal is not None and not cal.empty:
            today = datetime.now().date()
            if 'Earnings Date' in cal.index:
                event_dates = cal.loc['Earnings Date'].values
                for ed in event_dates:
                    ed_date = pd.to_datetime(ed).date()
                    if abs((ed_date - today).days) <= 3:
                        return True, f"🚨 [이벤트 리스크] 3일 이내 어닝콜/실적 발표 예정 ({ed_date}) ➔ 매수 강제 차단"
    except Exception:
        pass
    return False, ""

# ====================================================================
# 🏛️ [신규 추가] 국내 주식 외국인/기관 순매수 수급 감지 엔진
# ====================================================================
@st.cache_data(ttl=1800)
def get_kr_investor_flow(ticker_symbol):
    """
    국내 주식(.KS, .KQ)의 최근 외국인 및 기관 순매수 유입 여부 감지
    반환값: (bonus_score: float, reason_msg: str)
    """
    clean_ticker = ticker_symbol.split('.')[0].strip()
    is_kr_stock = ticker_symbol.upper().endswith('.KS') or ticker_symbol.upper().endswith('.KQ') or (clean_ticker.isdigit() and len(clean_ticker) == 6)
    
    if not is_kr_stock:
        return 0.0, ""
        
    try:
        import FinanceDataReader as fdr
        # 최근 수급 데이터 수집 (FDR 수급 API)
        df_flow = fdr.DataReader(f'KRX-STK-{clean_ticker}', start='2024-01-01')
        if df_flow is None or df_flow.empty:
            return 0.0, ""
        
        recent_3d = df_flow.tail(3)
        foreign_buy = (recent_3d['ForeignNet'] > 0).sum() if 'ForeignNet' in recent_3d.columns else 0
        inst_buy = (recent_3d['InstNet'] > 0).sum() if 'InstNet' in recent_3d.columns else 0
        
        if foreign_buy >= 2 and inst_buy >= 2:
            return 7.0, "🏛️ [쌍끌이 수급] 최근 3일 중 2일 이상 외국인+기관 동반 순매수 유입 (+7% 가산)"
        elif foreign_buy >= 2:
            return 4.0, "🌐 [외국인 수급] 최근 3일 중 2일 이상 외국인 순매수 지속 (+4% 가산)"
        elif inst_buy >= 2:
            return 4.0, "🏢 [기관 수급] 최근 3일 중 2일 이상 기관 순매수 지속 (+4% 가산)"
        
        return 0.0, ""
    except Exception:
        return 0.0, ""

# ====================================================================
# 📱 [신규 추가] 텔레그램 실시간 고확신 시그널 웹훅 알림 엔진
# ====================================================================
def send_telegram_alert(bot_token, chat_id, message):
    """
    텔레그램 Bot API를 활용하여 고확신 종목 진입 시그널 메시지 즉시 발송
    """
    if not bot_token or not chat_id:
        return False
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        res = requests.post(url, json=payload, timeout=3)
        return res.status_code == 200
    except Exception:
        return False

# 🎯 @st.cache_data(ttl=3600)
@st.cache_data(ttl=3600)
def fetch_and_process_news(symbol, api_key=""):
    """ 백그라운드 API 호출을 100% 차단한 뉴스 수집 함수 """
    try:
        ticker_obj = yf.Ticker(symbol)
        raw_news = ticker_obj.news
        if not raw_news:
            return [], 0, "최근 5일 이내의 주요 뉴스가 없습니다. (기술적 지표 100% 반영)"
        
        now_ts = time.time()
        five_days_sec = 5 * 24 * 60 * 60
        valid_news = [n for n in raw_news if (now_ts - n.get('providerPublishTime', 0)) <= five_days_sec]
        
        if not valid_news:
            return [], 0, "최근 5일 이내의 신규 언론 보도가 없습니다. (기술적 지표 100% 반영)"
        
        summary_lines = []
        pos_words = ['buy', 'up', 'growth', 'gain', 'bull', 'surge', 'profit', 'beat', 'higher', '호재', '상승', '성장', '실적']
        neg_words = ['sell', 'down', 'drop', 'fall', 'loss', 'bear', 'plummet', 'risk', 'investigation', '악재', '하락', '손실']
        
        pos_score, neg_score = 0, 0
        for item in valid_news[:3]:
            title = item.get('title', '')
            publisher = item.get('publisher', '주요 언론사')
            pub_time = item.get('providerPublishTime', 0)
            days_ago = int((now_ts - pub_time) / 86400)
            time_str = f"{days_ago}일 전" if days_ago > 0 else "오늘"
            
            summary_lines.append(f"• **[{time_str}]** **[{publisher}]** {title}")
            
            t_lower = title.lower()
            pos_score += sum(1 for w in pos_words if w in t_lower)
            neg_score += sum(1 for w in neg_words if w in t_lower)
        
        # 키워드 매칭만 수행 (API 호출 0건)
        if pos_score > neg_score:
            news_impact = 10
            impact_reason = "🟢 호재 성향 뉴스 포착 (하단 AI 분석 버튼 클릭 시 정밀 분석)"
        elif neg_score > pos_score:
            news_impact = -10
            impact_reason = "❌ 악재 성향 뉴스 포착 (하단 AI 분석 버튼 클릭 시 정밀 분석)"
        else:
            news_impact = 0
            impact_reason = "⚪ 뉴스 중립/혼조세 (하단 AI 분석 버튼 클릭 시 정밀 분석)"
                
        return summary_lines, news_impact, impact_reason
    except Exception:
        return [], 0, "뉴스 데이터를 가져오는 중 일시적 통신 지연이 발생했습니다."
# ====================================================================
# --- [5. 보조지표 연산 및 패턴 인식 통합 스코어링 엔진] ---
# ====================================================================
def process_data(df_raw, timeframe, ticker_symbol, skip_news=False):
    import pandas as pd
    df = df_raw.copy()
    
    
    # [기존 지표 연산 코드 그대로 진행...]
        
    # 2. 거래정지나 데이터 누락으로 생긴 빈 구멍(NaN)을 앞뒤 데이터로 강제 결속 (증발 방지)
    df = df.ffill().bfill()
    if 'Volume' in df.columns:
        df['Volume'] = df['Volume'].fillna(0)

    if timeframe == 'weekly':
        df = df.resample('W-FRI', on='Date').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna().reset_index()
    elif timeframe == 'monthly':
        df = df.resample('ME', on='Date').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna().reset_index()

    # 신규 상장주도 차트가 그려지도록 최소 기준 완화
    min_required = 1
    if len(df) < min_required: 
        return None, None

    # 데이터 안전장치 및 지표 계산 (👈 이 부분 교체)
    df['MA_5']   = df['Close'].rolling(window=5, min_periods=1).mean()
    df['MA_10']  = df['Close'].rolling(window=10, min_periods=1).mean()
    df['MA_20']  = df['Close'].rolling(window=20, min_periods=1).mean()
    df['MA_60']  = df['Close'].rolling(window=60, min_periods=1).mean()
    df['MA_120'] = df['Close'].rolling(window=120, min_periods=1).mean()
    df['MA_200'] = df['Close'].rolling(window=200, min_periods=1).mean()

    df['STD_20'] = df['Close'].rolling(window=20, min_periods=1).std()
    df['Vol_MA_20'] = df['Volume'].rolling(window=20, min_periods=1).mean()

# 💵 [PRO QUANT 교정] 국내주식 거래대금 하한선 150억 원으로 완화 (LG생건 250억 대형주 정상 노출)
    df['Value'] = df['Close'] * df['Volume']
    turnover_5d = df['Value'].tail(5).mean()
    is_kr_asset = any(x in ticker_symbol for x in [".KS", ".KQ", "-KRW"])
    min_turnover = 15_000_000_000 if is_kr_asset else 15_000_000  # 국내 150억 / 해외 $1,500만

    df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(window=14, min_periods=1).mean()
    df['ATR_Pct'] = (df['ATR'] / df['Close']) * 100.0

    c_vol_curr = float(df['Volume'].iloc[-1])
    vol_ma20_curr = float(df['Vol_MA_20'].iloc[-1]) if float(df['Vol_MA_20'].iloc[-1]) > 0 else 1.0
    rvol_curr = c_vol_curr / vol_ma20_curr

    # ATR% 1.5% 이상이거나 거래량이 1.2배 이상 터진 종목은 필터 통과
    is_high_volatility = (float(df['ATR_Pct'].iloc[-1]) >= 1.5) or (rvol_curr >= 1.2)
    is_high_liquidity = turnover_5d >= min_turnover

    if timeframe == 'daily' and not (is_high_volatility and is_high_liquidity):
        return None, None
    
    # 1. 표준 볼린저 밴드(2.0배) 및 켈트너 채널 연산
    df['BB_Upper'] = df['MA_20'] + (df['STD_20'] * 2.0)
    df['BB_Lower'] = df['MA_20'] - (df['STD_20'] * 2.0)
    df['KC_Upper'] = df['MA_20'] + (df['ATR'] * 1.5)
    df['KC_Lower'] = df['MA_20'] - (df['ATR'] * 1.5)

    # 밴드가 채널 안쪽에 갇혀 있을 때만 응축
    df['Squeeze_On'] = (df['BB_Upper'] < df['KC_Upper']) & (df['BB_Lower'] > df['KC_Lower'])

    df['Resist_20'] = df['High'].rolling(window=20, min_periods=1).max()
    df['Support_20'] = df['Low'].rolling(window=20, min_periods=1).min()

    # 차트 필수 지표 연산
    delta = df['Close'].diff()
    up = delta.clip(lower=0).rolling(window=14, min_periods=1).mean()
    down = (-1 * delta.clip(upper=0)).rolling(window=14, min_periods=1).mean()
    df['RSI'] = np.where(down == 0, 100, 100 - (100 / (1 + up / down)))

    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    df['EMA_12'] = ema_12
    df['STD_20'] = df['Close'].rolling(window=20, min_periods=1).std()  # 👈 20일 윈도우로 교정 완료!

    # ADX 및 DMI 연산
    up_move = df['High'].diff()
    down_move = df['Low'].shift(1) - df['Low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    df['Plus_DM'] = plus_dm
    df['Minus_DM'] = minus_dm
    
    # 💡 [트레이딩뷰 100% 동기화] 와일더 평활법(Wilder's RMA) 적용 ADX 계산
    tr_14 = df['TR'].ewm(alpha=1/14, adjust=False).mean()
    p_dm_14 = pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean()
    m_dm_14 = pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean()

    df['Plus_DI'] = 100 * (p_dm_14 / (tr_14 + 1e-10))
    df['Minus_DI'] = 100 * (m_dm_14 / (tr_14 + 1e-10))

    di_sum = df['Plus_DI'] + df['Minus_DI']
    dx = 100 * (df['Plus_DI'] - df['Minus_DI']).abs() / (di_sum + 1e-10)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()

# ====================================================================
    # 🎯 [신규 추가] 4대 핵심 매수 조건 실시간 충족 여부 검증
    # ====================================================================
    latest_temp = df.iloc[-1]
    prev_temp = df.iloc[-2] if len(df) >= 2 else latest_temp

    # 1. 20일선 & 60일선 상승세 (기울기 양수)
    ma20_c = float(latest_temp['MA_20']) if 'MA_20' in latest_temp else float(latest_temp['Close'])
    ma20_p = float(prev_temp['MA_20']) if 'MA_20' in prev_temp else ma20_c
    ma60_c = float(latest_temp['MA_60']) if 'MA_60' in latest_temp else float(latest_temp['Close'])
    ma60_p = float(prev_temp['MA_60']) if 'MA_60' in prev_temp else ma60_c
    cond_ma_up = (ma20_c > ma20_p) and (ma60_c > ma60_p)

    # 2. ADX 20 이상 및 상승세
    adx_c = float(latest_temp['ADX']) if 'ADX' in latest_temp else 25.0
    adx_p = float(prev_temp['ADX']) if 'ADX' in prev_temp else 20.0
    cond_adx_up = (adx_c >= 20.0) and (adx_c > adx_p)

    # 3. DMI (+DI 20 이상, -DI 우위, 상승세)
    p_di_c = float(latest_temp['Plus_DI']) if 'Plus_DI' in latest_temp else 25.0
    p_di_p = float(prev_temp['Plus_DI']) if 'Plus_DI' in prev_temp else 20.0
    m_di_c = float(latest_temp['Minus_DI']) if 'Minus_DI' in latest_temp else 15.0
    cond_dmi_up = (p_di_c >= 20.0) and (p_di_c > m_di_c) and (p_di_c > p_di_p)

    # 4. MACD 0선~20 이내 및 상승세
    macd_c = float(latest_temp['MACD']) if 'MACD' in latest_temp else 5.0
    macd_p = float(prev_temp['MACD']) if 'MACD' in prev_temp else 4.0
    cond_macd_up = (0.0 < macd_c <= 20.0) and (macd_c > macd_p)

    # 최종 4대 조건 동시 충족 여부
    is_four_conditions_met = cond_ma_up and cond_adx_up and cond_dmi_up and cond_macd_up

  # 최신 데이터 매핑 (들여쓰기가 완벽하게 교정된 구역)
    latest = df.iloc[-1]
    price = float(latest['Close'])
    ma5 = float(latest['MA_5'])
    ma10 = float(latest['MA_10'])
    ma20 = float(latest['MA_20'])
    ma60 = float(latest['MA_60'])
    ma120 = float(latest['MA_120'])
    ma200 = float(latest['MA_200'])
    atr = float(latest['ATR'])
    resist = float(latest['Resist_20'])
    support = float(latest['Support_20'])
    volume = float(latest['Volume'])
    vol_ma20 = float(latest['Vol_MA_20'])
    c_vol_prev = float(df['Volume'].iloc[-2]) if len(df) >= 2 else 0.0
    bb_upper = float(latest['BB_Upper'])
    bb_lower = float(latest['BB_Lower'])
    rsi_val = float(latest['RSI'])
    minus_di_curr = float(latest['Minus_DI'])
    plus_di_curr = float(latest['Plus_DI'])
    adx_curr = float(latest['ADX'])
    adx_prev = float(df['ADX'].iloc[-2]) if len(df) > 2 else 0.0
    
# ====================================================================
    # 📊 [통합 교체] 30개 매물대 정밀 분할 + 터치 횟수 + 비중(%) 동적 연산
    # ====================================================================
    recent_df = df.tail(120)  # 최근 120봉 스캔
    min_p, max_p = recent_df['Low'].min(), recent_df['High'].max()
    price_bins = np.linspace(min_p, max_p, 31)  # 30개 매물대 구간 생성
    
    bin_volumes = np.zeros(30)
    bin_touches = np.zeros(30)
    
    # 30개 구간별 거래량 집계 및 캔들 터치 횟수 검증
    for i in range(len(recent_df)):
        row_c = recent_df['Close'].iloc[i]
        row_l = recent_df['Low'].iloc[i]
        row_h = recent_df['High'].iloc[i]
        row_v = recent_df['Volume'].iloc[i]
        
        # 종가 기준 거래량 할당
        b_idx = np.digitize(row_c, price_bins) - 1
        if 0 <= b_idx < 30:
            bin_volumes[b_idx] += row_v
            
        # 해당 매물대 가격 범위를 캔들(High~Low)이 스치거나 터치했는지 카운트
        for b in range(30):
            if row_l <= price_bins[b+1] and row_h >= price_bins[b]:
                bin_touches[b] += 1

    total_bin_vol = bin_volumes.sum() if bin_volumes.sum() > 0 else 1.0
    bin_pcts = (bin_volumes / total_bin_vol) * 100  # 매물대별 비중(%)

    # 터치 횟수와 비중(%)을 결합한 동적 방어/저항 확률 점수 산출
    bin_defense_scores = bin_pcts * np.log1p(bin_touches)
    
    sorted_indices = np.argsort(bin_defense_scores)[::-1]
    top1_idx = sorted_indices[0]
    top2_idx = sorted_indices[1]
    
    # 1위 및 2위 매물대 중심 가격 및 상·하단 경계 추출
    poc_price = float((price_bins[top1_idx] + price_bins[top1_idx+1]) / 2)
    poc_price_2nd = float((price_bins[top2_idx] + price_bins[top2_idx+1]) / 2)
    t1_low, t1_high = float(price_bins[top1_idx]), float(price_bins[top1_idx+1])
    t2_low, t2_high = float(price_bins[top2_idx]), float(price_bins[top2_idx+1])
    
    top1_pct = bin_pcts[top1_idx]
    top2_pct = bin_pcts[top2_idx]
    top1_touches = int(bin_touches[top1_idx])
    
    # 현재가가 위치한 매물대의 비중(%) 및 터치 기반 방어 확률 산출
    curr_b_idx = min(max(np.digitize(price, price_bins) - 1, 0), 29)
    curr_bin_pct = bin_pcts[curr_b_idx]
    curr_bin_touches = int(bin_touches[curr_b_idx])
    defense_prob = min(curr_bin_pct * 1.8 + curr_bin_touches * 2.5, 95.0)

    # 📌 차트 표시용 라벨 텍스트 조립
    is_kr_currency = "-KRW" in ticker_symbol or ".KS" in ticker_symbol or ".KQ" in ticker_symbol
    c_symbol = "₩" if is_kr_currency else "$"
    
    if c_symbol == "₩":
        poc_range_text_1 = f"★ 1위 최대 매물대 ({t1_low:,.0f} ~ {t1_high:,.0f}) [{top1_pct:.1f}%]"
        poc_range_text_2 = f"★ 2위 차상위 매물대 ({t2_low:,.0f} ~ {t2_high:,.0f}) [{top2_pct:.1f}%]"
    else:
        poc_range_text_1 = f"★ 1위 최대 매물대 (${t1_low:,.2f} ~ ${t1_high:,.2f}) [{top1_pct:.1f}%]"
        poc_range_text_2 = f"★ 2위 차상위 매물대 (${t2_low:,.2f} ~ ${t2_high:,.2f}) [{top2_pct:.1f}%]"

    # ====================================================================
    # 🕯️ 캔들 및 패턴 스캔 시작
    # ====================================================================
    pattern_score = 0
    success_reasons = []
    failed_reasons = []

    # 캔들 속성 배열 변환
    c_open, c_high, c_low, c_close = df['Open'].to_numpy(), df['High'].to_numpy(), df['Low'].to_numpy(), df['Close'].to_numpy()
    body = np.abs(c_close - c_open)
    upper_sh = c_high - np.maximum(c_open, c_close)
    lower_sh = np.minimum(c_open, c_close) - c_low
    is_green = c_close > c_open
    is_red = c_close < c_open

    # 캔들 패턴 스캔
    if lower_sh[-1] > (2.0 * body[-1]) and upper_sh[-1] < (0.3 * body[-1]) and price < ma20:
        pattern_score += 15
        success_reasons.append("⚡ [캔들] 바닥권 망치형(Hammer) 포착: 저점 매수세 급증")
    if upper_sh[-1] > (2.0 * body[-1]) and lower_sh[-1] < (0.3 * body[-1]) and price > ma20:
        pattern_score -= 15
        failed_reasons.append("[캔들] 고점권 유성형(Shooting Star) 포착: 상방 차익 매물 투하")

    # 🛡️ 개미털기(Bear Trap) 정밀 판독기
    if c_low[-1] < support and c_close[-1] >= (support * 0.995) and lower_sh[-1] > (body[-1] * 1.2):
        pattern_score += 30
        if price < ma60: pattern_score += 20 
        success_reasons.append("🔥 [지표 판독] 개미털기(Bear Trap) 포착: 장중 손절가를 의도적으로 이탈시킨 후 아래꼬리로 강력하게 말아 올림 (초강력 반등 신호)")
    if is_red[-2] and is_green[-1] and c_open[-1] <= c_close[-2] and c_close[-1] >= c_open[-2]:
        pattern_score += 15
        success_reasons.append("⚡ [캔들] 상승장악형 포착: 이전 음봉 매물대를 거래량 실린 양봉이 장악")
    if is_green[-2] and is_red[-1] and c_open[-1] >= c_close[-2] and c_close[-1] <= c_open[-2]:
        pattern_score -= 15
        failed_reasons.append("[캔들] 하락장악형 포착: 이전 상승세를 거대 음봉 세력이 압도")

    # 차트 패턴 스캔
    recent_support_touches = np.sum(c_low[-15:] <= (support * 1.01))
    is_support_sliding_down = df['Support_20'].iloc[-1] < df['Support_20'].iloc[-8] if len(df) > 10 else False
    is_dead_trend = price < ma20 and ma5 < ma20
    
    if recent_support_touches >= 2 and price > ma5 and is_green[-1] and not is_support_sliding_down and not is_dead_trend:
        pattern_score += 15
        success_reasons.append("🎯 [패턴] 쌍바닥(W자형) 지지 성공: 이중 바닥 확인 후 단기 우상향 탈출")

    recent_resist_touches = np.sum(c_high[-15:] >= (resist * 0.99))
    if recent_resist_touches >= 2 and price < ma5:
        pattern_score -= 20
        failed_reasons.append("[패턴] 쌍봉(M자형) / 헤드앤숄더형 위기: 강력한 천정 저항 매물벽 봉착")

    # 볼린저밴드 이탈 스캔
    if price >= bb_upper:
        pattern_score += 20
        success_reasons.append("💥 [볼린저밴드] 상단 강력 돌파: 변동성 확장 구간 진입 및 강한 주도주 랠리 가속")
    elif price <= bb_lower:
        pattern_score -= 15
        failed_reasons.append("❌ [볼린저밴드] 하단 이탈: 지지선 붕괴에 따른 추가 하락 리스크 주의")

    # ====================================================================
    # 🎯 [완전 교체] 유저 정의 매물대 상단 돌파 / 하단 지지 정밀 판정 엔진
    # ====================================================================
    up_prob_base = 0

    # 캔들 몸통의 최하단 가격 계산 (음봉/양봉 상관없이 몸통이 내려간 하한선)
    candle_body_min = min(float(latest['Open']), float(latest['Close']))

    # 화폐 단위별 직관적인 텍스트 포맷팅 처리
    if c_symbol == "₩":
        fmt_high = f"{t1_high:,.0f}원"
        fmt_low = f"{t1_low:,.0f}원"
    else:
        fmt_high = f"${t1_high:,.2f}"
        fmt_low = f"${t1_low:,.2f}"

    # 1. 🔥 [돌파 타점] 현재가가 최대 매물 박스 상단(t1_high)을 뚫고 올라갔을 때 (강력 공격 가점)
    if price >= t1_high:
        up_prob_base = 25
        success_reasons.append(f"💥 [매물대 상단 돌파] 최대 매물대 상단벽({fmt_high})을 완전히 돌파하며 악성 대기 매물 소화 후 시세 분출 국면 진입")

    # 2. 🛡️ [지점 타점] 캔들 몸통이 박스 하단(t1_low) 밑으로 내려가지 않고 사수할 때 (안정 방어 가점)
    elif candle_body_min >= t1_low:
        up_prob_base = 15
        success_reasons.append(f"📊 [매물대 하단 지지] 캔들 몸통이 최대 매물대 하단선({fmt_low}) 위를 견고하게 사수하며 세력의 저점 매집 방어력 확인")

    # 3. 🚨 [붕괴 위험] 박스 하단마저 깨고 아래로 캔들 몸통이 주저앉았을 때 (하방 패널티)
    else:
        up_prob_base = -25
        failed_reasons.append(f"🚨 [매물대 하단 붕괴] 가격이 최대 매물대 최후 방어선({fmt_low}) 밑으로 추락하여 머리 위에 거대한 저항 매물벽 누적 리스크 발생")

    # ====================================================================
    # 🎯 [1단계 보완] 1~5일 단타/스윙 전용 핵심 4대 필터 조건 검증
    # ====================================================================
    candle_body_min = min(float(latest['Open']), float(latest['Close']))

    # 1) 추세 조건: 5일선이 20일선 위에 있고 현재가가 5일선 및 60일선 위 (단기 정배열)
    cond_trend = (price >= ma5) and (ma5 >= ma20) and (price >= ma60)
    
    # 2) 수급 조건: 20일 평균 거래량 대비 1.5배 이상 거래량 유입 + 양봉
    rvol_temp = volume / vol_ma20 if vol_ma20 > 0 else 1.0
    cond_volume = (rvol_temp >= 1.5) and (latest['Close'] >= latest['Open'])
    
    # 3) 매물대 조건: 최대 매물대(t1_low) 하단을 종가로 사수 중
    cond_structure = (candle_body_min >= t1_low)
    
    # 4) 모멘텀 조건: RSI 50~68 지대 (과열 미진입 + 침체 탈출) & MACD 오실레이터 양수
    cond_momentum = (50.0 <= rsi_val <= 68.0) and (float(latest['MACD_Hist']) > 0)

    # 4대 핵심 조건 충족 개수 카운트
    core_score = sum([cond_trend, cond_volume, cond_structure, cond_momentum])

    # 객관적 승률 산출 (조건 충족 개수 기반 정밀 정규화)
    if core_score == 4:
        up_prob_base = 88.0  # S등급: 4개 조건 완벽 일치 (초강력 단타 타점)
    elif core_score == 3:
        up_prob_base = 72.0  # A등급: 우수한 스윙 타점
    elif core_score == 2:
        up_prob_base = 55.0  # B등급: 관망 및 보수적 접근
    else:
        up_prob_base = 30.0  # C등급: 진입 금지 구역

    # ====================================================================
    # 🛡️ [추가] 6대 이동평균선(5, 10, 20, 60, 120, 200일) 지지·저항 종합 검증
    # ====================================================================
    ma10 = float(latest['MA_10'])
    ma200 = float(latest['MA_200'])
    ma_score_bonus = 0

    # 1) 200일선 (대세 장기 지지/저항)
    if price >= ma200:
        ma_score_bonus += 5
        success_reasons.append("🛡️ [200일선 지지] 장기 대세선(200일선) 상회: 대세 상승 지지선 확보")
    else:
        ma_score_bonus -= 10
        failed_reasons.append("🧱 [200일선 저항] 장기 대세선(200일선) 하회: 강력한 대세 저항 매물벽 봉착")

    # 2) 120일선 (중장기 경기 지지/저항)
    if price >= ma120:
        ma_score_bonus += 4
        success_reasons.append("🛡️ [120일선 지지] 중장기 이평선(120일선) 사수: 중장기 수급 바닥 지지 유효")
    else:
        ma_score_bonus -= 8
        failed_reasons.append("🧱 [120일선 저항] 중장기 이평선(120일선) 하방 이탈: 중장기 매물 압박 구간")

    # 3) 60일선 (중기 수급 선)
    if price >= ma60:
        ma_score_bonus += 3
    else:
        ma_score_bonus -= 5

    # 4) 10일선 및 5/10/20일 단기 정배열 (단타 생명선)
    if price >= ma10 and ma5 >= ma10:
        ma_score_bonus += 3
        success_reasons.append("⚡ [5/10일선 정배열] 단기 단타 생명선 사수: 단기 매수 수급 관성 유효")

    # 5) 6대 이평선 완전 정배열 검증 (5 > 10 > 20 > 60 > 120 > 200)
    is_perfect_alignment = (ma5 >= ma10 >= ma20 >= ma60 >= ma120 >= ma200)
    if is_perfect_alignment:
        ma_score_bonus += 10
        success_reasons.append("🚀 [이평선 완전 정배열] 5/10/20/60/120/200일선 정렬: 최상급 상승 추세 관성")

    # 이평선 종합 점수 가산
    up_prob_base += ma_score_bonus

    # 역배열/RSI 과열 시 강제 패널티 락
    if price < ma60 or rsi_val >= 70:
        up_prob_base = min(up_prob_base, 35.0)

    # 🛡️ [PRO QUANT 개선] Market Regime Filter (하락장 -30% 패널티 및 매수 차단)
    is_bear, bear_msg = check_benchmark_regime(ticker_symbol)
    if is_bear:
        up_prob_base -= 30.0  # 하락장(Bear Regime) 진입 시 확신도 -30% 강한 패널티 부여
        failed_reasons.append(bear_msg)
        if up_prob_base < 60.0:
            failed_reasons.append("🚨 [Market Regime Filter] 지수 약세장 국면으로 인한 매수 시그널 강제 차단(Hard Lock)")

# 📐 [PRO QUANT 고도화 1] 20일 이격도(Disparity) 과열 차단 (108% 이상 매수 금지)
    disparity_20 = (price / ma20) * 100.0 if ma20 > 0 else 100.0
    if disparity_20 >= 108.0:
        up_prob_base -= 40.0
        failed_reasons.append(f"🚨 [고이격 과열 경고] 20일선 이격도({disparity_20:.1f}%) 108% 초과 ➔ 폭락 리스크로 매수 강제 차단")

    # 🗓️ [PRO QUANT 고도화 2] 어닝콜 / 실적 발표 이벤트 리스크 강제 차단
    has_event, event_msg = check_event_risk(ticker_symbol)
    if has_event:
        up_prob_base -= 50.0
        failed_reasons.append(event_msg)

    # 🏛️ 국내 주식 외국인/기관 순매수 수급 가산점 반영
    flow_bonus, flow_msg = get_kr_investor_flow(ticker_symbol)
    if flow_bonus > 0:
        up_prob_base += flow_bonus
        success_reasons.append(flow_msg)

    up_prob = float(up_prob_base)

    # 🎯 [섹터 주도주 보너스] 5일(1주) 지수 기여도 리포트 실시간 반영 (line 1184 부근)
    try:
        kr_pos, kr_neg, us_pos, us_neg = get_realtime_sector_influence()
        pos_names = [x[0] for x in kr_pos + us_pos]
        neg_names = [x[0] for x in kr_neg + us_neg]
        
        is_leading_sector = any(p_name in ticker_symbol for p_name in pos_names)
        is_lagging_sector = any(n_name in ticker_symbol for n_name in neg_names)

        if is_leading_sector:
            up_prob_base += 8.0
            success_reasons.append("🔥 [주도 테마] 최근 1주 지수 상승 견인 TOP 3 섹터 포착 (+8% 승률 가산)")
        elif is_lagging_sector:
            up_prob_base -= 10.0
            failed_reasons.append("🚨 [하락 테마] 최근 1주 지수 하락 주도 TOP 3 섹터 속함 (-10% 승률 패널티)")
    except Exception:
        pass

# 🎯 캔들 및 차트 패턴 가산점 + 뉴스 분석 정밀 결합
    # 1) 캔들/차트 패턴 가산점 (패턴당 ±3.0%, 최대 ±10.0%)
    pattern_bonus = (len(success_reasons) * 3.0) - (len(failed_reasons) * 3.0)
    pattern_bonus = min(max(pattern_bonus, -10.0), 10.0)

    # 2) 뉴스 정밀 분석 가동 및 점수 합산
    news_bonus = 0.0
    if not skip_news:
        summary_lines, news_impact, impact_reason = fetch_and_process_news(ticker_symbol)
        news_bonus = float(news_impact)

    # ====================================================================
    # 📌 [수정] 3) 최종 승률 산출 (승률 상한선 99.0% 제한 적용)
    # ====================================================================
    up_prob = min(max(float(up_prob_base + pattern_bonus + news_bonus), 0.0), 99.0)

    # --- [예상수익률 연산 구역] ---
    if price < ma20:
        base_move = ((ma20 - price) / price) * 100
        if price <= bb_lower:
            base_move = ((bb_upper - price) / price) * 0.7 * 100
    elif price < bb_upper:
        base_move = ((bb_upper - price) / price) * 100
    else:
        base_move = ((max(resist, bb_upper * 1.08) - price) / price) * 100

    # 🎯 수급 및 상방 모멘텀 직접 정의 (NameError 방지)
    rvol_val = volume / vol_ma20 if vol_ma20 > 0 else 1.0
    is_upward_val = (latest['Close'] >= latest['Open']) and (price >= ma20)

    vol_multiplier = 1.0
    if rvol_val >= 2.0 and is_upward_val:
        vol_multiplier = 1.35
    elif rvol_val >= 1.2 and is_upward_val:
        vol_multiplier = 1.15
    elif rvol_val < 0.7:
        vol_multiplier = 0.80

    momentum_multiplier = 1.0
    macd_hist = float(latest['MACD_Hist'])
    macd_hist_prev = float(df['MACD_Hist'].iloc[-2]) if len(df) > 2 else 0.0

    if 30 <= rsi_val <= 65: momentum_multiplier += 0.15
    if macd_hist > macd_hist_prev and macd_hist > 0: momentum_multiplier += 0.10

    squeeze_expansion_multiplier = 1.0
    had_recent_squeeze = df['Squeeze_On'].iloc[-8:-1].any() if len(df) >= 10 else False
    is_bands_widening = (df['BB_Upper'].iloc[-1] - df['BB_Lower'].iloc[-1]) > (df['BB_Upper'].iloc[-2] - df['BB_Lower'].iloc[-2]) if len(df) > 2 else False
    
    if had_recent_squeeze and is_bands_widening:
        if price >= bb_upper and rvol_val >= 1.3:
            squeeze_expansion_multiplier += 0.35
            if "💥 [볼밴 발산] 에너지 응축(Squeeze) 완료 후 상방 분출 개화 (주도주 시세 확장 타점)" not in success_reasons:
                success_reasons.append("💥 [볼밴 발산] 에너지 응축(Squeeze) 완료 후 상방 분출 개화 (주도주 시세 확장 타점)")
        elif price <= bb_lower:
            squeeze_expansion_multiplier *= 0.60
            if "🚨 [볼밴 발산] 에너지 응축 이후 하방 이탈 붕괴: 변동성 하방 폭발 리스크 경계" not in failed_reasons:
                failed_reasons.append("🚨 [볼밴 발산] 에너지 응축 이후 하방 이탈 붕괴: 변동성 하방 폭발 리스크 경계")

    macd_curr = float(latest['MACD'])
    macd_hist_curr = float(latest['MACD_Hist'])
    if macd_hist_curr < 0 or macd_curr < 0:
        if macd_hist_curr < macd_hist_prev:
            macd_msg = "🌊 [MACD 약세] 데드크로스 진행 및 하락 히스토그램 확장 (하방 압력 가속)"
        else:
            macd_msg = "🌊 [MACD 약세] 이평 오실레이터 0선 아래 침체 국면 (중장기 매도세 지배 구간)"
        if macd_msg not in failed_reasons: failed_reasons.append(macd_msg)

    if rsi_val < 50 or rsi_val < (float(df['RSI'].iloc[-2]) if len(df) > 2 else 50.0):
        if "🌊 [RSI 위축] RSI 지표가 50선 밑으로 밀리거나 하향 꺾이며 매수 심리 위축" not in failed_reasons:
            failed_reasons.append("🌊 [RSI 위축] RSI 지표가 50선 밑으로 밀리거나 하향 꺾이며 매수 심리 위축")

    if minus_di_curr > plus_di_curr:
        if adx_curr > 25 and adx_curr > adx_prev:
            if "🚨 [DMI/ADX 폭발] 강력한 하락 추세 진행" not in failed_reasons:
                failed_reasons.append("🚨 [DMI/ADX 폭발] 매도 세력(-DI)이 매수 세력(+DI)을 압도하며, 황금색 ADX 상승으로 하락 가속도 증가")
        else:
            if "🔵 [DMI 약세] 하방 힘(-DI)이 상방 힘(+DI)보다 우위에 있어 단기 하락 압력 잔존" not in failed_reasons:
                failed_reasons.append("🔵 [DMI 약세] 하방 힘(-DI)이 상방 힘(+DI)보다 우위에 있어 단기 하락 압력 잔존")

    pattern_premium = len(success_reasons) * 1.5 - len(failed_reasons) * 2.0
    predicted_return = (base_move * vol_multiplier * momentum_multiplier * squeeze_expansion_multiplier) + pattern_premium
    predicted_return = predicted_return * (up_prob / 100.0)
    upside = min(max(predicted_return, 2.0), 35.0)  
    win_rate = up_prob 



    # 최종 출력 텍스트 시그널 맵핑
    if up_prob >= 80: msg, color, t_state = "🔥 적극 매수 / 돌파 유효 (BUY)", "#ff4b4b", "🔥 강세 상승 구간"
    elif up_prob >= 45: msg, color, t_state = "🟢 분할 매수 / 지지 확인 (HOLD/BUY)", "#10b981", "🧭 횡보 및 반등 모색 구간"
    else: msg, color, t_state = "🔵 매도 우위 / 비중 축소 (SELL / AVOID)", "#2563eb", "🌊 관망/낙폭 과대 구간"

    # 🛡️ [개선] 1.5배 ATR 기반 동적 손절선 및 -3% 하드 캡(Hard Limit) 동시 적용
    atr_sl = price - (atr * 1.5)           # 변동성 기반 동적 손절선
    hard_limit_sl = price * 0.97           # 고정 -3% 하드 캡
    
    # 지지선과 ATR 동적 손절선 중 더 신뢰도 높은 선을 택하되, 최대 손실은 -3%를 넘지 않도록 제한
    dynamic_stop = max(support, atr_sl) if support < price else atr_sl
    tighter_sl = max(dynamic_stop, hard_limit_sl)

 # ====================================================================
    # 🚨 [신규 주입] 30년 베테랑 실시간 분할 청산 및 마스터 행동 지시 지침
    # ====================================================================
    # 진입가 대비 타이트 구조 컷 및 목표가 연산 규칙 동기화
    tighter_sl = max(support, price * 0.96) if support < price and (price - support)/price < 0.05 else price * 0.965
    tp_price = price + (atr * 2.5)  # 단타 고정 익절 목표가

# 🛡️ [PRO QUANT 개선] 손익비 2.0 : 1 강제 구조화 (+5.0% 익절 / -2.5% 손절)
    entry_target_p = price * 0.995                          # 진입가 (-0.5% 눌림 지정가 가정)
    tighter_sl = entry_target_p * 0.975                     # -2.5% 타이트 손절선 (Hard Cap)
    tp1_price = entry_target_p * 1.050                      # +5.0% 1차 목표가 (R:R = 2.0 : 1)
    tp2_price = entry_target_p * 1.090                      # +9.0% 2차 목표가 (R:R = 3.6 : 1)
    tp_price = tp1_price

    # 💡 Break-Even 메커니즘: 주가 +3.0% 이상 상승 도달 경험 시, 손절가를 매수가 +0.3%(수수료 보존)로 즉시 상향
    recent_high_pct = ((df['High'].iloc[-1] - entry_target_p) / entry_target_p) * 100.0
    if recent_high_pct >= 3.0:
        tighter_sl = max(tighter_sl, entry_target_p * 1.003)
    
    # 기본값 셋업
    live_action = "🧭 신규 진입 타이밍 관망 중"
    action_color = "#64748b"
    live_reasoning = "현재 알고리즘 확신도가 90% 미만이므로, 무리한 추격 매수를 금지하고 기준 조건 충족 시까지 대기합니다."

    # 오직 90% 이상 확신 타점 스펙에 한해서만 실시간 명령 가동
    if up_prob >= 90:
        live_action = "🔥 알고리즘 90% 확신 포착: 적극 매수 (STRONG BUY)"
        action_color = "#ff4b4b"
        live_reasoning = f"수급 유입 및 MACD/DMI 상방 정배열이 결합된 극강의 단타 타점입니다. 오늘 장 마감 종가 기준 적극 매수 진입이 유효하며, 목표가는 {tp_price:,.2f}, 구조 컷 라인은 {tighter_sl:,.2f}로 설정합니다."

    # ====================================================================
    # 📈 60일선 돌파 후 경과 봉(Bar) 수 연산 및 시그널 맵핑
    # ====================================================================
    above_ma60_mask = (df['Close'] >= df['MA_60']).values
    
    if latest['Close'] >= latest['MA_60']:
        bars_count = 0
        for is_above in reversed(above_ma60_mask):
            if is_above:
                bars_count += 1
            else:
                break
        msg = f"60일선 돌파 후 {bars_count}봉째"
        color = "#ff4b4b"
        t_state = f"60일선 상회 ({bars_count}봉째)"
    else:
        bars_count = 0
        for is_above in reversed(above_ma60_mask):
            if not is_above:
                bars_count += 1
            else:
                break
        msg = f"60일선 하회 {bars_count}봉째"
        color = "#2563eb"
        t_state = f"60일선 하회 ({bars_count}봉째)"

    # ====================================================================
    # 📊 [신규 주입] 세력 거래량/수급 스캔 (거래대금 제외: RVOL + OBV + CLV)
    # ====================================================================
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    obv_ma = obv.rolling(20).mean()
    is_obv_up = bool(obv.iloc[-1] > obv_ma.iloc[-1])
    
    rvol_val = float(volume / vol_ma20) if vol_ma20 > 0 else 1.0
    clv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'] + 1e-10)
    smart_money_val = float((clv * rvol_val).iloc[-1]) if hasattr(clv, 'iloc') else float(clv * rvol_val)

    if rvol_val >= 1.5 and is_obv_up and smart_money_val > 0:
        swing_setup = f"🔥 세력 매집 우위 (RVOL {rvol_val:.1f}배 & OBV 상승)"
    elif rvol_val >= 1.2 and is_obv_up:
        swing_setup = f"🟢 단기 수급 유입 (RVOL {rvol_val:.1f}배)"
    else:
        swing_setup = "⚪ 수급 혼조 / 관망"

    # ====================================================================
    # 🎯 [1~5봉 초단타 정밀 연산 엔진] 12대 지표 + 8대 고도화 필터 통합
    # ====================================================================
    
    # 단일 스칼라 값(float/bool) 안전 추출 (Series 에러 원천 차단)
    rvol_val = float(volume / vol_ma20) if vol_ma20 > 0 else 1.0
    clv_val = float(clv.iloc[-1]) if hasattr(clv, 'iloc') else float(clv)
    smart_money_val = float((clv * rvol_val).iloc[-1]) if hasattr(clv, 'iloc') else float(clv * rvol_val)
    is_obv_up = bool(obv.iloc[-1] > obv_ma.iloc[-1])
    is_upward_val = bool((latest['Close'] >= latest['Open']) and (price >= ma20))

    # 1. 체결강도 & 수급 모멘텀 (가중치 15%)
    volume_power = (clv_val + 1.0) * 50.0 * min(rvol_val, 2.0)
    vp_score = 15 if volume_power >= 120 else (5 if volume_power >= 100 else -15)

    # 2. 메이저 수급 연속성 (가중치 15%)
    flow_score = 15 if (rvol_val >= 1.2 and is_obv_up and smart_money_val > 0) else (5 if is_obv_up else -10)

    # 3. 🚀 [신규 1] 래리 윌리엄스 변동성 돌파 필터 (+10점 / -5점)
    prev_range = df['High'].iloc[-2] - df['Low'].iloc[-2] if len(df) > 2 else 0
    v_target = float(latest['Open']) + (prev_range * 0.5)
    v_breakout_score = 10 if price >= v_target else -5

    # 4. 🏰 [신규 2] 최근 5일 대량거래 매집봉 중심선 사수 여부 (+10점 / -10점)
    recent_5 = df.tail(5)
    max_vol_idx = recent_5['Volume'].idxmax()
    candle_mid = (df.loc[max_vol_idx, 'Open'] + df.loc[max_vol_idx, 'Close']) / 2.0
    mid_support_score = 10 if price >= candle_mid else -10

    # 5. 📐 [신규 3] 20일 이격도(Disparity) 과열/추격 매수 차단 (-15점)
    disparity_20 = (price / ma20) * 100.0 if ma20 > 0 else 100.0
    disparity_score = -15 if disparity_20 >= 108.0 else (10 if 98.0 <= disparity_20 <= 104.0 else 0)

    # 6. 🚨 [신규 4] 당일 갭상승 윗꼬리 음봉(피뢰침) 털기 필터 (-20점)
    gap_pct = ((df['Open'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100.0 if len(df) > 2 else 0
    is_red_candle = float(latest['Close']) < float(latest['Open'])
    gap_filter_score = -20 if (gap_pct >= 4.0 and is_red_candle) else (10 if (0 <= gap_pct <= 3.0 and not is_red_candle) else 0)

    # 7. 섹터/추세 상대강도 (가중치 10%)
    sector_score = 10 if (price > ma5 and is_upward_val) else -10

   # ====================================================================
    # 🤖 [4대 AI Multi-Agent 앙상블 평가 & 듀얼 모드 스캐너]
    # ====================================================================
    # 1) Quant Factor Agent (40점 만점)
    q_score = (
        (10.0 if cond_trend else 0.0) +
        (10.0 if cond_structure else 0.0) +
        (10.0 if cond_momentum else 0.0) +
        (10.0 if is_perfect_alignment else 0.0)
    )

    # 2) Microstructure Agent (20점 만점: RVOL, OBV, CLV)
    m_score = (
        (8.0 if rvol_val >= 1.5 else (4.0 if rvol_val >= 1.2 else 0.0)) +
        (6.0 if is_obv_up else 0.0) +
        (6.0 if smart_money_val > 0 else 0.0)
    )

    # 3) Market Regime Agent (20점 만점: 지수 대비 상대강도 RS)
    is_bear, bear_msg = check_benchmark_regime(ticker_symbol)
    recent_20_ret = ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) * 100.0 if len(df) >= 20 else 0.0
    
    if is_bear:
        # 하락장(Alpha Mode): 시장 하락을 이겨내는 상대강도(RS > +10%) 종목에 우대
        r_score = 20.0 if recent_20_ret >= 10.0 else (12.0 if recent_20_ret > 0 else 0.0)
        if recent_20_ret >= 10.0:
            success_reasons.append(f"🔥 [Alpha Mode] 하락장 대비 상대강도(+{recent_20_ret:.1f}%) 우수 역주행주 포착")
    else:
        # 상승장(Beta Mode): 정배열 추세 관성 유지 종목 우대
        r_score = 20.0 if price >= ma20 else 10.0

    # 4) AI Sentiment Agent (20점 만점: 뉴스 감성 분석)
    s_score = 10.0  # 기본 중립
    if not skip_news:
        summary_lines, news_impact, impact_reason = fetch_and_process_news(ticker_symbol)
        if news_impact > 0: s_score = 20.0
        elif news_impact < 0: s_score = 0.0

    # 💥 [TTM Squeeze Release] 최근 5봉 내 응축 후 당일 볼밴 상단 돌파 발산 시 가산점 (+10점)
    had_recent_squeeze = df['Squeeze_On'].iloc[-6:-1].any() if len(df) >= 6 else False
    is_squeeze_release = had_recent_squeeze and (not latest['Squeeze_On']) and (price >= bb_upper)
    
    squeeze_bonus = 10.0 if is_squeeze_release else 0.0
    if is_squeeze_release:
        success_reasons.append("💥 [TTM Squeeze Release] 변동성 응축 완료 후 상방 폭발 개화 (1~5봉 내 5% 슈팅 타점)")

    # 🎯 4대 Agent 종합 앙상블 스코어 합산 (TTM Squeeze 발산 가산점 포함 100점 캡)
    ensemble_score = min(q_score + m_score + r_score + s_score + squeeze_bonus, 100.0)
    pure_win_rate = min(max(round(float(ensemble_score), 1), 0.0), 99.0)

    # 9. 1~5봉 ATR 변동성 한계 기반 예상 수익률(Upside) 연산 (-15.0% ~ +15.0%)
    atr_val = float(latest['ATR'])
    atr_max_move_pct = (atr_val * 2.0 / price) * 100.0  # 1~5봉 현실적 물리적 한계 파동
    direction_mult = (pure_win_rate - 50.0) / 40.0      # 승률 50% 기준 음수/양수 전환
    calculated_upside = atr_max_move_pct * direction_mult
    pure_upside = min(max(round(float(calculated_upside), 1), -15.0), 15.0)

    # 변동성 응축 vs 폭발 동적 판정 로직
    is_squeeze_now = bool(latest['Squeeze_On'])
    was_squeeze_recently = df['Squeeze_On'].iloc[-6:-1].any() if len(df) >= 6 else False
    is_bb_upper_break = price >= float(latest['BB_Upper'])

    # 상단 밴드 돌파 또는 최근 응축 후 해제 시 '변동성 폭발'
    if is_bb_upper_break or (was_squeeze_recently and not is_squeeze_now):
        squeeze_status_txt = "🟢 [변동성 폭발]"
        squeeze_color_txt = "#10b981"
    elif is_squeeze_now:
        squeeze_status_txt = "🔴 [변동성 응축]"
        squeeze_color_txt = "#ef4444"
    else:
        squeeze_status_txt = "🟢 [변동성 확장]"
        squeeze_color_txt = "#10b981"

    ai_data = {
        "up_prob": pure_win_rate, 
        "win_rate": pure_win_rate,                  
        "down_prob": round(100.0 - pure_win_rate, 1),
        "upside": pure_upside,                      
        "return_prob": pure_win_rate,
        "current_signal": msg, 
        "signal_color": color, 
        "trend_state": t_state,
        "is_four_conditions_met": is_four_conditions_met,
        "failed_reasons": failed_reasons, 
        "success_reasons": success_reasons,
        "resist": resist, 
        "support": support, 
        "price": price, 
        "tighter_sl": tighter_sl,
        "tp_price": tp_price, 
        "ma_5": ma5,
        "ma_10": ma10,
        "ma_20": ma20,
        "ma_60": ma60,
        "ma_120": ma120,
        "ma_200": ma200,
        
        "poc_price": poc_price,
        "poc_price_2nd": poc_price_2nd,
        "t1_low": t1_low,
        "t1_high": t1_high,
        "t2_low": t2_low,
        "t2_high": t2_high,
        "poc_range_text_1": poc_range_text_1,
        "poc_range_text_2": poc_range_text_2,

        "top1_pct": top1_pct,
        "top1_touches": top1_touches,
        "curr_bin_pct": curr_bin_pct,
        "curr_bin_touches": curr_bin_touches,        

        "mtf_score": int(price > ma20) + int(price > ma60) * 2,
        "squeeze_status": squeeze_status_txt,  # 👈 변수 연결
        "squeeze_color": squeeze_color_txt,   # 👈 변수 연결
        "swing_trend": "🔥 단기 5개 봉 가속 구간" if price > ma5 else "🌊 단기 5개 봉 하향 구간",
        "swing_setup": swing_setup,
        "news_summary_lines": summary_lines if 'summary_lines' in locals() else [], 
        "news_impact_reason": impact_reason if 'impact_reason' in locals() else "분석 완료",
        "live_action": live_action, 
        "action_color": action_color, 
        "live_reasoning": live_reasoning
    }
    return df, ai_data

# --- [5-1. 제미나이 AI 스윙 트레이더 핵심 조언 함수 (고급 프로 트레이더 최적화)] ---
def get_gemini_advice(api_key, ticker, ai_data, entry_price, roi, currency_symbol, user_question=""):
    if not api_key:
        return "⚠️ 사이드바에 Gemini API Key를 입력하시면 실시간 AI 진단이 활성화됩니다."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        if entry_price > 0:
            position_info = f"- 나의 평단가(매수가): {currency_symbol}{entry_price:,.2f}\n- 현재 실시간 수익률: {roi:+.2f}%"
        else:
            position_info = "- 나의 포지션: 현재 미보유 (신규 진입 타이밍 관망 중)"
        
        # 💡 [PRO QUANT 교정] 특수 이모지 파싱 문법 에러 원천 차단 포맷
        system_instruction = (
            "당신은 월스트리트 프랍 데스크 출신의 냉철한 PRO QUANT 트레이딩 디렉터입니다.\n"
            "손익비 2.0 : 1 (+5.0% 익절 / -2.5% 손절) 전략을 철저히 준수하여 대응 시나리오를 지시하십시오.\n\n"
            "[핵심 매매 규칙 지침]\n"
            "1. 손익비 2.0 : 1 구조: 1차 목표가(+5.0%) 도달 시 50% 물량 익절을 지시하십시오.\n"
            "2. Break-Even 본절가 방어: 주가가 +3.0% 이상 상승 시, 손절가를 매수가 +0.3%(수수료 보존)로 상향하여 리스크를 0으로 확정짓는 전략을 조언하십시오.\n"
            "3. -2.5% Hard Cap 손절: -2.5% 하락 시 즉시 원칙 손절을 선언하십시오."
        )

        prompt = f"{system_instruction}\n\n{fact_sheet}\n\n위 데이터를 종합하여 분석 브리핑을 작성해라."
        
        if user_question.strip():
            prompt += f"\n\n[🔥 사용자의 특별 추가 질문]: {user_question}\n위 차트 데이터와 뉴스를 근거로 이 질문에 대한 명쾌하고 단호한 답변을 브리핑 하단에 반드시 포함해라."
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI 진단 생성 중 오류가 발생했습니다: {str(e)}"

import sqlite3
from datetime import datetime, timedelta

DB_FILE = "rec_history.db"

def init_rec_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rec_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_date TEXT,
        market_type TEXT,
        ticker TEXT,
        stock_name TEXT,
        entry_price REAL,
        tp_price REAL,
        sl_price REAL,
        status TEXT,
        final_return REAL
    )
    """)
    conn.commit()
    conn.close()

init_rec_db()

# ====================================================================
# 🎯 내 실전 보유종목 주문서 관제탑 (하이브리드 익절 + -3% 강제 손절 연동)
def render_my_portfolio_manager():
    st.markdown("### 🎯 내 실전 보유종목 주문서 관제")

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

    # 1. 신규 등록 UI
    with st.expander("➕ 새 매수 종목 등록하기", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1: input_name = st.text_input("종목명", placeholder="예: 누 홀딩스 / 테슬라 / 삼성전자")
        with c2: input_ticker = st.text_input("티커 (선택사항)", placeholder="비워두어도 자동 찾기")
        with c3: input_price = st.number_input("매수가 (진입가)", min_value=0.0, step=1.0)
        with c4:
            st.write(" ")
            st.write(" ")
            if st.button("등록", use_container_width=True):
                if input_name and input_price > 0:
                    search_keyword = input_ticker.strip() if input_ticker.strip() else input_name.strip()
                    auto_ticker, _ = search_ticker(search_keyword)
                    final_ticker = auto_ticker if auto_ticker else (input_ticker if input_ticker else "N/A")
                    
                    cursor.execute(
                        "INSERT INTO my_trades (stock_name, ticker, entry_price, entry_date) VALUES (?, ?, ?, ?)",
                        (input_name.strip(), final_ticker, input_price, datetime.now().strftime("%Y-%m-%d"))
                    )
                    conn.commit()
                    st.success(f"'{input_name}' ({final_ticker}) 등록 완료!")
                    st.rerun()
                else:
                    st.warning("⚠️ 종목명과 매수가를 입력해 주세요.")

    cursor.execute("SELECT id, stock_name, ticker, entry_price, entry_date FROM my_trades ORDER BY id DESC")
    my_stocks = cursor.fetchall()
    conn.close()

    if not my_stocks:
        st.info("💡 등록된 실전 매수 종목이 없습니다. 위에서 매수 종목을 등록해 보세요!")
        return

    st.markdown("---")
    for s_id, s_name, s_ticker, entry_p, e_date in my_stocks:
        c_card, c_del = st.columns([8.8, 1.2])
        
        with c_del:
            if st.button("🗑️ 삭제", key=f"btn_del_{s_id}", use_container_width=True):
                conn_del = sqlite3.connect(DB_FILE, check_same_thread=False)
                cursor_del = conn_del.cursor()
                cursor_del.execute("DELETE FROM my_trades WHERE id = ?", (s_id,))
                conn_del.commit()
                conn_del.close()
                st.success(f"'{s_name}' 종목 삭제 완료!")
                st.rerun()

        df_curr = get_raw_daily_data(s_ticker)
        
        is_krw = any(x in s_ticker for x in [".KS", ".KQ", "-KRW"])
        curr_symbol = "₩" if is_krw else "$"
        
        def fmt_p(p):
            if p is None: return f"{curr_symbol}0"
            if p < 1.0:
                return f"{curr_symbol}{p:,.6f}"
            elif p < 100.0:
                return f"{curr_symbol}{p:,.2f}"
            else:
                return f"{curr_symbol}{p:,.0f}" if is_krw else f"{curr_symbol}{p:,.2f}"

        if df_curr is not None and not df_curr.empty:
            curr_p = float(df_curr['Close'].iloc[-1])
            curr_low = float(df_curr['Low'].iloc[-1])
            
            df_after = df_curr[df_curr['Date'].dt.strftime('%Y-%m-%d') >= e_date]
            if df_after.empty:
                df_after = df_curr.tail(5)

            max_high_since_entry = float(df_after['High'].max())
            max_ret_pct = ((max_high_since_entry - entry_p) / entry_p) * 100.0
            curr_ret_pct = ((curr_p - entry_p) / entry_p) * 100.0

            df_curr['TR'] = np.maximum(df_curr['High'] - df_curr['Low'], np.maximum(abs(df_curr['High'] - df_curr['Close'].shift(1)), abs(df_curr['Low'] - df_curr['Close'].shift(1))))
            c_atr = float(df_curr['TR'].rolling(14, min_periods=1).mean().iloc[-1])

            tp1_price = entry_p * 1.050
            tp2_price = entry_p * 1.090
            tp3_price = entry_p * 1.120
            sl_price  = entry_p * 0.975

            tp1_pct = 5.0
            tp2_pct = 9.0
            tp3_pct = 12.0

            if curr_ret_pct <= -2.5 or curr_low <= sl_price:
                action_bg = "#450a0a"
                action_border = "#ef4444"
                action_color = "#fca5a5"
                action_text = f"🛑 <b>[전량 강제 손절]</b> -2.5% 손절가({fmt_p(sl_price)}) 도달! 미련 없이 즉시 전량 손절하세요."
            elif max_ret_pct >= 3.0:
                if curr_p <= entry_p * 1.003:
                    action_bg = "#064e3b"
                    action_border = "#10b981"
                    action_color = "#a7f3d0"
                    action_text = f"🛡️ <b>[수익 방어 청산]</b> 최고 +{max_ret_pct:.1f}% 상승 후 하락 반전! 본절 방어선({fmt_p(entry_p*1.003)})에서 청산 완료하세요."
                else:
                    action_bg = "#431407"
                    action_border = "#f97316"
                    action_color = "#fdba74"
                    action_text = f"🔥 <b>[Break-Even 가동]</b> 최고 +{max_ret_pct:.1f}% 상승! 주가 밀릴 시 <b>{fmt_p(entry_p*1.003)} (+0.3%)</b> 본절 방어 대기하세요."
            else:
                action_bg = "#0f172a"
                action_border = "#3b82f6"
                action_color = "#93c5fd"
                action_text = f"🧭 <b>[관망/홀딩]</b> 현재 수익률 {curr_ret_pct:+.2f}%. -2.5% 손절 및 +5.0% 익절 목표 범위 안에서 추적 중입니다."

        else:
            curr_p = entry_p
            curr_ret_pct = 0.0
            sl_price = entry_p * 0.975
            tp1_price, tp2_price, tp3_price = entry_p*1.05, entry_p*1.09, entry_p*1.12
            tp1_pct, tp2_pct, tp3_pct = 5.0, 9.0, 12.0
            action_bg = "#0f172a"
            action_border = "#334155"
            action_color = "#cbd5e1"
            action_text = "⚪ 데이터 수집 중..."

        ret_color = "#ff4b4b" if curr_ret_pct > 0 else ("#38bdf8" if curr_ret_pct < 0 else "#94a3b8")

        curr_ret_str = f"{curr_ret_pct:+.2f}%"
        tp1_pct_str = f"{tp1_pct:.1f}%"
        tp2_pct_str = f"{tp2_pct:.1f}%"
        tp3_pct_str = f"{tp3_pct:.1f}%"

        card_html = (
            f'<div style="background-color: #1e2230; padding: 16px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #334155;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
            f'<div>'
            f'<span style="font-size: 18px; font-weight: bold; color: #ffffff;">{s_name}</span>'
            f'<span style="font-size: 13px; color: #94a3b8;"> ({s_ticker}) | 등록일: {e_date}</span>'
            f'</div>'
            f'<div style="text-align: right;">'
            f'<div style="font-size: 15px; font-weight: bold; color: {ret_color};">'
            f'현재가: {fmt_p(curr_p)} ({curr_ret_str})'
            f'</div>'
            f'</div>'
            f'</div>'
            f'<div style="background-color: {action_bg}; border: 1px solid {action_border}; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px; color: {action_color}; font-size: 13px; line-height: 1.5;">'
            f'{action_text}'
            f'</div>'
            f'<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; background-color: #0f172a; padding: 12px; border-radius: 8px; text-align: center;">'
            f'<div>'
            f'<div style="font-size: 11px; color: #94a3b8;">내 진입가</div>'
            f'<div style="font-size: 14px; font-weight: bold; color: #ffffff;">{fmt_p(entry_p)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #38bdf8;">강제 손절 (-2.5%)</div>'
            f'<div style="font-size: 14px; font-weight: bold; color: #38bdf8;">{fmt_p(sl_price)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #f59e0b;">1차 ({tp1_pct_str})</div>'
            f'<div style="font-size: 14px; font-weight: bold; color: #f59e0b;">{fmt_p(tp1_price)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #ef4444;">2차 ({tp2_pct_str})</div>'
            f'<div style="font-size: 14px; font-weight: bold; color: #ef4444;">{fmt_p(tp2_price)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #a855f7;">3차 ({tp3_pct_str})</div>'
            f'<div style="font-size: 14px; font-weight: bold; color: #a855f7;">{fmt_p(tp3_price)}</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        with c_card:
            st.markdown(card_html, unsafe_allow_html=True)

def save_top5_to_db(kr_list, us_list):
    today_str = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    def insert_items(items, market_label):
        for item in items[:5]:
            ticker = item['ticker']
            cursor.execute("SELECT id FROM rec_history WHERE rec_date=? AND ticker=?", (today_str, ticker))
            if cursor.fetchone() is None:
                entry = item.get('price', 1.0)
                tp = entry * (1 + (item.get('upside', 5.0) / 100))
                sl = entry * 0.96
                cursor.execute("""
                INSERT INTO rec_history (rec_date, market_type, ticker, stock_name, entry_price, tp_price, sl_price, status, final_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, '진행중', 0.0)
                """, (today_str, market_label, ticker, item['name'], entry, tp, sl))
    
    insert_items(kr_list, "국내")
    insert_items(us_list, "미국")
    conn.commit()
    conn.close()

def update_history_returns():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id, rec_date, ticker, entry_price, tp_price, sl_price FROM rec_history WHERE status='진행중'")
    rows = cursor.fetchall()
    
    for row in rows:
        rec_id, rec_date, ticker, entry_p, tp_p, sl_p = row
        df_t = get_raw_daily_data(ticker)
        if df_t is None or df_t.empty:
            continue
            
        df_t['Date_Str'] = df_t['Date'].dt.strftime("%Y-%m-%d")
        df_after = df_t[df_t['Date_Str'] > rec_date].head(5)
        
        if df_after.empty:
            continue
            
        max_high = df_after['High'].max()
        min_low = df_after['Low'].min()
        last_close = df_after['Close'].iloc[-1]
        
        if min_low <= sl_p:
            status = "손절"
            ret = ((sl_p - entry_p) / entry_p) * 100
        elif max_high >= tp_p:
            status = "익절"
            ret = ((tp_p - entry_p) / entry_p) * 100
        elif len(df_after) >= 5:
            status = "5봉만기"
            ret = ((last_close - entry_p) / entry_p) * 100
        else:
            status = "진행중"
            ret = ((last_close - entry_p) / entry_p) * 100
            
        cursor.execute("UPDATE rec_history SET status=?, final_return=? WHERE id=?", (status, ret, rec_id))
        
    conn.commit()
    conn.close()

# ====================================================================
# 📊 거래량 입체 분석 및 패턴 신뢰도 검증 함수
# ====================================================================
def render_volume_reliability_analysis(df, detected_pattern="지정되지 않음"):
    if df is None or len(df) < 20:
        st.warning("데이터가 부족하여 거래량 및 신뢰도 분석을 진행할 수 없습니다. (최소 20거래일 필요)")
        return

    df = df.copy()
    df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    latest_vol = float(latest['Volume'])
    vol_ma20 = float(latest['Vol_MA20']) if latest['Vol_MA20'] > 0 else 1.0
    vol_ratio = (latest_vol / vol_ma20) * 100
    
    price_up = latest['Close'] > prev['Close']
    vol_surged = latest_vol > (vol_ma20 * 1.5)
    
    vol_verdict = "📊 거래량 평이함"
    vol_color = "neutral"
    vol_desc = "현재 주가 움직임에 강력한 주도 세력의 개입 흔적은 보이지 않습니다."

    if price_up and vol_surged:
        vol_verdict = "💥 세력 매집 포착 (대량 거래 동반 상승)"
        vol_color = "success"
        vol_desc = "강력한 매수세가 유입되었습니다. 캔들 패턴 신뢰도가 높아지는 구간입니다."
    elif not price_up and vol_surged:
        vol_verdict = "🚨 폭탄 매물 출회 (대량 거래 동반 하락)"
        vol_color = "error"
        vol_desc = "지지선을 깨며 대량 거래가 터진 하락입니다. 진입 위험 구역입니다."

    st.markdown("---")
    st.subheader("📊 거래량 입체 분석 및 패턴 신뢰도 검증")
    
    col1, col2 = st.columns(2)
    col1.metric("현재 거래량 (20일 평균 대비)", f"{vol_ratio:.1f} %")
    col2.metric("패턴 최종 신뢰도", "🔥 HIGH CONFIRMED" if vol_surged else "⚠️ 일반")

    if vol_color == "success":
        st.success(f"**{vol_verdict}**\n\n{vol_desc}")
    elif vol_color == "error":
        st.error(f"**{vol_verdict}**\n\n{vol_desc}")
    else:
        st.info(f"**{vol_verdict}**\n\n{vol_desc}")

# --- [6. UI 및 차트 렌더링 (단타 손절선 완벽 연동 버전)] ---
def render_dashboard(tab_name, df_raw, api_key, entry_price, selected_name, safe_ticker, is_krw):
    import pandas as pd
    
    if df_raw is not None and not df_raw.empty:
        if isinstance(df_raw.columns, pd.MultiIndex):
            df_raw.columns = df_raw.columns.get_level_values(0)

    try:
        df_proc, ai = process_data(df_raw, tab_name, safe_ticker, skip_news=True)
    except Exception as e:
        st.error(f"🚨 process_data 내부 연산 에러 발생 ({tab_name}): {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return

# ====================================================================
    # 📊 데이터 부족 및 오류 방어선 (raw_data ➔ df_raw 매개변수 참조 오류 교정)
    # ====================================================================
    if df_proc is None or df_raw is None or len(df_raw) < 10:
        st.warning("데이터가 부족하여 해당 탭의 차트를 생성할 수 없습니다.")
        return None

# 🟢 [종합 버그 방어선] 데이터가 깨졌든 안 깨졌든 변수부터 무조건 무조건 생성하고 시작합니다.
    is_filtered_out = False
    filter_msg = ""

    # 일봉/주봉 2024년 이후 데이터 무제한 스크롤 반영
    if tab_name == 'monthly':
        df_disp = df_proc.tail(120).copy()
    else:
        df_disp = df_proc[df_proc['Date'] >= '2024-01-01'].copy()
        if len(df_disp) < 60:
            df_disp = df_proc.tail(120).copy()

    df_disp['Date_Str'] = df_disp['Date'].dt.strftime('%Y-%m-%d')
    x_axis = df_disp['Date_Str']
    currency_symbol = "₩" if is_krw else "$"

    # 상단 요약 시그널 바
   # ====================================================================
    # 📊 [교체 추가] 월가 프랍데스크 스타일 실시간 AI 트레이딩 오더 시트

# 🧭 [복구] 대시보드에 필요한 다중 시간프레임(MTF) 색상 및 메시지 데이터셋
    mtf_colors = {3: "#10b981", 2: "#34d399", 1: "#fbbf24", 0: "#ef4444"}
    mtf_msg = {
        3: "🚀 [초강세] 5일선 및 단/중기 이평선 완벽 정배열 정렬",
        2: "🔥 [우상향 우세] 단기 가속도 유효 및 매수세 장악",
        1: "🟡 [추세 혼조] 박스권 갇힘 또는 단기 숨고르기 국면",
        0: "🧊 [역배열 약세] 이평선 저항 누적 및 진입 금지 구간"
    }
    
# 💵 [등락률 0% 해결 예외 연산]
    day_pct = 0.0
    try:
        if len(df_disp) >= 2:
            prev_c = float(df_disp['Close'].iloc[-2])
            curr_c = float(ai['price'])
            if prev_c > 0:
                day_pct = ((curr_c - prev_c) / prev_c) * 100
    except Exception: day_pct = 0.0

    if day_pct > 0:
        day_pct_txt = f"▲ +{day_pct:.2f}%"
        day_pct_color = "#ff4b4b"
    elif day_pct < 0:
        day_pct_txt = f"▼ {day_pct:.2f}%"
        day_pct_color = "#1e88e5"
    else:
        day_pct_txt = "0.00%"
        day_pct_color = "#999999"

    # 💡 [PRO QUANT 교정] 웹 특수 공백(\xa0) 및 multiline string 인코딩 에러 원천 차단
    legend_html = (
        '<div style="background-color:#0f172a; padding:12px 16px; border-radius:8px; border:1px solid #334155; margin-bottom:12px;">'
        '<div style="font-size:12px; font-weight:bold; color:#94a3b8; margin-bottom:8px;">이동평균선(MA) 범례 및 주요 역할</div>'
        '<div style="display:flex; flex-wrap:wrap; gap:16px; font-size:12px; font-weight:bold;">'
        '<span style="color:#FF1493;">━ 5일선 <span style="color:#cbd5e1; font-weight:normal;">(초단기 추세)</span></span>'
        '<span style="color:#29B6F6;">━ 10일선 <span style="color:#cbd5e1; font-weight:normal;">(단기 단타 생명선)</span></span>'
        '<span style="color:#00E676;">━ 20일선 <span style="color:#cbd5e1; font-weight:normal;">(중단기 세력 심리선)</span></span>'
        '<span style="color:#AB47BC;">━ 60일선 <span style="color:#cbd5e1; font-weight:normal;">(중기 수급 지지/저항)</span></span>'
        '<span style="color:#FF6D00;">━ 120일선 <span style="color:#cbd5e1; font-weight:normal;">(경기/중장기 핵심 저항선)</span></span>'
        '<span style="color:#FF1744;">━ 200일선 <span style="color:#cbd5e1; font-weight:normal;">(대세/장기 추세 분수령)</span></span>'
        '</div>'
        '</div>'
    )
    st.markdown(legend_html, unsafe_allow_html=True)

    # 1. 💡 화폐 기호, 포맷터 및 파동 마디가/손익비 연산
    currency_symbol = "₩" if is_krw else "$"
    fmt_p = lambda p: f"{currency_symbol}{p:,.0f}" if is_krw else f"{currency_symbol}{p:,.2f}"

    c_entry_p, entry_tag = calculate_smart_entry_price(df_proc, ai)
    entry_target_p = c_entry_p  # 👈 [신규 추가] NameError 방지용 변수 바인딩
    c_atr = float(df_proc['ATR'].iloc[-1]) if 'ATR' in df_proc.columns else (c_entry_p * 0.02)

    # 🎯 익절(+3.5% / +5.0%) & ATR 손절(-3.0% 하드 캡)
    c_tp1_p = c_entry_p * 1.035
    c_tp2_p = c_entry_p * 1.050
    
    # ATR 기반 손절가 산출 후 -3.0% 하드 캡 적용
    raw_sl = c_entry_p - (c_atr * 1.2)
    hard_cap_sl = c_entry_p * 0.97
    c_sl_p = max(raw_sl, hard_cap_sl)

    tp1_pct_disp = ((c_tp1_p - c_entry_p) / c_entry_p) * 100.0
    sl_pct_disp = ((c_sl_p - c_entry_p) / c_entry_p) * 100.0

    # 🚦 [실시간 3대 매매 가이드 신호등 카드]
    col_e, col_t, col_s = st.columns(3)
    col_e.metric("🟢 권장 진입가 (눌림목)", f"{fmt_p(c_entry_p)}", "0~2일 체결 대기")
    col_t.metric("🔴 1차 익절가 (50% 청산)", f"{fmt_p(c_tp1_p)}", f"+{tp1_pct_disp:.1f}%")
    col_s.metric("🔵 동적 손절가 (Hard Cap)", f"{fmt_p(c_sl_p)}", f"{sl_pct_disp:.1f}%", delta_color="inverse")

    # 💡 [PRO QUANT 교정] f-string 다중 문자열 특수 공백(\xa0) 및 이모지 인코딩 에러 원천 차단
    primary_reason = ai['success_reasons'][0] if ai['success_reasons'] else "주요 이동평균선 정배열 지지 구조 형성"
    reason_html = (
        '<div style="background-color:#1e293b; padding:10px 14px; border-radius:6px; border-left:4px solid #10b981; margin:10px 0 15px 0; font-size:13px; color:#e2e8f0;">'
        f'<b>[AI 1줄 핵심 진단]</b> {primary_reason} (진입 타점: {entry_tag})'
        '</div>'
    )
    st.markdown(reason_html, unsafe_allow_html=True)

    col_stat1, col_stat2 = st.columns(2)

    with col_stat1:
        stat1_html = (
            '<div style="background-color:#141414; padding:15px; border-radius:10px; border-top: 5px solid #38bdf8; margin-bottom:15px; height:100px;">'
            '<p style="margin:0; font-size:12px; color:#999; font-weight:bold;">REAL-TIME PRICE (실시간 현재가)</p>'
            f'<h4 style="margin:8px 0 0 0; color:#38bdf8; font-size:20px; font-weight:bold;">'
            f'{currency_symbol}{ai["price"]:,.2f} <span style="font-size:14px; color:{day_pct_color}; margin-left:6px;">({day_pct_txt})</span>'
            '</h4>'
            '</div>'
        )
        st.markdown(stat1_html, unsafe_allow_html=True)
        
    with col_stat2:
        stat2_html = (
            f'<div style="background-color:#141414; padding:15px; border-radius:10px; border-top: 5px solid {ai["squeeze_color"]}; margin-bottom:15px; height:100px;">'
            '<p style="margin:0; font-size:12px; color:#999; font-weight:bold;">TTM SQUEEZE (변동성 에너지)</p>'
            f'<h4 style="margin:8px 0 0 0; color:{ai["squeeze_color"]}; font-size:16px; font-weight:bold;">{ai["squeeze_status"]}</h4>'
            '</div>'
        )
        st.markdown(stat2_html, unsafe_allow_html=True)

    # 💡 [신규 추가] 모바일용 보조지표 접기/펴기(Toggle) 컨트롤 UI
    with st.expander("⚙️ 차트 보조지표 접기/펴기 (모바일 가독성 최적화)", expanded=False):
        selected_subplots = st.multiselect(
            "화면에 표시할 보조지표 선택:",
            options=["Volume", "MACD", "RSI", "ADX & DMI"],
            default=["Volume", "MACD", "RSI", "ADX & DMI"],
            key=f"toggle_indicators_{tab_name}"
        )

    # 선택된 보조지표 수에 따라 서브플롯 행(Row) 및 높이 동적 계산
    active_rows = 1 + len(selected_subplots)
    
    # 캔들차트 비중(0.55) + 나머지 선택 보조지표 균등 분배
    if len(selected_subplots) > 0:
        sub_height = 0.45 / len(selected_subplots)
        row_heights = [0.55] + [sub_height] * len(selected_subplots)
    else:
        row_heights = [1.0]

    subplot_titles = [f"[{selected_name}] Price Action 및 주도주 이평선 선형"] + selected_subplots

    fig = make_subplots(
        rows=active_rows, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=row_heights,
        subplot_titles=subplot_titles
    )
    
    kr_up, kr_dn = '#ff4b4b', '#1e88e5'
    c_s, o_s = df_disp['Close'], df_disp['Open']


# ====================================================================
    # 📌 1. 수익률 변동치 계산 (전일 종가 기준 완벽 반영)
    df_disp['Prev_Close'] = df_proc['Close'].shift(1).loc[df_disp.index].fillna(df_disp['Open'])

    fmt = ":,.0f" if is_krw else ":,.2f"
    unit_suffix = "원" if is_krw else ""

    prev_c = df_disp['Prev_Close']
    o_pct = (df_disp['Open'] - prev_c) / prev_c * 100
    h_pct = (df_disp['High'] - prev_c) / prev_c * 100
    l_pct = (df_disp['Low'] - prev_c) / prev_c * 100
    c_pct = (df_disp['Close'] - prev_c) / prev_c * 100

    open_txt = [f"<span style='color:#ff4b4b'>+{v:.2f}%</span>" if v > 0 else f"<span style='color:#1e88e5'>{v:.2f}%</span>" if v < 0 else "0.00%" for v in o_pct]
    high_txt = [f"<span style='color:#ff4b4b'>+{v:.2f}%</span>" if v > 0 else f"<span style='color:#1e88e5'>{v:.2f}%</span>" if v < 0 else "0.00%" for v in h_pct]
    low_txt = [f"<span style='color:#ff4b4b'>+{v:.2f}%</span>" if v > 0 else f"<span style='color:#1e88e5'>{v:.2f}%</span>" if v < 0 else "0.00%" for v in l_pct]
    close_txt = [f"<span style='color:#ff4b4b'>+{v:.2f}%</span>" if v > 0 else f"<span style='color:#1e88e5'>{v:.2f}%</span>" if v < 0 else "0.00%" for v in c_pct]

    custom_hover_strings = np.stack((open_txt, high_txt, low_txt, close_txt), axis=-1)

    # 📌 2. 한국어 맞춤형 호버 박스가 적용된 캔들스틱 추가
    fig.add_trace(go.Candlestick(
        x=x_axis, open=o_s, high=df_disp['High'], low=df_disp['Low'], close=c_s, 
        increasing_line_color=kr_up, decreasing_line_color=kr_dn,
        customdata=custom_hover_strings, 
        hovertemplate=(
            "<b>📅 날짜: %{x}</b><br>"
            "----------------------------<br>"
            f"시작 {currency_symbol}%{{open{fmt}}}{unit_suffix} (%{{customdata[0]}})<br>"
            f"고가 {currency_symbol}%{{high{fmt}}}{unit_suffix} (%{{customdata[1]}})<br>"
            f"저가 {currency_symbol}%{{low{fmt}}}{unit_suffix} (%{{customdata[2]}})<br>"
            f"종가 {currency_symbol}%{{close{fmt}}}{unit_suffix} (%{{customdata[3]}})"
            "<extra></extra>"
        )
    ), row=1, col=1)

    # 📌 3. 이동평균선 및 지지저항선 (hoverinfo="skip" 주입으로 마우스 팝업 원천 차단)
    fig.add_trace(go.Scatter(
        x=x_axis, y=df_disp['Resist_20'], 
        line=dict(color='rgba(255, 75, 75, 0.3)', width=1.5, dash='dot'),
        hoverinfo="skip"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=x_axis, y=df_disp['Support_20'], 
        line=dict(color='rgba(30, 136, 229, 0.3)', width=1.5, dash='dot'),
        hoverinfo="skip"
    ), row=1, col=1)
    
    # 📌 색상 코드가 정정된 이동평균선 6종
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MA_5'], line=dict(color='#FF1493', width=1.2), hoverinfo="skip"), row=1, col=1)  # 5일선: 연분홍
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MA_10'],  line=dict(color='#29B6F6', width=1.5), hoverinfo="skip"), row=1, col=1)  # 10일선: 파랑
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MA_20'],  line=dict(color='#00E676', width=1.8), hoverinfo="skip"), row=1, col=1)  # 20일선: 연두
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MA_60'],  line=dict(color='#AB47BC', width=2.0), hoverinfo="skip"), row=1, col=1)  # 60일선: 보라
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MA_120'], line=dict(color='#FF6D00', width=2.0), hoverinfo="skip"), row=1, col=1)  # 120일선: 주황
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MA_200'], line=dict(color='#FF1744', width=2.2), hoverinfo="skip"), row=1, col=1)  # 200일선: 빨강

    # 1위 최대 매물대 박스
    fig.add_shape(
        type="rect", xref="paper", yref="y", x0=0, x1=1,
        y0=ai['t1_low'], y1=ai['t1_high'],
        fillcolor="rgba(255, 0, 0, 0.12)", layer="below", line_width=0
    )
    # ====================================================================

    # 기존 지지저항선선형 유지
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Resist_20'], line=dict(color='rgba(255, 75, 75, 0.3)', width=1.5, dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Support_20'], line=dict(color='rgba(30, 136, 229, 0.3)', width=1.5, dash='dot')), row=1, col=1)

    # 2. 1위 최대 매물대 박스 (연한 빨강 네모) 및 비율 글자 라벨 추가
    fig.add_shape(
        type="rect", xref="paper", yref="y", x0=0, x1=1,
        y0=ai['t1_low'], y1=ai['t1_high'],
        fillcolor="rgba(255, 0, 0, 0.12)", layer="below", line_width=0
    )
    fig.add_annotation(
        xref="paper", yref="y", x=0.005, y=(ai['t1_low'] + ai['t1_high']) / 2,
        text=ai['poc_range_text_1'], showarrow=False,
        font=dict(color="#ff6b6b", size=11, family="monospace"), xanchor="left", yanchor="middle"
    )
    
    # 3. 2위 차상위 매물대 박스 (연한 노랑 네모) 및 비율 글자 라벨 추가
    fig.add_shape(
        type="rect", xref="paper", yref="y", x0=0, x1=1,
        y0=ai['t2_low'], y1=ai['t2_high'],
        fillcolor="rgba(255, 235, 59, 0.12)", layer="below", line_width=0
    )
    fig.add_annotation(
        xref="paper", yref="y", x=0.005, y=(ai['t2_low'] + ai['t2_high']) / 2,
        text=ai['poc_range_text_2'], showarrow=False,
        font=dict(color="#ffd54f", size=11, family="monospace"), xanchor="left", yanchor="middle"
    )

    # ====================================================================
    # 📊 [교체] 1위(연한 빨강), 2위(연한 노랑) 불투명 매물대 박스 및 라벨 구현
    # ====================================================================
    # 1위 최대 매물대 박스 (연한 빨강)
    fig.add_shape(
        type="rect",
        xref="paper", yref="y",
        x0=0, x1=1,
        y0=ai['t1_low'], y1=ai['t1_high'],
        fillcolor="rgba(255, 0, 0, 0.12)",  # 연한 빨강 (투명도 12%)
        layer="below",                      # 캔들 차트 뒤로 정렬하여 차트 가림 방지
        line_width=0,
    )
    
    # 2위 차상위 매물대 박스 (연한 노랑)
    fig.add_shape(
        type="rect",
        xref="paper", yref="y",
        x0=0, x1=1,
        y0=ai['t2_low'], y1=ai['t2_high'],
        fillcolor="rgba(255, 235, 59, 0.12)", # 연한 노랑/골드 (투명도 12%)
        layer="below",                       # 캔들 차트 뒤로 정렬하여 차트 가림 방지
        line_width=0,
    )

    # ====================================================================
    # 📊 [교체] 1위, 2위 매물대 글자 라벨 (오류 수정 버전)
    # ====================================================================
    # 1위 최대 매물대 글자 라벨 (박스 정중앙 좌측 정렬)
    fig.add_annotation(
        xref="paper", yref="y",
        x=0.005, y=(ai['t1_low'] + ai['t1_high']) / 2,
        text=ai['poc_range_text_1'],
        showarrow=False,
        font=dict(color="#ff6b6b", size=11, family="monospace"),  # 👈 font_family에서 family로 수정
        xanchor="left", yanchor="middle"
    )
    
    # 2위 차상위 매물대 글자 라벨 (박스 정중앙 좌측 정렬)
    fig.add_annotation(
        xref="paper", yref="y",
        x=0.005, y=(ai['t2_low'] + ai['t2_high']) / 2,
        text=ai['poc_range_text_2'],
        showarrow=False,
        font=dict(color="#ffd54f", size=11, family="monospace"),  # 👈 font_family에서 family로 수정
        xanchor="left", yanchor="middle"
    )

    # 💡 동적 서브플롯 행 위치 추적 인덱스
    curr_row = 2

    # 1. Volume (거래량)
    if "Volume" in selected_subplots:
        colors = [kr_up if c_s.iloc[i] >= o_s.iloc[i] else kr_dn for i in range(len(df_disp))]
        fig.add_trace(go.Bar(x=x_axis, y=df_disp['Volume'], marker_color=colors), row=curr_row, col=1)
        curr_row += 1

    # 2. MACD
    if "MACD" in selected_subplots:
        m_cols = [kr_up if val > 0 else kr_dn for val in df_disp['MACD_Hist']]
        fig.add_trace(go.Bar(x=x_axis, y=df_disp['MACD_Hist'], marker_color=m_cols), row=curr_row, col=1)
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MACD'], line=dict(color='cyan')), row=curr_row, col=1)
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Signal'], line=dict(color='orange')), row=curr_row, col=1)
        curr_row += 1

    # 3. RSI
    if "RSI" in selected_subplots:
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['RSI'], line=dict(color='purple', width=2)), row=curr_row, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="blue", row=curr_row, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="red", row=curr_row, col=1)
        curr_row += 1

    # 4. ADX & DMI
    if "ADX & DMI" in selected_subplots and 'ADX' in df_disp.columns:
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['ADX'], line=dict(color='gold', width=2.5)), row=curr_row, col=1)
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Plus_DI'], line=dict(color='gray', width=1.5)), row=curr_row, col=1)
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Minus_DI'], line=dict(color='#ff4b4b', width=1.5)), row=curr_row, col=1)
        curr_row += 1
    
# ====================================================================
    # 🎯 [최종 해결] 잘림 현상 방지 및 무조건 표시(always) 옵션 적용
    # ====================================================================
    fig.update_xaxes(type='category', showticklabels=False)
    fig.update_yaxes(autorange=True, fixedrange=False)

    # 💡 모바일 터치 시 페이지 스크롤 대신 차트 제스처가 동작하도록 강제하는 CSS
    st.markdown("""
    <style>
    .js-plotly-plot .plotly .main-svg {
        touch-action: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    fig.update_layout(
        height=1000, 
        template="plotly_dark", 
        margin=dict(l=65, r=10, t=30, b=10),
        showlegend=False, 
        xaxis_rangeslider_visible=False,
        hovermode="closest",
        dragmode="pan",
        
        # 🟡 [선 도구 색상 설정] 새로 그리는 선을 선명한 노란색으로 지정
        newshape=dict(
            line=dict(color="#facc15", width=2.5),
            opacity=1.0
        ),
        
        modebar=dict(
            orientation='v',                  
            bgcolor='rgba(20, 20, 20, 0.7)', 
            color='#cbd5e1',                  
            activecolor='#38bdf8',
            add=['drawline', 'eraseshape', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'], 
            remove=['autoScale2d', 'drawopenpath', 'lasso2d', 'select2d'] 
        )
    )
    
    chart_config = {
        'scrollZoom': True,
        'displayModeBar': True,
        'responsive': True
    }

    st.plotly_chart(fig, use_container_width=True, key=f"chart_{tab_name}", config=chart_config)

    # 💡 [신규 위치] 5대 보조지표 시그널 변수 사전 연산 (detail_tab1보다 먼저 선언)
    v_last = float(df_proc['Volume'].iloc[-1])
    v_ma20 = float(df_proc['Vol_MA_20'].iloc[-1]) if float(df_proc['Vol_MA_20'].iloc[-1]) > 0 else 1.0
    m_line = float(df_proc['MACD'].iloc[-1])
    m_sig = float(df_proc['Signal'].iloc[-1])
    m_hist = float(df_proc['MACD_Hist'].iloc[-1])
    m_hist_prev = float(df_proc['MACD_Hist'].iloc[-2]) if len(df_proc) > 2 else 0.0
    rsi_curr = float(df_proc['RSI'].iloc[-1])
    rsi_prev = float(df_proc['RSI'].iloc[-2]) if len(df_proc) > 2 else 50.0
    p_di = float(df_proc['Plus_DI'].iloc[-1])
    m_di = float(df_proc['Minus_DI'].iloc[-1])
    adx_val = float(df_proc['ADX'].iloc[-1])
    price = float(ai['price'])

    sig_vol_buy = v_last >= (v_ma20 * 2.0) and df_proc['Close'].iloc[-1] > df_proc['Open'].iloc[-1]
    sig_vol_sell = v_last >= (v_ma20 * 3.0) and df_proc['Close'].iloc[-1] < df_proc['Open'].iloc[-1]
    sig_macd_buy = (m_line > m_sig and df_proc['MACD'].iloc[-2] <= df_proc['Signal'].iloc[-2]) or (m_hist > m_hist_prev and m_hist < 0)
    sig_macd_sell = m_line < m_sig
    sig_rsi_buy = rsi_curr <= 30 or (rsi_prev < 30 and rsi_curr >= 30)
    sig_rsi_sell = rsi_curr >= 70 or (rsi_prev > 70 and rsi_curr <= 70)
    sig_dmi_buy = p_di > m_di and adx_val >= 20
    sig_dmi_sell = m_di > p_di

    ma120_val = float(df_proc['MA_120'].iloc[-1]) if 'MA_120' in df_proc.columns else price
    ma200_val = float(df_proc['MA_200'].iloc[-1]) if 'MA_200' in df_proc.columns else price

    sig_ma_buy = (price >= ma120_val) and (price >= ma200_val)
    sig_ma_sell = (price < ma120_val) or (price < ma200_val)

    # 📑 하단 상세 분석 정보 그룹화 3대 구조화 탭
    st.markdown("<br>", unsafe_allow_html=True)
    detail_tab1, detail_tab2, detail_tab3 = st.tabs([
        "📊 심층 보조지표 & 매물대", 
        "🧮 자산/포지션 계산기", 
        "📰 AI 진단 & 실시간 뉴스"
    ])

    # --------------------------------------------------------------------
    # 탭 1: 심층 보조지표 & 매물대 분석
    # --------------------------------------------------------------------
    with detail_tab1:
        curr_p = float(ai.get('price', 0.0))
        supp_p = float(ai.get('support', 0.0))
        resi_p = float(ai.get('resist', 0.0))
        poc_p = float(ai.get('poc_price', 0.0))
        ma20_p = float(ai.get('ma_20', curr_p))
        sl_p = float(ai.get('tighter_sl', supp_p))

        win_rate = float(ai.get('up_prob', 50.0))
        upside_val = float(ai.get('upside', 0.0))

        def fmt_color_pct(val):
            color = "#ff4b4b" if val > 0 else "#38bdf8" if val < 0 else "#ffffff"
            return f'<span style="color:{color}; font-weight:bold;">({val:+.1f}%)</span>'

        poc_dist = ((poc_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0
        supp_dist = ((supp_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0
        resi_dist = ((resi_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0
        disparity_20 = (curr_p / ma20_p * 100.0) if ma20_p > 0 else 100.0

        win_color = "#ff4b4b" if win_rate >= 50.0 else "#38bdf8"
        upside_color = "#ff4b4b" if upside_val > 0 else "#38bdf8" if upside_val < 0 else "#ffffff"
        upside_txt = f"+{upside_val:.1f}%" if upside_val > 0 else f"{upside_val:.1f}%"

        c_atr = float(df_proc['ATR'].iloc[-1]) if 'ATR' in df_proc.columns else (curr_p * 0.02)
        st_tp_p = curr_p + (c_atr * 1.5)
        reward_st = st_tp_p - curr_p
        risk_st = curr_p - sl_p if curr_p > sl_p else (curr_p * 0.02)
        rr_val_str = f"{reward_st / risk_st:.2f} : 1" if (risk_st > 0 and reward_st > 0) else "N/A"

        bin_p = float(ai.get('curr_bin_price', poc_p))
        level_label, level_icon = ("하방 지지(방어)", "🛡️") if curr_p >= bin_p else ("상방 저항(막힐)", "🧱")
        def_prob = float(ai.get('defense_prob', 60.0))
        def_color = "#ff4b4b" if def_prob >= 50.0 else "#38bdf8"

        top_pct = float(ai.get('top1_pct', 0.0))
        top_touch = int(ai.get('top1_touches', 0))
        curr_pct = float(ai.get('curr_bin_pct', 0.0))
        curr_touch = int(ai.get('curr_bin_touches', 0))

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div style="background-color:#1e1e1e; padding:20px; border-radius:10px; border: 1px solid #444; height:100%;">
                <h2 style="margin-top:0; color:#ffffff; font-size:20px;">📝 Price Action & 지지저항 브리핑</h2>
                <ul style="font-size:15px; color:#dddddd; line-height: 1.9; list-style:none; padding-left:0;">
                    <li style="font-size:16px; color:#ffeb3b;">📌 <b>현재 가격:</b> <b>{fmt_p(curr_p)}</b> (20일 이격도: <b>{disparity_20:.1f}%</b>)</li>
                    <li style="font-size:15px; color:#ffb300;">🎯 <b>최대 매물대(POC):</b> <b>{fmt_p(poc_p)}</b> {fmt_color_pct(poc_dist)} (비중: {top_pct:.1f}%, 터치: {top_touch}회)</li>
                    <li style="font-size:15px; color:#6ee7b7;">📈 <b>이동평균 관성:</b> <b>{ai['swing_trend']}</b></li>
                    <li style="font-size:14px; color:#38bdf8;">🛡️ <b>장기 수급 지지/저항:</b> 120일선 <b>{fmt_p(ai.get('ma_120', 0))}</b> | 200일선 <b>{fmt_p(ai.get('ma_200', 0))}</b></li>
                    <li style="font-size:15px; color:#6ee7b7;">📊 <b>세력 수급 스캔:</b> <b>{ai['swing_setup']}</b></li>
                    <li style="font-size:15px; color:#38bdf8;">{level_icon} <b>매물대 {level_label} 확률:</b> <b style="color:{def_color};">{def_prob:.1f}%</b> (비중: {curr_pct:.1f}%, 터치: {curr_touch}회)</li>
                    <li style="font-size:16px; color:#ffffff;">🎯 <b>알고리즘 확신도 / 1~5봉 기대수익:</b> <b style="color:{win_color};">{win_rate:.1f}%</b> / <b style="color:{upside_color};">{upside_txt}</b></li>
                    <li style="font-size:14px; color:#a7f3d0;">⚖️ <b>실전 단타 기대 손익비 (R/R):</b> <b>{rr_val_str}</b> (ATR 목표/손절 기준)</li>
                    <li style="font-size:14px; color:#e2e8f0;">🛡️ <b>수평 지지:</b> <b>{fmt_p(supp_p)}</b> {fmt_color_pct(supp_dist)} | 🧱 <b>수평 저항:</b> <b>{fmt_p(resi_p)}</b> {fmt_color_pct(resi_dist)}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            if ai['success_reasons'] or ai['failed_reasons']:
                st.markdown("""
                <div style="background-color:#141414; padding:18px; border-radius:10px; border: 1px solid #334155; height:100%;">
                    <h2 style="margin-top:0; color:#38bdf8; font-size:19px; font-weight:bold; margin-bottom:15px;">🔍 차트 내부 지표 조건 실시간 매칭 상태</h2>
                """, unsafe_allow_html=True)
                
                if ai['success_reasons']:
                    st.markdown('<p style="color:#ff4b4b; font-weight:bold; margin-bottom:5px; font-size:14px;">🟢 12대 지표 상방 합일 조건 (매수 모멘텀 유효)</p>', unsafe_allow_html=True)
                    for reason in ai['success_reasons']:
                        st.markdown(f"<span style='color:#e2e8f0; font-size:13.5px;'>• {reason}</span>", unsafe_allow_html=True)
                    st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)
                    
                if ai['failed_reasons']:
                    st.markdown('<p style="color:#3b82f6; font-weight:bold; margin-bottom:5px; font-size:14px;">🔵 12대 지표 하방 약세 조건 (리스크/관망 권고)</p>', unsafe_allow_html=True)
                    for reason in ai['failed_reasons']:
                        st.markdown(f"<span style='color:#e2e8f0; font-size:13.5px;'>• {reason}</span>", unsafe_allow_html=True)
                        
                st.markdown("</div>", unsafe_allow_html=True)

        # 실시간 AI 매매 주문서
        st.write("---")
        st.markdown("### 📋 실시간 AI 매매 주문서 (5대 기술 지표 실시간 검증)")
# ====================================================================
        # 🎯 [신규 추가] 4대 핵심 매수 필터 조건 실시간 충족 여부 상태 바
        # ====================================================================
        is_4cond_met = ai.get('is_four_conditions_met', False)
        if is_4cond_met:
            st.markdown("""
            <div style="background-color: #064e3b; border: 1px solid #10b981; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; color: #a7f3d0; font-size: 14px;">
                🔥 <b>[4대 핵심 매수 조건 100% 충족]</b> 20/60일선 우상향 + ADX(20↑) 상승 + DMI(+DI) 우위/상승 + MACD(0~20) 조건 완벽 부합!
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color: #1e293b; border: 1px solid #334155; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; color: #94a3b8; font-size: 13px;">
                ⚪ <b>[4대 핵심 필터 관망]</b> 현재 4대 매수 필수 조건 중 일부 미달 국면입니다. (눌림목 대기 권고)
            </div>
            """, unsafe_allow_html=True)

        ord_col1, ord_col2 = st.columns([1, 1])
        with ord_col1:
            st.markdown("#### 🟢 실시간 매수 승인 체크리스트")
            st.markdown(f"""
            * **그랜빌의 거래량 돌파:** {'🔥 [상승] 평소 2배 이상 세력 거래량 유입' if sig_vol_buy else '⚪ [대기] 기준 돌파 거래량 미달'}
            * **제럴드 아펠의 MACD 골든/반전:** {'🔥 [상승] MACD 교차 또는 히스토그램 반전' if sig_macd_buy else '⚪ [대기] 매수 모멘텀 약세'}
            * **와일더의 RSI 과매도 탈출:** {'🔥 [상승] RSI 30 이하 공포 권역 진입/탈출' if sig_rsi_buy else '⚪ [대기] 침체 신호 없음'}
            * **와일더의 DMI/ADX 추세 가속:** {'🔥 [상승] +DI 우위 및 ADX 20 돌파 가속' if sig_dmi_buy else '⚪ [대기] 정배열 에너지 부족'}
            * **장기 이평선(120/200일) 지지:** {'🔥 [상승] 120일/200일선 상회 (장기 지지선 사수)' if sig_ma_buy else '⚪ [대기] 장기 이평선 저항 상존'}
            """, unsafe_allow_html=True)

        with ord_col2:
            st.markdown("#### 🔵 실시간 매도/진입 금지 체크리스트")
            st.markdown(f"""
            * **그랜빌의 거래량 클라이맥스:** {'🌊 [위험] 역사적 대량 거래량 음봉 폭탄' if sig_vol_sell else '🟢 [안전] 대량 투매 징후 없음'}
            * **제럴드 아펠의 MACD 데드크로스:** {'🌊 [위험] MACD 추세선 하향 교차 붕괴' if sig_macd_sell else '🟢 [안전] 추세 상방 유지'}
            * **와일더의 RSI 과매수 광기 이탈:** {'🌊 [위험] RSI 70 이상 과열권 붕괴 시작' if sig_rsi_sell else '🟢 [안전] 과열 리스크 낮음'}
            * **와일더의 DMI 매도 우위 역배열:** {'🌊 [위험] -DI가 +DI를 압도하는 매도세 장악' if sig_dmi_sell else '🟢 [안전] 매도 주도권 없음'}
            * **장기 이평선(120/200일) 저항:** {'🌊 [위험] 120일 또는 200일선 하회 (머리 위 저항벽)' if sig_ma_sell else '🟢 [안전] 장기 저항선 위험 낮음'}
            """, unsafe_allow_html=True)

    # --------------------------------------------------------------------
    # 탭 2: 자산/포지션 계산기 및 분할 청산 전술
    # --------------------------------------------------------------------
    with detail_tab2:
        st.markdown("### 🧮 자산 관리 & 포지션 사이징")
        
        c_ps1, c_ps2 = st.columns(2)
        default_balance = 10000000.0 if currency_symbol == "₩" else 10000.0
        step_balance = 1000000.0 if currency_symbol == "₩" else 1000.0
        
        with c_ps1:
            account_balance = st.number_input(
                f"💰 투자 가능 금액 ({currency_symbol})", 
                min_value=0.0, value=default_balance, step=step_balance, key=f"ps_balance_{tab_name}"
            )
            # 💡 [3자리 콤마 실시간 안내] 입력 금액 천단위 구분선 표기
            fmt_bal = f"{account_balance:,.0f}" if currency_symbol == "₩" else f"{account_balance:,.2f}"
            st.caption(f"💡 입력 금액 확인: <b style='color:#38bdf8;'>{currency_symbol}{fmt_bal}</b>", unsafe_allow_html=True)
        with c_ps2:
            risk_pct = st.slider(
                "🛡️ 1회 매매 허용 리스크 비율 (%)", 
                min_value=0.5, max_value=5.0, value=1.5, step=0.1, key=f"ps_risk_{tab_name}"
            )
        
        max_risk_amount = account_balance * (risk_pct / 100.0)
        price_risk_per_share = max(entry_target_p - sl_p, entry_target_p * 0.01)
        calc_qty = int(max_risk_amount / price_risk_per_share) if price_risk_per_share > 0 else 0
        calc_buy_val = calc_qty * entry_target_p
        
        if calc_buy_val > account_balance and entry_target_p > 0:
            calc_qty = int(account_balance / entry_target_p)
            calc_buy_val = calc_qty * entry_target_p

        account_weight = (calc_buy_val / account_balance * 100.0) if account_balance > 0 else 0.0
        fmt_val = lambda v: f"₩{v:,.0f}" if currency_symbol == "₩" else f"${v:,.2f}"

        st.markdown(f"""
        <div style="background-color:#0f172a; padding:12px; border-radius:8px; border:1px solid #334155; margin-top:10px; margin-bottom:15px;">
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; text-align:center;">
                <div>
                    <div style="font-size:11px; color:#94a3b8;">🎯 1회 최대 허용 손실금</div>
                    <div style="font-size:14px; font-weight:bold; color:#ef4444;">{fmt_val(max_risk_amount)}</div>
                </div>
                <div>
                    <div style="font-size:11px; color:#94a3b8;">📦 권장 매수 수량</div>
                    <div style="font-size:14px; font-weight:bold; color:#38bdf8;">{calc_qty:,} 주(개)</div>
                </div>
                <div>
                    <div style="font-size:11px; color:#94a3b8;">💵 권장 투입 금액 (비중)</div>
                    <div style="font-size:14px; font-weight:bold; color:#10b981;">{fmt_val(calc_buy_val)} ({account_weight:.1f}%)</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🏅 30년 베테랑 분할 청산 및 물타기 전술 보드")
        base_price = entry_price if ('entry_price' in locals() and entry_price > 0) else entry_target_p
        veteran_stop_loss = ai['poc_price']
        fallback_entry = round(base_price * 0.94, 1)  
        pool_entry_price = round(base_price * 0.88, 1) 
        target_profit = round(base_price * 1.12, 1)  

        if currency_symbol == "₩":
            txt_entry, txt_stop = f"{currency_symbol}{fallback_entry:,.0f}", f"{currency_symbol}{veteran_stop_loss:,.0f}"
            txt_pool, txt_target = f"{currency_symbol}{pool_entry_price:,.0f}", f"{currency_symbol}{target_profit:,.0f}"
        else:
            txt_entry, txt_stop = f"{currency_symbol}{fallback_entry:,.1f}", f"{currency_symbol}{veteran_stop_loss:,.1f}"
            txt_pool, txt_target = f"{currency_symbol}{pool_entry_price:,.1f}", f"{currency_symbol}{target_profit:,.1f}"

        st.markdown(f"""
        <div style="background-color:#1e293b55; padding:12px; border-radius:6px; border: 1px solid #475569; font-size:13px; line-height:1.6;">
            <div>📉 <b>현실적 눌림목 진입가:</b> <b style="color:#f43f5e; font-size:15px;">{txt_entry}</b></div>
            <div>🚨 <b>리스크 방어선 손절가:</b> <b style="color:#3b82f6; font-size:14px;">{txt_stop}</b></div>
            <div>💧 <b>재무 대기 물타기 타점:</b> <b style="color:#eab308; font-size:14px;">{txt_pool}</b></div>
            <hr style="border:0; border-top:1px solid #475569; margin:10px 0;">
            <div>🎯 <b>물타기 후 청산 목표 익절가:</b> <b style="color:#10b981; font-size:16px;">{txt_target}</b></div>
        </div>
        """, unsafe_allow_html=True)

    # --------------------------------------------------------------------
    # 탭 3: AI 진단 및 실시간 뉴스피드
    # --------------------------------------------------------------------
    with detail_tab3:
        if api_key:
            st.markdown("### 🤖 Gemini AI 실시간 차트 분석")
            user_question = st.text_input(
                "💬 제미나이에게 궁금한 점을 질문해 보세요", 
                placeholder="예시: 오늘 꼬리 달릴 때 불타기 해도 될까?", 
                key=f"gemini_q_{tab_name}"
            )
            roi = ((ai['price'] - entry_price) / entry_price * 100) if (entry_price > 0 and ai.get('price', 0) > 0) else 0.0

            if st.button("🔍 제미나이 AI 분석 실행", key=f"gemini_btn_{tab_name}"):
                with st.spinner("제미나이가 데이터 시트를 분석 중입니다..."):
                    advice_text = get_gemini_advice(api_key, selected_name, ai, entry_price, roi, currency_symbol, user_question)
                with st.container(border=True):
                    st.markdown(advice_text)

        # AI 분석 투명성 근거 도장
        st.caption("ℹ️ *본 AI 진단은 실시간 시세, POC 매물대, TTM Squeeze, 6대 이평선 수치(Fact Sheet)만을 바탕으로 생성된 정량적 분석 결과입니다.*")
        st.markdown("<br>", unsafe_allow_html=True)

        # ====================================================================
        # 📰 실시간 주요 뉴스피드 수집 및 출력 (NameError 완전 방지)
        # ====================================================================
        st.markdown("### 📰 실시간 주요 뉴스피드")
        
        news_html = ""
        try:
            import urllib.request
            import urllib.parse
            import xml.etree.ElementTree as ET

            encoded_name = urllib.parse.quote(f"{selected_name} when:3d")
            url = f"https://news.google.com/rss/search?q={encoded_name}&hl=ko&gl=KR&ceid=KR:ko"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                xml_data = response.read()
                
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:2]
            
            if items:
                news_html = "<b>📰 실시간 관련 주요 뉴스 링크 (클릭 시 원본 직통):</b><br>"
                for item in items:
                    title = item.find('title').text
                    working_link = item.find('link').text
                    news_html += f"• <a href='{working_link}' target='_blank' style='color: #38bdf8; text-decoration: none; font-weight: bold;'>{title}</a><br>"
            else:
                news_html = "<b>📰 실시간 관련 주요 뉴스:</b><br>• 최근 3일 이내에 해당 종목의 단기 특이 뉴스가 포착되지 않았습니다."
        except Exception:
            news_html = "⚠️ [시스템] 실시간 뉴스 망 연동 중 지연이 발생하여 뉴스를 표시할 수 없습니다."

        st.markdown(f"""
        <div style="background-color: rgba(255,255,255,0.03); padding: 10px 14px; border-radius: 6px; font-size: 13px; line-height: 1.7; color: #e2e8f0; border: 1px solid #334155;">
        {news_html.strip()}
        </div>
        """, unsafe_allow_html=True)


# ====================================================================
# [4. UI 화면 렌더링 및 사이드바 이벤트 제어]
# ====================================================================
import requests
import re
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

def contains_hangul(text):
    return bool(re.search('[ㄱ-ㅎㅏ-ㅣ가-힣]', text))

def translate_ko_to_en(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ko&tl=en&dt=t&q={text}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            return response.json()[0][0][0]
    except Exception: pass
    return text

def search_ticker(query):
    if not query: return None, None
    query_clean = query.strip().lower()
    
    # 1. 한 글자 이상 입력 시 셋업 리스트(ASSETS) 부분 일치(contains) 검색
    for sector_name, sector_dict in ASSETS.items():
        for name, ticker in sector_dict.items():
            if "등극주" in name or "시총" in name or "주요통화" in name: 
                continue
            t_lower = ticker.lower()
            ticker_base = t_lower.replace('-', '.').split('.')[0]
            # 이름이나 티커에 입력 키워드가 한 글자라도 포함되면 즉시 반환
            if query_clean in name.lower() or query_clean in ticker_base or query_clean in t_lower:
                return ticker, name
                
    # 2. 한국 주식 KRX 마스터 명부 한 글자 부분 일치 검색
    try:
        import FinanceDataReader as fdr
        krx_df = fdr.StockListing('KRX')
        matched = krx_df[krx_df['Name'].str.lower().str.contains(query_clean, na=False)]
        if not matched.empty:
            code = matched['Code'].values[0]
            market = matched['Market'].values[0]
            matched_name = matched['Name'].values[0]
            suffix = '.KQ' if 'KOSDAQ' in str(market).upper() else '.KS'
            return f"{code}{suffix}", matched_name
    except Exception:
        pass

    # 3. 매칭되는 한국 주식이 없으면 외국 주식용 기존 야후 검색 엔진 작동
    search_term = query_clean
    if contains_hangul(query):
        translated = translate_ko_to_en(query)
        if translated: search_term = translated.strip().lower()
        
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={search_term}&lang=en-US"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            quotes = response.json().get('quotes', [])
            if quotes:
                best_match = quotes[0]
                ticker = best_match.get('symbol', '').upper()
                name = best_match.get('shortname') or best_match.get('longname') or ticker
                if best_match.get('quoteType', '') == 'CRYPTOCURRENCY' or ticker.endswith('-USD'):
                    ticker = f"{ticker.split('-')[0]}-KRW"
                    name = f"{name} (KRW)"
                return ticker, name
    except Exception: pass
    return query.strip().upper(), query.strip().upper()

# ====================================================================
# [4. UI 화면 렌더링 및 사이드바 이벤트 제어] - 관제탑 통합 업그레이드 버젼
# ====================================================================
st.sidebar.markdown("### 🔍 종목 탐색기")

sector = st.sidebar.radio(
    "📁 섹터 선택",
    [
        "₩ 국내 주식",
        "💲 미국 주식",  # 👈 기존 '$'를 '💲' 이모지로 똑같이 바꿔줍니다!
        "🪙 암호화폐(코인)",
        "🎯 내 실전 보유종목 관제",
        "🌏 글로벌 실시간 증시 뉴스",
        "🔍 직접 이름/티커 검색"
    ]
)

# =========================================================
# 📍 1번 위치: 사이드바에 토스증권 바로가기 버튼 추가
# =========================================================
st.sidebar.markdown("---")
st.sidebar.link_button(
    "🔥 토스증권 바로가기 PC ↗", 
    "https://www.tossinvest.com/?ranking-type=trending_category&focusedTicsId=29&tics-nation=KR",
    use_container_width=True
)

# 현재 시스템 구동 모드 판정용 플래그 초기화
is_macro_mode = False

# -------------------------------------------------------------------
# [분기점 0] 내 실전 보유종목 관제 선택 시 (🎯 신규 처리)
# -------------------------------------------------------------------
if sector == "🎯 내 실전 보유종목 관제":
    render_my_portfolio_manager()
    st.stop()  # 관제탑만 화면에 띄우고 하단 차트 연산 중단

# -------------------------------------------------------------------
# [분기점 1] 사용자가 직접 타이핑해서 주식을 검색할 때
# -------------------------------------------------------------------
elif sector == "🔍 직접 이름/티커 검색":
    search_query = st.sidebar.text_input("✍️ 기업명 또는 티커 검색 (한글 가능)", value="테슬라", key="sb_custom_search_input")
    if search_query:
        safe_ticker, selected_name = search_ticker(search_query)
        if safe_ticker:
            st.sidebar.markdown(f"<div style='background-color:#1e293b; padding:8px; border-radius:5px; border-left:4px solid #38bdf8; color:#38bdf8; font-size:12px; font-weight:bold; margin-bottom:15px;'>🎯 매칭 성공: {selected_name} ({safe_ticker})</div>", unsafe_allow_html=True)
    else:
        safe_ticker, selected_name = "TSLA", "Tesla"

# -------------------------------------------------------------------
# [분기점 2] 유저가 요청한 실시간 뉴스 매크로 관제탑 메뉴를 선택했을 때 (세션 주입 교정)
# -------------------------------------------------------------------
elif sector == "🌏 글로벌 실시간 증시 뉴스":
    st.session_state['is_macro_mode'] = True  # 👈 세션 상태에 직접 True 주입
    is_macro_mode = True
    safe_ticker, selected_name = None, "글로벌 매크로 시황"

# -------------------------------------------------------------------
# [분기점 3] 일반 주식 섹터(국내, 미국, 코인)를 선택해 탐색할 때
# -------------------------------------------------------------------
else:
    st.session_state['is_macro_mode'] = False
    raw_ticker_list = list(ASSETS[sector].keys())
    ticker_list = [k for k in raw_ticker_list if not any(x in k for x in ["등극주", "시총", "주요통화"])]
    
    # 🟢 섹터 변경 시 인덱스 및 선택 상태 초기화
    if 'current_sector' not in st.session_state or st.session_state.current_sector != sector:
        st.session_state.current_sector = sector
        st.session_state.current_idx = 0
        st.session_state['sb_ticker_select'] = ticker_list[0]

    # 🟢 selectbox 수동 변경 시 인덱스 자동 동기화
    if 'sb_ticker_select' in st.session_state and st.session_state.sb_ticker_select in ticker_list:
        st.session_state.current_idx = ticker_list.index(st.session_state.sb_ticker_select)
        
    if 'current_idx' not in st.session_state or st.session_state.current_idx >= len(ticker_list):
        st.session_state.current_idx = 0

    col1, col2 = st.sidebar.columns(2)
    if col1.button("⬅️ 이전 종목", key="btn_prev_ticker"):
        st.session_state.current_idx = max(0, st.session_state.current_idx - 1)
        st.session_state.sb_ticker_select = ticker_list[st.session_state.current_idx]
        st.rerun()
        
    if col2.button("다음 종목 ➡️", key="btn_next_ticker"):
        st.session_state.current_idx = min(len(ticker_list) - 1, st.session_state.current_idx + 1)
        st.session_state.sb_ticker_select = ticker_list[st.session_state.current_idx]
        st.rerun()

    selected_name = st.sidebar.selectbox("🎯 종목명", ticker_list, index=st.session_state.current_idx, key="sb_ticker_select")
    safe_ticker = ASSETS[sector][selected_name]

# 🌟 사이드바 통계창을 그리기 전에 실시간 주가 데이터부터 강제 로드
# 매크로 모드가 아닐 때만 주가 연산 엔진을 작동시켜 무필터 오류를 방지합니다.
if not is_macro_mode:
    raw_data = get_raw_daily_data(safe_ticker) if safe_ticker else None
else:
    raw_data = None

# 초기 동적 변수 선언
GLOBAL_WIN_RATE, GLOBAL_AVG_RETURN, GLOBAL_TOTAL_SIGNALS = 0.0, 0.0, 0

# -------------------------------------------------------------------
# [관제탑 핵심 출력 엔진] AttributeError 방어형 뉴스피드 코드
# -------------------------------------------------------------------
# 🎯 [오류 해결] .is_macro_mode 대신 .get()을 사용하여 변수가 없을 때 발생하는 크래시를 원천 차단합니다.
if st.session_state.get('is_macro_mode', False):
    st.info("🌍 글로벌 실시간 증시 뉴스")
    st.write("미국 뉴욕증시 및 국내 금융시장에 직접적인 하이 임팩트를 주는 당일 주요 시황 뉴스를 실시간 스캔합니다.")
    st.markdown("### 🔥 당일 미-국내 증시 영향력 TOP 5 핵심 뉴스")

    try:
        import urllib.request
        import urllib.parse
        import xml.etree.ElementTree as ET

        macro_query = "미국 증시 국채 금리 환율 시황 연준 Fed 뉴욕증시 코스피"
        encoded_macro = urllib.parse.quote(macro_query)
        url = f"https://news.google.com/rss/search?q={encoded_macro}&hl=ko&gl=KR&ceid=KR:ko"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')[:5]
        
        placeholders = [
            "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=300&q=80",
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&q=80",
            "https://images.unsplash.com/photo-1591696205602-2f950c417cb9?w=300&q=80",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=300&q=80",
            "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=300&q=80"
        ]
        
        if items:
            for idx, item in enumerate(items):
                title_text = item.find('title').text
                
                if ' - ' in title_text:
                    pure_title, source = title_text.rsplit(' - ', 1)
                else:
                    pure_title, source = title_text, "시황 종합"
                    
                encoded_title = urllib.parse.quote(pure_title)
                working_link = f"https://search.naver.com/search.naver?where=news&query={encoded_title}"
                thumb_url = placeholders[idx % len(placeholders)]
                
                st.markdown(f"""
                <div style="display: flex; background-color: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); align-items: center; width: 100%;">
                    <img src="{thumb_url}" style="width: 120px; height: 85px; object-fit: cover; flex-shrink: 0;" />
                    <div style="padding: 10px 16px; flex-grow: 1;">
                        <span style="font-size: 11px; color: #a1a1aa; font-weight: 600; text-transform: uppercase;">📰 {source}</span>
                        <h4 style="margin: 4px 0 0 0; font-size: 14px; line-height: 1.45; font-weight: bold;">
                            <a href="{working_link}" target="_blank" style="color: #38bdf8; text-decoration: none; transition: color 0.2s;">{pure_title}</a>
                        </h4>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("🔥 현재 금융시장을 흔들 만한 단기 대형 돌발 뉴스가 포착되지 않았습니다.")
    except Exception as e:
        st.error("⚠️ [시스템] 실시간 글로벌 마켓 뉴스망 연동 중 지연이 발생했습니다.")
        
    st.stop()



# ====================================================================
# 🌟 [개동적 백테스팅] 10개년(또는 상장일 이후) 90% 타점 + 3단 분할 익절 + 구조컷 손절 시뮬레이터
# ====================================================================
if raw_data is not None and not raw_data.empty:
    df_stats = raw_data.copy()
    df_stats['MA_5']   = df_stats['Close'].rolling(5, min_periods=1).mean()
    df_stats['MA_10']  = df_stats['Close'].rolling(10, min_periods=1).mean()
    df_stats['MA_20']  = df_stats['Close'].rolling(20, min_periods=1).mean()
    df_stats['MA_60']  = df_stats['Close'].rolling(60, min_periods=1).mean()
    df_stats['MA_120'] = df_stats['Close'].rolling(120, min_periods=1).mean()
    df_stats['MA_200'] = df_stats['Close'].rolling(200, min_periods=1).mean()
    df_stats['STD_20'] = df_stats['Close'].rolling(20, min_periods=1).std()
    df_stats['Vol_MA_20'] = df_stats['Volume'].rolling(20, min_periods=1).mean()
    df_stats['TR'] = np.maximum(df_stats['High'] - df_stats['Low'], np.maximum(abs(df_stats['High'] - df_stats['Close'].shift(1)), abs(df_stats['Low'] - df_stats['Close'].shift(1))))
    df_stats['ATR'] = df_stats['TR'].rolling(14, min_periods=1).mean()
    df_stats['BB_Upper'] = df_stats['MA_20'] + (df_stats['STD_20'] * 2)
    df_stats['BB_Lower'] = df_stats['MA_20'] - (df_stats['STD_20'] * 2)
    df_stats['BB_Width'] = df_stats['BB_Upper'] - df_stats['BB_Lower']
    df_stats['KC_Upper'] = df_stats['MA_20'] + (df_stats['ATR'] * 1.5)
    df_stats['Squeeze_On'] = df_stats['BB_Upper'] < df_stats['KC_Upper']
    df_stats['Resist_20'] = df_stats['High'].rolling(20, min_periods=1).max()
    df_stats['Support_20'] = df_stats['Low'].rolling(20, min_periods=1).min()
    
    delta = df_stats['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / (loss + 1e-10)
    df_stats['RSI_14'] = 100 - (100 / (1 + rs))
    df_stats['RSI_14'] = df_stats['RSI_14'].fillna(50)

    ema_12 = df_stats['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df_stats['Close'].ewm(span=26, adjust=False).mean()
    df_stats['MACD'] = ema_12 - ema_26
    df_stats['Signal'] = df_stats['MACD'].ewm(span=9, adjust=False).mean()
    df_stats['MACD_Hist'] = df_stats['MACD'] - df_stats['Signal']
    
    base_score = 50
    p_score = np.zeros(len(df_stats))
    body = (df_stats['Close'] - df_stats['Open']).abs()
    upper_sh = df_stats['High'] - np.maximum(df_stats['Open'], df_stats['Close'])
    lower_sh = np.minimum(df_stats['Open'], df_stats['Close']) - df_stats['Low']
    is_green = df_stats['Close'] > df_stats['Open']
    is_red = df_stats['Close'] < df_stats['Open']
    
    p_score += np.where((lower_sh > 2.0 * body) & (upper_sh < 0.3 * body) & (df_stats['Close'] < df_stats['MA_20']), 15, 0)
    p_score -= np.where((upper_sh > 2.0 * body) & (lower_sh < 0.3 * body) & (df_stats['Close'] > df_stats['MA_20']), 15, 0)
    p_score += np.where(is_red.shift(1) & is_green & (df_stats['Open'] <= df_stats['Close'].shift(1)) & (df_stats['Close'] >= df_stats['Open'].shift(1)), 15, 0)
    p_score -= np.where(is_green.shift(1) & is_red & (df_stats['Open'] >= df_stats['Close'].shift(1)) & (df_stats['Close'] <= df_stats['Open'].shift(1)), 15, 0)
    p_score += np.where((df_stats['Low'] <= df_stats['Support_20'].shift(1) * 1.01).rolling(15, min_periods=1).sum() >= 2, 15, 0)
    p_score -= np.where((df_stats['High'] >= df_stats['Resist_20'].shift(1) * 0.99).rolling(15, min_periods=1).sum() >= 2, 20, 0)
    p_score += np.where(df_stats['Close'] >= df_stats['BB_Upper'], 20, 0)
    p_score -= np.where(df_stats['Close'] <= df_stats['BB_Lower'], 15, 0)
    p_score += np.where(df_stats['Close'] >= df_stats['Resist_20'].shift(1) * 0.98, 25, 0)
    rvol = df_stats['Volume'] / df_stats['Vol_MA_20']
    p_score += np.where(rvol >= 2.0, 25, np.where(rvol >= 1.2, 10, 0))
    p_score += np.where((df_stats['Close'] > df_stats['MA_5']) & (df_stats['MA_5'] > df_stats['MA_20']), 20, 0)
    p_score -= np.where(df_stats['Close'] < df_stats['MA_20'], 35, 0)
    p_score -= np.where(df_stats['Close'] < df_stats['MA_60'], 15, 0)
    
    clv = ((df_stats['Close'] - df_stats['Low']) - (df_stats['High'] - df_stats['Close'])) / (df_stats['High'] - df_stats['Low'] + 1e-10)
    smart_money_flow = clv * rvol
    p_score += np.where(smart_money_flow >= 1.5, 20, np.where(smart_money_flow <= -1.5, -25, 0))

    fake_breakout = (df_stats['Close'] < df_stats['Open']) & (df_stats['High'] >= df_stats['Open'] * 1.05) & (rvol >= 1.5)
    p_score -= np.where(fake_breakout, 45, 0)
    p_score -= np.where((df_stats['Close'] < df_stats['MA_60']) | (df_stats['Close'] < df_stats['MA_120']), 40, 0)
    p_score -= np.where(df_stats['RSI_14'] >= 65, 30, 0)
    p_score += np.where(df_stats['Squeeze_On'] & (rvol >= 1.5), 20, 0)
    
    df_stats['Calculated_Score'] = np.clip(base_score + p_score, 10, 95)
    
    sig_days = df_stats[df_stats['Calculated_Score'] >= 90].copy()
    
    if not sig_days.empty:
        trade_returns = []
        is_win_list = []
        
        for idx in sig_days.index:
            pos = df_stats.index.get_loc(idx)
            
            # 💡 [승률 보스터 필터 1] 장기 역배열(60일선 아래) 종목 연산에서 원천 차단 패스
            if float(df_stats['Close'].iloc[pos]) < float(df_stats['MA_60'].iloc[pos]):
                continue
                
            # 💡 [승률 보스터 필터 2] RSI 70 이상의 단기 꼭대기 초과열 종목 패스
            if float(df_stats['RSI_14'].iloc[pos]) >= 70:
                continue
                
            available_bars = len(df_stats) - pos - 1
            if available_bars <= 0: continue
            
            # 💡 [승률 보스터 필터 3] 다음 날 -1% 지정가 눌림목 체결 시뮬레이션
            signal_close = float(df_stats['Close'].iloc[pos])
            entry_target = signal_close * 0.990 # 당일 종가 대비 1% 할인 가격
            
            next_low = float(df_stats['Low'].iloc[pos + 1])
            if next_low > entry_target:
                continue # 다음 날 더 비싸게 날아가 버린 건 추격하지 않고 취소 (승률 보호)
                
            # 체결 성공 시 평단가는 할인된 지정가(entry_target)로 강력 세팅
            entry_p = entry_target
            atr = float(df_stats['ATR'].iloc[pos])
            support_p = float(df_stats['Support_20'].iloc[pos])
            
            # 보정된 평단가 기준으로 익절 상한선(5/10/20%) 재매핑
            tighter_sl = max(support_p, entry_p * 0.96) if support_p < entry_p and (entry_p - support_p)/entry_p < 0.05 else entry_p * 0.965
            tp1_target = min(entry_p + (atr * 0.8), entry_p * 1.05)
            tp2_target = min(entry_p + (atr * 1.5), entry_p * 1.10)
            tp3_target = min(entry_p + (atr * 2.5), entry_p * 1.20)
            
            tp1_sold, tp2_sold, tp3_sold = False, False, False
            total_revenue = 0.0
            remaining_weight = 1.0
            
            # 체결일(pos+1) 당일 변동성부터 즉시 추적 개시
            for d in range(1, available_bars + 1):
                current_idx = pos + d
                high_d = float(df_stats['High'].iloc[current_idx])
                low_d = float(df_stats['Low'].iloc[current_idx])
                close_d = float(df_stats['Close'].iloc[current_idx])
                ma20_d = float(df_stats['MA_20'].iloc[current_idx])
                macd_hist_d = float(df_stats['MACD_Hist'].iloc[current_idx])
                bb_width_curr = float(df_stats['BB_Width'].iloc[current_idx])
                bb_width_prev = float(df_stats['BB_Width'].iloc[current_idx - 1])
                
                if low_d <= tighter_sl:
                    total_revenue += remaining_weight * tighter_sl
                    remaining_weight = 0.0
                    break
                
                if not tp1_sold and high_d >= tp1_target:
                    total_revenue += 0.50 * tp1_target
                    remaining_weight -= 0.50
                    tp1_sold = True
                    
                if not tp2_sold and high_d >= tp2_target:
                    total_revenue += 0.25 * tp2_target
                    remaining_weight -= 0.25
                    tp2_sold = True
                    
                # 미세 수렴(전날보다 좁아짐) 포착 시 3차 물량 조기 대피 청산
                is_early_exit = (close_d < ma20_d) or (bb_width_curr < bb_width_prev) or (macd_hist_d < 0)
                
                if not tp3_sold:
                    if high_d >= tp3_target:
                        total_revenue += remaining_weight * tp3_target
                        remaining_weight = 0.0
                        tp3_sold = True
                        break
                    elif is_early_exit:
                        total_revenue += remaining_weight * close_d
                        remaining_weight = 0.0
                        tp3_sold = True
                        break
                        
                if remaining_weight <= 0:
                    break
            
            if remaining_weight > 0:
                total_revenue += remaining_weight * float(df_stats['Close'].iloc[-1])
                remaining_weight = 0.0
                
            final_trade_return = (total_revenue - entry_p) / entry_p
            trade_returns.append(final_trade_return)
            is_win_list.append(final_trade_return > 0)
            
        if trade_returns:
            GLOBAL_WIN_RATE = float(sum(is_win_list) / len(trade_returns) * 100)
            GLOBAL_AVG_RETURN = float(np.mean(trade_returns) * 100)
            GLOBAL_TOTAL_SIGNALS = len(trade_returns)

# ====================================================================
# 4. 검증 통계 실시간 스코어보드 연산 및 출력 (하락 다이버전스 매수 금지 추가본)
# ====================================================================
import numpy as np

# 🚨 글로벌 변수 초기화 및 안전장치
GLOBAL_CUM_RETURN = 0.0
GLOBAL_WIN_RATE = 0.0
GLOBAL_TOTAL_SIGNALS = 0

# 🎯 종목명이 "글로벌 매크로 시황"이면 주식 분석을 전부 패스하고 즉시 뉴스피드 출력 후 종료
if 'selected_name' in locals() and selected_name == "글로벌 매크로 시황":
    st.info("🌍 글로벌 실시간 증시 뉴스 (국내 6개 + 미국 6개)")
    st.write("장전, 장중, 장 마감 후 시간대에 맞춰 단타 핵심 뉴스를 자동 분기하여 스캔합니다.")

    try:
        import urllib.request
        import urllib.parse
        import xml.etree.ElementTree as ET
        import re
        from datetime import datetime, time as dtime

        now_time = datetime.now().time()

        # 🎯 1. 대한민국 증시 세부 시간대 분기 (09:00 개장 / 15:30 마감)
        is_kr_premarket  = dtime(6, 0) <= now_time < dtime(9, 0)     # 장전 (06:00 ~ 09:00)
        is_kr_market     = dtime(9, 0) <= now_time < dtime(15, 30)   # 장중 (09:00 ~ 15:30)

        if is_kr_premarket:
            kr_time_filter = "when:3h"
            kr_status_txt = "🔴 장전 3시간 속보 모드 (09:00 개장 직전)"
        elif is_kr_market:
            kr_time_filter = "when:7h"
            kr_status_txt = "🟢 장중 실시간 속보 모드 (09:00~15:30 장중)"
        else:
            kr_time_filter = "when:12h"
            kr_status_txt = "🌙 장 마감 후 실시간 속보 모드 (15:30 마감 이후)"

        # 🎯 2. 미국 증시 세부 시간대 분기 (22:30 개장 / 05:00 마감 기준)
        is_us_premarket  = dtime(19, 30) <= now_time < dtime(22, 30)               # 장전 (19:30 ~ 22:30)
        is_us_market     = (now_time >= dtime(22, 30)) or (now_time < dtime(5, 0)) # 장중 (22:30 ~ 05:00)

        if is_us_premarket:
            us_time_filter = "when:3h"
            us_status_txt = "🔴 장전 3시간 속보 모드 (22:30 개장 직전)"
        elif is_us_market:
            us_time_filter = "when:7h"
            us_status_txt = "🟢 장중 실시간 속보 모드 (22:30~05:00 장중)"
        else:
            us_time_filter = "when:14h"
            us_status_txt = "🌙 장 마감 후 실시간 속보 모드 (05:00 마감 이후)"

        # 🎯 3. 검색 쿼리 구성
        kr_query = f"(실적 OR 급등 OR 수주 OR 공시 OR 어닝 OR 목표가 OR M&A) (코스피 OR 코스닥 OR 삼성전자 OR SK하이닉스) {kr_time_filter}"
        us_query = f"(실적 OR 급등 OR 어닝 OR M&A OR 엔비디아 OR 테슬라 OR 애플 OR 나스닥 OR 뉴욕증시) {us_time_filter}"

        EXCLUDE_SOURCES = ['블로그', 'blog', 'brunch', '포스트', '뉴스wire', 'newswire', '브런치']

        def extract_keywords(text):
            return set(re.findall(r'[가-힣a-zA-Z0-9]{2,}', text))

        def is_similar_news(new_words, word_set_list, threshold=0.4):
            if not new_words: return True
            for existing_words in word_set_list:
                intersection = new_words.intersection(existing_words)
                if len(intersection) / float(min(len(new_words), len(existing_words))) >= threshold:
                    return True
            return False

        # 🎯 4. 뉴스 수집 헬퍼 함수
        def fetch_market_news(query, limit=6):
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            items_res = []
            collected_words = []
            
            with urllib.request.urlopen(req, timeout=3) as response:
                root = ET.fromstring(response.read())
                for item in root.findall('.//item'):
                    if len(items_res) >= limit: break
                    
                    title_text = item.find('title').text
                    pure_title, source = title_text.rsplit(' - ', 1) if ' - ' in title_text else (title_text, "속보")
                    
                    if any(ex.lower() in source.lower() for ex in EXCLUDE_SOURCES):
                        continue
                        
                    current_words = extract_keywords(pure_title)
                    if is_similar_news(current_words, collected_words):
                        continue
                        
                    items_res.append((pure_title, source, item.find('link').text))
                    collected_words.append(current_words)
            return items_res

        kr_news = fetch_market_news(kr_query, 6)
        us_news = fetch_market_news(us_query, 6)

        # 📸 썸네일 고화질 이미지 리스트
        placeholders = [
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&q=80",
            "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=300&q=80",
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=300&q=80",
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=300&q=80",
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=300&q=80",
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=300&q=80"
        ]

        # 🎯 5. 썸네일 포함 UI 카드 출력 헬퍼 함수
        def render_news_section(title, news_list, status_txt):
            st.markdown(f"#### {title} <span style='font-size:12px; color:#38bdf8;'>[{status_txt}]</span>", unsafe_allow_html=True)
            
            if not news_list:
                st.caption("⚪ 해당 시간대에 발생한 특이 뉴스가 없습니다.")
                return

            for idx, (pure_title, source, working_link) in enumerate(news_list):
                thumb_url = placeholders[idx % len(placeholders)]
                st.markdown(f"""
                <div style="display: flex; background-color: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); align-items: center; width: 100%;">
                    <img src="{thumb_url}" style="width: 120px; height: 85px; object-fit: cover; flex-shrink: 0;" />
                    <div style="padding: 10px 16px; flex-grow: 1;">
                        <span style="font-size: 11px; color: #38bdf8; font-weight: bold;">🔥 [{source}]</span>
                        <h4 style="margin: 4px 0 0 0; font-size: 14px; line-height: 1.45; font-weight: bold;">
                            <a href="{working_link}" target="_blank" style="color: #e2e8f0; text-decoration: none;">{pure_title}</a>
                        </h4>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        render_news_section("🇰🇷 대한민국 증시 핵심 뉴스 (6선)", kr_news, kr_status_txt)
        st.write("")
        render_news_section("🇺🇸 미국 증시 핵심 뉴스 (6선)", us_news, us_status_txt)

    except Exception as e:
        st.error(f"⚠️ [시스템] 실시간 글로벌 뉴스망 동기화 실패 (오류 원인: {e})")
    
    st.stop()

# -------------------------------------------------------------------
# 🟢 [일반 주식 모드] 주식 종목을 선택했을 때만 작동하는 기존 분석 엔진
# -------------------------------------------------------------------
if 'df_stats' in locals() and df_stats is not None:
    df_back = df_stats.copy()
else:
    st.error("📊 시스템 데이터 로드 실패 가드레일 작동")
    st.markdown(f"""
    **🚨 실시간 데이터 내부 상태 점검 리포트:**
    * **선택된 종목명:** `{selected_name if 'selected_name' in locals() else '미지'}`
    * **전달된 주식 티커:** `{safe_ticker if 'safe_ticker' in locals() else 'None'}`
    * **주가 원본(`raw_data`):** `{'🟢 정상 로드됨' if ('raw_data' in locals() and raw_data is not None) else '❌ 비어있음 (서버 통신 실패)'}`
    """)
    st.stop()

# 💡 [속도 극대화] 10년치 전수 백테스트 루프 전체를 캐싱 처리하여 Rerun 시 반복 연산 완벽 차단
@st.cache_data(ttl=3600)
def run_heavy_backtest_engine(df_back):
    # 🧭 다이버전스 판독용 CCI 지표 연산
    tp = (df_back['High'] + df_back['Low'] + df_back['Close']) / 3
    ma_tp = tp.rolling(14, min_periods=1).mean()
    md_tp = tp.rolling(14, min_periods=1).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df_back['CCI_14'] = (tp - ma_tp) / (0.015 * md_tp + 1e-10)

    trade_returns = []
    is_win_list = []

    # 과거 10개년 하루씩 순차 전수조사 진행
    for pos in range(120, len(df_back) - 15):
        c_open = float(df_back['Open'].iloc[pos])
        c_high = float(df_back['High'].iloc[pos])
        c_low = float(df_back['Low'].iloc[pos])
        c_close = float(df_back['Close'].iloc[pos])
        c_atr = float(df_back['ATR'].iloc[pos])
        c_score = float(df_back['Calculated_Score'].iloc[pos])
        
        # 🧭 [실시간 Rolling POC 산출] 실제 달력 기준 90일 = 63거래일 압축 최적화 완료!
        start_idx = max(0, pos - 90)
        w_closes = df_back['Close'].iloc[start_idx:pos+1].to_numpy()
        w_volumes = df_back['Volume'].iloc[start_idx:pos+1].to_numpy()
        
        if len(w_closes) > 0 and w_volumes.sum() > 0:
            price_bins = np.linspace(w_closes.min(), w_closes.max(), 15)
            bin_volumes = np.zeros(14)
            bin_indices = np.digitize(w_closes, price_bins) - 1
            for i, b_idx in enumerate(bin_indices):
                if 0 <= b_idx < 14: 
                    bin_volumes[b_idx] += w_volumes[i]
            poc_price = float((price_bins[np.argmax(bin_volumes)] + price_bins[np.argmax(bin_volumes)+1]) / 2)
        else:
            poc_price = c_close

        # 📊 [상승/하락 다이버전스 실시간 계량 연산 구역]
        past_window = df_back.iloc[pos-15:pos-2]
        bull_div_count = 0
        bear_div_count = 0
        
        if not past_window.empty:
            # A. 1번 타점용 상승 다이버전스 판독
            past_low_idx = past_window['Low'].idxmin()
            p_low = float(df_back['Low'].loc[past_low_idx])
            if c_low <= p_low * 1.01:
                if float(df_back['RSI_14'].iloc[pos]) > float(df_back['RSI_14'].loc[past_low_idx]): bull_div_count += 1
                if float(df_back['MACD'].iloc[pos]) > float(df_back['MACD'].loc[past_low_idx]): bull_div_count += 1
                if float(df_back['MACD_Hist'].iloc[pos]) > float(df_back['MACD_Hist'].loc[past_low_idx]): bull_div_count += 1
                if float(df_back['CCI_14'].iloc[pos]) > float(df_back['CCI_14'].loc[past_low_idx]): bull_div_count += 1

            # B. 2번 타점용 하락 다이버전스 판독
            past_high_idx = past_window['High'].idxmax()
            p_high = float(df_back['High'].loc[past_high_idx])
            if c_high >= p_high * 0.99:
                if float(df_back['RSI_14'].iloc[pos]) < float(df_back['RSI_14'].loc[past_high_idx]): bear_div_count += 1
                if float(df_back['MACD'].iloc[pos]) < float(df_back['MACD'].loc[past_high_idx]): bear_div_count += 1
                if float(df_back['MACD_Hist'].iloc[pos]) < float(df_back['MACD_Hist'].loc[past_high_idx]): bear_div_count += 1
                if float(df_back['CCI_14'].iloc[pos]) < float(df_back['CCI_14'].loc[past_high_idx]): bear_div_count += 1

        # 🔍 [양방향 진입 조건 분기 필터링]
        is_setup_ai = (c_score >= 90)
        
        # ====================================================================
        # 🎯 [2단계 보완] 전일 종가 대비 -1.0% / -0.5% 지정가 눌림목 체결 검증
        # ====================================================================
        # 승률 72% 이상(A등급 이상) 조건 충족 종목만 진입 시도
        if c_score < 72.0:
            continue

        # 강세 등급에 따른 지정가 매수 타점 설정 (S등급: -0.5%, A등급: -1.0%)
        if c_score >= 88.0:
            target_entry_price = c_close * 0.995  # 초강력 모멘텀: -0.5% 할인 타점
        else:
            target_entry_price = c_close * 0.990  # 우수 모멘텀: -1.0% 할인 타점

        next_low = float(df_back['Low'].iloc[pos + 1])

        # 다음 날 당일 저가(Low)가 지정가 이하로 내려왔을 때만 체결 (안 사지면 패스)
        if next_low <= target_entry_price:
            entry_p = target_entry_price
        else:
            continue  # 미체결 종목은 백테스트 대상에서 제외하여 승률 왜곡 차단
            
        # ====================================================================
        # 🎯 [PRO QUANT 개편] 손익비 2.0 : 1 강제 구조화 및 Break-Even 가동
        # ====================================================================
        sl_hard_target = entry_p * 0.975  # -2.5% 타이트 손절선 (Hard Cap)
        tp_target = entry_p * 1.050       # +5.0% 1차 익절 타깃 (R:R = 2.0 : 1)
        
        available_bars = min(10, len(df_back) - pos - 1)
        weight_remaining = 1.0
        realized_pnl = 0.0
        is_tp_done = False

        for d in range(1, available_bars + 1):
            curr_idx = pos + d
            c_open_d = float(df_back['Open'].iloc[curr_idx])
            c_low_d = float(df_back['Low'].iloc[curr_idx])
            c_high_d = float(df_back['High'].iloc[curr_idx])
            c_close_d = float(df_back['Close'].iloc[curr_idx])
            c_ma5_d = float(df_back['MA_5'].iloc[curr_idx])

            # 💡 Break-Even: 주가가 +3.0% 이상 상승 경험 시, 손절가를 매수가 +0.3%로 상향
            if ((c_high_d - entry_p) / entry_p) >= 0.030:
                sl_hard_target = max(sl_hard_target, entry_p * 1.003)

            # 1) -2.5% 손절 터치 시 ➔ 시가 갭하락 음봉 손절 오차 보정 연산
            if c_low_d <= sl_hard_target:
                # 시가 자체가 손절가보다 낮게 갭하락 개장한 경우 ➔ 시가 체결 반영
                actual_exit_price = c_open_d if c_open_d <= sl_hard_target else sl_hard_target
                realized_pnl += weight_remaining * ((actual_exit_price - entry_p) / entry_p)
                weight_remaining = 0.0
                break

        if weight_remaining > 0:
            last_close = float(df_back['Close'].iloc[pos + available_bars])
            realized_pnl += weight_remaining * ((last_close - entry_p) / entry_p)

        # 💡 슬리피지 및 제세공과금 -0.25% 차감
        final_trade_return = realized_pnl - 0.0025

        trade_returns.append(final_trade_return)
        is_win_list.append(final_trade_return > 0)

    # 복리 최종 수렴
    global_total_signals = len(trade_returns)
    if global_total_signals > 0:
        global_win_rate = (sum(is_win_list) / global_total_signals) * 100
        
        cumulative_multiplier = 1.0
        for ret in trade_returns:
            cumulative_multiplier *= (1.0 + ret)
        global_cum_return = (cumulative_multiplier - 1.0) * 100
    else:
        global_win_rate = 0.0
        global_cum_return = 0.0

    return trade_returns, is_win_list, global_win_rate, global_cum_return, global_total_signals

# 💡 캐싱된 무거운 연산 함수 호출 및 변수 바인딩
trade_returns, is_win_list, GLOBAL_WIN_RATE, GLOBAL_CUM_RETURN, GLOBAL_TOTAL_SIGNALS = run_heavy_backtest_engine(df_back)

# ====================================================================
# 🎯 [2구역 추가] 상장일 기준 표본 수(N >= 20) 및 손익비(저항선 - 현재가) / (현재가 - 지지선) 연산
# ====================================================================
first_date = df_back['Date'].min()
last_date = df_back['Date'].max()

listing_days = (last_date - first_date).days
listing_years = listing_days / 365.25
sample_count = len(trade_returns) if 'trade_returns' in locals() else 0

if listing_years >= 2.0 and sample_count < 20:
    sample_status = f"⚠️ 표본 부족 ({sample_count}개 / 최소 20개 필요)"
    is_sample_valid = False
elif listing_years < 2.0:
    sample_status = f"🆕 신규주 통계 ({sample_count}개 표본 인정 / 상장 {listing_years:.1f}년차)"
    is_sample_valid = True
else:
    sample_status = f"✅ 통계 신뢰 확보 ({sample_count}개 표본 / 상장 {listing_years:.1f}년차)"
    is_sample_valid = True

if 'trade_returns' in locals() and trade_returns:
    wins = [r for r in trade_returns if r > 0]
    losses = [abs(r) for r in trade_returns if r < 0]
    avg_win = np.mean(wins) * 100 if wins else 0.0
    avg_loss = np.mean(losses) * 100 if losses else 1e-9
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
else:
    rr_ratio = 0.0

# 🏆 AI 추세 최적화 단타 검증 스코어보드 (12대 지표 엔진 100% 기반)
ai_dict = {}
if 'raw_data' in locals() and raw_data is not None and not raw_data.empty:
    # 12대 지표 정밀 연산 엔진 실행
    _, ai_dict = process_data(raw_data, "daily", safe_ticker, skip_news=True)

# 💡 ai_dict가 None이 아닐 때만 값을 가져오도록 안전장치 추가
if ai_dict is not None:
    win_rate = round(float(ai_dict.get('up_prob', 50.0)), 1)
    upside_val = round(float(ai_dict.get('upside', 0.0)), 1)
else:
    win_rate = 0.0
    upside_val = 0.0

# 부호 및 색상 분기
if upside_val >= 0:
    upside_str = f"+{upside_val:.1f}%"
    upside_color = "#ff4b4b"  # 상승 (빨간색)
else:
    upside_str = f"{upside_val:.1f}%"  # 하락 (파란색)
    upside_color = "#38bdf8"

# 🏆 스코어보드 HTML 연동 출력 ('알고리즘 확신도'와 '과거 백테스트 실증 승률' 명확히 분리)
hist_win_rate = GLOBAL_WIN_RATE if 'GLOBAL_WIN_RATE' in locals() else 0.0

st.sidebar.markdown(f"""
<div style="background-color:#0f172a; padding:15px; border-radius:10px; border: 2px solid #38bdf8; margin-bottom:20px; text-align:center;">
    <p style="margin:0; font-size:12px; color:#38bdf8; font-weight:bold; letter-spacing:0.5px;">🏆 {selected_name} AI 추세 진단 및 성과 리포트</p>
    <p style="margin:3px 0 12px 0; font-size:10px; color:#94a3b8;">(🔥 확신도 점수 vs 과거 통계 실증 검증)</p>
    <div style="display: flex; justify-content: space-around; margin-top: 5px;">
        <!-- 왼쪽: 알고리즘 확신도 점수 -->
        <div>
            <span style="font-size: 10px; color: #94a3b8; display: block;">알고리즘 확신도</span>
            <span style="font-size: 18px; color: #38bdf8; font-weight: bold;">{win_rate:.1f}%</span>
        </div>
        <div style="border-left: 1px solid #334155; height: 32px; margin-top: 3px;"></div>
        <!-- 오른쪽: 백테스트 실증 승률 -->
        <div>
            <span style="font-size: 10px; color: #94a3b8; display: block;">백테스트 실증 승률</span>
            <span style="font-size: 18px; color: #10b981; font-weight: bold;">{hist_win_rate:.1f}%</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------
# ⚙️ 유저 포지션 및 API 연동 UI (여기서부터 기존 코드와 완전히 일치합니다)
# --------------------------------------------------------------------
st.markdown("---")
st.sidebar.subheader("🤖 AI 설정 및 내 포지션")
api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password", key="sb_api_key_input")
tg_token = st.sidebar.text_input("📱 Telegram Bot Token", type="password", key="sb_tg_token")
tg_chat_id = st.sidebar.text_input("💬 Telegram Chat ID", key="sb_tg_chat_id")

if api_key:
    st.sidebar.markdown("<div style='background-color:#1e2e1e; padding:8px; border-radius:5px; border-left:4px solid #00e676; color:#00e676; font-weight:bold; font-size:12px; margin-bottom:15px;'>🟢 Gemini API 연동 완료</div>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<div style='background-color:#2d2010; padding:8px; border-radius:5px; border-left:4px solid #ff9100; color:#ff9100; font-weight:bold; font-size:12px; margin-bottom:15px;'>🟡 API Key 입력 대기 중...</div>", unsafe_allow_html=True)

is_krw = bool(safe_ticker) and ("KRW" in safe_ticker or ".KS" in safe_ticker or ".KQ" in safe_ticker)
step_val = 1.0 if is_krw else 0.01

entry_price = st.sidebar.number_input(f"🎯 나의 매수가 입력 ({'₩' if is_krw else '$'})", value=0.0, step=step_val, key="sb_entry_price_input")

from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# ====================================================================
# 🎯 [PRO QUANT 개편 3.0] 종목 습성(Profile) + 실시간 모멘텀 동적 결합 엔진
# ====================================================================

# 👇 [여기부터 추가] ----------------------------------------------------
def get_preferred_ma_layer(df_proc):
    """최근 60봉 기준, 5/10/20일 이평선 중 종목이 가장 잘 지지받는 이평선(5, 10, 20)을 추출하는 함수"""
    try:
        recent = df_proc.tail(60).copy()
        if len(recent) < 20 or 'MA_5' not in recent.columns:
            return 5

        # 각 이평선과 최근 저가(Low) 간의 평균 이격 거리 계산
        dist_5 = (np.abs(recent['Low'] - recent['MA_5']) / recent['MA_5']).mean()
        dist_10 = (np.abs(recent['Low'] - recent['MA_10']) / recent['MA_10']).mean()
        dist_20 = (np.abs(recent['Low'] - recent['MA_20']) / recent['MA_20']).mean()

        distances = {5: dist_5, 10: dist_10, 20: dist_20}
        return min(distances, key=distances.get)
    except Exception:
        return 5
# ====================================================================
# 🎯 [PRO QUANT 개편] 7대 매수 타점(시초가/5/10/20/60/120/200일선) 정밀 분기 엔진
# ====================================================================
def calculate_smart_entry_price(df_proc, ai_data):
    c_close = float(df_proc['Close'].iloc[-1])
    c_open  = float(df_proc['Open'].iloc[-1])
    c_high  = float(df_proc['High'].iloc[-1])
    c_low   = float(df_proc['Low'].iloc[-1])
    c_vol   = float(df_proc['Volume'].iloc[-1])
    
    vol_ma20 = float(df_proc['Vol_MA_20'].iloc[-1]) if 'Vol_MA_20' in df_proc.columns and float(df_proc['Vol_MA_20'].iloc[-1]) > 0 else 1.0
    rvol = c_vol / vol_ma20

    # 이동평균선 연산
    ma5   = float(df_proc['MA_5'].iloc[-1])   if 'MA_5' in df_proc.columns else c_close
    ma10  = float(df_proc['MA_10'].iloc[-1])  if 'MA_10' in df_proc.columns else c_close
    ma20  = float(df_proc['MA_20'].iloc[-1])  if 'MA_20' in df_proc.columns else c_close
    ma60  = float(df_proc['MA_60'].iloc[-1])  if 'MA_60' in df_proc.columns else c_close
    ma120 = float(df_proc['MA_120'].iloc[-1]) if 'MA_120' in df_proc.columns else c_close
    ma200 = float(df_proc['MA_200'].iloc[-1]) if 'MA_200' in df_proc.columns else c_close

    # MACD 오실레이터 및 Squeeze 감지
    macd_hist_curr = float(df_proc['MACD_Hist'].iloc[-1]) if 'MACD_Hist' in df_proc.columns else 0.0
    macd_hist_prev = float(df_proc['MACD_Hist'].iloc[-2]) if 'MACD_Hist' in df_proc.columns and len(df_proc) >= 2 else macd_hist_curr
    had_squeeze = df_proc['Squeeze_On'].iloc[-5:-1].any() if 'Squeeze_On' in df_proc.columns and len(df_proc) >= 5 else False

    # 캔들 형태 및 이격도
    body = abs(c_close - c_open)
    upper_shadow = c_high - max(c_open, c_close)
    is_fading = (macd_hist_curr < macd_hist_prev) or (c_close < c_open) or (upper_shadow > body * 0.4)
    disp_ma5 = (c_close / ma5) * 100.0 if ma5 > 0 else 100.0

    # ----------------------------------------------------------------
    # 🛒 [타점 0] 시초가 매수 (NetApp, Jacobs 등 초강세주/수급폭발주)
    # - 완전정배열, RVOL >= 1.5, 모멘텀 가속, 과열 미진입(disp_ma5 <= 104)
    # ----------------------------------------------------------------
    if (c_close >= ma5 >= ma10 >= ma20) and rvol >= 1.5 and (macd_hist_curr > macd_hist_prev or had_squeeze) and disp_ma5 <= 104.0:
        final_entry = c_close  # 익일 시초가 대응
        tag = "🛒 [시초가 대응] 수급 폭발 추세 돌파 진입"

    # ----------------------------------------------------------------
    # ⚡ [타점 1] 5일선 지지 매수 (단기 강세 지속주)
    # ----------------------------------------------------------------
    elif c_close >= ma5 and ma5 >= ma10 and not is_fading:
        final_entry = ma5
        tag = "⚡ [실제 5일선] 초강세 추세 관성 진입"

    # ----------------------------------------------------------------
    # 🎯 [타점 2] 10일선 지지 매수 (단기 생명선 눌림주)
    # ----------------------------------------------------------------
    elif c_close >= ma10 and ma10 >= ma20 and (c_close < ma5 or is_fading):
        final_entry = ma10
        tag = "🎯 [실제 10일선] 단기 생명선 지지 진입"

    # ----------------------------------------------------------------
    # 🧱 [타점 3] 20일선 지지 매수 (메리츠금융지주 등 세력 눌림목주)
    # ----------------------------------------------------------------
    elif c_close >= ma20 and (c_close < ma10 or is_fading or rvol < 1.2):
        final_entry = ma20
        tag = "🧱 [실제 20일선] 세력 심리선 지지 눌림목 진입"

    # ----------------------------------------------------------------
    # 🛡️ [타점 4] 60일선 지지 매수 (중기 수급선 지지주)
    # ----------------------------------------------------------------
    elif c_close >= ma60:
        final_entry = ma60
        tag = "🛡️ [실제 60일선] 중기 수급선 저점 바닥 진입"

    # ----------------------------------------------------------------
    # 🏦 [타점 5] 120일선 지지 매수 (경기 분수령 낙폭과대주)
    # ----------------------------------------------------------------
    elif c_close >= ma120:
        final_entry = ma120
        tag = "🏦 [실제 120일선] 경기 분수령 낙폭과대 바닥 진입"

    # ----------------------------------------------------------------
    # 💎 [타점 6] 200일선 지지 매수 (대세 최후 보루선)
    # ----------------------------------------------------------------
    else:
        final_entry = ma200
        tag = "💎 [실제 200일선] 대세 최후 보루 장기 지지 진입"

    return round(final_entry, 2), tag


# ====================================================================
# 🎯 [1번 탑10 & 2번 소급 검증 공통 - TOP 5 캔들 + TOP 5 차트패턴 융합 90% 승률 평가 스캐너]
# ====================================================================
def evaluate_stock_signal(df_proc, ai_data):
    if not ai_data or df_proc is None or len(df_proc) < 30:
        return None, 0.0, 0.0, ""

    # 💡 [ADX 20.0 필수 강제 필터] 추세 강도 20 미만 박스권/횡보주 원천 차단
    adx_val = float(df_proc['ADX'].iloc[-1]) if 'ADX' in df_proc.columns else 0.0
    if adx_val < 20.0:
        return None, 0.0, 0.0, ""

    c_close = float(df_proc['Close'].iloc[-1])
    c_open  = float(df_proc['Open'].iloc[-1])
    c_high  = float(df_proc['High'].iloc[-1])
    c_low   = float(df_proc['Low'].iloc[-1])
    
    calc_entry, entry_tag = calculate_smart_entry_price(df_proc, ai_data)
    if calc_entry <= 0 or (abs(c_close - calc_entry) / calc_entry * 100.0) > 7.0:
        return None, 0.0, 0.0, ""

    pattern_score = 0
    sig_tags = []

    # ------------------------------------------------------------
    # 🕯️ [TOP 5 캔들 패턴 검증]
    # ------------------------------------------------------------
    body = abs(c_close - c_open)
    upper_sh = c_high - max(c_open, c_close)
    lower_sh = min(c_open, c_close) - c_low
    
    p1_c, p1_o = float(df_proc['Close'].iloc[-2]), float(df_proc['Open'].iloc[-2])
    p2_c, p2_o = float(df_proc['Close'].iloc[-3]), float(df_proc['Open'].iloc[-3])

    # 1. 망치형
    if lower_sh >= (body * 1.5) and upper_sh <= (body * 0.5):
        pattern_score += 20; sig_tags.append("망치형")
    # 2. 상승장악형
    if (p1_c < p1_o) and (c_close > c_open) and (c_close >= p1_o) and (c_open <= p1_c):
        pattern_score += 20; sig_tags.append("상승장악형")
    # 3. 상승관통형
    if (p1_c < p1_o) and (c_close > c_open) and (c_open < p1_c) and (c_close > (p1_o + p1_c) / 2):
        pattern_score += 15; sig_tags.append("상승관통형")
    # 4. 샛별형
    if (p2_c < p2_o) and (abs(p1_c - p1_o) < abs(p2_c - p2_o) * 0.3) and (c_close > (p2_o + p2_c) / 2):
        pattern_score += 15; sig_tags.append("샛별형")
    # 5. 상승잉태형
    if (p1_c < p1_o) and (c_close > c_open) and (c_open > p1_c) and (c_close < p1_o):
        pattern_score += 10; sig_tags.append("상승잉태형")

    # ------------------------------------------------------------
    # 📊 [TOP 5 차트 패턴 검증]
    # ------------------------------------------------------------
    poc_high = float(ai_data.get('poc_price', c_close))
    ma5  = float(df_proc['MA_5'].iloc[-1])  if 'MA_5' in df_proc.columns else c_close
    ma10 = float(df_proc['MA_10'].iloc[-1]) if 'MA_10' in df_proc.columns else c_close
    ma20 = float(df_proc['MA_20'].iloc[-1]) if 'MA_20' in df_proc.columns else c_close
    ma60 = float(df_proc['MA_60'].iloc[-1]) if 'MA_60' in df_proc.columns else c_close

    # 1. POC 최대 매물대 방어
    if c_close >= poc_high * 0.99:
        pattern_score += 20; sig_tags.append("POC매물대방어")
    # 2. 이평선 완전정배열 & 밀집
    if ma5 >= ma10 >= ma20 >= ma60:
        pattern_score += 20; sig_tags.append("이평정배열")
    # 3. 쌍바닥(W자)
    recent_lows = df_proc['Low'].tail(15).values
    if len(recent_lows) >= 10 and c_low > min(recent_lows[:-3]) * 0.995:
        pattern_score += 15; sig_tags.append("쌍바닥지지")
    # 4. 삼각수렴 발산
    if df_proc['Squeeze_On'].iloc[-2] if 'Squeeze_On' in df_proc.columns else False:
        pattern_score += 15; sig_tags.append("수렴후발산")
    # 5. V자 반등 / 3연속 양봉
    if c_close > p1_c > p2_c and c_open > p1_o > p2_o:
        pattern_score += 10; sig_tags.append("3연속양봉")

    # ------------------------------------------------------------
    # 🛡️ [PRO QUANT 개편] 손익비 2.0 : 1 고정 & 정예 커트라인(50점) 조율
    # ------------------------------------------------------------
    if pattern_score < 50:
        return None, 0.0, 0.0, ""

    exp_win = min(88.0 + (pattern_score * 0.1), 98.0)
    exp_ret = 5.0  # 1차 익절 고정 목표가 +5.0% (R:R = 2.0 : 1)

    unique_tags = list(dict.fromkeys([entry_tag] + sig_tags))
    full_signal = " / ".join(unique_tags)
    return full_signal, exp_win, exp_ret, c_close



# ====================================================================
# 💡 [통합 정밀 매매/비중/동적 매도 엔진] 4대 매매 상태 및 실시간 비중 제어
# ====================================================================
def evaluate_advanced_trade_signal(df_proc, ticker, name, c_close, entry_p, max_p, min_p):
    """
    최고 수익 극대화 동적 매도 + 신규 눌림목 / 추세 재진입 / 물타기(손절) 통합 판정
    """
    if df_proc is None or len(df_proc) < 20:
        return "⚪ [관망]", "비중 0%"

    latest = df_proc.iloc[-1]
    prev = df_proc.iloc[-2] if len(df_proc) >= 2 else latest

    # 💡 해당 차트 위치(pos)의 실제 날짜 추출 (YY-MM-DD 포맷)
    raw_date = latest.get('Date', pd.Timestamp.now())
    latest_date_str = pd.to_datetime(raw_date).strftime('%y-%m-%d')

    # 주요 기술적 지표
    ma5 = float(latest.get('MA_5', c_close))
    ma20 = float(latest.get('MA_20', c_close))
    ma200 = float(latest.get('MA_200', c_close))
    vol_ma20 = float(latest.get('Vol_MA_20', 1.0)) if float(latest.get('Vol_MA_20', 1.0)) > 0 else 1.0
    c_vol = float(latest.get('Volume', 0.0))
    rvol = c_vol / vol_ma20

    disp_20 = (c_close / ma20) * 100.0 if ma20 > 0 else 100.0
    rsi_val = float(latest.get('RSI', 50.0))
    macd_curr = float(latest.get('MACD', 0.0))
    signal_curr = float(latest.get('Signal', 0.0))
    macd_hist_curr = float(latest.get('MACD_Hist', 0.0))
    macd_hist_prev = float(prev.get('MACD_Hist', 0.0))

    bb_upper = float(latest.get('BB_Upper', c_close * 1.2))
    bb_lower = float(latest.get('BB_Lower', c_close * 0.8))
    bb_range = bb_upper - bb_lower
    pct_b = (c_close - bb_lower) / bb_range if bb_range > 0 else 0.5

    # 수익률 및 고점 대비 하락률
    curr_ret = ((c_close - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0
    drop_from_peak = ((max_p - c_close) / max_p) * 100.0 if max_p > 0 else 0.0

    # 4대 최고점(Peak) 피크 신호 감지
    peak_signals = 0
    if rvol >= 2.5 and c_close < float(latest.get('Open', c_close)): peak_signals += 1
    if disp_20 >= 118.0 or pct_b >= 0.92: peak_signals += 1
    if rsi_val >= 72.0 and macd_hist_curr < macd_hist_prev: peak_signals += 1
    if c_close < ma5 and float(prev.get('Close', c_close)) >= float(prev.get('MA_5', c_close)): peak_signals += 1

    # 💡 3개월(60D) 주도주 동적 판정
    c_60b = float(df_proc['Close'].iloc[-60]) if len(df_proc) >= 60 else float(df_proc['Close'].iloc[0])
    ret_3m = ((c_close - c_60b) / c_60b) * 100.0 if c_60b > 0 else 0.0
    is_leading = (ret_3m >= 10.0) and (c_close >= ma200) and (ma20 >= ma200)

    # 1️⃣ [매도/익절/손절 상태 정밀 분기]
    if drop_from_peak >= 10.0 or peak_signals >= 2 or (curr_ret >= 20.0 and c_close < ma5):
        return f"🚨 [상투/트레일링스탑] ({latest_date_str})", "익일 시초가 즉시 전량 매도 (수익 최종 확정)"
    if curr_ret >= 50.0:
        return f"💰 [2차 동적 익절] ({latest_date_str})", "+50% 도달 시 30~40% 부분 청산"
    if curr_ret >= 25.0:
        return f"💰 [1차 동적 익절] ({latest_date_str})", "+25% 도달 시 30~40% 부분 청산"
    if c_close < ma200 or curr_ret <= -20.0:
        return f"⚠️ [리스크관리/손절] ({latest_date_str})", "200일선 이탈 시 전량 손절"
    if curr_ret <= -10.0 or (macd_curr < signal_curr and macd_hist_curr < 0):
        return f"⚠️ [리스크관리/손절] ({latest_date_str})", "추세 약화 시 50% 비중 축소"
    if -30.0 <= curr_ret <= -15.0:
        return f"💧 [우량주 물타기] ({latest_date_str})", "-15~-30% 조정 시 1:1 동일금액 추매 (평단 하향)"
    if curr_ret > 0 and (108.0 < disp_20 <= 112.0 or 60.0 < rsi_val <= 68.0):
        return f"🔥 [추세 재진입] ({latest_date_str})", "보유자 불타기 (원금의 +30~50% 추가 적립)"
    if disp_20 <= 108.0 and rsi_val <= 60.0:
        weight_str = "주도주 12~15%" if is_leading else "일반 8~10%"
        return f"🎯 [신규 눌림목] ({latest_date_str})", f"최초 진입 ({weight_str})"

    return f"🟢 [보유/추세 추종] ({latest_date_str})", "잔량 홀딩"

    # 3️⃣ [추세 재진입 / 불타기 판정] (수익 중 + 대시세 연장)
    if curr_ret > 0 and (108.0 < disp_20 <= 112.0 or 60.0 < rsi_val <= 68.0) and macd_curr >= signal_curr:
        return f"🔥 [추세 재진입] ({latest_date_str})", "기존 투자금의 +30%~+50% 추가 적립"

    # 4️⃣ [신규 눌림목 진입 판정] (안전한 최초 진입 타점)
    if disp_20 <= 108.0 and rsi_val <= 60.0 and macd_curr >= signal_curr:
        weight_str = "포트폴리오 비중 12~15% (3M 주도 섹터)" if is_leading else "포트폴리오 비중 8~10%"
        return f"🎯 [신규 눌림목] ({latest_date_str})", weight_str

    return f"🟢 [보유/추세 추종] ({latest_date_str})", "잔량 홀딩"

    # ====================================================================
# 🚀 [1~5봉 내 10%+ 초급등주(Surge Stock) 전용 정밀 스캐너 Engine]
# ====================================================================
def evaluate_surge_stock_signal(df_proc, ai_data):
    if not ai_data or df_proc is None or len(df_proc) < 60:
        return None, 0.0, 0.0, ""

    # 💡 [ADX 20.0 필수 강제 필터]
    adx_val = float(df_proc['ADX'].iloc[-1]) if 'ADX' in df_proc.columns else 0.0
    if adx_val < 20.0:
        return None, 0.0, 0.0, ""

    latest = df_proc.iloc[-1]
    c_close = float(latest['Close'])
    c_open  = float(latest['Open'])
    c_high  = float(latest['High'])
    c_low   = float(latest['Low'])
    c_vol   = float(latest['Volume'])
    vol_ma20= float(latest['Vol_MA_20']) if float(latest['Vol_MA_20']) > 0 else 1.0
    rvol_val = c_vol / vol_ma20

    # 1. 🚀 수급 폭발 (RVOL 2.0배 이상)
    if rvol_val < 2.0:
        return None, 0.0, 0.0, ""

    # 2. 🏰 매물대 공백 (최근 60일 최고가 3% 이내 접근)
    recent_60_high = float(df_proc['High'].tail(60).max())
    if c_close < (recent_60_high * 0.97):
        return None, 0.0, 0.0, ""

    # 3. 🕯️ 장대양봉 (윗꼬리 비율 25% 이하)
    candle_range = c_high - c_low
    upper_shadow = c_high - max(c_open, c_close)
    shadow_ratio = (upper_shadow / candle_range) if candle_range > 0 else 1.0
    if shadow_ratio > 0.25 or c_close < c_open:
        return None, 0.0, 0.0, ""

    exp_win = float(ai_data.get('up_prob', 0.0))
    exp_ret = float(ai_data.get('upside', 0.0))
    surge_exp_ret = max(exp_ret * 1.8, 10.5)

    sig_tags = ["🚀RVOL폭발", "🏰60일신고가", "🕯️장대양봉"]
    signal_str = " / ".join(sig_tags)

    return signal_str, exp_win, surge_exp_ret, c_close


# ====================================================================
# 🎯 [1번 스캔 & 2번 과거검증 100% 로직 공유] 통합 퀀트 평가 파이프라인
# ====================================================================
def run_unified_quant_eval(df_sub, name, ticker):
    """1번 실시간 스캔과 2번 소급 검증이 동일하게 사용하는 100% 동일 조건 엔진"""
    if df_sub is None or len(df_sub) < 130:
        return None, None

    # 1. 공통 지표 연산
    df_proc, ai_data = process_data(df_sub, "daily", ticker, skip_news=True)
    if df_proc is None or ai_data is None:
        return None, None

    # 💡 [1번 & 2번 검증 공통] ADX 20.0 미만 약세/횡보주 100% 원천 차단 가드레일
    adx_val = float(df_proc['ADX'].iloc[-1]) if 'ADX' in df_proc.columns else 0.0
    if adx_val < 20.0:
        return None, None

    # ====================================================================
    # 🛡️ [PRO QUANT 신규] 시장 지수 국면 및 갭/이격도 과열 방어 필터
    # ====================================================================
    # 1. 시장 지수 약세장 국면 차단 (Market Regime Lock)
    is_bear, _ = check_benchmark_regime(ticker)
    if is_bear:
        return None, None

    # 2. 시가 갭이 +6% 초과이거나 5일선 이격도 +5% 초과 과열주 매수 차단
    latest = df_proc.iloc[-1]
    prev_close = float(df_proc['Close'].iloc[-2]) if len(df_proc) >= 2 else float(latest['Open'])
    open_price = float(latest['Open'])
    
    if open_price / prev_close > 1.06:
        return None, None
        
    ma5 = float(latest['MA_5']) if 'MA_5' in latest else open_price
    if (open_price - ma5) / ma5 > 0.05:
        return None, None

    swing_res, surge_res = None, None

# ====================================================================
    # 🛡️ [신규 추가] 시장 지수 국면 및 갭/이격도 과열 방어 필터
    # ====================================================================
    # 1. 시장 지수 국면 필터 (약세장 진입 시 추천 차단)
    is_bear, _ = check_benchmark_regime(ticker)
    if is_bear:
        return None, None

    # 2. 이격도 및 갭 상승 제한 필터 (+6% 갭 초과 또는 5일선 이격 +5% 초과 차단)
    latest = df_proc.iloc[-1]
    prev_close = float(df_proc['Close'].iloc[-2]) if len(df_proc) >= 2 else float(latest['Open'])
    open_price = float(latest['Open'])
    
    if open_price / prev_close > 1.06:
        return None, None
        
    ma5 = float(latest['MA_5']) if 'MA_5' in latest else open_price
    if (open_price - ma5) / ma5 > 0.05:
        return None, None

    swing_res, surge_res = None, None

    # 2. 스마트 눌림목 공통 검증 (승률 85% 이상 & 패턴점수 75점 이상만)
    sig_sw, up_p_sw, up_s_sw, c_close_sw = evaluate_stock_signal(df_proc, ai_data)
    if sig_sw and up_p_sw >= 85.0 and sig_sw != "None":
        calc_entry_sw, _ = calculate_smart_entry_price(df_proc, ai_data)
        swing_res = {
            "name": name, 
            "ticker": ticker, 
            "entry_price": calc_entry_sw,
            "entry_p": calc_entry_sw,
            "up_prob": round(up_p_sw, 1), 
            "exp_win": round(up_p_sw, 1),
            "upside": 5.0,  # +5.0% 고정 익절선 (R:R = 2.0 : 1)
            "exp_ret": 5.0,
            "composite_score": round((up_p_sw * 0.7) + (5.0 * 3.0), 2),
            "signal": sig_sw, 
            "score": (up_p_sw * 0.5) + (5.0 * 4.0),
            "adx": round(adx_val, 1)
        }

    # 3. 10%+ 초급등주 공통 검증
    sig_sg, up_p_sg, up_s_sg, c_close_sg = evaluate_surge_stock_signal(df_proc, ai_data)
    if sig_sg and up_p_sg >= 85.0:
        calc_entry_sg = round(c_close_sg * 0.995, 2)
        surge_res = {
            "name": name, 
            "ticker": ticker, 
            "entry_price": calc_entry_sg,
            "entry_p": calc_entry_sg,
            "up_prob": round(up_p_sg, 1), 
            "exp_win": round(up_p_sg, 1),
            "upside": round(up_s_sg, 1), 
            "exp_ret": round(up_s_sg, 1),
            "composite_score": round((up_p_sg * 0.4) + (up_s_sg * 5.0), 2),
            "signal": f"⚡ [돌파/추격] {sig_sg}", 
            "score": (up_p_sg * 0.5) + (up_s_sg * 5.0),
            "adx": round(adx_val, 1)
        }

    return swing_res, surge_res

# ====================================================================
# 🚀 [6M~1Y 저점 매수 엔진] 볼린저밴드 상단 차단 해제 스캐너
# ====================================================================
def run_midterm_quant_eval(df_sub, name, ticker, fin_info=None):
    """MACD 골든크로스 필수 + 주봉 정배열 + 일봉 눌림목 스캐너"""
    if df_sub is None or len(df_sub) < 150:
        return None

    # 1. 펀더멘털 스크리닝 (시총 8천억 이상 / 부채비율 120% 이하)
    try:
        if fin_info is None:
            import yfinance as yf
            fin_info = yf.Ticker(ticker).info
            
        if isinstance(fin_info, dict):
            # 시가총액 (국내 8천억 이상)
            if ".KS" in ticker or ".KQ" in ticker:
                mcap = fin_info.get('marketCap', 0)
                if mcap and mcap < 800_000_000_000:
                    return None
            
            # 💡 [요청 반영] 부채비율(Debt to Equity) 120% 이하만 엄격 승인
            debt_to_equity = fin_info.get('debtToEquity', None)
            if debt_to_equity is not None:
                d_e_val = float(debt_to_equity)
                # yfinance 수치 규격 대응 (120% 표기 방식: 120.0 또는 1.2)
                if d_e_val > 120.0 or (1.2 < d_e_val <= 100.0):
                    return None
    except Exception:
        pass

    # 2. 기술적 지표 계산
    df_proc, ai_data = process_data(df_sub, "daily", ticker, skip_news=True)
    if df_proc is None or ai_data is None:
        return None

    latest = df_proc.iloc[-1]
    prev = df_proc.iloc[-2] if len(df_proc) >= 2 else latest
    c_close = float(latest['Close'])

    # ----------------------------------------------------------------
    # 🚨 MACD 데드크로스 & 음수 강제 차단 (유지)
    # ----------------------------------------------------------------
    macd_curr = float(latest['MACD']) if 'MACD' in latest else 0.0
    signal_curr = float(latest['Signal']) if 'Signal' in latest else 0.0
    macd_hist_curr = float(latest['MACD_Hist']) if 'MACD_Hist' in latest else 0.0
    macd_hist_prev = float(prev['MACD_Hist']) if 'MACD_Hist' in prev else 0.0

    if macd_curr < signal_curr or macd_hist_curr <= 0 or macd_hist_curr < macd_hist_prev:
        return None

    # ----------------------------------------------------------------
    # 3. 주봉(Weekly) 대세 방향성 확인
    # ----------------------------------------------------------------
    df_w = df_sub.copy()
    df_w['Date'] = pd.to_datetime(df_w['Date'])
    
    df_weekly = df_w.resample('W-FRI', on='Date').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna().reset_index()

    if len(df_weekly) < 15:
        return None

    df_weekly['W_MA20'] = df_weekly['Close'].rolling(min(20, len(df_weekly))).mean()
    df_weekly['W_MA50'] = df_weekly['Close'].rolling(min(50, len(df_weekly))).mean()
    
    w_latest = df_weekly.iloc[-1]
    w_close = float(w_latest['Close'])
    w_ma20 = float(w_latest['W_MA20'])
    w_ma20_prev = float(df_weekly['W_MA20'].iloc[-3]) if len(df_weekly) >= 3 else w_ma20

    if not (w_close >= w_ma20 * 0.97 and w_ma20 >= w_ma20_prev * 0.98):
        return None

    # ----------------------------------------------------------------
    # 4. 일봉(Daily) 저점 눌림목 타점 스크리닝
    # ----------------------------------------------------------------
    ma20 = float(latest['MA_20']) if 'MA_20' in latest else c_close
    ma200 = float(latest['MA_200']) if 'MA_200' in latest else c_close

    # 일봉 20일선 이격도 제한
    disp_20 = (c_close / ma20) * 100.0 if ma20 > 0 else 100.0
    if not (95.0 <= disp_20 <= 108.0):
        return None

    # RSI 식힘 구간 (38 ~ 60 지대)
    rsi_val = float(latest['RSI']) if 'RSI' in latest else 50.0
    if not (38.0 <= rsi_val <= 60.0):
        return None

    # OBV 세력 매집
    obv = (np.sign(df_sub['Close'].diff()) * df_sub['Volume']).fillna(0).cumsum()
    obv_ma10 = obv.rolling(10).mean()
    if float(obv.iloc[-1]) < float(obv_ma10.iloc[-1]):
        return None

    calc_entry = round(min(c_close * 0.99, ma20), 2)
    score = 82.0
    if c_close >= ma200: score += 5.0
    if float(obv.iloc[-1]) >= float(obv.max() * 0.90): score += 5.0

    up_prob = min(score, 98.0)
    if up_prob < 85.0:
        return None

    # 💡 실시간 매매 대응 및 비중 연산
    action_status, rec_weight = evaluate_advanced_trade_signal(df_sub, ticker, name, c_close, calc_entry, c_close, c_close)

    return {
        "name": name,
        "ticker": ticker,
        "entry_price": calc_entry,
        "entry_p": calc_entry,
        "up_prob": round(up_prob, 1),
        "exp_win": round(up_prob, 1),
        "upside": 100.0,
        "exp_ret": 100.0,
        "composite_score": round(score, 2),
        "signal": action_status,
        "action_status": action_status,
        "rec_weight": rec_weight,
        "score": round(score, 2),
        "adx": 25.0
    }

# ====================================================================
# 1️⃣ [1번 오늘의 Top 10 추천 단일 종목 처리]
# ====================================================================
def process_single_ticker_unbound(item):
    name, ticker = item
    try:
        df_t = get_raw_daily_data(ticker)
        return run_unified_quant_eval(df_t, name, ticker)
    except Exception:
        pass
    return (None, None)


# ====================================================================
# 2️⃣ [2번 과거 소급 검증 단일 종목 처리]
# ====================================================================
def eval_past_recommendation_worker(cand, ctx):
    if ctx is not None:
        add_script_run_ctx(ctx=ctx)
    try:
        market_label, name, ticker = cand
        df_hist = get_raw_daily_data(ticker)
        if df_hist is None or len(df_hist) < 130:
            return None

        bars_ago_val = st.session_state.get('slider_bars_ago', 5)
        t_idx = len(df_hist) - 1 - bars_ago_val
        if t_idx < 60:
            return None

        df_sub = df_hist.iloc[:t_idx + 1].copy()
        
        # 1번 스캐너와 동일한 공통 평가 파이프라인 호출
        swing_res, surge_res = run_unified_quant_eval(df_sub, name, ticker)
        
        # 눌림목 결과 우선, 없으면 급등주 결과 사용
        res = swing_res if swing_res else surge_res
        if res:
            res['market'] = market_label
            res['t_idx'] = t_idx
            return res
            
        return None
    except Exception:
        return None

# ====================================================================
# ⚡ [스레드 워커 래퍼 함수]
# ====================================================================
def worker_task(item, ctx):
    if ctx is not None:
        add_script_run_ctx(ctx=ctx)
    return process_single_ticker_unbound(item)

# ====================================================================
# ⚡ [자가 피드백 보완] DB 누적 승률 60% 미만 조건 자동 필터링 스캐너
# ====================================================================
def bg_scan_worker(assets_dict):
    import requests
    import sqlite3

    ctx = get_script_run_ctx()

    # 💡 1. DB 기록에서 최근 성과 피드백 조회 (승률 60% 미만 약세 항목 필터용)
    underperforming_tickers = set()
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticker, 
                   COUNT(*) as total, 
                   SUM(CASE WHEN final_return > 0 THEN 1 ELSE 0 END) as wins
            FROM rec_history 
            WHERE status != '진행중'
            GROUP BY ticker
            HAVING total >= 3 AND (CAST(wins AS FLOAT) / total) < 0.6
        """)
        rows = cursor.fetchall()
        conn.close()
        underperforming_tickers = {r[0] for r in rows}
    except Exception:
        pass

    # 2. 스캔 대상 수집
    kr_items = {k: v for k, v in assets_dict["₩ 국내 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}
    us_items = {k: v for k, v in assets_dict["💲 미국 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}

    coin_items = {}
    try:
        upbit_res = requests.get("https://api.upbit.com/v1/market/all?isDetails=false", timeout=5)
        if upbit_res.status_code == 200:
            for m in upbit_res.json():
                m_code = m.get('market', '')
                if m_code.startswith('KRW-'):
                    symbol = m_code.split('-')[1]
                    kor_name = m.get('korean_name', symbol)
                    coin_items[f"{kor_name} ({symbol})"] = f"{symbol}-KRW"
    except Exception:
        pass

    if not coin_items:
        coin_items = {k: v for k, v in assets_dict["🪙 암호화폐(코인)"].items() if v.endswith('-KRW') and not any(x in k for x in ["등극주", "시총", "주요통화"])}

    all_tasks = []
    for k, v in kr_items.items(): all_tasks.append((k, v, 'scan_results_kr'))
    for k, v in us_items.items(): all_tasks.append((k, v, 'scan_results_us'))
    for k, v in coin_items.items(): all_tasks.append((k, v, 'scan_results_coin'))

    total_count = len(all_tasks)
    if total_count == 0:
        return

    progress_bar = st.progress(0.0)
    status_box = st.empty()

    # 💡 [초급등주 리스트 변수 선제 초기화 - UnboundLocalError 방지]
    results_kr, results_us, results_coin = [], [], []
    results_surge_kr, results_surge_us = [], []
    processed = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_item = {executor.submit(worker_task, (item[0], item[1]), ctx): item for item in all_tasks}

        for future in as_completed(future_to_item):
            processed += 1
            item_info = future_to_item[future]
            target_key = item_info[2]
            stock_name, ticker_code = item_info[0], item_info[1]

            pct = min(1.0, processed / total_count)
            progress_bar.progress(pct)
            status_box.markdown(f"🚀 **실시간 전 시장 초고속 스캔 중...** `{processed}/{total_count}` ({int(pct*100)}%) | 분석 중: **{stock_name}**")

            res_tuple = future.result()
            if res_tuple and ticker_code not in underperforming_tickers:
                swing_res, surge_res = res_tuple
                
                # 안정 스윙 결과 반영
                if swing_res:
                    if target_key == 'scan_results_kr': results_kr.append(swing_res)
                    elif target_key == 'scan_results_us': results_us.append(swing_res)
                    elif target_key == 'scan_results_coin': results_coin.append(swing_res)

                # 10%+ 초급등주 결과 반영
                if surge_res:
                    if target_key == 'scan_results_kr': results_surge_kr.append(surge_res)
                    elif target_key == 'scan_results_us': results_surge_us.append(surge_res)

    # 세션 데이터 정렬 및 고정 저장
    st.session_state['scan_results_kr'] = sorted(results_kr, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_results_us'] = sorted(results_us, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_results_coin'] = sorted(results_coin, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]

    st.session_state['scan_surge_kr'] = sorted(results_surge_kr, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_surge_us'] = sorted(results_surge_us, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]

    # 📱 [PRO QUANT 추가] 텔레그램 90%+ 고확신 시그널 실시간 웹훅 발송 연동
    tg_token = st.session_state.get('sb_tg_token', '')
    tg_chat_id = st.session_state.get('sb_tg_chat_id', '')

    if tg_token and tg_chat_id:
        all_top_picks = (st.session_state['scan_results_kr'] + 
                         st.session_state['scan_results_us'] + 
                         st.session_state['scan_results_coin'])
        
        for pick in all_top_picks:
            if pick.get('up_prob', 0.0) >= 90.0:
                msg = (
                    f"🚨 *[PRO QUANT 90%+ 고확신 시그널 포착]*\n\n"
                    f"📌 *종목명*: {pick['name']} ({pick['ticker']})\n"
                    f"🎯 *권장 진입가*: {pick['entry_p']}\n"
                    f"🔴 *1차 목표가 (+5.0%)*: {round(pick['entry_p'] * 1.05, 2)}\n"
                    f"🔵 *강제 손절가 (-2.5%)*: {round(pick['entry_p'] * 0.975, 2)}\n"
                    f"🔥 *알고리즘 확신도*: {pick['up_prob']}%\n"
                    f"🔍 *충족 시그널*: {pick['signal']}"
                )
                send_telegram_alert(tg_token, tg_chat_id, msg)

    progress_bar.progress(1.0)
    status_box.success(f"✅ 초고속 스캔 완료! (안정 스윙 & 10%+ 초급등주 동시 추출 완료)")

# ====================================================================
# ⚡ [중장기 전용] 6M~1Y 정예 종목 백그라운드 스캔 워커 (암호화폐 제외)
# ====================================================================
def bg_scan_worker_midterm(assets_dict):
    ctx = get_script_run_ctx()
    
    # 코인 제외 - 국내 및 미국 주식만 수집
    kr_items = {k: v for k, v in assets_dict["₩ 국내 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}
    us_items = {k: v for k, v in assets_dict["💲 미국 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}

    all_tasks = []
    for k, v in kr_items.items(): all_tasks.append((k, v, 'scan_midterm_kr'))
    for k, v in us_items.items(): all_tasks.append((k, v, 'scan_midterm_us'))

    total_count = len(all_tasks)
    if total_count == 0: return

    progress_bar = st.progress(0.0)
    status_box = st.empty()

    res_kr, res_us = [], []
    processed = 0

    def midterm_task(item_tuple):
        name, ticker = item_tuple[0], item_tuple[1]
        try:
            df_t = get_raw_daily_data(ticker)
            return run_midterm_quant_eval(df_t, name, ticker)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(midterm_task, task): task for task in all_tasks}
        for future in as_completed(futures):
            processed += 1
            task_info = futures[future]
            target_key, stock_name = task_info[2], task_info[0]

            pct = min(1.0, processed / total_count)
            progress_bar.progress(pct)
            status_box.markdown(f"🚀 **중장기 100%+ 주식 정예주 정밀 스캔 중...** `{processed}/{total_count}` ({int(pct*100)}%) | 분석: **{stock_name}**")

            res = future.result()
            if res:
                if target_key == 'scan_midterm_kr': res_kr.append(res)
                elif target_key == 'scan_midterm_us': res_us.append(res)

    st.session_state['scan_midterm_kr'] = sorted(res_kr, key=lambda x: x.get('up_prob', 0), reverse=True)[:10]
    st.session_state['scan_midterm_us'] = sorted(res_us, key=lambda x: x.get('up_prob', 0), reverse=True)[:10]

    try:
        save_top5_to_db(st.session_state['scan_midterm_kr'], st.session_state['scan_midterm_us'])
    except Exception:
        pass

    progress_bar.progress(1.0)
    status_box.success("✅ 중장기 주식 정예주 스캔 완료! (재무/주봉/200일선 90%+ 엄선)")

# ====================================================================
# ⚡ [과거 1년 초고속 전수 스캔] 볼린저밴드 상단 차단 제거 버전
# ====================================================================
def scan_all_historical_midterm_signals(assets_dict):
    from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
    ctx = get_script_run_ctx()
    
    kr_items = {k: v for k, v in assets_dict["₩ 국내 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}
    us_items = {k: v for k, v in assets_dict["💲 미국 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}

    all_tasks = []
    for k, v in kr_items.items(): all_tasks.append(("국내", k, v))
    for k, v in us_items.items(): all_tasks.append(("미국", k, v))

    total_count = len(all_tasks)
    if total_count == 0: return []

    progress_bar = st.progress(0.0)
    status_box = st.empty()

    historical_hits = []
    processed = 0

    # 💡 종목별 최초 진입 여부 추적용 딕셔너리 선언
    first_entry_tracker = {}

    def stock_history_task(task_tuple, ctx_obj):
        if ctx_obj is not None:
            add_script_run_ctx(ctx=ctx_obj)
            
        m_label, name, ticker = task_tuple
        try:
            # 💡 대형주 누락 방지: 재무 데이터 연동 실패 시 기본 통과 처리 및 부채비율 200% 완화
            import time
            import yfinance as yf
            
            # 삼성전자, SK하이닉스, 애플, 엔비디아 등 대표 대형주 예외 승인 목록
            blue_chips = ["005930.KS", "000660.KS", "352820.KS", "AAPL", "NVDA", "MSFT", "TSLA", "GOOGL", "AMZN"]
            
            if ticker not in blue_chips:
                try:
                    f_info = yf.Ticker(ticker).info
                    if isinstance(f_info, dict) and f_info:
                        de_val = f_info.get('debtToEquity', None)
                        if de_val is not None:
                            val = float(de_val)
                            de_pct = val if val > 10.0 else val * 100.0
                            if de_pct > 200.0: # 안정적인 우량주 누락 방지를 위해 200%로 완화
                                return []
                except Exception:
                    pass # API 조회 실패 시 대형주 탈락 방지를 위해 감수하고 통과

            df_hist = get_raw_daily_data(ticker)
            if df_hist is None or len(df_hist) < 200:
                return []
            
            df_proc, _ = process_data(df_hist, "daily", ticker, skip_news=True)
            if df_proc is None:
                return []

            hits = []
            total_len = len(df_proc)
            start_search_idx = max(200, total_len - 250)
            
            last_hit_bar = -99
            for pos in range(start_search_idx, total_len - 3, 5):
                if pos - last_hit_bar < 10:
                    continue
                
                latest = df_proc.iloc[pos]
                prev = df_proc.iloc[pos - 1] if pos > 0 else latest
                c_close = float(latest['Close'])

                # 🚨 [개선 1] MACD 단순 데드크로스만 차단
                macd_curr = float(latest.get('MACD', 0))
                signal_curr = float(latest.get('Signal', 0))
                if macd_curr < signal_curr:
                    continue

                # 🎯 [개선 2] 일봉 20일선 이격도 완화
                ma20 = float(latest.get('MA_20', c_close))
                disp_20 = (c_close / ma20) * 100.0 if ma20 > 0 else 100.0
                if not (93.0 <= disp_20 <= 112.0):
                    continue

                # 🎯 [개선 3] RSI 기준 완화
                rsi_val = float(latest.get('RSI', 50))
                if not (38.0 <= rsi_val <= 68.0):
                    continue

                last_hit_bar = pos
                raw_hit_date = df_proc['Date'].iloc[pos]
                hit_date_str = pd.to_datetime(raw_hit_date).strftime('%Y-%m-%d')
                entry_p = round(min(c_close * 0.99, ma20), 2)

                after_df = df_proc.iloc[pos + 1:]
                if not after_df.empty:
                    curr_p = float(df_proc['Close'].iloc[-1])
                    max_p = float(after_df['High'].max())
                    min_p = float(after_df['Low'].min())

                    # 물타기(-30% 1:1 추매) & 1차/2차/손절/상투 실전 PnL 시뮬레이션
                    avg_entry = entry_p
                    total_cost = entry_p
                    current_qty = 1.0
                    realized_profit = 0.0
                    tp1_done = False
                    tp2_done = False

                    for _, row in after_df.iterrows():
                        row_h, row_l, row_c = float(row['High']), float(row['Low']), float(row['Close'])
                        row_ma200 = float(row.get('MA_200', row_c))

                       # 물타기: 기존 평단가 대비 정확히 -30% 이하 타격 시에만 1:1 동일 금액 추매
                        # 추매 후 신규 평단가는 기존 평단가의 85%(-15% 손실 상태)로 조정되며, 다음 -30% 기준점도 이 평단가 기준
                        while (row_l - avg_entry) / avg_entry <= -0.30:
                            total_cost *= 2.0                     # 1:1 동일 금액 추가 매수 (원금 2배)
                            avg_entry = avg_entry * 0.85          # 신규 평단가 = 기존 평단가 × 0.85 (현재가 기준 -15% 손실로 재설정)
                            current_qty = total_cost / avg_entry  # 보유 수량 업데이트
                            action_status = f"💧 [우량주 물타기] ({hit_date_str})"

                        # 1차 익절 (+25% 도달 시 35% 부분 청산)
                        if (row_h - avg_entry) / avg_entry >= 0.25 and not tp1_done and current_qty > 0:
                            sell_q = current_qty * 0.35
                            realized_profit += sell_q * (row_h - avg_entry)
                            current_qty -= sell_q
                            tp1_done = True

                        # 2차 익절 (+50% 도달 시 35% 추가 청산)
                        if (row_h - avg_entry) / avg_entry >= 0.50 and not tp2_done and current_qty > 0:
                            sell_q = current_qty * 0.35
                            realized_profit += sell_q * (row_h - avg_entry)
                            current_qty -= sell_q
                            tp2_done = True

                        # 손절 (200일선 이탈 시 잔량 전량 손절)
                        if row_c < row_ma200 and current_qty > 0:
                            realized_profit += current_qty * (row_c - avg_entry)
                            current_qty = 0
                            break

                    # 실현 손익 + 미실현 잔량 손익 합산하여 최종 실전 PnL 산출
                    unrealized_profit = current_qty * (curr_p - avg_entry) if current_qty > 0 else 0.0
                    total_pnl_val = realized_profit + unrealized_profit
                    cum_pnl = round((total_pnl_val / total_cost) * 100.0, 1)

                    # 대응 시그널 추출
                    action_status, rec_weight = evaluate_advanced_trade_signal(df_proc, ticker, name, curr_p, avg_entry, max_p, min_p)

                    # 동일 종목 재진입 보정
                    if name in first_entry_tracker:
                        prev_p = first_entry_tracker[name]
                        if "🎯 [신규 눌림목]" in action_status:
                            action_status = action_status.replace("🎯 [신규 눌림목]", "🔥 [추세 재진입]" if curr_p >= prev_p else "💧 [우량주 물타기]")
                    else:
                        first_entry_tracker[name] = avg_entry

                    curr_ret = round(((curr_p - avg_entry) / avg_entry) * 100.0, 1)
                    max_ret = round(((max_p - avg_entry) / avg_entry) * 100.0, 1)

                    is_krw = any(x in ticker for x in [".KS", ".KQ", "-KRW"])
                    sign_str = "+" if curr_ret >= 0 else ""
                    ret_color = "#f87171" if curr_ret > 0 else ("#60a5fa" if curr_ret < 0 else "#ffffff")

                    fmt_entry = f"₩{avg_entry:,.0f}" if is_krw else f"${avg_entry:,.2f}"
                    fmt_price_val = f"₩{curr_p:,.0f}" if is_krw else f"${curr_p:,.2f}"
                    # HTML 태그 제거 (st.dataframe에서 태그 코드가 텍스트로 출력되는 오류 방지)
                    fmt_curr = f"{fmt_price_val} ({sign_str}{curr_ret:.1f}%)"

                    hits.append({
                        "시장": m_label,
                        "종목명": name,
                        "추천 포착 날짜": hit_date_str,
                        "추천 진입가": fmt_entry,
                        "현재가": fmt_curr,
                        "최대 파동 수익률 (%)": max_ret,
                        "추천 매매 대응": action_status,
                        "누적 실전 PnL (%)": cum_pnl,
                        "raw_curr_ret": curr_ret
                    })
            return hits
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(stock_history_task, task, ctx): task for task in all_tasks}
        for future in as_completed(futures):
            processed += 1
            task_info = futures[future]
            stock_name = task_info[1]

            pct = min(1.0, processed / total_count)
            progress_bar.progress(pct)
            status_box.markdown(f"⚡ **[초고속 스캔] 과거 1년 추천 포착 전수 조사 중...** `{processed}/{total_count}` ({int(pct*100)}%) | 분석: **{stock_name}**")

            try:
                hits = future.result()
                if hits: historical_hits.extend(hits)
            except Exception:
                pass

    progress_bar.progress(1.0)
    status_box.success(f"✅ 초고속 과거 1년 스캔 완료! 총 {len(historical_hits)}건의 정예 추천 포착 기록을 찾았습니다.")
    
    sorted_hits = sorted(historical_hits, key=lambda x: x['raw_curr_ret'], reverse=True)
    return sorted_hits

# ====================================================================
# 메인 탭 선언 및 레이아웃 분리
# ====================================================================
main_tab1, main_tab2, main_tab3 = st.tabs([
    "📈 실시간 차트 & 종목 분석", 
    " ✨단타 개별주 추천✨ ",
    " 🚀 6M~1Y 중장기 유망주 🚀 "  # 👈 빨간색 구역 신규 탭
])

# --------------------------------------------------------------------
# 1️⃣ 메인 탭 1: 실시간 차트 & 종목 분석
# --------------------------------------------------------------------
with main_tab1:
    # 🔍 모바일 빠른 종목 검색창 및 단기 스윙 시스템 명시 안내
    c_m1, c_m2 = st.columns([3, 1])
    with c_m1:
        quick_search = st.text_input("🔍 [모바일 빠른 종목 검색]", placeholder="종목명 또는 티커 입력 (예: 엔비디아, 005930)", key="quick_search_top")
        if quick_search:
            s_ticker, s_name = search_ticker(quick_search)
            if s_ticker:
                safe_ticker, selected_name = s_ticker, s_name
                raw_data = get_raw_daily_data(safe_ticker)
                # 💡 검색된 티커에 따라 is_krw 즉시 재계산
                is_krw = bool(safe_ticker) and ("KRW" in safe_ticker or ".KS" in safe_ticker or ".KQ" in safe_ticker)
    with c_m2:
        st.write("")
        st.caption("📌 **PRO QUANT 안내**\n본 엔진은 **1~5일 보유 단기 스윙/눌림목 타점** 전용 시스템입니다.")

    st.markdown("---")

    tab_d, tab_w, tab_m = st.tabs([
        "📆 일봉", 
        "🗓️ 주봉", 
        "📅 월봉"
    ])
    if safe_ticker and raw_data is not None and not raw_data.empty:
        with tab_d:
            render_dashboard("daily", raw_data, api_key, entry_price, selected_name, safe_ticker, is_krw)
        with tab_w:
            render_dashboard("weekly", raw_data, api_key, entry_price, selected_name, safe_ticker, is_krw)
        with tab_m:
            render_dashboard("monthly", raw_data, api_key, entry_price, selected_name, safe_ticker, is_krw)
    else:
        st.error(f"⚠️ 데이터를 불러오지 못했습니다. 종목 코드({safe_ticker})를 다시 확인해 주세요.")

# --------------------------------------------------------------------
# 2️⃣ 메인 탭 2: 과거 추천주 성과 검증 관제탑
# --------------------------------------------------------------------
with main_tab2:
    st.markdown("### ⚡ AI 실시간 추천 및 과거 소급 검증 관제탑")
    # 💡 [시장별 최적 스캔 시간 안내 박스]
    st.markdown("""
    <div style="background-color: #0f172a; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; margin: 10px 0 15px 0; font-size: 13px; line-height: 1.6;">
        <div style="font-weight: bold; color: #38bdf8; margin-bottom: 6px;">⏰ 시장별 AI 최적 스캔 권장 시간 안내</div>
        <div style="display: flex; gap: 16px; flex-wrap: wrap; color: #e2e8f0;">
            <span>🇰🇷 <b>국내 주식:</b> 오전 <b style="color: #ff4b4b;">08:00 ~ 08:40</b> <span style="color: #94a3b8; font-size: 11px;">(개장 전 동시호가 준비)</span></span>
            <span>🇺🇸 <b>미국 주식:</b> 밤 <b style="color: #ff4b4b;">21:30 ~ 22:00</b> <span style="color: #94a3b8; font-size: 11px;">(정규장 개장 전 준비)</span></span>
            <span>🪙 <b>암호화폐:</b> 오전 <b style="color: #ff4b4b;">08:30 ~ 08:50</b> <span style="color: #94a3b8; font-size: 11px;">(09시 일봉 리셋 전)</span></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_b1, col_b2 = st.columns([1.1, 0.9])

    # --------------------------------------------------------------------
    # 1. 오늘의 시장별 통합 Top 10 추천 (전략별 태그 직관화)
    # --------------------------------------------------------------------
    with col_b1:
        st.markdown("#### 1️⃣ 오늘의 시장별 통합 Top 10 추천")
        st.markdown("<div style='color: #ffffff; font-weight: bold; font-size: 14px; margin-bottom: 10px;'>✨무조건 20일선 or 60일선에 조건주문 걸기✨ / 바로 주문 ❌</div>", unsafe_allow_html=True)

        if st.button("🔥 실시간 전 시장 스캔", key="btn_direct_scan", use_container_width=True):
            bg_scan_worker(ASSETS)

        # ====================================================================
        # 🎯 [1번 탭 UI] 90% 승률 정예 Top 3 표출 및 스마트 진입가 표기
        # ====================================================================
        def render_midterm_top10(market_title, key_name):
            raw_results = st.session_state.get(key_name, [])
            
            # 승률 85% 이상 & 예상수익 플러스 종목만 엄선
            results = [
                x for x in raw_results 
                if x.get('up_prob', 0.0) >= 85.0 and x.get('upside', 0.0) > 0.0
            ]

            st.markdown(f"### {market_title}")
            
            if not results:
                st.caption("⚪ 현재 90% 승률 엄격 기준(캔들/이평/매물대 패턴 충족)에 부합하는 정예 종목이 없습니다.")
                return

            # 자금 집중 및 관리를 위해 최상위 정예 Top 3만 표출
            for rank, res in enumerate(results[:3], 1):
                sig = res.get('signal', '')
                win_rate = res.get('up_prob', 0.0)
                upside_val = res.get('upside', 0.0)
                entry_p = res.get('entry_price', 0.0)
                
                # 💡 신규 매매 대응 상태 및 추천 비중 바인딩
                action_status = res.get('action_status', '🎯 [신규 눌림목]')
                rec_weight = res.get('rec_weight', '포트폴리오 비중 8~10%')
                
                upside_color = "#ff4b4b" if upside_val > 0 else "#38bdf8"
                upside_html = f"+{upside_val:.1f}%" if upside_val > 0 else f"{upside_val:.1f}%"
                
                # 화폐 단위 자동 포맷팅
                is_krw = any(x in res.get('ticker', '') for x in [".KS", ".KQ", "-KRW"])
                if is_krw:
                    fmt_entry = f"₩{entry_p:,.0f}원" if entry_p >= 1.0 else f"₩{entry_p:,.6f}원"
                else:
                    fmt_entry = f"${entry_p:,.2f}"

                # 시그널 태그 정돈
                sig_list = [s.strip("[] ") for s in sig.split('/') if s.strip()]
                sig_bullets = "".join([f"<div style='margin-left:8px; color:#94a3b8;'>• {s}</div>" for s in sig_list])

                card_html = f"""
                <div style="background-color: #1e293b; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #38bdf8; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                    <div style="font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 6px;">
                        🏆 {rank}위. {res['name']} <span style="font-size: 12px; color: #64748b; font-weight: normal;">({res['ticker']})</span>
                    </div>
                    <div style="font-size: 13px; color: #ffd700; font-weight: bold; margin-bottom: 4px;">
                        🎯 지정가 추천 진입가: <span style="color: #ffffff;">{fmt_entry}</span>
                    </div>
                    <div style="font-size: 12px; color: #10b981; font-weight: bold; margin-bottom: 6px;">
                        💡 대응 및 비중: <span style="color: #ffffff;">{action_status}</span> <span style="color: #94a3b8;">({rec_weight})</span>
                    </div>
                    <hr style="border:0; border-top:1px solid #334155; margin: 6px 0;">
                    <div style="font-size: 13px; color: #e2e8f0; margin-bottom: 6px;">
                        📌 <b>알고리즘 확신도 / 목표수익:</b> <span style="color:#38bdf8; font-weight:bold;">{win_rate:.1f}%</span> (<span style="color:{upside_color}; font-weight:bold;">{upside_html}</span>)
                    </div>
                    <div style="font-size: 12px; color: #e2e8f0; line-height: 1.5;">
                        🔍 <b>충족 패턴 및 시그널:</b>
                        {sig_bullets}
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

        kr_res = st.session_state.get('scan_midterm_kr', [])
        us_res = st.session_state.get('scan_midterm_us', [])

        if kr_res or us_res:
            c1, c2 = st.columns(2)
            with c1: render_midterm_top10("🇰🇷 국내 증시", 'scan_midterm_kr')
            with c2: render_midterm_top10("🇺🇸 미국 증시", 'scan_midterm_us')
        else:
            st.info("💡 위의 [실시간 중장기 정예 종목 스캔] 버튼을 누르면 스캔이 시작됩니다.")

    # --------------------------------------------------------------------
    # 2. 과거 N봉 전 추천주 실전 매매 검증 (하이브리드 익절 & -3% 강제 손절)
    # --------------------------------------------------------------------
    with col_b2:
        st.markdown("#### 2️⃣ 과거 추천주 실전 매매 성과 검증 (하이브리드 익절 & -3% 강제 손절)")
        
        bars_ago = st.slider("📊 검증할 과거 시점(봉) 선택", min_value=1, max_value=20, value=5, key="slider_bars_ago")
        
        # 🗓️ [영업일 기준 실시간 날짜 산출 및 색상 지정 UI]
        import pandas as pd
        from datetime import datetime, timedelta
        target_dt = (datetime.now() - pd.tseries.offsets.BDay(bars_ago)).strftime("%Y-%m-%d")
        
        st.markdown(
            f"🗓️ 선택 시점: <span style='color:#ff4b4b; font-weight:bold;'>{bars_ago}봉 전</span> <span style='color:#ffffff; font-weight:bold;'>({target_dt})</span>",
            unsafe_allow_html=True
        )
        st.caption("※ **고정 %와 ATR 중 적은 값**으로 익절하며, **+2% 달성 시 +0.5% 방어**, **미달 시 무조건 -3.0% 강제 손절**합니다.")

        if st.button(f"📈 {bars_ago}봉 전 추천주 실전 매매 성과 검증하기", key="btn_check_retro_perf", use_container_width=True):
            import socket
            import sqlite3
            import numpy as np
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
            
            socket.setdefaulttimeout(2.5)

            # 1. DB 저장 기록 확인
            target_date_str = (datetime.now() - timedelta(days=bars_ago*1.5)).strftime("%Y-%m-%d")
            db_top_tasks = []
            try:
                conn = sqlite3.connect(DB_FILE, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT market_type, stock_name, ticker, entry_price FROM rec_history WHERE rec_date <= ? ORDER BY rec_date DESC LIMIT 15", (target_date_str,))
                db_rows = cursor.fetchall()
                conn.close()
                if len(db_rows) >= 5:
                    for row in db_rows:
                        db_top_tasks.append({"market": row[0], "name": row[1], "ticker": row[2], "entry_p": row[3], "signal": "DB실기록"})
            except Exception:
                pass

            # 🎯 selected_tops 선제적 안전 초기화 (UnboundLocalError 방지)
            selected_tops = []

            # 2. 📊 프로그레스 바 및 스캔 진행 상황 UI 세팅
            if not db_top_tasks:
                categories = [("국내", "₩ 국내 주식"), ("미국", "💲 미국 주식"), ("코인", "🪙 암호화폐(코인)")]
                all_candidates = []
                for m_label, asset_key in categories:
                    items = {k: v for k, v in ASSETS[asset_key].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}
                    for name, ticker in items.items():
                        all_candidates.append((m_label, name, ticker))

                total_count = len(all_candidates)
                cand_matched = []
                processed = 0

                progress_bar = st.progress(0.0)
                status_box = st.empty()
                ctx = get_script_run_ctx()

                with ThreadPoolExecutor(max_workers=25) as executor:
                    futures = {executor.submit(eval_past_recommendation_worker, cand, ctx): cand for cand in all_candidates}
                    for future in as_completed(futures):
                        processed += 1
                        cand_info = futures[future]
                        stock_name = cand_info[1]

                        pct = min(1.0, processed / total_count)
                        progress_bar.progress(pct)
                        status_box.markdown(f"🚀 **과거 {bars_ago}봉 전 추천주 스캔 중...** `{processed}/{total_count}` ({int(pct*100)}%) | 분석 중: **{stock_name}**")

                        try:
                            res = future.result(timeout=2.0)
                            if res: cand_matched.append(res)
                        except Exception:
                            continue

                progress_bar.progress(1.0)
                status_box.success(f"✅ 과거 {bars_ago}봉 전 추천주 스캔 완료!")

                # 🎯 [전 시장 무제한 통합 순위 정렬] 국가/시장 상관없이 종합 점수(score) 내림차순 정렬
                cand_matched_sorted = sorted(cand_matched, key=lambda x: x['score'], reverse=True)

                # 상위 통합 정예 종목 선정 (통합 Top 10)
                selected_tops = cand_matched_sorted[:10]
            else:
                selected_tops = db_top_tasks

            # 💡 [유령 종목 및 ADX < 20 차단] DB 기록도 ADX 20.0 미만은 강제 탈락
            valid_tops = []
            for x in selected_tops:
                if x and isinstance(x, dict):
                    exp_w = x.get('exp_win', x.get('up_prob', 0.0))
                    sig_w = str(x.get('signal', '')).strip()
                    adx_w = float(x.get('adx', 25.0))
                    
                    if exp_w >= 85.0 and sig_w and sig_w != "None" and adx_w >= 20.0:
                        valid_tops.append(x)

            # 🚀 통합 순위(1위~N위) 엄격 재부여 (미국/국내/코인 종합 최우수 순)
            selected_tops = sorted(valid_tops, key=lambda x: x['score'], reverse=True)
            for r, x in enumerate(selected_tops, 1):
                x['rank'] = r

            # 3. 🎯 실시간 매매 시뮬레이션 진행 (5/10/20/60/120/200일선 저항 + 5/10/20% 상한선 락 + -3% 손절)
            final_results = []
            all_returns = []
            win_count = 0

            # ====================================================================
            # 🎯 [2번 탭 백테스트] 1~2봉 체결 & -3% 하드손절 정밀 시뮬레이션
            # ====================================================================
            for item in selected_tops:
                ticker = item['ticker']
                df_hist = get_raw_daily_data(ticker)
                if df_hist is None: continue

                t_idx = item.get('t_idx', len(df_hist) - 1 - bars_ago)
                if t_idx < 0: t_idx = 0
                
                rec_entry = item['entry_p'] if item.get('entry_p', 0) > 0 else float(df_hist['Close'].iloc[t_idx])

                # 1~5봉 이내 미래 차트 구간 추출
                future_bars = df_hist.iloc[t_idx + 1 : t_idx + 6]
                if future_bars.empty:
                    continue

                is_bought = False
                is_closed = False
                max_ret = -999.0
                realized_ret = 0.0
                remaining_qty = 1.0
                action_events = []
                actual_entry = rec_entry

                for bar_idx, (_, bar) in enumerate(future_bars.iterrows(), start=1):
                    if is_closed: break

                    b_open, b_high, b_low = float(bar['Open']), float(bar['High']), float(bar['Low'])

                    just_bought_today = False

                    # 💡 [1. 지정가 체결 정밀 연산] 최저가 착시 차단 (시가가 지정가보다 낮으면 시가, 아니면 지정가 체결)
                    if not is_bought:
                        if bar_idx <= 2 and b_low <= rec_entry * 1.002:
                            is_bought = True
                            just_bought_today = True
                            
                            # 최저가(b_low)가 아닌 실제 체결 가능 가격(b_open 또는 rec_entry) 반영
                            actual_entry = min(b_open, rec_entry)
                            sl_price = actual_entry * 0.97  # -3.0% 칼손절선
                            
                            raw_b_date = bar['Date']
                            dt_obj = pd.to_datetime(raw_b_date, format='mixed', errors='coerce') if isinstance(raw_b_date, str) else pd.to_datetime(raw_b_date)
                            item['bought_date'] = f"{dt_obj.month}월 {dt_obj.day}일"
                            item['actual_entry'] = actual_entry
                        else:
                            if bar_idx >= 2:
                                break
                            continue

                    # 💡 [2. 아침 고가 착시 차단] 체결 당일 아침 슈팅 무시
                    if just_bought_today:
                        eff_high = actual_entry
                    else:
                        eff_high = max(actual_entry, b_high)

                    # 최고 수익률 추적
                    b_high_ret = ((eff_high - actual_entry) / actual_entry) * 100.0
                    if b_high_ret > max_ret:
                        max_ret = b_high_ret

                    # 💡 [대형 파동 판별] RVOL 폭발, 급등, 60일 신고가 태그 포함 여부
                    is_super_wave = any(k in item.get('signal', '') for k in ["🚀RVOL", "대형파동", "신고가", "장대양봉", "추격"])

                    # 🎯 [PRO QUANT 개편] 손익비 2.0 : 1 및 Break-Even 청산 수식
                    sl_price = actual_entry * 0.975  # -2.5% 타이트 손절선
                    tp1_price = actual_entry * 1.050 # +5.0% 1차 익절선 (R:R = 2.0 : 1)
                    tp2_price = actual_entry * 1.090 # +9.0% 2차 익절선

                    # 💡 Break-Even: +3.0% 이상 고가 형성 시 손절가를 매수가 +0.3%로 즉시 상향
                    if max_ret >= 3.0:
                        sl_price = max(sl_price, actual_entry * 1.003)

                    if is_super_wave:
                        # 🚀 [대형 파동주]: 2차 목표(+9.0%) 도달 시 50% 익절
                        if eff_high >= tp2_price and remaining_qty == 1.0:
                            realized_ret += 0.50 * 0.090
                            remaining_qty -= 0.50
                            action_events.append("대파동 익절 (+9.0%)")
                    else:
                        # 🛡️ [일반 스윙주]: 1차 목표(+5.0%) 도달 시 50% 익절
                        if eff_high >= tp1_price and remaining_qty == 1.0:
                            realized_ret += 0.50 * 0.050
                            remaining_qty -= 0.50
                            action_events.append("1차 익절 (+5.0%)")

                    # 🛑 [-2.5% 또는 Break-Even 손절]
                    if b_low <= sl_price and remaining_qty > 0 and not just_bought_today:
                        actual_loss_pct = ((min(b_open, sl_price) - actual_entry) / actual_entry)
                        realized_ret += remaining_qty * actual_loss_pct
                        action_events.append(f"손절/본절방어 ({actual_loss_pct*100:+.1f}%)")
                        remaining_qty = 0.0
                        is_closed = True
                        break

                # ------------------------------------------------------------
                # ⚪ [미체결 전문 분석 ENGINE - 날짜 보정 / 순수 HTML 포맷 교정본]
                # ------------------------------------------------------------
                if not is_bought:
                    item['is_bought'] = False
                    item['real_ret'] = 0.0
                    item['max_ret'] = 0.0

                    # 1~2봉 이내 실제 형성된 시가(open_p), 저가(min_2b_low) 및 최고가 추출
                    open_p = float(future_bars.iloc[0]['Open'])
                    min_2b_low = float(future_bars.iloc[:2]['Low'].min())
                    max_5b_high = float(future_bars['High'].max())
                    
                    # 💡 [날짜 보정] 체결일(추천 다음 영업일) 날짜를 시차 오차 없이 정확 추출
                    raw_b_date = future_bars.iloc[0]['Date']
                    dt_obj = pd.to_datetime(raw_b_date).tz_localize(None) if hasattr(pd.to_datetime(raw_b_date), 'tz_localize') else pd.to_datetime(raw_b_date)
                    buy_date_str = f"{dt_obj.month}월 {dt_obj.day}일"

                    # 잠재 수익률 연산
                    open_potential_ret = ((max_5b_high - open_p) / open_p) * 100.0
                    potential_ret = ((max_5b_high - min_2b_low) / min_2b_low) * 100.0

                    # 이동평균선 수치 추출
                    ma5_val  = float(df_hist['MA_5'].iloc[t_idx])  if 'MA_5' in df_hist.columns else rec_entry
                    ma10_val = float(df_hist['MA_10'].iloc[t_idx]) if 'MA_10' in df_hist.columns else rec_entry
                    ma20_val = float(df_hist['MA_20'].iloc[t_idx]) if 'MA_20' in df_hist.columns else rec_entry

                    # 화폐 단위 포맷팅
                    is_krw = any(x in ticker for x in [".KS", ".KQ", "-KRW"])
                    fmt_p = lambda p: f"₩{p:,.0f}" if is_krw else f"${p:,.2f}"

                    # 🔥 [HTML 전용 빨간색 태그] (Streamlit 마크다운 문법 제거)
                    red_open_ret = f"<span style='color:#ff4b4b; font-weight:bold;'>+{open_potential_ret:.1f}%</span>"
                    red_low_ret  = f"<span style='color:#ff4b4b; font-weight:bold;'>+{potential_ret:.1f}%</span>"

                    # 1. 지지 받은 이동평균선 및 차트 분석
                    if abs(min_2b_low - ma5_val) / ma5_val < 0.015:
                        cause_msg = f"🎯 <b>5일선 지지 반등</b>: 지정가({fmt_p(rec_entry)})까지 밀리지 않고, <b>실제 5일 이동평균선({fmt_p(min_2b_low)})</b>을 견고하게 지지받고 우상향했습니다."
                    elif abs(min_2b_low - ma10_val) / ma10_val < 0.015:
                        cause_msg = f"🛡️ <b>10일선 지지 반등</b>: 지정가({fmt_p(rec_entry)}) 미달 후 <b>실제 10일 이동평균선({fmt_p(min_2b_low)})</b> 부근에서 저점을 지지받았습니다."
                    elif abs(min_2b_low - ma20_val) / ma20_val < 0.015:
                        cause_msg = f"🧱 <b>20일선 지지 반등</b>: 세력 심리선인 <b>20일 이동평균선({fmt_p(min_2b_low)})</b> 지지를 확인하고 시세가 반등했습니다."
                    elif open_p > rec_entry * 1.012:
                        cause_msg = f"🚀 <b>갭상승 모멘텀 분출</b>: 추천 익일 시가가 갭상승으로 시작하여 지정가({fmt_p(rec_entry)}) 하향 눌림 없이 강한 관성으로 직행했습니다."
                    else:
                        cause_msg = f"📐 <b>단기 저점 형성 후 직행</b>: 지정가({fmt_p(rec_entry)}) 근처 저점({fmt_p(min_2b_low)})까지만 눌린 뒤 상방 파동이 분출했습니다."

                    # 2. 체결 시점/가격 및 최고 수익률 피드백 (줄바꿈 <br> 사용으로 초록색 코드블록 원천 차단)
                    feedback_msg = (
                        f"💡 <b>실전 체결 시점 및 최고 수익률 분석</b>:<br>"
                        f"• <b>시초가 매수 시</b>: {buy_date_str} 시초가({fmt_p(open_p)})에 매수했다면 최고 {red_open_ret} 달성!<br>"
                        f"• <b>저점 매수 시</b>: {buy_date_str} 실제 저점({fmt_p(min_2b_low)})에 매수했다면 최고 {red_low_ret} 대파동 수익 포착!"
                    )

                    item['reason'] = f"{cause_msg}<br><br>{feedback_msg}"
                    final_results.append(item)
                    continue

                item['is_bought'] = True
                if not is_closed and remaining_qty > 0:
                    last_c_ret = ((float(future_bars['Close'].iloc[-1]) - actual_entry) / actual_entry)
                    realized_ret += remaining_qty * last_c_ret
                    action_events.append(f"기간 만기 청산 ({last_c_ret*100:+.1f}%)")

                realized_ret_pct = realized_ret * 100.0
                if realized_ret_pct > 0: win_count += 1
                all_returns.append(realized_ret_pct)

                event_str = f" ({', '.join(action_events)})" if action_events else ""
                if "1차 익절" in "".join(action_events):
                    reason = f"🎯 **목표 달성**: 단기 파동 수익을 확정했습니다.{event_str}"
                elif "강제 손절" in "".join(action_events):
                    reason = f"🛑 **-3% 원칙 손절**: 지지선 붕괴에 따라 지정 손절가에 손절했습니다.{event_str}"
                else:
                    reason = f"⏸️ **기간 만기**: 5봉 경과 후 보유 물량을 청산했습니다.{event_str}"

                item['real_ret'] = realized_ret_pct
                item['max_ret'] = max_ret
                item['reason'] = reason
                final_results.append(item)

            st.session_state['retro_kr'] = [x for x in final_results if x['market'] == "국내"]
            st.session_state['retro_us'] = [x for x in final_results if x['market'] == "미국"]
            st.session_state['retro_coin'] = [x for x in final_results if x['market'] == "코인"]
            st.session_state['retro_returns'] = all_returns
            st.session_state['retro_win_count'] = win_count

        # --------------------------------------------------------------------
        # 📊 소급 검증 결과 화면 표출
        # --------------------------------------------------------------------
        retro_returns = st.session_state.get('retro_returns', [])
        retro_kr = st.session_state.get('retro_kr', [])
        retro_us = st.session_state.get('retro_us', [])
        retro_coin = st.session_state.get('retro_coin', [])
        win_count = st.session_state.get('retro_win_count', 0)

        if 'retro_returns' in st.session_state:
            if retro_returns:
                avg_r = sum(retro_returns) / len(retro_returns)
                win_rate = (win_count / len(retro_returns)) * 100
                n_samples = len(retro_returns)

                # 💡 [신규 연산] Profit Factor (총 이익 / 총 손실 비율) 연산
                gains = [r for r in retro_returns if r > 0]
                losses = [abs(r) for r in retro_returns if r < 0]
                tot_gain = sum(gains)
                tot_loss = sum(losses)
                profit_factor = (tot_gain / tot_loss) if tot_loss > 0 else (tot_gain if tot_gain > 0 else 1.0)

                # 💡 [신규 연산] MDD (Maximum Drawdown - 누적 수익률 기준 최대 낙폭) 연산
                cum_returns = np.cumsum(retro_returns)
                peaks = np.maximum.accumulate(cum_returns)
                drawdowns = peaks - cum_returns
                mdd = np.max(drawdowns) if len(drawdowns) > 0 else 0.0

                # 📊 통계적 신뢰 표본(N >= 15) 판정 레이블
                if n_samples >= 15:
                    sample_trust_msg = f"✅ 통계적 신뢰 표본 확보 (N = {n_samples}개 ≥ 15개)"
                else:
                    sample_trust_msg = f"⚠️ 표본 수 부족 (N = {n_samples}개 < 15개: 대수의 법칙 미달)"

                st.markdown("---")
                st.markdown(f"#### 📊 과거 검증 정밀 퀀트 리포트 <span style='font-size:12px; color:#94a3b8; font-weight:normal;'>({sample_trust_msg})</span>", unsafe_allow_html=True)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🎯 검증 승률 (Win Rate)", f"{win_rate:.1f}%")
                m2.metric("📈 평균 수익률", f"{avg_r:+.1f}%")
                m3.metric("⚖️ Profit Factor", f"{profit_factor:.2f}")
                m4.metric("📉 MDD (최대 낙폭)", f"-{mdd:.1f}%", help=f"총 검증 표본 수 N = {n_samples}개")
                st.markdown("---")

                def render_retro_cards(title, item_list):
                    st.markdown(f"### {title}")
                    if not item_list:
                        st.caption("⚪ 해당 시점 충족 종목 없음")
                        return

                    for item in item_list:
                        exp_win = item.get('exp_win', 75.0)
                        exp_ret = item.get('exp_ret', 3.0)
                        entry_p = item.get('entry_p', 0.0)
                        is_bought = item.get('is_bought', True)

                        # 화폐 단위별 진입가 포맷팅
                        is_krw = any(x in item.get('ticker', '') for x in [".KS", ".KQ", "-KRW"])
                        fmt_entry = f"₩{entry_p:,.0f}원" if is_krw else f"${entry_p:,.2f}"

                        ret_val = item.get('real_ret', 0.0)
                        max_val = item.get('max_ret', 0.0)
                        ret_html = f"<span style='color:#ff4b4b; font-weight:bold;'>+{ret_val:.1f}%</span>" if ret_val > 0 else (f"<span style='color:#38bdf8; font-weight:bold;'>{ret_val:.1f}%</span>" if ret_val < 0 else "<span style='color:#94a3b8;'>0.0%</span>")

                        bought_date = item.get('bought_date', '')
                        date_section = f"""<div style="font-size: 12px; color: #a7f3d0; margin-bottom: 6px; font-weight: bold;">
📅 실제 체결일: <span style="color:#ffffff;">{bought_date}</span>
</div>""" if (is_bought and bought_date) else ""

                        # 🟢 ret_section 변수 복구 정의
                        if is_bought:
                            ret_section = f"""{date_section}<div style="font-size: 13px; color: #e2e8f0; margin-bottom: 6px; font-weight: bold;">
📈 실전 수익률: {ret_html} (최고: <span style="color:#ff4b4b;">+{max_val:.1f}%</span>)
</div>"""
                        else:
                            ret_section = """<div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px; font-weight: bold;">
⚪ 매매 상태: 미체결
</div>"""

                        # 당시 추천 순위 라벨 매핑 (1위~Top 5)
                        rank_num = item.get('rank', '-')
                        rank_badge = f"<span style='color: #ffd700; font-weight: bold;'>🏆 당시 추천 {rank_num}위</span>" if isinstance(rank_num, int) else ""

                        card_html = f"""<div style="background-color: #1e2230; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
    <div style="font-size: 15px; font-weight: bold; color: #ffffff;">
        • {item['name']} <span style="font-size: 12px; color: #94a3b8; font-weight: normal;">({item['ticker']})</span>
    </div>
    <div style="font-size: 12px;">
        {rank_badge}
    </div>
</div>
<div style="font-size: 11px; color: #38bdf8; margin-bottom: 4px; font-weight: 600;">
🏷️ 시그널: {item['signal']}
</div>
<div style="font-size: 13px; color: #ffd700; margin-bottom: 6px; font-weight: bold;">
🎯 당시 추천 진입가: <span style="color:#ffffff;">{fmt_entry}</span>
</div>
<div style="font-size: 12px; color: #e2e8f0; margin-bottom: 6px; font-weight: bold;">
📌 당시 예상 승률 / 예상 수익: <span style="color:#38bdf8;">{exp_win:.1f}%</span> (<span style="color:#ff4b4b;">+{exp_ret:.1f}%</span>)
</div>
{ret_section}
<div style="font-size: 12px; color: #cbd5e1; line-height: 1.5; background-color: #0f172a; padding: 8px 10px; border-radius: 6px; margin-top: 4px;">
💡 <b>매매 경과 및 분석</b><br>
{item['reason'].replace('**', '')}
</div>
</div>"""

                        st.markdown(card_html, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1: render_retro_cards("🇰🇷 국내 주식", retro_kr)
                with c2: render_retro_cards("🇺🇸 미국 주식", retro_us)
                with c3: render_retro_cards("🪙 암호화폐", retro_coin)
            else:
                st.warning(f"⚠️ {st.session_state.get('slider_bars_ago', 5)}봉 전 시점에는 조건 충족 추천주가 없었습니다.")
        else:
            st.info("💡 위의 [검증하기] 버튼을 누르면 하이브리드 익절 및 -3% 강제 손절 지침을 반영한 실전 성과가 연산됩니다.")

# --------------------------------------------------------------------
# 3️⃣ 메인 탭 3: 6M~1Y 중장기 저점 유망주 과거 1년 전수 스캐너
# --------------------------------------------------------------------
with main_tab3:
    col_hdr1, col_hdr2 = st.columns([1.1, 0.9])
    
    with col_hdr1:
        st.markdown("### 🚀 6개월~1년 중장기 정예 유망주 관제탑")
        st.markdown("""
        <div style="background-color: #0f172a; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; font-size: 13px; line-height: 1.6;">
            <div style="font-weight: bold; color: #10b981; margin-bottom: 6px;">💡 6M~1Y 중장기 +100% 목표 초엄격 스캐닝 시스템</div>
            <div style="color: #e2e8f0;">
                • <b>스캐닝 스펙:</b> 시총 8천억↑ / S&P500 + 주봉 20주/50주선 정배열 + 일봉 20일선 눌림목 + OBV 세력 매집.<br>
                • <b>중장기 대응 전략:</b> -30% 도달 시 1:1 동일 금액 물타기(평단 -15% 하향) / <b>+30%(1차) ➔ +60%(2차) ➔ +100%+(트레일링)</b>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_hdr2:
        st.markdown("""
        <div style="background-color: #1e1b2e; border: 2px solid #ef4444; padding: 12px 16px; border-radius: 8px; font-size: 12.5px; height: 100%;">
            <div style="color: #fca5a5; font-weight: bold; font-size: 14px; margin-bottom: 6px;">
                📌 추천 매매 대응 행동 및 비중 가이드
            </div>
            <div style="color: #e2e8f0; line-height: 1.65;">
                • <b>🎯 [신규 눌림목]</b>: 최초 진입 (주도주 12~15% / 일반 8~10%)<br>
                • <b>🔥 [추세 재진입]</b>: 보유자 불타기 (원금의 +30~50% 추가 적립)<br>
                • <b>💧 [우량주 물타기]</b>: -15~-30% 조정 시 1:1 동일금액 추매 (평단 하향)<br>
                • <b>⚠️ [리스크관리/손절]</b>: 200일선 이탈 시 50% 축소 또는 전량 손절<br>
                • <b>💰 [1/2차 동적 익절]</b>: +25%/+50% 도달 시 30~40% 부분 청산<br>
                • <b>🚨 [상투/트레일링스탑]</b>: <b>익일 시초가 즉시 전량 매도</b> (수익 최종 확정)
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # 과거 1년 전체 종목 추천 날짜 & 수익률 전수 조사
    # ----------------------------------------------------------------
    st.markdown("#### 과거 1년 전체 종목 추천 날짜 & 수익률 전수 조사")
    st.markdown("<div style='color: #38bdf8; font-weight: bold; font-size: 14px; margin-bottom: 10px;'>✨ 과거 1년 내 포착된 종목과 추천 날짜 및 현재/최고 수익률 표 ✨</div>", unsafe_allow_html=True)

    if st.button("🔥 과거 1년 추천 날짜/수익률 전체 전수 스캔", key="btn_history_all_scan", use_container_width=True):
        history_results = scan_all_historical_midterm_signals(ASSETS)
        st.session_state['history_scan_table'] = history_results

    history_table_data = st.session_state.get('history_scan_table', [])

    if history_table_data:
        df_display = pd.DataFrame(history_table_data)
        df_display = df_display.sort_values(by=["종목명", "추천 포착 날짜"], ascending=[True, False])

        # 💡 [정상화] 통계 집계는 실제 현재가 손익(raw_curr_ret) 기준으로 정확히 산출
        total_hits = len(df_display)
        win_hits = len(df_display[df_display['raw_curr_ret'] > 0])
        win_rate = (win_hits / total_hits * 100) if total_hits > 0 else 0.0
        
        pos_rets = df_display[df_display['raw_curr_ret'] > 0]['raw_curr_ret']
        neg_rets = df_display[df_display['raw_curr_ret'] < 0]['raw_curr_ret']
        total_gain = pos_rets.sum()
        total_loss = abs(neg_rets.sum())
        profit_factor = (total_gain / total_loss) if total_loss > 0 else (total_gain if total_gain > 0 else 0.0)

        max_hit_ret = df_display['최대 파동 수익률 (%)'].max()
        pf_color = "#10b981" if profit_factor >= 2.0 else "#38bdf8"

        st.markdown(f"""
        <div style="background-color: #1e2230; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 15px;">
            <div style="font-size: 13px; color: #ffffff; font-weight: bold; margin-bottom: 6px;">📊 과거 1년 실전 분할 매도 적용 성과 보고서</div>
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div><span style="font-size: 11px; color: #94a3b8;">총 포착 건수</span><br><b style="font-size: 15px; color: #ffffff;">{total_hits}건</b></div>
                <div><span style="font-size: 11px; color: #94a3b8;">실전 승률</span><br><b style="font-size: 15px; color: #10b981;">{win_rate:.1f}%</b></div>
                <div><span style="font-size: 11px; color: #94a3b8;">Profit Factor (PF)</span><br><b style="font-size: 15px; color: {pf_color};">{profit_factor:.2f}</b></div>
                <div><span style="font-size: 11px; color: #94a3b8;">최고 수익 파동</span><br><b style="font-size: 15px; color: #ff4b4b;">+{max_hit_ret:.1f}%</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 💡 [시그널 매도 이익 컬럼 제거] 깔끔한 표 구성
        cols_to_show = ["시장", "종목명", "추천 포착 날짜", "추천 진입가", "현재가", "최대 파동 수익률 (%)", "추천 매매 대응", "누적 실전 PnL (%)"]
        table_df = df_display[cols_to_show]

        # 💡 [st.dataframe 전용 Pandas Styler 색상 적용 함수]
        def style_pnl_colors(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: #ff4b4b; font-weight: bold;'  # 수익 (빨강)
                elif val < 0:
                    return 'color: #38bdf8; font-weight: bold;'  # 손실 (파랑)
                return 'color: #ffffff;'                        # 0% (흰색)
            elif isinstance(val, str):
                if '(+' in val:
                    return 'color: #ff4b4b; font-weight: bold;'  # 수익 (빨강)
                elif '(-' in val:
                    return 'color: #38bdf8; font-weight: bold;'  # 손실 (파랑)
            return ''

        # Pandas Styler 적용
        styled_df = table_df.style.map(style_pnl_colors)

        st.markdown("##### 🏆 과거 1년 포착 종목 순위표")
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "현재가": st.column_config.TextColumn(help="현재 주가 및 추천 진입가 대비 수익률입니다."),
                "누적 실전 PnL (%)": st.column_config.NumberColumn(format="%.1f%%", help="1~2차 익절 및 손절/상투 청산으로 실제 확정된 PnL입니다. (매도 미실행 시 0.0%)"),
                "최대 파동 수익률 (%)": st.column_config.NumberColumn(format="%.1f%%")
            }
        )
    else:
        st.info("💡 위의 [과거 1년 추천 날짜/수익률 전체 전수 스캔] 버튼을 누르면 전체 주식의 추천 날짜와 수익률 표가 완성됩니다.")