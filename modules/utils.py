"""
공통 유틸리티 함수 모듈
"""

import csv
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

from config import API_BASE_URL, CSV_ENCODING, ERROR_MESSAGES

# 로깅 설정
logger = logging.getLogger(__name__)


def save_to_csv(data: List[Dict], filename: str) -> str:
    """
    데이터를 CSV 파일로 저장

    Args:
        data: 저장할 데이터 리스트
        filename: 저장할 파일명

    Returns:
        저장된 파일 경로
    """
    try:
        # 파일명 정리
        if not filename.endswith(".csv"):
            filename += ".csv"

        # 데이터프레임 생성
        df = pd.DataFrame(data)

        # 컬럼 순서 정리
        columns = [
            "prompt",
            "video_url",
            "status",
            "created_at",
            "completed_at",
            "error_message",
        ]
        existing_columns = [col for col in columns if col in df.columns]
        df = df[existing_columns]

        # CSV 저장 (한글 지원을 위한 BOM 포함)
        df.to_csv(filename, index=False, encoding=CSV_ENCODING)

        logger.info(f"CSV 파일 저장 완료: {filename}")
        return filename

    except Exception as e:
        logger.error(f"CSV 저장 실패: {str(e)}")
        raise Exception(f"CSV 파일 저장에 실패했습니다: {str(e)}")


def calculate_progress(completed: int, total: int) -> float:
    """
    진행률 계산

    Args:
        completed: 완료된 작업 수
        total: 전체 작업 수

    Returns:
        진행률 (0.0 ~ 1.0)
    """
    if total == 0:
        return 0.0
    return min(completed / total, 1.0)


def format_time_remaining(seconds: float) -> str:
    """
    남은 시간을 읽기 쉬운 형식으로 변환

    Args:
        seconds: 남은 시간 (초)

    Returns:
        포맷된 시간 문자열
    """
    if seconds <= 0:
        return "완료"

    # timedelta 객체 생성
    td = timedelta(seconds=int(seconds))

    # 시간 단위별로 분해
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # 포맷팅
    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0:
        parts.append(f"{minutes}분")
    if seconds > 0 or not parts:  # 초만 있거나 아무것도 없을 때
        parts.append(f"{seconds}초")

    return " ".join(parts)


def validate_api_key(api_key: str) -> Dict[str, bool]:
    """
    API 키 유효성 검증

    Args:
        api_key: API 키

    Returns:
        키의 유효성 결과
    """
    results = {"valid": False, "error": None}

    # API 키 검증
    if not api_key or not api_key.strip():
        results["error"] = "API 키가 비어있습니다."
    else:
        try:
            # API 키 형식 검증 (간단한 패턴 체크)
            if len(api_key) < 20:
                results["error"] = "API 키 형식이 올바르지 않습니다."
            else:
                # 실제 API 호출로 검증 (상태 확인 엔드포인트 사용)
                headers = {"X-API-Key": api_key}
                # 존재하지 않는 task_id로 호출하여 인증 확인
                response = requests.get(
                    f"{API_BASE_URL}/v3/video/test", headers=headers, timeout=5
                )
                # 401이 아니면 키는 유효함 (404는 정상)
                if response.status_code != 401:
                    results["valid"] = True
                else:
                    results["error"] = "API 키가 유효하지 않습니다."
        except Exception as e:
            # 네트워크 오류 등은 키 유효성과 별개로 처리
            results["valid"] = True  # 키 형식이 맞으면 일단 통과
            logger.warning(f"API 키 검증 중 네트워크 오류: {str(e)}")

    return results


class SessionManager:
    """Streamlit 세션 상태 관리 클래스"""

    @staticmethod
    def init():
        """세션 상태 초기화"""
        if "initialized" not in st.session_state:
            st.session_state.initialized = True
            st.session_state.api_keys = {"openai": "", "kie": ""}
            st.session_state.generation_tasks = []
            st.session_state.generation_results = []
            st.session_state.current_step = "setup"  # setup, generating, completed
            st.session_state.prompts = []
            st.session_state.video_settings = {"aspect_ratio": "16:9", "duration": 5}
            st.session_state.generation_theme = ""
            st.session_state.generation_style = ""
            st.session_state.generation_count = 5

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """세션 상태 값 가져오기"""
        return getattr(st.session_state, key, default)

    @staticmethod
    def set(key: str, value: Any):
        """세션 상태 값 설정"""
        setattr(st.session_state, key, value)

    @staticmethod
    def update(updates: Dict[str, Any]):
        """여러 세션 상태 값 업데이트"""
        for key, value in updates.items():
            setattr(st.session_state, key, value)

    @staticmethod
    def clear_results():
        """생성 결과 초기화"""
        st.session_state.generation_tasks = []
        st.session_state.generation_results = []
        st.session_state.prompts = []

    @staticmethod
    def add_result(result: Dict):
        """생성 결과 추가"""
        if "generation_results" not in st.session_state:
            st.session_state.generation_results = []
        st.session_state.generation_results.append(result)

    @staticmethod
    def get_statistics() -> Dict:
        """현재 생성 통계 가져오기"""
        results = st.session_state.get("generation_results", [])
        if not results:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "success_rate": 0,
            }

        total = len(results)
        completed = sum(1 for r in results if r.get("status") == "completed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        pending = sum(
            1 for r in results if r.get("status") in ["pending", "processing"]
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "success_rate": (completed / total * 100) if total > 0 else 0,
        }

    @staticmethod
    def export_session() -> Dict:
        """세션 데이터 내보내기"""
        return {
            "api_keys": st.session_state.get("api_keys", {}),
            "prompts": st.session_state.get("prompts", []),
            "video_settings": st.session_state.get("video_settings", {}),
            "generation_results": st.session_state.get("generation_results", []),
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def import_session(data: Dict):
        """세션 데이터 가져오기"""
        if "api_keys" in data:
            st.session_state.api_keys = data["api_keys"]
        if "prompts" in data:
            st.session_state.prompts = data["prompts"]
        if "video_settings" in data:
            st.session_state.video_settings = data["video_settings"]
        if "generation_results" in data:
            st.session_state.generation_results = data["generation_results"]
