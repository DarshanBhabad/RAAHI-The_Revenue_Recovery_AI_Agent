import time
from playwright.sync_api import sync_playwright
from app.services.razorpay_client import create_test_order, client as rzp_client
from app.ml.real_checkout_cards import CARD_MAP

BASE_URL = "http://127.0.0.1:8000"


def run_real_checkout(amount: float, root_cause: str, should_succeed: bool) -> dict:
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
        page.goto(url, wait_until="domcontentloaded", timeout=45000)

        try:
            frame = page.frame_locator("iframe.razorpay-checkout-frame")

            # Step 1: Contact details screen — enter mobile number, click Continue
            mobile_input = frame.locator("input[placeholder='Mobile number']")
            mobile_input.wait_for(timeout=15000)
            mobile_input.fill("9999999999")
            frame.locator("button:has-text('Continue')").click()

            # Step 2: Payment Options screen — Cards tab is selected by default
            card_number_input = frame.locator("input[placeholder='Card Number']")
            card_number_input.wait_for(timeout=15000)
            card_number_input.fill(card_info["number"])

            frame.locator("input[placeholder='MM / YY']").fill("12/30")
            frame.locator("input[placeholder='CVV']").fill("123")
            frame.locator("button:has-text('Continue')").click()

            # Step 3: Mock bank page — Success/Failure choice
            page.wait_for_timeout(3000)
            mock_frame = page.frame_locator("iframe.razorpay-checkout-frame")
            mock_frame.locator(f"button:has-text('{card_info['target']}')").click(timeout=10000)

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