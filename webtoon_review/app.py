import streamlit as st
from google_play_scraper import reviews, Sort
import pandas as pd
from collections import Counter
from wordcloud import WordCloud
import re
import os
from io import BytesIO

# ----------------------------
# 페이지 설정
# ----------------------------
st.set_page_config(
    page_title="경쟁사 앱 리뷰 분석",
    page_icon="📊",
    layout="wide"
)

# ----------------------------
# 반응형 CSS 스타일
# ----------------------------
st.markdown("""
<style>
/* 전체 폰트 크기 축소 */
html, body, [class*="css"] {
    font-size: 14px;
}

/* 제목 크기 조정 */
h1 {
    font-size: 1.6rem !important;
}
h2 {
    font-size: 1.3rem !important;
}
h3, .stSubheader {
    font-size: 1.1rem !important;
}
h4 {
    font-size: 1rem !important;
}

/* 사이드바 최적화 */
[data-testid="stSidebar"] {
    min-width: 280px;
    max-width: 320px;
}
[data-testid="stSidebar"] .stMarkdown {
    font-size: 13px;
}
[data-testid="stSidebar"] code {
    font-size: 11px;
    padding: 4px 8px;
}
[data-testid="stSidebar"] .stCaption {
    font-size: 11px;
}

/* 메트릭 카드 크기 조정 */
[data-testid="stMetricValue"] {
    font-size: 1.3rem !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
}

/* 탭 고정 (스크롤 시 상단에 고정) */
.stTabs [data-baseweb="tab-list"] {
    position: sticky;
    top: 0;
    background: white;
    z-index: 999;
    padding: 10px 0;
    border-bottom: 1px solid #eee;
}

/* 탭 크기 조정 */
.stTabs [data-baseweb="tab-list"] button {
    font-size: 13px;
    padding: 8px 12px;
}

/* 테이블 폰트 크기 */
.stDataFrame {
    font-size: 12px;
}

/* 버튼 크기 */
.stButton > button {
    font-size: 13px;
    padding: 8px 16px;
}

/* 입력 필드 기본 스타일 */
.stTextInput input {
    font-size: 13px;
}

/* 키워드 입력 필드 - 기본 녹색 테두리 */
.keyword-input input {
    border: 2px solid #28a745 !important;
    border-radius: 5px !important;
}

/* 키워드 입력 필드 - 포커스 및 입력 시 노란색 */
.keyword-input input:focus,
.keyword-input input:not(:placeholder-shown) {
    border-color: #ffc107 !important;
    box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.3) !important;
}

/* 모바일 대응 (아이폰 15: 393px) */
@media (max-width: 768px) {
    html, body, [class*="css"] {
        font-size: 12px;
    }
    h1 {
        font-size: 1.4rem !important;
    }
    h2 {
        font-size: 1.2rem !important;
    }
    [data-testid="stSidebar"] {
        min-width: 100%;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 11px;
        padding: 6px 8px;
    }
}

/* 맥북 에어 (1440px 이하) */
@media (max-width: 1440px) {
    [data-testid="stSidebar"] {
        min-width: 260px;
        max-width: 280px;
    }
}

/* 간격 최적화 - Streamlit Cloud 헤더 고려 */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 1rem;
}

/* 메인 컨텐츠 영역 상단 여백 */
.main .block-container {
    padding-top: 3rem;
}

.stMarkdown {
    line-height: 1.5;
}

/* 데이터프레임 컴팩트 */
[data-testid="stDataFrame"] td, 
[data-testid="stDataFrame"] th {
    padding: 4px 8px !important;
    font-size: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# 폰트 경로 설정
# ----------------------------
def get_font_path():
    possible_paths = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

FONT_PATH = get_font_path()

# ----------------------------
# 앱 목록 정의
# ----------------------------
APP_LIST = {
    "네이버 웹툰": "com.nhn.android.webtoon",
    "카카오페이지": "com.kakaopage.app",
    "레진코믹스": "com.lezhin.comics",
    "리디북스": "com.initialcoms.ridi",
}

# ----------------------------
# 불용어 정의
# ----------------------------
STOPWORDS = {
    "너무", "정말", "진짜", "매우", "아주", "완전", "되게", "꽤", "좀", "약간", "살짝",
    "그냥", "이거", "저거", "그것", "이것", "저것", "하는", "있는", "없는",
    "해서", "하고", "해요", "합니다", "입니다", "있어요", "없어요", "같아요",
    "이런", "저런", "그런", "어떤", "무슨", "왜", "어디", "언제", "어떻게",
    "근데", "그래서", "하지만", "그러나", "그리고", "또한", "그래도",
    "있어", "없어", "하면", "이용", "사용", "정도", "이상", "계속", "다시", "처음", "마지막",
    "네이버", "웹툰", "쿠키", "만화", "작품", "좋아", "읽고", "보고", "해서", "하고"
}

# ----------------------------
# 토픽 키워드 정의
# ----------------------------
TOPIC_KEYWORDS = {
    "📚 콘텐츠": ["작품", "연재", "완결", "스토리", "내용", "재미", "그림", "퀄리티", "신작", "추천", "작가", "회차", "출시", "보고싶", "읽고싶", "기다", "시즌", "에피소드", "캐릭터", "결말", "전작", "후속", "외전", "재밌", "재미있", "웹툰"],
    "💰 결제/가격": ["결제", "돈", "유료", "무료", "가격", "비싸", "비용", "코인", "충전", "환불", "구매", "구독", "이용권", "할인", "캐시", "쿠키", "유료화", "과금", "유료가", "무료로", "무료면", "유료면", "돈내", "돈을"],
    "📺 광고": ["광고", "배너", "팝업", "스킵", "건너뛰기", "동영상광고", "전면광고", "광고가", "광고없", "광고좀", "광고를"],
    "🐛 버그/오류": ["버그", "오류", "에러", "렉걸", "튕김", "튕겨", "멈춤", "작동안", "느려", "로딩", "꺼짐", "강제종료", "crash", "팅김", "무한로딩", "앱꺼", "실행안", "멈춰", "다운됨"],
    "📱 UI/UX": ["화면", "버튼", "디자인", "인터페이스", "메뉴", "레이아웃", "구성", "위치", "아이콘", "색상", "폰트", "글씨", "스크롤", "터치", "조작"],
    "🔔 알림/편의": ["알림", "푸시", "북마크", "저장", "기록", "목록", "검색", "정렬", "필터", "공유", "다운로드", "오프라인"],
}

# ----------------------------
# 감성 키워드 정의 (기본)
# ----------------------------
POSITIVE_WORDS = {"좋아", "최고", "재밌", "재미있", "편리", "편해", "만족", "추천", "굿", "대박", "사랑", "완벽", "훌륭", "감사", "행복", "즐거"}
NEGATIVE_WORDS = {"별로", "싫어", "최악", "불편", "짜증", "화나", "실망", "후회", "쓰레기", "폭망", "구림", "개선", "답답", "불만", "짜증나", "에러", "버그"}

# ----------------------------
# 웹툰/만화 특화 감성 키워드 (가중치 포함)
# ----------------------------
WEBTOON_SENTIMENT = {
    "positive": {
        # 기본 (weight 1-3)
        "좋다": 1, "좋아요": 1, "만족": 1,
        "재밌다": 2, "재미있다": 2, "추천": 2, "감동": 2, "몰입": 2, "여운": 2,
        "강추": 3, "최고": 3, "완벽": 3,
        # 웹툰특화
        "작화좋다": 2, "작화좋음": 2, "작화미쳤다": 3, "작화미침": 3,
        "스토리탄탄": 3, "전개깔끔": 2, "연출좋다": 2, "연출좋음": 2,
        "캐릭터매력": 2, "개연성있다": 2, "세계관탄탄": 3,
        "떡밥회수": 3, "다음화기대": 2, "정주행": 2, "시간순삭": 3,
        # 극단
        "갓작": 3, "명작": 3, "레전드": 3, "인생웹툰": 3, "소름": 3,
        # 추가 변형
        "재밌": 2, "재미있": 2, "좋아": 1, "강력추천": 3, "꿀잼": 3,
        "작화": 1, "스토리": 1, "몰입감": 2, "감동적": 2,
    },
    "negative": {
        # 기본
        "노잼": 3, "별로": 1, "실망": 2, "아쉽다": 1, "아쉬움": 1,
        "지루": 2, "답답": 2, "비추": 2, "최악": 3, "재미없다": 2, "재미없": 2,
        # 웹툰특화
        "작화붕괴": 3, "작붕": 3, "스토리산으로": 3, "산으로": 2,
        "개연성없다": 3, "개연성없음": 3, "전개느림": 2, "급전개": 2,
        "캐붕": 3, "설정붕괴": 3, "질질끈다": 2, "질질끔": 2,
        "떡밥방치": 3, "몰입깨짐": 2,
        # 극단
        "하차": 3, "시간낭비": 3, "돈아까움": 3, "발암": 3, "개망작": 3,
        # 추가 변형
        "노잼임": 3, "별로임": 1, "지루함": 2, "지루해": 2,
    }
}

# ----------------------------
# 요청 패턴 정의
# ----------------------------
REQUEST_PATTERNS = [
    r"(.{2,20})(해주세요|해줘요|해주길|바랍니다|바래요|원합니다|원해요|했으면|으면 좋겠|면 좋겠|해달라|해줬으면)",
    r"(제발|부탁).{0,20}(해주|바랍|원)",
    r"(.{2,15})(기능|옵션).{0,5}(추가|넣어|만들어)",
]

# ----------------------------
# 유틸리티 함수
# ----------------------------
def simple_tokenizer(text):
    tokens = re.findall(r"[가-힣]{2,}", str(text))
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]
    return tokens

def extract_bigrams(text):
    """키워드 조합 (바이그램) 추출"""
    tokens = simple_tokenizer(text)
    bigrams = []
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} + {tokens[i+1]}"
        bigrams.append(bigram)
    return bigrams

def extract_trigrams(text):
    """키워드 조합 (트리그램 - 3단어) 추출"""
    tokens = simple_tokenizer(text)
    trigrams = []
    for i in range(len(tokens) - 2):
        trigram = f"{tokens[i]} + {tokens[i+1]} + {tokens[i+2]}"
        trigrams.append(trigram)
    return trigrams

@st.cache_data(ttl=86400, show_spinner="기본 데이터 로딩...")
def load_default_data():
    """기본 데이터 로드 (CSV에 sentiment 포함 시 즉시 반환)"""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), "default_reviews.csv")
        df = pd.read_csv(csv_path)
        df["at"] = pd.to_datetime(df["at"])
        
        # CSV에 이미 sentiment가 있으면 바로 반환
        if "sentiment" in df.columns:
            return df
        
        # 없으면 감성분석 수행 (최초 1회)
        results = []
        pos_scores = []
        neg_scores = []
        
        for _, row in df.iterrows():
            text = str(row["content"])
            score = row["score"]
            
            pos_weight = sum(weight for word, weight in WEBTOON_SENTIMENT["positive"].items() if word in text)
            neg_weight = sum(weight for word, weight in WEBTOON_SENTIMENT["negative"].items() if word in text)
            
            pos_scores.append(pos_weight)
            neg_scores.append(neg_weight)
            
            if score >= 4:
                sentiment = "부정" if neg_weight >= 6 and neg_weight > pos_weight else "긍정"
            elif score <= 2:
                sentiment = "긍정" if pos_weight >= 6 and pos_weight > neg_weight else "부정"
            else:
                diff = pos_weight - neg_weight
                sentiment = "긍정" if diff >= 2 else ("부정" if diff <= -2 else "중립")
            
            results.append(sentiment)
        
        df["sentiment"] = results
        df["pos_score"] = pos_scores
        df["neg_score"] = neg_scores
        
        return df
    except Exception as e:
        st.error(f"기본 데이터 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=7200, show_spinner=False)
def get_reviews_cached(app_id, count=1000):
    result = []
    continuation_token = None
    
    try:
        while len(result) < count:
            batch_size = min(100, count - len(result))
            review_batch, continuation_token = reviews(
                app_id, lang="ko", country="kr",
                sort=Sort.NEWEST, count=batch_size,
                continuation_token=continuation_token
            )
            result.extend(review_batch)
            if not continuation_token:
                break
    except Exception as e:
        st.error(f"리뷰 수집 중 오류: {e}")
        return pd.DataFrame()
    
    df = pd.DataFrame(result)
    if not df.empty:
        df["at"] = pd.to_datetime(df["at"])
        df["content"] = df["content"].astype(str)
    return df

# ----------------------------
# 분석 함수들 (캐싱 적용)
# ----------------------------
@st.cache_data(ttl=7200, show_spinner=False)
def analyze_sentiment_basic_cached(df_json):
    """기본 감성 분석 (캐싱용)"""
    df = pd.read_json(df_json)
    results = []
    
    for _, row in df.iterrows():
        text = str(row["content"])
        score = row["score"]
        
        pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)
        
        if score >= 4:
            sentiment = "긍정"
        elif score <= 2:
            sentiment = "부정"
        else:
            if pos_count > neg_count:
                sentiment = "긍정"
            elif neg_count > pos_count:
                sentiment = "부정"
            else:
                sentiment = "중립"
        
        results.append(sentiment)
    
    df["sentiment"] = results
    df["pos_score"] = 0
    df["neg_score"] = 0
    return df.to_json()

@st.cache_data(ttl=7200, show_spinner=False)
def analyze_sentiment_webtoon_cached(df_json):
    """웹툰/만화 특화 감성 분석 (캐싱용)"""
    df = pd.read_json(df_json)
    results = []
    pos_scores = []
    neg_scores = []
    
    for _, row in df.iterrows():
        text = str(row["content"])
        score = row["score"]
        
        # 가중치 합산
        pos_weight = sum(weight for word, weight in WEBTOON_SENTIMENT["positive"].items() if word in text)
        neg_weight = sum(weight for word, weight in WEBTOON_SENTIMENT["negative"].items() if word in text)
        
        pos_scores.append(pos_weight)
        neg_scores.append(neg_weight)
        
        # 평점 기반 기본 판단 + 가중치 보정
        if score >= 4:
            if neg_weight >= 6:
                sentiment = "부정" if neg_weight > pos_weight else "긍정"
            else:
                sentiment = "긍정"
        elif score <= 2:
            if pos_weight >= 6:
                sentiment = "긍정" if pos_weight > neg_weight else "부정"
            else:
                sentiment = "부정"
        else:
            diff = pos_weight - neg_weight
            if diff >= 2:
                sentiment = "긍정"
            elif diff <= -2:
                sentiment = "부정"
            else:
                sentiment = "중립"
        
        results.append(sentiment)
    
    df["sentiment"] = results
    df["pos_score"] = pos_scores
    df["neg_score"] = neg_scores
    return df.to_json()

def analyze_sentiment_basic(df):
    """기본 감성 분석 (래퍼)"""
    result_json = analyze_sentiment_basic_cached(df.to_json())
    return pd.read_json(result_json)

def analyze_sentiment_webtoon(df):
    """웹툰/만화 특화 감성 분석 (래퍼)"""
    result_json = analyze_sentiment_webtoon_cached(df.to_json())
    return pd.read_json(result_json)

def get_matched_keywords(text, is_webtoon_mode=False):
    """텍스트에서 매칭된 감성 키워드 추출"""
    if is_webtoon_mode:
        pos_matched = [(w, weight) for w, weight in WEBTOON_SENTIMENT["positive"].items() if w in text]
        neg_matched = [(w, weight) for w, weight in WEBTOON_SENTIMENT["negative"].items() if w in text]
    else:
        pos_matched = [(w, 1) for w in POSITIVE_WORDS if w in text]
        neg_matched = [(w, 1) for w in NEGATIVE_WORDS if w in text]
    return pos_matched, neg_matched

@st.cache_data(ttl=7200)
def analyze_topics(contents_tuple):
    """토픽 분류 - 리뷰별로 분류 (복수 토픽 허용)"""
    topic_priority = ["📚 콘텐츠", "💰 결제/가격", "📺 광고", "🐛 버그/오류", "📱 UI/UX", "🔔 알림/편의"]
    topic_data = {topic: [] for topic in topic_priority}
    
    # 요청 패턴 (이게 있으면 버그가 아님)
    request_patterns = ["해주", "해줘", "싶어", "바람", "원해", "으면 좋", "면 좋겠", "제발", "부탁", "없으면", "있으면"]
    
    for text in contents_tuple:
        text = str(text)
        is_request = any(p in text for p in request_patterns)
        
        # 복수 토픽 허용
        for topic in topic_priority:
            keywords = TOPIC_KEYWORDS[topic]
            
            # 버그/오류 토픽은 요청 패턴이 있으면 스킵
            if topic == "🐛 버그/오류" and is_request:
                continue
            
            if any(kw in text for kw in keywords):
                topic_data[topic].append(text)
    
    return topic_data

@st.cache_data(ttl=7200)
def extract_requests(contents_tuple):
    """요청사항 추출"""
    requests = []
    
    for text in contents_tuple:
        text = str(text)
        for pattern in REQUEST_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    request_text = "".join(match)
                else:
                    request_text = match
                if len(request_text) > 5:
                    requests.append(request_text)
    
    return Counter(requests).most_common(30)

@st.cache_data(ttl=7200)
def analyze_complaints_trigram(df):
    """불만 키워드 조합 분석 (1-2점 리뷰, 트리그램 - 3단어 조합)"""
    negative_df = df[df["score"] <= 2]
    
    if negative_df.empty:
        return [], [], pd.DataFrame()
    
    bigrams = []
    trigrams = []
    for text in negative_df["content"]:
        bigrams += extract_bigrams(text)
        trigrams += extract_trigrams(text)
    
    return Counter(bigrams).most_common(30), Counter(trigrams).most_common(30), negative_df

@st.cache_data(ttl=7200)
def analyze_positive_bigram(df):
    """긍정 키워드 조합 분석 (4-5점 리뷰, 바이그램)"""
    positive_df = df[df["score"] >= 4]
    
    if positive_df.empty:
        return [], pd.DataFrame()
    
    bigrams = []
    for text in positive_df["content"]:
        bigrams += extract_bigrams(text)
    
    return Counter(bigrams).most_common(30), positive_df

@st.cache_data(ttl=7200)
def generate_wordcloud_image(word_freq_tuple, font_path):
    word_freq = dict(word_freq_tuple)
    try:
        wc = WordCloud(
            font_path=font_path,
            width=800, height=400,
            background_color="white",
            colormap="viridis",
            max_words=50
        )
        wc.generate_from_frequencies(word_freq)
        img_buffer = BytesIO()
        wc.to_image().save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer.getvalue()
    except:
        return None

@st.cache_data(ttl=7200)
def extract_keywords_cached(contents_tuple):
    tokens = []
    for text in contents_tuple:
        tokens += simple_tokenizer(text)
    return tokens

@st.cache_data(ttl=7200)
def calculate_co_occurrence(contents_tuple):
    co_occurrence = {}
    for text in contents_tuple:
        tokens = simple_tokenizer(text)
        for i in range(len(tokens) - 1):
            a, b = tokens[i], tokens[i + 1]
            if a != b:
                co_occurrence.setdefault(a, []).append(b)
    return co_occurrence

# ----------------------------
# 메인 분석 표시 함수
# ----------------------------
def display_analysis(df, app_name="", data_info=""):
    if df.empty:
        st.error("❌ 데이터가 없습니다.")
        return
    
    if data_info:
        st.info(data_info)
    
    # 웹툰 특화 키워드 help 텍스트 (표 형태)
    webtoon_help = """
【긍정 키워드 (가중치)】
• 기본: 좋다(1), 재밌다(2), 강추(3), 최고(3)
• 웹툰특화: 작화좋다(2), 스토리탄탄(3), 정주행(2), 시간순삭(3)
• 극단: 갓작(3), 명작(3), 인생웹툰(3)

【부정 키워드 (가중치)】
• 기본: 별로(1), 노잼(3), 지루(2), 최악(3)
• 웹툰특화: 작화붕괴(3), 캐붕(3), 급전개(2), 떡밥방치(3)
• 극단: 하차(3), 시간낭비(3), 발암(3)
"""
    
    # 데이터 고유 키 생성 (캐싱용)
    data_key = f"{app_name}_{len(df)}"
    
    # 웹툰 특화 모드 토글
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ **{len(df):,}건** 리뷰 분석 완료! {f'({app_name})' if app_name else ''}")
    with col2:
        webtoon_mode = st.toggle("🎨 웹툰 특화 분석", value=True, help=webtoon_help)
    
    # 감성 분석: 이미 sentiment 컬럼이 있으면 그대로 사용
    if "sentiment" not in df.columns:
        # sentiment 없을 때만 분석 (새로 수집한 데이터)
        cache_key = f"analyzed_{data_key}_{'webtoon' if webtoon_mode else 'basic'}"
        if cache_key in st.session_state:
            df = st.session_state[cache_key]
        else:
            with st.spinner("🔄 감성 분석 중..."):
                if webtoon_mode:
                    df = analyze_sentiment_webtoon(df)
                else:
                    df = analyze_sentiment_basic(df)
                st.session_state[cache_key] = df
    
    # datetime 변환 확인
    if not pd.api.types.is_datetime64_any_dtype(df["at"]):
        df["at"] = pd.to_datetime(df["at"])
    
    contents_tuple = tuple(df["content"].tolist())
    
    # 탭 구성 (5개) - 순서: 통계, 토픽, 키워드, 요청/리뷰, 감성/불만
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 통계", "📂 토픽분류", "🔎 키워드분석", "🙏 요청/리뷰", "😊 감성/불만"
    ])
    
    # ----------------------------
    # 탭 1: 통계
    # ----------------------------
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 리뷰", f"{len(df):,}")
        with col2:
            st.metric("평균 평점", f"{df['score'].mean():.1f}⭐")
        with col3:
            pos_ratio = (df["sentiment"] == "긍정").sum() / len(df) * 100
            st.metric("긍정 비율", f"{pos_ratio:.0f}%")
        with col4:
            neg_ratio = (df["sentiment"] == "부정").sum() / len(df) * 100
            st.metric("부정 비율", f"{neg_ratio:.0f}%")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🗓️ 날짜별 리뷰")
            daily = df.groupby(df["at"].dt.date).size()
            st.line_chart(daily)
        
        with col2:
            st.markdown("#### ⭐ 평점 분포")
            scores = df["score"].value_counts().sort_index()
            st.bar_chart(scores)
    
    # ----------------------------
    # 탭 5: 감성/불만 분석 (통합)
    # ----------------------------
    with tab5:
        # 감성 분석 섹션
        st.markdown("### 😊 감성 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sentiment_counts = df["sentiment"].value_counts()
            for sentiment, count in sentiment_counts.items():
                pct = count / len(df) * 100
                if sentiment == "긍정":
                    st.success(f"😊 긍정: **{count:,}건** ({pct:.1f}%)")
                elif sentiment == "부정":
                    st.error(f"😤 부정: **{count:,}건** ({pct:.1f}%)")
                else:
                    st.warning(f"😐 중립: **{count:,}건** ({pct:.1f}%)")
        
        with col2:
            sentiment_by_score = df.groupby(["score", "sentiment"]).size().unstack(fill_value=0)
            st.dataframe(sentiment_by_score, use_container_width=True)
        
        # 웹툰 모드일 때 감성 점수 표시
        if webtoon_mode and "pos_score" in df.columns:
            st.markdown("---")
            st.markdown("#### 🎯 감성 점수 분포 (웹툰 특화)")
            col1, col2 = st.columns(2)
            with col1:
                avg_pos = df["pos_score"].mean()
                max_pos = df["pos_score"].max()
                st.metric("평균 긍정 점수", f"{avg_pos:.1f}", help=f"최대 {max_pos}")
            with col2:
                avg_neg = df["neg_score"].mean()
                max_neg = df["neg_score"].max()
                st.metric("평균 부정 점수", f"{avg_neg:.1f}", help=f"최대 {max_neg}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 😊 긍정 키워드 조합")
            pos_bigrams, _ = analyze_positive_bigram(df)
            if pos_bigrams:
                pos_df = pd.DataFrame(pos_bigrams[:10], columns=["키워드 조합", "빈도"])
                st.dataframe(pos_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 😤 부정 키워드 조합")
            neg_bigrams, neg_trigrams, _ = analyze_complaints_trigram(df)
            if neg_bigrams:
                neg_df = pd.DataFrame(neg_bigrams[:10], columns=["키워드 조합", "빈도"])
                st.dataframe(neg_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 불만 분석 섹션
        st.markdown("### 😤 불만 집중 분석 (1~2점)")
        
        neg_bigrams, neg_trigrams, neg_df = analyze_complaints_trigram(df)
        
        st.markdown(f"🔴 불만 리뷰: **{len(neg_df):,}건** ({len(neg_df)/len(df)*100:.1f}%)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 2단어 조합")
            if neg_bigrams:
                st.dataframe(pd.DataFrame(neg_bigrams[:15], columns=["조합", "빈도"]), use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 3단어 조합 (맥락)")
            if neg_trigrams:
                st.dataframe(pd.DataFrame(neg_trigrams[:15], columns=["조합", "빈도"]), use_container_width=True, hide_index=True)
        
        # 불만 리뷰 원문
        with st.expander(f"📋 불만 리뷰 원문 ({len(neg_df):,}건)", expanded=False):
            search_complaint = st.text_input("🔍 검색", key="complaint_search")
            filtered_neg = neg_df.copy()
            if search_complaint:
                filtered_neg = filtered_neg[filtered_neg["content"].str.contains(search_complaint, na=False)]
            
            display_neg = filtered_neg[["at", "score", "content"]].copy()
            display_neg["at"] = display_neg["at"].dt.strftime("%Y-%m-%d")
            display_neg.columns = ["날짜", "평점", "내용"]
            st.dataframe(display_neg, use_container_width=True, hide_index=True, height=300)
    
    # ----------------------------
    # 탭 2: 토픽분류
    # ----------------------------
    with tab2:
        st.markdown("### 📂 토픽별 리뷰 분류")
        
        topic_data = analyze_topics(contents_tuple)
        sorted_topics = sorted(topic_data.items(), key=lambda x: len(x[1]), reverse=True)
        
        # 요약 테이블
        summary_data = []
        for topic, reviews_list in sorted_topics:
            summary_data.append({"토픽": topic, "건수": len(reviews_list), "비율": f"{len(reviews_list)/len(df)*100:.1f}%"})
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 토픽별 펼침
        for topic, reviews_list in sorted_topics:
            with st.expander(f"{topic} ({len(reviews_list):,}건)", expanded=False):
                if reviews_list:
                    keywords = TOPIC_KEYWORDS[topic]
                    st.caption(f"🔑 키워드: {', '.join(keywords[:8])}")
                    for i, review in enumerate(reviews_list[:5], 1):
                        truncated = review[:120] + "..." if len(review) > 120 else review
                        st.text(f"{i}. {truncated}")
                else:
                    st.info("해당 토픽 리뷰 없음")
    
    # ----------------------------
    # 탭 3: 키워드 분석 (통합)
    # ----------------------------
    with tab3:
        # 키워드 심층 분석
        st.markdown("### 🔍 키워드 심층 분석")
        st.caption("특정 키워드 입력 시 해당 리뷰만 추출하여 분석")
        
        # 분석할 키워드 입력 (타이틀 + 인풋 가로 배치)
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown('<p style="margin-top: 8px;">분석할 키워드</p>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="keyword-input">', unsafe_allow_html=True)
            deep_keyword = st.text_input("분석할 키워드", value="컷츠", placeholder="예: 광고, 결제", key="deep_kw", max_chars=30, label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        
        if deep_keyword:
            keyword_df = df[df["content"].str.contains(deep_keyword, na=False, case=False)].copy()
            
            if keyword_df.empty:
                st.warning(f"'{deep_keyword}' 포함 리뷰 없음")
            else:
                st.success(f"**'{deep_keyword}'** 관련 **{len(keyword_df):,}건** ({len(keyword_df)/len(df)*100:.1f}%)")
                
                col1, col2, col3, col4 = st.columns(4)
                pos_cnt = (keyword_df["sentiment"] == "긍정").sum()
                neg_cnt = (keyword_df["sentiment"] == "부정").sum()
                
                with col1:
                    st.metric("리뷰 수", f"{len(keyword_df):,}")
                with col2:
                    st.metric("평균 평점", f"{keyword_df['score'].mean():.1f}⭐")
                with col3:
                    st.metric("긍정", f"{pos_cnt/len(keyword_df)*100:.0f}%")
                with col4:
                    st.metric("부정", f"{neg_cnt/len(keyword_df)*100:.0f}%")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 연관 키워드")
                    kw_tokens = extract_keywords_cached(tuple(keyword_df["content"].tolist()))
                    kw_tokens = [t for t in kw_tokens if deep_keyword not in t and t not in deep_keyword]
                    kw_counter = Counter(kw_tokens).most_common(10)
                    if kw_counter:
                        st.dataframe(pd.DataFrame(kw_counter, columns=["키워드", "빈도"]), use_container_width=True, hide_index=True)
                
                with col2:
                    st.markdown("#### 키워드 조합")
                    bigrams = []
                    for text in keyword_df["content"]:
                        bigrams += extract_bigrams(text)
                    bigrams = [b for b in bigrams if deep_keyword in b]
                    bigram_cnt = Counter(bigrams).most_common(10)
                    if bigram_cnt:
                        st.dataframe(pd.DataFrame(bigram_cnt, columns=["조합", "빈도"]), use_container_width=True, hide_index=True)
                
                # 긍정/부정 리뷰 비교
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"#### 😊 긍정 ({pos_cnt}건)")
                    for _, row in keyword_df[keyword_df["sentiment"] == "긍정"].head(5).iterrows():
                        st.caption(f"⭐{row['score']} | {row['content'][:80]}...")
                with col2:
                    st.markdown(f"#### 😤 부정 ({neg_cnt}건)")
                    for _, row in keyword_df[keyword_df["sentiment"] == "부정"].head(5).iterrows():
                        st.caption(f"⭐{row['score']} | {row['content'][:80]}...")
                
                st.markdown("---")
                
                # 하위: 긍부정별 최다 빈도 키워드 분석
                st.markdown(f"### 📊 '{deep_keyword}' 연관 긍부정 키워드 분석")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 😊 긍정 리뷰 최다 키워드")
                    pos_keyword_df = keyword_df[keyword_df["sentiment"] == "긍정"]
                    if not pos_keyword_df.empty:
                        pos_tokens = extract_keywords_cached(tuple(pos_keyword_df["content"].tolist()))
                        pos_tokens = [t for t in pos_tokens if deep_keyword not in t and t not in deep_keyword]
                        pos_kw_counter = Counter(pos_tokens).most_common(15)
                        if pos_kw_counter:
                            st.dataframe(pd.DataFrame(pos_kw_counter, columns=["키워드", "빈도"]), use_container_width=True, hide_index=True)
                            
                            # 워드클라우드
                            img_bytes = generate_wordcloud_image(tuple(pos_kw_counter), FONT_PATH)
                            if img_bytes:
                                st.image(img_bytes, use_container_width=True)
                    else:
                        st.info("긍정 리뷰 없음")
                
                with col2:
                    st.markdown("#### 😤 부정 리뷰 최다 키워드")
                    neg_keyword_df = keyword_df[keyword_df["sentiment"] == "부정"]
                    if not neg_keyword_df.empty:
                        neg_tokens = extract_keywords_cached(tuple(neg_keyword_df["content"].tolist()))
                        neg_tokens = [t for t in neg_tokens if deep_keyword not in t and t not in deep_keyword]
                        neg_kw_counter = Counter(neg_tokens).most_common(15)
                        if neg_kw_counter:
                            st.dataframe(pd.DataFrame(neg_kw_counter, columns=["키워드", "빈도"]), use_container_width=True, hide_index=True)
                            
                            # 워드클라우드
                            img_bytes = generate_wordcloud_image(tuple(neg_kw_counter), FONT_PATH)
                            if img_bytes:
                                st.image(img_bytes, use_container_width=True)
                    else:
                        st.info("부정 리뷰 없음")
        
        else:
            st.caption("💡 추천: 광고, 결제, 버그, 로딩, 작품, 연재, 쿠키")
    
    # ----------------------------
    # 탭 4: 요청/리뷰 (통합)
    # ----------------------------
    with tab4:
        # 요청사항 섹션
        st.markdown("### 🙏 사용자 요청사항")
        
        requests = extract_requests(contents_tuple)
        
        if requests:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 요청사항 TOP 15")
                st.dataframe(pd.DataFrame(requests[:15], columns=["요청", "횟수"]), use_container_width=True, hide_index=True)
            with col2:
                st.markdown("#### 요청 빈도")
                st.bar_chart(pd.DataFrame(requests[:8], columns=["요청", "횟수"]).set_index("요청"))
        else:
            st.info("요청사항 없음")
        
        st.markdown("---")
        
        # 리뷰 원문 섹션
        st.markdown("### 📝 리뷰 원문")
        
        # 키워드 검색, 평점, 감성 같은 라인
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="keyword-input">', unsafe_allow_html=True)
            keyword = st.text_input("키워드 검색", key="review_search", max_chars=30, placeholder="검색어 입력")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            score_filter = st.multiselect("평점", [1,2,3,4,5], default=[1,2,3,4,5], key="review_score")
        with col3:
            sentiment_filter = st.multiselect("감성", ["긍정", "중립", "부정"], default=["긍정", "중립", "부정"], key="review_sent")
        
        filtered = df[df["score"].isin(score_filter) & df["sentiment"].isin(sentiment_filter)]
        if keyword:
            filtered = filtered[filtered["content"].str.contains(keyword, na=False)]
        
        st.write(f"**{len(filtered):,}건**")
        
        display_df = filtered[["at", "score", "sentiment", "content"]].copy()
        display_df["at"] = display_df["at"].dt.strftime("%Y-%m-%d")
        display_df.columns = ["날짜", "평점", "감성", "내용"]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

# ----------------------------
# 메인 UI
# ----------------------------
st.markdown("#### 📊 앱 리뷰 분석 &nbsp;&nbsp;|&nbsp;&nbsp; [GitHub](https://github.com/blendiing/appread)")

# 사이드바
with st.sidebar:
    st.markdown("#### 🔍 앱 ID")
    app_id_input = st.text_input(
        "앱 ID",
        value="",
        placeholder="com.example.app",
        label_visibility="collapsed"
    )
    
    # 샘플 앱 ID - 컴팩트하게
    with st.expander("📋 샘플 앱 ID", expanded=False):
        st.code("com.nhn.android.webtoon")
        st.caption("네이버 웹툰")
        st.code("com.kakaopage.app")
        st.caption("카카오페이지")
        st.code("com.initialcoms.ridi")
        st.caption("리디북스")
    
    st.markdown("---")
    
    # 수집 옵션
    review_count = st.select_slider(
        "📊 수집 리뷰 수",
        options=[100, 300, 500, 700, 1000],
        value=500
    )
    
    # 데이터 수집 버튼
    has_input = app_id_input is not None and len(app_id_input.strip()) > 0
    collect_btn = st.button(
        "🚀 수집 시작", 
        type="primary", 
        use_container_width=True,
        disabled=(not has_input)
    )
    
    if not has_input:
        st.caption("💡 앱 ID 입력 시 활성화")

# 메인 콘텐츠
# 수집 버튼 클릭 시 데이터 수집
if collect_btn and has_input:
    with st.spinner(f"📥 {app_id_input} 리뷰 수집 중... ({review_count}건)"):
        df = get_reviews_cached(app_id_input, count=review_count)
        df = df.sort_values(by="at", ascending=False)
        st.session_state["collected_df"] = df
        st.session_state["collected_app"] = app_id_input

# 수집된 데이터가 있으면 표시
if st.session_state.get("collected_df") is not None and not st.session_state["collected_df"].empty:
    display_analysis(st.session_state["collected_df"], st.session_state.get("collected_app", ""))

# 수집된 데이터가 없으면 기본 데이터 표시 (load_default_data가 이미 분석 완료)
else:
    default_df = load_default_data()  # @st.cache_data로 캐싱됨, 감성분석 포함
    display_analysis(default_df, "네이버 웹툰", "📌 **기본 데이터**: 네이버 웹툰 리뷰 1,000건 (2025.01.19 기준)")

st.markdown("---")
st.caption("Made with ❤️ using Streamlit | 데이터: Google Play Store")
