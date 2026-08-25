import json
from fastapi import APIRouter, Request, Header, HTTPException
import razorpay

from app.config import settings
from app.db.database import SessionLocal
from app.models.transaction import Transaction

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

    if event in ("payment_link.paid", "payment.captured"):
        _handle_payment_success(payload)

    return {"status": "ok"}


def _handle_payment_success(payload: dict):
    entity_payload = payload.get("payload", {})
    payment_link_entity = entity_payload.get("payment_link", {}).get("entity", {})
    payment_entity = entity_payload.get("payment", {}).get("entity", {})

    link_id = payment_link_entity.get("id")
    payment_id = payment_entity.get("id")

    db = SessionLocal()
    try:
        txn = db.query(Transaction).filter(Transaction.razorpay_payment_link_id == link_id).first() if link_id else None

        if txn:
            txn.status = "recovered"
            txn.recovered_amount = txn.amount
            txn.outcome_source = "real_verified"
            txn.real_payment_id = payment_id
            db.commit()
            print(f"✅ Recovered via webhook: {txn.id} — ₹{txn.amount:,.2f}", flush=True)
        else:
            print(f"⚠️ No matching transaction for link_id={link_id}", flush=True)
    finally:
        db.close()