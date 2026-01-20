"""
기존 default_reviews.csv에 sentiment, pos_score, neg_score 컬럼 추가
GitHub에서 기존 CSV 다운로드 후 이 스크립트 실행
"""
import pandas as pd

# 웹툰 특화 감성 키워드
WEBTOON_SENTIMENT = {
    "positive": {
        "좋다": 1, "좋아": 1, "좋아요": 1, "좋습니다": 1, "좋네": 1,
        "재밌다": 2, "재밌어": 2, "재밌어요": 2, "재미있": 2, "재미있어요": 2,
        "강추": 3, "최고": 3, "최고예요": 3, "최고입니다": 3, "최고다": 3,
        "작화좋": 2, "작화최고": 3, "그림좋": 2, "그림최고": 3,
        "스토리좋": 2, "스토리탄탄": 3, "내용좋": 2, "전개좋": 2,
        "정주행": 2, "몰입": 2, "빠져들": 2, "시간순삭": 3, "시간가는줄": 3,
        "갓작": 3, "명작": 3, "레전드": 3, "인생웹툰": 3, "인생작": 3,
        "완벽": 3, "대박": 2, "짱": 2, "존잼": 3, "꿀잼": 3, "핵꿀잼": 3,
        "기대": 1, "응원": 1, "감사": 1, "고마워": 1, "추천": 2,
    },
    "negative": {
        "별로": 1, "별로예요": 1, "별로다": 1, "별로야": 1,
        "노잼": 3, "재미없": 2, "재미없어": 2, "지루": 2, "지루해": 2,
        "최악": 3, "최악이다": 3, "최악입니다": 3, "쓰레기": 3,
        "작화붕괴": 3, "작화별로": 2, "그림별로": 2, "작화구림": 2,
        "캐붕": 3, "캐릭터붕괴": 3, "스토리별로": 2, "내용별로": 2,
        "급전개": 2, "전개별로": 2, "떡밥방치": 3, "결말별로": 2,
        "하차": 3, "안봄": 2, "삭제": 2, "접음": 2, "그만": 1,
        "시간낭비": 3, "시간아까": 2, "돈아까": 2, "후회": 2,
        "발암": 3, "답답": 2, "짜증": 2, "화남": 2, "실망": 2,
        "광고": 1, "광고많": 2, "광고도배": 3, "버그": 2, "오류": 2,
    }
}

def analyze_csv(input_path, output_path):
    df = pd.read_csv(input_path)
    
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
    
    df.to_csv(output_path, index=False)
    print(f"완료! {output_path} 저장됨")
    print(f"감성 분포: {df['sentiment'].value_counts().to_dict()}")

if __name__ == "__main__":
    analyze_csv("default_reviews.csv", "default_reviews_analyzed.csv")
