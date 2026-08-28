from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    groq_api_key: str = ""
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    database_url: str = "sqlite:///./raahi.db"
    environment: str = "development"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_voice_from: str = ""
    raahi_verified_phone: str = ""

    class Config:
        env_file = ".env"


settings = Settings()