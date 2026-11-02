from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"
    jwt_secret_key: str = "development-only-change-this-secret"
    jwt_expire_minutes: int = 1440
    upload_dir: Path = BACKEND_DIR / "uploads"
    chroma_dir: Path = BACKEND_DIR / "data" / "chroma"
    chroma_collection: str = "knowledge_chunks"
    retrieval_max_distance: float = 0.72
    retrieval_candidate_top_k: int = 60
    retrieval_final_top_k: int = 3
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    mem0_enabled: bool = False
    mem0_llm_api_key: str = ""
    mem0_llm_base_url: str = ""
    mem0_llm_model: str = ""
    mem0_embedder_api_key: str = ""
    mem0_embedder_base_url: str = ""
    mem0_embedder_model: str = ""
    mem0_embedding_dims: int = 0
    mem0_chroma_dir: Path = BACKEND_DIR / "data" / "mem0_chroma"
    mem0_chroma_collection: str = "conversation_memories"
    web_search_enabled: bool = False
    tavily_api_key: str = ""
    tavily_mcp_url: str = "https://mcp.tavily.com/mcp/"

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    @model_validator(mode="after")
    def resolve_storage_paths(self) -> "Settings":
        if self.database_url.startswith("sqlite:"):
            sqlite_path = self.database_url.removeprefix("sqlite:///")
            database_path = Path(sqlite_path)
            if not database_path.is_absolute():
                database_path = BACKEND_DIR / database_path
            self.database_url = f"sqlite:///{database_path.resolve().as_posix()}"

        for field_name in ("upload_dir", "chroma_dir", "mem0_chroma_dir"):
            path = Path(getattr(self, field_name))
            if not path.is_absolute():
                path = BACKEND_DIR / path
            setattr(self, field_name, path.resolve())
        return self


settings = Settings()
