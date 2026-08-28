import json
from datetime import datetime
from fastapi import APIRouter, Request, Header, HTTPException
import razorpay

from app.config import settings
from app.db.database import SessionLocal
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
rzp_utility = razorpay.Utility()


@router.post("/razorpay")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    raw_body = await request.body()

    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing signature header")

    try:
        rzp_utility.verify_webhook_signature(
            raw_body.decode("utf-8"), x_razorpay_signature, settings.razorpay_webhook_secret
        )
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        print(f"⚠️ Unexpected webhook verification error: {str(e)[:200]}", flush=True)
        raise HTTPException(status_code=400, detail="Webhook verification failed")

    payload = json.loads(raw_body)
    event = payload.get("event")
    print(f"📨 Webhook received: {event}", flush=True)

    handlers = {
        "payment_link.paid": _handle_link_paid,
        "payment_link.partially_paid": _handle_link_partially_paid,
        "payment_link.expired": _handle_link_expired,
        "payment_link.cancelled": _handle_link_cancelled,
        "payment.failed": _handle_payment_failed,
        "payment.downtime.started": _handle_downtime_event,
        "payment.downtime.updated": _handle_downtime_event,
        "payment.downtime.resolved": _handle_downtime_event,
        "invoice.paid": _handle_invoice_paid,
        "invoice.partially_paid": _handle_invoice_partially_paid,
        "invoice.expired": _handle_invoice_expired,
        "subscription.charged": _handle_subscription_charged,
        "subscription.halted": _handle_subscription_halted,
        "subscription.pending": _handle_subscription_pending,
        "subscription.activated": _handle_subscription_activated,
        "subscription.cancelled": _handle_subscription_cancelled,
        "order.paid": _handle_order_paid,
    }

    handler = handlers.get(event)
    if handler:
        handler(payload)

    return {"status": "ok"}


# Single shared lookup — razorpay_payment_link_id stores the real Razorpay ID
# regardless of whether it's a payment link, invoice, or subscription ID.
def _get_txn_by_instrument_id(db, instrument_id):
    return db.query(Transaction).filter(Transaction.razorpay_payment_link_id == instrument_id).first()


# ---------- Payment Link events ----------

def _handle_link_paid(payload: dict):
    entity = payload["payload"]["payment_link"]["entity"]
    payment_entity = payload["payload"].get("payment", {}).get("entity", {})

    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
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
        else:
            print(f"⚠️ No matching transaction for payment_link id={entity.get('id')}", flush=True)
    finally:
        db.close()


def _handle_link_partially_paid(payload: dict):
    entity = payload["payload"]["payment_link"]["entity"]
    amount_paid = entity.get("amount_paid", 0) / 100

    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
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
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
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
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
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
        order_id = entity.get("order_id")
        db.add(AuditLog(transaction_id=order_id or "unknown", stage="execution",
                         summary=f"Real payment attempt failed: {entity.get('error_reason')}",
                         reasoning=f"Real webhook: {entity.get('error_description')}",
                         timestamp=datetime.utcnow()))
        db.commit()
    finally:
        db.close()


# ---------- Invoice events ----------

def _handle_invoice_paid(payload: dict):
    entity = payload["payload"]["invoice"]["entity"]
    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
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
        else:
            print(f"⚠️ No matching transaction for invoice id={entity.get('id')}", flush=True)
    finally:
        db.close()


def _handle_invoice_partially_paid(payload: dict):
    entity = payload["payload"]["invoice"]["entity"]
    amount_paid = entity.get("amount_paid", 0) / 100
    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
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
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
        if txn and txn.status == "recovering":
            txn.is_exception = True
            txn.exception_reason = "Invoice expired unpaid"
            db.commit()
    finally:
        db.close()


# ---------- Subscription events ----------

def _handle_subscription_charged(payload: dict):
    entity = payload["payload"]["subscription"]["entity"]
    payment_entity = payload["payload"].get("payment", {}).get("entity", {})
    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
        if txn:
            txn.status = "recovered"
            txn.recovered_amount = txn.amount
            txn.outcome_source = "real_verified"
            txn.real_payment_id = payment_entity.get("id")
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Recovered — subscription charged",
                             reasoning=f"Real webhook confirmed subscription {entity.get('id')} charged.",
                             timestamp=datetime.utcnow()))
            db.commit()
            print(f"✅ Recovered (subscription): {txn.id}", flush=True)
        else:
            print(f"⚠️ No matching transaction for subscription id={entity.get('id')}", flush=True)
    finally:
        db.close()


def _handle_subscription_halted(payload: dict):
    entity = payload["payload"]["subscription"]["entity"]
    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
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

def _handle_downtime_event(payload: dict):
    entity = payload["payload"].get("payment", {}).get("entity", {}) or \
             payload["payload"].get("downtime", {}).get("entity", {})
    method = entity.get("method", "unknown")
    status = entity.get("status", "unknown")
    print(f"⚠️ Razorpay-confirmed downtime — method: {method}, status: {status}", flush=True)
    _set_downtime_flag(method, active=(status != "resolved"))


def _set_downtime_flag(method: str, active: bool):
    from app.services.cache_service import _get_client
    client = _get_client()
    key = f"downtime:{method}"
    try:
        if client:
            if active:
                client.set(key, "1", ex=3600)
            else:
                client.delete(key)
    except Exception as e:
        print(f"⚠️ Downtime flag update failed: {str(e)[:100]}", flush=True)


def _handle_subscription_activated(payload: dict):
    entity = payload["payload"]["subscription"]["entity"]
    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
        if txn:
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Subscription mandate authorized by customer",
                             reasoning=f"Real webhook confirmed subscription {entity.get('id')} activated — "
                                        f"customer completed one-time mandate authorization.",
                             timestamp=datetime.utcnow()))
            db.commit()
            print(f"✅ Subscription activated: {txn.id}", flush=True)
    finally:
        db.close()


def _handle_subscription_cancelled(payload: dict):
    entity = payload["payload"]["subscription"]["entity"]
    db = SessionLocal()
    try:
        txn = _get_txn_by_instrument_id(db, entity.get("id"))
        if txn and txn.status == "recovering":
            txn.is_exception = True
            txn.exception_reason = "Subscription cancelled before recovery completed"
            db.add(AuditLog(transaction_id=txn.id, stage="execution",
                             summary="Subscription cancelled — routed to exception",
                             reasoning=f"Real webhook confirmed subscription {entity.get('id')} cancelled.",
                             timestamp=datetime.utcnow()))
            db.commit()
    finally:
        db.close()

def _handle_order_paid(payload: dict):
    entity = payload["payload"]["order"]["entity"]
    db = SessionLocal()
    try:
        # In a full production build, RAAHI would store the razorpay_order_id
        # at checkout-creation time to match here. Documented as the real linkage point.
        print(f"ℹ️ order.paid received for order {entity.get('id')} — customer completed independently.", flush=True)
    finally:
        db.close()

def _handle_payment_failed(payload: dict):
    entity = payload["payload"]["payment"]["entity"]
    order_id = entity.get("order_id")
    error_code = entity.get("error_code")
    error_description = entity.get("error_description")
    error_reason = entity.get("error_reason")
    
    db = SessionLocal()
    try:
        txn = db.query(Transaction).filter(Transaction.razorpay_order_id == order_id).first()
        if txn and txn.status == "checkout_pending":
            # THIS is the real moment RAAHI learns the genuine failure reason —
            # directly from Razorpay, not guessed by a merchant.
            txn.status = "at_risk"
            txn.failure_reason_code = _map_razorpay_error_to_reason_code(error_code, error_reason)

            db.add(AuditLog(
                transaction_id=txn.id, stage="detection",
                summary=f"Real checkout failure captured: {error_reason}",
                reasoning=f"Razorpay webhook confirmed real payment failure. "
                            f"error_code={error_code}, error_reason={error_reason}, "
                            f"description=\"{error_description}\". This is the genuine root "
                            f"cause signal RAAHI's Diagnosis Agent will process next cycle.",
                timestamp=datetime.utcnow(),
            ))
            db.commit()
            print(f"✅ Real failure captured for {txn.id}: {error_reason}", flush=True)
    finally:
        db.close()


def _map_razorpay_error_to_reason_code(error_code: str, error_reason: str) -> str:
    """Maps Razorpay's real error taxonomy to RAAHI's internal root-cause categories."""
    mapping = {
        "insufficient_funds": "insufficient_funds",
        "payment_timed_out": "network_timeout",
        "gateway_technical_error": "issuer_unavailable",
        "authentication_failed": "authentication_failed",
        "card_declined": "card_declined",
    }
    return mapping.get(error_reason, "unknown")