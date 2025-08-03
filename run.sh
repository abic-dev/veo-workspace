#!/bin/bash

# uv 환경에서 Streamlit 앱 실행 스크립트

# 가상환경 활성화
source .venv/bin/activate

# 환경변수 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 복사하여 생성합니다..."
    cp .env.example .env
    echo "✅ .env 파일이 생성되었습니다. API 키를 입력해주세요."
    echo ""
fi

# Streamlit 앱 실행
echo "🎬 AI 영상 생성 도구를 시작합니다..."
echo ""
streamlit run app.py