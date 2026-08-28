from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.services.razorpay_client import create_test_order
from app.db.database import SessionLocal
from app.models.customer import Customer
from app.models.transaction import Transaction
import uuid

router = APIRouter(prefix="/checkout", tags=["checkout"])


class CheckoutRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    amount: float
    record_type: str


@router.post("/create")
def create_checkout_session(body: CheckoutRequest):
    """
    Creates a real Razorpay Order and a pending customer record.
    The actual Transaction row is created ONLY when payment.failed fires —
    this endpoint just sets up the real checkout attempt.
    """
    db = SessionLocal()
    try:
        customer = Customer(
            id=f"cust_{uuid.uuid4().hex[:10]}",
            name=body.name,
            email=body.email,
            phone=body.phone,
            ltv_segment="standard",
            opted_out=False,
        )
        db.add(customer)
        db.flush()

        order = create_test_order(body.amount, receipt=customer.id)

        # Store a PENDING placeholder — becomes a real at_risk Transaction
        # only when the webhook confirms a genuine failure.
        pending_txn = Transaction(
            id=f"pending_{uuid.uuid4().hex[:12]}",
            merchant_id="merch_real_001",
            customer_id=customer.id,
            record_type=body.record_type,
            amount=body.amount,
            status="checkout_pending",
            razorpay_order_id=order["id"],
        )
        db.add(pending_txn)
        db.commit()

        return {
            "checkout_url": f"/checkout/pay/{order['id']}?amount={int(body.amount * 100)}&txn_id={pending_txn.id}",
            "order_id": order["id"],
            "transaction_id": pending_txn.id,
        }
    finally:
        db.close()


@router.get("/pay/{order_id}", response_class=HTMLResponse)
def checkout_page(order_id: str, amount: int, txn_id: str):
    return f"""
    <!DOCTYPE html>
    <html><body style="font-family: sans-serif; text-align: center; padding-top: 100px;">
    <h2>RAAHI — Real Checkout</h2>
    <p>Complete or fail this payment to test real failure capture.</p>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
        var options = {{
            "key": "{settings.razorpay_key_id}",
            "amount": "{amount}",
            "currency": "INR",
            "order_id": "{order_id}",
            "notes": {{ "raahi_txn_id": "{txn_id}" }},
            "handler": function (response) {{
                document.body.innerHTML = "<h2>✅ Payment Succeeded</h2><p>" + response.razorpay_payment_id + "</p>";
            }},
            "modal": {{
                "ondismiss": function() {{
                    document.body.innerHTML = "<h2>Checkout closed</h2>";
                }}
            }}
        }};
        var rzp = new Razorpay(options);
        rzp.on('payment.failed', function (response){{
            document.body.innerHTML = "<h2>❌ Payment Failed</h2><p>" + response.error.description + "</p>";
        }});
        window.onload = function() {{ rzp.open(); }};
    </script>
    </body></html>
    """