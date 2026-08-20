from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.config import settings
from app.schemas import TtsRequest
from app.services.media_service import analyze_image, analyze_video, create_speech


media_router = APIRouter(prefix="/api/media", tags=["Multimodal"])


@media_router.post("/image-analysis")
async def image_analysis(
    image: UploadFile = File(...),
    question: str = Form("여행자가 알아야 할 정보와 주의점을 알려주세요."),
) -> dict:
    try:
        result = analyze_image(image.content_type or "", await image.read(), question)
        return result.model_dump()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"이미지 분석 실패: {error}") from error


@media_router.post("/tts")
def text_to_speech(payload: TtsRequest) -> Response:
    try:
        audio = create_speech(payload.text, payload.voice, payload.instructions)
        return Response(
            content=audio,
            media_type="audio/mpeg",
            headers={"X-Synthetic-Voice": "true"},
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"TTS 생성 실패: {error}") from error


@media_router.post("/video-analysis")
async def video_analysis(
    video: UploadFile = File(...),
    question: str = Form(
        "영상의 전체 흐름과 주요 장면, 사용자가 주의해야 할 점을 알려주세요."
    ),
    frame_count: int | None = Form(None),
) -> dict:
    try:
        result, extracted_frame_count, duration_seconds = analyze_video(
            video.content_type or "",
            await video.read(),
            question,
            frame_count or settings.video_analysis_frame_count,
        )
        return {
            **result.model_dump(),
            "extracted_frame_count": extracted_frame_count,
            "duration_seconds": duration_seconds,
        }
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"영상 분석 실패: {error}") from error
