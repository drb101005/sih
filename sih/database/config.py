import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or sih folder
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Fallback to local CSV if Supabase is not configured or in offline test mode
    USE_LOCAL_FALLBACK: bool = os.getenv("USE_LOCAL_FALLBACK", "true").lower() in ("true", "1", "yes")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")


settings = Settings()
