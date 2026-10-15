from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Defaults below are for local development only; override via environment
    # variables (or a .env file) in every other environment.
    DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"
    SECRET: str = "SECRET_SUPER_SECURISÉ_A_CHANGER_EN_PROD"

    # Comma-separated list of allowed origins, e.g.
    # "http://localhost:8081,https://app.example.com". Defaults to "*" (any
    # origin) for local development.
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list, expanding "*" to a single wildcard entry."""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]


config = Config()  # global
