from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ProcessingStatus
from app.schemas.image import (
    ErrorResponse,
    ResultsResponse,
    StatusResponse,
    UploadAcceptedResponse,
)
from app.services.image_access_service import get_api_stored_image_path
from app.services.query_service import build_results_payload, get_image_or_404
from app.services.upload_service import upload_image

router = APIRouter(prefix="/images", tags=["images"])


@router.post(
    "",
    response_model=UploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def upload(
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> UploadAcceptedResponse:
    record = upload_image(db, image)
    return UploadAcceptedResponse(
        processing_id=record.id,
        status=record.status,
        message="Image accepted for processing",
    )


@router.get(
    "/{processing_id}/status",
    response_model=StatusResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_status(processing_id: str, db: Session = Depends(get_db)) -> StatusResponse:
    record = get_image_or_404(db, processing_id)
    payload = StatusResponse(processing_id=record.id, status=record.status)
    if record.status == ProcessingStatus.FAILED.value:
        payload.failure_reason = record.failure_reason
    return payload


@router.get(
    "/{processing_id}/file",
    responses={404: {"model": ErrorResponse}},
)
def get_image_file(processing_id: str, db: Session = Depends(get_db)) -> FileResponse:
    record = get_image_or_404(db, processing_id)
    file_path = get_api_stored_image_path(record)
    return FileResponse(
        path=file_path,
        media_type=record.mime_type,
        filename=record.original_filename,
    )


@router.get(
    "/{processing_id}/results",
    response_model=ResultsResponse,
    responses={
        202: {"model": ResultsResponse},
        404: {"model": ErrorResponse},
    },
)
def get_results(processing_id: str, db: Session = Depends(get_db)):
    record = get_image_or_404(db, processing_id)

    if record.status in {
        ProcessingStatus.PENDING.value,
        ProcessingStatus.PROCESSING.value,
    }:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "processing_id": record.id,
                "status": record.status,
                "analysis": None,
                "failure_reason": None,
                "message": "Analysis is not ready yet",
            },
        )

    return build_results_payload(record)
