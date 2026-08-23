from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.schemas.pydantic_schemas import TransactionOut, AuditLogOut

router = APIRouter(prefix="/records", tags=["records"])


def get_db_session() -> Session:
    return SessionLocal()


@router.get("", response_model=list[TransactionOut])
def list_records(
    status: str | None = Query(None, description="Filter by status: at_risk, recovering, recovered"),
    merchant_id: str | None = Query(None),
    is_exception: bool | None = Query(None),
    limit: int = Query(100, le=500),
):
    db = get_db_session()
    try:
        query = db.query(Transaction)
        if status:
            query = query.filter(Transaction.status == status)
        if merchant_id:
            query = query.filter(Transaction.merchant_id == merchant_id)
        if is_exception is not None:
            query = query.filter(Transaction.is_exception == is_exception)

        return query.order_by(Transaction.created_at.desc()).limit(limit).all()
    finally:
        db.close()


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_record(transaction_id: str):
    db = get_db_session()
    try:
        txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return txn
    finally:
        db.close()


@router.get("/{transaction_id}/trace", response_model=list[AuditLogOut])
def get_record_trace(transaction_id: str):
    """
    Full reasoning trace for one record: detection -> diagnosis -> decision -> guardrail -> execution.
    This IS the audit trail the brief requires — every stage, in order, with reasoning.
    """
    db = get_db_session()
    try:
        txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        logs = (
            db.query(AuditLog)
            .filter(AuditLog.transaction_id == transaction_id)
            .order_by(AuditLog.timestamp.asc())
            .all()
        )
        return logs
    finally:
        db.close()


@router.get("/exceptions/all", response_model=list[TransactionOut])
def list_exceptions():
    """The honest exception list — everything the agent could not resolve on its own."""
    db = get_db_session()
    try:
        return (
            db.query(Transaction)
            .filter(Transaction.is_exception == True)  # noqa: E712
            .order_by(Transaction.created_at.desc())
            .all()
        )
    finally:
        db.close()