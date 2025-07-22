# app/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Path
from .core.predict import predict_disease
from .models import DiagnosisResult, ErrorResponse, AnalysisRequest # Pydantic 모델 임포트
from PIL import Image
from io import BytesIO
import requests

app = FastAPI(
    title="작물별 질병 진단 API",
    description="사용자가 선택한 작물에 맞는 AI 모델을 사용하여 질병을 진단하고, 상세 정보와 해결 방안을 제공합니다.",
    version="3.0.0"
)

@app.get("/", summary="서버 상태 확인")
def read_root():
    """서버가 정상적으로 동작하는지 확인합니다."""
    return {"status": "OK", "message": "작물별 질병 진단 서버가 준비되었습니다."}

# --- 여기부터 수정된 부분 ---

@app.post(
    "/diagnose/{crop_name}",
    summary="작물별 이미지 파일 진단",
    description="URL 경로에 **작물 이름(예: pumpkin, k_melon)**을 명시하고 이미지 파일을 업로드하면, 해당 작물 전용 AI 모델이 진단합니다.",
    response_model=DiagnosisResult,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 파일 형식"},
        404: {"model": ErrorResponse, "description": "지원하지 않는 작물이거나 모델 파일 없음"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"}
    }
)
async def diagnose_crop(
    crop_name: str = Path(..., description="진단할 작물의 영문 이름 (예: pumpkin)", example="pumpkin"),
    file: UploadFile = File(..., description="진단할 작물 이미지 파일")
):
    """
    - **crop_name**: URL을 통해 전달받는 작물의 영문 이름입니다. (predict.py의 MODEL_CONFIG 키와 일치해야 함)
    - **file**: `multipart/form-data` 형식으로 전송된 이미지 파일입니다.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")

    image_bytes = await file.read()

    # AI 예측 함수 호출
    disease_info, confidence, error = predict_disease(crop_name, image_bytes)

    # 예측 과정에서 오류 발생 시 처리
    if error:
        if "지원되지 않는" in error:
            raise HTTPException(status_code=404, detail=error)
        elif "모델 파일이 없습니다" in error or "불러오는 데 실패" in error:
            raise HTTPException(status_code=404, detail=error)
        else:
            raise HTTPException(status_code=500, detail=error)

    # 성공적으로 예측 완료 시, 결과 반환
    return DiagnosisResult(
        filename=file.filename,
        confidence=round(confidence, 2),
        disease_info=disease_info
    )


@app.post(
    "/diagnose-by-url/{crop_name}",
    summary="작물별 이미지 URL 진단",
    description="URL 경로에 **작물 이름(예: pumpkin, k_melon)**을 명시하고 이미지 URL을 JSON으로 전송하면, 해당 작물 전용 AI 모델이 진단합니다.",
    response_model=DiagnosisResult,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 이미지 URL 또는 형식"},
        404: {"model": ErrorResponse, "description": "지원하지 않는 작물이거나 모델 파일 없음"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"}
    }
)
async def diagnose_by_url(crop_name: str, request: AnalysisRequest):
    """
    - **crop_name**: URL을 통해 전달받는 작물의 영문 이름입니다.
    - **request**: 이미지 URL을 포함하는 요청 본문입니다.
    """
    try:
        response = requests.get(request.image_url)
        response.raise_for_status() # 2xx 상태 코드가 아니면 오류 발생
        image_bytes = response.content
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"이미지 URL에서 파일을 다운로드할 수 없습니다: {e}")

    # 이미지 유효성 확인
    try:
        img = Image.open(BytesIO(image_bytes))
        img.verify() # 이미지가 유효한지 체크
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"유효한 이미지 파일이 아닙니다: {e}")

    # AI 예측 함수 호출
    disease_info, confidence, error = predict_disease(crop_name, image_bytes)

    # 예측 과정에서 오류 발생 시 처리
    if error:
        if "지원되지 않는" in error:
            raise HTTPException(status_code=404, detail=error)
        elif "모델 파일이 없습니다" in error or "불러오는 데 실패" in error:
            raise HTTPException(status_code=404, detail=error)
        else:
            raise HTTPException(status_code=500, detail=error)

    # 성공적으로 예측 완료 시, 결과 반환
    return DiagnosisResult(
        filename=request.image_url.split("/")[-1],
        confidence=round(confidence, 2),
        disease_info=disease_info
    )
