import streamlit as st
from google_play_scraper import reviews, Sort
import pandas as pd
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re

# ----------------------------
# 페이지 설정
# ----------------------------
st.set_page_config(
    page_title="네이버 웹툰 앱리뷰 분석",
    page_icon="📊",
    layout="wide"
)

# ----------------------------
# 한글 처리를 위한 간단한 토크나이저 (KoNLPy 대체)
# Streamlit Cloud에서 Java 설치가 어려우므로 정규식 기반으로 처리
# ----------------------------

# 불용어 정의
STOPWORDS = {
    "너무", "정말", "진짜", "매우", "아주", "완전", "되게", "꽤", "좀", "약간", "살짝",
    "웹툰", "그냥", "이거", "저거", "그것", "이것", "저것", "하는", "있는", "없는",
    "해서", "하고", "해요", "합니다", "입니다", "있어요", "없어요", "같아요",
    "이런", "저런", "그런", "어떤", "무슨", "왜", "어디", "언제", "어떻게",
    "근데", "그래서", "하지만", "그러나", "그리고", "또한", "그래도",
    "앱", "어플", "앱이", "어플이", "네이버", "naver"
}

def simple_tokenizer(text):
    """정규식 기반 한글 토크나이저"""
    # 한글 2글자 이상 단어 추출
    tokens = re.findall(r"[가-힣]{2,}", str(text))
    # 불용어 제거
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]
    return tokens

@st.cache_data(ttl=3600, show_spinner=False)
def get_reviews(app_id, count=1000):
    """Google Play 리뷰 수집 (캐싱 적용)"""
    result = []
    continuation_token = None
    
    while len(result) < count:
        batch_size = min(200, count - len(result))
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
    
    df = pd.DataFrame(result)
    if not df.empty:
        df["at"] = pd.to_datetime(df["at"])
        df["content"] = df["content"].astype(str)
    return df

def extract_keywords(df):
    """키워드 추출"""
    tokens = []
    for text in df["content"]:
        tokens += simple_tokenizer(text)
    return tokens

# ----------------------------
# 메인 UI
# ----------------------------
st.title("📊 네이버 웹툰 앱 리뷰 분석 대시보드")
st.markdown("Google Play Store 리뷰를 실시간으로 수집하고 분석합니다.")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    app_id = st.text_input(
        "앱 ID",
        value="com.nhn.android.webtoon",
        help="Google Play Store 앱 ID를 입력하세요"
    )
    
    review_count = st.slider(
        "수집할 리뷰 수",
        min_value=100,
        max_value=3000,
        value=1000,
        step=100
    )
    
    analyze_btn = st.button("🔍 분석 시작", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📌 다른 앱 분석 예시")
    st.code("com.kakaopage.app", language=None)
    st.code("com.lezhin.comics", language=None)
    st.code("com.toptoon.app", language=None)

# ----------------------------
# 데이터 수집 및 분석
# ----------------------------
if analyze_btn or "df" in st.session_state:
    
    if analyze_btn:
        with st.spinner(f"📥 리뷰 데이터를 불러오는 중... (최대 {review_count}건)"):
            df = get_reviews(app_id, review_count)
            df = df.sort_values(by="at", ascending=False)
            st.session_state["df"] = df
            st.session_state["app_id"] = app_id
    else:
        df = st.session_state["df"]
        app_id = st.session_state.get("app_id", app_id)
    
    if df.empty:
        st.error("리뷰 데이터를 불러올 수 없습니다. 앱 ID를 확인해주세요.")
    else:
        st.success(f"✅ 총 **{len(df):,}건**의 리뷰 데이터를 불러왔습니다. (앱 ID: `{app_id}`)")
        
        # 탭 구성
        tab1, tab2, tab3, tab4 = st.tabs(["📈 통계", "💬 키워드", "🔗 연관어", "📝 리뷰 원문"])
        
        # ----------------------------
        # 탭 1: 기본 통계
        # ----------------------------
        with tab1:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("총 리뷰 수", f"{len(df):,}건")
            with col2:
                avg_score = df["score"].mean()
                st.metric("평균 평점", f"{avg_score:.2f}⭐")
            with col3:
                recent_week = df[df["at"] >= df["at"].max() - pd.Timedelta(days=7)]
                st.metric("최근 7일 리뷰", f"{len(recent_week):,}건")
            with col4:
                five_star_ratio = (df["score"] == 5).sum() / len(df) * 100
                st.metric("5점 비율", f"{five_star_ratio:.1f}%")
            
            st.markdown("---")
            
            # 날짜별 리뷰 수 추이
            st.subheader("🗓️ 날짜별 리뷰 수 추이")
            daily_counts = df.groupby(df["at"].dt.date).size().reset_index(name="리뷰수")
            daily_counts.columns = ["날짜", "리뷰수"]
            st.line_chart(daily_counts.set_index("날짜"))
            
            # 평점 분포
            st.subheader("⭐ 평점 분포")
            score_counts = df["score"].value_counts().sort_index()
            st.bar_chart(score_counts)
        
        # ----------------------------
        # 탭 2: 키워드 분석
        # ----------------------------
        with tab2:
            st.subheader("💬 주요 키워드 TOP 30")
            
            tokens = extract_keywords(df)
            counter = Counter(tokens)
            common_words = counter.most_common(30)
            
            if common_words:
                # 워드클라우드
                try:
                    # 시스템 폰트 찾기
                    import matplotlib.font_manager as fm
                    font_path = None
                    
                    # 가능한 한글 폰트 경로들
                    possible_fonts = [
                        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    ]
                    
                    for fp in possible_fonts:
                        try:
                            if fm.FontProperties(fname=fp):
                                font_path = fp
                                break
                        except:
                            continue
                    
                    wordcloud = WordCloud(
                        font_path=font_path,
                        width=800,
                        height=400,
                        background_color="white",
                        colormap="viridis"
                    ).generate_from_frequencies(dict(common_words))
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wordcloud, interpolation="bilinear")
                    ax.axis("off")
                    st.pyplot(fig)
                    plt.close()
                except Exception as e:
                    st.warning(f"워드클라우드 생성 중 오류: {e}")
                
                # 키워드 테이블
                keyword_df = pd.DataFrame(common_words, columns=["키워드", "빈도"])
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.dataframe(keyword_df.head(15), use_container_width=True)
                with col2:
                    st.dataframe(keyword_df.tail(15), use_container_width=True)
            else:
                st.info("추출된 키워드가 없습니다.")
        
        # ----------------------------
        # 탭 3: 연관어 분석
        # ----------------------------
        with tab3:
            st.subheader("🔗 주요 키워드 연관 단어")
            
            co_occurrence = {}
            for text in df["content"]:
                tokens = simple_tokenizer(text)
                for i in range(len(tokens) - 1):
                    a, b = tokens[i], tokens[i + 1]
                    if a != b:
                        co_occurrence.setdefault(a, []).append(b)
            
            related_words = []
            for k, v in counter.most_common(30):
                related = Counter(co_occurrence.get(k, [])).most_common(5)
                related_words.append({
                    "키워드": k,
                    "빈도": v,
                    "연관단어": ", ".join([f"{r[0]}({r[1]})" for r in related]) if related else "-"
                })
            
            related_df = pd.DataFrame(related_words)
            st.dataframe(related_df, use_container_width=True)
        
        # ----------------------------
        # 탭 4: 리뷰 원문
        # ----------------------------
        with tab4:
            st.subheader("📝 최신 리뷰 원문")
            
            # 필터링 옵션
            col1, col2 = st.columns(2)
            with col1:
                score_filter = st.multiselect(
                    "평점 필터",
                    options=[1, 2, 3, 4, 5],
                    default=[1, 2, 3, 4, 5]
                )
            with col2:
                search_keyword = st.text_input("키워드 검색", "")
            
            filtered_df = df[df["score"].isin(score_filter)]
            
            if search_keyword:
                filtered_df = filtered_df[
                    filtered_df["content"].str.contains(search_keyword, case=False, na=False)
                ]
            
            st.write(f"**{len(filtered_df):,}건**의 리뷰가 검색되었습니다.")
            
            # 페이지네이션
            page_size = 20
            total_pages = (len(filtered_df) - 1) // page_size + 1
            page = st.number_input("페이지", min_value=1, max_value=max(1, total_pages), value=1)
            
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            for _, row in filtered_df.iloc[start_idx:end_idx].iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        st.write(f"⭐ **{row['score']}점**")
                        st.caption(str(row['at'].date()))
                    with col2:
                        st.write(row["content"])
                    st.markdown("---")

else:
    # 초기 화면
    st.info("👈 왼쪽 사이드바에서 **분석 시작** 버튼을 클릭하세요!")
    
    st.markdown("""
    ### 🎯 이 대시보드로 할 수 있는 것
    
    - **실시간 리뷰 수집**: Google Play Store에서 최신 리뷰를 수집합니다
    - **키워드 분석**: 리뷰에서 자주 등장하는 키워드를 추출합니다
    - **연관어 분석**: 키워드 간의 관계를 분석합니다
    - **트렌드 파악**: 날짜별 리뷰 추이와 평점 분포를 확인합니다
    
    ### 🚀 시작하기
    
    1. 사이드바에서 앱 ID를 입력하세요 (기본: 네이버 웹툰)
    2. 수집할 리뷰 수를 선택하세요
    3. **분석 시작** 버튼을 클릭하세요!
    """)

# ----------------------------
# 푸터
# ----------------------------
st.markdown("---")
st.caption("Made with ❤️ using Streamlit | 데이터 출처: Google Play Store")
