import json
from fastapi import APIRouter, Request, Header, HTTPException
import razorpay

from app.config import settings
from app.db.database import SessionLocal
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from datetime import datetime

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
rzp_utility = razorpay.Utility()


@router.post("/razorpay")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    raw_body = await request.body()

    try:
        rzp_utility.verify_webhook_signature(
            raw_body.decode("utf-8"), x_razorpay_signature, settings.razorpay_webhook_secret
        )
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = json.loads(raw_body)
    event = payload.get("event")
    print(f"📨 Webhook received: {event}", flush=True)

    handlers = {
        "payment_link.paid": _handle_link_paid,
        "payment_link.partially_paid": _handle_link_partially_paid,
        "payment_link.expired": _handle_link_expired,
        "payment_link.cancelled": _handle_link_cancelled,
        "payment.failed": _handle_payment_failed,
        "invoice.paid": _handle_invoice_paid,
        "invoice.partially_paid": _handle_invoice_partially_paid,
        "invoice.expired": _handle_invoice_expired,
        "subscription.charged": _handle_subscription_charged,
        "subscription.halted": _handle_subscription_halted,
        "subscription.pending": _handle_subscription_pending,
    }

    handler = handlers.get(event)
    if handler:
        handler(payload)

    return {"status": "ok"}


def _get_txn_by_link_id(db, link_id):
    return db.query(Transaction).filter(Transaction.razorpay_payment_link_id == link_id).first()


def _handle_link_paid(payload: dict):
    entity = payload["payload"]["payment_link"]["entity"]
    payment_entity = payload["payload"].get("payment", {}).get("entity", {})

    db = SessionLocal()
    try:
        txn = _get_txn_by_link_id(db, entity.get("id"))
        if txn:
            txn.status = "recovered"
            txn.recovered_amount = txn.amount
            txn.outcome_source = "real_verified"
            txn.real_payment_id = payment_entity.get("id")
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Recovered — payment link paid",
                             reasoning=f"Real webhook confirmed full payment via link {entity.get('id')}.",
                             timestamp=datetime.utcnow()))
            db.commit()
            print(f"✅ Recovered: {txn.id} — ₹{txn.amount:,.2f}", flush=True)
    finally:
        db.close()


def _handle_link_partially_paid(payload: dict):
    entity = payload["payload"]["payment_link"]["entity"]
    amount_paid = entity.get("amount_paid", 0) / 100

    db = SessionLocal()
    try:
        txn = _get_txn_by_link_id(db, entity.get("id"))
        if txn:
            txn.status = "partially_recovered"
            txn.recovered_amount = amount_paid
            txn.outcome_source = "real_verified"
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary=f"Partially recovered — ₹{amount_paid:,.2f} of ₹{txn.amount:,.2f}",
                             reasoning="Real webhook confirmed partial payment via link.",
                             timestamp=datetime.utcnow()))
            db.commit()
    finally:
        db.close()


def _handle_link_expired(payload: dict):
    entity = payload["payload"]["payment_link"]["entity"]

    db = SessionLocal()
    try:
        txn = _get_txn_by_link_id(db, entity.get("id"))
        if txn and txn.status == "recovering":
            txn.is_exception = True
            txn.exception_reason = "Payment link expired unpaid"
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Link expired — routed to exception",
                             reasoning="Real webhook confirmed link expiry with no payment received.",
                             timestamp=datetime.utcnow()))
            db.commit()
    finally:
        db.close()


def _handle_link_cancelled(payload: dict):
    entity = payload["payload"]["payment_link"]["entity"]

    db = SessionLocal()
    try:
        txn = _get_txn_by_link_id(db, entity.get("id"))
        if txn:
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Link cancelled",
                             reasoning="Real webhook confirmed link cancellation.",
                             timestamp=datetime.utcnow()))
            db.commit()
    finally:
        db.close()


def _handle_payment_failed(payload: dict):
    entity = payload["payload"]["payment"]["entity"]

    db = SessionLocal()
    try:
        # Match by order_id if the failed payment ties back to one of our records
        order_id = entity.get("order_id")
        db.add(AuditLog(transaction_id=order_id or "unknown", stage="execution",
                         summary=f"Real payment attempt failed: {entity.get('error_reason')}",
                         reasoning=f"Real webhook: {entity.get('error_description')}",
                         timestamp=datetime.utcnow()))
        db.commit()
    finally:
        db.close()

def _get_txn_by_invoice_id(db, invoice_id):
    return db.query(Transaction).filter(Transaction.razorpay_payment_link_id == invoice_id).first()


def _handle_invoice_paid(payload: dict):
    entity = payload["payload"]["invoice"]["entity"]
    db = SessionLocal()
    try:
        txn = _get_txn_by_invoice_id(db, entity.get("id"))
        if txn:
            txn.status = "recovered"
            txn.recovered_amount = txn.amount
            txn.outcome_source = "real_verified"
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Recovered — invoice paid",
                             reasoning=f"Real webhook confirmed invoice {entity.get('id')} paid.",
                             timestamp=datetime.utcnow()))
            db.commit()
            print(f"✅ Recovered (invoice): {txn.id} — ₹{txn.amount:,.2f}", flush=True)
    finally:
        db.close()


def _handle_invoice_partially_paid(payload: dict):
    entity = payload["payload"]["invoice"]["entity"]
    amount_paid = entity.get("amount_paid", 0) / 100
    db = SessionLocal()
    try:
        txn = _get_txn_by_invoice_id(db, entity.get("id"))
        if txn:
            txn.status = "partially_recovered"
            txn.recovered_amount = amount_paid
            txn.outcome_source = "real_verified"
            db.commit()
    finally:
        db.close()


def _handle_invoice_expired(payload: dict):
    entity = payload["payload"]["invoice"]["entity"]
    db = SessionLocal()
    try:
        txn = _get_txn_by_invoice_id(db, entity.get("id"))
        if txn and txn.status == "recovering":
            txn.is_exception = True
            txn.exception_reason = "Invoice expired unpaid"
            db.commit()
    finally:
        db.close()


def _handle_subscription_charged(payload: dict):
    entity = payload["payload"]["subscription"]["entity"]
    payment_entity = payload["payload"].get("payment", {}).get("entity", {})
    db = SessionLocal()
    try:
        # Match subscription failures by customer/amount since we don't have a stored subscription_id yet;
        # in a full build, store razorpay_subscription_id on the transaction when created upstream.
        txn = db.query(Transaction).filter(
            Transaction.record_type == "subscription",
            Transaction.status == "recovering",
        ).first()  # simplified matching — refine with a stored subscription_id field for production
        if txn:
            txn.status = "recovered"
            txn.recovered_amount = txn.amount
            txn.outcome_source = "real_verified"
            txn.real_payment_id = payment_entity.get("id")
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Recovered — subscription auto-retry succeeded",
                             reasoning="Real webhook confirmed subscription.charged event.",
                             timestamp=datetime.utcnow()))
            db.commit()
            print(f"✅ Recovered (subscription): {txn.id}", flush=True)
    finally:
        db.close()


def _handle_subscription_halted(payload: dict):
    entity = payload["payload"]["subscription"]["entity"]
    db = SessionLocal()
    try:
        txn = db.query(Transaction).filter(
            Transaction.record_type == "subscription", Transaction.status == "recovering",
        ).first()
        if txn:
            txn.is_exception = True
            txn.exception_reason = "Subscription halted — Razorpay exhausted automatic retries"
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Subscription halted — routed to exception",
                             reasoning="Real webhook: subscription.halted after exhausted retries.",
                             timestamp=datetime.utcnow()))
            db.commit()
    finally:
        db.close()


def _handle_subscription_pending(payload: dict):
    print("ℹ️ Subscription charge pending/retrying — no state change needed.", flush=True)