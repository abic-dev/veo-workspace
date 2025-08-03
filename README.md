# AI 영상 생성 도구

AI를 활용한 대량 영상 생성 도구입니다.

## 주요 기능

- 📝 **프롬프트 일괄 입력**: 빈 줄로 구분하여 여러 프롬프트를 한 번에 입력
- 🎬 **대량 영상 생성**: 고품질 영상 대량 생성 (Veo3 모델 사용)
  - 최대 20개 영상 동시 처리
  - 비동기 처리로 빠른 생성 속도
- 🎥 **영상 미리보기**: 생성된 영상을 바로 재생하여 확인 가능
- 📊 **실시간 진행 상황**: 각 영상 생성 상태를 실시간으로 모니터링
  - 전체 진행률 표시 (완료/진행중/실패)
  - 개별 작업 경과 시간 표시
  - 예상 남은 시간 계산
  - 5초마다 자동 새로고침
- 🔄 **세션 유지**: 브라우저를 닫았다 열어도 진행 상황 확인 가능
- ✅ **선택적 다운로드**: 생성된 영상 중 필요한 것만 선택하여 다운로드
- 💾 **CSV 내보내기**: 프롬프트, 영상 URL, 선택 여부를 CSV로 저장
- 🎨 **사용자 친화적 UI**: 개발 지식 없이도 쉽게 사용 가능한 Streamlit 웹 인터페이스

## 설치 방법

### 1. 필수 요구사항

- Python 3.8 이상
- KIE.AI API 키 (Bearer Token)

### 2. 프로젝트 클론

```bash
git clone <repository-url>
cd veo-workspace
```

### 3. 환경 설정 (uv 사용 - 권장)

#### uv를 사용하는 경우 (빠른 설치)

```bash
# uv 설치 (아직 설치하지 않은 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 가상환경 생성 및 패키지 설치
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

#### 기존 pip를 사용하는 경우

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 4. 패키지 설치 완료

### 5. 환경 설정

1. `.env.example` 파일을 `.env`로 복사
2. `.env` 파일에 API 키 입력

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 API 키 입력
```

## 사용 방법

### 1. 애플리케이션 실행

#### 간편 실행 (권장)

```bash
./run.sh
```

#### 수동 실행

```bash
source .venv/bin/activate  # 가상환경 활성화
streamlit run app.py
```

### 2. API 키 설정

`.env` 파일을 열어 KIE.AI Bearer Token을 설정하세요:

```
API_KEY=your_bearer_token_here

# 선택적 설정 (기본값: 20)
MAX_CONCURRENT_REQUESTS=20  # 최대 동시 처리 영상 수 (1-20)
```

### 3. 웹 브라우저에서 사용

1. **프롬프트 입력**:

   - 텍스트 영역에 프롬프트 입력
   - 각 프롬프트는 빈 줄(엔터 두 번)로 구분
   - 하나의 프롬프트는 여러 줄로 작성 가능
   - 예시:

     ```
     첫 번째 프롬프트입니다
     여러 줄로 작성 가능합니다

     두 번째 프롬프트입니다
     이것도 여러 줄 가능합니다
     ```

2. **생성 시작**: "🚀 영상 생성 시작" 버튼 클릭
3. **진행 상황 확인**: 실시간으로 각 영상의 생성 상태 확인
4. **영상 확인**: 생성된 영상을 미리보기로 재생하고 필요한 것만 체크박스로 선택
5. **결과 다운로드**: 전체 결과를 CSV 파일로 다운로드 (프롬프트, 영상 URL, 상태, 선택 여부 포함)

## 프로젝트 구조

```
veo-workspace/
├── app.py                 # Streamlit 메인 애플리케이션
├── modules/
│   ├── __init__.py
│   ├── prompt_generator.py  # ChatGPT 프롬프트 생성 모듈
│   ├── video_generator.py   # KIE.AI 영상 생성 모듈
│   └── utils.py            # 공통 유틸리티 함수
├── requirements.txt        # 의존성 패키지 목록
├── .env.example           # 환경변수 예시 파일
├── .env                   # 실제 환경변수 파일 (gitignore)
├── README.md              # 프로젝트 문서
└── config.py              # 설정 관리

```

## 프롬프트 예시

`example_prompts.txt` 파일에 샘플 프롬프트가 포함되어 있습니다. 이 파일의 내용을 복사하여 사용하거나 참고하실 수 있습니다.

## 주의사항

- API 사용량에 따라 비용이 발생할 수 있습니다
- 대량 생성 시 API rate limit에 주의하세요
- 생성된 영상은 일정 시간 후 삭제될 수 있으니 즉시 다운로드하세요
- Veo3 모델은 기본적으로 8초 길이의 영상을 생성합니다

## 문제 해결

### 일반적인 문제들

1. **ModuleNotFoundError**: `pip install -r requirements.txt` 재실행
2. **API 키 오류**: `.env` 파일의 API 키가 올바른지 확인
3. **연결 오류**: 인터넷 연결 상태 확인

## 라이센스

MIT License
