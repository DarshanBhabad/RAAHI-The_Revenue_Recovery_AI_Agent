import time
import json
import re
from groq import Groq
from app.config import settings

client = Groq(api_key=settings.groq_api_key)
MODEL = "openai/gpt-oss-20b"       #"openai/gpt-oss-120b"


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def get_diagnosis_narrative(record_type: str, failure_reason_code: str, amount: float, retries: int = 2) -> dict:
    prompt = f"""You are a payments risk analyst. Analyze this failed transaction and respond with ONLY a JSON object, no other text.

Record type: {record_type}
Failure reason code: {failure_reason_code}
Amount: ₹{amount:,.2f}

JSON format required:
{{"narrative": "one short sentence max 25 words explaining the likely root cause", "confidence": 0.75}}
"""

    last_error = None
    for attempt in range(retries + 1):
        try:
            # response = client.chat.completions.create(
            #     model=MODEL,
            #     messages=[{"role": "user", "content": prompt}],
            #     temperature=0.2,
            #     max_tokens=500,          # raised — reasoning models need headroom beyond the visible answer
            #     reasoning_effort="low",  # minimizes hidden reasoning tokens, leaves room for actual output
            # )
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500,
            )
            choice = response.choices[0]
            text = (choice.message.content or "").strip()
            finish_reason = choice.finish_reason

            if not text:
                last_error = f"Empty response (finish_reason={finish_reason})"
                print(f"⚠️ Groq returned empty content (attempt {attempt + 1}, finish_reason={finish_reason})", flush=True)
                continue

            data = _extract_json(text)
            if data is None:
                last_error = f"Could not extract JSON from: {text[:150]}"
                print(f"⚠️ Groq response not parseable (attempt {attempt + 1}): {text[:150]}", flush=True)
                continue

            narrative = str(data.get("narrative", "")).strip()
            try:
                confidence = float(data.get("confidence", 0.5))
            except (TypeError, ValueError):
                confidence = 0.5
            confidence = max(0.0, min(1.0, confidence))

            return {
                "narrative": narrative or "Model returned empty narrative.",
                "confidence": confidence,
            }

        except Exception as e:
            last_error = e
            error_str = str(e)
            print(f"⚠️ Groq call failed (attempt {attempt + 1}/{retries + 1}): {error_str[:150]}", flush=True)

            if "429" in error_str or "rate" in error_str.lower():
                time.sleep(3 * (attempt + 1))
            elif "reasoning_effort" in error_str.lower() or "unrecognized" in error_str.lower():
                # Param not supported by this model/SDK version — retry once without it
                return _fallback_without_reasoning_param(record_type, failure_reason_code, amount)
            else:
                break

    return {
        "narrative": f"LLM reasoning unavailable after {retries + 1} attempts ({str(last_error)[:80]}).",
        "confidence": 0.4,
    }


def _fallback_without_reasoning_param(record_type: str, failure_reason_code: str, amount: float) -> dict:
    """If reasoning_effort isn't accepted, retry once with plain params and a bigger token budget."""
    prompt = f"""You are a payments risk analyst. Analyze this failed transaction and respond with ONLY a JSON object, no other text.

Record type: {record_type}
Failure reason code: {failure_reason_code}
Amount: ₹{amount:,.2f}

JSON format required:
{{"narrative": "one short sentence max 25 words explaining the likely root cause", "confidence": 0.75}}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
        )
        text = (response.choices[0].message.content or "").strip()
        data = _extract_json(text)
        if data:
            narrative = str(data.get("narrative", "")).strip()
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
            return {"narrative": narrative or "Model returned empty narrative.", "confidence": confidence}
    except Exception as e:
        print(f"⚠️ Fallback call also failed: {str(e)[:150]}", flush=True)

    return {"narrative": "LLM reasoning unavailable (fallback also failed).", "confidence": 0.4}