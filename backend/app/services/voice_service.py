import os
import uuid
from gtts import gTTS
from app.services.llm_service import client as groq_client, MODEL

VOICE_DIR = "app/static/voice_messages"
os.makedirs(VOICE_DIR, exist_ok=True)


def generate_hinglish_script(customer_name: str, amount: float, days_overdue: int, retries: int = 2) -> str:
    """Generates a natural Hinglish voice-call script via LLM."""
    prompt = f"""Write a short, polite Hinglish (Hindi+English mix, in Devanagari script for the Hindi
parts so it sounds natural when read aloud by a text-to-speech engine) voice call script for a
payment reminder.

Customer name: {customer_name}
Amount due: ₹{amount:,.2f}
Days overdue: {days_overdue}

Keep it under 35 words, warm and respectful, like a real customer support call. Do not include
any links (this is a spoken message, not a text message)."""

    for attempt in range(retries + 1):
        try:
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=400,
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                return text
            print(f"⚠️ Voice script generation returned empty (attempt {attempt + 1})", flush=True)
        except Exception as e:
            print(f"⚠️ Voice script generation failed (attempt {attempt + 1}): {str(e)[:150]}", flush=True)

    # Safe fallback — never return empty, since gTTS requires non-empty text
    return (f"Namaste {customer_name} ji, aapka payment of ₹{amount:,.2f} "
            f"{days_overdue} din se pending hai. Kripya jald bhugtan karein. Dhanyavaad.")


def generate_voice_audio(script_text: str) -> str:
    """
    Converts a Hinglish script into a real Hindi-voiced MP3 file using gTTS.
    Returns the relative file path (served statically by FastAPI).
    """
    filename = f"{uuid.uuid4().hex[:12]}.mp3"
    filepath = os.path.join(VOICE_DIR, filename)

    tts = gTTS(text=script_text, lang="hi", slow=False)
    tts.save(filepath)

    return f"/static/voice_messages/{filename}"