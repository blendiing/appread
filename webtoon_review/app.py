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
# 감성 키워드 정의
# ----------------------------
POSITIVE_WORDS = {"좋아", "최고", "재밌", "재미있", "편리", "편해", "만족", "추천", "굿", "대박", "사랑", "완벽", "훌륭", "감사", "행복", "즐거"}
NEGATIVE_WORDS = {"별로", "싫어", "최악", "불편", "짜증", "화나", "실망", "후회", "쓰레기", "폭망", "구림", "개선", "답답", "불만", "짜증나", "에러", "버그"}

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

@st.cache_data(ttl=86400, show_spinner=False)
def load_default_data():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), "default_reviews.csv")
        df = pd.read_csv(csv_path)
        df["at"] = pd.to_datetime(df["at"])
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
# 분석 함수들
# ----------------------------
@st.cache_data(ttl=7200)
def analyze_sentiment(df):
    """감성 분석"""
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
    
    df = df.copy()
    df["sentiment"] = results
    return df

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
def analyze_complaints_bigram(df):
    """불만 키워드 조합 분석 (1-2점 리뷰, 바이그램)"""
    negative_df = df[df["score"] <= 2]
    
    if negative_df.empty:
        return [], pd.DataFrame()
    
    bigrams = []
    for text in negative_df["content"]:
        bigrams += extract_bigrams(text)
    
    return Counter(bigrams).most_common(30), negative_df

@st.cache_data(ttl=7200)
def analyze_positive(df):
    """긍정 키워드 분석 (4-5점 리뷰)"""
    positive_df = df[df["score"] >= 4]
    
    if positive_df.empty:
        return [], pd.DataFrame()
    
    tokens = []
    for text in positive_df["content"]:
        tokens += simple_tokenizer(text)
    
    return Counter(tokens).most_common(30), positive_df

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
    
    st.success(f"✅ **{len(df):,}건** 리뷰 분석 완료! {f'({app_name})' if app_name else ''}")
    
    # 감성 분석 적용
    df = analyze_sentiment(df)
    contents_tuple = tuple(df["content"].tolist())
    
    # 탭 구성
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 통계", "😊 감성분석", "📂 토픽분류", "😤 불만분석", "🙏 요청사항", "💬 키워드", "📝 리뷰"
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
            st.subheader("🗓️ 날짜별 리뷰")
            daily = df.groupby(df["at"].dt.date).size()
            st.line_chart(daily)
        
        with col2:
            st.subheader("⭐ 평점 분포")
            scores = df["score"].value_counts().sort_index()
            st.bar_chart(scores)
    
    # ----------------------------
    # 탭 2: 감성 분석
    # ----------------------------
    with tab2:
        st.subheader("😊 감성 분석 결과")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sentiment_counts = df["sentiment"].value_counts()
            st.markdown("#### 감성 분포")
            
            for sentiment, count in sentiment_counts.items():
                pct = count / len(df) * 100
                if sentiment == "긍정":
                    st.success(f"😊 긍정: **{count:,}건** ({pct:.1f}%)")
                elif sentiment == "부정":
                    st.error(f"😤 부정: **{count:,}건** ({pct:.1f}%)")
                else:
                    st.warning(f"😐 중립: **{count:,}건** ({pct:.1f}%)")
        
        with col2:
            st.markdown("#### 평점별 감성")
            sentiment_by_score = df.groupby(["score", "sentiment"]).size().unstack(fill_value=0)
            st.dataframe(sentiment_by_score, use_container_width=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 😊 긍정 리뷰 키워드")
            pos_keywords, _ = analyze_positive(df)
            if pos_keywords:
                pos_df = pd.DataFrame(pos_keywords[:15], columns=["키워드", "빈도"])
                st.dataframe(pos_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 😤 부정 리뷰 키워드 조합")
            neg_bigrams, _ = analyze_complaints_bigram(df)
            if neg_bigrams:
                neg_df = pd.DataFrame(neg_bigrams[:15], columns=["키워드 조합", "빈도"])
                st.dataframe(neg_df, use_container_width=True, hide_index=True)
    
    # ----------------------------
    # 탭 3: 토픽 분류 (세로 나열)
    # ----------------------------
    with tab3:
        st.subheader("📂 토픽별 리뷰 분류")
        st.caption("리뷰가 어떤 주제에 대해 이야기하는지 분류합니다.")
        
        topic_data = analyze_topics(contents_tuple)
        
        # 토픽별 개수 정렬
        sorted_topics = sorted(topic_data.items(), key=lambda x: len(x[1]), reverse=True)
        
        # 전체 요약
        st.markdown("#### 📊 토픽별 언급량 요약")
        summary_data = []
        for topic, reviews_list in sorted_topics:
            summary_data.append({"토픽": topic, "건수": len(reviews_list), "비율": f"{len(reviews_list)/len(df)*100:.1f}%"})
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 카테고리별 세로 나열
        for topic, reviews_list in sorted_topics:
            with st.expander(f"{topic} ({len(reviews_list):,}건)", expanded=False):
                if reviews_list:
                    # 해당 토픽 키워드 표시
                    keywords = TOPIC_KEYWORDS[topic]
                    st.caption(f"🔑 관련 키워드: {', '.join(keywords[:10])}")
                    
                    st.markdown("**📋 대표 리뷰:**")
                    for i, review in enumerate(reviews_list[:10], 1):
                        truncated = review[:150] + "..." if len(review) > 150 else review
                        st.text(f"{i}. {truncated}")
                else:
                    st.info("해당 토픽의 리뷰가 없습니다.")
    
    # ----------------------------
    # 탭 4: 불만 분석 (키워드 조합)
    # ----------------------------
    with tab4:
        st.subheader("😤 불만 사항 집중 분석")
        st.caption("1~2점 리뷰에서 키워드 조합을 분석하여 구체적인 불만 포인트를 파악합니다.")
        
        neg_bigrams, neg_df = analyze_complaints_bigram(df)
        
        st.markdown(f"#### 🔴 불만 리뷰 수: **{len(neg_df):,}건** ({len(neg_df)/len(df)*100:.1f}%)")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔥 불만 키워드 조합 TOP 20")
            st.caption("어떤 단어들이 함께 언급되는지 파악합니다.")
            if neg_bigrams:
                neg_df_display = pd.DataFrame(neg_bigrams[:20], columns=["키워드 조합", "빈도"])
                st.dataframe(neg_df_display, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 💡 주요 불만 패턴 해석")
            if neg_bigrams:
                st.markdown("**가장 많이 언급된 불만:**")
                for i, (bigram, count) in enumerate(neg_bigrams[:5], 1):
                    st.markdown(f"{i}. **{bigram}** ({count}회)")
        
        st.markdown("---")
        st.markdown("#### 📋 불만 리뷰 원문 (최근 20건)")
        
        if not neg_df.empty:
            display_neg = neg_df.head(20)[["at", "score", "content"]].copy()
            display_neg["at"] = display_neg["at"].dt.strftime("%Y-%m-%d")
            display_neg.columns = ["날짜", "평점", "내용"]
            st.dataframe(display_neg, use_container_width=True, hide_index=True)
    
    # ----------------------------
    # 탭 5: 요청사항
    # ----------------------------
    with tab5:
        st.subheader("🙏 사용자 요청사항 추출")
        st.caption("'~해주세요', '~했으면 좋겠어요' 등의 패턴에서 사용자 니즈를 추출합니다.")
        
        requests = extract_requests(contents_tuple)
        
        if requests:
            st.markdown(f"#### 총 **{len(requests)}개** 요청사항 발견")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📌 주요 요청사항")
                req_df = pd.DataFrame(requests[:15], columns=["요청 내용", "언급 횟수"])
                st.dataframe(req_df, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### 📊 요청 빈도")
                req_chart = pd.DataFrame(requests[:10], columns=["요청", "횟수"]).set_index("요청")
                st.bar_chart(req_chart)
            
            st.markdown("---")
            st.markdown("#### 💡 핵심 인사이트")
            
            if requests:
                top_requests = [r[0] for r in requests[:5]]
                st.markdown("**사용자들이 가장 원하는 것:**")
                for i, req in enumerate(top_requests, 1):
                    st.markdown(f"{i}. {req}")
        else:
            st.info("추출된 요청사항이 없습니다.")
    
    # ----------------------------
    # 탭 6: 키워드
    # ----------------------------
    with tab6:
        st.subheader("💬 전체 키워드 분석")
        
        tokens = extract_keywords_cached(contents_tuple)
        counter = Counter(tokens)
        common_words = counter.most_common(30)
        
        if common_words:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                img_bytes = generate_wordcloud_image(tuple(common_words), FONT_PATH)
                if img_bytes:
                    st.image(img_bytes, use_container_width=True)
            
            with col2:
                keyword_df = pd.DataFrame(common_words, columns=["키워드", "빈도"])
                st.dataframe(keyword_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 🔗 연관 키워드")
        
        co_occurrence = calculate_co_occurrence(contents_tuple)
        related_words = []
        for k, v in counter.most_common(15):
            related = Counter(co_occurrence.get(k, [])).most_common(5)
            related_words.append({
                "키워드": k,
                "빈도": v,
                "연관단어": ", ".join([f"{r[0]}({r[1]})" for r in related]) if related else "-"
            })
        
        st.dataframe(pd.DataFrame(related_words), use_container_width=True, hide_index=True)
    
    # ----------------------------
    # 탭 7: 리뷰 원문
    # ----------------------------
    with tab7:
        st.subheader("📝 리뷰 원문")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            score_filter = st.multiselect("평점", [1,2,3,4,5], default=[1,2,3,4,5])
        with col2:
            sentiment_filter = st.multiselect("감성", ["긍정", "중립", "부정"], default=["긍정", "중립", "부정"])
        with col3:
            keyword = st.text_input("검색")
        
        filtered = df[df["score"].isin(score_filter) & df["sentiment"].isin(sentiment_filter)]
        if keyword:
            filtered = filtered[filtered["content"].str.contains(keyword, na=False)]
        
        st.write(f"**{len(filtered):,}건**")
        
        display_df = filtered.head(100)[["at", "score", "sentiment", "content"]].copy()
        display_df["at"] = display_df["at"].dt.strftime("%Y-%m-%d")
        display_df.columns = ["날짜", "평점", "감성", "내용"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ----------------------------
# 메인 UI
# ----------------------------
st.title("📊 경쟁사 앱 리뷰 분석 대시보드")
st.caption("Google Play Store 리뷰를 분석하여 경쟁사 인사이트를 도출합니다.")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    st.markdown("---")
    
    mode = st.radio(
        "분석 모드",
        ["📌 기본 데이터 보기", "🔄 새로 수집하기"],
        index=0
    )
    
    if mode == "🔄 새로 수집하기":
        st.markdown("---")
        selected_app = st.selectbox("앱 선택", list(APP_LIST.keys()))
        custom_app_id = st.text_input("또는 앱 ID 직접 입력", placeholder="com.example.app")
        review_count = st.select_slider("수집할 리뷰 수", options=[100, 300, 500, 700, 1000], value=500)
        collect_btn = st.button("🔍 데이터 수집", type="primary", use_container_width=True)
    else:
        collect_btn = False
    
    st.markdown("---")
    st.markdown("##### 📌 지원 앱")
    for name in APP_LIST.keys():
        st.caption(f"• {name}")

# 메인 콘텐츠
if mode == "📌 기본 데이터 보기":
    with st.spinner("📥 기본 데이터 로딩 중..."):
        df = load_default_data()
    display_analysis(df, "네이버 웹툰", "📌 **기본 데이터**: 네이버 웹툰 리뷰 1,000건 (2025.01.19 기준)")

else:
    if collect_btn:
        app_id = custom_app_id if custom_app_id else APP_LIST[selected_app]
        app_name = custom_app_id if custom_app_id else selected_app
        
        with st.spinner(f"📥 {app_name} 리뷰 수집 중... ({review_count}건)"):
            df = get_reviews_cached(app_id, count=review_count)
            df = df.sort_values(by="at", ascending=False)
            st.session_state["collected_df"] = df
            st.session_state["collected_app"] = app_name
    
    if st.session_state.get("collected_df") is not None and not st.session_state["collected_df"].empty:
        display_analysis(st.session_state["collected_df"], st.session_state.get("collected_app", ""))
    else:
        st.info("👈 사이드바에서 앱을 선택하고 **데이터 수집** 버튼을 클릭하세요!")

st.markdown("---")
st.caption("Made with ❤️ using Streamlit | 데이터: Google Play Store")
