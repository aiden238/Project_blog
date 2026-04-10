from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    data_dir: Path = Field(default=Path("./data"))
    logs_dir: Path = Field(default=Path("./logs"))
    auto_publish_threshold: float = Field(default=0.75)
    auto_publish_disabled: bool = Field(default=False)
    fetch_timeout_sec: int = Field(default=30)
    fetch_max_retries: int = Field(default=3)
    fetch_rate_limit_per_hour: int = Field(default=60)
    fetch_user_agent: str = Field(default="blog-automation-bot/0.1")

    @property
    def project_root(self) -> Path:
        return _project_root()

    @property
    def resolved_data_dir(self) -> Path:
        return self._resolve_path(self.data_dir)

    @property
    def resolved_logs_dir(self) -> Path:
        return self._resolve_path(self.logs_dir)

    @property
    def sources_dir(self) -> Path:
        return self.project_root / "sources"

    def _resolve_path(self, value: Path) -> Path:
        if value.is_absolute():
            return value
        return self.project_root / value


settings = Settings()
