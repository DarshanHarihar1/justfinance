from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import db_session, get_llm
from app.core.exceptions import not_found
from app.models import Statement, Transaction
from app.schemas.statement import ParsedSummary, StatementOut
from app.schemas.transaction import TransactionOut
from app.services.llm.openrouter import OpenRouterClient
from app.services.upload_pipeline import ingest_statement

router = APIRouter()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/upload", response_model=ParsedSummary)
async def upload_statement(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(db_session),
    llm: OpenRouterClient = Depends(get_llm),
) -> ParsedSummary:
    if file.content_type not in (None, "application/pdf", "application/octet-stream"):
        from app.core.exceptions import unprocessable

        raise unprocessable("invalid_file_type", "Only PDF files are accepted.")
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        from app.core.exceptions import unprocessable

        raise unprocessable("file_too_large", "Maximum upload size is 10 MB.")
    if not data.startswith(b"%PDF"):
        from app.core.exceptions import unprocessable

        raise unprocessable("invalid_file_type", "Only PDF files are accepted.")

    summary = await ingest_statement(
        pdf_bytes=data,
        filename=file.filename or "statement.pdf",
        db=db,
        llm=llm,
    )
    return ParsedSummary(
        statement_id=summary.statement_id,
        period_start=summary.period_start,
        period_end=summary.period_end,
        parsed_count=summary.parsed_count,
        new_count=summary.new_count,
        needs_review_count=summary.needs_review_count,
        warnings=summary.warnings,
    )


@router.get("", response_model=list[StatementOut])
async def list_statements(db: AsyncSession = Depends(db_session)) -> list[Statement]:
    result = await db.execute(select(Statement).order_by(Statement.period_start.desc()))
    return list(result.scalars().all())


@router.get("/{statement_id}", response_model=StatementOut)
async def get_statement(
    statement_id: int,
    db: AsyncSession = Depends(db_session),
) -> Statement:
    stmt = await db.get(Statement, statement_id)
    if stmt is None:
        raise not_found("statement")
    return stmt


@router.delete("/{statement_id}", status_code=204)
async def delete_statement(
    statement_id: int,
    db: AsyncSession = Depends(db_session),
) -> None:
    stmt = await db.get(Statement, statement_id)
    if stmt is None:
        raise not_found("statement")
    await db.delete(stmt)
    await db.commit()


@router.get("/{statement_id}/review", response_model=list[TransactionOut])
async def review_statement(
    statement_id: int,
    db: AsyncSession = Depends(db_session),
) -> list[Transaction]:
    stmt = await db.get(Statement, statement_id)
    if stmt is None:
        raise not_found("statement")
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.statement_id == statement_id,
            Transaction.needs_review.is_(True),
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    return list(result.scalars().all())
