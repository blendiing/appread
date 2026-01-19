import streamlit as st
from google_play_scraper import reviews, Sort
import pandas as pd
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import os
from io import BytesIO
from datetime import datetime

# ----------------------------
# 페이지 설정
# ----------------------------
st.set_page_config(
    page_title="경쟁사 앱 리뷰 분석",
    page_icon="📊",
    layout="wide"
)

# ----------------------------
# 폰트 경로 설정 (시스템 폰트 사용)
# ----------------------------
def get_font_path():
    """사용 가능한 한글 폰트 찾기"""
    possible_paths = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
    "웹툰", "그냥", "이거", "저거", "그것", "이것", "저것", "하는", "있는", "없는",
    "해서", "하고", "해요", "합니다", "입니다", "있어요", "없어요", "같아요",
    "이런", "저런", "그런", "어떤", "무슨", "왜", "어디", "언제", "어떻게",
    "근데", "그래서", "하지만", "그러나", "그리고", "또한", "그래도",
    "있어", "없어", "하면", "이용", "사용", "정도", "이상", "계속", "다시", "처음", "마지막"
}

# ----------------------------
# 유틸리티 함수
# ----------------------------
def simple_tokenizer(text):
    """정규식 기반 한글 토크나이저"""
    tokens = re.findall(r"[가-힣]{2,}", str(text))
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]
    return tokens

@st.cache_data(ttl=7200, show_spinner=False)
def get_reviews_cached(app_id, count=1000):
    """Google Play 리뷰 수집 (캐싱)"""
    result = []
    continuation_token = None
    
    try:
        while len(result) < count:
            batch_size = min(100, count - len(result))
            review_batch, continuation_token = reviews(
                app_id,
                lang="ko",
                country="kr",
                sort=Sort.NEWEST,
                count=batch_size,
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

@st.cache_data(ttl=86400, show_spinner=False)
def get_default_data():
    """
    디폴트 데이터 로드
    - 네이버 웹툰 리뷰
    - 2025년 1월 19일 19:00 이전 데이터 1000건
    """
    cutoff_date = datetime(2025, 1, 19, 19, 0, 0)
    
    df = get_reviews_cached("com.nhn.android.webtoon", count=1500)
    
    if not df.empty:
        # 기준 시간 이전 데이터만 필터링
        df = df[df["at"] < cutoff_date]
        # 최신순 정렬 후 1000건만
        df = df.sort_values(by="at", ascending=False).head(1000)
    
    return df

@st.cache_data(ttl=7200, show_spinner=False)
def extract_keywords_cached(contents_tuple):
    """키워드 추출 (캐싱)"""
    tokens = []
    for text in contents_tuple:
        tokens += simple_tokenizer(text)
    return tokens

@st.cache_data(ttl=7200, show_spinner=False)
def generate_wordcloud_image(word_freq_tuple, font_path):
    """워드클라우드를 이미지로 생성"""
    word_freq = dict(word_freq_tuple)
    
    try:
        wc = WordCloud(
            font_path=font_path,
            width=800,
            height=400,
            background_color="white",
            colormap="viridis",
            max_words=50
        )
        wc.generate_from_frequencies(word_freq)
        
        img_buffer = BytesIO()
        wc.to_image().save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    except Exception as e:
        return None

@st.cache_data(ttl=7200, show_spinner=False)
def calculate_co_occurrence(contents_tuple):
    """연관어 계산 (캐싱)"""
    co_occurrence = {}
    for text in contents_tuple:
        tokens = simple_tokenizer(text)
        for i in range(len(tokens) - 1):
            a, b = tokens[i], tokens[i + 1]
            if a != b:
                co_occurrence.setdefault(a, []).append(b)
    return co_occurrence

def display_analysis(df, app_name="", data_info=""):
    """분석 결과 표시"""
    
    if df.empty:
        st.error("❌ 데이터가 없습니다.")
        return
    
    # 데이터 정보 표시
    if data_info:
        st.info(data_info)
    
    st.success(f"✅ **{len(df):,}건** 리뷰 분석 완료! {f'({app_name})' if app_name else ''}")
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📈 통계", "💬 키워드", "🔗 연관어", "📝 리뷰"])
    
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
            recent = df[df["at"] >= df["at"].max() - pd.Timedelta(days=7)]
            st.metric("최근 7일", f"{len(recent):,}")
        with col4:
            ratio = (df["score"] == 5).sum() / len(df) * 100
            st.metric("5점 비율", f"{ratio:.0f}%")
        
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
    # 탭 2: 키워드
    # ----------------------------
    with tab2:
        st.subheader("💬 주요 키워드 TOP 30")
        
        contents_tuple = tuple(df["content"].tolist())
        tokens = extract_keywords_cached(contents_tuple)
        counter = Counter(tokens)
        common_words = counter.most_common(30)
        
        if common_words:
            word_freq_tuple = tuple(common_words)
            img_bytes = generate_wordcloud_image(word_freq_tuple, FONT_PATH)
            
            if img_bytes:
                st.image(img_bytes, use_container_width=True)
            else:
                st.warning("워드클라우드 생성 불가. 아래 표를 확인하세요.")
            
            keyword_df = pd.DataFrame(common_words, columns=["키워드", "빈도"])
            
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(keyword_df.head(15), use_container_width=True, hide_index=True)
            with col2:
                st.dataframe(keyword_df.tail(15), use_container_width=True, hide_index=True)
    
    # ----------------------------
    # 탭 3: 연관어
    # ----------------------------
    with tab3:
        st.subheader("🔗 키워드 연관 단어")
        
        contents_tuple = tuple(df["content"].tolist())
        co_occurrence = calculate_co_occurrence(contents_tuple)
        
        related_words = []
        for k, v in counter.most_common(20):
            related = Counter(co_occurrence.get(k, [])).most_common(5)
            related_words.append({
                "키워드": k,
                "빈도": v,
                "연관단어": ", ".join([f"{r[0]}({r[1]})" for r in related]) if related else "-"
            })
        
        st.dataframe(pd.DataFrame(related_words), use_container_width=True, hide_index=True)
    
    # ----------------------------
    # 탭 4: 리뷰 원문
    # ----------------------------
    with tab4:
        st.subheader("📝 리뷰 원문")
        
        col1, col2 = st.columns(2)
        with col1:
            score_filter = st.multiselect("평점", [1,2,3,4,5], default=[1,2,3,4,5])
        with col2:
            keyword = st.text_input("검색")
        
        filtered = df[df["score"].isin(score_filter)]
        if keyword:
            filtered = filtered[filtered["content"].str.contains(keyword, na=False)]
        
        st.write(f"**{len(filtered):,}건**")
        
        display_df = filtered.head(100)[["at", "score", "content"]].copy()
        display_df["at"] = display_df["at"].dt.strftime("%Y-%m-%d")
        display_df.columns = ["날짜", "평점", "내용"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ----------------------------
# 메인 UI
# ----------------------------
st.title("📊 경쟁사 앱 리뷰 분석 대시보드")
st.caption("Google Play Store 리뷰를 분석하여 경쟁사 인사이트를 도출합니다.")

# ----------------------------
# 사이드바
# ----------------------------
with st.sidebar:
    st.header("⚙️ 설정")
    
    st.markdown("---")
    
    # 모드 선택
    mode = st.radio(
        "분석 모드",
        ["📌 기본 데이터 보기", "🔄 새로 수집하기"],
        index=0
    )
    
    if mode == "🔄 새로 수집하기":
        st.markdown("---")
        
        # 앱 선택
        selected_app = st.selectbox(
            "앱 선택",
            options=list(APP_LIST.keys()),
            index=0
        )
        
        # 또는 직접 입력
        custom_app_id = st.text_input(
            "또는 앱 ID 직접 입력",
            placeholder="com.example.app"
        )
        
        review_count = st.select_slider(
            "수집할 리뷰 수",
            options=[100, 300, 500, 700, 1000],
            value=500
        )
        
        collect_btn = st.button("🔍 데이터 수집", type="primary", use_container_width=True)
    else:
        collect_btn = False
    
    st.markdown("---")
    st.markdown("##### 📌 지원 앱 목록")
    for name in APP_LIST.keys():
        st.caption(f"• {name}")

# ----------------------------
# 메인 콘텐츠
# ----------------------------
if mode == "📌 기본 데이터 보기":
    
    with st.spinner("📥 기본 데이터 로딩 중..."):
        df = get_default_data()
    
    display_analysis(
        df, 
        app_name="네이버 웹툰",
        data_info="📌 **기본 데이터**: 네이버 웹툰 리뷰 1,000건 (2025.01.19 19:00 기준 이전 데이터)"
    )

else:  # 새로 수집하기
    if collect_btn:
        # 앱 ID 결정
        if custom_app_id:
            app_id = custom_app_id
            app_name = custom_app_id
        else:
            app_id = APP_LIST[selected_app]
            app_name = selected_app
        
        with st.spinner(f"📥 {app_name} 리뷰 수집 중... ({review_count}건)"):
            df = get_reviews_cached(app_id, count=review_count)
            df = df.sort_values(by="at", ascending=False)
            st.session_state["collected_df"] = df
            st.session_state["collected_app"] = app_name
    
    # 수집된 데이터가 있으면 표시
    if st.session_state.get("collected_df") is not None and not st.session_state["collected_df"].empty:
        df = st.session_state["collected_df"]
        app_name = st.session_state.get("collected_app", "")
        display_analysis(df, app_name)
    else:
        st.info("👈 사이드바에서 앱을 선택하고 **데이터 수집** 버튼을 클릭하세요!")
        
        st.markdown("""
        ### 🎯 분석 가능 항목
        - 📈 **통계**: 평점 분포, 날짜별 추이
        - 💬 **키워드**: 자주 언급되는 단어 TOP 30
        - 🔗 **연관어**: 키워드 간 관계 분석
        - 📝 **리뷰 원문**: 필터링 & 검색
        """)

# ----------------------------
# 푸터
# ----------------------------
st.markdown("---")
st.caption("Made with ❤️ using Streamlit | 데이터: Google Play Store")
