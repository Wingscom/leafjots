"""Reports API — generate and stream bangketoan.xlsx on-demand."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db
from cryptotax.api.schemas.reports import ReportGenerateRequest
from cryptotax.db.repos.entity_repo import EntityRepo
from cryptotax.report.service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/download")
async def download_report(body: ReportGenerateRequest, db: DbDep):
    """Generate bangketoan.xlsx from DB and stream it — no file saved to disk."""
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
    buf = await service.generate_buffer(entity.id, start, end)

    filename = f"bangketoan_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf,
        media_type=XLSX_CONTENT_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
