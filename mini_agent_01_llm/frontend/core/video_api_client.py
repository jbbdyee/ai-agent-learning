"""영상 업로드처럼 처리 시간이 긴 미디어 요청 기능."""

import os
from typing import Any

import httpx

from core.api_client import BackendAPIError


BACKEND_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000").rstrip("/")
VIDEO_REQUEST_TIMEOUT = 180.0


def upload_video(
    filename: str,
    content: bytes,
    content_type: str,
    question: str,
    frame_count: int,
) -> Any:
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/media/video-analysis",
            files={"video": (filename, content, content_type)},
            data={"question": question, "frame_count": str(frame_count)},
            timeout=VIDEO_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        try:
            detail = error.response.json().get("detail", str(error))
        except ValueError:
            detail = str(error)
        raise BackendAPIError(detail) from error
    except httpx.TimeoutException as error:
        raise BackendAPIError("영상 분석 응답 시간이 초과되었습니다.") from error
    except httpx.RequestError as error:
        raise BackendAPIError("백엔드 서버에 연결할 수 없습니다.") from error
