from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.config import settings

router = APIRouter(prefix="/test-checkout", tags=["test-checkout"])


@router.get("/{order_id}", response_class=HTMLResponse)
def checkout_page(order_id: str, amount: int):
    return f"""
    <!DOCTYPE html>
    <html><body>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
        var options = {{
            "key": "{settings.razorpay_key_id}",
            "amount": "{amount}",
            "currency": "INR",
            "order_id": "{order_id}",
            "handler": function (response) {{
                document.title = "SUCCESS:" + response.razorpay_payment_id;
            }},
            "modal": {{
                "ondismiss": function() {{
                    document.title = "DISMISSED";
                }}
            }}
        }};
        var rzp = new Razorpay(options);
        rzp.on('payment.failed', function (response){{
            document.title = "FAILED:" + response.error.metadata.payment_id;
        }});
        window.onload = function() {{ rzp.open(); }};
    </script>
    </body></html>
    """