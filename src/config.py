from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # DB
    database_url: str

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:12b"
    ollama_temperature: float = 0.3
    ollama_max_tokens: int = 2048
    ollama_timeout_sec: int = 120
    ollama_max_retries: int = 3

    # 자동 게시 게이트
    auto_publish_threshold: float = 0.75
    auto_publish_disabled: bool = False

    # 상용 LLM (기본 비활성)
    use_commercial_llm: bool = False
    openai_api_key: str = ""

    # Tistory (Phase 4)
    tistory_enabled: bool = False
    tistory_access_token: str = ""
    tistory_blog_name: str = ""

    # Notion
    notion_token: str = ""
    notion_database_id: str = ""

    # 수집
    fetch_timeout_sec: int = 30
    fetch_max_retries: int = 3
    fetch_rate_limit_per_hour: int = 60

    # 로컬 스토리지
    data_dir: Path = Path("./data")
    logs_dir: Path = Path("./logs")

    # Phase 4 feature flags
    pgvector_enabled: bool = False
    s3_mirror_enabled: bool = False
    litellm_enabled: bool = False


settings = Settings()
