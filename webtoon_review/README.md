# 📊 네이버 웹툰 앱 리뷰 분석 대시보드

Google Play Store 리뷰를 실시간으로 수집하고 분석하는 Streamlit 대시보드입니다.

## ✨ 주요 기능

- 📥 **실시간 리뷰 수집**: Google Play Store에서 최신 리뷰 수집
- 💬 **키워드 분석**: 자주 등장하는 키워드 추출 및 워드클라우드 시각화
- 🔗 **연관어 분석**: 키워드 간의 관계 분석
- 📈 **통계 대시보드**: 날짜별 추이, 평점 분포 등

## 🚀 Streamlit Community Cloud 배포 가이드

### 1단계: GitHub 저장소 생성

1. [GitHub](https://github.com)에 로그인
2. 우측 상단 `+` → `New repository` 클릭
3. 저장소 이름 입력 (예: `webtoon-review-analysis`)
4. `Public` 선택 후 `Create repository` 클릭

### 2단계: 파일 업로드

저장소에 다음 파일들을 업로드하세요:

```
webtoon-review-analysis/
├── app.py                    # 메인 앱 파일
├── requirements.txt          # 패키지 의존성
├── .streamlit/
│   └── config.toml          # Streamlit 설정
└── README.md                 # 이 파일
```

**GitHub에서 파일 업로드 방법:**
1. `Add file` → `Upload files` 클릭
2. 파일들을 드래그 앤 드롭
3. `Commit changes` 클릭

**폴더 생성 방법 (.streamlit 폴더):**
1. `Add file` → `Create new file` 클릭
2. 파일명에 `.streamlit/config.toml` 입력
3. 내용 붙여넣기 후 `Commit new file` 클릭

### 3단계: Streamlit Community Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io) 접속
2. GitHub 계정으로 로그인
3. `New app` 클릭
4. 설정:
   - **Repository**: 방금 만든 저장소 선택
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. `Deploy!` 클릭

### 4단계: 배포 완료! 🎉

- 약 2-3분 후 앱이 실행됩니다
- URL 형식: `https://[your-app-name].streamlit.app`
- 이 URL을 공유하면 누구나 접속할 수 있습니다

## 🔧 커스터마이징

### 다른 앱 분석하기

사이드바에서 앱 ID를 변경하면 다른 앱의 리뷰도 분석할 수 있습니다.

**앱 ID 찾는 방법:**
1. Google Play Store에서 앱 페이지 열기
2. URL에서 `id=` 뒤의 값이 앱 ID
   - 예: `https://play.google.com/store/apps/details?id=com.nhn.android.webtoon`
   - 앱 ID: `com.nhn.android.webtoon`

### 인기 웹툰 앱 ID 목록

| 앱 이름 | 앱 ID |
|--------|-------|
| 네이버 웹툰 | `com.nhn.android.webtoon` |
| 카카오페이지 | `com.kakaopage.app` |
| 레진코믹스 | `com.lezhin.comics` |
| 탑툰 | `com.toptoon.app` |
| 봄툰 | `com.bomtoon.app` |

## 📝 주의사항

- 리뷰 수집에는 시간이 걸릴 수 있습니다 (최대 1-2분)
- 데이터는 1시간 동안 캐싱되어 빠르게 로드됩니다
- 무료 Streamlit Cloud는 일정 시간 미사용 시 슬립 모드로 전환됩니다

## 🛠️ 로컬 실행 방법

```bash
# 저장소 클론
git clone https://github.com/[your-username]/webtoon-review-analysis.git
cd webtoon-review-analysis

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 실행
streamlit run app.py
```

## 📄 라이선스

MIT License

---

Made with ❤️ using Streamlit
