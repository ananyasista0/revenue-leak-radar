from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_uri: str
    db_name: str = "revenue_leak_radar"

    class Config:
        env_file = "../.env"
        extra = "ignore"  # <- this line ignores any extra fields

settings = Settings()