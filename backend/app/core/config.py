from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "3GPP RAG Backend"
    database_url: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_password: str = ""
    upload_dir: str = "uploads"
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_chat_model: str = "gemini-3.6-flash"
    chunk_size_words: int = 250
    chunk_overlap_words: int = 40
    top_k_results: int = 8
    chat_max_output_tokens: int = 1024

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        password = quote_plus(self.db_password)
        return (
            f"postgresql+psycopg://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
