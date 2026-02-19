"""ReportService — orchestrates report generation."""

import logging
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.report import ReportRecord
from cryptotax.report.data_collector import ReportDataCollector
from cryptotax.report.excel_writer import ExcelWriter

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")


class ReportService:
    """Orchestrates data collection → Excel generation → persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate(
        self,
        entity_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> ReportRecord:
        """Generate a bangketoan.xlsx report and persist metadata."""
        filename = f"bangketoan_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.xlsx"

        record = ReportRecord(
            entity_id=entity_id,
            period_start=start,
            period_end=end,
            status="generating",
            filename=filename,
        )
        self._session.add(record)
        await self._session.flush()

        try:
            # Collect data
            collector = ReportDataCollector(self._session)
            report_data = await collector.collect(entity_id, start, end)

            # Write Excel
            writer = ExcelWriter()
            buf = writer.write_to_buffer(report_data)

            # Save to disk
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            file_path = REPORTS_DIR / f"{record.id}_{filename}"
            file_path.write_bytes(buf.getvalue())

            # Update record
            record.status = "completed"
            record.generated_at = datetime.now()
            await self._session.flush()

            logger.info("Report generated: %s", file_path)
        except Exception as e:
            record.status = "failed"
            record.error_message = str(e)
            await self._session.flush()
            logger.exception("Report generation failed")

        return record

    async def get_report(self, report_id: uuid.UUID) -> ReportRecord | None:
        result = await self._session.execute(
            select(ReportRecord).where(ReportRecord.id == report_id)
        )
        return result.scalar_one_or_none()

    async def list_reports(self, entity_id: uuid.UUID | None = None) -> list[ReportRecord]:
        stmt = select(ReportRecord).order_by(ReportRecord.created_at.desc())
        if entity_id is not None:
            stmt = stmt.where(ReportRecord.entity_id == entity_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def get_file_path(self, report: ReportRecord) -> Path | None:
        """Return the file path for a completed report."""
        if report.status != "completed" or not report.filename:
            return None
        path = REPORTS_DIR / f"{report.id}_{report.filename}"
        return path if path.exists() else None

    async def generate_buffer(
        self,
        entity_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> BytesIO:
        """Generate report and return the Excel buffer directly (no file save)."""
        collector = ReportDataCollector(self._session)
        report_data = await collector.collect(entity_id, start, end)
        writer = ExcelWriter()
        return writer.write_to_buffer(report_data)
