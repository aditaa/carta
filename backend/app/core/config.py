import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    api_v1_prefix: str
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_user: str
    mysql_password: str
    database_url: str
    rules_file: Path
    auth_secret_key: str
    access_token_minutes: int

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


@lru_cache
def get_settings() -> Settings:
    backend_root = Path(__file__).resolve().parents[2]
    rules_file = Path(os.getenv("RULES_FILE", "../rules/carta-arcanum-2.1.4.rules.json"))
    if not rules_file.is_absolute():
        rules_file = backend_root / rules_file

    mysql_host = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_database = os.getenv("MYSQL_DATABASE", "carta_arcanum")
    mysql_user = os.getenv("MYSQL_USER", "carta")
    mysql_password = os.getenv("MYSQL_PASSWORD", "change-me")
    default_database_url = (
        f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    )

    return Settings(
        app_name=os.getenv("APP_NAME", "Carta Arcanum API"),
        app_env=os.getenv("APP_ENV", "local"),
        api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
        mysql_host=mysql_host,
        mysql_port=mysql_port,
        mysql_database=mysql_database,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        database_url=os.getenv("DATABASE_URL", default_database_url),
        rules_file=rules_file.resolve(),
        auth_secret_key=os.getenv("AUTH_SECRET_KEY", "local-dev-change-me"),
        access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "720")),
    )
