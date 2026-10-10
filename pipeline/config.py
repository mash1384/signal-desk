"""SIGNAL 파이프라인 설정.

수집원, 자산 사전, 분류 키워드, 측정 구간을 한곳에 모은다.
여기 값만 바꾸면 동작이 바뀌도록 다른 모듈에는 상수를 두지 않는다.
"""

import os

SITE_URL = (os.environ.get("SIGNAL_SITE_URL") or "https://mash1384.github.io/signal-desk").rstrip("/")
SITE_BASE = os.environ.get("SIGNAL_SITE_BASE") or "/signal-desk/"
SITE_NAME = "SIGNAL"
USER_AGENT = "Mozilla/5.0 (compatible; SIGNAL-bot/1.0; +" + SITE_URL + "/about/)"

# 보관 정책
KEEP_DAYS = 30
MAX_ARTICLES = 6000
INGEST_MAX_AGE_HOURS = 72
PER_SOURCE_LIMIT = 30
FEED_JSON_LIMIT = 300
HOME_RENDER_LIMIT = 40

# 임팩트 측정 구간 (초)
WINDOWS = [("15m", 900), ("1h", 3600), ("24h", 86400)]
GRADE_STRONG = 3.0
GRADE_MEDIUM = 2.0
CONCURRENT_EVENT_SECONDS = 900

# 수집원. hint: 기본 카테고리, require: True면 키워드가 맞는 기사만 남긴다
NOISE_TITLES = ["price prediction", "price analysis", "price forecast", "technical analysis", "could reach", "will hit", "가격 예측", "전망가"]

SOURCES = [
    {"id": "coindesk", "name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss", "lang": "en", "hint": "crypto", "require": False},
    {"id": "cointelegraph", "name": "Cointelegraph", "url": "https://cointelegraph.com/rss", "lang": "en", "hint": "crypto", "require": False},
    {"id": "decrypt", "name": "Decrypt", "url": "https://decrypt.co/feed", "lang": "en", "hint": "crypto", "require": False},
    {"id": "theblock", "name": "The Block", "url": "https://www.theblock.co/rss.xml", "lang": "en", "hint": "crypto", "require": False},
    {"id": "blockmedia", "name": "블록미디어", "url": "https://www.blockmedia.co.kr/feed", "lang": "ko", "hint": "crypto", "require": False},
    {"id": "tokenpost", "name": "토큰포스트", "url": "https://www.tokenpost.kr/rss", "lang": "ko", "hint": "crypto", "require": False},
    {"id": "techcrunch-ai", "name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "lang": "en", "hint": "ai", "require": False},
    {"id": "verge-ai", "name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "lang": "en", "hint": "ai", "require": False},
    {"id": "aitimes", "name": "AI타임스", "url": "https://www.aitimes.com/rss/allArticle.xml", "lang": "ko", "hint": "ai", "require": False},
    {"id": "digitaltoday", "name": "디지털투데이", "url": "https://www.digitaltoday.co.kr/rss/allArticle.xml", "lang": "ko", "hint": None, "require": True},
    {"id": "cnbc-economy", "name": "CNBC Economy", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html", "lang": "en", "hint": "macro", "require": False},
    {"id": "marketwatch", "name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "lang": "en", "hint": "macro", "require": True},
    {"id": "yna-economy", "name": "연합뉴스 경제", "url": "https://www.yna.co.kr/rss/economy.xml", "lang": "ko", "hint": "macro", "require": True},
    {"id": "hankyung-economy", "name": "한국경제 경제", "url": "https://www.hankyung.com/feed/economy", "lang": "ko", "hint": "macro", "require": True},
    {"id": "hankyung-finance", "name": "한국경제 증권", "url": "https://www.hankyung.com/feed/finance", "lang": "ko", "hint": "macro", "require": True},
    {"id": "mk-economy", "name": "매일경제 경제", "url": "https://www.mk.co.kr/rss/30100041/", "lang": "ko", "hint": "macro", "require": True},
    # 크립토 전문지
    {"id": "thedefiant", "name": "The Defiant", "url": "https://thedefiant.io/api/feed", "lang": "en", "hint": "crypto", "require": False},
    {"id": "bitcoinmag", "name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/feed", "lang": "en", "hint": "crypto", "require": False},
    {"id": "cryptoslate", "name": "CryptoSlate", "url": "https://cryptoslate.com/feed/", "lang": "en", "hint": "crypto", "require": False},
    {"id": "unchained", "name": "Unchained", "url": "https://unchainedcrypto.com/feed/", "lang": "en", "hint": "crypto", "require": False},
    {"id": "cryptobriefing", "name": "Crypto Briefing", "url": "https://cryptobriefing.com/feed/", "lang": "en", "hint": "crypto", "require": False},
    # 알트코인 개별 소식이 많은 매체(뉴스 영향 연결용). 가격 예측·차트 분석 글은 제목으로 거른다
    {"id": "utoday", "name": "U.Today", "url": "https://u.today/rss", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "cryptopotato", "name": "CryptoPotato", "url": "https://cryptopotato.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "cryptonews-com", "name": "crypto.news", "url": "https://crypto.news/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "cryptonews-net", "name": "Cryptonews", "url": "https://cryptonews.com/news/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "thecryptobasic", "name": "The Crypto Basic", "url": "https://thecryptobasic.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "coingape", "name": "CoinGape", "url": "https://coingape.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "newsbtc", "name": "NewsBTC", "url": "https://www.newsbtc.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "bitcoinist", "name": "Bitcoinist", "url": "https://bitcoinist.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "coinpedia", "name": "Coinpedia", "url": "https://coinpedia.org/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "beincrypto", "name": "BeInCrypto", "url": "https://beincrypto.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "beincrypto-kr", "name": "비인크립토", "url": "https://kr.beincrypto.com/feed/", "lang": "ko", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "ambcrypto", "name": "AMBCrypto", "url": "https://ambcrypto.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "dailyhodl", "name": "The Daily Hodl", "url": "https://dailyhodl.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "coincentral", "name": "CoinCentral", "url": "https://coincentral.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    {"id": "bitcoin-com", "name": "Bitcoin.com News", "url": "https://news.bitcoin.com/feed/", "lang": "en", "hint": "crypto", "require": False, "skip": NOISE_TITLES},
    # 프로젝트 공식 채널(업그레이드·파트너십 발표)
    {"id": "solana-news", "name": "Solana 공식", "url": "https://solana.com/news/rss.xml", "lang": "en", "hint": "crypto", "require": False},
    {"id": "sui-blog", "name": "Sui 공식 블로그", "url": "https://blog.sui.io/rss/", "lang": "en", "hint": "crypto", "require": False},
    {"id": "hedera-blog", "name": "Hedera 공식 블로그", "url": "https://hedera.com/blog/feed", "lang": "en", "hint": "crypto", "require": False},
    {"id": "ethereum-blog", "name": "Ethereum 재단 블로그", "url": "https://blog.ethereum.org/feed.xml", "lang": "en", "hint": "crypto", "require": False},
    # AI: 전문지와 회사 공식 발표
    {"id": "mittr-ai", "name": "MIT Technology Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "lang": "en", "hint": "ai", "require": False},
    {"id": "ars-ai", "name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed/", "lang": "en", "hint": "ai", "require": False},
    {"id": "wired-ai", "name": "WIRED AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss", "lang": "en", "hint": "ai", "require": False},
    {"id": "thedecoder", "name": "The Decoder", "url": "https://the-decoder.com/feed/", "lang": "en", "hint": "ai", "require": False},
    {"id": "openai", "name": "OpenAI", "url": "https://openai.com/news/rss.xml", "lang": "en", "hint": "ai", "require": False},
    {"id": "google-ai", "name": "Google AI", "url": "https://blog.google/technology/ai/rss/", "lang": "en", "hint": "ai", "require": False},
    {"id": "huggingface", "name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "lang": "en", "hint": "ai", "require": False},
    {"id": "zdnet-kr", "name": "지디넷코리아", "url": "https://feeds.feedburner.com/zdkorea", "lang": "ko", "hint": None, "require": True},
    {"id": "etnews", "name": "전자신문", "url": "https://rss.etnews.com/Section901.xml", "lang": "ko", "hint": None, "require": True},
    {"id": "bloter", "name": "블로터", "url": "https://www.bloter.net/rss/allArticle.xml", "lang": "ko", "hint": None, "require": True},
    # 매크로: 통신·경제지와 중앙은행
    {"id": "bloomberg-econ", "name": "Bloomberg Economics", "url": "https://feeds.bloomberg.com/economics/news.rss", "lang": "en", "hint": "macro", "require": False},
    {"id": "bloomberg-markets", "name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss", "lang": "en", "hint": "macro", "require": True},
    {"id": "ft-markets", "name": "Financial Times", "url": "https://www.ft.com/markets?format=rss", "lang": "en", "hint": "macro", "require": True},
    {"id": "cnbc-markets", "name": "CNBC Markets", "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html", "lang": "en", "hint": "macro", "require": True},
    {"id": "fed", "name": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "lang": "en", "hint": "macro", "require": True,
     # 은행 합병 승인·제재 같은 행정 공지는 빼고 통화정책 발표만
     "only": ["federal open market committee", "fomc", "monetary policy", "minutes", "economic projections", "discount rate", "interest rate", "beige book", "balance sheet", "statement", "speech", "testimony"]},
    {"id": "einfomax", "name": "연합인포맥스", "url": "https://news.einfomax.co.kr/rss/allArticle.xml", "lang": "ko", "hint": "macro", "require": True},
    {"id": "edaily", "name": "이데일리", "url": "http://rss.edaily.co.kr/edaily_news.xml", "lang": "ko", "hint": "macro", "require": True},
]

# 소스별 가중치 (중요도 계산에 더함)
SOURCE_WEIGHT = {"coindesk": 1, "theblock": 1, "cnbc-economy": 1, "yna-economy": 1, "bloomberg-econ": 1, "bloomberg-markets": 1, "ft-markets": 1, "fed": 1, "openai": 1}

# 임팩트를 잴 수 있는 자산 사전. names는 기사에서 찾을 이름(소문자 비교)
ASSETS = {
    "BTC": {"names": ["bitcoin", "btc", "비트코인"], "binance": "BTCUSDT", "coinbase": "BTC-USD", "upbit": "KRW-BTC"},
    "ETH": {"names": ["ethereum", "ether", "eth", "이더리움"], "binance": "ETHUSDT", "coinbase": "ETH-USD", "upbit": "KRW-ETH"},
    "SOL": {"names": ["solana", "sol", "솔라나"], "binance": "SOLUSDT", "coinbase": "SOL-USD", "upbit": "KRW-SOL"},
    "XRP": {"names": ["xrp", "ripple", "리플"], "binance": "XRPUSDT", "coinbase": "XRP-USD", "upbit": "KRW-XRP"},
    "BNB": {"names": ["bnb", "binance coin", "바이낸스코인"], "binance": "BNBUSDT", "coinbase": None, "upbit": None},
    "DOGE": {"names": ["dogecoin", "doge", "도지코인", "도지"], "binance": "DOGEUSDT", "coinbase": "DOGE-USD", "upbit": "KRW-DOGE"},
    "ADA": {"names": ["cardano", "ada", "카르다노", "에이다"], "binance": "ADAUSDT", "coinbase": "ADA-USD", "upbit": "KRW-ADA"},
    "LINK": {"names": ["chainlink", "체인링크"], "binance": "LINKUSDT", "coinbase": "LINK-USD", "upbit": "KRW-LINK"},
    "AVAX": {"names": ["avalanche", "avax", "아발란체"], "binance": "AVAXUSDT", "coinbase": "AVAX-USD", "upbit": "KRW-AVAX"},
    "SUI": {"names": ["sui network", "수이"], "binance": "SUIUSDT", "coinbase": "SUI-USD", "upbit": "KRW-SUI"},
    "TON": {"names": ["toncoin", "톤코인"], "binance": "TONUSDT", "coinbase": None, "upbit": None},
    "DOT": {"names": ["polkadot", "폴카닷"], "binance": "DOTUSDT", "coinbase": "DOT-USD", "upbit": "KRW-DOT"},
    # 뉴스 영향(moves)과 같은 24개를 기사에서 알아본다. 흔한 영어 단어와 겹치는 이름은 넣지 않는다
    "LTC": {"names": ["litecoin", "라이트코인"], "binance": "LTCUSDT", "coinbase": "LTC-USD", "upbit": None},
    "TRX": {"names": ["tron", "트론"], "binance": "TRXUSDT", "coinbase": None, "upbit": "KRW-TRX"},
    "HBAR": {"names": ["hedera", "헤데라"], "binance": "HBARUSDT", "coinbase": "HBAR-USD", "upbit": "KRW-HBAR"},
    "TAO": {"names": ["bittensor", "비트텐서"], "binance": "TAOUSDT", "coinbase": None, "upbit": None},
    "AAVE": {"names": ["aave", "에이브"], "binance": "AAVEUSDT", "coinbase": "AAVE-USD", "upbit": "KRW-AAVE"},
    "UNI": {"names": ["uniswap", "유니스왑"], "binance": "UNIUSDT", "coinbase": "UNI-USD", "upbit": None},
    "NEAR": {"names": ["near protocol", "니어프로토콜"], "binance": "NEARUSDT", "coinbase": "NEAR-USD", "upbit": "KRW-NEAR"},
    "APT": {"names": ["aptos", "앱토스"], "binance": "APTUSDT", "coinbase": "APT-USD", "upbit": "KRW-APT"},
    "ONDO": {"names": ["ondo finance", "온도파이낸스"], "binance": "ONDOUSDT", "coinbase": None, "upbit": "KRW-ONDO"},
    "ENA": {"names": ["ethena", "에테나"], "binance": "ENAUSDT", "coinbase": None, "upbit": "KRW-ENA"},
    "PEPE": {"names": ["pepe", "페페"], "binance": "PEPEUSDT", "coinbase": None, "upbit": "KRW-PEPE"},
    "ZEC": {"names": ["zcash", "지캐시"], "binance": "ZECUSDT", "coinbase": "ZEC-USD", "upbit": "KRW-ZEC"},
    "FET": {"names": ["fetch.ai"], "binance": "FETUSDT", "coinbase": None, "upbit": None},
}
MARKET_ASSETS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "LINK", "AVAX", "SUI", "TON", "DOT"]
MAX_ASSETS_PER_ARTICLE = 4

# 카테고리 키워드 (소문자 부분 일치). 영어 단어는 앞뒤 경계를 확인한다
CATEGORY_KEYWORDS = {
    "crypto": [
        "bitcoin", "crypto", "cryptocurrency", "blockchain", "stablecoin", "ethereum", "defi", "token", "web3", "nft", "altcoin", "mining", "layer 2", "mainnet",
        "비트코인", "가상자산", "암호화폐", "코인", "블록체인", "스테이블코인", "이더리움", "디파이", "토큰", "채굴", "업비트", "빗썸", "바이낸스", "레이어2", "메인넷",
    ],
    "ai": [
        "artificial intelligence", "ai", "llm", "openai", "anthropic", "chatgpt", "claude", "gemini", "nvidia", "gpu",
        "model", "machine learning", "data center", "datacenter", "chip", "chips", "semiconductor", "hbm", "tsmc", "foundry", "agentic",
        "인공지능", "생성형", "에이아이", "엔비디아", "데이터센터", "반도체", "llm", "gpu", "챗gpt", "딥러닝", "오픈ai", "파운드리", "에이전트",
    ],
    "macro": [
        "fed", "fomc", "inflation", "cpi", "pce", "interest rate", "rate cut", "rate hike", "treasury", "yield", "jobs report",
        "payroll", "unemployment", "gdp", "recession", "tariff", "dollar", "oil", "gold", "stocks", "s&p", "nasdaq", "dow",
        "federal reserve", "central bank", "ecb", "bank of japan", "powell", "bond", "bonds", "economy", "jobless", "wall street",
        "equities", "yen", "euro", "crude", "opec", "trade war", "stimulus", "rates", "pboc", "boj", "yuan", "copper", "currency", "treasuries", "yields", "tariffs", "payrolls",
        "연준", "기준금리", "금리", "물가", "인플레이션", "소비자물가", "고용지표", "실업률", "국채", "환율", "달러", "유가",
        "금값", "증시", "코스피", "코스닥", "나스닥", "관세", "한은", "한국은행", "외국인 순매도", "외국인 순매수", "fomc", "cpi",
        "파월", "국고채", "채권", "엔화", "원·달러", "외환", "경기침체", "무역수지", "수출", "뉴욕증시", "미 증시", "연은", "중앙은행", "위안", "유로화", "구리", "월가", "다우", "고용보고서",
    ],
}

# 키워드를 요구하는 종합지에서, 제목에 하나만 있어도 그 분야 기사로 인정하는 핵심어.
# 금액·일반 기사에도 흔한 말("달러", "고용", "수출")은 넣지 않는다. 코인 이름·티커는 따로 본다
TITLE_STRONG = {
    "crypto": [
        "bitcoin", "crypto", "cryptocurrency", "blockchain", "stablecoin", "ethereum", "defi", "web3", "altcoin", "layer 2", "mainnet",
        "비트코인", "가상자산", "암호화폐", "코인", "블록체인", "스테이블코인", "이더리움", "디파이", "업비트", "빗썸", "바이낸스", "레이어2", "메인넷",
    ],
    "ai": [
        "artificial intelligence", "ai", "llm", "openai", "anthropic", "chatgpt", "claude", "gemini", "nvidia", "semiconductor", "chip", "chips",
        "hbm", "tsmc", "foundry", "data center", "agentic",
        "인공지능", "생성형", "오픈ai", "챗gpt", "엔비디아", "반도체", "파운드리", "데이터센터", "에이전트", "딥러닝",
    ],
    "macro": [
        "fed", "fomc", "federal reserve", "powell", "ecb", "boj", "pboc", "central bank", "interest rate", "rates", "yield", "yields",
        "treasury", "treasuries", "bond", "bonds", "dollar", "yuan", "yen", "currency", "oil", "crude", "opec", "gold", "copper",
        "inflation", "cpi", "pce", "gdp", "recession", "jobs report", "payrolls", "unemployment", "tariff", "tariffs", "trade war",
        "stocks", "s&p", "nasdaq", "dow", "wall street", "markets wrap",
        "연준", "연은", "파월", "한은", "한국은행", "중앙은행", "금리", "국채", "국고채", "채권금리", "채권시장", "환율", "원/달러", "원·달러", "달러화",
        "달러 강세", "달러 약세", "위안", "엔화", "유로화", "외환", "유가", "금값", "구리", "물가", "인플레이션", "소비자물가", "경기침체",
        "고용지표", "고용보고서", "실업률", "관세", "증시", "뉴욕증시", "코스피", "코스닥", "나스닥", "다우", "월가",
    ],
}

# 중요도 3을 주는 키워드
HIGH_KEYWORDS = [
    "fomc", "cpi", "rate decision", "rate cut", "rate hike", "jobs report", "nonfarm", "etf approval", "etf approved",
    "hack", "exploit", "bankrupt", "bankruptcy", "sec", "lawsuit",
    "기준금리", "금리 인하", "금리 인상", "소비자물가", "고용보고서", "etf 승인", "해킹", "파산",
]
# 크립토 기사에서만 중요도 3을 주는 키워드 (주식 상장과 구분)
HIGH_KEYWORDS_CRYPTO = ["listing", "listings", "delist", "delisting", "상장", "유의 종목", "거래 지원 종료", "디지털 자산 추가"]

# 제목이 이렇게 시작하면 버린다 (인사·표·부고 같은 공지성 기사)
TITLE_BLOCK_PREFIX = ["[연합뉴스 이 시각 헤드라인]", "[인사]", "[표]", "[부고]", "[게시판]", "[포토]", "[사진]", "[알림]", "[신간]", "[날씨]", "[운세]", "[오늘의 운세]"]

# /impact 통계용 이벤트 유형 (먼저 맞는 것)
EVENT_TYPES = [
    ("fomc", "FOMC·연준", ["fomc", "federal reserve", "fed chair", "powell", "연준", "파월", "fomc"]),
    ("cpi", "물가 지표", ["cpi", "pce", "inflation", "소비자물가", "물가", "인플레이션"]),
    ("jobs", "고용 지표", ["jobs report", "payroll", "payrolls", "unemployment", "jobless", "고용지표", "고용보고서", "실업률", "취업자"]),
    ("etf", "ETF", ["etf"]),
    ("listing", "상장·상폐", ["listing", "listings", "delist", "delisting", "상장", "거래 지원 종료", "유의 종목", "디지털 자산 추가"]),
    ("hack", "해킹·사고", ["hack", "hacked", "hacker", "exploit", "exploited", "breach", "stolen", "해킹", "탈취", "유출"]),
    ("regulation", "규제·소송", ["sec", "regulation", "regulator", "regulators", "regulatory", "lawsuit", "court", "bill", "규제", "법안", "소송", "금융위", "금감원"]),
    ("ai-model", "AI 모델·제품", ["launch", "launches", "release", "releases", "model", "models", "출시", "공개", "모델"]),
    ("earnings", "실적", ["earnings", "revenue", "quarterly", "실적", "매출", "영업이익"]),
]

# 분류 결과 라벨
CATEGORY_LABEL = {"crypto": "크립토", "ai": "AI", "macro": "매크로"}

# 외부 데이터 소스
BINANCE_HOSTS = ["https://data-api.binance.vision", "https://api.binance.com"]
COINBASE_HOST = "https://api.exchange.coinbase.com"
UPBIT_TICKER = "https://api.upbit.com/v1/ticker"
UPBIT_CANDLES_BASE = "https://api.upbit.com/v1/candles/"
UPBIT_NOTICE_DETAIL = "https://api-manager.upbit.com/api/v1/announcements/%s"
UPBIT_NOTICES = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade"
# 업비트가 GitHub 서버 IP를 막아서, 직접 받다 실패하면 Cloudflare 스케줄러(worker/)를 거쳐 받는다
UPBIT_NOTICES_PROXY = os.environ.get("SIGNAL_UPBIT_PROXY") or ""
FNG_URL = "https://api.alternative.me/fng/?limit=30"
FX_URL = "https://open.er-api.com/v6/latest/USD"
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# 알림 정책
ALERT_DAILY_CAP = 12
ALERT_DEDUPE_SECONDS = 1800
QUIET_HOURS_KST = (1, 7)  # 01:00 이상 07:00 미만
KIMP_ALERT_DELTA = 3.0  # %p, 1시간 안 변화

# LLM 요약 (키가 있을 때만 동작)
LLM_MODEL = os.environ.get("SIGNAL_LLM_MODEL") or "claude-opus-5-5"
LLM_EFFORT = os.environ.get("SIGNAL_LLM_EFFORT") or "low"
LLM_MAX_PER_RUN = int(os.environ.get("SIGNAL_LLM_MAX_PER_RUN") or "20")
