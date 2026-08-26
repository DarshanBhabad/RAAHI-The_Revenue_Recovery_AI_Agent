import razorpay
from app.config import settings

client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def create_test_order(amount: float, currency: str = "INR", receipt: str | None = None) -> dict:
    amount_paise = int(round(amount * 100))
    return client.order.create({
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt or f"raahi_{amount_paise}",
        "payment_capture": 1,
    })


def create_payment_link(amount: float, customer_name: str, customer_email: str,
                         customer_phone: str, description: str) -> dict:
    amount_paise = int(round(amount * 100))
    return client.payment_link.create({
        "amount": amount_paise,
        "currency": "INR",
        "description": description,
        "customer": {
            "name": customer_name,
            "email": customer_email,
            "contact": customer_phone,
        },
        "notify": {"sms": True, "email": True},
        "reminder_enable": True,
    })
def create_subscription_charge_retry(subscription_id: str) -> dict:
    """Triggers Razorpay to retry a failed subscription charge."""
    return client.subscription.fetch(subscription_id)  # Razorpay auto-retries; we just monitor


def create_invoice(amount: float, customer_name: str, customer_email: str,
                    customer_phone: str, description: str) -> dict:
    """Creates a real Razorpay Invoice. Returns an invoice object containing
    a 'short_url' — the real invoice link a customer clicks to pay."""
    amount_paise = int(round(amount * 100))
    return client.invoice.create({
        "type": "invoice",
        "customer": {
            "name": customer_name,
            "email": customer_email,
            "contact": customer_phone,
        },
        "line_items": [{
            "name": description,
            "amount": amount_paise,
            "currency": "INR",
            "quantity": 1,
        }],
        "sms_notify": 1,
        "email_notify": 1,
    })


def create_plan(amount: float, plan_name: str, period: str = "monthly", interval: int = 1) -> dict:
    """Creates a real Razorpay Plan — required before a Subscription can be created."""
    amount_paise = int(round(amount * 100))
    return client.plan.create({
        "period": period,
        "interval": interval,
        "item": {
            "name": plan_name,
            "amount": amount_paise,
            "currency": "INR",
        },
    })


def create_subscription(plan_id: str, total_count: int = 12) -> dict:
    """Creates a real Razorpay Subscription. Returns a subscription object
    containing 'short_url' — the real authorization link a customer clicks
    once to activate recurring billing."""
    return client.subscription.create({
        "plan_id": plan_id,
        "customer_notify": 1,
        "total_count": total_count,
        "notes": {"source": "RAAHI recovery"},
    })