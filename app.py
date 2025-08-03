"""
AI 영상 생성 도구 - Streamlit 애플리케이션
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from config import (
    API_KEY,
    DEFAULT_ASPECT_RATIO,
    DEFAULT_VIDEO_DURATION,
    ERROR_MESSAGES,
    UI_TEXTS,
    VIDEO_MODEL,
)
from modules import (
    SessionManager,
    VideoGenerator,
    VideoSettings,
    calculate_progress,
    format_time_remaining,
    save_to_csv,
)

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="🎬 AI 영상 생성 도구",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 세션 파일 경로
SESSION_FILE = "session_data.json"


def init_session():
    """세션 초기화 및 복원"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # 세션 데이터 복원
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                if saved_data.get("session_id") == st.session_state.session_id:
                    # 같은 세션이면 데이터 복원
                    for key, value in saved_data.items():
                        st.session_state[key] = value
        except Exception as e:
            logger.error(f"세션 복원 실패: {e}")

    # 기본값 설정
    if "prompts" not in st.session_state:
        st.session_state.prompts = []
    if "generation_tasks" not in st.session_state:
        st.session_state.generation_tasks = []
    if "generation_results" not in st.session_state:
        st.session_state.generation_results = []
    if "video_settings" not in st.session_state:
        st.session_state.video_settings = {"aspect_ratio": "16:9", "duration": 5}
    if "selected_videos" not in st.session_state:
        st.session_state.selected_videos = {}


def save_session():
    """세션 데이터 저장"""
    try:
        session_data = {
            "session_id": st.session_state.session_id,
            "prompts": st.session_state.prompts,
            "generation_tasks": st.session_state.generation_tasks,
            "generation_results": st.session_state.generation_results,
            "video_settings": st.session_state.video_settings,
            "selected_videos": st.session_state.selected_videos,
            "timestamp": datetime.now().isoformat(),
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"세션 저장 실패: {e}")


def render_header():
    """헤더 렌더링"""
    st.title(UI_TEXTS["app_title"])
    st.markdown(UI_TEXTS["app_description"])
    st.divider()


def get_api_key():
    """환경 변수에서 API 키 가져오기"""
    api_key = API_KEY
    if not api_key:
        st.error("⚠️ API 키가 설정되지 않았습니다. .env 파일에 API_KEY를 설정해주세요.")
        st.stop()
    return api_key


def render_prompt_input():
    """프롬프트 입력 섹션"""
    st.header("📝 영상 프롬프트 입력")
    st.markdown("각 프롬프트는 **빈 줄(엔터 두 번)**로 구분하여 입력하세요.")

    # 텍스트 영역
    prompt_text = st.text_area(
        "프롬프트 입력",
        height=200,
        placeholder="첫 번째 프롬프트입니다.\n여러 줄로 작성할 수 있습니다.\n\n두 번째 프롬프트입니다.\n이것도 여러 줄 가능합니다.\n\n세 번째 프롬프트...",
        help="빈 줄(엔터 두 번)로 각 프롬프트를 구분하세요.",
    )

    # 프롬프트 파싱 - 빈 줄로 구분
    if prompt_text:
        # 두 개 이상의 연속된 줄바꿈으로 분리
        prompts = [p.strip() for p in re.split(r"\n\s*\n", prompt_text) if p.strip()]
        st.session_state.prompts = prompts

        if prompts:
            st.success(f"✅ {len(prompts)}개의 프롬프트가 입력되었습니다.")
            with st.expander("입력된 프롬프트 확인"):
                for i, prompt in enumerate(prompts, 1):
                    st.markdown(f"**{i}번째 프롬프트:**")
                    st.text(prompt)
                    st.divider()

    return st.session_state.prompts


def get_video_settings():
    """기본 영상 설정 반환"""
    return VideoSettings(
        aspect_ratio=DEFAULT_ASPECT_RATIO, duration=DEFAULT_VIDEO_DURATION
    )


async def generate_videos(api_key: str, prompts: list, video_settings: VideoSettings):
    """비동기 영상 생성 프로세스"""
    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    try:
        # VideoGenerator를 컨텍스트 매니저로 사용
        async with VideoGenerator(api_key) as video_generator:

            # 기존 작업 확인
            existing_tasks = st.session_state.generation_tasks

            # 진행 상황 표시를 위한 컨테이너
            with progress_placeholder.container():
                st.markdown("### 🎬 영상 생성 진행 상황")
                progress_bar = st.progress(0)
                status_text = st.empty()

            results = []
            total = len(prompts)

            for i, prompt in enumerate(prompts):
                # 진행률 업데이트
                progress = calculate_progress(i, total)
                progress_bar.progress(progress)
                status_text.text(f"생성 중: {i + 1}/{total}")

                # 영상 생성
                result = await video_generator.generate_video(prompt, video_settings)

                # 작업 ID 저장
                st.session_state.generation_tasks.append(
                    {
                        "task_id": result.task_id,
                        "prompt": prompt,
                        "status": "pending",
                        "created_at": datetime.now().isoformat(),
                    }
                )
                save_session()

                # 완료 대기
                final_result = await video_generator.wait_for_completion(result.task_id)

                # 결과 저장
                result_data = {
                    "task_id": final_result.task_id,
                    "prompt": final_result.prompt,
                    "status": final_result.status,
                    "video_url": final_result.video_url or "",
                    "error_message": final_result.error_message or "",
                    "created_at": (
                        final_result.created_at.isoformat()
                        if final_result.created_at
                        else ""
                    ),
                    "completed_at": (
                        final_result.completed_at.isoformat()
                        if final_result.completed_at
                        else ""
                    ),
                }

                # 결과 업데이트
                st.session_state.generation_results.append(result_data)
                save_session()

                results.append(final_result)

            # 완료
            progress_bar.progress(1.0)
            status_text.text("✅ 모든 영상 생성 완료!")

            # 통계 표시
            stats = video_generator.get_statistics(results)

            with status_placeholder.container():
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("전체", stats["total"])
                with col2:
                    st.metric("성공", stats["completed"])
                with col3:
                    st.metric("실패", stats["failed"])
                with col4:
                    st.metric("성공률", f"{stats['success_rate']:.1f}%")

    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
        logger.error(f"영상 생성 중 오류: {str(e)}", exc_info=True)


async def check_generation_status(api_key: str):
    """진행 중인 작업 상태 확인"""
    if not st.session_state.generation_tasks:
        return

    try:
        async with VideoGenerator(api_key) as video_generator:
            updated = False

            for task in st.session_state.generation_tasks:
                # 이미 완료된 작업은 건너뛰기
                if any(
                    r["task_id"] == task["task_id"]
                    and r["status"] in ["completed", "failed"]
                    for r in st.session_state.generation_results
                ):
                    continue

                # 상태 확인
                result = await video_generator.check_status(task["task_id"])

                # 결과 업데이트
                result_data = {
                    "task_id": result.task_id,
                    "prompt": result.prompt,
                    "status": result.status,
                    "video_url": result.video_url or "",
                    "error_message": result.error_message or "",
                    "created_at": task.get("created_at", ""),
                    "completed_at": (
                        result.completed_at.isoformat() if result.completed_at else ""
                    ),
                }

                # 기존 결과 업데이트 또는 추가
                existing_index = next(
                    (
                        i
                        for i, r in enumerate(st.session_state.generation_results)
                        if r["task_id"] == task["task_id"]
                    ),
                    None,
                )

                if existing_index is not None:
                    st.session_state.generation_results[existing_index] = result_data
                else:
                    st.session_state.generation_results.append(result_data)

                updated = True

            if updated:
                save_session()

    except Exception as e:
        logger.error(f"상태 확인 중 오류: {str(e)}")


def render_generation_progress():
    """생성 진행 상황 시각화"""
    results = st.session_state.generation_results
    if not results:
        return

    # 상태별 집계
    total = len(results)
    completed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] == "failed")
    pending = sum(1 for r in results if r["status"] in ["pending", "processing"])

    if pending == 0:
        return

    st.header("3️⃣ 생성 진행 상황")

    # 전체 진행률 표시
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 작업", total)
    with col2:
        st.metric(
            "✅ 완료",
            completed,
            delta=f"{completed/total*100:.0f}%" if total > 0 else "0%",
        )
    with col3:
        st.metric("⏳ 진행중", pending)
    with col4:
        st.metric("❌ 실패", failed)

    # 진행률 바
    progress = completed / total if total > 0 else 0
    st.progress(
        progress, text=f"전체 진행률: {progress*100:.1f}% ({completed}/{total})"
    )

    # 진행 중인 작업 상세
    st.subheader("🔄 실시간 진행 상황")

    for i, result in enumerate(results):
        if result["status"] in ["pending", "processing"]:
            with st.container():
                col1, col2, col3 = st.columns([0.5, 4, 1.5])
                with col1:
                    st.write(f"**#{i+1}**")
                with col2:
                    prompt_preview = (
                        result["prompt"][:60] + "..."
                        if len(result["prompt"]) > 60
                        else result["prompt"]
                    )
                    st.write(f"📝 {prompt_preview}")

                    # 경과 시간 계산
                    if result.get("created_at"):
                        try:
                            created_at = datetime.fromisoformat(result["created_at"])
                            elapsed = (datetime.now() - created_at).total_seconds()
                            st.caption(f"⏱️ 경과 시간: {int(elapsed)}초")
                        except:
                            pass

                    # 진행 애니메이션
                    st.markdown("🎬 영상 생성 중...")
                with col3:
                    st.info("⏳ 생성중")

                st.divider()

    # 예상 남은 시간
    if pending > 0:
        completed_times = []
        for result in results:
            if (
                result["status"] == "completed"
                and result.get("created_at")
                and result.get("completed_at")
            ):
                try:
                    created_at = datetime.fromisoformat(result["created_at"])
                    completed_at = datetime.fromisoformat(result["completed_at"])
                    duration = (completed_at - created_at).total_seconds()
                    completed_times.append(duration)
                except:
                    pass

        if completed_times:
            avg_time = sum(completed_times) / len(completed_times)
            remaining_time = pending * avg_time
            st.info(
                f"⏱️ 예상 남은 시간: {format_time_remaining(int(remaining_time))} (평균 생성 시간: {int(avg_time)}초)"
            )
        else:
            remaining_time = pending * 45  # 기본 45초
            st.info(f"⏱️ 예상 남은 시간: {format_time_remaining(int(remaining_time))}")


def render_results_table():
    """결과 테이블 렌더링"""
    results = st.session_state.generation_results

    if not results:
        st.info("아직 생성된 영상이 없습니다.")
        return

    st.header("4️⃣ 생성된 영상 목록")

    # 각 영상을 카드 형식으로 표시
    for i, result in enumerate(results):
        with st.container():
            # 상단: 체크박스, 번호, 상태
            header_col1, header_col2, header_col3, header_col4 = st.columns(
                [0.5, 1.5, 4, 2]
            )

            with header_col1:
                is_selected = st.checkbox(
                    "선택",
                    value=st.session_state.selected_videos.get(
                        result["task_id"], False
                    ),
                    key=f"check_{result['task_id']}",
                    label_visibility="collapsed",
                )
                st.session_state.selected_videos[result["task_id"]] = is_selected

            with header_col2:
                st.markdown(f"### 영상 {i + 1}")

            with header_col3:
                # 프롬프트 미리보기 (한 줄로)
                st.markdown(
                    f"**프롬프트:** {result['prompt'][:80]}..."
                    if len(result["prompt"]) > 80
                    else f"**프롬프트:** {result['prompt']}"
                )

            with header_col4:
                # 상태
                if result["status"] == "completed":
                    st.success("✅ 완료")
                elif result["status"] == "failed":
                    st.error("❌ 실패")
                else:
                    st.info("⏳ 진행중")

            # 하단: 상세 정보와 미리보기
            detail_col1, detail_col2, detail_col3 = st.columns([5, 1, 2])

            with detail_col1:
                # 전체 프롬프트 표시
                with st.expander("전체 프롬프트 보기"):
                    st.text(result["prompt"])

                # URL 표시
                if result.get("video_url"):
                    st.text_input(
                        "영상 URL:",
                        value=result["video_url"],
                        key=f"url_{result['task_id']}",
                        disabled=True,
                    )

            with detail_col2:
                # 빈 공간
                st.empty()

            with detail_col3:
                # 작은 영상 미리보기
                if result["status"] == "completed" and result.get("video_url"):
                    st.markdown("**미리보기:**")
                    try:
                        st.video(result["video_url"])
                    except:
                        # 비디오 로드 실패시 링크로 대체
                        st.info("미리보기 불가")
                        st.markdown(f"[🎬 새 탭에서 보기]({result['video_url']})")
                elif result["status"] == "pending" or result["status"] == "processing":
                    st.info("🎬 생성 중...")
                elif result["status"] == "failed":
                    st.error("생성 실패")
                    if result.get("error_message"):
                        st.caption(
                            result["error_message"][:50] + "..."
                            if len(result.get("error_message", "")) > 50
                            else result.get("error_message")
                        )

            st.divider()

    save_session()


def render_download_section():
    """다운로드 섹션"""
    results = st.session_state.generation_results

    if not results:
        return

    st.header("4️⃣ 결과 다운로드")

    # CSV 데이터 준비
    csv_data = []
    for result in results:
        csv_data.append(
            {
                "프롬프트": result["prompt"],
                "영상 URL": result["video_url"],
                "상태": result["status"],
                "선택 여부": (
                    "선택"
                    if st.session_state.selected_videos.get(result["task_id"], False)
                    else "미선택"
                ),
                "생성 시작": result.get("created_at", ""),
                "생성 완료": result.get("completed_at", ""),
            }
        )

    df = pd.DataFrame(csv_data)
    csv = df.to_csv(index=False, encoding="utf-8-sig")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 다운로드 버튼을 중앙에 배치
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label="💾 전체 결과 CSV 다운로드",
            data=csv,
            file_name=f"video_results_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )


def main():
    """메인 함수"""
    init_session()
    render_header()

    # 사이드바
    with st.sidebar:
        st.header("📋 사용 가이드")
        st.markdown(
            """
        1. **프롬프트 입력**: 빈 줄(엔터 두 번)로 구분하여 여러 프롬프트를 입력하세요.
        2. **생성 시작**: 🚀 버튼을 클릭하여 영상 생성을 시작하세요.
        3. **진행 상황**: 실시간으로 생성 진행 상황을 확인하세요.
        4. **영상 확인**: 생성된 영상을 미리보기로 재생하고 필요한 것을 선택하세요.
        5. **다운로드**: 전체 결과를 CSV 파일로 다운로드하세요.
        """
        )

        st.divider()

        # 세션 관리
        if st.button("🔄 세션 초기화"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            st.rerun()

        # 진행 중인 작업 확인
        pending_count = sum(
            1
            for r in st.session_state.generation_results
            if r["status"] in ["pending", "processing"]
        )
        if pending_count > 0:
            st.info(f"🔄 진행 중인 작업: {pending_count}개")
            if st.button("상태 업데이트"):
                api_key = get_api_key()
                asyncio.run(check_generation_status(api_key))
                st.rerun()

    # API 키 가져오기
    api_key = get_api_key()

    # 메인 컨텐츠
    prompts = render_prompt_input()

    # 생성 버튼 섹션
    st.divider()

    # 프롬프트가 입력된 경우에만 생성 버튼 활성화
    button_disabled = not prompts or len(prompts) == 0

    # 생성 버튼을 더 눈에 띄게 표시
    if prompts:
        st.markdown(f"### 🎬 총 {len(prompts)}개의 영상을 생성합니다")

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        if st.button(
            "🚀 영상 생성 시작" if prompts else "⚠️ 프롬프트를 입력해주세요",
            type="primary" if prompts else "secondary",
            use_container_width=True,
            disabled=button_disabled,
            help=(
                "프롬프트를 입력한 후 클릭하세요"
                if not prompts
                else f"{len(prompts)}개의 영상을 생성합니다"
            ),
        ):
            with st.spinner(
                f"🎬 {len(prompts)}개의 영상을 생성 중... 잠시만 기다려주세요."
            ):
                video_settings = get_video_settings()
                asyncio.run(generate_videos(api_key, prompts, video_settings))
                st.rerun()

    # 진행 상황 섹션
    if st.session_state.generation_results:
        render_generation_progress()

    # 결과 섹션
    if st.session_state.generation_results:
        st.divider()
        render_results_table()
        st.divider()
        render_download_section()

    # 자동 새로고침 (진행 중인 작업이 있을 때)
    pending_count = sum(
        1
        for r in st.session_state.generation_results
        if r["status"] in ["pending", "processing"]
    )
    if pending_count > 0:
        time.sleep(5)
        asyncio.run(check_generation_status(api_key))
        st.rerun()


if __name__ == "__main__":
    main()
