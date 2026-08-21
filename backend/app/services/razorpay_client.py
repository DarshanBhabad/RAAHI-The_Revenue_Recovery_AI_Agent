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