"""Reports API — generate and download bangketoan.xlsx."""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db
from cryptotax.api.schemas.reports import ReportGenerateRequest, ReportResponse
from cryptotax.db.repos.entity_repo import EntityRepo
from cryptotax.report.service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/generate", response_model=ReportResponse)
async def generate_report(body: ReportGenerateRequest, db: DbDep) -> ReportResponse:
    """Generate a bangketoan.xlsx report for the given entity and date range."""
    entity_repo = EntityRepo(db)

    if body.entity_id:
        entity = await entity_repo.get_by_id(body.entity_id)
    else:
        entity = await entity_repo.get_default()

    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    try:
        start = datetime.fromisoformat(body.start_date).replace(tzinfo=None)
        end = datetime.fromisoformat(body.end_date).replace(hour=23, minute=59, second=59, tzinfo=None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    service = ReportService(db)
    record = await service.generate(entity.id, start, end)
    await db.commit()

    return ReportResponse(
        id=record.id,
        entity_id=record.entity_id,
        period_start=record.period_start,
        period_end=record.period_end,
        status=record.status,
        filename=record.filename,
        generated_at=record.generated_at,
        error_message=record.error_message,
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    db: DbDep,
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter reports by entity"),
) -> list[ReportResponse]:
    """List all generated reports, optionally filtered by entity."""
    service = ReportService(db)
    records = await service.list_reports(entity_id=entity_id)
    return [
        ReportResponse(
            id=r.id,
            entity_id=r.entity_id,
            period_start=r.period_start,
            period_end=r.period_end,
            status=r.status,
            filename=r.filename,
            generated_at=r.generated_at,
            error_message=r.error_message,
        )
        for r in records
    ]


@router.get("/{report_id}/status", response_model=ReportResponse)
async def get_report_status(report_id: str, db: DbDep) -> ReportResponse:
    """Get status of a specific report."""
    import uuid as _uuid

    try:
        rid = _uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    service = ReportService(db)
    record = await service.get_report(rid)

    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        id=record.id,
        entity_id=record.entity_id,
        period_start=record.period_start,
        period_end=record.period_end,
        status=record.status,
        filename=record.filename,
        generated_at=record.generated_at,
        error_message=record.error_message,
    )


@router.get("/{report_id}/download")
async def download_report(report_id: str, db: DbDep):
    """Download a completed report as .xlsx file."""
    import uuid as _uuid

    try:
        rid = _uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    service = ReportService(db)
    record = await service.get_report(rid)

    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if record.status != "completed":
        raise HTTPException(status_code=400, detail=f"Report status is '{record.status}', not downloadable")

    file_path = service.get_file_path(record)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    buf = file_path.read_bytes()
    filename = record.filename or "bangketoan.xlsx"

    from io import BytesIO

    return StreamingResponse(
        BytesIO(buf),
        media_type=XLSX_CONTENT_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
