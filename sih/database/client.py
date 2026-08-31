import logging
from typing import Optional
from supabase import create_client, Client
from .config import settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Returns a singleton Supabase client instance if configured."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Supabase credentials not configured (SUPABASE_URL / SUPABASE_KEY missing). "
            "Using local fallback data loader if enabled."
        )
        return None

    try:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("Successfully initialized Supabase client.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def is_supabase_connected() -> bool:
    """Checks if Supabase client is initialized and reachable."""
    return get_supabase_client() is not None
