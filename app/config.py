from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/finguard.db"
    model_dir: Path = Path("artifacts")
    raw_data_dir: Path = Path("data/raw")
    feature_store_path: Path = Path("data/processed/v3_model_features.parquet")
    catalog_path: Path = Path("data/processed/transaction_catalog.parquet")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    max_import_rows: int = 0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
for p in [settings.model_dir, settings.raw_data_dir, settings.feature_store_path.parent]:
    p.mkdir(parents=True, exist_ok=True)
Path("data").mkdir(exist_ok=True)
