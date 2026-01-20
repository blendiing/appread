import streamlit as st
from google_play_scraper import reviews, Sort
import pandas as pd
from collections import Counter
from wordcloud import WordCloud
import re
import os
from io import BytesIO

# ----------------------------
# Page Config
# ----------------------------
st.set_page_config(
    page_title="App Review Analysis",
    page_icon="📊",
    layout="wide"
)

# ----------------------------
# Responsive CSS
# ----------------------------
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 14px; }
h1 { font-size: 1.6rem !important; }
h2 { font-size: 1.3rem !important; }
h3, .stSubheader { font-size: 1.1rem !important; }
h4 { font-size: 1rem !important; }
[data-testid="stSidebar"] { min-width: 280px; max-width: 320px; }
[data-testid="stSidebar"] .stMarkdown { font-size: 13px; }
[data-testid="stSidebar"] code { font-size: 11px; padding: 4px 8px; }
[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
.stTabs [data-baseweb="tab-list"] button { font-size: 13px; padding: 8px 12px; }
.stDataFrame { font-size: 12px; }
@media (max-width: 768px) {
    html, body, [class*="css"] { font-size: 12px; }
    h1 { font-size: 1.4rem !important; }
}
/* Streamlit Cloud header spacing */
.block-container { padding-top: 2.5rem; padding-bottom: 1rem; }
.main .block-container { padding-top: 3rem; }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# Font Path
# ----------------------------
def get_font_path():
    possible_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

FONT_PATH = get_font_path()

# ----------------------------
# Stopwords (English)
# ----------------------------
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "this",
    "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
    "my", "your", "his", "her", "its", "our", "their", "me", "him", "us",
    "them", "what", "which", "who", "whom", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "also", "now", "app", "apps", "really", "very", "much",
    "get", "got", "like", "dont", "don't", "doesn't", "didnt", "didn't"
}

# ----------------------------
# Topic Keywords (English)
# ----------------------------
TOPIC_KEYWORDS = {
    "💰 Payment/Price": ["payment", "pay", "price", "cost", "expensive", "cheap", "free", "premium", "subscription", "purchase", "refund", "money", "coin", "credit"],
    "📱 UI/UX": ["screen", "button", "design", "interface", "menu", "layout", "icon", "font", "scroll", "touch", "ui", "ux", "navigation"],
    "🐛 Bug/Error": ["bug", "error", "crash", "freeze", "stuck", "slow", "loading", "lag", "glitch", "fix", "issue", "problem", "broken"],
    "📺 Ads": ["ad", "ads", "advertisement", "banner", "popup", "skip", "commercial", "advertising"],
    "📚 Content": ["story", "content", "chapter", "episode", "character", "plot", "quality", "update", "new", "series", "author", "writer", "art", "artwork"],
    "🔔 Features": ["notification", "bookmark", "save", "download", "search", "filter", "share", "offline", "feature", "option", "setting"],
}

# ----------------------------
# Sentiment Keywords (English)
# ----------------------------
POSITIVE_WORDS = {"love", "great", "amazing", "awesome", "excellent", "fantastic", "wonderful", "perfect", "best", "good", "nice", "enjoy", "fun", "recommend", "favorite"}
NEGATIVE_WORDS = {"hate", "bad", "terrible", "awful", "horrible", "worst", "disappointing", "annoying", "frustrating", "boring", "waste", "useless", "poor", "garbage", "trash"}

# ----------------------------
# Webtoon/Comic Sentiment (English)
# ----------------------------
WEBTOON_SENTIMENT_EN = {
    "positive": {
        "love": 2, "great": 2, "amazing": 3, "awesome": 3, "excellent": 3,
        "fantastic": 3, "wonderful": 3, "perfect": 3, "best": 3, "good": 1,
        "nice": 1, "enjoy": 2, "fun": 2, "recommend": 2, "favorite": 2,
        # Comic/Webtoon specific
        "masterpiece": 3, "addictive": 3, "bingeworthy": 3, "binge": 2,
        "artwork": 2, "art style": 2, "beautiful art": 3, "stunning": 3,
        "well written": 3, "engaging": 2, "captivating": 3, "immersive": 3,
        "plot twist": 2, "character development": 3, "emotional": 2,
        "cant stop": 3, "hooked": 3, "addicted": 3,
    },
    "negative": {
        "hate": 2, "bad": 1, "terrible": 3, "awful": 3, "horrible": 3,
        "worst": 3, "disappointing": 2, "annoying": 2, "frustrating": 2,
        "boring": 2, "waste": 3, "useless": 2, "poor": 1, "garbage": 3, "trash": 3,
        # Comic/Webtoon specific
        "dropped": 3, "dropped it": 3, "gave up": 3, "unreadable": 3,
        "bad art": 3, "ugly art": 3, "poor writing": 3, "plot holes": 3,
        "inconsistent": 2, "rushed": 2, "slow pacing": 2, "filler": 2,
        "predictable": 2, "cliche": 2, "generic": 2, "overrated": 2,
        "waste of time": 3, "regret": 2,
    }
}

# ----------------------------
# Utility Functions
# ----------------------------
def simple_tokenizer(text):
    tokens = re.findall(r"[a-zA-Z]{3,}", str(text).lower())
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) >= 3]
    return tokens

def extract_bigrams(text):
    tokens = simple_tokenizer(text)
    bigrams = []
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} + {tokens[i+1]}"
        bigrams.append(bigram)
    return bigrams

def extract_trigrams(text):
    tokens = simple_tokenizer(text)
    trigrams = []
    for i in range(len(tokens) - 2):
        trigram = f"{tokens[i]} + {tokens[i+1]} + {tokens[i+2]}"
        trigrams.append(trigram)
    return trigrams

@st.cache_data(ttl=7200, show_spinner=False)
def get_reviews_cached(app_id, count=1000, lang="en", country="us"):
    result = []
    continuation_token = None
    
    try:
        while len(result) < count:
            batch_size = min(100, count - len(result))
            review_batch, continuation_token = reviews(
                app_id, lang=lang, country=country,
                sort=Sort.NEWEST, count=batch_size,
                continuation_token=continuation_token
            )
            result.extend(review_batch)
            if not continuation_token:
                break
    except Exception as e:
        st.error(f"Error collecting reviews: {e}")
        return pd.DataFrame()
    
    df = pd.DataFrame(result)
    if not df.empty:
        df["at"] = pd.to_datetime(df["at"])
        df["content"] = df["content"].astype(str)
    return df

# ----------------------------
# Analysis Functions
# ----------------------------
def analyze_sentiment_basic(df):
    results = []
    for _, row in df.iterrows():
        text = str(row["content"]).lower()
        score = row["score"]
        
        pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)
        
        if score >= 4:
            sentiment = "Positive"
        elif score <= 2:
            sentiment = "Negative"
        else:
            if pos_count > neg_count:
                sentiment = "Positive"
            elif neg_count > pos_count:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
        
        results.append(sentiment)
    
    df = df.copy()
    df["sentiment"] = results
    df["pos_score"] = 0
    df["neg_score"] = 0
    return df

def analyze_sentiment_webtoon(df):
    results = []
    pos_scores = []
    neg_scores = []
    
    for _, row in df.iterrows():
        text = str(row["content"]).lower()
        score = row["score"]
        
        pos_weight = sum(weight for word, weight in WEBTOON_SENTIMENT_EN["positive"].items() if word in text)
        neg_weight = sum(weight for word, weight in WEBTOON_SENTIMENT_EN["negative"].items() if word in text)
        
        pos_scores.append(pos_weight)
        neg_scores.append(neg_weight)
        
        if score >= 4:
            if neg_weight >= 6:
                sentiment = "Negative" if neg_weight > pos_weight else "Positive"
            else:
                sentiment = "Positive"
        elif score <= 2:
            if pos_weight >= 6:
                sentiment = "Positive" if pos_weight > neg_weight else "Negative"
            else:
                sentiment = "Negative"
        else:
            diff = pos_weight - neg_weight
            if diff >= 2:
                sentiment = "Positive"
            elif diff <= -2:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
        
        results.append(sentiment)
    
    df = df.copy()
    df["sentiment"] = results
    df["pos_score"] = pos_scores
    df["neg_score"] = neg_scores
    return df

def analyze_topics(contents_tuple):
    topic_priority = list(TOPIC_KEYWORDS.keys())
    topic_data = {topic: [] for topic in topic_priority}
    request_patterns = ["please", "wish", "hope", "want", "need", "should", "would be nice"]
    
    for text in contents_tuple:
        text_lower = str(text).lower()
        is_request = any(p in text_lower for p in request_patterns)
        
        for topic in topic_priority:
            keywords = TOPIC_KEYWORDS[topic]
            if topic == "🐛 Bug/Error" and is_request:
                continue
            if any(kw in text_lower for kw in keywords):
                topic_data[topic].append(text)
    
    return topic_data

def analyze_complaints_trigram(df):
    negative_df = df[df["score"] <= 2]
    if negative_df.empty:
        return [], [], pd.DataFrame()
    
    bigrams = []
    trigrams = []
    for text in negative_df["content"]:
        bigrams += extract_bigrams(text)
        trigrams += extract_trigrams(text)
    
    return Counter(bigrams).most_common(30), Counter(trigrams).most_common(30), negative_df

def analyze_positive_bigram(df):
    positive_df = df[df["score"] >= 4]
    if positive_df.empty:
        return [], pd.DataFrame()
    
    bigrams = []
    for text in positive_df["content"]:
        bigrams += extract_bigrams(text)
    
    return Counter(bigrams).most_common(30), positive_df

def extract_requests(contents_tuple):
    requests = []
    patterns = [
        r"(please .{5,30})",
        r"(wish .{5,30})",
        r"(would be nice .{5,30})",
        r"(should .{5,30})",
        r"(need .{5,30})",
        r"(want .{5,30})",
    ]
    
    for text in contents_tuple:
        text_lower = str(text).lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if len(match) > 10:
                    requests.append(match.strip())
    
    return Counter(requests).most_common(30)

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

def extract_keywords_cached(contents_tuple):
    tokens = []
    for text in contents_tuple:
        tokens += simple_tokenizer(text)
    return tokens

# ----------------------------
# Main Analysis Display
# ----------------------------
def display_analysis(df, app_name=""):
    if df.empty:
        st.error("❌ No data available.")
        return
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ **{len(df):,}** reviews analyzed! {f'({app_name})' if app_name else ''}")
    with col2:
        webtoon_mode = st.toggle("🎨 Comic Mode", value=True, help="Use comic/webtoon specific sentiment keywords")
    
    if webtoon_mode:
        df = analyze_sentiment_webtoon(df)
    else:
        df = analyze_sentiment_basic(df)
    
    contents_tuple = tuple(df["content"].tolist())
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Stats", "😊 Sentiment", "📂 Topics", "🔎 Keywords", "🙏 Requests"
    ])
    
    # Tab 1: Stats
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Reviews", f"{len(df):,}")
        with col2:
            st.metric("Avg Rating", f"{df['score'].mean():.1f}⭐")
        with col3:
            pos_ratio = (df["sentiment"] == "Positive").sum() / len(df) * 100
            st.metric("Positive", f"{pos_ratio:.0f}%")
        with col4:
            neg_ratio = (df["sentiment"] == "Negative").sum() / len(df) * 100
            st.metric("Negative", f"{neg_ratio:.0f}%")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🗓️ Reviews by Date")
            daily = df.groupby(df["at"].dt.date).size()
            st.line_chart(daily)
        with col2:
            st.markdown("#### ⭐ Rating Distribution")
            scores = df["score"].value_counts().sort_index()
            st.bar_chart(scores)
    
    # Tab 2: Sentiment
    with tab2:
        st.markdown("### 😊 Sentiment Analysis")
        
        if webtoon_mode:
            with st.expander("🎨 Comic Sentiment Keywords", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**😊 Positive**")
                    st.caption(", ".join(list(WEBTOON_SENTIMENT_EN["positive"].keys())[:12]) + "...")
                with col2:
                    st.markdown("**😤 Negative**")
                    st.caption(", ".join(list(WEBTOON_SENTIMENT_EN["negative"].keys())[:12]) + "...")
        
        col1, col2 = st.columns(2)
        with col1:
            sentiment_counts = df["sentiment"].value_counts()
            for sentiment, count in sentiment_counts.items():
                pct = count / len(df) * 100
                if sentiment == "Positive":
                    st.success(f"😊 Positive: **{count:,}** ({pct:.1f}%)")
                elif sentiment == "Negative":
                    st.error(f"😤 Negative: **{count:,}** ({pct:.1f}%)")
                else:
                    st.warning(f"😐 Neutral: **{count:,}** ({pct:.1f}%)")
        
        with col2:
            sentiment_by_score = df.groupby(["score", "sentiment"]).size().unstack(fill_value=0)
            st.dataframe(sentiment_by_score, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 😤 Complaint Analysis (1-2 stars)")
        
        neg_bigrams, neg_trigrams, neg_df = analyze_complaints_trigram(df)
        st.markdown(f"🔴 Complaints: **{len(neg_df):,}** ({len(neg_df)/len(df)*100:.1f}%)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 2-word combos")
            if neg_bigrams:
                st.dataframe(pd.DataFrame(neg_bigrams[:15], columns=["Combo", "Count"]), use_container_width=True, hide_index=True)
        with col2:
            st.markdown("#### 3-word combos")
            if neg_trigrams:
                st.dataframe(pd.DataFrame(neg_trigrams[:15], columns=["Combo", "Count"]), use_container_width=True, hide_index=True)
        
        with st.expander(f"📋 Complaint Reviews ({len(neg_df):,})", expanded=False):
            if not neg_df.empty:
                display_neg = neg_df[["at", "score", "content"]].copy()
                display_neg["at"] = display_neg["at"].dt.strftime("%Y-%m-%d")
                display_neg.columns = ["Date", "Rating", "Content"]
                st.dataframe(display_neg, use_container_width=True, hide_index=True, height=300)
    
    # Tab 3: Topics
    with tab3:
        st.markdown("### 📂 Topic Classification")
        
        topic_data = analyze_topics(contents_tuple)
        sorted_topics = sorted(topic_data.items(), key=lambda x: len(x[1]), reverse=True)
        
        summary_data = []
        for topic, reviews_list in sorted_topics:
            summary_data.append({"Topic": topic, "Count": len(reviews_list), "Ratio": f"{len(reviews_list)/len(df)*100:.1f}%"})
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        for topic, reviews_list in sorted_topics:
            with st.expander(f"{topic} ({len(reviews_list):,})", expanded=False):
                if reviews_list:
                    keywords = TOPIC_KEYWORDS[topic]
                    st.caption(f"🔑 Keywords: {', '.join(keywords[:8])}")
                    for i, review in enumerate(reviews_list[:5], 1):
                        truncated = review[:120] + "..." if len(review) > 120 else review
                        st.text(f"{i}. {truncated}")
    
    # Tab 4: Keywords
    with tab4:
        st.markdown("### 🔎 Keyword Analysis")
        
        tokens = extract_keywords_cached(contents_tuple)
        counter = Counter(tokens)
        common_words = counter.most_common(30)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if common_words:
                img_bytes = generate_wordcloud_image(tuple(common_words), FONT_PATH)
                if img_bytes:
                    st.image(img_bytes, use_container_width=True)
        with col2:
            st.markdown("#### TOP 15")
            if common_words:
                st.dataframe(pd.DataFrame(common_words[:15], columns=["Keyword", "Count"]), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🔍 Deep Keyword Analysis")
        
        deep_keyword = st.text_input("Enter keyword", placeholder="e.g., ads, crash, story", key="deep_kw_en")
        
        if deep_keyword:
            keyword_df = df[df["content"].str.contains(deep_keyword, na=False, case=False)].copy()
            
            if keyword_df.empty:
                st.warning(f"No reviews containing '{deep_keyword}'")
            else:
                st.success(f"**'{deep_keyword}'**: **{len(keyword_df):,}** reviews ({len(keyword_df)/len(df)*100:.1f}%)")
                
                col1, col2, col3, col4 = st.columns(4)
                pos_cnt = (keyword_df["sentiment"] == "Positive").sum()
                neg_cnt = (keyword_df["sentiment"] == "Negative").sum()
                
                with col1:
                    st.metric("Reviews", f"{len(keyword_df):,}")
                with col2:
                    st.metric("Avg Rating", f"{keyword_df['score'].mean():.1f}⭐")
                with col3:
                    st.metric("Positive", f"{pos_cnt/len(keyword_df)*100:.0f}%")
                with col4:
                    st.metric("Negative", f"{neg_cnt/len(keyword_df)*100:.0f}%")
    
    # Tab 5: Requests
    with tab5:
        st.markdown("### 🙏 User Requests")
        
        requests = extract_requests(contents_tuple)
        
        if requests:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Top Requests")
                st.dataframe(pd.DataFrame(requests[:15], columns=["Request", "Count"]), use_container_width=True, hide_index=True)
            with col2:
                st.markdown("#### Frequency")
                st.bar_chart(pd.DataFrame(requests[:8], columns=["Request", "Count"]).set_index("Request"))
        else:
            st.info("No requests found")
        
        st.markdown("---")
        st.markdown("### 📝 All Reviews")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            score_filter = st.multiselect("Rating", [1,2,3,4,5], default=[1,2,3,4,5], key="review_score_en")
        with col2:
            sentiment_filter = st.multiselect("Sentiment", ["Positive", "Neutral", "Negative"], default=["Positive", "Neutral", "Negative"], key="review_sent_en")
        with col3:
            keyword = st.text_input("Search", key="review_search_en")
        
        filtered = df[df["score"].isin(score_filter) & df["sentiment"].isin(sentiment_filter)]
        if keyword:
            filtered = filtered[filtered["content"].str.contains(keyword, na=False, case=False)]
        
        st.write(f"**{len(filtered):,}** reviews")
        
        display_df = filtered[["at", "score", "sentiment", "content"]].copy()
        display_df["at"] = display_df["at"].dt.strftime("%Y-%m-%d")
        display_df.columns = ["Date", "Rating", "Sentiment", "Content"]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

# ----------------------------
# Main UI
# ----------------------------
st.title("📊 App Review Analysis (English)")

# Sidebar
with st.sidebar:
    st.markdown("#### 🔍 App ID")
    app_id_input = st.text_input(
        "App ID",
        placeholder="com.example.app",
        label_visibility="collapsed",
        key="app_id_en"
    )
    
    with st.expander("📋 Sample App IDs", expanded=False):
        st.code("com.webtoons.webcomics")
        st.caption("WEBTOON")
        st.code("com.tapas.tapastic")
        st.caption("Tapas")
        st.code("com.naver.linewebtoon")
        st.caption("LINE Webtoon")
        st.code("com.toomics.global.google")
        st.caption("Toomics")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        lang = st.selectbox("Language", ["en", "es", "fr", "de", "pt", "ja"], index=0)
    with col2:
        country = st.selectbox("Country", ["us", "gb", "ca", "au", "jp"], index=0)
    
    review_count = st.select_slider(
        "📊 Reviews to collect",
        options=[100, 300, 500, 700, 1000],
        value=500,
        key="review_count_en"
    )
    
    collect_btn = st.button(
        "🚀 Collect Data", 
        type="primary", 
        use_container_width=True,
        disabled=(not app_id_input),
        key="collect_en"
    )
    
    if not app_id_input:
        st.caption("💡 Enter App ID to enable")

# Main Content
if collect_btn and app_id_input:
    with st.spinner(f"📥 Collecting {app_id_input} reviews... ({review_count})"):
        df = get_reviews_cached(app_id_input, count=review_count, lang=lang, country=country)
        df = df.sort_values(by="at", ascending=False)
        st.session_state["collected_df_en"] = df
        st.session_state["collected_app_en"] = app_id_input

if st.session_state.get("collected_df_en") is not None and not st.session_state["collected_df_en"].empty:
    display_analysis(st.session_state["collected_df_en"], st.session_state.get("collected_app_en", ""))
else:
    st.info("👈 Enter an App ID and click **Collect Data** to start analysis")
    
    st.markdown("""
    ### 🎯 Features
    | Tab | Description |
    |-----|-------------|
    | 📈 Stats | Rating distribution, daily trends |
    | 😊 Sentiment | Positive/Negative analysis with comic-specific keywords |
    | 📂 Topics | Payment, Ads, Bugs, Content classification |
    | 🔎 Keywords | Word cloud + deep keyword analysis |
    | 🙏 Requests | User request extraction |
    """)

st.markdown("---")
st.caption("Made with ❤️ using Streamlit | Data: Google Play Store")
