import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from cryptotax.db.models.csv_import import CsvImport, CsvImportRow


class CsvImportRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_import(
        self,
        entity_id: uuid.UUID,
        exchange: str,
        filename: str,
        rows_data: list[dict],
    ) -> CsvImport:
        """Create a CsvImport with all its rows in one transaction."""
        csv_import = CsvImport(
            entity_id=entity_id,
            exchange=exchange,
            filename=filename,
            row_count=len(rows_data),
            status="uploaded",
        )
        self._session.add(csv_import)
        await self._session.flush()

        for idx, row in enumerate(rows_data, start=1):
            csv_row = CsvImportRow(
                import_id=csv_import.id,
                row_number=idx,
                utc_time=row.get("utc_time", ""),
                account=row.get("account", ""),
                operation=row.get("operation", ""),
                coin=row.get("coin", ""),
                change=row.get("change", ""),
                remark=row.get("remark"),
            )
            self._session.add(csv_row)

        await self._session.flush()
        # Refresh to load rows via selectin
        await self._session.refresh(csv_import)
        return csv_import

    async def get_by_id(self, import_id: uuid.UUID) -> Optional[CsvImport]:
        result = await self._session.execute(
            select(CsvImport).where(CsvImport.id == import_id)
        )
        return result.scalar_one_or_none()

    async def list_for_entity(
        self,
        entity_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CsvImport], int]:
        """List imports for an entity (without loading rows). Returns (imports, total_count)."""
        # Count total
        count_result = await self._session.execute(
            select(func.count(CsvImport.id)).where(CsvImport.entity_id == entity_id)
        )
        total = count_result.scalar() or 0

        # Fetch imports without rows (noload to override the selectin default)
        result = await self._session.execute(
            select(CsvImport)
            .where(CsvImport.entity_id == entity_id)
            .options(noload(CsvImport.rows))
            .order_by(CsvImport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        imports = list(result.scalars().all())
        return imports, total

    async def update_status(
        self,
        import_id: uuid.UUID,
        status: str,
        parsed_count: Optional[int] = None,
        error_count: Optional[int] = None,
    ) -> None:
        csv_import = await self.get_by_id(import_id)
        if csv_import is None:
            return
        csv_import.status = status
        if parsed_count is not None:
            csv_import.parsed_count = parsed_count
        if error_count is not None:
            csv_import.error_count = error_count
        await self._session.flush()

    async def get_rows(
        self,
        import_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CsvImportRow]:
        stmt = select(CsvImportRow).where(CsvImportRow.import_id == import_id)
        if status:
            stmt = stmt.where(CsvImportRow.status == status)
        stmt = stmt.order_by(CsvImportRow.row_number).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
