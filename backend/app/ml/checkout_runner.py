import time
from playwright.sync_api import sync_playwright
from app.services.razorpay_client import create_test_order, client as rzp_client
from app.ml.real_checkout_cards import CARD_MAP

BASE_URL = "http://127.0.0.1:8000"


def run_real_checkout(amount: float, root_cause: str, should_succeed: bool) -> dict:
    """
    Drives an actual headless Razorpay test-mode checkout and returns the
    REAL resulting payment status and error details from Razorpay's API —
    not a modeled/random outcome.
    """
    amount_paise = int(round(amount * 100))
    order = create_test_order(amount)
    order_id = order["id"]

    card_info = CARD_MAP["success_card"] if should_succeed else CARD_MAP.get(root_cause, CARD_MAP["card_expired"])

    url = f"{BASE_URL}/test-checkout/{order_id}?amount={amount_paise}"
    payment_id = None
    outcome = "unknown"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        try:
            frame = page.frame_locator("iframe[name^='razorpay']").first
            frame.locator("input[placeholder='Card Number']").fill(card_info["number"], timeout=8000)
            frame.locator("input[placeholder='Valid thru']").fill("12/30")
            frame.locator("input[placeholder='CVV']").fill("123")
            frame.locator("button:has-text('Pay')").click()

            page.wait_for_timeout(3000)
            mock_frame = page.frame_locator("iframe[name^='razorpay']").first
            mock_frame.locator(f"button:has-text('{card_info['target']}')").click(timeout=8000)

            page.wait_for_timeout(3000)
            title = page.title()
            if title.startswith("SUCCESS:"):
                payment_id = title.split(":", 1)[1]
                outcome = "success"
            elif title.startswith("FAILED:"):
                payment_id = title.split(":", 1)[1]
                outcome = "failed"
        except Exception as e:
            outcome = f"automation_error: {str(e)[:150]}"
        finally:
            browser.close()

    result = {"order_id": order_id, "payment_id": payment_id, "outcome": outcome,
              "error_code": None, "error_reason": None, "error_description": None}

    if payment_id:
        try:
            real_payment = rzp_client.payment.fetch(payment_id)
            result["status"] = real_payment.get("status")
            result["error_code"] = real_payment.get("error_code")
            result["error_reason"] = real_payment.get("error_reason")
            result["error_description"] = real_payment.get("error_description")
        except Exception as e:
            result["fetch_error"] = str(e)[:150]

    return result