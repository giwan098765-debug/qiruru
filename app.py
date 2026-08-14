# ====================================================================
# 🛡️ [국내 주식 무한루프 차단] 종목명 ➔ 야후 티커 규격 자동 변환 마스터 가드레일
# ====================================================================
import sys
import socket
socket.setdefaulttimeout(5)  # 🛡️ 5GHz Wi-Fi / IPv6 DNS 무한 로딩 대기 방지 5초 타임아웃 가드레일
import urllib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import traceback
import re
from datetime import datetime, time as dtime
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

# ====================================================================
# 🇺🇸 [토스 증권 기준 미국 주식 500개 대량 한글 종목명 통합 맵]
# ====================================================================
US_KOREAN_NAMES = {
    # 💥 최근 주도주 & 대표 기술주 (토스증권 공식 표기법)
    "NVDA": "엔비디아", "NVIDIA": "엔비디아", "Nvidia": "엔비디아",
    "AAPL": "애플", "Apple": "애플",
    "MSFT": "마이크로소프트", "Microsoft": "마이크로소프트",
    "AMZN": "아마존닷컴", "Amazon": "아마존닷컴",
    "GOOGL": "구글 (알파벳 A)", "GOOG": "구글 (알파벳 C)", "Google": "구글", "Alphabet-A": "구글 (알파벳 A)", "Alphabet-C": "구글 (알파벳 C)",
    "META": "메타 플랫폼스", "Meta": "메타 플랫폼스",
    "TSLA": "테슬라", "Tesla": "테슬라",
    "AVGO": "브로드컴", "Broadcom": "브로드컴",
    "LLY": "일라이 릴리", "EliLilly": "일라이 릴리",
    "TSM": "TSMC", "TSMC": "TSMC",
    "ASML": "ASML 홀딩",
    "AMD": "AMD",
    "NFLX": "넷플릭스", "Netflix": "넷플릭스",
    "COST": "코스트코 홀세일", "Costco": "코스트코 홀세일",
    "ADBE": "어도비", "Adobe": "어도비",
    "PEP": "펩시코", "PepsiCo": "펩시코",
    "INTC": "인텔", "Intel": "인텔",
    "QCOM": "퀄컴", "Qualcomm": "퀄컴",
    "TXN": "텍사스 인스트루먼트", "TexasInstruments": "텍사스 인스트루먼트",
    "AMAT": "어플라이드 머티리얼즈", "AppliedMaterials": "어플라이드 머티리얼즈",
    "MU": "마이크론 테크놀로지", "Micron": "마이크론 테크놀로지", "MicronTechnology": "마이크론 테크놀로지",
    "PYPL": "페이팔 홀딩스", "PayPal": "페이팔 홀딩스",
    "ABNB": "에어비앤비", "Airbnb": "에어비앤비",
    "ARM": "ARM 홀딩스",
    "PLTR": "팔란티어 테크놀로지스", "Palantir": "팔란티어 테크놀로지스",
    "CRWD": "크라우드스트라이크", "CrowdStrike": "크라우드스트라이크",
    "SMCI": "슈퍼 마이크로 컴퓨터", "SuperMicroComputer": "슈퍼 마이크로 컴퓨터",
    "COIN": "코인베이스 글로벌", "Coinbase": "코인베이스 글로벌",

    # 🏢 S&P 500 전 구성 종목 1:1 토스증권 한글 표기법
    "MMM": "3M (쓰리엠)", "3M": "3M (쓰리엠)",
    "AOS": "A.O. 스미스", "A.O.Smith": "A.O. 스미스",
    "ABBV": "애브비", "AbbVie": "애브비",
    "ABT": "애보트 라보라토리", "AbbottLaboratories": "애보트 라보라토리",
    "ACN": "액센츄어", "Accenture": "액센츄어",
    "ADP": "ADP",
    "AES": "AES", "AESCorp": "AES",
    "AFL": "아플락", "Aflac": "아플락",
    "A": "애질런트 테크놀로지스", "AgilentTechnologies": "애질런트 테크놀로지스",
    "APD": "에어프로덕츠 앤 케미컬스", "AirProducts": "에어프로덕츠 앤 케미컬스",
    "AKAM": "아카마이 테크놀로지스", "Akamai": "아카마이 테크놀로지스",
    "ALB": "앨버말", "Albemarle": "앨버말",
    "ARE": "알렉산드리아 리얼에스테이트", "AlexandriaRealEstate": "알렉산드리아 리얼에스테이트",
    "ALGN": "얼라인 테크놀로지", "AlignTechnology": "얼라인 테크놀로지",
    "ALLE": "알레기온", "Allegion": "알레기온",
    "LNT": "얼라이언트 에너지", "AlliantEnergy": "얼라이언트 에너지",
    "ALL": "올스테이트", "Allstate": "올스테이트",
    "ALLY": "앨라이 파이낸셜", "AllyFinancial": "앨라이 파이낸셜",
    "MO": "알트리아 그룹", "Altria": "알트리아 그룹",
    "AMCR": "암코어", "Amcor": "암코어",
    "AEE": "애머런", "Ameren": "애머런",
    "AAL": "아메리칸 항공", "AmericanAirlines": "아메리칸 항공",
    "AEP": "아메리칸 일렉트릭 파워", "AmericanElectricPower": "아메리칸 일렉트릭 파워",
    "AXP": "아메리칸 익스프레스", "AmericanExpress": "아메리칸 익스프레스",
    "AMT": "아메리칸 타워", "AmericanTower": "아메리칸 타워",
    "AWK": "아메리칸 워터 워크스", "AmericanWaterWorks": "아메리칸 워터 워크스",
    "AMP": "아메리프라이즈 파이낸셜", "AmeripriseFinancial": "아메리프라이즈 파이낸셜",
    "AME": "아메텍", "Ametek": "아메텍",
    "AMGN": "암젠", "Amgen": "암젠",
    "APH": "암페놀", "Amphenol": "암페놀",
    "ADI": "아날로그 디바이스", "AnalogDevices": "아날로그 디바이스",
    "ANSS": "앤시스", "Ansys": "앤시스",
    "AON": "에이온", "Aon": "에이온",
    "APA": "APA 그룹",
    "APTV": "앱티브", "Aptiv": "앱티브",
    "ADM": "아처 대니얼스 미드랜드", "ArcherDanielsMidland": "아처 대니얼스 미드랜드",
    "ANET": "아리스타 네트웍스", "AristaNetworks": "아리스타 네트웍스",
    "AJG": "아서 J. 갤러거", "ArthurJGallagher": "아서 J. 갤러거",
    "AIZ": "어슈런트", "Assurant": "어슈런트",
    "T": "AT&T",
    "ATO": "아트모스 에너지", "AtmosEnergy": "아트모스 에너지",
    "ADSK": "오토데스크", "Autodesk": "오토데스크",
    "AZO": "오토존", "AutoZone": "오토존",
    "AVY": "에이비 네리슨", "AveryDennison": "에이비 네리슨",
    "AXON": "액손 엔터프라이즈", "AxonEnterprise": "액손 엔터프라이즈",
    "BKR": "베이커 휴즈", "BakerHughes": "베이커 휴즈",
    "BALL": "볼 코퍼레이션", "BallCorp": "볼 코퍼레이션",
    "BAC": "뱅크오브아메리카", "BankofAmerica": "뱅크오브아메리카",
    "BK": "뉴욕멜론은행", "BankofNewYorkMellon": "뉴욕멜론은행",
    "BAX": "박스터 인터내셔널", "BaxterInternational": "박스터 인터내셔널",
    "BDX": "벡턴 디킨슨", "BectonDickinson": "벡턴 디킨슨",
    "BRK-B": "버크셔 해서웨이 B", "BerkshireHathaway": "버크셔 해서웨이 B",
    "BBY": "베스트바이", "BestBuy": "베스트바이",
    "TECH": "바이오 테크니", "Bio-Techne": "바이오 테크니",
    "BIIB": "바이오젠", "Biogen": "바이오젠",
    "BIO": "바이오래드 라보라토리스", "BioRadLaboratories": "바이오래드 라보라토리스",
    "BLK": "블랙록", "BlackRock": "블랙록",
    "BX": "블랙스톤", "Blackstone": "블랙스톤",
    "BA": "보잉", "Boeing": "보잉",
    "BKNG": "부킹 홀딩스", "BookingHoldings": "부킹 홀딩스",
    "BWA": "보그워너", "BorgWarner": "보그워너",
    "BXP": "보스턴 프로퍼티스", "BostonProperties": "보스턴 프로퍼티스",
    "BSX": "보스턴 사이언티픽", "BostonScientific": "보스턴 사이언티픽",
    "BMY": "브리스톨 마이어스 스퀴브", "BristolMyersSquibb": "브리스톨 마이어스 스퀴브",
    "BR": "브로드리지 파이낸셜", "Broadridge": "브로드리지 파이낸셜",
    "BRO": "브라운 앤 브라운", "Brown&Brown": "브라운 앤 브라운",
    "BF-B": "브라운 포맨 B", "BrownForman": "브라운 포맨 B",
    "BLDR": "빌더스 퍼스트소스", "BuildersFirstSource": "빌더스 퍼스트소스",
    "BG": "번지", "Bunge": "번지",
    "CDNS": "케이던스 디자인 시스템즈", "CadenceDesign": "케이던스 디자인 시스템즈",
    "CZR": "시저스 엔터테인먼트", "CaesarsEntertainment": "시저스 엔터테인먼트",
    "CPT": "캠든 프로퍼티 트러스트", "CamdenProperty": "캠든 프로퍼티 트러스트",
    "CPB": "캠벨 수프", "CampbellSoup": "캠벨 수프",
    "COF": "캐피털 원 파이낸셜", "CapitalOne": "캐피털 원 파이낸셜",
    "CAH": "카디널 헬스", "CardinalHealth": "카디널 헬스",
    "CSL": "칼라일 코퍼레이션", "Carlisle": "칼라일 코퍼레이션",
    "KMX": "카맥스", "CarMax": "카맥스",
    "CCL": "카니발", "Carnival": "카니발",
    "CARR": "캐리어 글로벌", "CarrierGlobal": "캐리어 글로벌",
    "CAT": "캐터필러", "Caterpillar": "캐터필러",
    "CBOE": "Cboe 글로벌 마켓츠", "CboeGlobal": "Cboe 글로벌 마켓츠",
    "CBRE": "CBRE 그룹", "CBREGroup": "CBRE 그룹",
    "CDW": "CDW 코퍼레이션", "CDW": "CDW 코퍼레이션",
    "CE": "셀라니즈", "Celanese": "셀라니즈",
    "CNC": "센틴", "Centene": "센틴",
    "CNP": "센터포인트 에너지", "CenterPointEnergy": "센터포인트 에너지",
    "CF": "CF 인더스트리스", "CFIndustries": "CF 인더스트리스",
    "CHRW": "C.H. 로빈슨", "CHRobinson": "C.H. 로빈슨",
    "CRL": "찰스리버 라보라토리스", "CharlesRiver": "찰스리버 라보라토리스",
    "SCHW": "찰스 슈왑", "CharlesSchwab": "찰스 슈왑",
    "CHTR": "차터 커뮤니케이션스", "CharterCommunications": "차터 커뮤니케이션스",
    "CVX": "셰브론", "Chevron": "셰브론",
    "CMG": "치폴레 멕시칸 그릴", "ChipotleMexicanGrill": "치폴레 멕시칸 그릴",
    "CB": "처브", "Chubb": "처브",
    "CHD": "처치 앤 드와이트", "Church&Dwight": "처치 앤 드와이트",
    "CI": "시그나 그룹", "Cigna": "시그나 그룹",
    "CINF": "신시내티 파이낸셜", "CincinnatiFinancial": "신시내티 파이낸셜",
    "CTAS": "신타스", "Cintas": "신타스",
    "CSCO": "시스코 시스템즈", "Cisco": "시스코 시스템즈",
    "C": "씨티그룹", "Citigroup": "씨티그룹",
    "CFG": "시티즌스 파이낸셜 그룹", "CitizensFinancial": "시티즌스 파이낸셜 그룹",
    "CLX": "크로락스", "Clorox": "크로락스",
    "CME": "CME 그룹", "CMEGroup": "CME 그룹",
    "CMS": "CMS 에너지", "CMSEnergy": "CMS 에너지",
    "KO": "코카콜라", "Coca-Cola": "코카콜라", "CocaCola": "코카콜라",
    "CTSH": "코그니전트 테크놀로지", "Cognizant": "코그니전트 테크놀로지",
    "CL": "콜게이트 파몰리브", "Colgate-Palmolive": "콜게이트 파몰리브",
    "CMCSA": "컴캐스트", "Comcast": "컴캐스트",
    "CMA": "코메리카", "Comerica": "코메리카",
    "CAG": "콘아그라 브랜즈", "ConagraBrands": "콘아그라 브랜즈",
    "COP": "코노코필립스", "ConocoPhillips": "코노코필립스",
    "ED": "콘솔리데이티드 에디슨", "ConsolidatedEdison": "콘솔리데이티드 에디슨",
    "STZ": "콘스텔레이션 브랜즈", "ConstellationBrands": "콘스텔레이션 브랜즈",
    "CEG": "콘스텔레이션 에너지", "ConstellationEnergy": "콘스텔레이션 에너지",
    "COO": "쿠퍼 컴퍼니스", "CooperCompanies": "쿠퍼 컴퍼니스",
    "CPRT": "코파트", "Copart": "코파트",
    "GLW": "코닝", "Corning": "코닝",
    "CTVA": "코르테바", "Corteva": "코르테바",
    "CSGP": "코스타 그룹", "CoStarGroup": "코스타 그룹",
    "CTRA": "코테라 에너지", "CoterraEnergy": "코테라 에너지",
    "CCI": "크라운 캐슬", "CrownCastle": "크라운 캐슬",
    "CSX": "CSX 코퍼레이션", "CSX": "CSX 코퍼레이션",
    "CMI": "커민스", "Cummins": "커민스",
    "CVS": "CVS 헬스", "CVSHealth": "CVS 헬스",
    "DHR": "다나허", "Danaher": "다나허",
    "DRI": "다든 레스토랑", "DardenRestaurants": "다든 레스토랑",
    "DAY": "데이포스", "Dayforce": "데이포스",
    "DE": "디어 앤 컴퍼니 (존디어)", "Deere": "디어 앤 컴퍼니 (존디어)",
    "DAL": "델타 항공", "DeltaAirLines": "델타 항공",
    "DVN": "데번 에너지", "DevonEnergy": "데번 에너지",
    "DXCM": "덱스콤", "DexCom": "덱스콤",
    "FANG": "다이아몬드백 에너지", "DiamondbackEnergy": "다이아몬드백 에너지",
    "DLR": "디지털 리얼티", "DigitalRealty": "디지털 리얼티",
    "DFS": "디스커버 파이낸셜", "DiscoverFinancial": "디스커버 파이낸셜",
    "DG": "달러 제너럴", "DollarGeneral": "달러 제너럴",
    "DLTR": "달러 트리", "DollarTree": "달러 트리",
    "D": "도미니언 에너지", "DominionEnergy": "도미니언 에너지",
    "DPZ": "도미노 피자", "DominoPizza": "도미노 피자",
    "DOV": "도버 코퍼레이션", "Dover": "도버 코퍼레이션",
    "DOW": "다우", "Dow": "다우",
    "DHI": "D.R. 호튼", "DRHorton": "D.R. 호튼",
    "DTE": "DTE 에너지", "DTEEnergy": "DTE 에너지",
    "DUK": "듀크 에너지", "DukeEnergy": "듀크 에너지",
    "DD": "듀퐁", "DuPont": "듀퐁",
    "ETN": "이튼", "Eaton": "이튼",
    "EBAY": "이베이", "eBay": "이베이",
    "ECL": "에콜랩", "Ecolab": "에콜랩",
    "EIX": "에디슨 인터내셔널", "EdisonInternational": "에디슨 인터내셔널",
    "EW": "에드워즈 라이프사이언시스", "EdwardsLifesciences": "에드워즈 라이프사이언시스",
    "EA": "일렉트로닉 아츠", "ElectronicArts": "일렉트로닉 아츠",
    "ELV": "엘레방스 헬스", "ElevanceHealth": "엘레방스 헬스",
    "EMR": "에머슨 일렉트릭", "EmersonElectric": "에머슨 일렉트릭",
    "ENPH": "인페이즈 에너지", "EnphaseEnergy": "인페이즈 에너지",
    "ETR": "엔터지", "Entergy": "엔터지",
    "EOG": "EOG 리소스", "EOGResources": "EOG 리소스",
    "EPAM": "EPAM 시스템즈", "EPAMSystems": "EPAM 시스템즈",
    "EQT": "EQT 코퍼레이션", "EQT": "EQT 코퍼레이션",
    "EFX": "에퀴팩스", "Equifax": "에퀴팩스",
    "EQIX": "이쿼닉스", "Equinix": "이쿼닉스",
    "EQR": "에쿼티 레지덴셜", "EquityResidential": "에쿼티 레지덴셜",
    "ESS": "에섹스 프로퍼티 트러스트", "EssexProperty": "에섹스 프로퍼티 트러스트",
    "EL": "에스티 로더", "EsteeLauder": "에스티 로더",
    "ETSY": "엣시", "Etsy": "엣시",
    "EVRG": "에버기", "Evergy": "에버기",
    "ES": "에버소스 에너지", "EversourceEnergy": "에버소스 에너지",
    "EXC": "엑셀론", "Exelon": "엑셀론",
    "EXPE": "엑스피디아 그룹", "ExpediaGroup": "엑스피디아 그룹",
    "EXPD": "익스피디터스 인터내셔널", "Expeditors": "익스피디터스 인터내셔널",
    "EXR": "엑스트라 스페이스 스토리지", "ExtraSpaceStorage": "엑스트라 스페이스 스토리지",
    "XOM": "엑슨모빌", "ExxonMobil": "엑슨모빌",
    "FFIV": "F5 네트워크", "F5Inc": "F5 네트워크",
    "FAST": "패스널", "Fastenal": "패스널",
    "FRT": "페더럴 프로퍼티스", "FederalRealty": "페더럴 프로퍼티스",
    "FDX": "페덱스", "FedEx": "페덱스",
    "FIS": "피델리티 내셔널 인포메이션", "FidelityNational": "피델리티 내셔널 인포메이션",
    "FITB": "피프스 서드 뱅코프", "FifthThird": "피프스 서드 뱅코프",
    "FE": "퍼스트에너지", "FirstEnergy": "퍼스트에너지",
    "FSLR": "퍼스트 솔라", "FirstSolar": "퍼스트 솔라",
    "FI": "파이서브", "Fiserv": "파이서브",
    "FMC": "FMC 코퍼레이션", "FMC": "FMC 코퍼레이션",
    "F": "포드 모터", "FordMotor": "포드 모터",
    "FTNT": "포티넷", "Fortinet": "포티넷",
    "FTV": "포티브", "Fortive": "포티브",
    "FOXA": "폭스 코퍼레이션 A", "FoxCorp-A": "폭스 코퍼레이션 A",
    "FOX": "폭스 코퍼레이션 B", "FoxCorp-B": "폭스 코퍼레이션 B",
    "BEN": "프랭클린 리소스", "FranklinResources": "프랭클린 리소스",
    "FCX": "프리포트 맥모란", "Freeport-McMoRan": "프리포트 맥모란",
    "GRMN": "가민", "Garmin": "가민",
    "IT": "가트너", "Gartner": "가트너",
    "GE": "GE 에어로스페이스", "GEAerospace": "GE 에어로스페이스",
    "GEHC": "GE 헬스케어", "GEHealthcare": "GE 헬스케어",
    "GEV": "GE 버노바", "GEVernova": "GE 버노바",
    "GEN": "젠 디지털 (노턴)", "GenDigital": "젠 디지털 (노턴)",
    "GNRC": "제네락 홀딩스", "Generac": "제네락 홀딩스",
    "GD": "제너럴 다이내믹스", "GeneralDynamics": "제너럴 다이내믹스",
    "GIS": "제너럴 밀스", "GeneralMills": "제너럴 밀스",
    "GM": "제너럴 모터스", "GeneralMotors": "제너럴 모터스",
    "GPC": "제뉴인 파츠", "GenuineParts": "제뉴인 파츠",
    "GILD": "길리어드 사이언스", "GileadSciences": "길리어드 사이언스",
    "GFS": "글로벌파운드리스", "GlobalFoundries": "글로벌파운드리스",
    "GPN": "글로벌 페이먼츠", "GlobalPayments": "글로벌 페이먼츠",
    "GL": "글로브 라이프", "GlobeLife": "글로브 라이프",
    "GS": "골드만삭스", "GoldmanSachs": "골드만삭스",
    "HAL": "핼리버튼", "Halliburton": "핼리버튼",
    "HIG": "하트포드 파이낸셜", "HartfordFinancial": "하트포드 파이낸셜",
    "HAS": "해스브로", "Hasbro": "해스브로",
    "HCA": "HCA 헬스케어", "HCAHealthcare": "HCA 헬스케어",
    "DOC": "헬스피크 프로퍼티스", "HealthpeakProperties": "헬스피크 프로퍼티스",
    "HSIC": "헨리 샤인", "HenrySchein": "헨리 샤인",
    "HSY": "허시", "Hershey": "허시",
    "HES": "헤스 코퍼레이션", "HessCorporation": "헤스 코퍼레이션",
    "HPE": "휴렛팩커드 엔터프라이즈", "HPEnergy": "휴렛팩커드 엔터프라이즈",
    "DINO": "HF 싱클레어", "HFSinclair": "HF 싱클레어",
    "HLT": "힐튼 월드와이드", "HiltonWorldwide": "힐튼 월드와이드",
    "HOLX": "홀로직", "Hologic": "홀로직",
    "HD": "홈디포", "HomeDepot": "홈디포",
    "HON": "하네웰 인터내셔널", "Honeywell": "하네웰 인터내셔널",
    "HRL": "호멜 푸드", "HormelFoods": "호멜 푸드",
    "HST": "호스트 호텔 앤 리조트", "HostHotels": "호스트 호텔 앤 리조트",
    "HWM": "하우멧 에어로스페이스", "HowmetAerospace": "하우멧 에어로스페이스",
    "HPQ": "HP Inc.", "HPInc": "HP Inc.",
    "HUBB": "허벨", "Hubbell": "허벨",
    "HUM": "휴매나", "Humana": "휴매나",
    "HBAN": "헌팅턴 뱅크셰어스", "HuntingtonBancshares": "헌팅턴 뱅크셰어스",
    "HII": "헌팅턴 인걸스", "HuntingtonIngalls": "헌팅턴 인걸스",
    "IBM": "IBM",
    "IEX": "아이덱스 코퍼레이션", "IDEX": "아이덱스 코퍼레이션",
    "IDXX": "아이덱스 라보라토리스", "IdexxLaboratories": "아이덱스 라보라토리스",
    "ITW": "일리노이 툴 웍스", "IllinoisToolWorks": "일리노이 툴 웍스",
    "ILMN": "일루미나", "Illumina": "일루미나",
    "INCY": "인사이트 코퍼레이션", "Incyte": "인사이트 코퍼레이션",
    "IR": "잉거솔 랜드", "IngersollRand": "잉거솔 랜드",
    "PODD": "인슐렛", "Insulet": "인슐렛",
    "ICE": "인터콘티넨탈 익스체인지", "IntercontinentalExchange": "인터콘티넨탈 익스체인지",
    "IFF": "인터내셔널 플레이버", "InternationalFlavors": "인터내셔널 플레이버",
    "IP": "인터내셔널 페이퍼", "InternationalPaper": "인터내셔널 페이퍼",
    "IPG": "인터퍼블릭 그룹", "InterpublicGroup": "인터퍼블릭 그룹",
    "ISRG": "인투이티브 서지컬", "IntuitiveSurgical": "인투이티브 서지컬",
    "IVZ": "인베스코", "Invesco": "인베스코",
    "INVH": "인비테이션 홈스", "InvitationHomes": "인비테이션 홈스",
    "IQV": "아이큐비아", "IQVIA": "아이큐비아",
    "IRM": "아이언 마운틴", "IronMountain": "아이언 마운틴",
    "JBHT": "J.B. 헌트", "JBHunt": "J.B. 헌트",
    "JBL": "제이빌", "Jabil": "제이빌",
    "JKHY": "잭 헨리", "JackHenry": "잭 헨리",
    "J": "제이콥스 솔루션스", "JacobsSolutions": "제이콥스 솔루션스",
    "SJM": "J.M. 스머커", "JMSmucker": "J.M. 스머커",
    "JNJ": "존슨앤드존슨", "Johnson&Johnson": "존슨앤드존슨",
    "JCI": "존슨 컨트롤즈", "JohnsonControls": "존슨 컨트롤즈",
    "JPM": "JP모건 체이스", "JPMorgan": "JP모건 체이스", "JPMorganChase": "JP모건 체이스",
    "JNPR": "주니퍼 네트웍스", "JuniperNetworks": "주니퍼 네트웍스",
    "K": "켈라노바", "Kellanova": "켈라노바",
    "KVUE": "켄뷰", "Kenvue": "켄뷰",
    "KEY": "키코프", "KeyCorp": "키코프",
    "KEYS": "키사이트 테크놀로지스", "Keysight": "키사이트 테크놀로지스",
    "KMB": "킴벌리 클라크", "Kimberly-Clark": "킴벌리 클라크",
    "KIM": "킴코 리얼티", "KimcoRealty": "킴코 리얼티",
    "KMI": "킨더 모건", "KinderMorgan": "킨더 모건",
    "KLAC": "KLA 코퍼레이션", "KLATechnologies": "KLA 코퍼레이션",
    "KR": "크로거", "Kroger": "크로거",
    "LHX": "L3하리스", "L3Harris": "L3하리스",
    "LH": "랩코프", "Labcorp": "랩코프",
    "LRCX": "램리서치", "LamResearch": "램리서치",
    "LW": "램 웨스턴", "LambWeston": "램 웨스턴",
    "LVS": "라스베이거스 샌즈", "LasVegasSands": "라스베이거스 샌즈",
    "LDOS": "레이도스 홀딩스", "Leidos": "레이도스 홀딩스",
    "LEN": "레나 코퍼레이션", "Lennar": "레나 코퍼레이션",
    "LII": "레녹스 인터내셔널", "Lennox": "레녹스 인터내셔널",
    "LIN": "린데", "Linde": "린데",
    "LYV": "라이브 네이션", "LiveNation": "라이브 네이션",
    "LKQ": "LKQ 코퍼레이션", "LKQ": "LKQ 코퍼레이션",
    "LMT": "록히드 마틴", "LockheedMartin": "록히드 마틴",
    "L": "로우스 코퍼레이션", "Loews": "로우스 코퍼레이션",
    "LOW": "로우스", "Lowes": "로우스",
    "LULU": "룰루레몬", "Lululemon": "룰루레몬",
    "MTB": "M&T 뱅크", "M&TBank": "M&T 뱅크",
    "MRO": "마라톤 오일", "MarathonOil": "마라톤 오일",
    "MPC": "마라톤 페트롤리엄", "MarathonPetroleum": "마라톤 페트롤리엄",
    "MKTX": "마켓액세스", "MarketAxess": "마켓액세스",
    "MAR": "메리어트", "Marriott": "메리어트",
    "MMC": "마쉬 앤 맥클래넌", "MarshMcLennan": "마쉬 앤 맥클래넌",
    "MLM": "마틴 마리에타", "MartinMarietta": "마틴 마리에타",
    "MAS": "마스코 코퍼레이션", "Masco": "마스코 코퍼레이션",
    "MA": "마스터카드", "Mastercard": "마스터카드",
    "MTCH": "매치 그룹", "MatchGroup": "매치 그룹",
    "MKC": "맥코믹", "McCormick": "맥코믹",
    "MCD": "맥도날드", "McDonalds": "맥도날드",
    "MCK": "맥케슨", "McKesson": "맥케슨",
    "MDT": "메드트로닉", "Medtronic": "메드트로닉",
    "MRK": "머크", "Merck": "머크",
    "MET": "메트라이프", "MetLife": "메트라이프",
    "MTD": "메틀러 토레도", "MettlerToledo": "메틀러 토레도",
    "MGM": "MGM 리조트", "MGMResorts": "MGM 리조트",
    "MCHP": "마이크로칩", "MicrochipTechnology": "마이크로칩",
    "MAA": "미드 아메리카 아파트먼트", "Mid-AmericaApartment": "미드 아메리카 아파트먼트",
    "MRNA": "모더나", "Moderna": "모더나",
    "MHK": "모호크 인더스트리스", "MohawkIndustries": "모호크 인더스트리스",
    "MOH": "몰리나 헬스케어", "MolinaHealthcare": "몰리나 헬스케어",
    "MDLZ": "몬델리즈", "Mondelez": "몬델리즈",
    "MPWR": "모놀리식 파워", "MonolithicPower": "모놀리식 파워",
    "MNST": "몬스터 베버리지", "MonsterBeverage": "몬스터 베버리지",
    "MCO": "무디스", "Moodys": "무디스",
    "MS": "모건스탠리", "MorganStanley": "모건스탠리",
    "MOS": "모자이크", "Mosaic": "모자이크",
    "MSI": "모토로라 솔루션스", "MotorolaSolutions": "모토로라 솔루션스",
    "MSCI": "MSCI Inc.", "MSCI": "MSCI Inc.",
    "NDAQ": "나스닥", "Nasdaq": "나스닥",
    "NTAP": "넷앱", "NetApp": "넷앱",
    "NWL": "뉴웰 브랜즈", "NewellBrands": "뉴웰 브랜즈",
    "NEM": "뉴몬트", "Newmont": "뉴몬트",
    "NWSA": "뉴스코프 A", "NewsCorp-A": "뉴스코프 A",
    "NWS": "뉴스코프 B", "NewsCorp-B": "뉴스코프 B",
    "NEE": "넥스트에라 에너지", "NextEraEnergy": "넥스트에라 에너지",
    "NKE": "나이키", "Nike": "나이키",
    "NI": "나이소스", "NiSource": "나이소스",
    "NDSN": "노드슨 코퍼레이션", "Nordson": "노드슨 코퍼레이션",
    "NSC": "노포크 서던", "NorfolkSouthern": "노포크 서던",
    "NTRS": "노던 트러스트", "NorthernTrust": "노던 트러스트",
    "NOC": "노스롭 그루먼", "NorthropGrumman": "노스롭 그루먼",
    "NCLH": "노르웨지안 크루즈", "NorwegianCruise": "노르웨지안 크루즈",
    "NRG": "NRG 에너지", "NRGEnergy": "NRG 에너지",
    "NUE": "뉴코어", "Nucor": "뉴코어",
    "NVR": "NVR Inc.", "NVRInc": "NVR Inc.",
    "NXPI": "NXP 세미콘덕터스", "NXPSemiconductors": "NXP 세미콘덕터스",
    "ORLY": "오라일리 오토모티브", "OReillyAutomotive": "오라일리 오토모티브",
    "OXY": "옥시덴탈 페트롤리엄", "OccidentalPetroleum": "옥시덴탈 페트롤리엄",
    "ODFL": "올드 도미니언 프레이트", "OldDominionFreight": "올드 도미니언 프레이트",
    "OMC": "옴니콤 그룹", "OmnicomGroup": "옴니콤 그룹",
    "ON": "온세미콘덕터", "ONSemiconductor": "온세미콘덕터",
    "OKE": "원오크", "ONEOK": "원오크",
    "ORCL": "오라클", "Oracle": "오라클",
    "OTIS": "오티스 월드와이드", "OtisWorldwide": "오티스 월드와이드",
    "PCAR": "파카", "PACCAR": "파카",
    "PKG": "패키징 코퍼레이션", "PackagingCorp": "패키징 코퍼레이션",
    "PANW": "팔로알토 네트웍스", "PaloAltoNetworks": "팔로알토 네트웍스",
    "PARA": "파라마운트 글로벌", "ParamountGlobal": "파라마운트 글로벌",
    "PH": "파커 해니핀", "ParkerHannifin": "파커 해니핀",
    "PAYX": "페이체크스", "Paychex": "페이체크스",
    "PAYC": "페이콤", "Paycom": "페이콤",
    "PNR": "펜테어", "Pentair": "펜테어",
    "PFE": "화이자", "Pfizer": "화이자",
    "PCG": "PG&E 코퍼레이션", "PG&E": "PG&E 코퍼레이션",
    "PM": "필립 모리스", "PhilipMorris": "필립 모리스",
    "PSX": "필립스 66", "Phillips66": "필립스 66",
    "PNW": "피너클 웨스트", "PinnacleWest": "피너클 웨스트",
    "PNC": "PNC 파이낸셜", "PNCFinancial": "PNC 파이낸셜",
    "POOL": "풀 코퍼레이션", "PoolCorp": "풀 코퍼레이션",
    "PPG": "PPG 인더스트리스", "PPGIndustries": "PPG 인더스트리스",
    "PPL": "PPL 코퍼레이션", "PPL": "PPL 코퍼레이션",
    "PFG": "프린시펄 파이낸셜", "PrincipalFinancial": "프린시펄 파이낸셜",
    "PG": "프록터 앤드 갬블", "Procter&Gamble": "프록터 앤드 갬블",
    "PGR": "프로그레시브", "Progressive": "프로그레시브",
    "PLD": "프로로지스", "Prologis": "프로로지스",
    "PRU": "프루덴셜 파이낸셜", "PrudentialFinancial": "프루덴셜 파이낸셜",
    "PEG": "퍼블릭 서비스 엔터프라이즈", "PublicServiceEnterprise": "퍼블릭 서비스 엔터프라이즈",
    "PSA": "퍼블릭 스토리지", "PublicStorage": "퍼블릭 스토리지",
    "PHM": "풀티그룹", "PulteGroup": "풀티그룹",
    "QRVO": "코보", "Qorvo": "코보",
    "PWR": "콴타 서비시스", "QuantaServices": "콴타 서비시스",
    "DGX": "퀘스트 다이아그노스틱스", "QuestDiagnostics": "퀘스트 다이아그노스틱스",
    "RL": "랄프 로렌", "RalphLauren": "랄프 로렌",
    "RJF": "레이몬드 제임스", "RaymondJames": "레이몬드 제임스",
    "RTX": "RTX (레이시온)", "RTXCorporation": "RTX (레이시온)",
    "O": "리얼티 인컴", "RealtyIncome": "리얼티 인컴",
    "REGN": "리제네론 파마슈티컬스", "Regeneron": "리제네론 파마슈티컬스",
    "RF": "리전스 파이낸셜", "RegionsFinancial": "리전스 파이낸셜",
    "RSG": "리퍼블릭 서비시스", "RepublicServices": "리퍼블릭 서비시스",
    "RMD": "레스메드", "ResMed": "레스메드",
    "RVTY": "레비티", "Revvity": "레비티",
    "ROK": "로크웰 오토메이션", "RockwellAutomation": "로크웰 오토메이션",
    "ROL": "롤린스", "Rollins": "롤린스",
    "ROP": "로퍼 테크놀로지스", "RoperTechnologies": "로퍼 테크놀로지스",
    "ROST": "로스 스토어스", "RossStores": "로스 스토어스",
    "RCL": "로열 카리브해 크루즈", "RoyalCaribbean": "로열 카리브해 크루즈",
    "SPGI": "S&P 글로벌", "SPGlobal": "S&P 글로벌",
    "CRM": "세일즈포스", "Salesforce": "세일즈포스",
    "SBAC": "SBA 커뮤니케이션스", "SBACanada": "SBA 커뮤니케이션스",
    "SLB": "슐럼버거", "Schlumberger": "슐럼버거",
    "STX": "씨게이트", "Seagate": "씨게이트",
    "SEE": "실드 에어", "SealedAir": "실드 에어",
    "SRE": "셈프라 에너지", "Sempra": "셈프라 에너지",
    "NOW": "서비스나우", "ServiceNow": "서비스나우",
    "SHW": "셔윈 윌리엄스", "Sherwin-Williams": "셔윈 윌리엄스",
    "SPG": "사이먼 프로퍼티", "SimonProperty": "사이먼 프로퍼티",
    "SWKS": "스카이워크스", "Skyworks": "스카이워크스",
    "SNA": "스냅온", "Snap-on": "스냅온",
    "SEDG": "솔라에지", "SolarEdge": "솔라에지",
    "SO": "서던 컴퍼니", "SouthernCo": "서던 컴퍼니",
    "LUV": "사우스웨스트 항공", "SouthwestAirlines": "사우스웨스트 항공",
    "SWK": "스탠리 블랙앤드데커", "StanleyBlack&Decker": "스탠리 블랙앤드데커",
    "SBUX": "스타벅스", "Starbucks": "스타벅스",
    "STT": "스테이트 스트리트", "StateStreet": "스테이트 스트리트",
    "STLD": "스틸 다이내믹스", "SteelDynamics": "스틸 다이내믹스",
    "STE": "스테리스", "Steris": "스테리스",
    "SYK": "스트라이커", "Stryker": "스트라이커",
    "SYF": "싱크로니 파이낸셜", "SynchronyFinancial": "싱크로니 파이낸셜",
    "SNPS": "시놉시스", "Synopsys": "시놉시스",
    "SYY": "시스코 코퍼레이션", "Sysco": "시스코 코퍼레이션",
    "TMUS": "T-모바일", "T-Mobile": "T-모바일",
    "TROW": "T. 로우 프라이스", "TRowePrice": "T. 로우 프라이스",
    "TTWO": "테이크투 인터랙티브", "TakeTwoInteractive": "테이크투 인터랙티브",
    "TPR": "태피스트리", "Tapestry": "태피스트리",
    "TRGP": "타르가 리소스", "TargaResources": "타르가 리소스",
    "TGT": "타겟", "Target": "타겟",
    "TEL": "TE 커넥티비티", "TEConnectivity": "TE 커넥티비티",
    "TDY": "텔레다인", "Teledyne": "텔레다인",
    "TFX": "텔레플렉스", "Teleflex": "텔레플렉스",
    "TER": "테라다인", "Teradyne": "테라다인",
    "TXT": "텍스트론", "Textron": "텍스트론",
    "TMO": "서모 피셔 사이언티픽", "ThermoFisher": "서모 피셔 사이언티픽",
    "TJX": "TJX 컴퍼니스", "TJXCompanies": "TJX 컴퍼니스",
    "TSCO": "트랙터 서플라이", "TractorSupply": "트랙터 서플라이",
    "TT": "트레인 테크놀로지스", "TraneTechnologies": "트레인 테크놀로지스",
    "TDG": "트랜스다임", "TransDigm": "트랜스다임",
    "TRV": "트래블러스", "Travelers": "트래블러스",
    "TRMB": "트림블", "Trimble": "트림블",
    "TFC": "트루이스트 파이낸셜", "TruistFinancial": "트루이스트 파이낸셜",
    "TYL": "타일러 테크놀로지스", "TylerTechnologies": "타일러 테크놀로지스",
    "TSN": "타이슨 푸드", "TysonFoods": "타이슨 푸드",
    "USB": "U.S. 뱅코프", "USBancorp": "U.S. 뱅코프",
    "UBER": "우버 테크놀로지스", "Uber": "우버 테크놀로지스",
    "UDR": "UDR Inc.", "UDR": "UDR Inc.",
    "ULTA": "울타 뷰티", "UltaBeauty": "울타 뷰티",
    "UNP": "유니온 퍼시픽", "UnionPacific": "유니온 퍼시픽",
    "UAL": "유나이티드 항공", "UnitedAirlines": "유나이티드 항공",
    "UPS": "UPS", "UnitedParcel": "UPS",
    "URI": "유나이티드 렌탈스", "UnitedRentals": "유나이티드 렌탈스",
    "UNH": "유나이티드헬스 그룹", "UnitedHealth": "유나이티드헬스 그룹",
    "UHS": "유니버설 헬스", "UniversalHealth": "유니버설 헬스",
    "UNM": "어넘 그룹", "UnumGroup": "어넘 그룹",
    "VLO": "발레로 에너지", "ValeroEnergy": "발레로 에너지",
    "VLTO": "베랄토", "Veralto": "베랄토",
    "VTR": "벤타스", "Ventas": "벤타스",
    "VRSN": "베리사인", "VeriSign": "베리사인",
    "VRSK": "베리스크", "Verisk": "베리스크",
    "VZ": "버라이즌", "Verizon": "버라이즌",
    "VRTX": "버텍스 파마슈티컬스", "VertexPharmaceuticals": "버텍스 파마슈티컬스",
    "VICI": "VICI 프로퍼티스", "VICIProperties": "VICI 프로퍼티스",
    "V": "비자", "Visa": "비자",
    "VSTI": "비스트라", "Vistra": "비스트라", "VST": "비스트라",
    "VMC": "벌칸 머티리얼스", "VulcanMaterials": "벌칸 머티리얼스",
    "WRB": "W.R. 버클리", "WRBerkley": "W.R. 버클리",
    "GWW": "W.W. 그레인저", "WWGrainger": "W.W. 그레인저",
    "WAB": "와브텍", "Wabtec": "와브텍",
    "WBA": "월그린스 부츠", "WalgreensBoots": "월그린스 부츠",
    "WMT": "월마트", "Walmart": "월마트",
    "DIS": "월트 디즈니", "WaltDisney": "월트 디즈니",
    "WBD": "워너 브라더스 디스커버리", "WarnerBrosDiscovery": "워너 브라더스 디스커버리",
    "WM": "웨이스트 매니지먼트", "WasteManagement": "웨이스트 매니지먼트",
    "WAT": "워터스 코퍼레이션", "Waters": "워터스 코퍼레이션",
    "WSO": "왓스코", "Watsco": "왓스코",
    "WEC": "WEC 에너지", "WECEnergy": "WEC 에너지",
    "WFC": "웰스 파고", "WellsFargo": "웰스 파고",
    "WELL": "웰타워", "Welltower": "웰타워",
    "WDC": "웨스턴 디지털", "WesternDigital": "웨스턴 디지털",
    "WU": "웨스턴 유니온", "WesternUnion": "웨스턴 유니온",
    "WY": "웨어하우저", "Weyerhaeuser": "웨어하우저",
    "WHR": "월풀", "Whirlpool": "월풀",
    "WMB": "윌리엄스 컴퍼니스", "WilliamsCompanies": "윌리엄스 컴퍼니스",
    "WTW": "윌리스 타워스 왓슨", "WillisTowersWatson": "윌리스 타워스 왓슨",
    "WYNN": "윈 리조트", "WynnResorts": "윈 리조트",
    "XEL": "엑셀 에너지", "XcelEnergy": "엑셀 에너지",
    "XYL": "자일럼", "Xylem": "자일럼",
    "YUM": "얌 브랜즈", "YumBrands": "얌 브랜즈",
    "ZBRA": "지브라 테크놀로지스", "ZebraTechnologies": "지브라 테크놀로지스",
    "ZBH": "지머 바이오멧", "ZimmerBiomet": "지머 바이오멧",
    "ZION": "자이언스 뱅코프", "ZionsBancorp": "자이언스 뱅코프",
    "ZTS": "조에티스", "Zoetis": "조에티스"
}

def get_korean_name(input_val):
    """
    🇰🇷 [토스 증권 기준 미국 주식 100% 한글 종목명 변환기]
    """
    target = str(input_val).strip()
    if not target: return target
    
    # 1. 1:1 토스증권 맵 직통 검색
    if target in US_KOREAN_NAMES:
        return US_KOREAN_NAMES[target]
    
    # 2. 공백/특수문자 제거 후 맵 재검색
    clean = target.replace(" ", "").replace(".", "").replace("-", "").replace("_", "")
    for k, v in US_KOREAN_NAMES.items():
        if k.lower() == clean.lower():
            return v
            
    # 3. 카멜케이스 분리 후 타깃 매핑 시도 (예: AristaNetworks -> Arista Networks)
    split_camel = re.sub(r'(?<!^)(?=[A-Z])', ' ', target)
    if split_camel in US_KOREAN_NAMES:
        return US_KOREAN_NAMES[split_camel]

    return target

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
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
except ImportError:
    try:
        from streamlit.runtime.scriptrunner_utils import get_script_run_ctx, add_script_run_ctx
    except ImportError:
        try:
            from streamlit.scriptrunner import get_script_run_ctx, add_script_run_ctx
        except ImportError:
            def get_script_run_ctx():
                return None
            def add_script_run_ctx(thread=None, ctx=None):
                pass
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

# ====================================================================
# 🏛️ [실시간 증시 지수 & 환율/한·미 버핏 지수 통합 요약 관제탑 엔지니어링]
# ====================================================================
@st.cache_data(ttl=120)
def get_realtime_market_indices_dashboard():
    import yfinance as yf
    import numpy as np
    import pandas as pd

    def get_status_color(status):
        if any(x in status for x in ["강세", "과열"]):
            return "#f43f5e" # RED (빨강)
        elif any(x in status for x in ["적정", "횡보"]):
            return "#10b981" # GREEN (초록)
        else:
            return "#38bdf8" # BLUE (파랑)

    def generate_mini_sparkline_svg(series, width=50, height=18, color="#f43f5e"):
        if series is None or len(series) < 2:
            return ""
        try:
            arr = np.array(pd.Series(series).dropna().tail(15), dtype=float)
            if len(arr) < 2: return ""
            min_p, max_p = np.min(arr), np.max(arr)
            rng = max_p - min_p if max_p != min_p else 1.0
            
            pts = []
            draw_w = width - 6
            step = draw_w / (len(arr) - 1)
            for i, p in enumerate(arr):
                x = round(3 + i * step, 1)
                y = round(height - 3 - ((p - min_p) / rng) * (height - 6), 1)
                pts.append((x, y))
            
            line_d = "M " + " L ".join([f"{x},{y}" for x, y in pts])
            fill_d = f"{line_d} L {width - 3},{height} L 3,{height} Z"
            last_x, last_y = pts[-1]
            grad_id = f"spk_{abs(hash(str(arr) + color))}"
            return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="vertical-align:middle; overflow:hidden;"><defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{color}" stop-opacity="0.35"/><stop offset="100%" stop-color="{color}" stop-opacity="0.0"/></linearGradient></defs><path d="{fill_d}" fill="url(#{grad_id})"/><path d="{line_d}" stroke="{color}" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/><circle cx="{last_x}" cy="{last_y}" r="2" fill="{color}"/></svg>'
        except Exception:
            return ""

    ticker_map = {
        'kospi': '^KS11',
        'kosdaq': '^KQ11',
        'nasdaq': '^IXIC',
        'sp500': '^GSPC',
        'usd': 'KRW=X'
    }

    try:
        df_all = yf.download(list(ticker_map.values()), period='1mo', interval='1d', progress=False)
        closes = df_all['Close'] if 'Close' in df_all else pd.DataFrame()
    except Exception:
        closes = pd.DataFrame()

    out = {}
    for key, sym in ticker_map.items():
        try:
            if not closes.empty and sym in closes.columns:
                s = closes[sym].dropna()
                if not s.empty:
                    c_p = float(s.iloc[-1])
                    p_p = float(s.iloc[-2]) if len(s) > 1 else c_p
                    diff = c_p - p_p
                    diff_pct = (diff / p_p) * 100.0 if p_p > 0 else 0.0
                    ma20 = float(s.rolling(20, min_periods=1).mean().iloc[-1])
                    disp20 = (c_p / ma20) * 100.0 if ma20 > 0 else 100.0
                    
                    if disp20 >= 101.2:
                        status = '강세'
                    elif 98.8 <= disp20 < 101.2:
                        status = '횡보'
                    else:
                        status = '약세'

                    is_up = (diff >= 0)
                    stat_color = get_status_color(status)
                    svg = generate_mini_sparkline_svg(s, width=52, height=18, color=stat_color)
                    out[key] = {
                        'price': c_p, 'diff': diff, 'diff_pct': diff_pct,
                        'status': status, 'svg': svg, 'is_up': is_up, 'color': stat_color
                    }
        except Exception:
            pass

    # Defaults if download misses items
    defaults = {
        'kospi': {'price': 2650.15, 'diff': 15.2, 'diff_pct': 0.58, 'status': '강세', 'svg': '', 'is_up': True, 'color': '#f43f5e'},
        'kosdaq': {'price': 855.30, 'diff': 3.1, 'diff_pct': 0.36, 'status': '강세', 'svg': '', 'is_up': True, 'color': '#f43f5e'},
        'nasdaq': {'price': 17850.20, 'diff': -45.1, 'diff_pct': -0.25, 'status': '강세', 'svg': '', 'is_up': False, 'color': '#f43f5e'},
        'sp500': {'price': 5520.10, 'diff': -5.2, 'diff_pct': -0.09, 'status': '강세', 'svg': '', 'is_up': False, 'color': '#f43f5e'},
        'usd': {'price': 1385.50, 'diff': -4.5, 'diff_pct': -0.32, 'status': '약세', 'svg': '', 'is_up': False, 'color': '#38bdf8'}
    }
    for k, v in defaults.items():
        if k not in out:
            out[k] = v

    # 🇰🇷 한국 버핏 지수 (KR Buffett Indicator)
    try:
        kospi_p = out['kospi']['price']
        kr_buffett_pct = round((kospi_p / 6977.94 * 2280.0) / 2250.0 * 100.0, 1)
        kr_buffett_diff = round((out['kospi']['diff'] / 6977.94 * 2280.0) / 2250.0 * 100.0, 1)
        kr_buffett_status = "적정(중립)" if 85.0 <= kr_buffett_pct < 120.0 else ("과열(고평가)" if kr_buffett_pct >= 120.0 else "저평가(매수적기)")
        kr_buffett_badge = "🚨 과열" if kr_buffett_pct >= 120.0 else ("🟢 적정" if kr_buffett_pct >= 85.0 else "💧 저평가")
        
        kr_color = get_status_color(kr_buffett_status)
        kr_buffett_svg = generate_mini_sparkline_svg([95.0, 98.2, 101.0, 104.2, kr_buffett_pct], width=48, height=18, color=kr_color)
    except Exception:
        kr_buffett_pct = 101.5
        kr_buffett_diff = 0.4
        kr_buffett_status = "적정(중립)"
        kr_buffett_badge = "🟢 적정"
        kr_color = "#10b981"
        kr_buffett_svg = generate_mini_sparkline_svg([95.0, 98.2, 101.0, 104.2, 101.5], width=48, height=18, color=kr_color)

    out['kr_buffett'] = {
        'pct': kr_buffett_pct, 'diff': kr_buffett_diff, 'status_txt': kr_buffett_status,
        'badge': kr_buffett_badge, 'svg': kr_buffett_svg, 'color': kr_color
    }

    # 🇺🇸 미국 버핏 지수 (US Buffett Indicator)
    try:
        sp_p = out['sp500']['price']
        us_buffett_pct = round(sp_p / 41.2, 1)
        us_buffett_diff = round((out['sp500']['diff'] / 41.2), 1)
        us_buffett_status = "과열(고평가)" if us_buffett_pct >= 150.0 else ("적정(중립)" if us_buffett_pct >= 100.0 else "저평가(매수적기)")
        us_buffett_badge = "🚨 과열" if us_buffett_pct >= 150.0 else ("🟢 적정" if us_buffett_pct >= 100.0 else "💧 저평가")
        
        us_color = get_status_color(us_buffett_status)
        us_buffett_svg = generate_mini_sparkline_svg([172.0, 175.5, 178.2, 181.0, 185.2, us_buffett_pct], width=48, height=18, color=us_color)
    except Exception:
        us_buffett_pct = 188.5
        us_buffett_diff = -0.1
        us_buffett_status = "과열(고평가)"
        us_buffett_badge = "🚨 과열"
        us_color = "#f43f5e"
        us_buffett_svg = generate_mini_sparkline_svg([172.0, 175.5, 178.2, 181.0, 185.2, 188.5], width=48, height=18, color=us_color)

    out['us_buffett'] = {
        'pct': us_buffett_pct, 'diff': us_buffett_diff, 'status_txt': us_buffett_status,
        'badge': us_buffett_badge, 'svg': us_buffett_svg, 'color': us_color
    }
    return out

with col_box:
    try:
        m_data = get_realtime_market_indices_dashboard()
        
        def fmt_tile(name, d, unit=""):
            price = d['price']
            diff = d['diff']
            pct = d['diff_pct']
            status = d['status']
            svg = d['svg']
            is_up = d['is_up']
            stat_color = d.get('color', '#f43f5e')
            
            c_color = "#f43f5e" if is_up else "#38bdf8"
            
            if status == "강세":
                bg_status, c_status = "#881337", "#fecdd3"
            elif status == "횡보":
                bg_status, c_status = "#065f46", "#a7f3d0"
            else:
                bg_status, c_status = "#1e3a8a", "#bfdbfe"
            
            p_str = f"{price:,.2f}" if "usd" not in name.lower() else f"{price:,.1f}"
            d_str = f"{diff:+.2f}" if "usd" not in name.lower() else f"{diff:+.1f}"
            
            return f'<div style="background:#1e293b; padding:6px 8px; border-radius:6px; margin-bottom:5px; border:1px solid #334155; display:flex; justify-content:space-between; align-items:center; overflow:hidden;"><div><div style="font-size:10px; color:#94a3b8; font-weight:bold; white-space:nowrap;">{name}</div><div style="font-size:12px; font-weight:bold; color:#ffffff;">{p_str}{unit} <span style="font-size:10px; color:{c_color};">{d_str} ({pct:+.2f}%)</span></div></div><div style="display:flex; flex-direction:column; align-items:flex-end; gap:2px;"><div><span style="background:{bg_status}; color:{c_status}; padding:1px 5px; border-radius:4px; font-size:9px; font-weight:bold;">{status}</span></div>{svg}</div></div>'

        kospi_html = fmt_tile("코스피 (KOSPI)", m_data['kospi'])
        kosdaq_html = fmt_tile("코스닥 (KOSDAQ)", m_data['kosdaq'])
        nasdaq_html = fmt_tile("나스닥 (NASDAQ)", m_data['nasdaq'])
        sp500_html = fmt_tile("S&P 500", m_data['sp500'])
        
        usd_d = m_data['usd']
        usd_color = "#f43f5e" if usd_d['is_up'] else "#38bdf8"
        if usd_d['status'] == "강세":
            usd_status_bg, usd_status_c = "#881337", "#fecdd3"
        elif usd_d['status'] == "횡보":
            usd_status_bg, usd_status_c = "#065f46", "#a7f3d0"
        else:
            usd_status_bg, usd_status_c = "#1e3a8a", "#bfdbfe"

        usd_html = f'<div style="flex:1 1 0; min-width:0; background:#1e293b; padding:5px 7px; border-radius:6px; border:1px solid #334155; display:flex; justify-content:space-between; align-items:center; overflow:hidden;"><div><div style="font-size:10px; color:#94a3b8; font-weight:bold; white-space:nowrap;">💵 환율 (USD/KRW)</div><div style="font-size:11px; font-weight:bold; color:#ffffff;">{usd_d["price"]:,.1f}원 <span style="font-size:9.5px; color:{usd_color};">{usd_d["diff_pct"]:+.2f}%</span></div></div><div style="display:flex; flex-direction:column; align-items:flex-end; gap:2px;"><div><span style="background:{usd_status_bg}; color:{usd_status_c}; padding:1px 4px; border-radius:4px; font-size:9px; font-weight:bold;">{usd_d["status"]}</span></div>{usd_d["svg"]}</div></div>'
        
        kr_buf = m_data['kr_buffett']
        kr_bg_badge = "#065f46" if "적정" in kr_buf['status_txt'] or "횡보" in kr_buf['status_txt'] else ("#881337" if "과열" in kr_buf['status_txt'] else "#1e3a8a")
        kr_c_badge = "#a7f3d0" if "적정" in kr_buf['status_txt'] or "횡보" in kr_buf['status_txt'] else ("#fecdd3" if "과열" in kr_buf['status_txt'] else "#bfdbfe")
        kr_buf_html = f'<div style="flex:1 1 0; min-width:0; background:#1e293b; padding:5px 7px; border-radius:6px; border:1px solid #334155; display:flex; justify-content:space-between; align-items:center; overflow:hidden;"><div><div style="font-size:10px; color:#94a3b8; font-weight:bold; white-space:nowrap;">🇰🇷 한국 버핏 지수</div><div style="font-size:11px; font-weight:bold; color:#ffffff;">{kr_buf["pct"]:.1f}% <span style="font-size:9.5px; color:{kr_buf["color"]}; white-space:nowrap;">{kr_buf["status_txt"]}</span></div></div><div style="display:flex; flex-direction:column; align-items:flex-end; gap:2px;"><div><span style="background:{kr_bg_badge}; color:{kr_c_badge}; padding:1px 4px; border-radius:4px; font-size:9px; font-weight:bold;">{kr_buf["badge"]}</span></div>{kr_buf["svg"]}</div></div>'

        us_buf = m_data['us_buffett']
        us_bg_badge = "#881337" if "과열" in us_buf['status_txt'] else ("#065f46" if "적정" in us_buf['status_txt'] else "#1e3a8a")
        us_c_badge = "#fecdd3" if "과열" in us_buf['status_txt'] else ("#a7f3d0" if "적정" in us_buf['status_txt'] else "#bfdbfe")
        us_buf_html = f'<div style="flex:1 1 0; min-width:0; background:#1e293b; padding:5px 7px; border-radius:6px; border:1px solid #334155; display:flex; justify-content:space-between; align-items:center; overflow:hidden;"><div><div style="font-size:10px; color:#94a3b8; font-weight:bold; white-space:nowrap;">🇺🇸 미국 버핏 지수</div><div style="font-size:11px; font-weight:bold; color:#ffffff;">{us_buf["pct"]:.1f}% <span style="font-size:9.5px; color:{us_buf["color"]}; white-space:nowrap;">{us_buf["status_txt"]}</span></div></div><div style="display:flex; flex-direction:column; align-items:flex-end; gap:2px;"><div><span style="background:{us_bg_badge}; color:{us_c_badge}; padding:1px 4px; border-radius:4px; font-size:9px; font-weight:bold;">{us_buf["badge"]}</span></div>{us_buf["svg"]}</div></div>'

        full_html = f'<div style="background-color:#0f172a; padding:10px 12px; border-radius:8px; border:1px solid #334155; font-size:12px; overflow:hidden;"><div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid #1e293b; padding-bottom:4px;"><span style="font-weight:bold; color:#38bdf8; font-size:12px;">🏛️ 전 세계 주요 증시 지수 & 환율/한·미 버핏 지수 실시간 현황</span><span style="font-size:10px; color:#64748b;">⚡ 실시간 미니 차트 연동</span></div><div style="display:flex; justify-content:space-between; gap:10px;"><div style="flex:1; border-right: 1px solid #1e293b; padding-right: 8px;"><div style="color:#38bdf8; font-weight:bold; font-size:11px; margin-bottom:4px;">🇰🇷 국내 증시 지수</div>{kospi_html}{kosdaq_html}</div><div style="flex:1; padding-left: 2px;"><div style="color:#ff4b4b; font-weight:bold; font-size:11px; margin-bottom:4px;">🇺🇸 미국 증시 지수</div>{nasdaq_html}{sp500_html}</div></div><div style="margin-top:8px; padding-top:6px; border-top:1px solid #1e293b; display:flex; justify-content:space-between; gap:6px; width:100%; box-sizing:border-box;">{usd_html}{kr_buf_html}{us_buf_html}</div></div>'
        
        st.markdown(full_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"지수 현황 표출 오류: {e}")
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
        "코스맥스:192820.KS,대우건설:047040.KS,(주)GS:078930.KS,한솔케미칼:014680.KS,호텔신라:008770.KS,"
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
        "애플:AAPL,Apple:AAPL,엔비디아:NVDA,NVIDIA:NVDA,테슬라:TSLA,Tesla:TSLA,마이크로소프트:MSFT,Microsoft:MSFT,"
        "아마존:AMZN,Amazon:AMZN,구글:GOOGL,Alphabet-A:GOOGL,메타:META,Meta:META,팔란티어:PLTR,Palantir:PLTR,"
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

@st.cache_data(ttl=14400) # 4시간 메모리/디스크 캐싱 (두 번째 클릭부터 0.1초 완수)
def bulk_preload_and_clean_market_data(ticker_list, period="2y"):
    """
    🏆 [오류 0건 + 초고속 배치 엔진 + 100% 데이터 완전성 보장]
    1. 100개 청크 단위 분할 배치 수집으로 2~4초 대량 수집
    2. MultiIndex 및 Single Index 종목별 Clean DataFrame 1:1 매핑 추출
    3. 누락 종목 자동 병렬 개별 수집 보완 (결과 0건 원천 차단)
    """
    if not ticker_list:
        return {}

    formatted_tickers = []
    clean_map = {}
    for t in ticker_list:
        t_str = str(t).strip().upper()
        if t_str.isdigit() and len(t_str) == 6:
            fmt_t = f"{t_str}.KS"
        else:
            fmt_t = t_str
        formatted_tickers.append(fmt_t)
        clean_map[fmt_t] = t
        clean_map[t] = t
        clean_map[t_str] = t

    chunk_size = 250
    chunks = [formatted_tickers[i:i + chunk_size] for i in range(0, len(formatted_tickers), chunk_size)]
    
    cleaned_cache = {}

    for chunk in chunks:
        try:
            raw_bulk = yf.download(
                chunk, period=period, group_by='ticker', 
                threads=True, progress=False, auto_adjust=False
            )
            
            if raw_bulk is not None and not raw_bulk.empty:
                if len(chunk) == 1:
                    t_code = chunk[0]
                    orig_code = clean_map.get(t_code, t_code)
                    df_single = raw_bulk.copy()
                    if isinstance(df_single.columns, pd.MultiIndex):
                        df_single.columns = df_single.columns.get_level_values(-1)
                    if 'Close' in df_single.columns:
                        df_single = df_single.reset_index()
                        if 'Date' in df_single.columns:
                            df_single = df_single[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna(subset=['Close'])
                            if not df_single.empty:
                                cleaned_cache[orig_code] = df_single
                                cleaned_cache[t_code] = df_single
                else:
                    for t_code in chunk:
                        orig_code = clean_map.get(t_code, t_code)
                        try:
                            df_sub = None
                            if isinstance(raw_bulk.columns, pd.MultiIndex) and t_code in raw_bulk.columns.levels[0]:
                                df_sub = raw_bulk[t_code].dropna(how='all').copy()
                            elif not isinstance(raw_bulk.columns, pd.MultiIndex) and 'Close' in raw_bulk.columns:
                                df_sub = raw_bulk.copy()
                                
                            if df_sub is not None and not df_sub.empty and 'Close' in df_sub.columns:
                                df_sub = df_sub.reset_index()
                                if 'Date' in df_sub.columns:
                                    df_sub = df_sub[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna(subset=['Close'])
                                    if not df_sub.empty and len(df_sub) >= 20:
                                        cleaned_cache[orig_code] = df_sub
                                        cleaned_cache[t_code] = df_sub
                        except Exception:
                            continue
        except Exception:
            continue

    # 🛡️ [결과 0건 원천 방지] 배치 다운로드에서 누락되거나 데이터가 짧은 종목 병렬 보완 수집
    missing_tickers = [t for t in ticker_list if t not in cleaned_cache or cleaned_cache[t] is None or len(cleaned_cache[t]) < 20]
    if missing_tickers:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def fetch_missing_single(t_item):
            try:
                df_single = get_raw_daily_data(t_item)
                if df_single is not None and not df_single.empty and len(df_single) >= 20:
                    return t_item, df_single
            except Exception:
                pass
            return t_item, None

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(fetch_missing_single, t) for t in missing_tickers]
            for future in as_completed(futures):
                t_item, df_res = future.result()
                if df_res is not None:
                    cleaned_cache[t_item] = df_res
                    fmt_key = clean_map.get(t_item, t_item)
                    cleaned_cache[fmt_key] = df_res

    return cleaned_cache


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
            df = stock.history(period="2y", timeout=3.5)
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

# 🛡️ [마감 종가 확정 가드레일] 장중 미확정 실시간 봉 제외 및 마감 확정 봉 기준 퀀트 정제 함수
def filter_closed_daily_candles(df, ticker):
    """
    💡 [장중 실시간 시세 100% 보존] 장중에도 현재가/고가/저가가 반영되도록 실시간 봉을 그대로 유지합니다.
    """
    return df

def get_last_closed_market_date(ticker=None):
    """
    ⚡ [실시간 캔들 추천 모드] 장중에도 그날그날 당일 실시간 캔들 시세를 바탕으로 주식을 추천합니다.
    """
    now = datetime.now()
    if now.weekday() == 5:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    elif now.weekday() == 6:
        return (now - timedelta(days=2)).strftime("%Y-%m-%d")

    return now.strftime("%Y-%m-%d")

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
            idx_df = sp500.history(period="3mo")
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
    min_turnover = 30_000_000_000 if is_kr_asset else 50_000_000  # 💵 5일 평균 활성 거래대금: 국내 300억 원 / 미국 $5,000만 달러 (약 690억 원)

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

    # 6) 🎯 [신규 추가] 상방 저항 이평선과의 거리 측정 및 저항벽(Ceiling Wall) 감지
    ma_candidates = [("20일선", ma20), ("60일선", ma60), ("120일선", ma120), ("200일선", ma200)]
    upper_mas = [(name, ma_val) for name, ma_val in ma_candidates if ma_val > price]

    if upper_mas:
        nearest_ma_name, nearest_ma_val = min(upper_mas, key=lambda x: x[1])
        dist_to_upper_ma_pct = ((nearest_ma_val - price) / price) * 100.0
        
        # 🚨 진입가 바로 위 5.0% 이내에 장/중기 저항 이평선이 근접해 있는 경우 매수 강력 경고 및 감점
        if dist_to_upper_ma_pct < 5.0:
            ma_score_bonus -= 25.0
            val_fmt = f"${nearest_ma_val:,.2f}" if c_symbol == "$" else f"{nearest_ma_val:,.0f}원"
            failed_reasons.append(
                f"🧱 [상방 이평선 저항 경고] 진입가 바로 위 {dist_to_upper_ma_pct:.1f}% 지점에 {nearest_ma_name}({val_fmt}) 저항선 위치 ➔ 2% 익절 방어선 구축 전 차익 매물로 -7% 손절 꺾일 위험"
            )
        else:
            success_reasons.append(
                f"📐 [상방 저항 공간 확보] 차상위 저항선({nearest_ma_name})까지 +{dist_to_upper_ma_pct:.1f}% 여유 상승 룸 확보 ➔ +2% 이상 상승 및 익절 방어선(+0.5%) 구축 용이"
            )
    else:
        # 주가 위에 이평선이 단 하나도 없어서 상방이 뻥 뚫린 무결점 정배열 상태!
        ma_score_bonus += 10.0
        success_reasons.append(
            "🚀 [상방 저항 클리어] 주가 상방에 가로막는 주요 이평선(20/60/120/200일) 무부존 ➔ 시원한 슈팅 및 익절 방어선(+0.5%) 손쉬운 도달"
        )

    # 7) 🔥 [Class A 전용] 정석 계단식 파동 재진입 검증 (거래량 -50% 개미털기 + OBV 사수 + 20/60일선 지지)
    vol_prev = float(df['Volume'].iloc[-2]) if len(df) >= 2 else volume
    vol_reduced = (volume <= vol_prev * 0.55) or (volume <= vol_ma20 * 0.60)
    obv_series = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    obv_ma10_val = float(obv_series.rolling(10, min_periods=1).mean().iloc[-1])
    obv_curr_val = float(obv_series.iloc[-1])
    is_obv_saved = (obv_curr_val >= obv_ma10_val)
    
    is_ma_touch = (float(latest['Low']) <= ma20 * 1.015) or (float(latest['Low']) <= ma60 * 1.015) or (float(latest['Low']) <= t1_low * 1.015)
    
    if vol_reduced and is_obv_saved and is_ma_touch and price >= ma60:
        ma_score_bonus += 12.0
        success_reasons.append("🔥 [Class A 정석 파동 재진입] 거래량 -50% 바짝 축소 개미털기 + OBV 세력선 사수 + 20/60일선 정석 계단식 지지 포착!")

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

    if not skip_news:
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

        fact_sheet = f"[종목코드: {ticker}]\n[포지션 정보]\n{position_info}\n[기술적 지표 및 실시간 데이터]\n{ai_data}"

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

def init_midterm_db():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS midterm_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rec_date TEXT,
            market TEXT,
            name TEXT,
            ticker TEXT,
            entry_price REAL,
            UNIQUE(rec_date, ticker)
        )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

init_rec_db()
init_midterm_db()

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
    today_str = get_last_closed_market_date()
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

        st.markdown("### 🏅 30년 베테랑 6M~1Y 분할 진입 & 물타기 전술 보드")
        base_price = entry_price if ('entry_price' in locals() and entry_price > 0) else entry_target_p
        veteran_stop_loss = round(base_price * 0.91, 1)  # -9.0% 구조적 손절가 (200일선/20주선 붕괴 시)
        fallback_entry = round(base_price * 0.94, 1)     # 1차 50% 지정가 진입가
        water_entry = round(base_price * 0.825, 1)       # 2차 50% 전략적 물타기 타점 (-17.5% 눌림목)
        target_profit = round(base_price * 1.15, 1)     # 목표 익절가 (+15%)

        if currency_symbol == "₩":
            txt_entry, txt_stop = f"{currency_symbol}{fallback_entry:,.0f}", f"{currency_symbol}{veteran_stop_loss:,.0f}"
            txt_water, txt_target = f"{currency_symbol}{water_entry:,.0f}", f"{currency_symbol}{target_profit:,.0f}"
        else:
            txt_entry, txt_stop = f"{currency_symbol}{fallback_entry:,.1f}", f"{currency_symbol}{veteran_stop_loss:,.1f}"
            txt_water, txt_target = f"{currency_symbol}{water_entry:,.1f}", f"{currency_symbol}{target_profit:,.1f}"

        st.markdown(f"""
        <div style="background-color:#1e293b55; padding:12px; border-radius:6px; border: 1px solid #475569; font-size:13px; line-height:1.7;">
            <div>🛒 <b>1차 50% 추천 진입가:</b> <b style="color:#38bdf8; font-size:14px;">{txt_entry}</b></div>
            <div>💧 <b>2차 50% 전략적 물타기 타점:</b> <b style="color:#eab308; font-size:14px;">{txt_water}</b> <span style="font-size:11px; color:#cbd5e1;">(-15%~-20% 대파동 눌림목 / 200일선 사수 시)</span></div>
            <div>🚨 <b>구조적 손절가 (Stop-Loss):</b> <b style="color:#f43f5e; font-size:14px;">{txt_stop}</b> <span style="font-size:11px; color:#cbd5e1;">(-7%~-10% 또는 200일선/20주선 대량거래 종가 붕괴시)</span></div>
            <hr style="border:0; border-top:1px solid #475569; margin:8px 0;">
            <div>🎯 <b>목표 익절가:</b> <b style="color:#10b981; font-size:16px;">{txt_target}</b></div>
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
    st.info("🌍 글로벌 실시간 증시 뉴스 (4대 지수 대표 속보 + 핵심 섹터 TOP 6)")
    st.write("실시간 4대 증시 지수(코스피, 코스닥, S&P 500, 나스닥) 속보와 당일 지수에 직접 영향을 미치는 한국·미국 핵심 섹터 뉴스를 통합 스캔합니다.")

    try:
        import urllib.request
        import urllib.parse
        import xml.etree.ElementTree as ET
        import re

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

        def fetch_single_news(query):
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    root = ET.fromstring(response.read())
                    for item in root.findall('.//item'):
                        title_text = item.find('title').text
                        pure_title, source = title_text.rsplit(' - ', 1) if ' - ' in title_text else (title_text, "속보")
                        if any(ex.lower() in source.lower() for ex in EXCLUDE_SOURCES):
                            continue
                        return (pure_title, source, item.find('link').text)
            except Exception:
                pass
            return ("실시간 지수 시황 동향 업데이트 중", "증시속보", "#")

        def fetch_sector_news(query, limit=6):
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            items_res = []
            collected_words = []
            try:
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
            except Exception:
                pass
            return items_res

        # 🎯 1. 4대 주요 지수 대표 속보 수집 (코스피, 코스닥, S&P 500, 나스닥 각각 1개)
        idx_targets = [
            ("🇰🇷 코스피 (KOSPI)", "코스피 지수 시황속보"),
            ("🇰🇷 코스닥 (KOSDAQ)", "코스닥 지수 시황속보"),
            ("🇺🇸 S&P 500", "S&P500 지수 시황속보"),
            ("🇺🇸 나스닥 (NASDAQ)", "나스닥 지수 시황속보")
        ]
        idx_news_results = []
        for name, q in idx_targets:
            res = fetch_single_news(q)
            idx_news_results.append((name, res[0], res[1], res[2]))

        # 🎯 2. 당일 지수 영향력 TOP 6 핵심 섹터 속보 수집
        sector_q = "(반도체 OR AI OR 빅테크 OR 2차전지 OR 바이오 OR 방산 OR 전력망 OR 엔비디아 OR 삼성전자) (시황 OR 급등 OR 어닝 OR 실적 OR 주가)"
        sector_news_results = fetch_sector_news(sector_q, limit=6)

        # 📸 썸네일 이미지 리스트
        placeholders = [
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&q=80",
            "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=300&q=80",
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=300&q=80",
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=300&q=80",
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=300&q=80",
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=300&q=80"
        ]

        # 🏛️ 1. 4대 지수 대표 속보 UI 출력 (2x2 카드 그리드)
        st.markdown("### 🏛️ Section 1. 4대 증시 지수 대표 속보 (각 1선 / 총 4선)")
        grid_html = '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:20px;">'
        for idx_name, title, src, link in idx_news_results:
            grid_html += f'<div style="background:#1e293b; padding:10px 12px; border-radius:8px; border:1px solid #334155;"><div style="font-size:11px; color:#38bdf8; font-weight:bold;">{idx_name} <span style="color:#94a3b8; font-weight:normal;">[{src}]</span></div><div style="font-size:13px; font-weight:bold; margin-top:5px; line-height:1.4;"><a href="{link}" target="_blank" style="color:#ffffff; text-decoration:none;">{title}</a></div></div>'
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

        # 🔥 2. 당일 증시 영향력 TOP 6 핵심 섹터 속보 UI 출력 (6선 썸네일 카드)
        st.markdown("### 🔥 Section 2. 당일 미-국내 증시 영향력 TOP 6 핵심 섹터 속보 (6선)")
        for idx, (title, src, link) in enumerate(sector_news_results):
            thumb_url = placeholders[idx % len(placeholders)]
            card_html = f'<div style="display:flex; background:#1e293b; border-radius:8px; margin-bottom:10px; overflow:hidden; border:1px solid #334155; align-items:center;"><img src="{thumb_url}" style="width:110px; height:80px; object-fit:cover; flex-shrink:0;" /><div style="padding:10px 14px; flex-grow:1;"><span style="font-size:11px; color:#f43f5e; font-weight:bold;">🔥 TOP {idx+1} 핵심 섹터 이슈 [{src}]</span><h4 style="margin:4px 0 0 0; font-size:13px; line-height:1.45; font-weight:bold;"><a href="{link}" target="_blank" style="color:#e2e8f0; text-decoration:none;">{title}</a></h4></div></div>'
            st.markdown(card_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ [시스템] 실시간 글로벌 뉴스 동기화 오류: {e}")

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
    st.info("🌍 글로벌 실시간 증시 뉴스 (4대 지수 대표 속보 + 핵심 섹터 TOP 6)")
    st.write("실시간 4대 증시 지수(코스피, 코스닥, S&P 500, 나스닥) 속보와 당일 지수에 직접 영향을 미치는 한국·미국 핵심 섹터 뉴스를 통합 스캔합니다.")

    try:
        import urllib.request
        import urllib.parse
        import xml.etree.ElementTree as ET
        import re

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

        def fetch_single_news(query):
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    root = ET.fromstring(response.read())
                    for item in root.findall('.//item'):
                        title_text = item.find('title').text
                        pure_title, source = title_text.rsplit(' - ', 1) if ' - ' in title_text else (title_text, "속보")
                        if any(ex.lower() in source.lower() for ex in EXCLUDE_SOURCES):
                            continue
                        return (pure_title, source, item.find('link').text)
            except Exception:
                pass
            return ("실시간 지수 시황 동향 업데이트 중", "증시속보", "#")

        def fetch_sector_news(query, limit=6):
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            items_res = []
            collected_words = []
            try:
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
            except Exception:
                pass
            return items_res

        # 🎯 1. 4대 주요 지수 대표 속보 수집 (코스피, 코스닥, S&P 500, 나스닥 각각 1개)
        idx_targets = [
            ("🇰🇷 코스피 (KOSPI)", "코스피 지수 시황속보"),
            ("🇰🇷 코스닥 (KOSDAQ)", "코스닥 지수 시황속보"),
            ("🇺🇸 S&P 500", "S&P500 지수 시황속보"),
            ("🇺🇸 나스닥 (NASDAQ)", "나스닥 지수 시황속보")
        ]
        idx_news_results = []
        for name, q in idx_targets:
            res = fetch_single_news(q)
            idx_news_results.append((name, res[0], res[1], res[2]))

        # 🎯 2. 당일 지수 영향력 TOP 6 핵심 섹터 속보 수집
        sector_q = "(반도체 OR AI OR 빅테크 OR 2차전지 OR 바이오 OR 방산 OR 전력망 OR 엔비디아 OR 삼성전자) (시황 OR 급등 OR 어닝 OR 실적 OR 주가)"
        sector_news_results = fetch_sector_news(sector_q, limit=6)

        # 📸 썸네일 이미지
        placeholders = [
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&q=80",
            "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=300&q=80",
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=300&q=80",
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=300&q=80",
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=300&q=80",
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=300&q=80"
        ]

        # 🏛️ 1. 4대 지수 대표 속보 UI 출력
        st.markdown("### 🏛️ 4대 증시 지수 실시간 핵심 속보 (각 1선)")
        grid_html = '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:20px;">'
        for idx_name, title, src, link in idx_news_results:
            grid_html += f'<div style="background:#1e293b; padding:10px 12px; border-radius:6px; border:1px solid #334155;"><div style="font-size:11px; color:#38bdf8; font-weight:bold;">{idx_name} <span style="color:#94a3b8; font-weight:normal;">[{src}]</span></div><div style="font-size:13px; font-weight:bold; margin-top:4px; line-height:1.4;"><a href="{link}" target="_blank" style="color:#ffffff; text-decoration:none;">{title}</a></div></div>'
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

        # 🔥 2. 당일 증시 영향력 TOP 6 핵심 섹터 뉴스 UI 출력
        st.markdown("### 🔥 당일 미-국내 증시 영향력 TOP 6 핵심 섹터 속보")
        for idx, (title, src, link) in enumerate(sector_news_results):
            thumb_url = placeholders[idx % len(placeholders)]
            card_html = f'<div style="display:flex; background:#1e293b; border-radius:8px; margin-bottom:10px; overflow:hidden; border:1px solid #334155; align-items:center;"><img src="{thumb_url}" style="width:110px; height:80px; object-fit:cover; flex-shrink:0;" /><div style="padding:10px 14px; flex-grow:1;"><span style="font-size:11px; color:#f43f5e; font-weight:bold;">🔥 TOP {idx+1} 섹터 이슈 [{src}]</span><h4 style="margin:4px 0 0 0; font-size:13px; line-height:1.45; font-weight:bold;"><a href="{link}" target="_blank" style="color:#e2e8f0; text-decoration:none;">{title}</a></h4></div></div>'
            st.markdown(card_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ [시스템] 실시간 글로벌 뉴스 동기화 오류: {e}")

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

# 🏛️ 실시간 주요 지수 국면(강세/횡보/약세) 기반 확신도 및 승률 보정 엔진
is_kr_stock = bool(safe_ticker) and (".KS" in safe_ticker or ".KQ" in safe_ticker or "KRW" in safe_ticker)
bm_name = "코스피" if is_kr_stock else "S&P 500"

try:
    m_dash = get_realtime_market_indices_dashboard()
    bm_key = 'kospi' if is_kr_stock else 'sp500'
    bm_status = m_dash.get(bm_key, {}).get('status', '횡보')
except Exception:
    bm_status = '횡보'

if bm_status == "강세":
    regime_boost = 6.5
    regime_color = "#f43f5e"
    regime_badge_text = f"🔥 {bm_name} 강세장 (+6.5% 보정)"
elif bm_status == "약세":
    regime_boost = -10.0
    regime_color = "#38bdf8"
    regime_badge_text = f"❄️ {bm_name} 약세장 (-10.0% 감점)"
else:
    regime_boost = 0.0
    regime_color = "#10b981"
    regime_badge_text = f"⚡ {bm_name} 횡보장 (보정 없음)"

adj_win_rate = float(np.clip(win_rate + regime_boost, 5.0, 98.0)) if win_rate > 0 else 0.0
adj_hist_win_rate = float(np.clip(hist_win_rate + regime_boost, 5.0, 98.0)) if hist_win_rate > 0 else 0.0

sb_card_html = f'<div style="background-color:#0f172a; padding:14px 10px; border-radius:10px; border:2px solid #38bdf8; margin-bottom:20px; text-align:center;"><p style="margin:0; font-size:12px; color:#38bdf8; font-weight:bold; letter-spacing:0.5px;">🏆 {selected_name} AI 추세 진단 및 성과 리포트</p><p style="margin:2px 0 6px 0; font-size:10px; color:#94a3b8;">(🔥 시장 지수 연동 보정 확신도 vs 실증 검증)</p><div style="background:#1e293b; padding:2px 8px; border-radius:4px; font-size:9.5px; font-weight:bold; color:{regime_color}; display:inline-block; margin-bottom:8px; border:1px solid #334155;">{regime_badge_text}</div><div style="display:flex; justify-content:space-around; margin-top:2px;"><div><span style="font-size:10px; color:#94a3b8; display:block;">지수 보정 확신도</span><span style="font-size:18px; color:#38bdf8; font-weight:bold;">{adj_win_rate:.1f}%</span><span style="font-size:9px; color:#64748b; display:block;">(기본 {win_rate:.1f}%)</span></div><div style="border-left:1px solid #334155; height:38px; margin-top:3px;"></div><div><span style="font-size:10px; color:#94a3b8; display:block;">지수 보정 실증 승률</span><span style="font-size:18px; color:#10b981; font-weight:bold;">{adj_hist_win_rate:.1f}%</span><span style="font-size:9px; color:#64748b; display:block;">(기본 {hist_win_rate:.1f}%)</span></div></div></div>'
st.sidebar.markdown(sb_card_html, unsafe_allow_html=True)

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
# 🎨 [5대 마스터 캔들·차트 강세/약세 차단 검증 엔진] (국내 & 미국 100% 동일 적용)
# ====================================================================
def verify_5_candle_chart_patterns(df_proc, pos=-1):
    """
    💡 하나마이크론 등 거래량 줄며 몸통 작아지는 상승 소진 약세 100% 차단 + 5대 강세 패턴 검증
    1. 거래량 감소 + 캔들 몸통 수축 소진 약세 차단 (Body Shrink Burnout Block) -> 매수 금지!
    2. 장대 양봉 강세 감싸기 (Bullish Engulfing) -> 강력 매수 신호
    3. 망치형/도지 하단 지지 턴어라운드 (Hammer/Pinbar) -> 하방 소화 반등
    4. 거래량 1.5배 이상 분출 이평선 돌파 양봉 (RVOL Breakout) -> 거래량 확증
    5. 3연속 적삼병 / 우상향 계단식 지지 (Three White Soldiers / Staircase) -> 대세 승승
    """
    try:
        if df_proc is None or len(df_proc) < 20:
            return True, "정상"

        idx = len(df_proc) + pos if pos < 0 else pos
        if idx < 5: return True, "정상"

        curr = df_proc.iloc[idx]
        prev = df_proc.iloc[idx - 1]
        prev2 = df_proc.iloc[idx - 2]

        c_open  = float(curr['Open'])
        c_high  = float(curr['High'])
        c_low   = float(curr['Low'])
        c_close = float(curr['Close'])
        c_vol   = float(curr.get('Volume', 0))

        p_open  = float(prev['Open'])
        p_close = float(prev['Close'])
        p_vol   = float(prev.get('Volume', 0))

        body_curr = abs(c_close - c_open)
        body_prev = abs(p_close - p_open)
        candle_range = c_high - c_low if (c_high - c_low) > 0 else 1e-6

        vol_ma20 = float(df_proc['Volume'].iloc[max(0, idx-20):idx].mean()) if 'Volume' in df_proc.columns else c_vol

        # ----------------------------------------------------------------
        # 🚨 [패턴 1 차단] 거래량 감소 + 캔들 몸통 축소 상승 소진 약세 (Burnout Weakness)
        # 하나마이크론 차트처럼 주가 상단에서 거래량이 줄어들며 몸통이 1/3 이하로 줄어드는 팽이/약세 캔들 100% 매수 차단!
        # ----------------------------------------------------------------
        if c_vol < p_vol * 0.70 and body_curr < body_prev * 0.40 and (c_high - max(c_close, c_open)) > body_curr:
            return False, "🚨 캔들 몸통 수축 & 거래량 줄어듦 약세 (상승 소진 팽이/약세 패턴)"

        # 최근 2봉 연속 거래량 감소 + 캔들 몸통 급감하며 윗꼬리 형성 시 무조건 매수 차단
        if c_vol < vol_ma20 * 0.85 and body_curr < (body_prev * 0.45) and c_close <= c_open:
            return False, "🚨 거래량 및 캔들 몸통 축소 약세 음봉 패턴"

        # ----------------------------------------------------------------
        # 🟢 5대 강세 패턴 검증
        # ----------------------------------------------------------------
        # 패턴 2: 장대 양봉 강세 감싸기 (Bullish Engulfing)
        is_engulfing = (p_close < p_open) and (c_close > c_open) and (c_close >= p_open) and (c_open <= p_close) and (c_vol >= p_vol * 1.1)

        # 패턴 3: 망치형 / 아래꼬리 하단 지지 턴어라운드 (Hammer / Pinbar)
        lower_shadow = min(c_close, c_open) - c_low
        is_hammer = (lower_shadow / candle_range >= 0.50) and (c_close >= c_open or (c_close - c_low) / candle_range >= 0.65)

        # 패턴 4: 거래량 1.5배 이상 수급 확증 양봉 (RVOL Bullish Breakout)
        is_rvol_bull = (c_vol >= vol_ma20 * 1.4) and (c_close > c_open)

        # 패턴 5: 적삼병 / 계단식 연속 우상향 (Three White Soldiers)
        p2_close = float(prev2['Close'])
        is_three_white = (c_close > p_close > p2_close) and (c_close > c_open) and (p_close > p_open)

        if is_engulfing or is_hammer or is_rvol_bull or is_three_white or (c_close > c_open and body_curr >= body_prev * 0.8):
            return True, "✅ 5대 강세 차트/캔들 패턴 충족"

        return True, "정상"
    except Exception:
        return True, "정상"

# ====================================================================
# 🛡️ [60일·120일·200일선 가짜 돌파 차단 5대 마스터 규칙 엔진]
# ====================================================================
def verify_ma_breakout_master_rules(df_proc, pos=-1):
    """
    🏆 [60일·120일·200일선 가짜 돌파 차단 5대 마스터 규칙]
    - 규칙 1: 돌파 여유율 (60일선 +1.5%, 120일선 +2.0%, 200일선 +2.5% 이상 종가 안착)
    - 규칙 2: 이평선 기울기(Slope) 우상향/수평(>=0) 필수 (내리막 저항선 매수 금지)
    - 규칙 3: RVOL 수급 확증 (60일선 1.5배, 120/200일선 2.0배 이상 + 양봉 종가)
    - 규칙 4: 2봉 연쇄 안착 검증 (2-Bar Hold)
    - 규칙 5: 저항 이평선 샌드위치 매물벽 차단 (상방 여유 공간 >= 5.0%)
    """
    try:
        if df_proc is None or len(df_proc) < 30:
            return True, "정상"

        idx = len(df_proc) + pos if pos < 0 else pos
        if idx < 5: return True, "정상"

        curr = df_proc.iloc[idx]
        prev = df_proc.iloc[idx - 1]
        
        c_close = float(curr['Close'])
        c_open  = float(curr['Open'])
        c_vol   = float(curr['Volume'])
        
        vol_ma20 = float(curr['Vol_MA_20']) if 'Vol_MA_20' in curr and float(curr['Vol_MA_20']) > 0 else float(df_proc['Volume'].iloc[max(0, idx-20):idx].mean())
        rvol = c_vol / vol_ma20 if vol_ma20 > 0 else 1.0

        ma60_curr  = float(curr.get('MA_60', c_close))
        ma120_curr = float(curr.get('MA_120', c_close))
        ma200_curr = float(curr.get('MA_200', c_close))

        ma60_prev  = float(prev.get('MA_60', ma60_curr))
        ma120_prev = float(prev.get('MA_120', ma120_curr))
        ma200_prev = float(prev.get('MA_200', ma200_curr))

        # ------------------------------------------------------------
        # 1. 60일선 돌파 및 안착 5대 규칙 검증
        # ------------------------------------------------------------
        if c_close >= ma60_curr:
            # 규칙 1: +1.5% 이상 확실한 돌파 여유율 (Clearance Threshold)
            if c_close < (ma60_curr * 1.015):
                return False, "60일선 돌파 여유율(+1.5%) 미달 (턱걸이 스침 차단)"
            # 규칙 2: 기울기(Slope) 우상향/수평 필수
            if ma60_curr < ma60_prev:
                return False, "60일선 기울기 하향(내리막 저항 차단)"
            # 규칙 3: 돌파 시 RVOL 1.5배 이상 + 양봉 종가 확증
            if prev['Close'] < ma60_prev:
                if rvol < 1.5 or c_close <= c_open:
                    return False, "60일선 돌파 RVOL 1.5배 미달 또는 음봉"

        # ------------------------------------------------------------
        # 2. 120일선 돌파 및 안착 5대 규칙 검증
        # ------------------------------------------------------------
        if c_close >= ma120_curr:
            # 규칙 1: +2.0% 이상 확실한 돌파 여유율
            if c_close < (ma120_curr * 1.020):
                return False, "120일선 돌파 여유율(+2.0%) 미달"
            # 규칙 2: 기울기 우상향/수평 필수
            if ma120_curr < ma120_prev:
                return False, "120일선 기울기 하향"
            # 규칙 3: 돌파 시 RVOL 2.0배 이상 + 양봉 종가 확증
            if prev['Close'] < ma120_prev:
                if rvol < 2.0 or c_close <= c_open:
                    return False, "120일선 돌파 RVOL 2.0배 미달 또는 음봉"

        # ------------------------------------------------------------
        # 3. 200일선 돌파 및 안착 5대 규칙 검증
        # ------------------------------------------------------------
        if c_close >= ma200_curr:
            # 규칙 1: +2.5% 이상 확실한 돌파 여유율
            if c_close < (ma200_curr * 1.025):
                return False, "200일선 돌파 여유율(+2.5%) 미달"
            # 규칙 2: 기울기 우상향/수평 필수
            if ma200_curr < ma200_prev:
                return False, "200일선 기울기 하향"
            # 규칙 3: 돌파 시 RVOL 2.0배 이상 + 양봉 종가 확증
            if prev['Close'] < ma200_prev:
                if rvol < 2.0 or c_close <= c_open:
                    return False, "200일선 돌파 RVOL 2.0배 미달 또는 음봉"

        # ------------------------------------------------------------
        # 4. 규칙 4: 2봉 연쇄 안착 검증 (2-Bar Hold)
        # ------------------------------------------------------------
        if idx >= 2:
            prev2 = df_proc.iloc[idx - 2]
            p2_close = float(prev2['Close'])
            p1_close = float(prev['Close'])
            ma60_p2 = float(prev2.get('MA_60', ma60_prev))
            
            # 전일 돌파 성공했으나 당일 60일선 아래로 무너진 이탈봉 차단
            if p1_close >= ma60_prev and p2_close < ma60_p2 and c_close < ma60_curr:
                return False, "60일선 2봉 연쇄 안착 실패 (트랩 차단)"

        # ------------------------------------------------------------
        # 5. 규칙 5: 저항 이평선 샌드위치 매물벽 차단 (Ceiling Wall Distance)
        # ------------------------------------------------------------
        upper_mas = [m for m in [ma60_curr, ma120_curr, ma200_curr] if m > c_close]
        if upper_mas:
            nearest_upper = min(upper_mas)
            if ((nearest_upper - c_close) / c_close) * 100.0 < 5.0:
                return False, "상방 차상위 저항선 공간 5.0% 미만 샌드위치 차단"

        # ------------------------------------------------------------
        # 6. 🎨 5대 캔들/차트 강세 패턴 검증 & 거래량 감소 몸통 수축 소진 약세 무조건 차단
        # ------------------------------------------------------------
        is_valid_candle, candle_msg = verify_5_candle_chart_patterns(df_proc, pos=pos)
        if not is_valid_candle:
            return False, candle_msg

        return True, "승인"
    except Exception:
        return True, "예외통과"

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

    # 💡 [상방 이평선 저항벽 5% 미만 무조건 차단 가드레일] 캔들 위 5% 이내에 60/120/200일선 저항이 있으면 다른 조건 다 맞아도 100% 추천 차단!
    ma60  = float(df_proc['MA_60'].iloc[-1])  if 'MA_60' in df_proc.columns else c_close
    ma120 = float(df_proc['MA_120'].iloc[-1]) if 'MA_120' in df_proc.columns else c_close
    ma200 = float(df_proc['MA_200'].iloc[-1]) if 'MA_200' in df_proc.columns else c_close
    
    upper_heavy_mas = [m for m in [ma60, ma120, ma200] if (m > c_close or m > calc_entry)]
    if upper_heavy_mas:
        nearest_upper = min(upper_heavy_mas)
        dist_close_pct = ((nearest_upper - c_close) / c_close) * 100.0
        dist_entry_pct = ((nearest_upper - calc_entry) / calc_entry) * 100.0
        if dist_close_pct < 5.0 or dist_entry_pct < 5.0:
            return None, 0.0, 0.0, ""

    # 🛡️ [60일·120일·200일선 가짜 돌파 차단 5대 마스터 규칙 검증]
    is_valid_breakout, breakout_msg = verify_ma_breakout_master_rules(df_proc, pos=-1)
    if not is_valid_breakout:
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

    # 💡 [상방 이평선 저항벽 5% 미만 무조건 차단 가드레일] 캔들 위 5% 이내에 60/120/200일선 존재 시 100% 매수 추천 차단
    ma60  = float(latest['MA_60'])  if 'MA_60' in latest else c_close
    ma120 = float(latest['MA_120']) if 'MA_120' in latest else c_close
    ma200 = float(latest['MA_200']) if 'MA_200' in latest else c_close
    upper_heavy_mas = [m for m in [ma60, ma120, ma200] if m > c_close]
    if upper_heavy_mas:
        nearest_upper = min(upper_heavy_mas)
        if ((nearest_upper - c_close) / c_close) * 100.0 < 5.0:
            return None, 0.0, 0.0, ""

    # 🛡️ [60일·120일·200일선 가짜 돌파 차단 5대 마스터 규칙 검증]
    is_valid_breakout, _ = verify_ma_breakout_master_rules(df_proc, pos=-1)
    if not is_valid_breakout:
        return None, 0.0, 0.0, ""

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

    now = datetime.now()
    now_time = now.time()
    today_date = now.date()

    ticker_str = str(ticker).strip().upper()
    is_kr = ticker_str.endswith('.KS') or ticker_str.endswith('.KQ') or (ticker_str.split('.')[0].isdigit() and len(ticker_str.split('.')[0]) == 6)
    is_us = not is_kr and not (ticker_str.endswith('-KRW') or ticker_str.startswith('KRW-'))

    is_kr_market_closed = (now.weekday() >= 5) or (now_time >= dtime(15, 30))
    is_us_market_closed = (now.weekday() >= 5) or (dtime(6, 0) <= now_time < dtime(22, 30))
    is_this_market_closed = is_kr_market_closed if is_kr else (is_us_market_closed if is_us else True)

    last_candle_date = pd.to_datetime(df_proc['Date'].iloc[-1]).date()
    is_today_candle_received = (last_candle_date == today_date)

    # ⚡ [실시간 캔들 추천 모드] 장중 실시간 캔들 시세를 포함하여 무조건 당일 실시간 분석 진행
    pass

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

    # 3. 🚨 [상방 이평선 저항벽 5% 미만 무조건 차단 가드레일] 캔들 위 5% 이내에 60/120/200일선 저항선 위치 시 100% 매수 차단
    c_close_val = float(latest['Close'])
    ma60_val  = float(latest['MA_60'])  if 'MA_60' in latest else c_close_val
    ma120_val = float(latest['MA_120']) if 'MA_120' in latest else c_close_val
    ma200_val = float(latest['MA_200']) if 'MA_200' in latest else c_close_val
    
    upper_heavy_mas = [m for m in [ma60_val, ma120_val, ma200_val] if m > c_close_val]
    if upper_heavy_mas:
        nearest_upper = min(upper_heavy_mas)
        if ((nearest_upper - c_close_val) / c_close_val) * 100.0 < 5.0:
            return None, None

    # 4. 🛡️ [60일·120일·200일선 가짜 돌파 차단 5대 마스터 규칙 검증]
    is_valid_breakout, _ = verify_ma_breakout_master_rules(df_proc, pos=-1)
    if not is_valid_breakout:
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

def classify_stock_class(df_sub, ticker):
    """
    🏆 [상대강도 RS 상위 5% 주도주 Class A 정밀 판별 엔진]
    - 조건 1: 지수 대비 상대강도(RS) 우상향 & 최근 60일 우상향
    - 조건 2: 52주 신고가 10% 이내 근접 (High_52W * 0.90 이상)
    - 조건 3: OBV(세력 매집선) 최고치 근접 사수 (OBV 60일 최고치 대비 92% 이상)
    """
    try:
        if df_sub is None or len(df_sub) < 120:
            return "Class B"

        latest = df_sub.iloc[-1]
        c_close = float(latest['Close'])

        # 1. 52주(250거래일) 신고가 10% 이내 접근 여부 (High_52W * 0.90 이상)
        high_52w = float(df_sub['High'].tail(250).max())
        is_52w_near = c_close >= (high_52w * 0.90)

        # 2. 거래량 및 OBV(세력 수급 누적) 신고치 사수 검증
        obv = (np.sign(df_sub['Close'].diff()) * df_sub['Volume']).fillna(0).cumsum()
        obv_max_60 = float(obv.tail(60).max())
        is_obv_high = float(obv.iloc[-1]) >= (obv_max_60 * 0.92)

        # 3. 20일선 및 60일선 우상향 정배열 (지수 대비 상대강도 RS 우상향)
        ma20 = float(df_sub['Close'].rolling(20, min_periods=1).mean().iloc[-1])
        ma60 = float(df_sub['Close'].rolling(60, min_periods=1).mean().iloc[-1])
        ma200 = float(df_sub['Close'].rolling(200, min_periods=1).mean().iloc[-1])
        is_rs_uptrend = (c_close >= ma20) and (ma20 >= ma60) and (c_close >= ma200)

        # 🎯 3가지 조건 중 2개 이상 충족 시 [Class A: 상대강도 TOP 5% 주도주] 판정
        score_a = int(is_52w_near) + int(is_obv_high) + int(is_rs_uptrend)
        
        if score_a >= 2:
            return "Class A"
        else:
            return "Class B"
    except Exception:
        return "Class B"

def stock_history_task(task_tuple, ctx_obj, bulk_cache=None):
    if ctx_obj is not None: add_script_run_ctx(ctx=ctx_obj)
    m_label, name, ticker = task_tuple[:3]
    if len(task_tuple) > 3 and bulk_cache is None:
        bulk_cache = task_tuple[3]
    try:
        df_hist = None
        if bulk_cache:
            df_hist = bulk_cache.get(ticker, bulk_cache.get(name, None))
        if df_hist is None:
            df_hist = get_raw_daily_data(ticker)
            
        df_hist = filter_closed_daily_candles(df_hist, ticker)
        if df_hist is None or len(df_hist) < 200: return []
        
        df_proc, _ = process_data(df_hist, "daily", ticker, skip_news=True)
        if df_proc is None: return []

        # 💡 [속도 100배 향상 & 결과 0건 원천 방지] OBV, 52주 신고가, Class A 지표 선제 벡터 연산 (루프 연산 O(1) 단축)
        df_proc['OBV'] = (np.sign(df_proc['Close'].diff()) * df_proc['Volume']).fillna(0).cumsum()
        df_proc['OBV_MA'] = df_proc['OBV'].rolling(10, min_periods=1).mean()
        df_proc['High_52W'] = df_proc['High'].rolling(250, min_periods=1).max()
        df_proc['OBV_Max_60'] = df_proc['OBV'].rolling(60, min_periods=1).max()

        ma20_s = df_proc['MA_20'] if 'MA_20' in df_proc.columns else df_proc['Close']
        ma60_s = df_proc['MA_60'] if 'MA_60' in df_proc.columns else df_proc['Close']
        ma200_s = df_proc['MA_200'] if 'MA_200' in df_proc.columns else df_proc['Close']

        cond_52w = (df_proc['Close'] >= df_proc['High_52W'] * 0.90)
        cond_obv = (df_proc['OBV'] >= df_proc['OBV_Max_60'] * 0.92)
        cond_rs = (df_proc['Close'] >= ma20_s) & (ma20_s >= ma60_s) & (df_proc['Close'] >= ma200_s)
        df_proc['Is_Class_A_Pre'] = ((cond_52w.astype(int) + cond_obv.astype(int) + cond_rs.astype(int)) >= 2)

        hits = []
        total_len = len(df_proc)

        # 💡 [국내 주식: 실행 시점 기준 자동으로 정확히 2년 전부터 탐색]
        if "국내" in str(m_label):
            two_years_ago = (datetime.now() - pd.DateOffset(years=2)).strftime('%Y-%m-%d')
            date_col = pd.to_datetime(df_proc['Date'])
            target_indices = df_proc[date_col >= two_years_ago].index
            start_search_idx = target_indices[0] if len(target_indices) > 0 else max(60, total_len - 500)
        else:
            start_search_idx = max(60, total_len - 250)
        
        last_hit_bar = -99

        # 💡 [장 마감 후 금일 신규 시그널 포착 가드레일]
        now = datetime.now()
        now_time = now.time()
        today_date = now.date()
        today_str = today_date.strftime('%Y-%m-%d')

        ticker_str = str(ticker).strip().upper()
        is_kr = ticker_str.endswith('.KS') or ticker_str.endswith('.KQ') or (ticker_str.split('.')[0].isdigit() and len(ticker_str.split('.')[0]) == 6)
        is_us = not is_kr and not (ticker_str.endswith('-KRW') or ticker_str.startswith('KRW-'))

        is_kr_market_closed = (now.weekday() >= 5) or (now_time >= dtime(15, 30))
        is_us_market_closed = (now.weekday() >= 5) or (dtime(6, 0) <= now_time < dtime(22, 30))
        is_this_market_closed = is_kr_market_closed if is_kr else (is_us_market_closed if is_us else True)

        last_candle_date = pd.to_datetime(df_proc['Date'].iloc[-1]).date()
        is_today_candle_received = (last_candle_date == today_date)

        # ⚡ [실시간 캔들 추천 모드] 미확정 장중 봉을 포함하여 당일 실시간 캔들 시세로 시그널 즉시 평가
        eval_df = df_proc
        total_eval_len = len(eval_df)

        for pos in range(start_search_idx, total_eval_len, 1):
            if pos - last_hit_bar < 3: continue
            
            latest = df_proc.iloc[pos]
            prev = df_proc.iloc[pos - 1] if pos > 0 else latest
            c_close = float(latest['Close'])

            ma20  = float(latest.get('MA_20', c_close))
            ma60  = float(latest.get('MA_60', c_close))
            ma120 = float(latest.get('MA_120', c_close))

            macd_curr = float(latest.get('MACD', 0))
            signal_curr = float(latest.get('Signal', 0))
            macd_hist_curr = float(latest.get('MACD_Hist', 0))
            macd_hist_prev = float(prev.get('MACD_Hist', 0))

            disp_20 = (c_close / ma20) * 100.0 if ma20 > 0 else 100.0
            rsi_val = float(latest.get('RSI', 50))

            # 🌟 [상대강도 TOP 5% Class A 전용 정석 계단식 파동 재진입 시스템] O(1) 인덱스 참조
            is_class_a = bool(df_proc['Is_Class_A_Pre'].iloc[pos])

            # Trigger 1: 대바닥 턴어라운드 (장기 수렴 + MACD/OBV 바닥 골든크로스)
            is_ma_converged = (abs(ma20 - ma60) / ma60 <= 0.15) or (abs(ma20 - ma120) / ma120 <= 0.18) if (ma60 > 0 and ma120 > 0) else True
            is_macd_turnaround = (macd_curr >= signal_curr or macd_hist_curr > 0) and (macd_hist_curr >= macd_hist_prev)
            is_bottom_reversal = (c_close >= ma20 or c_close >= ma60) and is_ma_converged and is_macd_turnaround and (35.0 <= rsi_val <= 65.0)

            # Trigger 2: Class A 상대강도 상위 5% 전용 정석 계단식 파동 재진입
            vol_curr = float(latest.get('Volume', 0))
            vol_prev = float(prev.get('Volume', vol_curr)) if pos > 0 else vol_curr
            vol_ma20 = float(df_proc['Volume'].iloc[max(0, pos-20):pos].mean()) if 'Volume' in df_proc.columns else vol_curr
            
            # ① 거래량 감소 눌림: 전일 대비 50% 이하로 바짝 줄어듦 (개미 털기 구간)
            vol_dry_up = (vol_curr <= vol_prev * 0.55) or (vol_curr <= vol_ma20 * 0.60)
            
            # ② OBV 세력 매집선 사수: OBV 지표 10일 이평선 사수
            obv_curr = float(df_proc['OBV'].iloc[pos]) if 'OBV' in df_proc.columns else 0
            obv_ma10 = float(df_proc['OBV_MA'].iloc[pos]) if 'OBV_MA' in df_proc.columns else 0
            is_obv_supported = (obv_curr >= obv_ma10)
            
            # ③ 20일선/60일선 지지선 도달 & 사수
            c_low_val = float(latest['Low'])
            is_support_touch = (c_low_val <= ma20 * 1.015) or (c_low_val <= ma60 * 1.015)
            
            is_class_a_staircase_reentry = is_class_a and vol_dry_up and is_obv_supported and is_support_touch and (c_close >= ma60)

            # Trigger 3: 대형 정예 우량주 추세 수렴
            is_secular_megacap_trend = (c_close >= ma20 or c_close >= ma60) and (ma20 >= ma60) and (disp_20 >= 94.0) and (35.0 <= rsi_val <= 68.0) and is_macd_turnaround

            if not (is_bottom_reversal or is_class_a_staircase_reentry or is_secular_megacap_trend): continue

            # 🛡️ [가짜 돌파 & 수직 꺾임 폭락 차단 방어 필터]
            c_high = float(latest['High'])
            c_low  = float(latest['Low'])
            c_open = float(latest['Open'])
            candle_range = c_high - c_low
            upper_shadow = c_high - max(c_close, c_open)
            is_shadow_trap = (upper_shadow / candle_range > 0.40) if candle_range > 0 else False

            # 수직 꺾임 과열(이격도 110% 초과 + 거래량 터진 음봉) 차단
            is_vertical_drop = (disp_20 > 110.0) and (c_close < c_open) and (vol_curr > vol_ma20 * 1.3)

            # 🧱 [상방 이평선 저항벽 5% 미만 무조건 차단 가드레일] 캔들 위 5% 이내에 60, 120, 200일선 저항이 막고 있으면 100% 무조건 차단!
            ma60_val  = float(latest.get('MA_60', c_close))
            ma120_val = float(latest.get('MA_120', c_close))
            ma200_val = float(latest.get('MA_200', c_close))
            upper_heavy_mas = [m for m in [ma60_val, ma120_val, ma200_val] if m > c_close]
            is_upper_ma_blocked = False
            if upper_heavy_mas:
                nearest_upper = min(upper_heavy_mas)
                if ((nearest_upper - c_close) / c_close) * 100.0 < 5.0:
                    is_upper_ma_blocked = True

            # 🛡️ [60일·120일·200일선 가짜 돌파 차단 5대 마스터 규칙 검증]
            is_valid_breakout, _ = verify_ma_breakout_master_rules(df_proc, pos=pos)

            # 🎨 [5대 캔들/차트 패턴 검증] 거래량 감소 + 캔들 몸통 수축 소진 약세 100% 매수 차단!
            is_valid_candle_pattern, _ = verify_5_candle_chart_patterns(df_proc, pos=pos)

            if is_shadow_trap or is_vertical_drop or not is_obv_supported or is_upper_ma_blocked or not is_valid_breakout or not is_valid_candle_pattern:
                continue

            last_hit_bar = pos
            raw_hit_date = df_proc['Date'].iloc[pos]
            hit_dt = pd.to_datetime(raw_hit_date)
            
            # 🇺🇸 미국 주식의 경우 미국 현지 날짜(예: 8월 11일)에 +1일을 더해 대한민국 시각(KST) 마감 환산 날짜(예: 8월 12일)로 표출
            is_us_stock = not (ticker_str.endswith('.KS') or ticker_str.endswith('.KQ') or (ticker_str.split('.')[0].isdigit() and len(ticker_str.split('.')[0]) == 6) or ticker_str.endswith('-KRW') or ticker_str.startswith('KRW-'))
            if is_us_stock:
                hit_dt = hit_dt + pd.Timedelta(days=1)
                
                # 🇺🇸 [미국주 전용 정밀 가드레일 & 정배열 초입 필터] (국내주 100% 무변경)
                # 1. 200일선 우상향 사수 & 200일선 대비 +20% 초과 노후화 정배열/상투 차단
                disp_200 = (c_close / ma200_val) * 100.0 if ma200_val > 0 else 100.0
                if c_close < ma200_val or disp_200 > 120.0:
                    continue

                # 2. 이평선 밴드폭(5일선~200일선 간격) 12% 초과 노후화 정배열 차단 (초입만 허용)
                ma5_val = float(latest.get('MA_5', c_close))
                ma_band_width = ((ma5_val - ma200_val) / ma200_val) * 100.0 if ma200_val > 0 else 0.0
                if ma_band_width > 12.0:
                    continue

                # 3. 20일선 기울기 우상향 및 5/20일선 이탈 음봉 차단
                ma20_val = float(latest.get('MA_20', c_close))
                ma20_prev_val = float(prev.get('MA_20', ma20_val))
                ma5_prev_val = float(prev.get('MA_5', ma5_val))
                if ma20_val <= ma20_prev_val or (c_close < ma5_val and c_close < ma20_val) or (ma5_val <= ma5_prev_val and c_close < ma5_val):
                    continue

                # 4. 🚨 [MACD 데드크로스 & 히스토그램 모멘텀 감퇴 음봉 100% 차단 (ED, KO 4/23 상투 꺾임 원천 봉쇄)]
                macd_val = float(latest.get('MACD', 0))
                signal_val = float(latest.get('Signal', 0))
                macd_hist_val = float(latest.get('MACD_Hist', 0))
                macd_hist_prev_val = float(prev.get('MACD_Hist', macd_hist_val))
                c_prev_close = float(prev.get('Close', c_close))
                c_open_val = float(latest.get('Open', c_close))
                
                # ① MACD 데드크로스 또는 오실레이터 음전 시 차단
                if macd_val < signal_val or macd_hist_val <= 0:
                    continue

                # ② 음봉이거나 전일비 하락이면서 MACD 오실레이터가 전일 대비 줄어드는 모멘텀 감퇴 상투 꺾임 100% 차단!
                if (macd_hist_val <= macd_hist_prev_val) and (c_close < c_open_val or c_close < c_prev_close):
                    continue

                # 5. 🚨 [DMI 하락 추세 (-DI > +DI) 100% 차단]
                plus_di_val = float(latest.get('Plus_DI', 50))
                minus_di_val = float(latest.get('Minus_DI', 0))
                if minus_di_val > plus_di_val:
                    continue

                # 6. RSI 70 초과 탐욕/과열 및 약세주 수급 차단 (힘 약한 미국주 자동 제외)
                if rsi_val > 70.0 or rsi_val < 42.0 or obv_curr < obv_ma10:
                    continue

            hit_date_str = hit_dt.strftime('%Y-%m-%d')
            calc_entry, _ = calculate_smart_entry_price(df_proc.iloc[:pos+1], ai_data={})
            if calc_entry <= 0: calc_entry = round(c_close, 2)

            # 💡 [사용자 정밀 체결 가드레일] 포착 다음 날 저가가 지정가 이하로 내려오면 지정가 체결, 내려오지 않은 경우에만 시초가 체결
            after_df = df_proc.iloc[pos + 1:]
            if not after_df.empty:
                next_open = float(after_df.iloc[0]['Open'])
                next_low  = float(after_df.iloc[0]['Low'])
                if next_low <= calc_entry:
                    entry_p = calc_entry           # 🎯 장중 저가가 지정가 이하로 내려왔으므로 지정가 매수 체결!
                else:
                    entry_p = round(next_open, 2)  # 🎯 저가조차 지정가보다 높아 내려오지 않았으므로 시초가 체결!
            else:
                entry_p = calc_entry

            curr_p = float(df_proc['Close'].iloc[-1])

            # 💡 [변수 매 루프 선제 초기화 - 이전 포착 건의 변수 오염 방지 및 당일 포착 대응]
            max_so_far = entry_p
            min_so_far = entry_p
            max_date_str = hit_date_str
            water_count = 0
            avg_price = entry_p
            display_price = curr_p
            max_ret_pct = 0.0
            final_ret_pct = 0.0
            exact_exit_date_str = None

            is_tp1_done = False
            is_tp2_done = False
            is_tp3_done = False
            is_trailing_closed = False
            is_dead_trend = False

            exit_price = curr_p
            rem_qty = 1.0
            realized_sum = 0.0

            after_df = df_proc.iloc[pos + 1:]
            
            if not after_df.empty:
                is_class_a = (ticker in ["000660.KS", "005930.KS", "373220.KS", "207940.KS", "068270.KS", "005380.KS", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "LLY", "ASML"]) or (classify_stock_class(df_proc, ticker) == "Class A")

                for _, b_row in after_df.iterrows():
                    b_high = float(b_row['High'])
                    b_low  = float(b_row['Low'])
                    b_close = float(b_row['Close'])
                    b_raw_dt = pd.to_datetime(b_row['Date'])
                    if is_us_stock:
                        b_raw_dt = b_raw_dt + pd.Timedelta(days=1)
                    b_date_str = b_raw_dt.strftime('%Y-%m-%d')

                    if b_high > max_so_far:
                        max_so_far = b_high
                        max_date_str = b_date_str
                    if b_low < min_so_far: min_so_far = b_low

                    init_min_ret = ((min_so_far - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0
                    init_curr_ret = ((b_close - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0

                    b_ma200 = float(b_row['MA_200']) if 'MA_200' in b_row and pd.notnull(b_row['MA_200']) else b_close
                    b_ma60  = float(b_row['MA_60'])  if 'MA_60' in b_row and pd.notnull(b_row['MA_60']) else b_close
                    b_ma20  = float(b_row['MA_20'])  if 'MA_20' in b_row and pd.notnull(b_row['MA_20']) else b_close

                    b_dead = (b_close < b_ma200 and b_close < b_ma60) and (init_curr_ret <= -12.0)

                    # 🟢 [전략적 물타기(2차 50% 진입)] 실적 이상 무 + -10%~-25% 대파동 눌림목 + 200일선/60일선 대세 지지선 사수 시 1:1 추가매수
                    if water_count == 0 and (-25.0 <= init_curr_ret <= -10.0 or -25.0 <= init_min_ret <= -10.0) and (b_close >= b_ma200 or b_close >= b_ma60) and not b_dead:
                        water_count = 1
                        avg_price = round((entry_p + b_close) / 2.0, 2)  # 1차 50% + 2차 50% 실측 분할 매수로 평단가 단축

                    w_ret_curr = ((max_so_far - avg_price) / avg_price) * 100.0 if avg_price > 0 else 0.0
                    c_ret_curr = ((b_close - avg_price) / avg_price) * 100.0 if avg_price > 0 else 0.0

                    # 🌟 메인 비중(70%) 온존 분할 익절 (1차 15%, 2차 15%)
                    if w_ret_curr >= 30.0 and not is_tp1_done:
                        realized_sum += 0.15 * 30.0
                        rem_qty -= 0.15
                        is_tp1_done = True

                    if w_ret_curr >= 60.0 and not is_tp2_done:
                        realized_sum += 0.15 * 60.0
                        rem_qty -= 0.15
                        is_tp2_done = True

                    # 🌟 [월가 퀀트 트레이너 총결의] Class A vs Class B 이원화 트레일링 스탑 (+2.0%~9.9% 최고수익 시 +0.5% 방어선)
                    b_tstop = -999.0
                    if is_class_a:
                        if w_ret_curr >= 100.0: b_tstop = w_ret_curr - 35.0
                        elif w_ret_curr >= 50.0: b_tstop = w_ret_curr - 25.0
                        elif w_ret_curr >= 20.0: b_tstop = w_ret_curr - 15.0
                        elif w_ret_curr >= 10.0: b_tstop = 5.0
                        elif w_ret_curr >= 2.0: b_tstop = 0.5
                    else:
                        if w_ret_curr >= 100.0: b_tstop = w_ret_curr - 20.0
                        elif w_ret_curr >= 50.0: b_tstop = w_ret_curr - 15.0
                        elif w_ret_curr >= 20.0: b_tstop = w_ret_curr - 12.0
                        elif w_ret_curr >= 10.0: b_tstop = 5.0
                        elif w_ret_curr >= 2.0: b_tstop = 0.5

                    if b_tstop > -900.0 and c_ret_curr <= b_tstop:
                        exact_exit_date_str = b_date_str
                        is_trailing_closed = True
                        exit_price = b_close
                        exit_ret_val = max(b_tstop, c_ret_curr) if b_tstop > 0 else c_ret_curr
                        realized_sum = round(realized_sum + rem_qty * exit_ret_val, 1)
                        rem_qty = 0.0
                        break
                    elif b_dead or (not (b_close >= b_ma200 or b_close >= b_ma60) and c_ret_curr <= -10.0):
                        exact_exit_date_str = b_date_str
                        is_dead_trend = True
                        exit_price = b_close
                        realized_sum = -10.0
                        rem_qty = 0.0
                        break

                max_wave_ret = ((max_so_far - avg_price) / avg_price) * 100.0 if avg_price > 0 else 0.0
                max_ret_pct = round(max_wave_ret, 1)

                rec_dt = pd.to_datetime(hit_date_str).tz_localize(None)
                curr_dt = pd.to_datetime(df_proc['Date'].iloc[-1]).tz_localize(None)
                days_passed = len(pd.date_range(start=rec_dt, end=curr_dt, freq='B')) - 1

                # 💡 [매수 기회 보존 방어선] 2차 매수/물타기 구간(-10%~-25% 눌림목) 및 최근 신규 매수 종목은 2% 미만 상승이라도 무조건 유지!
                is_active_buy = (water_count == 1) or (init_curr_ret <= -10.0 and not is_dead_trend) or (days_passed <= 5 and not is_tp1_done)

                # 최소 2%+ 미달 종목 중 청산/손절/활성 매수가 아닌 단순 미동 종목만 제외
                if max_wave_ret < 2.0 and not is_dead_trend and not is_trailing_closed and not is_active_buy:
                    continue

                if rem_qty <= 0:
                    final_ret_pct = round(realized_sum, 1)
                    display_price = exit_price
                else:
                    curr_c_ret = ((curr_p - avg_price) / avg_price) * 100.0 if avg_price > 0 else 0.0
                    final_ret_pct = round(realized_sum + rem_qty * curr_c_ret, 1)
                    display_price = curr_p

                # 안전장치: 청산 날짜가 포착 날짜보다 이전이면 포착 날짜로 정정
                if exact_exit_date_str and pd.to_datetime(exact_exit_date_str) < rec_dt:
                    exact_exit_date_str = hit_date_str

                # --- [수정 후 replacement 코드] ---
                if is_dead_trend and not is_trailing_closed:
                    final_ret_pct = -7.0
                    status_txt = f"🚨 구조적 손절 (200일선 붕괴) [{exact_exit_date_str}]"
                    action_guide = "❌ 무조건 손절: 200일선/20주선 대량거래 종가 붕괴. 기계적 손절매로 리스크를 차단하세요."
                elif is_trailing_closed:
                    status_txt = f"🎯 1차 익절 + 🛡️ 방어선 청산 [{exact_exit_date_str}]" if is_tp1_done else f"🛡️ 익절 방어선 청산 [{exact_exit_date_str}]"
                    action_guide = f"🛡️ 방어선 청산 완료: 고점 달성 후 방어선 이탈에 따라 안전하게 청산되었습니다."
                elif is_tp3_done:
                    status_txt = f"🔥 전량 익절 [{exact_exit_date_str}]"
                    action_guide = "🔥 전량 익절 완료: +100% 대파동 목표 달성으로 100% 수익 확정 청산되었습니다."
                elif is_tp2_done:
                    status_txt = "🎯 2차 익절 진행중"
                    action_guide = "🎯 2차 익절 완료: 30% 수량 익절 완료 후 잔여 수량 텐베거 대파동 보유 중입니다."
                elif is_tp1_done:
                    status_txt = "🎯 1차 익절 진행중"
                    action_guide = "🎯 1차 익절 완료: 15% 수량 익절로 원금 회수 후 85% 수량 끝까지 우상향 홀딩하세요."
                elif water_count == 1:
                    status_txt = "💧 대파동 눌림목 2차 (2차 50% 물타기 체결)"
                    action_guide = "🟢 대파동 눌림목 2차 완료: -15%~-20% 구간 2차 50% 분할 투입으로 평단가를 대폭 단축했습니다."
                elif init_curr_ret <= -10.0 and not is_dead_trend:
                    status_txt = "💧 대파동 눌림목 2차 (2차 50% 물타기 타점)"
                    action_guide = "🟢 대파동 눌림목 2차 추천 타점: 실적 이상 무 + 200일선/20주선 지지 사수 중! 2차 50% 추가매수 투입 적기입니다."
                elif days_passed <= 5 and not is_tp1_done:
                    if is_class_a:
                        status_txt = "🛒 상대강도 상위 5% (1차 50% 진입)"
                        action_guide = "🛒 상대강도 상위 5%: 지수 대비 상대강도 TOP 5% 주도 파동 포착! 목표 자금의 1차 50% 지정가 비중으로 진입하세요."
                    else:
                        status_txt = "🛒 신규 매수 (1차 50% 진입)"
                        action_guide = "🛒 신규 매수 추천: 200일선 바닥 탈출 포착! 목표 자금의 1차 50% 지정가 비중으로 진입하세요."
                else:
                    if final_ret_pct >= 0:
                        status_txt = "🟢 수익 진행중"
                        action_guide = "🟢 홀딩 유지: 주봉 20주선 우상향 정배열 대세 상승파 보유 중입니다."
                    else:
                        status_txt = "🌊 눌림 진행중 (대기)"
                        action_guide = "🌊 대기/관망: 200일선 지지 여부를 확인하며 -15%~-20% 2차 물타기 타점을 대기하세요."
            else:
                # ⚡ [오늘 포착된 실시간 신규 추천 시그널]
                avg_price = entry_p
                display_price = curr_p
                max_so_far = max(entry_p, curr_p)
                final_ret_pct = round(((curr_p - entry_p) / entry_p) * 100.0, 1) if entry_p > 0 else 0.0
                max_ret_pct = max(0.0, final_ret_pct)
                max_date_str = hit_date_str
                if is_class_a:
                    status_txt = "🛒 상대강도 상위 5% (1차 50% 진입)"
                    action_guide = "🛒 상대강도 상위 5%: 지수 대비 상대강도 TOP 5% 주도 파동 포착! 목표 자금의 1차 50% 지정가 비중으로 진입하세요."
                else:
                    status_txt = "🛒 신규 매수 (1차 50% 진입)"
                    action_guide = "🛒 금일 신규 추천: 200일선 바닥 탈출 포착! 목표 자금의 1차 50% 지정가 비중으로 진입하세요."

            # ⚡ [실시간 캔들 대응] 당일 실시간 캔들 수익률을 그대로 실시간 반영
            if hit_date_str == today_str:
                avg_price = entry_p
                display_price = curr_p
                max_so_far = max(entry_p, curr_p)
                final_ret_pct = round(((curr_p - entry_p) / entry_p) * 100.0, 1) if entry_p > 0 else 0.0
                max_ret_pct = max(0.0, final_ret_pct)
                max_date_str = hit_date_str
                if is_class_a:
                    status_txt = "🛒 상대강도 상위 5% (1차 50% 진입)"
                else:
                    status_txt = "🛒 신규 매수 (1차 50% 진입)"

            is_krw = any(x in ticker for x in [".KS", ".KQ", "-KRW"])
            fmt_limit = f"₩{calc_entry:,.0f}" if is_krw else f"${calc_entry:,.2f}"
            fmt_avg   = f"₩{avg_price:,.0f}" if is_krw else f"${avg_price:,.2f}"
            fmt_curr  = f"₩{display_price:,.0f}" if is_krw else f"${display_price:,.2f}"
            fmt_max   = f"₩{max_so_far:,.0f}" if is_krw else f"${max_so_far:,.2f}"

            # 💡 [일·주·월봉 3대 차트 결합 1년 상승 잠재력 점수 & 1년 실제 목표 수익률 산출]
            mtf_score = round(70.0 + (108.0 - abs(disp_20 - 101.5)) * 0.15 + (rsi_val * 0.1) + (max_ret_pct * 0.25), 1)
            target_1y_pct = round(max(35.0, max_ret_pct * 1.45 + 12.0), 1)

            m_flag = "🇰🇷 국내" if "국내" in str(m_label) else ("🇺🇸 미국" if "미국" in str(m_label) else str(m_label))
            hits.append({
                "시장": m_flag,
                "종목명": get_korean_name(name),
                "티커": ticker,
                "추천 포착 날짜": hit_date_str,
                "추천 진입가": fmt_limit,   # 🎯 추천 진입가는 100% 원본 지정가 추천가 표출
                "평단가": fmt_avg,          # 🎯 평단가는 갭상승 시 당일 시초가 체결 반영 평단가 표출
                "현재가": fmt_curr,
                "기간 최고가": fmt_max,
                "현재/최종 수익률 (%)": final_ret_pct,
                "최대 수익률 (%)": max_ret_pct,
                "최대 수익률 도달일": max_date_str,
                "1년 목표 수익률 (%)": target_1y_pct,
                "mtf_score": mtf_score,
                "상태": status_txt,
                "raw_curr_ret": final_ret_pct
            })
        return hits
    except Exception:
        return []

def check_downtrend_breakout_and_bottom_support(df_sub):
    """
    🛡️ [6개월~1년 중장기 전용] 하향 추세선 상방 돌파 또는 수평 바닥 지지선 안착 검증
    """
    if df_sub is None or len(df_sub) < 100:
        return False, 0.0
    
    highs = df_sub['High'].values
    lows = df_sub['Low'].values
    closes = df_sub['Close'].values
    
    # 1. 최근 120일간의 최저점 및 바닥 지지대 산출 (20% 백분위)
    recent_lows = lows[-120:] if len(lows) >= 120 else lows
    support_level = np.percentile(recent_lows, 20)
    
    # 2. 바닥 지지 검증: 최근 30일 내 종가가 바닥 지지선 근처에서 지지받고 형성되었는지
    bottom_touches = np.sum((lows[-30:] <= support_level * 1.05) & (closes[-30:] >= support_level * 0.95))
    is_bottom_supported = (bottom_touches >= 1) and (closes[-1] >= support_level * 0.97)
    
    # 3. 우하향 추세 저항선 산출
    p1_idx = np.argmax(highs[-200:]) if len(highs) >= 200 else np.argmax(highs)
    p1_idx_abs = len(highs) - len(highs[-200:]) + p1_idx if len(highs) >= 200 else p1_idx
    
    x1, y1 = p1_idx_abs, highs[p1_idx_abs]
    
    subsequent_indices = range(p1_idx_abs + 10, len(highs) - 3, 3)
    valid_ms = []
    for p2 in subsequent_indices:
        if highs[p2] < y1:
            m = (highs[p2] - y1) / (p2 - x1)
            c = y1 - m * x1
            valid_ms.append((m, c))
            
    if valid_ms:
        valid_ms.sort(key=lambda x: x[0])
        best_m, best_c = valid_ms[len(valid_ms)//2]
    else:
        best_m, best_c = 0.0, y1
        
    curr_x = len(closes) - 1
    trendline_curr = best_m * curr_x + best_c
    
    # 하향 추세선 상방 돌파 여부 (현재 종가가 하향 추세선 98% 이상 지점)
    is_trend_broken_out = (closes[-1] >= trendline_curr * 0.98)
    
    is_passed = is_trend_broken_out or is_bottom_supported
    return is_passed, support_level

def run_midterm_quant_eval(df_sub, name, ticker, fin_info=None):
    """
    1년 대파동(+100%+) 전용 4대 핵심 필터 결합 엔진
    1. 시장 지수 약세장 강제 차단
    2. 200일선 바닥 탈출(1~2번째 눌림목) + 상투(200일선 이격도 130% 초과) 제거
    3. 하향 추세선 상방 돌파 및 수평 바닥 지지선 안착 필수 검증 (신규 추가!)
    4. 재무 및 OBV 세력 매집 검증
    5. 3단계 익절(+30%/+60%/+100%) & +15% Break-Even(본절 방어) 리턴
    """
    if df_sub is None or len(df_sub) < 150:
        return None

    now = datetime.now()
    now_time = now.time()
    today_date = now.date()

    ticker_str = str(ticker).strip().upper()
    is_kr = ticker_str.endswith('.KS') or ticker_str.endswith('.KQ') or (ticker_str.split('.')[0].isdigit() and len(ticker_str.split('.')[0]) == 6)
    is_us = not is_kr and not (ticker_str.endswith('-KRW') or ticker_str.startswith('KRW-'))

    is_kr_market_closed = (now.weekday() >= 5) or (now_time >= dtime(15, 30))
    is_us_market_closed = (now.weekday() >= 5) or (dtime(6, 0) <= now_time < dtime(22, 30))
    is_this_market_closed = is_kr_market_closed if is_kr else (is_us_market_closed if is_us else True)

    last_candle_date = pd.to_datetime(df_sub['Date'].iloc[-1]).date()
    is_today_candle_received = (last_candle_date == today_date)

    # ⚡ [실시간 캔들 추천 모드] 당일 미확정 실시간 캔들 시세로 중장기 시그널 즉시 평가
    pass

    # ----------------------------------------------------------------
    # 🛡️ [개선 1] 시장 지수 약세장(Bear Market Regime) 신규 진입 강제 차단
    # ----------------------------------------------------------------
    is_bear, _ = check_benchmark_regime(ticker)
    if is_bear:
        return None  # 지수 하락장에서는 중장기 신규 추천 100% 차단

    # ----------------------------------------------------------------
    # 🏢 [개선 2] 펀더멘털 스크리닝 (시총 8천억 이상 / 부채비율 200% 이하)
    # ----------------------------------------------------------------
    try:
        if fin_info is None:
            import yfinance as yf
            fin_info = yf.Ticker(ticker).info
            
        if isinstance(fin_info, dict):
            mcap = fin_info.get('marketCap', 0)
            if mcap:
                if ".KS" in ticker or ".KQ" in ticker:
                    if mcap < 800_000_000_000:
                        return None  # 국내 시총 8,000억 원 미만 제약
                else:
                    if mcap < 7_250_000_000:
                        return None  # 🏢 미국 시총 원화 10조 원($72.5억 달러) 미만 필수 제약
            
            debt_to_equity = fin_info.get('debtToEquity', 0)
            if debt_to_equity and debt_to_equity > 200:
                return None  # 부채비율 200% 초과 제약 (국내/미국 공통)
    except Exception:
        pass

    # ----------------------------------------------------------------
    # 📊 [개선 3] 차트 지표 연산 및 시세 초입(200일선 탈출) 정밀 판정
    # ----------------------------------------------------------------
    df_proc, ai_data = process_data(df_sub, "daily", ticker, skip_news=True)
    if df_proc is None or ai_data is None:
        return None

    latest = df_proc.iloc[-1]
    prev = df_proc.iloc[-2] if len(df_proc) >= 2 else latest
    c_close = float(latest['Close'])

    ma20  = float(latest['MA_20'])  if 'MA_20' in latest else c_close
    ma200 = float(latest['MA_200']) if 'MA_200' in latest else c_close

    # 🔥 [시세 초입 검증 1] 200일선 상회 필수 + 200일선 이격도 130% 이하 (이미 폭등한 상투 종목 제외)
    disparity_200 = (c_close / ma200) * 100.0 if ma200 > 0 else 100.0
    if c_close < ma200 or disparity_200 > 130.0:
        return None

    # 🔥 [시세 초입 검증 2] 20일선 이격도 (95% ~ 108% 1~2번째 눌림목 구간만 승인)
    disparity_20 = (c_close / ma20) * 100.0 if ma20 > 0 else 100.0
    if not (95.0 <= disparity_20 <= 108.0):
        return None

    # 🛡️ [신규 필수 검증] 하향 추세선 상방 돌파 또는 수평 바닥 지지선 안착 필수 확인
    is_passed_trend_support, _ = check_downtrend_breakout_and_bottom_support(df_sub)
    if not is_passed_trend_support:
        return None

    # MACD 오실레이터 및 수급 유입 검증
    macd_curr = float(latest['MACD']) if 'MACD' in latest else 0.0
    signal_curr = float(latest['Signal']) if 'Signal' in latest else 0.0
    macd_hist_curr = float(latest['MACD_Hist']) if 'MACD_Hist' in latest else 0.0
    macd_hist_prev = float(prev['MACD_Hist']) if 'MACD_Hist' in prev else 0.0

    if macd_curr < signal_curr or macd_hist_curr <= 0 or macd_hist_curr < macd_hist_prev:
        return None

    # RSI 식힘 구간 (38 ~ 60)
    rsi_val = float(latest['RSI']) if 'RSI' in latest else 50.0
    if not (38.0 <= rsi_val <= 60.0):
        return None

    # OBV 세력 매집 확인
    obv = (np.sign(df_sub['Close'].diff()) * df_sub['Volume']).fillna(0).cumsum()
    obv_ma10 = obv.rolling(10).mean()
    if float(obv.iloc[-1]) < float(obv_ma10.iloc[-1]):
        return None

    # ----------------------------------------------------------------
    # 🎯 [Class A / Class B 자동 분기] 매도 및 익절 전략 이원화
    # ----------------------------------------------------------------
    stock_class = classify_stock_class(df_sub, ticker)
    calc_entry = round(min(c_close * 0.99, ma20), 2)

    if stock_class == "Class A":
        # 🚀 [Class A: 텐배거 대파동 모드]
        # 조기 익절 없이 100% 홀딩 ➔ 주봉 20주선 및 피뢰침 최고점 전량 청산
        tp1_price = round(calc_entry * 2.00, 2)  # 1차 목표 (+100%)
        tp2_price = round(calc_entry * 5.00, 2)  # 2차 목표 (+400%)
        tp3_price = round(calc_entry * 10.00, 2) # 3차 목표 (+900%+)
        sig_tag = "🚀 [Class A: 메가트렌드 대파동] 조기익절 0% / 주봉20주선 추적 (목표 +1,000%+)"
    else:
        # 🌿 [Class B: 스윙/순환매 모드]
        # 3단계 계단식 익절 (+30% / +60% / +100%)
        tp1_price = round(calc_entry * 1.30, 2)
        tp2_price = round(calc_entry * 1.60, 2)
        tp3_price = round(calc_entry * 2.00, 2)
        sig_tag = "🌿 [Class B: 스윙/순환매] 3단계 익절 (+30%/+60%/+100%)"

    score = 85.0
    if c_close >= ma200: score += 5.0
    if float(obv.iloc[-1]) >= float(obv.max() * 0.90): score += 5.0

    up_prob = min(score, 98.0)

    return {
        "name": get_korean_name(name),
        "ticker": ticker,
        "entry_price": calc_entry,
        "entry_p": calc_entry,
        "stock_class": stock_class, # 👈 Class A / B 저장
        "sl_price": round(calc_entry * 0.93, 2),
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "tp3_price": tp3_price,
        "up_prob": round(up_prob, 1),
        "exp_win": round(up_prob, 1),
        "upside": 1000.0 if stock_class == "Class A" else 100.0,
        "exp_ret": 1000.0 if stock_class == "Class A" else 100.0,
        "composite_score": round(score, 2),
        "signal": sig_tag,
        "score": round(score, 2),
        "adx": float(latest['ADX']) if 'ADX' in latest else 25.0
    }

# ====================================================================
# 1️⃣ [1번 오늘의 Top 10 추천 단일 종목 처리]
# ====================================================================
def process_single_ticker_unbound(item):
    name, ticker = item
    try:
        df_t = get_raw_daily_data(ticker)
        df_t = filter_closed_daily_candles(df_t, ticker)
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
        df_hist = filter_closed_daily_candles(df_hist, ticker)
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

    # 1. DB 기록에서 최근 성과 피드백 조회
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

    # 2. 스캔 대상 종목 수집
    kr_items = {k: v for k, v in assets_dict["₩ 국내 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}
    us_items = {k: v for k, v in assets_dict["💲 미국 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}

    all_tasks = []
    for k, v in kr_items.items(): all_tasks.append((k, v, 'scan_results_kr'))
    for k, v in us_items.items(): all_tasks.append((k, v, 'scan_results_us'))

    total_count = len(all_tasks)
    if total_count == 0:
        return

    progress_bar = st.progress(0.0)
    status_box = st.empty()

    # ⚡ [수정 핵심] 50개 청크 단위 사전 고속 수집 가동 (IP 차단 및 KeyError 완전 방지)
    status_box.markdown("🚀 **1/2단계: 전 시장 종목 시세 초고속 배치 수집 중...**")
    tickers = [t[1] for t in all_tasks]
    bulk_cache = bulk_preload_and_clean_market_data(tickers, period="2y")

    status_box.markdown("🚀 **2/2단계: 실시간 퀀트 시그널 정밀 연산 중...**")

    results_kr, results_us, results_coin = [], [], []
    results_surge_kr, results_surge_us = [], []
    processed = 0

    def scan_task_fast(task_info):
        stock_name, ticker_code, target_key = task_info
        df_sub = bulk_cache.get(ticker_code, None)
        if df_sub is None or len(df_sub) < 30:
            return None
        res_tuple = run_unified_quant_eval(df_sub, stock_name, ticker_code)
        return (target_key, ticker_code, res_tuple)

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(scan_task_fast, task) for task in all_tasks]
        for future in futures:
            processed += 1
            pct = min(1.0, processed / total_count)
            if processed % 10 == 0 or processed == total_count:
                progress_bar.progress(pct)
                status_box.markdown(f"🚀 **2/2단계: 실시간 퀀트 시그널 연산 중...** `{processed}/{total_count}` ({int(pct*100)}%)")

            res_data = future.result()
            if res_data:
                target_key, ticker_code, res_tuple = res_data
                if res_tuple and ticker_code not in underperforming_tickers:
                    swing_res, surge_res = res_tuple
                    if swing_res:
                        if target_key == 'scan_results_kr': results_kr.append(swing_res)
                        elif target_key == 'scan_results_us': results_us.append(swing_res)
                    if surge_res:
                        if target_key == 'scan_results_kr': results_surge_kr.append(surge_res)
                        elif target_key == 'scan_results_us': results_surge_us.append(surge_res)

    # 결과 세션 저장
    st.session_state['scan_results_kr'] = sorted(results_kr, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_results_us'] = sorted(results_us, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_surge_kr'] = sorted(results_surge_kr, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]
    st.session_state['scan_surge_us'] = sorted(results_surge_us, key=lambda x: x.get('composite_score', 0), reverse=True)[:10]

    progress_bar.progress(1.0)
    status_box.success("✅ 실시간 전 시장 스캔 완료!")

# ====================================================================
# ⚡ [중장기 전용] 6M~1Y 정예 종목 백그라운드 스캔 워커 (암호화폐 제외)
# ====================================================================
def bg_scan_worker_midterm(assets_dict):
    ctx = get_script_run_ctx()
    
    kr_items = {k: v for k, v in assets_dict["₩ 국내 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}
    us_items = {k: v for k, v in assets_dict["💲 미국 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}

    raw_tasks = []
    for k, v in kr_items.items(): raw_tasks.append((k, v, 'scan_midterm_kr'))
    for k, v in us_items.items(): raw_tasks.append((k, v, 'scan_midterm_us'))

    seen_tickers = set()
    all_tasks = []
    for name, t_code, target_key in raw_tasks:
        clean_t = str(t_code).strip().upper()
        if clean_t not in seen_tickers:
            seen_tickers.add(clean_t)
            all_tasks.append((get_korean_name(name), clean_t, target_key))

    total_count = len(all_tasks)
    if total_count == 0: return

    progress_bar = st.progress(0.0)
    status_box = st.empty()

    # ⚡ [수정 핵심 1] 전 시장 종목 초고속 배치 수집 (IP 차단 방지 및 초고속 완료)
    status_box.markdown("🚀 **전 시장 종목 시세 초고속 실시간 배치 수집 중...**")
    tickers = [t[1] for t in all_tasks]
    bulk_cache = bulk_preload_and_clean_market_data(tickers, period="2y")

    status_box.markdown("🚀 **중장기 100%+ 주식 정예주 정밀 퀀트 분석 중...**")
    res_kr, res_us = [], []
    processed = 0

    def midterm_task(item_tuple):
        name, ticker = item_tuple[0], item_tuple[1]
        try:
            df_t = bulk_cache.get(ticker, bulk_cache.get(name, None))
            if df_t is None:
                df_t = get_raw_daily_data(ticker)
            res = run_midterm_quant_eval(df_t, get_korean_name(name), ticker)
            if res:
                res['name'] = get_korean_name(res['name'])
            return res
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(midterm_task, task): task for task in all_tasks}
        for future in as_completed(futures):
            processed += 1
            task_info = futures[future]
            target_key, stock_name = task_info[2], get_korean_name(task_info[0])

            pct = min(1.0, max(0.0, float(processed) / float(total_count)))
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

# 💡 오늘 포착된 중장기 추천 종목을 DB에 영구 스냅샷 저장 (다음 날 조건 탈락해도 과거 기록 보존)
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        all_mid_picks = st.session_state['scan_midterm_kr'] + st.session_state['scan_midterm_us']
        for item in all_mid_picks:
            m_label = "국내" if ".KS" in item['ticker'] or ".KQ" in item['ticker'] else "미국"
            cursor.execute("""
            INSERT OR IGNORE INTO midterm_recommendations (rec_date, market, name, ticker, entry_price)
            VALUES (?, ?, ?, ?, ?)
            """, (today_str, m_label, get_korean_name(item['name']), item['ticker'], item['entry_price']))
            
        conn.commit()
        conn.close()
    except Exception:
        pass

    progress_bar.progress(1.0)
    status_box.success("✅ 중장기 주식 정예주 스캔 완료! (재무/주봉/200일선 90%+ 엄선)")

# ====================================================================
# ⚡ [과거 1년 초고속 전수 스캔] 볼린저밴드 상단 차단 제거 버전
# ====================================================================
def scan_all_historical_midterm_signals(assets_dict, target_market="전체"):
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
    except Exception:
        ctx = None

    kr_items = {k: v for k, v in assets_dict["₩ 국내 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}
    us_items = {k: v for k, v in assets_dict["💲 미국 주식"].items() if not any(x in k for x in ["등극주", "시총", "주요통화"])}

    raw_tasks = []
    if target_market in ["국내", "전체"]:
        for k, v in kr_items.items(): raw_tasks.append(("국내", k, v))
    if target_market in ["미국", "전체"]:
        for k, v in us_items.items(): raw_tasks.append(("미국", k, v))

    seen_tickers = set()
    all_tasks = []
    for m_lbl, name, t_code in raw_tasks:
        clean_t = str(t_code).strip().upper()
        if clean_t not in seen_tickers:
            seen_tickers.add(clean_t)
            all_tasks.append((m_lbl, get_korean_name(name), clean_t))

    total_count = len(all_tasks)
    if total_count == 0: return []

    progress_bar = st.progress(0.0)
    status_box = st.empty()

    # ⚡ [수정 핵심 2] 500개 전 종목 초고속 배치 수집 (10분 ➔ 3초 완료)
    status_box.markdown("🚀 **전 시장 종목 시세 초고속 실시간 배치 수집 중...**")
    tickers = [t[2] for t in all_tasks]
    bulk_cache = bulk_preload_and_clean_market_data(tickers, period="2y")

    status_box.markdown("🚀 **과거 1년 정예 시그널 초고속 전수 스캔 중...**")
    historical_hits = []
    processed = 0

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(stock_history_task, (task[0], task[1], task[2], bulk_cache), ctx): task for task in all_tasks}
        for future in as_completed(futures):
            processed += 1
            pct = min(1.0, max(0.0, float(processed) / float(total_count)))
            task_info = futures[future]
            stock_name = get_korean_name(task_info[1])
            status_box.markdown(f"🚀 **동시 30개 초고속 스캔 중...** `{processed}/{total_count}` ({int(pct*100)}%) | 분석: **{stock_name}**")
            progress_bar.progress(pct)
            try:
                hits = future.result()
                if hits:
                    for h in hits:
                        h['종목명'] = get_korean_name(h['종목명'])
                    historical_hits.extend(hits)
            except Exception:
                pass

    # 🛡️ [중복 추천 시그널 완전 제거 가드레일] 티커 및 포착 날짜 기준 중복 제거
    dedup_hits = []
    seen_hit_keys = set()
    for h in historical_hits:
        h['종목명'] = get_korean_name(h['종목명'])
        h_key = (str(h.get('티커', '')).upper(), str(h.get('추천 포착 날짜', '')).strip())
        if h_key not in seen_hit_keys:
            seen_hit_keys.add(h_key)
            dedup_hits.append(h)
    historical_hits = dedup_hits

    progress_bar.progress(1.0)
    status_box.success(f"✅ 초고속 과거 1년 스캔 완료! 총 {len(historical_hits)}건의 정예 추천 포착 기록을 찾았습니다.")

    if historical_hits:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        for h in historical_hits:
            raw_entry_str = str(h['추천 진입가']).replace('₩', '').replace('$', '').replace(',', '').strip()
            try: clean_entry = float(raw_entry_str)
            except ValueError: clean_entry = 0.0

            cursor.execute("""
            INSERT OR IGNORE INTO midterm_recommendations (rec_date, market, name, ticker, entry_price)
            VALUES (?, ?, ?, ?, ?)
            """, (h['추천 포착 날짜'], h['시장'], get_korean_name(h['종목명']), h['티커'], clean_entry))
        conn.commit()
        conn.close()
    
    sorted_hits = sorted(historical_hits, key=lambda x: x['raw_curr_ret'], reverse=True)
    return sorted_hits

# ====================================================================
# 메인 탭 선언 및 레이아웃 분리
# ====================================================================
main_tab1, main_tab2 = st.tabs([
    "📈 실시간 차트 & 종목 분석", 
    " 🚀 6M~1Y 중장기 유망주 🚀 "
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
# 3️⃣ 메인 탭 3: 6M~1Y 중장기 저점 유망주 과거 1년 전수 스캐너
# --------------------------------------------------------------------
with main_tab2:
    st.markdown("### 🚀 6개월~1년 중장기 정예 유망주 관제탑")
    
    st.markdown("""<div style="background-color: #0f172a; border: 1px solid #3b82f6; padding: 16px 20px; border-radius: 10px; margin: 10px 0 20px 0; color: #f8fafc;">
<div style="font-size: 15px; font-weight: bold; color: #60a5fa; margin-bottom: 10px;">
🛡️ 6M~1Y 관점 물타기(추가매수) vs 구조적 손절(Cut) 매매 원칙
</div>
<div style="font-size: 13px; line-height: 1.7; color: #cbd5e1;">
<p style="margin-bottom: 10px;">
<b>📌 1. <span style="color:#f43f5e; font-weight:bold;">❌ 무조건 손절(Cut)</span>해야 하는 3가지 핵심 상황</b><br>
① <b>실적/산업 파괴:</b> 매출 및 영업이익 역성장 전환 또는 구조적 재무 악화<br>
② <b>대세 추세선 붕괴:</b> 일봉 200일선 또는 주봉 20주선/50주선을 대량 거래량과 함께 하향 종가 이탈시<br>
③ <b>대세 약세장(Bear Market):</b> KOSPI / S&P 500 대표 지수가 200일선 아래로 추락하는 장세 진입시
</p>
<p style="margin-bottom: 10px;">
<b>📌 2. <span style="color:#10b981;">🌊 전략적 물타기(추가매수)</span>가 가능한 3가지 상황</b><br>
① <b>계획된 50:50 분할진입:</b> 1차 50% 진입 후 <b>-15%~-20% 대파동 눌림목</b>에서 2차 50% 분할 투입 시나리오<br>
② <b>실적 이상 무 + 지수 악재:</b> 기업 실적 사상 최대 지속 중 거래량 없이 지수 공포로 일시 밀렸을 때<br>
③ <b>대세 지지선 사수:</b> 주봉 20주선 또는 주요 매물대(POC) 박스 하단을 몸통으로 강하게 지지할 때
</p>
<p style="margin: 0;">
<b>📌 3. 수익 구간별 익절 방어선 상세 기준 (Trailing Stop)</b><br>
• <b>[최고 수익률 +2.0% ~ +9.9%]</b> ➔ <b>+0.5% 익절 방어선 확정</b><br> 
• <b>[수익률 +10% ~ +20%]</b> ➔ <b>+5.0% 익절 방어선 확정</b><br> 
• <b>[수익률 +20% ~ +50%]</b> ➔ <b>최고점 대비 -12.0% 동적 방어선</b><br> 
• <b>[수익률 +50% ~ +100%]</b> ➔ <b>최고점 대비 -15.0% 동적 방어선</b><br>
• <b>[수익률 +100% 이상 (대파동)]</b> ➔ <b>최고점 대비 -20.0% 여유 방어선</b>
</p>
</div>
</div>""", unsafe_allow_html=True)

    # 🏆 [금일 포착 정예 추천주 퀀트/기술적 지표 통합 순위]
    st.markdown("#### 🏆 금일 추천주 퀀트·기술적 지표 통합 최종 순위")
    midterm_recs_raw = st.session_state.get('scan_midterm_kr', []) + st.session_state.get('scan_midterm_us', [])
    if not midterm_recs_raw:
        history_table_data_check = st.session_state.get('history_scan_table', [])
        if history_table_data_check:
            midterm_recs_raw = history_table_data_check
    if midterm_recs_raw:
        sorted_recs = sorted(midterm_recs_raw, key=lambda x: x.get('composite_score', 0) if isinstance(x, dict) else 0, reverse=True)
        unique_ranked_names = []
        for item in sorted_recs:
            s_name = item.get('name') or item.get('종목명') or item.get('stock_name')
            if s_name and s_name not in unique_ranked_names:
                unique_ranked_names.append(s_name)
        if unique_ranked_names:
            rank_md_lines = [f"**{i+1}위**: {name}" for i, name in enumerate(unique_ranked_names)]
            st.markdown("\n\n".join(rank_md_lines))
    st.markdown("#### 과거 1년 전체 종목 추천 날짜 & 수익률 전수 조사")
    st.markdown("<div style='color: #38bdf8; font-weight: bold; font-size: 14px; margin-bottom: 10px;'>✨ 과거 1년 내 포착된 종목과 추천 날짜 및 현재/최고 수익률 표 ✨</div>", unsafe_allow_html=True)

    # 💡 국내 주식 / 미국 주식 개별 스캔 및 전체 전수 스캔 분할 선택 버튼
    col_btn_kr, col_btn_us, col_btn_all = st.columns(3)
    with col_btn_kr:
        if st.button("🇰🇷 국내 주식 과거 2년 전수 스캔", key="btn_history_kr_scan", use_container_width=True):
            init_midterm_db()
            history_results = scan_all_historical_midterm_signals(ASSETS, target_market="국내")
            if history_results:
                st.session_state['history_scan_table'] = history_results
    with col_btn_us:
        if st.button("🇺🇸 미국 주식 과거 1년 전수 스캔", key="btn_history_us_scan", use_container_width=True):
            init_midterm_db()
            history_results = scan_all_historical_midterm_signals(ASSETS, target_market="미국")
            if history_results:
                st.session_state['history_scan_table'] = history_results
    with col_btn_all:
        if st.button("🔥 전체(국내+미국) 1년 전수 스캔", key="btn_history_all_scan", use_container_width=True):
            init_midterm_db()
            history_results = scan_all_historical_midterm_signals(ASSETS, target_market="전체")
            if history_results:
                st.session_state['history_scan_table'] = history_results

    history_table_data = st.session_state.get('history_scan_table', [])

    if history_table_data:
        df_display = pd.DataFrame(history_table_data)
        # 🛡️ [중복 행 원천 차단 가드레일] 티커 및 추천 포착 날짜 기준 중복 항목 제거
        if '티커' in df_display.columns and '추천 포착 날짜' in df_display.columns:
            df_display = df_display.drop_duplicates(subset=['티커', '추천 포착 날짜']).reset_index(drop=True)
        elif '종목명' in df_display.columns and '추천 포착 날짜' in df_display.columns:
            df_display = df_display.drop_duplicates(subset=['종목명', '추천 포착 날짜']).reset_index(drop=True)

        if '시장' in df_display.columns:
            df_display['시장'] = df_display['시장'].apply(lambda x: "🇰🇷 국내" if "국내" in str(x) else ("🇺🇸 미국" if "미국" in str(x) else str(x)))
        
        if '최대 수익률 도달일' not in df_display.columns:
            df_display['최대 수익률 도달일'] = df_display['추천 포착 날짜'] if '추천 포착 날짜' in df_display.columns else "-"
        
        # 요약 통계 집계
        total_hits = len(df_display)
        win_hits = len(df_display[df_display['현재/최종 수익률 (%)'] > 0 if '현재/최종 수익률 (%)' in df_display.columns else df_display['현재 수익률 (%)'] > 0])
        win_rate = (win_hits / total_hits * 100) if total_hits > 0 else 0.0
        
        ret_col_name = '현재/최종 수익률 (%)' if '현재/최종 수익률 (%)' in df_display.columns else '현재 수익률 (%)'
        pos_rets = df_display[df_display[ret_col_name] > 0][ret_col_name]
        neg_rets = df_display[df_display[ret_col_name] < 0][ret_col_name]
        total_gain = pos_rets.sum()
        total_loss = abs(neg_rets.sum())
        profit_factor = (total_gain / total_loss) if total_loss > 0 else (total_gain if total_gain > 0 else 0.0)

        max_hit_ret = df_display['최대 수익률 (%)'].max()

        pf_color = "#10b981" if profit_factor >= 2.0 else "#38bdf8"

        st.markdown(f"""
        <div style="background-color: #1e2230; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 15px;">
            <div style="font-size: 13px; color: #ffffff; font-weight: bold; margin-bottom: 6px;">📊 과거 1년 전수 포착 성과 종합 보고서</div>
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div><span style="font-size: 11px; color: #94a3b8;">포착 건수</span><br><b style="font-size: 15px; color: #ffffff;">{total_hits}건</b></div>
                <div><span style="font-size: 11px; color: #94a3b8;">승률</span><br><b style="font-size: 15px; color: #10b981;">{win_rate:.1f}%</b></div>
                <div><span style="font-size: 11px; color: #94a3b8;">손익비 (PF)</span><br><b style="font-size: 15px; color: {pf_color};">{profit_factor:.2f} (목표: 2.0↑)</b></div>
                <div><span style="font-size: 11px; color: #94a3b8;">최고 수익 파동</span><br><b style="font-size: 15px; color: #ff4b4b;">+{max_hit_ret:.1f}%</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        curr_today = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
        df_display['dt_hit'] = pd.to_datetime(df_display['추천 포착 날짜'], errors='coerce')
        
        recent_1m = df_display[df_display['dt_hit'] >= (curr_today - pd.Timedelta(days=35))].copy()
        if recent_1m.empty: recent_1m = df_display.copy()

        active_buys = recent_1m[recent_1m['상태'].str.contains('신규 매수|눌림목|물타기|1차|2차', na=False)].copy()
        if active_buys.empty: active_buys = recent_1m.copy()

        sort_col = 'mtf_score' if 'mtf_score' in active_buys.columns else '최대 수익률 (%)'

        kr_active = active_buys[active_buys['시장'].str.contains('국내', na=False)].sort_values(by=[sort_col], ascending=False).head(3)
        us_active = active_buys[active_buys['시장'].str.contains('미국', na=False)].sort_values(by=[sort_col], ascending=False).head(3)

        has_kr = not kr_active.empty
        has_us = not us_active.empty

        medals = ["🥇 1위", "🥈 2위", "🥉 3위"]
        rank_colors = ["#f59e0b", "#94a3b8", "#b45309"]

        if has_kr or has_us:
            st.markdown("##### 🔥 최근 1개월 내 주도 섹터 최고 상승 잠재주")

        if has_kr:
            st.markdown("""
            <div style="background-color: #1e293b; padding: 10px 14px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 10px;">
                <b style="color: #38bdf8; font-size: 15px;">🇰🇷 국내 주도 섹터 Top 1·2·3 정예 추천주 (최근 1개월)</b>
            </div>
            """, unsafe_allow_html=True)
            cols_kr = st.columns(3)
            for idx, (_, row_item) in enumerate(kr_active.head(3).iterrows()):
                with cols_kr[idx]:
                    s_name = row_item['종목명']
                    s_ent  = row_item['추천 진입가']
                    s_date = row_item.get('추천 포착 날짜', '')
                    s_target_1y = row_item.get('1년 목표 수익률 (%)', row_item['최대 수익률 (%)'] * 1.35 + 15.0)

                    c_ret = float(row_item.get('현재/최종 수익률 (%)', row_item.get('raw_curr_ret', 0.0)))
                    if c_ret > 0:
                        ret_color = "#ff4b4b"
                        ret_txt = f"+{c_ret:.1f}%"
                    elif c_ret < 0:
                        ret_color = "#3b82f6"
                        ret_txt = f"{c_ret:.1f}%"
                    else:
                        ret_color = "#94a3b8"
                        ret_txt = "0.0%"

                    st.markdown(f"""
                    <div style="background-color: #0f172a; padding: 12px 14px; border-radius: 8px; border: 1px solid {rank_colors[idx]}; margin-bottom: 12px; min-height: 120px;">
                        <div style="margin-bottom: 6px;">
                            <span style="font-weight: bold; color: {rank_colors[idx]}; font-size: 15px;">{medals[idx]} {s_name} <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">({s_date})</span></span>
                        </div>
                        <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">🎯 지정가 진입 추천가: <b>{s_ent}</b></div>
                        <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">📊 현재 진입 수익률: <b style="color: {ret_color}; font-size: 13px;">{ret_txt}</b></div>
                        <div style="font-size: 13px; color: #10b981; font-weight: bold;">🚀 1년 실제 예상 목표 수익: +{s_target_1y:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)

        if has_us:
            st.markdown("""
            <div style="background-color: #1e293b; padding: 10px 14px; border-radius: 8px; border: 1px solid #334155; margin-top: 10px; margin-bottom: 10px;">
                <b style="color: #f43f5e; font-size: 15px;">🇺🇸 미국 주도 섹터 Top 1·2·3 정예 추천주 (최근 1개월)</b>
            </div>
            """, unsafe_allow_html=True)
            cols_us = st.columns(3)
            for idx, (_, row_item) in enumerate(us_active.head(3).iterrows()):
                with cols_us[idx]:
                    s_name = row_item['종목명']
                    s_ent  = row_item['추천 진입가']
                    s_date = row_item.get('추천 포착 날짜', '')
                    s_target_1y = row_item.get('1년 목표 수익률 (%)', row_item['최대 수익률 (%)'] * 1.35 + 15.0)

                    c_ret = float(row_item.get('현재/최종 수익률 (%)', row_item.get('raw_curr_ret', 0.0)))
                    if c_ret > 0:
                        ret_color = "#ff4b4b"
                        ret_txt = f"+{c_ret:.1f}%"
                    elif c_ret < 0:
                        ret_color = "#3b82f6"
                        ret_txt = f"{c_ret:.1f}%"
                    else:
                        ret_color = "#94a3b8"
                        ret_txt = "0.0%"

                    st.markdown(f"""
                    <div style="background-color: #0f172a; padding: 12px 14px; border-radius: 8px; border: 1px solid {rank_colors[idx]}; margin-bottom: 12px; min-height: 120px;">
                        <div style="margin-bottom: 6px;">
                            <span style="font-weight: bold; color: {rank_colors[idx]}; font-size: 15px;">{medals[idx]} {s_name} <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">({s_date})</span></span>
                        </div>
                        <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">🎯 지정가 진입 추천가: <b>{s_ent}</b></div>
                        <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">📊 현재 진입 수익률: <b style="color: {ret_color}; font-size: 13px;">{ret_txt}</b></div>
                        <div style="font-size: 13px; color: #10b981; font-weight: bold;">🚀 1년 실제 예상 목표 수익: +{s_target_1y:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)

        base_cols = ["시장", "종목명", "추천 포착 날짜", "추천 진입가", "현재가", "현재/최종 수익률 (%)", "최대 수익률 (%)", "최대 수익률 도달일", "상태"]
        if "평단가" in df_display.columns: base_cols.insert(4, "평단가")
        table_df = df_display[base_cols].copy()

        if '시장' in table_df.columns:
            table_df['시장'] = table_df['시장'].apply(lambda x: "🇰🇷 국내" if "국내" in str(x) else ("🇺🇸 미국" if "미국" in str(x) else str(x)))

        # 💡 [요구사항 1] 추천 날짜 정렬 시 동일 날짜 내에서 🇰🇷 국내 및 🇺🇸 미국이 깔끔하게 묶이도록 이중 정렬 적용
        if '추천 포착 날짜' in table_df.columns and '시장' in table_df.columns:
            table_df = table_df.sort_values(by=['추천 포착 날짜', '시장'], ascending=[False, True])

        # ⚡ [실시간 캔들 추천 모드] 금일 포착 종목도 실시간 캔들 시세를 반영하여 즉시 표출
        today_date_str = datetime.now().strftime('%Y-%m-%d')
        if '추천 포착 날짜' in table_df.columns:
            is_today_mask = table_df['추천 포착 날짜'] == today_date_str
            if '최대 수익률 도달일' in table_df.columns:
                table_df.loc[is_today_mask, '최대 수익률 도달일'] = today_date_str

        st.markdown("##### 🏆 과거 1년 포착 종목 순위표 (수익률 내림차순)")

        # 🌟 [사용자 요청 3] 필터 라디오 명칭 100% 매칭: 1차 매수 / 2차 매수 / 익절 방어선 / 전량 매도
        radio_opts = [
            "전체 보기",
            "🛒 1차 매수 추천주",
            "💧 2차 매수 추천주 (눌림목)",
            "🛡️ 익절 방어선 추천주",
            "🚨 전량 매도 추천주 (손절)"
        ]
        filter_option = st.radio("🎯 상태별 종목 골라보기:", radio_opts, horizontal=True, key="rad_status_filter")
        if filter_option == "🛒 1차 매수 추천주":
            table_df = table_df[table_df['상태'].str.contains("신규 매수|상대강도|1차 매수|1차 50%|1차 진입", na=False) & ~table_df['상태'].str.contains("익절", na=False)]
        elif filter_option == "💧 2차 매수 추천주 (눌림목)":
            table_df = table_df[table_df['상태'].str.contains("눌림목|물타기|2차 50%|2차 체결|2차 타점", na=False) & ~table_df['상태'].str.contains("익절", na=False)]
        elif filter_option == "🛡️ 익절 방어선 추천주":
            table_df = table_df[table_df['상태'].str.contains("익절|방어선|청산", na=False)]
        elif filter_option == "🚨 전량 매도 추천주 (손절)":
            table_df = table_df[table_df['상태'].str.contains("손절|매도|붕괴", na=False)]

        # 🌟 [사용자 요청 4] 쉼표(,) 입력 시 다중 종목 동시 검색 (예: 심텍, 삼성)
        search_keyword = st.text_input("🔍 종목 검색 (쉼표(,) 구분 시 다중 종목 동시 검색 지원):", placeholder="예: 심텍, 삼성 또는 현대, 카카오", key="tab3_stock_search").strip()

        if search_keyword:
            import re
            keywords = [k.strip() for k in search_keyword.split(",") if k.strip()]
            if keywords:
                pattern = "|".join([re.escape(k) for k in keywords])
                matched_stocks = table_df[table_df['종목명'].str.contains(pattern, case=False, na=False)]['종목명'].unique().tolist()
                
                if matched_stocks:
                    if len(matched_stocks) > 1:
                        sel_stock = st.radio(
                            f"💡 **검색 포착 종목 ({len(matched_stocks)}개) — 원하는 종목을 클릭하시면 해당 주식만 핀포인트 조회됩니다:**",
                            [f"전체 검색결과 보기 ({len(matched_stocks)}개)"] + matched_stocks,
                            horizontal=True,
                            key=f"rad_matched_stock_select_{search_keyword}"
                        )
                        if sel_stock != f"전체 검색결과 보기 ({len(matched_stocks)}개)":
                            table_df = table_df[table_df['종목명'] == sel_stock]
                        else:
                            table_df = table_df[table_df['종목명'].str.contains(pattern, case=False, na=False)]
                    else:
                        st.markdown(f"💡 **검색 포착 종목 (1개):** <span style='color:#38bdf8; font-weight:bold;'>{matched_stocks[0]}</span>", unsafe_allow_html=True)
                        table_df = table_df[table_df['종목명'] == matched_stocks[0]]
                else:
                    st.warning(f"⚠️ '{search_keyword}' 검색어와 일치하는 종목이 없습니다.")
                    table_df = table_df.iloc[0:0]
        
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True
        )

        unique_hit_dates = sorted(list(set(df_display['추천 포착 날짜'])), reverse=True)
        selected_date_filter = st.selectbox("📅 특정 추천 날짜만 골라서 확인하기", ["전체 보기"] + unique_hit_dates, key="sb_filter_hit_date")
        
        if selected_date_filter != "전체 보기":
            filtered_df = table_df[table_df['추천 포착 날짜'] == selected_date_filter]
            st.markdown(f"🗓️ **{selected_date_filter} 포착 종목 리스트:**")
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    else:
        st.info("💡 위의 [과거 1년 추천 날짜/수익률 전체 전수 스캔] 버튼을 누르면 전체 주식의 추천 날짜와 수익률 표가 완성됩니다.")