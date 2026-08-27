import json
import re
from datetime import datetime
from app.services.llm_service import client as groq_client, MODEL


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def extract_promise_from_text(customer_reply: str, reference_date: datetime = None, retries: int = 2) -> dict:
    """
    Parses a customer's free-text reply (SMS/email/WhatsApp) and extracts a
    structured promise-to-pay date, if one is genuinely present. This is real
    NLP intent extraction, not a template match — handles natural variations
    like "Friday", "in 3 days", "next week", "after salary" etc.
    """
    reference_date = reference_date or datetime.utcnow()

    prompt = f"""Today's date is {reference_date.date().isoformat()} ({reference_date.strftime('%A')}).

A customer replied to a payment reminder with this message: "{customer_reply}"

Does this message contain a genuine commitment to pay by a specific date or timeframe?
Resolve relative dates (e.g. "Friday", "next week", "in 3 days") into an actual calendar date
based on today's date above.

Respond ONLY with a JSON object, no other text:
{{"has_promise": true or false, "promised_date": "YYYY-MM-DD" or null, "confidence": a number between 0.0 and 1.0, "reasoning": "one short sentence"}}

If the message is vague, evasive, or contains no real commitment (e.g. "I'll try", "maybe later"),
set has_promise to false."""

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=600
            )
            text = (response.choices[0].message.content or "").strip()
            data = _extract_json(text)

            if data is None:
                last_error = f"Could not parse JSON from: {text[:100]}"
                continue

            # Validate the date is actually parseable and in the future
            if data.get("has_promise") and data.get("promised_date"):
                try:
                    parsed_date = datetime.fromisoformat(data["promised_date"])
                    if parsed_date < reference_date:
                        data["has_promise"] = False
                        data["reasoning"] = "Extracted date was in the past — likely misparsed, treating as no valid promise."
                except (ValueError, TypeError):
                    data["has_promise"] = False
                    data["promised_date"] = None
                    data["reasoning"] = "Could not parse extracted date."

            return {
                "has_promise": bool(data.get("has_promise", False)),
                "promised_date": data.get("promised_date"),
                "confidence": max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
                "reasoning": data.get("reasoning", ""),
            }

        except Exception as e:
            last_error = e
            print(f"⚠️ Promise extraction call failed (attempt {attempt + 1}): {str(e)[:150]}", flush=True)

    return {
        "has_promise": False,
        "promised_date": None,
        "confidence": 0.0,
        "reasoning": f"Extraction failed after {retries + 1} attempts: {str(last_error)[:100]}",
    }