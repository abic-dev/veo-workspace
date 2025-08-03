"""
KIE.AI Veo3 API를 사용한 영상 생성 모듈
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp

from config import (
    API_BASE_URL,
    API_STATUS_ENDPOINT,
    API_VIDEO_ENDPOINT,
    DEFAULT_ASPECT_RATIO,
    DEFAULT_VIDEO_DURATION,
    ERROR_MESSAGES,
    MAX_CONCURRENT_REQUESTS,
    MAX_POLLING_TIME,
    MAX_RETRIES,
    POLLING_INTERVAL,
    RETRY_DELAY,
    VIDEO_MODEL,
)

# 로깅 설정
logger = logging.getLogger(__name__)


@dataclass
class VideoGenerationResult:
    """영상 생성 결과 데이터 클래스"""

    task_id: str
    prompt: str
    status: str  # pending, processing, completed, failed
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class VideoSettings:
    """영상 생성 설정"""

    aspect_ratio: str = DEFAULT_ASPECT_RATIO
    duration: int = DEFAULT_VIDEO_DURATION


class VideoGenerator:
    """영상 생성 클래스"""

    def __init__(self, api_key: str):
        """
        초기화

        Args:
            api_key: API 키
        """
        self.api_key = api_key
        self.base_url = API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.session = None

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    async def generate_video(
        self,
        prompt: str,
        settings: Optional[VideoSettings] = None,
        callback_url: Optional[str] = None,
    ) -> VideoGenerationResult:
        """
        단일 영상 생성

        Args:
            prompt: 영상 생성 프롬프트
            settings: 영상 설정
            callback_url: 완료 콜백 URL (선택)

        Returns:
            영상 생성 결과
        """
        if not settings:
            settings = VideoSettings()

        # API 요청 데이터
        data = {
            "prompt": prompt,
            "aspectRatio": settings.aspect_ratio,  # camelCase로 변경
            "model": VIDEO_MODEL,  # veo3 모델 사용
        }

        # duration은 veo3 API에서 지원하지 않으므로 제거

        if callback_url:
            data["callBackUrl"] = callback_url

        # 재시도 로직
        for attempt in range(MAX_RETRIES):
            try:
                async with self.session.post(
                    f"{self.base_url}{API_VIDEO_ENDPOINT}",
                    headers=self.headers,
                    json=data,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # KIE.AI 응답 형식: {code: 200, msg: "success", data: {taskId: "..."}}
                        if result.get("code") == 200:
                            task_id = result.get("data", {}).get("taskId")
                            if task_id:
                                return VideoGenerationResult(
                                    task_id=task_id,
                                    prompt=prompt,
                                    status="pending",
                                    created_at=datetime.now(),
                                )
                            else:
                                raise Exception("응답에 taskId가 없습니다.")
                        else:
                            raise Exception(
                                f"API 오류: {result.get('msg', 'Unknown error')}"
                            )
                    elif response.status == 401:
                        raise Exception(ERROR_MESSAGES["invalid_api_key"])
                    elif response.status == 429:
                        # Rate limit - 재시도
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                            continue
                        raise Exception("API 요청 한도 초과")
                    else:
                        error_text = await response.text()
                        raise Exception(f"API 오류: {error_text}")

            except aiohttp.ClientError as e:
                logger.error(f"네트워크 오류: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise Exception(ERROR_MESSAGES["network_error"])

        raise Exception(ERROR_MESSAGES["generation_failed"])

    async def check_status(self, task_id: str) -> VideoGenerationResult:
        """
        영상 생성 상태 확인

        Args:
            task_id: 작업 ID

        Returns:
            영상 생성 결과
        """
        try:
            # Query parameter로 taskId 전달
            async with self.session.get(
                f"{self.base_url}{API_STATUS_ENDPOINT}",
                headers=self.headers,
                params={"taskId": task_id},
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    # KIE.AI 응답 형식 처리
                    if result.get("code") == 200:
                        data = result.get("data", {})

                        # successFlag: 0=생성중, 1=성공, 2=실패, 3=생성실패
                        success_flag = data.get("successFlag", 0)

                        # paramJson 파싱하여 프롬프트 추출
                        param_json_str = data.get("paramJson", "{}")
                        try:
                            param_json = json.loads(param_json_str)
                            prompt = param_json.get("prompt", "")
                        except:
                            prompt = ""

                        video_result = VideoGenerationResult(
                            task_id=task_id,
                            prompt=prompt,
                            status=(
                                "pending"
                                if success_flag == 0
                                else "completed" if success_flag == 1 else "failed"
                            ),
                        )

                        # 성공한 경우 영상 URL 추가
                        if success_flag == 1:
                            response_data = data.get("response", {})
                            result_urls = response_data.get("resultUrls", [])
                            if result_urls:
                                video_result.video_url = result_urls[0]
                                video_result.completed_at = datetime.now()
                                video_result.status = "completed"
                        elif success_flag in [2, 3]:
                            video_result.error_message = data.get(
                                "errorMessage", "Unknown error"
                            )
                            video_result.status = "failed"

                        return video_result
                    else:
                        raise Exception(
                            f"상태 확인 실패: {result.get('msg', 'Unknown error')}"
                        )
                else:
                    raise Exception(f"상태 확인 실패: HTTP {response.status}")

        except Exception as e:
            logger.error(f"상태 확인 오류: {str(e)}")
            raise

    async def wait_for_completion(
        self, task_id: str, progress_callback=None
    ) -> VideoGenerationResult:
        """
        영상 생성 완료까지 대기

        Args:
            task_id: 작업 ID
            progress_callback: 진행 상황 콜백 함수

        Returns:
            완료된 영상 생성 결과
        """
        start_time = time.time()

        while True:
            # 시간 초과 체크
            if time.time() - start_time > MAX_POLLING_TIME:
                raise Exception(ERROR_MESSAGES["timeout_error"])

            # 상태 확인
            result = await self.check_status(task_id)

            # 진행 상황 콜백
            if progress_callback:
                progress_callback(result)

            # 완료 또는 실패 시 반환
            if result.status in ["completed", "failed"]:
                return result

            # 폴링 간격 대기
            await asyncio.sleep(POLLING_INTERVAL)

    async def batch_generate(
        self,
        prompts: List[str],
        settings: Optional[VideoSettings] = None,
        progress_callback=None,
    ) -> List[VideoGenerationResult]:
        """
        여러 영상 배치 생성

        Args:
            prompts: 프롬프트 리스트
            settings: 영상 설정
            progress_callback: 진행 상황 콜백

        Returns:
            생성 결과 리스트
        """
        results = []

        # 세마포어로 동시 요청 수 제한
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def generate_with_semaphore(prompt: str, index: int):
            async with semaphore:
                try:
                    # 영상 생성 요청
                    result = await self.generate_video(prompt, settings)

                    # 진행 상황 알림
                    if progress_callback:
                        progress_callback(f"요청 완료: {index + 1}/{len(prompts)}")

                    # 완료 대기
                    final_result = await self.wait_for_completion(
                        result.task_id,
                        lambda r: progress_callback(
                            f"처리 중: {index + 1}/{len(prompts)} - {r.status}"
                        ),
                    )

                    return final_result

                except Exception as e:
                    logger.error(f"영상 생성 실패 (프롬프트 {index + 1}): {str(e)}")
                    return VideoGenerationResult(
                        task_id=f"failed_{index}",
                        prompt=prompt,
                        status="failed",
                        error_message=str(e),
                    )

        # 모든 프롬프트에 대해 비동기 작업 생성
        tasks = [generate_with_semaphore(prompt, i) for i, prompt in enumerate(prompts)]

        # 모든 작업 완료 대기
        results = await asyncio.gather(*tasks)

        return results

    def get_statistics(self, results: List[VideoGenerationResult]) -> Dict:
        """
        생성 결과 통계

        Args:
            results: 생성 결과 리스트

        Returns:
            통계 정보
        """
        total = len(results)
        completed = sum(1 for r in results if r.status == "completed")
        failed = sum(1 for r in results if r.status == "failed")
        pending = sum(1 for r in results if r.status in ["pending", "processing"])

        # 평균 생성 시간 계산
        completion_times = []
        for r in results:
            if r.status == "completed" and r.created_at and r.completed_at:
                duration = (r.completed_at - r.created_at).total_seconds()
                completion_times.append(duration)

        avg_time = (
            sum(completion_times) / len(completion_times) if completion_times else 0
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "average_time": avg_time,
        }
