from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = ""
    groq_api_key: str = ""
    groq_model: str = ""
    github_token: str = ""
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./repopilot.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()