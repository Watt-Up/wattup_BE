from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_URL: str
    MONGO_URL: str
    MONGO_DB: str
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

settings = Settings()