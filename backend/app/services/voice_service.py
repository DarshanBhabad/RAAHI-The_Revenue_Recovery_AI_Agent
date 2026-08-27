import uuid
import io
from gtts import gTTS
from supabase import create_client
from app.config import settings
from app.services.llm_service import client as groq_client, MODEL

supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
BUCKET_NAME = "voice-messages"

def generate_hinglish_script(customer_name: str, amount: float, days_overdue: int, retries: int = 2) -> str:
    """Generates a natural Hinglish voice-call script via LLM."""
    prompt = f"""Write a short, polite Hinglish (Hindi+English mix, in Devanagari script for the Hindi
parts so it sounds natural when read aloud by a text-to-speech engine) voice call script for a
payment reminder.

Customer name: {customer_name}
Amount due: ₹{amount:,.2f}
Days overdue: {days_overdue}

Keep it under 35 words, warm and respectful, like a real customer support call. Do not include
any links (this is a spoken message, not a text message). Write ONLY the complete script,
nothing else."""

    for attempt in range(retries + 1):
        try:
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=600,  # raised — same truncation issue as promise extraction
            )
            choice = response.choices[0]
            text = (choice.message.content or "").strip()

            if text and choice.finish_reason != "length":
                return text

            print(f"⚠️ Voice script incomplete or truncated (attempt {attempt + 1}, "
                  f"finish_reason={choice.finish_reason})", flush=True)

        except Exception as e:
            print(f"⚠️ Voice script generation failed (attempt {attempt + 1}): {str(e)[:150]}", flush=True)

    # Safe fallback — never return empty or truncated text, since gTTS needs complete, valid input
    return (f"Namaste {customer_name} ji, aapka payment of ₹{amount:,.2f} "
            f"{days_overdue} din se pending hai. Kripya jald bhugtan karein. Dhanyavaad.")

def generate_voice_audio(script_text: str) -> str:
    """
    Converts text to real Hindi TTS audio and uploads it to Supabase Storage.
    Returns a real, permanent, publicly-playable URL.
    """
    filename = f"{uuid.uuid4().hex[:12]}.mp3"

    buffer = io.BytesIO()
    tts = gTTS(text=script_text, lang="hi", slow=False)
    tts.write_to_fp(buffer)
    buffer.seek(0)

    supabase.storage.from_(BUCKET_NAME).upload(
        filename, buffer.read(), file_options={"content-type": "audio/mpeg"}
    )

    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
    return public_url