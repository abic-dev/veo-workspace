"""
프로젝트 설정 관리
"""

import os

from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# API 설정
API_KEY = os.getenv("API_KEY", "")

# API 설정
API_BASE_URL = "https://api.kie.ai"
API_VIDEO_ENDPOINT = "/api/v1/veo/generate"
API_STATUS_ENDPOINT = "/api/v1/veo/record-info"

# 영상 생성 기본 설정
DEFAULT_VIDEO_DURATION = 8  # 기본 8초
DEFAULT_ASPECT_RATIO = "16:9"
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "20"))
VIDEO_MODEL = "veo3_fast"  # veo3 모델 사용

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 2  # 초

# 폴링 설정 (영상 생성 상태 확인)
POLLING_INTERVAL = 5  # 초
MAX_POLLING_TIME = 600  # 최대 10분

# CSV 설정
CSV_ENCODING = "utf-8-sig"  # BOM 포함으로 한글 지원

# UI 텍스트
UI_TEXTS = {
    "app_title": "🎬 AI 영상 생성 도구",
    "app_description": "AI를 활용한 대량 영상 생성 도구",
    "generate_button": "🚀 영상 생성 시작",
    "download_button": "📥 결과 다운로드 (CSV)",
    "progress_title": "진행 상황",
    "results_title": "생성 결과",
}

# 에러 메시지
ERROR_MESSAGES = {
    "missing_api_key": "API 키를 입력해주세요.",
    "invalid_api_key": "유효하지 않은 API 키입니다.",
    "generation_failed": "영상 생성에 실패했습니다.",
    "network_error": "네트워크 오류가 발생했습니다.",
    "timeout_error": "요청 시간이 초과되었습니다.",
}
