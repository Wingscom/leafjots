"""Imports API -- upload CSV files, list import history, trigger parsing."""

import csv
import io
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db, resolve_entity
from cryptotax.api.schemas.imports import (
    CsvImportDetailResponse,
    CsvImportListResponse,
    CsvImportResponse,
    CsvImportRowResponse,
    ImportSummaryResponse,
    ParseImportResponse,
    UploadResponse,
)
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.wallet import CEXWallet
from cryptotax.db.repos.csv_import_repo import CsvImportRepo
from cryptotax.parser.cex.binance_csv import BinanceCsvParser

router = APIRouter(prefix="/api/imports", tags=["imports"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

REQUIRED_COLUMNS = {"UTC_Time", "Account", "Operation", "Coin", "Change"}


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    db: DbDep,
    file: UploadFile = File(...),
    entity_id: uuid.UUID = Form(...),
    exchange: str = Form("binance"),
) -> UploadResponse:
    """Upload a CSV file and store all raw rows for later parsing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Read file content
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header")

    # Validate required columns
    actual_columns = set(reader.fieldnames)
    missing = REQUIRED_COLUMNS - actual_columns
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}",
        )

    # Extract rows
    rows_data: list[dict] = []
    for row in reader:
        rows_data.append({
            "utc_time": (row.get("UTC_Time") or "").strip(),
            "account": (row.get("Account") or "").strip(),
            "operation": (row.get("Operation") or "").strip(),
            "coin": (row.get("Coin") or "").strip(),
            "change": (row.get("Change") or "").strip(),
            "remark": (row.get("Remark") or "").strip() or None,
        })

    if not rows_data:
        raise HTTPException(status_code=400, detail="CSV file contains no data rows")

    repo = CsvImportRepo(db)
    csv_import = await repo.create_import(
        entity_id=entity_id,
        exchange=exchange,
        filename=file.filename,
        rows_data=rows_data,
    )
    await db.commit()

    return UploadResponse(
        import_id=csv_import.id,
        filename=csv_import.filename,
        row_count=csv_import.row_count,
        status=csv_import.status,
    )


@router.get("", response_model=CsvImportListResponse)
async def list_imports(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
) -> CsvImportListResponse:
    """List CSV imports for the resolved entity."""
    repo = CsvImportRepo(db)
    imports, total = await repo.list_for_entity(entity.id)
    return CsvImportListResponse(
        imports=[
            CsvImportResponse(
                id=imp.id,
                entity_id=imp.entity_id,
                exchange=imp.exchange,
                filename=imp.filename,
                row_count=imp.row_count,
                parsed_count=imp.parsed_count,
                error_count=imp.error_count,
                status=imp.status,
                created_at=imp.created_at,
            )
            for imp in imports
        ],
        total=total,
    )


@router.get("/{import_id}", response_model=CsvImportDetailResponse)
async def get_import_detail(
    import_id: uuid.UUID,
    db: DbDep,
) -> CsvImportDetailResponse:
    """Get a single import with its rows."""
    repo = CsvImportRepo(db)
    csv_import = await repo.get_by_id(import_id)
    if csv_import is None:
        raise HTTPException(status_code=404, detail="Import not found")

    return CsvImportDetailResponse(
        id=csv_import.id,
        entity_id=csv_import.entity_id,
        exchange=csv_import.exchange,
        filename=csv_import.filename,
        row_count=csv_import.row_count,
        parsed_count=csv_import.parsed_count,
        error_count=csv_import.error_count,
        status=csv_import.status,
        created_at=csv_import.created_at,
        rows=[
            CsvImportRowResponse(
                id=r.id,
                row_number=r.row_number,
                utc_time=r.utc_time,
                account=r.account,
                operation=r.operation,
                coin=r.coin,
                change=r.change,
                remark=r.remark,
                status=r.status,
                error_message=r.error_message,
            )
            for r in csv_import.rows
        ],
    )


@router.get("/{import_id}/rows", response_model=list[CsvImportRowResponse])
async def get_import_rows(
    import_id: uuid.UUID,
    db: DbDep,
    status: Optional[str] = Query(None, description="Filter rows by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[CsvImportRowResponse]:
    """Get rows for a specific import, with optional status filter."""
    repo = CsvImportRepo(db)
    # Verify import exists
    csv_import = await repo.get_by_id(import_id)
    if csv_import is None:
        raise HTTPException(status_code=404, detail="Import not found")

    rows = await repo.get_rows(import_id, status=status, limit=limit, offset=offset)
    return [
        CsvImportRowResponse(
            id=r.id,
            row_number=r.row_number,
            utc_time=r.utc_time,
            account=r.account,
            operation=r.operation,
            coin=r.coin,
            change=r.change,
            remark=r.remark,
            status=r.status,
            error_message=r.error_message,
        )
        for r in rows
    ]


@router.get("/{import_id}/summary", response_model=ImportSummaryResponse)
async def get_import_summary(import_id: uuid.UUID, db: DbDep) -> ImportSummaryResponse:
    """Get parse summary with operation counts and status breakdown."""
    repo = CsvImportRepo(db)
    csv_import = await repo.get_by_id(import_id)
    if csv_import is None:
        raise HTTPException(status_code=404, detail="Import not found")

    rows = csv_import.rows
    op_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {"parsed": 0, "error": 0, "skipped": 0, "pending": 0}
    for row in rows:
        op_counts[row.operation] = op_counts.get(row.operation, 0) + 1
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

    return ImportSummaryResponse(
        import_id=csv_import.id,
        total=csv_import.row_count,
        operation_counts=op_counts,
        status_counts=status_counts,
    )


@router.post("/{import_id}/parse", response_model=ParseImportResponse)
async def parse_import(import_id: uuid.UUID, db: DbDep) -> ParseImportResponse:
    """Trigger parsing of a CSV import's rows into journal entries."""
    repo = CsvImportRepo(db)
    csv_import = await repo.get_by_id(import_id)
    if csv_import is None:
        raise HTTPException(status_code=404, detail="Import not found")
    if csv_import.status not in ("uploaded", "completed"):
        raise HTTPException(
            status_code=409,
            detail=f"Import status is '{csv_import.status}', expected 'uploaded' or 'completed'",
        )

    # Get or create CEX wallet for this entity+exchange
    wallet = await _get_or_create_cex_wallet(db, csv_import.entity_id, csv_import.exchange)

    # Parse
    await repo.update_status(csv_import.id, "parsing")
    parser = BinanceCsvParser(db, csv_import.entity_id, wallet)
    stats = await parser.parse_import(csv_import)

    # Update import status
    final_status = "completed"
    await repo.update_status(csv_import.id, final_status, parsed_count=stats.parsed, error_count=stats.errors)
    await db.commit()

    return ParseImportResponse(
        import_id=csv_import.id,
        total=stats.total,
        parsed=stats.parsed,
        errors=stats.errors,
        skipped=stats.skipped,
    )


async def _get_or_create_cex_wallet(
    db: AsyncSession, entity_id: uuid.UUID, exchange: str
) -> CEXWallet:
    """Get or create a CEX wallet for this entity+exchange combo."""
    result = await db.execute(
        select(CEXWallet).where(
            CEXWallet.entity_id == entity_id,
            CEXWallet.exchange == exchange,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = CEXWallet(
            entity_id=entity_id,
            exchange=exchange,
            label=f"{exchange.title()} CSV Import",
            wallet_type="cex",
        )
        db.add(wallet)
        await db.flush()
    return wallet
