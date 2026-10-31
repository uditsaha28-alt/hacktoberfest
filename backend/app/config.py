from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = ""
    gemini_fallback_models: str = ""
    groq_api_key: str = ""
    groq_model: str = ""
    github_token: str = ""
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./repopilot.db"

    # Agent behaviour
    use_fake_run: bool = False
    agent_max_tool_calls: int = 14
    agent_timeout_seconds: int = 180
    agent_synthesis_seconds: int = 90
    llm_timeout_seconds: int = 60
    gemini_thinking_level: str = "low"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()