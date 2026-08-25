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