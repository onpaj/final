from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"  # "development" | "production"
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "uploads"
    appinsights_connection_string: str = ""

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
    )


settings = Settings()
