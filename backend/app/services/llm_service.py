from groq import Groq
from app.config import settings

client = Groq(api_key=settings.groq_api_key)

MODEL = "openai/gpt-oss-120b"


def get_diagnosis_narrative(record_type: str, failure_reason_code: str, amount: float) -> dict:
    """
    Asks the LLM to explain the root cause in plain English and assign a confidence score.
    Returns a dict: {"narrative": str, "confidence": float}
    """
    prompt = f"""You are a payments risk analyst. Given this failed transaction, explain the likely root cause in ONE short sentence (max 25 words), and give a confidence score between 0.0 and 1.0 for how certain this diagnosis is.

Record type: {record_type}
Failure reason code: {failure_reason_code}
Amount: ₹{amount:,.2f}

Respond ONLY in this exact format, nothing else:
NARRATIVE: <your one sentence explanation>
CONFIDENCE: <a number between 0.0 and 1.0>
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=150,
        )
        text = response.choices[0].message.content.strip()

        narrative = ""
        confidence = 0.5

        for line in text.split("\n"):
            if line.upper().startswith("NARRATIVE:"):
                narrative = line.split(":", 1)[1].strip()
            elif line.upper().startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    confidence = 0.5

        return {"narrative": narrative or "Unable to generate detailed reasoning.", "confidence": confidence}

    except Exception as e:
        # Never let an LLM failure break the pipeline — degrade gracefully
        return {
            "narrative": f"LLM reasoning unavailable ({str(e)[:60]}). Falling back to rule-based classification only.",
            "confidence": 0.4,
        }