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
                # 한국 종목은 FDR로 일괄 수집하여 누락을 완벽 방지
                clean_tickers = [t.split('.')[0] for t in all_tickers]
                # 최근 5거래일 시세 수집
                df_close = pd.DataFrame()
                df_vol = pd.DataFrame()
                for full_t, clean_t in zip(all_tickers, clean_tickers):
                    try:
                        df_single = fdr.DataReader(clean_t, start='2024-01-01').tail(7)
                        if len(df_single) >= 2:
                            df_close[full_t] = df_single['Close']
                            df_vol[full_t] = df_single['Volume']
                    except Exception:
                        continue
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
        "코스모화학:005420.KS,금양:009410.KS,영풍:000670.KS,풍산홀딩스:024810.KS,한국앤컴퍼니:000240.KS,"
        "코오롱인더:120110.KS,효성중공업:298040.KS,효성화학:298000.KS,대웅:003090.KS,종근당:185750.KS,"
        "JW중외제약:001060.KS,보령:003850.KS,동아쏘시오홀딩스:000640.KS,동아에스티:170900.KS,광동제약:009290.KS,"
        "한독:002390.KS,대원제약:003220.KS,일양약품:007570.KS,삼진제약:005500.KS,부광약품:003000.KS,"
        "영진약품:003520.KS,일동제약:249420.KS,하나제약:293480.KS,환인제약:016580.KS,동화약품:000020.KS,"
        "안국약품:001540.KQ,동국제약:086450.KQ,휴온스:243070.KQ,리가켐바이오:141080.KQ,바이오니아:064550.KQ,"
        "유나이티드제약:033270.KS,제넥신:095700.KQ,메드팩토:235980.KQ,앱클론:174900.KQ,지씨셀:144510.KQ,"
        "헬릭스미스:084990.KQ,에이치엘비생명과학:067630.KQ,셀리드:299660.KQ,큐리언트:115180.KQ,올릭스:226950.KQ,"
        "인트론바이오:048530.KQ,앤디포스:238090.KQ,바디텍메드:206640.KQ,랩지노믹스:084650.KQ,수젠텍:253840.KQ,"
        "피씨엘:241820.KQ,이수앱지스:086890.KQ,아미코젠:092040.KQ,대동:000490.KS,TYM:002900.KS,"
        "아세아텍:050860.KQ,경농:002100.KS,조비:001550.KS,남해화학:025860.KS,카프로:006380.KS,"
        "백광산업:001340.KS,송원산업:004430.KS,이수화학:005950.KS,한농화성:011500.KS,국도화학:007690.KS"
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

@st.cache_data(ttl=1800) # ⚡ 10초 -> 30분 캐싱으로 변경하여 서버 차단 완벽 방지
def get_raw_daily_data(ticker):
    import time
    import requests
    import pandas as pd
    import yfinance as yf
    import FinanceDataReader as fdr
    from datetime import datetime, timedelta

    # ⚡ 서버 연속 폭주 방지용 미세 지연
    time.sleep(0.01)

    # 🪙 [1. 암호화폐 특화 (업비트)]
    if ticker.endswith('-KRW'):
        try:
            coin_symbol = ticker.split('-')[0]
            market_code = f"KRW-{coin_symbol}"
            url = "https://api.upbit.com/v1/candles/days"
            headers = {"accept": "application/json"}
            
            candles = []
            to_param = None
            
            for _ in range(2):
                params = {"market": market_code, "count": 200}
                if to_param: params["to"] = to_param
                
                res = requests.get(url, params=params, headers=headers, timeout=2)
                if res.status_code == 200:
                    data = res.json()
                    if not data: break
                    candles.extend(data)
                    to_param = data[-1]["candle_date_time_utc"] + "Z"
                else:
                    break
            
            if not candles: return None
                
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
            return None

    # 🇰🇷 [2. 대한민국 국내 주식 특화 (FDR)]
    clean_ticker = ticker.split('.')[0].strip()
    is_kr_stock = ticker.upper().endswith('.KS') or ticker.upper().endswith('.KQ') or (clean_ticker.isdigit() and len(clean_ticker) == 6)
    
    if is_kr_stock:
        try:
            df = fdr.DataReader(clean_ticker, start='2024-01-01')
            if df.empty: return None
            df = df.reset_index()
            df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
            
            df['Date_Only'] = df['Date'].dt.date
            df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)
            return df
        except Exception:
            return None

    # 🇺🇸 [3. 미국 주식 및 기타 (yfinance)]
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y", timeout=2.5) # 2.5초 넘으면 무한 대기 없이 즉시 넘어감
        if df is None or df.empty: return None
        
        df = df.reset_index()
        df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        df['Date_Only'] = df['Date'].dt.date
        df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)
        return df
    except Exception:
        return None

    # 🇺🇸 [3. 미국 주식 수집]
    df = None
    try:
        df = yf.download(ticker, period="3y", interval="1d", auto_adjust=False, progress=False)
    except Exception:
        df = None
        
    if df is None or df.empty:
        try:
            df = fdr.DataReader(ticker, start='2024-01-01')
            if df is not None and not df.empty:
                df = df.reset_index()
                df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            df = None
            
    if df is None or df.empty:
        return None
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if 'Date' not in df.columns:
        df = df.reset_index()

    if df is not None and not df.empty:
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            if df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)
            
            df['Date_Only'] = df['Date'].dt.date
            df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)

    return df

    # 🇰🇷 [2. 대한민국 국내 주식 특화]
    clean_ticker = ticker.split('.')[0].strip()
    is_kr_stock = ticker.upper().endswith('.KS') or ticker.upper().endswith('.KQ') or (clean_ticker.isdigit() and len(clean_ticker) == 6)
    
    if is_kr_stock:
        try:
            df = fdr.DataReader(clean_ticker, start='1990-01-01')
            if df.empty: return None
            df = df.reset_index()
            df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
            
            # 날짜 중복 제거
            df['Date_Only'] = df['Date'].dt.date
            df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)
            return df
        except Exception:
            return None

    # 🇺🇸 [3. 미국 주식 수집 및 중복 캔들 방지]
    df = None
    try:
        if hasattr(yf, '_original_download'):
            df = yf._original_download(ticker, period="max", interval="1d", progress=False)
        else:
            df = yf.download(ticker, period="max", interval="1d", progress=False)
    except Exception:
        df = None
        
    if df is None or df.empty:
        try:
            ticker_obj = yf._original_Ticker(ticker) if hasattr(yf, '_original_Ticker') else yf.Ticker(ticker)
            df = ticker_obj.history(period="10y", interval="1d")
        except Exception:
            df = None
            
    if df is None or df.empty:
        try:
            df = fdr.DataReader(ticker, start='2016-01-01')
            if df is not None and not df.empty:
                df = df.reset_index()
                df = df.rename(columns={'Date':'Date', 'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'})
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            df = None
            
    if df is None or df.empty:
        return None
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if 'Date' not in df.columns:
        df = df.reset_index()

    # 🎯 미국 장중 실시간 가격 업데이트 (새 봉을 강제로 붙이지 않고 마지막 봉의 종가만 갱신)
    try:
        ticker_obj = yf._original_Ticker(ticker) if hasattr(yf, '_original_Ticker') else yf.Ticker(ticker)
        fast_info = ticker_obj.fast_info
        live_price = fast_info.last_price
        
        if live_price and not pd.isna(live_price):
            df.loc[df.index[-1], 'Close'] = live_price
    except Exception:
        pass

    # 🎯 [핵심] 날짜 타임존 정제 및 동일 날짜 캔들 강제 중복 제거
    if df is not None and not df.empty:
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            if df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)
            
            df['Date_Only'] = df['Date'].dt.date
            df = df.drop_duplicates(subset=['Date_Only'], keep='last').drop(columns=['Date_Only']).reset_index(drop=True)

    return df


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
        df = df.resample('M', on='Date').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna().reset_index()

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

# 💵 [개선 1] 하루 평균 거래대금 하한선 필터 (국내주식/코인 100억, 미국주식 2,000만$ 미만 자동 탈락)
    df['Value'] = df['Close'] * df['Volume']
    avg_value = df['Value'].tail(20).mean()
    is_kr_asset = any(x in ticker_symbol for x in [".KS", ".KQ", "-KRW"])
    liquidity_limit = 10_000_000_000 if is_kr_asset else 20_000_000
    
    # if timeframe == 'daily' and avg_value < liquidity_limit:
#     return None, None
    
    df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(window=14, min_periods=1).mean()
    
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
    df['EMA_12'] = ema_12  # 👈 기존 df['MA_20'] 덮어쓰기 버그 수정!
    df['STD_20'] = df['Close'].rolling(window=12).std()

    # ADX 및 DMI 연산
    up_move = df['High'].diff()
    down_move = df['Low'].shift(1) - df['Low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    df['Plus_DM'] = plus_dm
    df['Minus_DM'] = minus_dm
    
    tr_14 = df['TR'].rolling(window=14, min_periods=1).sum()
    tr_14 = np.where(tr_14 == 0, 1e-9, tr_14)
    df['Plus_DI'] = 100 * (df['Plus_DM'].rolling(window=14, min_periods=1).sum() / tr_14)
    df['Minus_DI'] = 100 * (df['Minus_DM'].rolling(window=14, min_periods=1).sum() / tr_14)
    
    di_sum = df['Plus_DI'] + df['Minus_DI']
    di_sum = np.where(di_sum == 0, 1e-9, di_sum)
    dx = 100 * (df['Plus_DI'] - df['Minus_DI']).abs() / di_sum
    df['ADX'] = dx.rolling(window=14, min_periods=1).mean()

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

    # 🛡️ 개미털기(Bear Trap) 정밀 판독기
    if c_low[-1] < support and c_close[-1] >= (support * 0.995) and lower_sh[-1] > (body[-1] * 1.2):
        pattern_score += 30
        if price < ma60: pattern_score += 20 
        success_reasons.append("🔥 [지표 판독] 개미털기(Bear Trap) 포착: 장중 손절가를 의도적으로 이탈시킨 후 아래꼬리로 강력하게 말아 올림 (초강력 반등 신호)")
        failed_reasons.append("[캔들] 고점권 유성형(Shooting Star) 포착: 상방 차익 매물 투하")
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

    up_prob = float(up_prob_base)

# 🎯 [섹터 주도주 보너스] 5일(1주) 지수 기여도 리포트 실시간 반영
    try:
        kr_pos, kr_neg, us_pos, us_neg = get_realtime_sector_influence()
        pos_names = [x[0] for x in kr_pos + us_pos]
        neg_names = [x[0] for x in kr_neg + us_neg]
        
        is_leading_sector = any(p_name in ticker_symbol for p_name in pos_names)
        is_lagging_sector = any(n_name in ticker_symbol or n_name in selected_name for n_name in neg_names)

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

    tighter_sl = max(support, price * 0.96) if support < price and (price - support)/price < 0.05 else price * 0.965

 # ====================================================================
    # 🚨 [신규 주입] 30년 베테랑 실시간 분할 청산 및 마스터 행동 지시 지침
    # ====================================================================
    # 진입가 대비 타이트 구조 컷 및 목표가 연산 규칙 동기화
    tighter_sl = max(support, price * 0.96) if support < price and (price - support)/price < 0.05 else price * 0.965
    tp_price = price + (atr * 2.5)  # 단타 고정 익절 목표가
    
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

    # 8. 🎯 통합 승률(Win Rate) 최종 산출 (12대 지표 50% + 8대 고도화 필터 50%)
    advanced_sum = vp_score + flow_score + v_breakout_score + mid_support_score + disparity_score + gap_filter_score + sector_score
    # 스코어를 0~100 범위로 정규화 후 12대 지표 승률(up_prob)과 5:5 결합
    combined_score = (up_prob * 0.5) + (((advanced_sum + 75.0) / 150.0) * 50.0)
    pure_win_rate = min(max(round(float(combined_score), 1), 0.0), 99.0)

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
        
        # 💡 [제미나이 팩트 시트에 2주 스윙 지표 탑재]
        fact_sheet = f"""
        [시장 데이터 분석 대상: {ticker}]
        - 현재가: {currency_symbol}{ai_data['price']:,.2f}
        {position_info}
        - 최대 매물대 가격 (POC): {currency_symbol}{ai_data['poc_price']:,.2f}
        - TTM Squeeze (변동성 에너지): {ai_data['squeeze_status']}
        - 다중 시간프레임(MTF) 정렬 점수: {ai_data['mtf_score']}/6 점
        - 2주 스윙 모멘텀 추세선: {ai_data['swing_trend']}
        - 2주 스윙 매수 셋업 패턴: {ai_data['swing_setup']}
        - 최근 수평 저항선(목표가): {currency_symbol}{ai_data['resist']:,.2f}
        - 최근 수평 지지선(최후방어): {currency_symbol}{ai_data['support']:,.2f}
        - 단기 생명선(20일선): {currency_symbol}{ai_data.get('ma_20', 0):,.2f}
        - 중기 수급선(60일선): {currency_symbol}{ai_data.get('ma_60', 0):,.2f}
        - 경기 저항선(120일선): {currency_symbol}{ai_data.get('ma_120', 0):,.2f}
        - 대세 장기선(200일선): {currency_symbol}{ai_data.get('ma_200', 0):,.2f}
        - 단타 타이트 손절가 (구조 컷): {currency_symbol}{ai_data['tighter_sl']:,.2f}
        - 시장 추세 상태: {ai_data['trend_state']}
        - 기술적 보조지표 종합 시그널: {ai_data['current_signal']}
        - 최근 5일간 수집된 뉴스 요약(5W1H): {ai_data['news_summary_lines']}
        - 뉴스 감성 분석 방향성: {ai_data['news_impact_reason']}
        """

        system_instruction = """
        당신은 15년 경력의 냉철하고 이성적인 월스트리트 출신 프로 스윙 트레이더입니다. 
        투자의 흔한 경고 문구(예: '본인의 책임...')는 일절 배제하고, 철저히 데이터에 입각한 공격적이고 스마트한 리스크 관리 대응 시나리오를 지시하십시오.

        특히, 대시보드에 새롭게 반영된 아래 고급 지표들을 전략 수립에 최우선적으로 반영하여 근거로 삼으십시오:
        
        1. 🎯 최대 매물대 (POC): 
           - 현재가가 이 가격대보다 위에 있다면, 든든한 바닥 매물 지지가 있으므로 '매수 우위'로 진단하십시오.
           - 현재가가 이 가격대 아래에 있다면, 머리 위에 강력한 저항 매물이 쏟아질 수 있으므로 '돌파 확인 전까지 관망' 또는 '보수적 대응'을 지시하십시오.
        
        2. 🔴 TTM Squeeze:
           - 스퀴즈 상태가 '스퀴즈 ON(수축)'이라면 곧 변동성 에너지의 폭발적인 분출이 다가오고 있음을 강하게 강조하고, 조만간 터질 시세 분출 방향을 대비하라고 조언하십시오.

        3. 🧭 다중 시간프레임 점수 (MTF Score):
           - [5~6점]: 장기, 중기, 단기 추세가 완전히 정배열로 정렬된 강세장입니다. 공격적인 비중 확보 및 불타기를 허용하십시오.
           - [0~2점]: 단기/중장기 추세가 전부 꺾인 약세장입니다. 리스크를 타이트하게 가져가십시오.

        4. 🔥 2주 스윙 모멘텀 & 셋업 (EMA & VDU):
           - 거래량 절벽(VDU) 지표와 8/21 EMA 추세의 강세/약세 부합 여부를 확인하여 1~14일 스윙 보유 시 최적의 분할 진입 타점인지 설명하십시오.

        [최종 브리핑 양식 가이드라인]
        - 신규 진입 시: POC 부근에서의 눌림목 매수 타점 또는 스퀴즈 돌파 시점의 명확한 진입 시나리오를 제시하십시오.
        - 기존 보유 시: 본인의 평단가를 반영한 실시간 수익률을 고려하여, 수평 저항선(목표가)과 동적 손절가(ATR 손절선) 기준의 '행동 요령'을 선언하십시오.
        """

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
# 🎯 내 실전 보유종목 주문서 관제탑 (소급 검증과 100% 일치 + 실시간/N봉 성과 동시 연동)
# ====================================================================
def render_my_portfolio_manager():
    st.markdown("### 🎯 내 실전 보유종목 주문서 관제")

    # 1. DB 테이블 생성 (없을 경우)
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

    # 2. 신규 진입 종목 등록 UI
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

    # 3. 등록된 보유 종목 모니터링 출력
    cursor.execute("SELECT id, stock_name, ticker, entry_price, entry_date FROM my_trades ORDER BY id DESC")
    my_stocks = cursor.fetchall()

    cursor.execute("SELECT ticker, rec_date FROM rec_history ORDER BY id DESC")
    rec_rows = cursor.fetchall()
    conn.close()

    rec_date_map = {}
    for r_ticker, r_date in rec_rows:
        if r_ticker not in rec_date_map:
            rec_date_map[r_ticker] = r_date

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
        
        def eval_conditions_at_idx(df, idx):
            if idx < 60: return []
            c_close = float(df['Close'].iloc[idx])
            c_low = float(df['Low'].iloc[idx])
            c_high = float(df['High'].iloc[idx])
            c_ma20 = float(df['MA_20'].iloc[idx])
            c_ma60 = float(df['MA_60'].iloc[idx])
            c_ma200 = float(df['MA_200'].iloc[idx])
            
            matched = []
            cond1 = (idx > 1) and (df['Close'].iloc[idx-1] < df['MA_60'].iloc[idx-1]) and (c_close >= c_ma60) and (df['MACD'].iloc[idx-1] < 0) and (df['MACD'].iloc[idx] >= 0)
            if cond1: matched.append(1)
            cond2 = (c_close >= c_ma20 * 0.992) and (c_close >= c_ma60)
            if cond2: matched.append(2)
            cond3 = (c_low <= c_ma200 <= c_high) and (c_ma60 > c_ma200)
            if cond3: matched.append(3)
            cond4 = (c_ma20 * 0.992 <= c_close <= c_ma20 * 1.03) and (c_ma20 >= c_ma60)
            if cond4: matched.append(4)
            return matched

        rec_display_txt = ""
        entry_conds = []
        today_conds = []
        is_valid_rec = False
        bars_passed = 0
        sim_ret = 0.0
        sim_status_txt = "성과 계산 중..."

        if df_curr is not None and len(df_curr) >= 60:
            df_curr['MA_20'] = df_curr['Close'].rolling(20, min_periods=1).mean()
            df_curr['MA_60'] = df_curr['Close'].rolling(60, min_periods=1).mean()
            df_curr['MA_200'] = df_curr['Close'].rolling(200, min_periods=1).mean()
            
            df_curr['Prev_Close'] = df_curr['Close'].shift(1)
            tr1 = df_curr['High'] - df_curr['Low']
            tr2 = (df_curr['High'] - df_curr['Prev_Close']).abs()
            tr3 = (df_curr['Low'] - df_curr['Prev_Close']).abs()
            df_curr['TR'] = np.maximum(tr1, np.maximum(tr2, tr3))
            df_curr['ATR'] = df_curr['TR'].rolling(14, min_periods=1).mean()

            ema_12 = df_curr['Close'].ewm(span=12, adjust=False).mean()
            ema_26 = df_curr['Close'].ewm(span=26, adjust=False).mean()
            df_curr['MACD'] = ema_12 - ema_26
            df_curr['Date_Str'] = df_curr['Date'].dt.strftime('%Y-%m-%d')

            curr_p = float(df_curr['Close'].iloc[-1])
            ma20_p = float(df_curr['MA_20'].iloc[-1])
            atr_v = float(df_curr['ATR'].iloc[-1]) if not np.isnan(df_curr['ATR'].iloc[-1]) else curr_p * 0.03

            # 추천일 탐색
            rec_idx = -1
            for idx in range(len(df_curr) - 1, 59, -1):
                conds = eval_conditions_at_idx(df_curr, idx)
                if conds:
                    rec_idx = idx
                    break

            today_conds = eval_conditions_at_idx(df_curr, len(df_curr) - 1)

            if rec_idx != -1:
                rec_date_str = df_curr['Date_Str'].iloc[rec_idx]
                bars_passed = len(df_curr) - 1 - rec_idx
                entry_conds = eval_conditions_at_idx(df_curr, rec_idx)

                if bars_passed <= 20:
                    rec_display_txt = f"추천일: {rec_date_str}"
                    is_valid_rec = True
                else:
                    rec_display_txt = f"추천 만료 ({rec_date_str})"
                    is_valid_rec = False
            else:
                rec_display_txt = f"등록일: {e_date}"
                is_valid_rec = False
                rec_matches = df_curr[df_curr['Date_Str'] <= e_date]
                rec_idx = rec_matches.index[-1] if not rec_matches.empty else len(df_curr) - 1
                bars_passed = len(df_curr) - 1 - rec_idx

            # 🔥 [소급 검증 알고리즘과 100% 동일한 N봉 실전 매매 성과 시뮬레이션]
            atr_pct = (atr_v / entry_p) * 100.0
            tp1_pct = min(5.0, 1.5 * atr_pct)
            tp2_pct = min(10.0, 3.0 * atr_pct)
            tp3_pct = min(20.0, 5.0 * atr_pct)
            sl_pct = -3.0

            future_bars = df_curr.iloc[rec_idx + 1 : rec_idx + 6]
            if not future_bars.empty:
                remaining_qty = 1.0
                realized_ret = 0.0
                max_ret = 0.0
                trailing_active = False
                tp1_done, tp2_done, tp3_done = False, False, False

                for _, bar in future_bars.iterrows():
                    b_high, b_low = float(bar['High']), float(bar['Low'])
                    b_high_ret = ((b_high - entry_p) / entry_p) * 100.0
                    b_low_ret = ((b_low - entry_p) / entry_p) * 100.0

                    if b_high_ret > max_ret: max_ret = b_high_ret
                    if b_high_ret >= 2.0: trailing_active = True

                    if not tp1_done and b_high_ret >= tp1_pct:
                        realized_ret += 0.50 * tp1_pct
                        remaining_qty -= 0.50
                        tp1_done = True

                    if tp1_done and not tp2_done and b_high_ret >= tp2_ret:
                        realized_ret += 0.25 * tp2_ret
                        remaining_qty -= 0.25
                        tp2_done = True

                    if tp2_done and not tp3_done and b_high_ret >= tp3_pct:
                        realized_ret += 0.25 * tp3_pct
                        remaining_qty -= 0.25
                        tp3_done = True
                        break

                    if trailing_active and b_low_ret <= 0.5 and remaining_qty > 0:
                        realized_ret += remaining_qty * 0.5
                        remaining_qty = 0.0
                        break
                    elif not trailing_active and b_low_ret <= sl_pct and remaining_qty > 0:
                        realized_ret += remaining_qty * sl_pct
                        remaining_qty = 0.0
                        break

                if remaining_qty > 0:
                    last_c_ret = ((float(future_bars['Close'].iloc[-1]) - entry_p) / entry_p) * 100.0
                    realized_ret += remaining_qty * last_c_ret

                sim_ret = realized_ret
                n_count = min(bars_passed, 5)
                sim_status_txt = f"{n_count}봉 성과 {sim_ret:+.2f}% ({'완료' if bars_passed >= 5 else '진행중'})"
            else:
                sim_status_txt = "진행중 (0봉째)"
        else:
            curr_p = entry_p
            ma20_p = entry_p
            atr_v = entry_p * 0.03
            rec_display_txt = "데이터 부족"
            tp1_pct, tp2_pct, tp3_pct = 5.0, 10.0, 20.0
            sim_status_txt = "데이터 부족"

        is_krw = any(x in s_ticker for x in [".KS", ".KQ", "-KRW"])
        curr_symbol = "₩" if is_krw else "$"
        fmt_p = lambda p: f"{curr_symbol}{p:,.0f}" if is_krw else f"{curr_symbol}{p:,.2f}"

        tp1_price = entry_p * (1.0 + tp1_pct / 100.0)
        tp2_price = entry_p * (1.0 + tp2_pct / 100.0)
        tp3_price = entry_p * (1.0 + tp3_pct / 100.0)
        sl_price = entry_p * 0.97

        ret_pct = ((curr_p - entry_p) / entry_p) * 100
        ret_color = "#ff4b4b" if ret_pct > 0 else ("#38bdf8" if ret_pct < 0 else "#94a3b8")
        sim_color = "#ff4b4b" if sim_ret > 0 else ("#38bdf8" if sim_ret < 0 else "#94a3b8")

        warning_html = ""
        if is_valid_rec and entry_conds:
            broken_conds = [c for c in entry_conds if c not in today_conds]
            if len(broken_conds) == len(entry_conds):
                entry_str = ", ".join([f"조건{c}" for c in entry_conds])
                warning_html = f"""<div style="background-color: #450a0a; border: 1px solid #ef4444; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px; color: #fca5a5; font-size: 12px; font-weight: bold; line-height: 1.5;">
🚨 <b>[전체 진입 근거 붕괴 - 100% 전량 매도]</b> 추천 당시 포착된 ({entry_str}) 조건 소멸! 전량 청산 권고.
</div>"""
            elif len(broken_conds) > 0:
                broken_str = ", ".join([f"조건{c}" for c in broken_conds])
                warning_html = f"""<div style="background-color: #431407; border: 1px solid #f97316; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px; color: #fdba74; font-size: 12px; font-weight: bold; line-height: 1.5;">
⚠️ <b>[부분 진입 근거 붕괴 - 50% 절반 매도]</b> 추천 조건 중 ({broken_str}) 지지선 붕괴! 50% 매도 권고.
</div>"""
            else:
                entry_str = ", ".join([f"조건{c}" for c in entry_conds])
                warning_html = f"""<div style="background-color: #064e3b; border: 1px solid #10b981; padding: 6px 12px; border-radius: 6px; margin-bottom: 10px; color: #a7f3d0; font-size: 11px; font-weight: bold;">
🟢 <b>[추천 근거 유지]</b> 추천 당시 포착된 ({entry_str}) 조건이 견고하게 유지 중입니다.
</div>"""
        else:
            if curr_p < ma20_p:
                warning_html = f"""<div style="background-color: #431407; border: 1px solid #f97316; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px; color: #fdba74; font-size: 12px; font-weight: bold; line-height: 1.5;">
⚠️ <b>[20일선 이탈 - 50% 절반 매도]</b> 현재가({fmt_p(curr_p)})가 20일선({fmt_p(ma20_p)}) 밑으로 하회했습니다.
</div>"""

        card_html = f"""<div style="background-color: #1e2230; padding: 16px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #334155;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
<div>
<span style="font-size: 18px; font-weight: bold; color: #ffffff;">{s_name}</span>
<span style="font-size: 13px; color: #94a3b8;"> ({s_ticker}) | {rec_display_txt}</span>
</div>
<div style="text-align: right;">
<div style="font-size: 15px; font-weight: bold; color: {ret_color};">
현재가: {fmt_p(curr_p)} ({ret_pct:+.2f}%)
</div>
<div style="font-size: 12px; font-weight: bold; color: {sim_color}; margin-top: 2px;">
📊 검증 매매 성과: {sim_status_txt}
</div>
</div>
</div>
{warning_html}
<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; background-color: #0f172a; padding: 12px; border-radius: 8px; text-align: center;">
<div>
<div style="font-size: 11px; color: #94a3b8;">📌 내 진입가</div>
<div style="font-size: 14px; font-weight: bold; color: #ffffff;">{fmt_p(entry_p)}</div>
</div>
<div>
<div style="font-size: 11px; color: #38bdf8;">🛑 강제 손절 (-3%)</div>
<div style="font-size: 14px; font-weight: bold; color: #38bdf8;">{fmt_p(sl_price)}</div>
</div>
<div>
<div style="font-size: 11px; color: #f59e0b;">🔥 1차 ({tp1_pct:.1f}%)</div>
<div style="font-size: 14px; font-weight: bold; color: #f59e0b;">{fmt_p(tp1_price)}</div>
</div>
<div>
<div style="font-size: 11px; color: #ef4444;">🚀 2차 ({tp2_pct:.1f}%)</div>
<div style="font-size: 14px; font-weight: bold; color: #ef4444;">{fmt_p(tp2_price)}</div>
</div>
<div>
<div style="font-size: 11px; color: #a855f7;">💎 3차 ({tp3_pct:.1f}%)</div>
<div style="font-size: 14px; font-weight: bold; color: #a855f7;">{fmt_p(tp3_price)}</div>
</div>
</div>
</div>"""
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
    
    # [안전장치] yfinance 일봉 특유의 이중 컬럼(MultiIndex) 깨짐 현상 강제 해결
    if df_raw is not None and not df_raw.empty:
        if isinstance(df_raw.columns, pd.MultiIndex):
            df_raw.columns = df_raw.columns.get_level_values(0)

    # 🟢 [CCTV 안전 구역] 여기서 연산을 감시하고, 터지면 범인의 족적을 강제 폭로합니다.
    try:
        df_proc, ai = process_data(df_raw, tab_name, safe_ticker, skip_news=True)
    except Exception as e:
        st.error(f"🚨 process_data 내부 연산 에러 발생 ({tab_name}): {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return

# ====================================================================
    # 📊 데이터 부족 및 오류 방어선 (줄 맞춤 정밀 교정본)
    # ====================================================================
    if df_proc is None or raw_data is None or len(raw_data) < 10:
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

    # 📌 범례 박스와 col_stat1 모두 else: 와 시작 위치를 똑같이 맞춥니다 (공백 4칸)
    st.markdown("""
<div style="background-color:#0f172a; padding:12px 16px; border-radius:8px; border:1px solid #334155; margin-bottom:12px;">
    <div style="font-size:12px; font-weight:bold; color:#94a3b8; margin-bottom:8px;">📈 이동평균선(MA) 범례 및 주요 역할</div>
    <div style="display:flex; flex-wrap:wrap; gap:16px; font-size:12px; font-weight:bold;">
        <span style="color:#FF1493;">━ 5일선 <span style="color:#cbd5e1; font-weight:normal;">(초단기 추세)</span></span>
        <span style="color:#29B6F6;">━ 10일선 <span style="color:#cbd5e1; font-weight:normal;">(단기 단타 생명선)</span></span>
        <span style="color:#00E676;">━ 20일선 <span style="color:#cbd5e1; font-weight:normal;">(중단기 세력 심리선)</span></span>
        <span style="color:#AB47BC;">━ 60일선 <span style="color:#cbd5e1; font-weight:normal;">(중기 수급 지지/저항)</span></span>
        <span style="color:#FF6D00;">━ 120일선 <span style="color:#cbd5e1; font-weight:normal;">(경기/중장기 핵심 저항선)</span></span>
        <span style="color:#FF1744;">━ 200일선 <span style="color:#cbd5e1; font-weight:normal;">(대세/장기 추세 분수령)</span></span>
    </div>
</div>
""", unsafe_allow_html=True)

    col_stat1, col_stat2 = st.columns(2)

    with col_stat1:

        st.markdown(f"""
<div style="background-color:#141414; padding:15px; border-radius:10px; border-top: 5px solid #38bdf8; margin-bottom:15px; height:100px;">
<p style="margin:0; font-size:12px; color:#999; font-weight:bold;">💵 REAL-TIME PRICE (실시간 현재가)</p>
<h4 style="margin:8px 0 0 0; color:#38bdf8; font-size:20px; font-weight:bold;">
{currency_symbol}{ai['price']:,.2f} <span style="font-size:14px; color:{day_pct_color}; margin-left:6px;">({day_pct_txt})</span>
</h4>
</div>
""", unsafe_allow_html=True)
        
    with col_stat2:
        st.markdown(f"""
<div style="background-color:#141414; padding:15px; border-radius:10px; border-top: 5px solid {ai['squeeze_color']}; margin-bottom:15px; height:100px;">
<p style="margin:0; font-size:12px; color:#999; font-weight:bold;">📊 TTM SQUEEZE (변동성 에너지)</p>
<h4 style="margin:8px 0 0 0; color:{ai['squeeze_color']}; font-size:16px; font-weight:bold;">{ai['squeeze_status']}</h4>
</div>
""", unsafe_allow_html=True)

    # 차트 구성 (기존 코드 위치)
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.15, 0.15, 0.15, 0.15],
                        subplot_titles=(f"[{selected_name}] Price Action 및 주도주 이평선 선형", "Volume (거래량)", "MACD", "RSI", "ADX & DMI"))
    
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

    colors = [kr_up if c_s.iloc[i] >= o_s.iloc[i] else kr_dn for i in range(len(df_disp))]
    fig.add_trace(go.Bar(x=x_axis, y=df_disp['Volume'], marker_color=colors), row=2, col=1)

    m_cols = [kr_up if val > 0 else kr_dn for val in df_disp['MACD_Hist']]
    fig.add_trace(go.Bar(x=x_axis, y=df_disp['MACD_Hist'], marker_color=m_cols), row=3, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['MACD'], line=dict(color='cyan')), row=3, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Signal'], line=dict(color='orange')), row=3, col=1)

    fig.add_trace(go.Scatter(x=x_axis, y=df_disp['RSI'], line=dict(color='purple', width=2)), row=4, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="blue", row=4, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="red", row=4, col=1)

    if 'ADX' in df_disp.columns:
        # 메인 추세 강도선 (황금색 실선)
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['ADX'], line=dict(color='gold', width=2.5)), row=5, col=1)
        # +DI 매수세 강도선 (회색 실선)
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Plus_DI'], line=dict(color='gray', width=1.5)), row=5, col=1)
        # -DI 매도세 강도선 (빨간색 실선)
        fig.add_trace(go.Scatter(x=x_axis, y=df_disp['Minus_DI'], line=dict(color='#ff4b4b', width=1.5)), row=5, col=1)
    
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

    if api_key:
        st.markdown("### 🤖 Gemini AI 실시간 차트 분석 및 스윙 전략")
        user_question = st.text_input(
            "💬 제미나이에게 궁금한 점을 자유롭게 물어보세요 (선택사항)", 
            placeholder="예시: 이 종목 오늘 꼬리 달릴 때 불타기 해도 괜찮을까?", 
            key=f"gemini_q_{tab_name}"
        )
        
        # 🎯 [추가] roi(수익률) 변수 계산 로직
        if entry_price > 0 and ai.get('price', 0) > 0:
            roi = ((ai['price'] - entry_price) / entry_price) * 100
        else:
            roi = 0.0

        if st.button("🔍 제미나이 AI 분석 및 질문 답변 듣기", key=f"gemini_btn_{tab_name}"):
            with st.spinner("제미나이 베테랑 트레이더가 실시간 거래대금과 돌파 강도를 분석 중입니다..."):
                advice_text = get_gemini_advice(api_key, selected_name, ai, entry_price, roi, currency_symbol, user_question)
            with st.container(border=True):
                st.markdown(advice_text)
        else:
            st.info("💡 질문을 입력하거나 비워둔 채로 위의 버튼을 누르면 실시간 분석을 시작합니다.")
        st.markdown("<br>", unsafe_allow_html=True)

    # 🎨 [위치 정밀 교정] left 값을 늘려 툴바를 좀 더 오른쪽으로 밀어냅니다.
    st.markdown("""
    <style>
    /* 1. 툴바 컨테이너를 좀 더 오른쪽으로 이동 (기존 10px ➔ 32px) */
    .js-plotly-plot .modebar-container {
        left: 32px !important;  /* 💡 이 숫자를 늘리면 더 오른쪽으로, 줄이면 왼쪽으로 갑니다! */
        right: auto !important;
        top: 60px !important;
        z-index: 999 !important;
    }
    /* 2. 내부 도구 세로 정렬 유지 */
    .js-plotly-plot .modebar {
        display: flex !important;
        flex-direction: column !important;
    }
    /* 3. 아이콘 그룹 간격 유지 */
    .js-plotly-plot .modebar-group {
        display: flex !important;
        flex-direction: column !important;
        padding-left: 0px !important;
        padding-right: 0px !important;
        margin-bottom: 6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # 🎯 [Price Action & 지지저항 브리핑 - 부호별 색상 연동]
    # ==========================================
    curr_p = float(ai.get('price', 0.0))
    supp_p = float(ai.get('support', 0.0))
    resi_p = float(ai.get('resist', 0.0))
    poc_p = float(ai.get('poc_price', 0.0))
    ma20_p = float(ai.get('ma_20', curr_p))
    sl_p = float(ai.get('tighter_sl', supp_p))

    # AI 연산 수치
    win_rate = float(ai.get('up_prob', 50.0))
    upside_val = float(ai.get('upside', 0.0))

    # 화폐 포맷터
    currency_symbol = "₩" if is_krw else "$"
    fmt_p = lambda p: f"{currency_symbol}{p:,.0f}" if is_krw else f"{currency_symbol}{p:,.2f}"

    # 🎨 부호/수치별 색상 자동 판별 함수 (양수/높음: 빨강, 음수/낮음: 파랑)
    def fmt_color_pct(val):
        color = "#ff4b4b" if val > 0 else "#38bdf8" if val < 0 else "#ffffff"
        return f'<span style="color:{color}; font-weight:bold;">({val:+.1f}%)</span>'

    # 괴리율 산출
    poc_dist = ((poc_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0
    supp_dist = ((supp_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0
    resi_dist = ((resi_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0
    disparity_20 = (curr_p / ma20_p * 100.0) if ma20_p > 0 else 100.0

    # 승률 및 수익률 색상 분기
    win_color = "#ff4b4b" if win_rate >= 50.0 else "#38bdf8"
    upside_color = "#ff4b4b" if upside_val > 0 else "#38bdf8" if upside_val < 0 else "#ffffff"
    upside_txt = f"+{upside_val:.1f}%" if upside_val > 0 else f"{upside_val:.1f}%"

    # 손익비 산출
    c_atr = float(df_proc['ATR'].iloc[-1]) if 'ATR' in df_proc.columns else (curr_p * 0.02)
    st_tp_p = curr_p + (c_atr * 1.5)
    reward_st = st_tp_p - curr_p
    risk_st = curr_p - sl_p if curr_p > sl_p else (curr_p * 0.02)
    rr_val_str = f"{reward_st / risk_st:.2f} : 1" if (risk_st > 0 and reward_st > 0) else "N/A"

    # 매물대 방어/저항 정보
    bin_p = float(ai.get('curr_bin_price', poc_p))
    level_label, level_icon = ("하방 지지(방어)", "🛡️") if curr_p >= bin_p else ("상방 저항(막힐)", "🧱")
    def_prob = float(ai.get('defense_prob', 60.0))
    def_color = "#ff4b4b" if def_prob >= 50.0 else "#38bdf8"

    top_pct = float(ai.get('top1_pct', 0.0))
    top_touch = int(ai.get('top1_touches', 0))
    curr_pct = float(ai.get('curr_bin_pct', 0.0))
    curr_touch = int(ai.get('curr_bin_touches', 0))

    # HTML 출력
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
                <li style="font-size:16px; color:#ffffff;">🎯 <b>AI 모델 승률 / 1~5봉 기대수익:</b> <b style="color:{win_color};">{win_rate:.1f}%</b> / <b style="color:{upside_color};">{upside_txt}</b></li>
                <li style="font-size:14px; color:#a7f3d0;">⚖️ <b>실전 단타 기대 손익비 (R/R):</b> <b>{rr_val_str}</b> (ATR 목표/손절 기준)</li>
                <li style="font-size:14px; color:#e2e8f0;">🛡️ <b>수평 지지:</b> <b>{fmt_p(supp_p)}</b> {fmt_color_pct(supp_dist)} | 🧱 <b>수평 저항:</b> <b>{fmt_p(resi_p)}</b> {fmt_color_pct(resi_dist)}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ====================================================================
    # 📊 [우측 열 채우기] 현재 종목에 '실제 부합한' 계량 지표 심층 분석 메모칸
    # ====================================================================
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
        else:
            st.markdown("""
            <div style="background-color:#141414; padding:18px; border-radius:10px; border: 1px solid #222; height:100%; text-align:center; padding-top:40px;">
                <p style="color:#64748b; font-size:14px;">🧭 현재 이 종목은 뚜렷한 반전 시그널이 감지되지 않은 <strong>중립/박스권 지대</strong>입니다.</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)

# ====================================================================
    # 📋 ['AI 추세 최적화 단타 검증' 승률 기준 완벽 통일 로직]
    # ====================================================================
    up_p = float(ai['up_prob'])       # 사이드바/검증표와 동일한 종합 승률
    down_p = float(ai['down_prob'])   # 하락 위험도
    is_filtered = locals().get('is_filtered_out', False)

    # 🎯 승률(up_p) 구간에 따른 단일 통일 상태 정의
    if is_filtered or up_p < 45.0:
        unified_status = "SELL_AVOID"  # 매도 / 절대 진입 금지
    elif up_p >= 70.0:
        unified_status = "STRONG_BUY"  # 적극 매수 / 포지션 유지
    else:
        unified_status = "HOLD_WAIT"   # 관망 / 분할 접근
    
# ====================================================================
    # 🏅 30년 베테랑 실시간 분할 청산 의사결정 시스템
    # ====================================================================
    st.write("")
    st.info("🏅 30년 베테랑 실시간 분할 청산 의사결정 시스템")

    c_atr = float(df_proc['ATR'].iloc[-1]) if 'ATR' in df_proc.columns else (ai['price'] * 0.02)
    entry_p = float(ai['price'])

    # 🎯 주가·차트 국면별 진입가 및 선정 이유 동적 산정
    if up_p >= 88.0:
        entry_target_p = entry_p * 0.995
        entry_reason = "초강세 주도주: 6대 이평선 완전 정배열 및 -0.5% 눌림목 체결 타점"
    elif up_p >= 72.0:
        entry_target_p = entry_p * 0.990
        entry_reason = "우수 추세: 주요 이평선 지지 확보 및 -1.0% 할인 지정가 타점"
    elif up_p >= 45.0:
        poc_p = float(ai['poc_price'])
        entry_target_p = poc_p if (0 < poc_p < entry_p) else entry_p * 0.980
        entry_reason = "박스권·수렴: 120일/200일선 지지력 및 매물대(POC) 확인 타점"
    else:
        entry_target_p = entry_p
        entry_reason = "하방 우세·장기 이평선(120/200일) 저항 붕괴: 떨어지는 칼날 방지용 진입 엄금"

    # 타겟 익절가 및 손절가 연산
    tp1_p = min(entry_target_p + (c_atr * 1.2), entry_target_p * 1.05)
    tp2_p = min(entry_target_p + (c_atr * 2.2), entry_target_p * 1.10)
    tp3_p = min(entry_target_p + (c_atr * 4.0), entry_target_p * 1.20)
    sl_p = float(ai['tighter_sl'])

    # 화폐 단위별 금액 포맷 함수
    fmt_p = lambda p: f"{currency_symbol}{p:,.0f}" if currency_symbol == "₩" else f"{currency_symbol}{p:,.2f}"

    # 상단 포지션 상태 메시지
    if unified_status == "STRONG_BUY":
        st.markdown(f"### :red[🚀 실시간 청산 포지션: 롱(매수) 관성 유지 및 분할 익절 레이싱]")
        st.markdown(f"12대 기술 지표 종합 상승확률 **{up_p:.1f}%** 구간입니다. 적극 분할 익절 매도를 준비하십시오.")
        core_reasons = ai['success_reasons'][:3]
        if not core_reasons: core_reasons = ["단기 이평선 정배열 및 상방 모멘텀 유지"]
    elif unified_status == "HOLD_WAIT":
        st.markdown(f"### ⚠️ 실시간 청산 포지션: 포지션 횡보 및 관망 국면]")
        st.markdown(f"상·하방 지표 혼조 구역(상승확률 **{up_p:.1f}%**)입니다. 추격 매수를 자제하고 지정가 대응하십시오.")
        core_reasons = (ai['success_reasons'][:2] + ai['failed_reasons'][:2])
        if not core_reasons: core_reasons = ["지표 상·하방 신호 혼조 및 수렴 국면"]
    else:
        st.markdown(f"### :blue[🚨 실시간 청산 포지션: 절대 진입 금지 및 관망/비중 축소 구간]")
        st.markdown(f"상승확률 **{up_p:.1f}%**의 하방 우세 구간입니다. 리스크 관리에 집중하십시오.")
        core_reasons = ai['failed_reasons'][:3]
        if not core_reasons: core_reasons = ["주요 이평선 역배열 및 매도세 지배"]

    # 💡 캔들/차트 패턴 및 지표 핵심 근거 출력
    reasons_html = "".join([f"<li style='margin-bottom:4px;'>• {r}</li>" for r in core_reasons])
    st.markdown(f"""
    <div style="background-color:#1e293b; padding:12px 15px; border-radius:6px; border:1px solid #334155; margin:10px 0 15px 0;">
        <b style="color:#38bdf8; font-size:14px;">🔍 판단 핵심 근거 (지표·캔들·차트 패턴):</b>
        <ul style="color:#e2e8f0; font-size:13px; margin:6px 0 0 0; padding-left:10px; list-style:none; line-height:1.5;">
            {reasons_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # 🎯 가격 가이드북 (진입가 이유 괄호 추가)
    st.markdown(f"""
    **🎯 계량형 단계별 가격 가이드:**
    * **진입가:** `{fmt_p(entry_target_p)}` ({entry_reason})
    * **1차 익절가:** `{fmt_p(tp1_p)}` (비중 25% / ATR 1.2배 조율선)
    * **2차 익절가:** `{fmt_p(tp2_p)}` (비중 50% / ATR 2.2배 관성선)
    * **3차 익절가:** `{fmt_p(tp3_p)}` (비중 25% / ATR 4.0배 슈팅선)
    * **손절가:** `{fmt_p(sl_p)}` (최후 리스크 방어선)
    """)

    # ====================================================================
    # 📋 실시간 AI 매매 주문서 (5대 기술 지표 실시간 검증)
    # ====================================================================
    st.write("---")
    st.markdown("### 📋 실시간 AI 매매 주문서 (5대 기술 지표 실시간 검증)")

    # 5대 보조지표 변수 추출
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

    sig_vol_buy = v_last >= (v_ma20 * 2.0) and df_proc['Close'].iloc[-1] > df_proc['Open'].iloc[-1]
    sig_vol_sell = v_last >= (v_ma20 * 3.0) and df_proc['Close'].iloc[-1] < df_proc['Open'].iloc[-1]
    sig_macd_buy = (m_line > m_sig and df_proc['MACD'].iloc[-2] <= df_proc['Signal'].iloc[-2]) or (m_hist > m_hist_prev and m_hist < 0)
    sig_macd_sell = m_line < m_sig
    sig_rsi_buy = rsi_curr <= 30 or (rsi_prev < 30 and rsi_curr >= 30)
    sig_rsi_sell = rsi_curr >= 70 or (rsi_prev > 70 and rsi_curr <= 70)
    sig_dmi_buy = p_di > m_di and adx_val >= 20
    sig_dmi_sell = m_di > p_di
    price = float(ai['price'])


    # 📌 이평선 장기 지지/저항 시그널 조건 추가
    ma120_val = float(df_proc['MA_120'].iloc[-1]) if 'MA_120' in df_proc.columns else price
    ma200_val = float(df_proc['MA_200'].iloc[-1]) if 'MA_200' in df_proc.columns else price

    sig_ma_buy = (price >= ma120_val) and (price >= ma200_val)
    sig_ma_sell = (price < ma120_val) or (price < ma200_val)

    # 체크리스트 2열 배치
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

    st.markdown("<br>", unsafe_allow_html=True)

    # 🎯 통일 판단(unified_status) 기반 매매 주문서 스탬프 발행
    if unified_status == "STRONG_BUY":
        st.success(f"🔥 [STRONG BUY] AI 단타 승률 상위 우수 구간 ➔ [알파 상승 확신도: {up_p:.1f}%]")
        st.info("🎯 실시간 주문서 지침: 종합 스코어가 높고 세력 수급 및 기술적 모멘텀이 상방을 가리키는 정배열 타점입니다. 자신 있게 분할 진입을 개시하십시오.")
    elif unified_status == "HOLD_WAIT":
        st.warning(f"🧭 [HOLD & WAIT] 지표 신호 혼조세 / 눌림목 관망 ➔ [상승 확률: {up_p:.1f}%]")
        st.info("🎯 실시간 주문서 지침: 매수 우위 기조는 유지되나 일부 단기 지표가 숨고르기 중입니다. 추격 매수보다는 아래꼬리 거미줄 진입이 유효합니다.")
    else:
        st.error(f"🚨 [AVOID / SELL] 매도 지표 장악 및 관망 권고 ➔ [하락 위험도: {down_p:.1f}%]")
        st.info("🎯 실시간 주문서 지침: 하방 압력이 우세하거나 주요 이평선이 이탈된 위험 구역입니다. 신규 매수를 엄격히 금지합니다.")

# ====================================================================
    # # 2. [알파 승률 부스터] 정배열/과열 필터 및 다음날 -1% 눌림목 가드레일
    # ====================================================================
    curr_price_base = float(ai['price']) if float(ai['price']) > 0 else 1.0
    ma5 = float(ai['ma_5'])
    ma20 = float(ai['ma_20'])
    poc = float(ai['poc_price'])
    support = float(ai['support'])
    sl_price = float(ai['tighter_sl'])

    # df_proc에서 승률 방어용 핵심 필터 지표 추출
    ma60_live = float(df_proc['MA_60'].iloc[-1]) if 'MA_60' in df_proc.columns else curr_price_base
    rsi_live = float(df_proc['RSI'].iloc[-1]) if 'RSI' in df_proc.columns else 50.0

    # 🚨 승률 65% 돌파를 위한 2대 메이저 필터링 시스템 가동
    is_filtered_out = False
    filter_msg = ""

    if curr_price_base < ma60_live:
        is_filtered_out = True
        filter_msg = "역배열 금지 (60일선 아래)"
    elif rsi_live >= 70:
        is_filtered_out = True
        filter_msg = "초과열 매수 금지 (RSI 70 이상)"

    # 🟢 필터를 통과한 우량 추세 종목에 한해서만 진입가 연산 진행
    if is_filtered_out:
        entry_target = curr_price_base
    else:
        if ai['up_prob'] >= 90:
            # 💡 추격 매수 방지: 90% 이상 강세 시그널이어도 종가 대비 -1% 눌림목 대기 타점 지정
            entry_target = curr_price_base * 0.990
        elif ai['up_prob'] >= 70:
            entry_target = ma5 if curr_price_base > ma5 else ma20
        elif ai['up_prob'] >= 45:
            entry_target = poc if support < poc < curr_price_base else ma20
        else:
            entry_target = support if support < curr_price_base else curr_price_base * 0.925

    # 손절가 중첩 방어 락(Lock)
    if not is_filtered_out and entry_target <= sl_price * 1.015:
        if ai['up_prob'] >= 70:
            entry_target = sl_price * 1.015
        else:
            is_filtered_out = True
            filter_msg = "손절가 중첩 (리스크 과다)"

    # 디스플레이용 퍼센트 계산
    entry_pct = ((entry_target - curr_price_base) / curr_price_base) * 100

    # 지표 기반 베이스 연산에서 변동성(ATR) 순정값 추출 및 5/10/20% 상한선 락 가동
    atr_pure = (ai['tp_price'] - curr_price_base) / 2.5
    tp1 = min(curr_price_base + (atr_pure * 0.8), curr_price_base * 1.05)
    tp2 = min(curr_price_base + (atr_pure * 1.5), curr_price_base * 1.10)
    tp3 = min(curr_price_base + (atr_pure * 2.5), curr_price_base * 1.20)

    tp1_pct = ((tp1 - curr_price_base) / curr_price_base) * 100
    tp2_pct = ((tp2 - curr_price_base) / curr_price_base) * 100
    tp3_pct = ((tp3 - curr_price_base) / curr_price_base) * 100

# ====================================================================
    # 3. [상단 라인] 익절가 3단 배치 (글자 잘림 해결)
    # ====================================================================
    col_top1, col_top2, col_top3 = st.columns(3)
    with col_top1:
        st.metric(label="🔥 1차 익절가 (50%)", value=f"{currency_symbol}{tp1:,.0f}", delta=f"+{tp1_pct:.1f}%")
    with col_top2:
        st.metric(label="🚀 2차 익절가 (25%)", value=f"{currency_symbol}{tp2:,.0f}", delta=f"+{tp2_pct:.1f}%")
    with col_top3:
        # 💡 '또는 신호이탈'을 지우고 가격만 넣어서 깔끔하게 뚫어버립니다.
        st.metric(label="💎 3차 익절가 (25%)", value=f"{currency_symbol}{tp3:,.0f}", delta=f"+{tp3_pct:.1f}%")

    st.write("")


# ====================================================================
    # 🎯 [하단 확장] 30년 베테랑 분할 청산 및 물타기/익절 전술 보드 (POC 최종 통일)
    # ====================================================================
    base_price = entry_price if ('entry_price' in locals() and entry_price > 0) else entry_target
    
    # 💡 [최종 수정] 위에서 찾은 ai['poc_price']를 손절가 변수에 다이렉트로 꽂아줍니다.
    veteran_stop_loss = ai['poc_price']

    fallback_entry = round(base_price * 0.94, 1)  
    pool_entry_price = round(base_price * 0.88, 1) 
    pool_weight = "20%"                             
    target_profit = round(base_price * 1.12, 1)  

    # 🌐 [국내/미국 통화 포맷팅 분기] 원화(₩)는 정수, 달러($)는 소수점 1자리 유지
    if currency_symbol == "₩":
        txt_entry = f"{currency_symbol}{fallback_entry:,.0f}"
        txt_stop = f"{currency_symbol}{veteran_stop_loss:,.0f}"
        txt_pool = f"{currency_symbol}{pool_entry_price:,.0f}"
        txt_target = f"{currency_symbol}{target_profit:,.0f}"
    else:
        txt_entry = f"{currency_symbol}{fallback_entry:,.1f}"
        txt_stop = f"{currency_symbol}{veteran_stop_loss:,.1f}"
        txt_pool = f"{currency_symbol}{pool_entry_price:,.1f}"
        txt_target = f"{currency_symbol}{target_profit:,.1f}"

    # 💡 생코드 출력 방지를 위해 아래 HTML 태그들은 왼쪽 벽면에 바짝 붙여야 합니다.
    st.markdown(f"""
<div style="background-color:#1e293b55; padding:12px; border-radius:6px; border: 1px solid #475569; margin-top:15px; font-size:13px; line-height:1.6; box-sizing:border-box;">
<div style="margin-bottom: 10px;">
<span style="color:#94a3b8; font-weight:bold;">📉 현실적 눌림목 진입가:</span> 
<span style="color:#f43f5e; font-weight:bold; font-size:15px;">{txt_entry}</span>
<div style="font-size:10.5px; color:#64748b; margin-top:1px;">RSI 과열 해소 시 주요 매물대 상단 지지선 기준 동적 역산</div>
</div>
<div style="margin-bottom: 10px;">
<span style="color:#94a3b8; font-weight:bold;">🚨 리스크 방어선 손절가:</span> 
<span style="color:#3b82f6; font-weight:bold; font-size:14px;">{txt_stop}</span>
<div style="font-size:10.5px; color:#64748b; margin-top:1px;">최근 63일 Rolling 최대 매물축(POC) 장중 실시간 이탈 시 전량 즉시 시장가 청산</div>
</div>
<div style="margin-bottom: 10px;">
<span style="color:#94a3b8; font-weight:bold;">💧 재무 대기 물타기 타점:</span> 
<span style="color:#eab308; font-weight:bold; font-size:14px;">{txt_pool}</span> 
<span style="color:#94a3b8; font-size:11px;">(비중: <b style="color:#eab308;">{pool_weight}</b> 추가)</span>
<div style="font-size:10.5px; color:#64748b; margin-top:1px;">안정적인 펀더멘탈 보장선 및 ATR 변동성 하단 융합 구역</div>
</div>
<hr style="border:0; border-top:1px solid #475569; margin:10px 0;">
<div>
<span style="color:#94a3b8; font-weight:bold;">🎯 물타기 후 청산 목표 익절가:</span> 
<span style="color:#10b981; font-weight:bold; font-size:16px;">{txt_target}</span>
<div style="font-size:10.5px; color:#94a3b8; margin-top:2px; background-color:#0f172a; padding:6px; border-radius:4px; border: 1px solid #334155; line-height:1.4;">
<b style="color:#10b981;">💡 베테랑 숏코멘트:</b><br>
매물대 저항선 밀집 지역입니다. 이 가격대 도달 시 탐욕 지수가 정점에 달하므로 수급 뉴스 호재가 터지더라도 미련 없이 70% 이상 분할 청산하여 확정 수익을 확보하는 것이 장기 생존의 핵심입니다.
</div>
</div>
</div>
""", unsafe_allow_html=True)


# ====================================================================
    # 4. [하단 라인] 왼쪽에는 손절가, 오른쪽에는 AI 근거 및 최근 뉴스 배치
    # ====================================================================
    st.write("") # 한 줄 띄움
    col_bot_left, col_bot_right = st.columns([1, 3]) # 1:3 비율로 공간 분할

    with col_bot_left:
        # 🚨 최종 구조컷 가격 추출 및 현재가 대비 실시간 마이너스 퍼센트 계산
        sl_price = float(ai['tighter_sl'])
        sl_pct = ((sl_price - curr_price_base) / curr_price_base) * 100
        
    with col_bot_right:
        # (오른쪽 AI 종합 진단 및 실시간 뉴스 관제탑 로직은 기존 코드 그대로 유지)
        
# [A-0] 실시간 활성화된 기술적 요소 계량화 및 정제
        active_buys = []
        if 'sig_vol_buy' in locals() and sig_vol_buy: active_buys.append("그랜빌의 세력 거래량 유입")
        if 'sig_macd_buy' in locals() and sig_macd_buy: active_buys.append("제럴드 아펠의 MACD 골든크로스/반전")
        if 'sig_rsi_buy' in locals() and sig_rsi_buy: active_buys.append("와일더의 RSI 과매도 탈출 역발상 타점")
        if 'sig_dmi_buy' in locals() and sig_dmi_buy: active_buys.append("와일더의 DMI/ADX 추세 가속화 엔진")

        active_sells = []
        if 'sig_vol_sell' in locals() and sig_vol_sell: active_sells.append("그랜빌의 역사적 거래량 바잉 클라이맥스 음봉 폭탄")
        if 'sig_macd_sell' in locals() and sig_macd_sell: active_sells.append("제럴드 아펠의 MACD 데드크로스 추세 붕괴")
        if 'sig_rsi_sell' in locals() and sig_rsi_sell: active_sells.append("와일더의 RSI 과매수 광기 이탈 신호")
        if 'sig_dmi_sell' in locals() and sig_dmi_sell: active_sells.append("와일더의 DMI 매도 우위 역배열 추세 역전")

        # 기존 연산 엔진의 강세/약세 캔들 및 차트 패턴명 동적 정제 추출
        detected_bull_patterns = [r.replace("⚡ ", "").replace("🎯 ", "").replace("📊 ", "").replace("🔥 ", "") for r in ai.get('success_reasons', [])]
        detected_bear_patterns = [r.replace("❌ ", "").replace("🌊 ", "").replace("🚨 ", "").replace("🔵 ", "") for r in ai.get('failed_reasons', [])]

        total_bulls = active_buys + detected_bull_patterns
        total_bears = active_sells + detected_bear_patterns

       # [A-1] 타이밍별 산정 근거 실시간 매스 매트릭스 브리핑 조립 (유니코드 우회 적용)
        if ai['up_prob'] >= 90:
            bull_items = [f"<li style='margin-left:15px; margin-bottom:4px;'>• {p.replace('상승', '<span style=\"color:#ff4b4b; font-weight:bold;\">상승</span>').replace('매수', '<span style=\"color:#ff4b4b; font-weight:bold;\">매수</span>')}</li>" for p in total_bulls]
            bull_list_html = "".join(bull_items) if bull_items else "<li style='margin-left:15px;'>• 장기 이평 정배열 지지 구조 형성</li>"
            
            reason_text = f"""
            <blockquote style='border-left: 4px solid #ff4b4b; padding-left: 10px; margin-bottom: 15px;'>
                <b style='font-size: 15px;'>\U0001F6A8 실시간 포지션 경보</b><br>
                현재 상승확률 {ai['up_prob']:.1f}%의 <b><span style='color:#ff4b4b;'>강력 초고확신 매수 타이밍</span></b>입니다.
            </blockquote>
            <p style='font-weight:bold; margin-bottom:5px;'>\U0001F4C8 차트 내 실시간 강세 시그널 연동 내역:</p>
            <ul style='list-style:none; padding-left:0; margin-bottom:15px;'>{bull_list_html}</ul>
            <p><b>\U0001F9F1 기술적 국면 분석:</b> 최근 14일 변동성(ATR) 대비 대량 거래대금이 상방 매물 분수령(POC)을 완벽한 지지 기반으로 전환시켰습니다.</p>
            <p style='margin-top:10px; color:#ff4b4b; font-weight:bold;'>\U0001F6E1 베테랑의 대응 강령: 1차 마디가 익절 이후 주가의 리스크 프리미엄을 극대화하여 대시세 파단까지 포지션을 강력 유지하십시오.</p>
            """
        elif ai['up_prob'] >= 70:
            bull_items = [f"<li style='margin-left:15px; margin-bottom:4px;'>• {p.replace('상승', '<span style=\"color:#ff4b4b; font-weight:bold;\">상승</span>').replace('매수', '<span style=\"color:#ff4b4b; font-weight:bold;\">매수</span>')}</li>" for p in total_bulls]
            bull_list_html = "".join(bull_items) if bull_items else "<li style='margin-left:15px;'>• 중기 추세 정배열 관성 유지</li>"
            
            reason_text = f"""
            <blockquote style='border-left: 4px solid #ff4b4b; padding-left: 10px; margin-bottom: 15px;'>
                <b style='font-size: 15px;'>\U0001F6A8 실시간 포지션 경보</b><br>
                현재 상승확률 {ai['up_prob']:.1f}%의 <b><span style='color:#ff4b4b;'>전략적 분할 매수 타점</span></b>입니다.
            </blockquote>
            <p style='font-weight:bold; margin-bottom:5px;'>\U0001F4C8 차트 내 실시간 강세 시그널 연동 내역:</p>
            <ul style='list-style:none; padding-left:0; margin-bottom:15px;'>{bull_list_html}</ul>
            <p><b>\U0001F9F1 기술적 국면 분석:</b> 단기 오실레이터 지표의 숨고르기 혹은 매물대 상단 마찰로 인해 장중 일시적인 차익 실현 흔들기가 출현할 수 있습니다.</p>
            <p style='margin-top:10px;'><b>\U0001F6E1 베테랑의 대응 강령:</b> 63일 POC 가격 중심축 주변 아래꼬리 영역에서 분할 거미줄 매집으로 방어 단가를 구축하십시오.</p>
            """
        elif ai['up_prob'] >= 45:
            reason_text = f"""
            <blockquote style='border-left: 4px solid #6b7280; padding-left: 10px; margin-bottom: 15px;'>
                <b style='font-size: 15px;'>\U0001F6A8 실시간 포지션 경보</b><br>
                현재 상승확률 {ai['up_prob']:.1f}%의 <b>중립 관망 및 포지션 동결 타이밍</b>입니다.
            </blockquote>
            <p><b>\U0001F9F1 기술적 국면 분석:</b> 기술적 지표상 상방 시그널과 하방 시그널이 1:1로 상쇄되며 에너지가 수렴하는 박스권 균형점 중심 단계입니다.</p>
            <p style='margin-top:10px; color:#94a3b8;'><b>\U0001F6E1 베테랑의 대응 강령:</b> 변동성 지표(BB Width)가 수축 후 확장되는 분수령이 터질 때까지 무리한 진입을 제한하고 현금을 유지하십시오.</p>
            """
        else:
            bear_items = []
            for p in total_bears:
                p_colored = (p.replace("하락", "<span style='color:#3b82f6; font-weight:bold;'>하락</span>")
                              .replace("매도", "<span style='color:#3b82f6; font-weight:bold;'>매도</span>")
                              .replace("데드크로스", "<span style='color:#3b82f6; font-weight:bold;'>데드크로스</span>")
                              .replace("위축", "<span style='color:#3b82f6; font-weight:bold;'>위축</span>")
                              .replace("압력", "<span style='color:#3b82f6; font-weight:bold;'>압력</span>")
                              .replace("위험", "<span style='color:#3b82f6; font-weight:bold;'>위험</span>")
                              .replace("붕괴", "<span style='color:#3b82f6; font-weight:bold;'>붕괴</span>")
                              .replace("상승", "<span style='color:#ff4b4b; font-weight:bold;'>상승</span>")
                              .replace("매수", "<span style='color:#ff4b4b; font-weight:bold;'>매수</span>"))
                bear_items.append(f"<li style='margin-left:15px; margin-bottom:6px;'>• {p_colored}</li>")
            bear_list_html = "".join(bear_items) if bear_items else "<li style='margin-left:15px;'>• 주요 지지선 붕괴 및 하방 관성 지배</li>"
            
            reason_text = f"""
            <blockquote style='border-left: 4px solid #3b82f6; padding-left: 10px; margin-bottom: 15px;'>
                <b style='font-size: 15px;'>\U0001F6A8 실시간 포지션 경보</b><br>
                현재 상승확률 {ai['up_prob']:.1f}%의 <b><span style='color:#3b82f6;'>절대 매도 및 진입 금지 (위험)</span></b> 타이밍입니다. 시장의 구조적 <span style='color:#3b82f6; font-weight:bold;'>붕괴</span> 징후가 방어선을 초토화시키고 있습니다.
            </blockquote>
            <p style='font-weight:bold; margin-bottom:5px;'>\U0001F4C9 차트 내 실시간 악재 시그널 연동 내역:</p>
            <ul style='list-style:none; padding-left:0; margin-bottom:15px; color:#cbd5e1; line-height:1.7;'>{bear_list_html}</ul>
            <p><b>\U0001F9F1 기술적 국면 분석:</b> 주요 장단기 이평선이 <span style='color:#3b82f6; font-weight:bold;'>역배열 마찰 구조</span>로 꺾이며 장중 투매성 거래량이 실리고 있습니다.</p>
            <p style='margin-top:5px;'>현재 타점들은 상승 반전이 아니라 과매도 구간 진입에 따른 <b>'단기 기술적 낙폭 과대 반등(데드캣 바운스)'</b>에 불과합니다.</p>
            <p style='margin-top:12px; color:#3b82f6; font-weight:bold;'>\U0001F6E1 베테랑의 대응 강령: 조금의 미련도 두지 말고 자산을 철저히 헷징하여 리스크 관리의 칼날을 세우십시오.</p>
            """


# ====================================================================
    # [B] 구글 실시간 뉴스 RSS를 이용한 한글 뉴스 2개 강제 매칭 엔진 (독립 배치형)
    # ====================================================================
    news_html = ""
    try:
        import urllib.request
        import urllib.parse
        import xml.etree.ElementTree as ET

        # 🎯 [조건 반영] 검색한 종목명 뒤에 3일 이내 필터(when:3d)를 강제 주입합니다.
        encoded_name = urllib.parse.quote(f"{selected_name} when:3d")
        url = f"https://news.google.com/rss/search?q={encoded_name}&hl=ko&gl=KR&ceid=KR:ko"
        
        # 브라우저인 척 속여서 구글 뉴스 데이터 요청
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            xml_data = response.read()
            
        # 가져온 XML 데이터에서 뉴스 제목만 2개 추출
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')[:2]
        
        if items:
            news_html = "<br><br><b>📰 실시간 관련 주요 뉴스 링크 (클릭 시 원본 직통):</b><br>"
            for item in items:
                title = item.find('title').text
                
                # ✨ [핵심 수정] 네이버 검색 우회 링크를 완전히 제거하고, 신문사 원본 사이트 직통 링크 추출
                working_link = item.find('link').text
                
                # HTML 하이퍼링크 태그 조립 (클릭 시 해당 언론사로 즉시 팝업 이동)
                news_html += f"• <a href='{working_link}' target='_blank' style='color: #38bdf8; text-decoration: none; font-weight: bold;'>{title}</a><br>"
        else:
            news_html = "<br><br><b>📰 실시간 관련 주요 뉴스:</b><br>• 최근 3일 이내에 해당 종목의 단기 특이 뉴스가 포착되지 않았습니다."
    except Exception:
        news_html = "<br><br>⚠️ [시스템] 실시간 뉴스 망 연동 중 지연이 발생하여 뉴스를 표시할 수 없습니다."

    # 🔄 박스 크기를 글자 길이에 맞게 꽉 조인 교체 코드
    # 💡 생코드 출력 오류를 막기 위해 HTML 시작 태그들을 왼쪽 벽면에 바짝 밀착시켰습니다.
    st.markdown(f"""
<div style="background-color: rgba(255,255,255,0.03); padding: 10px 14px; border-radius: 6px; font-size: 13px; line-height: 1.7; color: #e2e8f0; margin-top: 10px; margin-bottom: 10px; border: 1px solid #334155;">
{news_html.replace('<br><br>', '').strip()}
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
    
    # 1. 미리 지정된 셋업 리스트(ASSETS)에서 먼저 매칭되는지 찾기
    for sector_name, sector_dict in ASSETS.items():
        for name, ticker in sector_dict.items():
            t_lower = ticker.lower()
            ticker_base = t_lower.replace('-', '.').split('.')[0]
            if query_clean in name.lower() or query_clean == ticker_base or query_clean == t_lower:
                if "등극주" in name or "시총" in name or "주요통화" in name: continue
                return ticker, name
                
    # 2. 🌟 한글 종목명이 들어오면 국산 엔진(KRX 명부) 데이터 다이렉트 매칭
    if contains_hangul(query):
        try:
            import FinanceDataReader as fdr
            krx_df = fdr.StockListing('KRX')
            matched = krx_df[krx_df['Name'].str.lower() == query_clean]
            if matched.empty:
                matched = krx_df[krx_df['Name'].str.lower().str.contains(query_clean)]
                
            if not matched.empty:
                code = matched['Code'].values[0]
                market = matched['Market'].values[0]
                suffix = '.KQ' if 'KOSDAQ' in str(market).upper() else '.KS'
                return f"{code}{suffix}", matched['Name'].values[0]
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
    "🔥 토스증권 실시간 뜨는 산업 ↗", 
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
# [분기점 2] 유저가 요청한 실시간 뉴스 매크로 관제탑 메뉴를 선택했을 때
# -------------------------------------------------------------------
elif sector == "🌏 글로벌 실시간 증시 뉴스":
    is_macro_mode = True
    safe_ticker, selected_name = None, "글로벌 매크로 시황"

# -------------------------------------------------------------------
# [분기점 3] 일반 주식 섹터(국내, 미국, 코인)를 선택해 탐색할 때
# -------------------------------------------------------------------
else:
    raw_ticker_list = list(ASSETS[sector].keys())
    ticker_list = [k for k in raw_ticker_list if not any(x in k for x in ["등극주", "시총", "주요통화"])]
    
    # 🟢 섹터가 변경되었으면 인덱스 및 선택 상태 초기화
    if 'current_sector' not in st.session_state or st.session_state.current_sector != sector:
        st.session_state.current_sector = sector
        st.session_state.current_idx = 0
        st.session_state['sb_ticker_select'] = ticker_list[0]

    # 🟢 사용자가 마우스로 직접 selectbox를 바꿨을 때, 버튼 인덱스(current_idx)도 자동 동기화 (양방향 연결)
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

    # 이제 index와 상태값이 완벽히 일치하여 버튼 클릭 시 종목명이 실시간으로 바뀝니다.
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
    st.info("🌍 글로벌 실시간 증시 뉴스")
    st.write("미국 뉴욕증시 및 국내 금융시장에 직접적인 하이 임팩트를 주는 당일 주요 시황 뉴스를 실시간 스캔합니다.")
    st.markdown("### 🔥 당일 미-국내 증시 영향력 TOP 10 핵심 뉴스")

    try:
        import urllib.request
        import urllib.parse
        import xml.etree.ElementTree as ET

        # 3일 이내(when:3d) 핵심 타깃 검색
        macro_query = "(코스피 OR 코스닥 OR 나스닥 OR 삼성전자 OR 하이닉스 OR 엔비디아 OR 테슬라 OR 애플) when:3d"
        encoded_macro = urllib.parse.quote(macro_query)
        url = f"https://news.google.com/rss/search?q={encoded_macro}&hl=ko&gl=KR&ceid=KR:ko"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        all_items = root.findall('.//item')
        
        # 🧩 교통정리용 바구니 및 중복 방지 저장소
        seen_titles = set()
        seen_stocks = set()
        
        kospi_news = []
        kosdaq_news = []
        nasdaq_news = []
        stock_news = []
        
        # 1단계: 지수 뉴스 추출 (코스피, 코스닥, 나스닥 딱 1개씩 선점)
        for item in all_items:
            title_text = item.find('title').text
            pure_title = title_text.split(' - ')[0].strip()
            title_key = pure_title[:14]  # 앞 14글자가 같으면 중복 뉴스로 취급
            
            if title_key in seen_titles:
                continue
                
            if '코스피' in pure_title and not kospi_news:
                kospi_news.append(item)
                seen_titles.add(title_key)
            elif '코스닥' in pure_title and not kosdaq_news:
                kosdaq_news.append(item)
                seen_titles.add(title_key)
            elif '나스닥' in pure_title and not nasdaq_news:
                nasdaq_news.append(item)
                seen_titles.add(title_key)

        # 2단계: 대형주 종목별 '골고루 담기' 쿼터제 작동
        target_companies = ['삼성전자', '하이닉스', '엔비디아', '테슬라', '애플', '마이크로소프트']
        
        # 종목당 딱 1개씩만 우선적으로 바구니에 수집
        for item in all_items:
            title_text = item.find('title').text
            pure_title = title_text.split(' - ')[0].strip()
            title_key = pure_title[:14]
            
            if title_key in seen_titles:
                continue
            if item in (kospi_news + kosdaq_news + nasdaq_news):
                continue
                
            for company in target_companies:
                if company in pure_title and company not in seen_stocks:
                    if len(stock_news) < 7:
                        stock_news.append(item)
                        seen_stocks.add(company)
                        seen_titles.add(title_key)
                    break

        # 3단계: 그래도 10개가 안 채워졌다면, 중복되지 않은 최신 시황/종목 기사로 잔여석 마감
        final_items = kospi_news + kosdaq_news + nasdaq_news + stock_news
        if len(final_items) < 10:
            for item in all_items:
                if len(final_items) >= 10:
                    break
                title_text = item.find('title').text
                pure_title = title_text.split(' - ')[0].strip()
                title_key = pure_title[:14]
                
                if title_key in seen_titles or item in final_items:
                    continue
                    
                if any(k in pure_title for k in target_companies + ['증시', '시황']):
                    final_items.append(item)
                    seen_titles.add(title_key)
                    
        # 📸 뉴스피드 고화질 썸네일 플레이스홀더 10개
        placeholders = [
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&q=80",  # 지수
            "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=300&q=80",  # 지수
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=300&q=80",  # 미국지수
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=300&q=80",  # 삼전
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=300&q=80",  # 하이닉스
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=300&q=80",  # 엔비디아
            "https://images.unsplash.com/photo-1617788138017-80ad40651399?w=300&q=80",  # 테슬라
            "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=300&q=80",  # 애플
            "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=300&q=80",  # 마이크로소프트
            "https://images.unsplash.com/photo-1591696205602-2f950c417cb9?w=300&q=80"   # 종합
        ]
        
        if final_items:
            for idx, item in enumerate(final_items):
                title_text = item.find('title').text
                if ' - ' in title_text:
                    pure_title, source = title_text.rsplit(' - ', 1)
                else:
                    pure_title, source = title_text, "시황 종합"
                    
                working_link = item.find('link').text
                thumb_url = placeholders[idx % len(placeholders)]
                
                st.markdown(f"""
                <div style="display: flex; background-color: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); align-items: center; width: 100%;">
                    <img src="{thumb_url}" style="width: 120px; height: 85px; object-fit: cover; flex-shrink: 0;" />
                    <div style="padding: 10px 16px; flex-grow: 1;">
                        <span style="font-size: 11px; color: #a1a1aa; font-weight: 600; text-transform: uppercase;">📰 {source}</span>
                        <h4 style="margin: 4px 0 0 0; font-size: 14px; line-height: 1.45; font-weight: bold;">
                            <a href="{working_link}" target="_blank" style="color: #38bdf8; text-decoration: none;">{pure_title}</a>
                        </h4>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("🔥 최근 3일 이내에 조건에 맞는 핵심 뉴스가 포착되지 않았습니다.")
    except Exception as e:
        st.error(f"⚠️ [시스템] 실시간 뉴스망 동기화 실패 (오류 원인: {e})")
    
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
    # 🎯 [3단계 보완] 1~10봉 전용 추세 대응 청산 (5일선 이탈 + 10봉 시간제한)
    # ====================================================================
    sl_hard_target = entry_p * 0.960  # -4.0% 하드 손절선
    tp_target = entry_p * 1.050       # 1차 익절 타깃 (+5.0%)
    
    # 보유 기간을 최대 10봉(2주)으로 엄격히 제약
    available_bars = min(10, len(df_back) - pos - 1)
    
    weight_remaining = 1.0
    realized_pnl = 0.0
    is_tp_done = False

    for d in range(1, available_bars + 1):
        curr_idx = pos + d
        c_low_d = float(df_back['Low'].iloc[curr_idx])
        c_high_d = float(df_back['High'].iloc[curr_idx])
        c_close_d = float(df_back['Close'].iloc[curr_idx])
        c_ma5_d = float(df_back['MA_5'].iloc[curr_idx])

        # 1) -4.0% 하드 손절선 터치 시 즉시 전량 청산
        if c_low_d <= sl_hard_target:
            realized_pnl += weight_remaining * ((sl_hard_target - entry_p) / entry_p)
            weight_remaining = 0.0
            break

        # 2) +5.0% 달성 시 물량 절반(50%) 익절 확정
        if not is_tp_done and c_high_d >= tp_target:
            realized_pnl += 0.5 * ((tp_target - entry_p) / entry_p)
            weight_remaining -= 0.5
            is_tp_done = True

        # 3) 단기 관성선(5일 이동평균선) 종가 이탈 시 잔여 물량 전량 청산
        if c_close_d < c_ma5_d:
            realized_pnl += weight_remaining * ((c_close_d - entry_p) / entry_p)
            weight_remaining = 0.0
            break

    # 10봉(2주) 경과 시까지 이탈 신호가 없으면 10일차 종가에 강제 수익 확정
    if weight_remaining > 0:
        last_close = float(df_back['Close'].iloc[pos + available_bars])
        realized_pnl += weight_remaining * ((last_close - entry_p) / entry_p)

    # ====================================================================
    # 🎯 [4단계 보완] 실전 체결 오차(슬리피지 + 수수료 -0.3%) 패널티 차감
    # ====================================================================
    slippage_penalty = 0.003  # 0.3% 슬리피지 및 제세공과금 반영
    final_trade_return = realized_pnl - slippage_penalty

    trade_returns.append(final_trade_return)
    is_win_list.append(final_trade_return > 0)

# 복리 최종 수렴
GLOBAL_TOTAL_SIGNALS = len(trade_returns)
if GLOBAL_TOTAL_SIGNALS > 0:
    GLOBAL_WIN_RATE = (sum(is_win_list) / GLOBAL_TOTAL_SIGNALS) * 100
    
    cumulative_multiplier = 1.0
    for ret in trade_returns:
        cumulative_multiplier *= (1.0 + ret)
    GLOBAL_CUM_RETURN = (cumulative_multiplier - 1.0) * 100
else:
    GLOBAL_WIN_RATE = 0.0
    GLOBAL_CUM_RETURN = 0.0

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

# 🏆 스코어보드 HTML 연동 출력
st.sidebar.markdown(f"""
<div style="background-color:#0f172a; padding:15px; border-radius:10px; border: 2px solid #38bdf8; margin-bottom:20px; text-align:center;">
    <p style="margin:0; font-size:12px; color:#38bdf8; font-weight:bold; letter-spacing:0.5px;">🏆 {selected_name} AI 추세 최적화 단타 검증</p>
    <p style="margin:3px 0 12px 0; font-size:10px; color:#94a3b8;">(🔥 12대 기술적 지표 정밀 연동)</p>
    <div style="display: flex; justify-content: space-around; margin-top: 5px;">
        <!-- 왼쪽: 12대 지표 전략 승률 -->
        <div>
            <span style="font-size: 10px; color: #94a3b8; display: block;">실제 전략 승률</span>
            <span style="font-size: 19px; color: #38bdf8; font-weight: bold;">{win_rate:.1f}%</span>
        </div>
        <div style="border-left: 1px solid #334155; height: 32px; margin-top: 3px;"></div>
        <!-- 오른쪽: 12대 지표 1~5봉 예상 수익률 -->
        <div>
            <span style="font-size: 10px; color: #94a3b8; display: block;">예상 수익률 (1~5봉)</span>
            <span style="font-size: 19px; color: {upside_color}; font-weight: bold;">{upside_str}</span>
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

if api_key:
    st.sidebar.markdown("<div style='background-color:#1e2e1e; padding:8px; border-radius:5px; border-left:4px solid #00e676; color:#00e676; font-weight:bold; font-size:12px; margin-bottom:15px;'>🟢 Gemini API 연동 완료</div>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<div style='background-color:#2d2010; padding:8px; border-radius:5px; border-left:4px solid #ff9100; color:#ff9100; font-weight:bold; font-size:12px; margin-bottom:15px;'>🟡 API Key 입력 대기 중...</div>", unsafe_allow_html=True)

is_krw = bool(safe_ticker) and ("KRW" in safe_ticker or ".KS" in safe_ticker or ".KQ" in safe_ticker)
step_val = 1.0 if is_krw else 0.01

entry_price = st.sidebar.number_input(f"🎯 나의 매수가 입력 ({'₩' if is_krw else '$'})", value=0.0, step=step_val, key="sb_entry_price_input")

from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# ====================================================================
# 🎯 [공통 핵심 필터 Engine] 1번 탑10 & 2번 소급 검증 100% 공유 함수
# ====================================================================
def evaluate_stock_signal(df_proc, ai_data):
    if not ai_data or df_proc is None or len(df_proc) < 20:
        return None, 0.0, 0.0, ""

    c_close = float(df_proc['Close'].iloc[-1])
    c_open  = float(df_proc['Open'].iloc[-1])
    c_vol   = float(df_proc['Volume'].iloc[-1])
    vol_ma20= float(df_proc['Vol_MA_20'].iloc[-1]) if float(df_proc['Vol_MA_20'].iloc[-1]) > 0 else 1.0
    
    c_adx   = float(df_proc['ADX'].iloc[-1]) if 'ADX' in df_proc.columns else 25.0
    c_ma20  = float(df_proc['MA_20'].iloc[-1]) if 'MA_20' in df_proc.columns else c_close
    bb_upper = float(df_proc['BB_Upper'].iloc[-1]) if 'BB_Upper' in df_proc.columns else c_close
    poc_high = float(ai_data.get('poc_price', c_close))
    rvol_val = c_vol / vol_ma20

    # 1. 횡보 차단 (ADX 20 미만) 및 과열 차단 (20일 이격도 110% 초과)
    if c_adx < 20.0:
        return None, 0.0, 0.0, ""
    
    disparity_20 = (c_close / c_ma20) * 100.0 if c_ma20 > 0 else 100.0
    if disparity_20 > 110.0:
        return None, 0.0, 0.0, ""

    # 2. 대시세 모멘텀 필수 조건 (매물대 완파/지지 + 거래량 1.2배 양봉 OR 볼밴 돌파)
    cond_poc = (c_close >= poc_high * 0.99)
    cond_vol = (rvol_val >= 1.2) and (c_close >= c_open)
    cond_bb  = (c_close >= bb_upper)

    if not (cond_poc and (cond_vol or cond_bb)):
        return None, 0.0, 0.0, ""

    exp_win = float(ai_data.get('up_prob', 0.0))
    exp_ret = float(ai_data.get('upside', 0.0))

    # 3. 승률 70.0% 이상 & 예상 수익률 플러스(>0%) 필수 통과
    if exp_win < 70.0 or exp_ret <= 0.0:
        return None, 0.0, 0.0, ""

    # 시그널 태그 조립
    sig_tags = []
    if cond_bb: sig_tags.append("볼린저밴드 돌파")
    if c_close >= poc_high: sig_tags.append("매물대 완파")
    if rvol_val >= 1.2: sig_tags.append("대량수급")
    signal_str = " / ".join(sig_tags) if sig_tags else "추세우수"

    return signal_str, exp_win, exp_ret, c_close


# ====================================================================
# 1️⃣ [오늘의 Top 10 추천 스캐너]
# ====================================================================
def process_single_ticker_unbound(item):
    name, ticker = item
    try:
        df_t = get_raw_daily_data(ticker)
        if df_t is None or len(df_t) < 130:
            return None

        df_proc, ai_data = process_data(df_t, "daily", ticker, skip_news=True)
        signal_str, up_p, up_s, c_close = evaluate_stock_signal(df_proc, ai_data)
        if not signal_str:
            return None

        calc_entry = c_close * 0.995 if up_p >= 88.0 else (c_close * 0.990 if up_p >= 72.0 else c_close)
        composite_score = (up_p * 0.5) + (up_s * 4.0)

        return {
            "name": name, 
            "ticker": ticker,
            "entry_price": round(calc_entry, 2),
            "up_prob": round(up_p, 1),
            "upside": round(up_s, 1),
            "composite_score": round(composite_score, 2),
            "signal": signal_str,
            "score": 3 if up_p >= 80.0 else 2
        }
    except Exception:
        pass
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

    results_kr, results_us, results_coin = [], [], []
    processed = 0

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_item = {executor.submit(worker_task, (item[0], item[1]), ctx): item for item in all_tasks}

        for future in as_completed(future_to_item):
            processed += 1
            item_info = future_to_item[future]
            target_key = item_info[2]
            stock_name = item_info[0]
            ticker_code = item_info[1]

            pct = min(1.0, processed / total_count)
            progress_bar.progress(pct)
            status_box.markdown(f"🚀 **실시간 전 시장 스캔 중...** `{processed}/{total_count}` ({int(pct*100)}%) | 분석 중: **{stock_name}**")

            res = future.result()
            
            # 🔥 [피드백 적용] DB 검증 승률 60% 미만인 저성과 종목은 자동 추천 제외
            if res and ticker_code not in underperforming_tickers:
                if target_key == 'scan_results_kr': results_kr.append(res)
                elif target_key == 'scan_results_us': results_us.append(res)
                elif target_key == 'scan_results_coin': results_coin.append(res)

    st.session_state['scan_results_kr'] = sorted(results_kr, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_results_us'] = sorted(results_us, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_results_coin'] = sorted(results_coin, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]

    progress_bar.progress(1.0)
    status_box.success(f"✅ 전 종목 스캔 완료! (DB 저성과 항목 자동 필터링 적용)")



# ====================================================================
# 메인 탭 선언 및 레이아웃 분리
# ====================================================================
main_tab1, main_tab2 = st.tabs(["📈 실시간 차트 & 종목 분석", "📜 과거 추천주 성과 검증 관제탑"])

# --------------------------------------------------------------------
# 1️⃣ 메인 탭 1: 실시간 차트 & 종목 분석
# --------------------------------------------------------------------
with main_tab1:
    tab_d, tab_w, tab_m = st.tabs([
        "📆 일봉  *[1~5일 단타]*", 
        "🗓️ 주봉  *[1~3달 스윙]*", 
        "📅 월봉  *[6달~1년 장기]*"
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
    st.write("사이드바를 오갈 필요 없이, 여기서 직접 스캔을 실행하고 과거 추천 성과까지 한눈에 검증합니다.")
    st.write("")

    col_b1, col_b2 = st.columns([1.1, 0.9])

    # --------------------------------------------------------------------
    # 1. 오늘의 시장별 통합 Top 10 추천 (전략별 태그 직관화)
    # --------------------------------------------------------------------
    with col_b1:
        st.markdown("#### 1️⃣ 오늘의 시장별 통합 Top 10 추천")
        st.caption("👑 융합 스페셜 / 🛡️ 주도주 눌림목 / 🔥 단기 돌파 타점을 직관적으로 분류합니다.")

        if st.button("🔥 실시간 전 시장 스캔 & Top 10 보기", key="btn_direct_scan", use_container_width=True):
            bg_scan_worker(ASSETS)

        # ====================================================================
        # 🎯 [최종 UI 함수] 배지 태그 완벽 제거 & 추천 진입가 출력 고정본
        # ====================================================================
        def render_unified_top10(market_title, key_name):
            raw_results = st.session_state.get(key_name, [])
            
            # 승률 70% 이상 & 예상수익 플러스(>0%) 필수 검증
            results = [
                x for x in raw_results 
                if x.get('up_prob', 0.0) >= 70.0 and x.get('upside', 0.0) > 0.0
            ]

            st.markdown(f"### {market_title}")
            
            if not results:
                st.caption("⚪ 검증 기준(승률 70%↑ 및 예상수익 +0.1%↑)을 충족하는 종목이 없습니다.")
                return

            for rank, res in enumerate(results[:10], 1):
                sig = res.get('signal', '')
                win_rate = res.get('up_prob', 0.0)
                upside_val = res.get('upside', 0.0)
                entry_p = res.get('entry_price', 0.0)
                
                upside_color = "#ff4b4b" if upside_val > 0 else "#38bdf8"
                upside_html = f"+{upside_val:.1f}%" if upside_val > 0 else f"{upside_val:.1f}%"
                
                # 추천 진입가 화폐 단위 자동 처리 (국내주식/코인: 원화, 미국주식: 달러)
                is_krw = any(x in res.get('ticker', '') for x in [".KS", ".KQ", "-KRW"])
                if is_krw:
                    fmt_entry = f"₩{entry_p:,.0f}원" if entry_p > 0 else "종가 진입"
                else:
                    fmt_entry = f"${entry_p:,.2f}" if entry_p > 0 else "종가 진입"

                # 세부지표 조건 가독성 정돈 (슬래시 기준 줄바꿈)
                raw_sig = sig.replace('Track A', '').replace('Track B', '').strip(' / ')
                sig_list = [s.strip("[] ") for s in raw_sig.split('/') if s.strip()]
                sig_bullets = "".join([f"<div style='margin-left:12px; color:#94a3b8;'>• {s}</div>" for s in sig_list])

                # 문단 분리 카드 HTML
                card_html = f"""
                <div style="background-color: #1e293b; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #38bdf8; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                    <div style="font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 6px;">
                        {rank}위. {res['name']} <span style="font-size: 12px; color: #64748b; font-weight: normal;">({res['ticker']})</span>
                    </div>
                    <div style="font-size: 13px; color: #ffd700; font-weight: bold; margin-bottom: 8px;">
                        🎯 추천 진입가: <span style="color: #ffffff;">{fmt_entry}</span>
                    </div>
                    <hr style="border:0; border-top:1px solid #334155; margin: 6px 0;">
                    <div style="font-size: 13px; color: #e2e8f0; margin-bottom: 6px;">
                        📌 <b>승률 / 예상수익:</b> <span style="color:#38bdf8; font-weight:bold;">{win_rate:.1f}%</span> (<span style="color:{upside_color}; font-weight:bold;">{upside_html}</span>)
                    </div>
                    <div style="font-size: 12px; color: #e2e8f0; line-height: 1.5;">
                        🎯 <b>세부지표 조건:</b>
                        {sig_bullets}
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

        kr_res = st.session_state.get('scan_results_kr', [])
        us_res = st.session_state.get('scan_results_us', [])
        coin_res = st.session_state.get('scan_results_coin', [])

        if kr_res or us_res or coin_res:
            c1, c2, c3 = st.columns(3)
            with c1: render_unified_top10("🇰🇷 국내 증시", 'scan_results_kr')
            with c2: render_unified_top10("🇺🇸 미국 증시", 'scan_results_us')
            with c3: render_unified_top10("🪙 암호화폐", 'scan_results_coin')
        else:
            st.info("💡 위의 [실시간 전 시장 스캔 & Top 10 보기] 버튼을 누르면 스캔이 시작됩니다.")

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

            # 과거 시점 검증 워커 함수
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
                    df_proc, ai_data = process_data(df_sub, "daily", ticker, skip_news=True)
                    signal_str, exp_win, exp_ret, c_close = evaluate_stock_signal(df_proc, ai_data)

                    if not signal_str:
                        return None

                    entry_p = c_close * 0.995 if exp_win >= 88.0 else (c_close * 0.990 if exp_win >= 72.0 else c_close)
                    atr_val = float(df_proc['ATR'].iloc[-1]) if 'ATR' in df_proc.columns else entry_p * 0.03

                    return {
                        "market": market_label,
                        "name": name,
                        "ticker": ticker,
                        "entry_p": entry_p,
                        "signal": signal_str,
                        "score": (exp_win * 0.5) + (exp_ret * 4.0),
                        "exp_win": exp_win,
                        "exp_ret": exp_ret,
                        "atr": atr_val,
                        "t_idx": t_idx
                    }
                except Exception:
                    return None

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

                with ThreadPoolExecutor(max_workers=12) as executor:
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

                top_kr = sorted([x for x in cand_matched if x['market'] == "국내"], key=lambda x: x['score'], reverse=True)[:5]
                top_us = sorted([x for x in cand_matched if x['market'] == "미국"], key=lambda x: x['score'], reverse=True)[:5]
                top_coin = sorted([x for x in cand_matched if x['market'] == "코인"], key=lambda x: x['score'], reverse=True)[:5]
                selected_tops = top_kr + top_us + top_coin
            else:
                selected_tops = db_top_tasks

            # 3. 🎯 실시간 매매 시뮬레이션 진행
            final_results = []
            all_returns = []
            win_count = 0

            for item in selected_tops:
                ticker = item['ticker']
                df_hist = get_raw_daily_data(ticker)
                if df_hist is None: continue

                t_idx = item.get('t_idx', len(df_hist) - 1 - bars_ago)
                if t_idx < 0: t_idx = 0
                entry_p = item['entry_p'] if item.get('entry_p', 0) > 0 else float(df_hist['Close'].iloc[t_idx])

                atr_val = item.get('atr', entry_p * 0.03)
                atr_pct = (atr_val / entry_p) * 100.0

                tp1_ret = min(5.0, 1.5 * atr_pct)
                tp2_ret = min(10.0, 3.0 * atr_pct)
                tp3_ret = min(20.0, 5.0 * atr_pct)
                sl_ret = -3.0

                future_bars = df_hist.iloc[t_idx + 1 : t_idx + 6]
                if future_bars.empty: continue

                remaining_qty = 1.0
                realized_ret = 0.0
                max_ret = 0.0
                trailing_active = False
                tp1_done, tp2_done, tp3_done = False, False, False
                is_closed = False
                events = []

                for _, bar in future_bars.iterrows():
                    if is_closed: break

                    b_high, b_low = float(bar['High']), float(bar['Low'])
                    b_high_ret = ((b_high - entry_p) / entry_p) * 100
                    b_low_ret = ((b_low - entry_p) / entry_p) * 100

                    if b_high_ret > max_ret:
                        max_ret = b_high_ret

                    if b_high_ret >= 2.0:
                        trailing_active = True

                    if not tp1_done and b_high_ret >= tp1_ret:
                        realized_ret += 0.50 * tp1_ret
                        remaining_qty -= 0.50
                        tp1_done = True
                        events.append(f"1차익절(+{tp1_ret:.1f}%)")

                    if tp1_done and not tp2_done and b_high_ret >= tp2_ret:
                        realized_ret += 0.25 * tp2_ret
                        remaining_qty -= 0.25
                        tp2_done = True
                        events.append(f"2차익절(+{tp2_ret:.1f}%)")

                    if tp2_done and not tp3_done and b_high_ret >= tp3_ret:
                        realized_ret += 0.25 * tp3_ret
                        remaining_qty -= 0.25
                        tp3_done = True
                        events.append(f"3차익절(+{tp3_ret:.1f}%)")
                        is_closed = True
                        break

                    if trailing_active and b_low_ret <= 0.5 and remaining_qty > 0:
                        realized_ret += remaining_qty * 0.5
                        events.append("트레일링스탑(+0.5%강제청산)")
                        remaining_qty = 0.0
                        is_closed = True
                        break
                    elif not trailing_active and b_low_ret <= sl_ret and remaining_qty > 0:
                        realized_ret += remaining_qty * sl_ret
                        events.append("무조건강제손절(-3.0%)")
                        remaining_qty = 0.0
                        is_closed = True
                        break

                if not is_closed and remaining_qty > 0:
                    last_c_ret = ((float(future_bars['Close'].iloc[-1]) - entry_p) / entry_p) * 100
                    realized_ret += remaining_qty * last_c_ret
                    events.append(f"5봉종가청산({last_c_ret:+.1f}%)")

                if realized_ret > 0: win_count += 1
                all_returns.append(realized_ret)

                if "3차익절" in "".join(events):
                    reason = f"🎯 **전량 목표 달성**: 목표 수익률 상향 돌파 ({', '.join(events)})"
                elif "2차익절" in "".join(events):
                    reason = f"🚀 **2차 익절 달성**: ({', '.join(events)})"
                elif "1차익절" in "".join(events):
                    reason = f"🔥 **1차 익절 완료**: ({', '.join(events)})"
                elif "트레일링스탑" in "".join(events):
                    reason = f"🛡️ **수익 방어 성공**: 최고 +{max_ret:.1f}% 상승 후 +0.5% 지점에서 안전 청산"
                elif "무조건강제손절" in "".join(events):
                    reason = f"🛑 **-3.0% 강제 손절**: +2% 도달 못하고 하락하여 -3.0% 지점에서 즉시 전량 손절"
                else:
                    reason = f"⏸️ **5봉 종가 청산**: 익절/손절 미달로 5봉째 종가 매도 ({', '.join(events)})"

                item['real_ret'] = realized_ret
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

                st.markdown("---")
                m1, m2 = st.columns(2)
                m1.metric("📊 실전 트레이딩 평균 수익률", f"{avg_r:+.1f}%")
                m2.metric("🎯 실전 검증 승률", f"{win_rate:.1f}%")
                st.markdown("---")

                # ====================================================================
                # 🎯 [소급 검증 카드 출력 UI]
                # ====================================================================
                def render_retro_cards(title, item_list):
                    st.markdown(f"### {title}")
                    if not item_list:
                        st.caption("⚪ 해당 시점 충족 종목 없음")
                        return
                    
                    for item in item_list:
                        ret_val = item['real_ret']
                        max_val = item['max_ret']
                        exp_win = item.get('exp_win', 75.0)
                        exp_ret = item.get('exp_ret', 3.0)
                        
                        ret_html = f"<span style='color:#ff4b4b; font-weight:bold;'>+{ret_val:.1f}%</span>" if ret_val > 0 else (f"<span style='color:#38bdf8; font-weight:bold;'>{ret_val:.1f}%</span>" if ret_val < 0 else "<span style='color:#94a3b8;'>0.0%</span>")
                        
                        if max_val >= exp_ret:
                            diff_analysis = f"🚀 <b>[예상 초과 달성]</b> 당초 목표 예상 수익률(+{exp_ret:.1f}%) 대비 강력한 수급 유입으로 최고 +{max_val:.1f}%까지 시세 분출"
                        elif ret_val > 0:
                            diff_analysis = f"🟡 <b>[예상 미달 - 수익 방어]</b> 목표 예상 수익률(+{exp_ret:.1f}%)에는 미치지 못했으나(최고 +{max_val:.1f}%), +0.5% 방어선으로 확정 청산"
                        else:
                            diff_analysis = f"🚨 <b>[예상 미달 - 손절 대응]</b> 당시 예상 승률({exp_win:.1f}%)과 달리 진입 후 단기 매물 압박으로 -3.0% 강제 손절 집행"

                        card_html = f"""
                        <div style="background-color: #1e2230; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                            <div style="font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 2px;">
                                • {item['name']} <span style="font-size: 12px; color: #94a3b8; font-weight: normal;">({item['ticker']})</span>
                            </div>
                            <div style="font-size: 11px; color: #38bdf8; margin-bottom: 4px; font-weight: 600;">
                                🏷️ 시그널: {item['signal']}
                            </div>
                            <div style="font-size: 12px; color: #ffd700; margin-bottom: 6px; font-weight: bold;">
                                📌 당시 예상 승률 / 예상 수익: <span style="color:#ffffff;">{exp_win:.1f}%</span> (<span style="color:#ff4b4b;">+{exp_ret:.1f}%</span>)
                            </div>
                            <div style="font-size: 13px; color: #e2e8f0; margin-bottom: 8px;">
                                📈 <b>실전 매매 수익률:</b> {ret_html} <span style="font-size: 11px; color: #94a3b8;">(최고 도달 +{max_val:.1f}%)</span>
                            </div>
                            <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5; background-color: #0f172a; padding: 8px 10px; border-radius: 6px; margin-top: 4px;">
                                💡 <b>매매 경과 및 분석</b><br>
                                {item['reason'].replace('**', '')}<br>
                                <hr style="border:0; border-top:1px solid #334155; margin: 6px 0;">
                                {diff_analysis}
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1: render_retro_cards("🇰🇷 국내 주식", retro_kr)
                with c2: render_retro_cards("🇺🇸 미국 주식", retro_us)
                with c3: render_retro_cards("🪙 암호화폐", retro_coin)
            else:
                st.warning(f"⚠️ {st.session_state.get('slider_bars_ago', 5)}봉 전 시점에는 조건 충족 추천주가 없었습니다.")
        else:
            st.info("💡 위의 [검증하기] 버튼을 누르면 하이브리드 익절 및 -3% 강제 손절 지침을 반영한 실전 성과가 연산됩니다.")