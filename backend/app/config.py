from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    groq_api_key: str = ""
    database_url: str = "sqlite:///./raahi.db"
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()