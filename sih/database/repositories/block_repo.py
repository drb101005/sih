import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from ..client import get_supabase_client
from ..config import settings

logger = logging.getLogger(__name__)


class BlockRepository:
    def __init__(self):
        self.table_name = "blocks"

    def get_available_blocks(
        self,
        corridor_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 2000,
    ) -> List[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                query = client.table(self.table_name).select("*").in_("availability", ["AVAILABLE", "PROVISIONAL"])
                if corridor_id:
                    query = query.eq("corridor_id", corridor_id)
                if date_from:
                    query = query.gte("start_time", date_from)
                if date_to:
                    query = query.lte("end_time", date_to)
                response = query.limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching available blocks from Supabase: {e}")

        # Local CSV Fallback
        if settings.USE_LOCAL_FALLBACK:
            csv_path = Path(settings.DATA_DIR) / "blocks.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                if "availability" in df.columns:
                    df = df[df["availability"].isin(["AVAILABLE", "PROVISIONAL"])]
                if corridor_id and "corridor_id" in df.columns:
                    df = df[df["corridor_id"] == corridor_id]
                return df.head(limit).to_dict(orient="records")
        return []

    def get_all(
        self,
        corridor_id: Optional[str] = None,
        availability: Optional[str] = None,
        limit: int = 2000,
    ) -> List[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                query = client.table(self.table_name).select("*")
                if corridor_id:
                    query = query.eq("corridor_id", corridor_id)
                if availability:
                    query = query.eq("availability", availability)
                response = query.limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching blocks from Supabase: {e}")

        # Local CSV Fallback
        if settings.USE_LOCAL_FALLBACK:
            csv_path = Path(settings.DATA_DIR) / "blocks.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                if corridor_id and "corridor_id" in df.columns:
                    df = df[df["corridor_id"] == corridor_id]
                if availability and "availability" in df.columns:
                    df = df[df["availability"].str.upper() == availability.upper()]
                return df.head(limit).to_dict(orient="records")
        return []

    def get_by_id(self, block_id: str) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).select("*").eq("block_id", block_id).execute()
                if response.data:
                    return response.data[0]
                return None
            except Exception as e:
                logger.error(f"Error fetching block {block_id} from Supabase: {e}")

        if settings.USE_LOCAL_FALLBACK:
            csv_path = Path(settings.DATA_DIR) / "blocks.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                row = df[df["block_id"] == block_id]
                if not row.empty:
                    return row.iloc[0].to_dict()
        return None

    def create(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        bid = block_data.get("block_id")
        if not bid:
            raise ValueError("block_id is required.")

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).insert(block_data).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error inserting block {bid} into Supabase: {e}")
                raise e
        return block_data

    def update_availability(self, block_id: str, availability: str) -> Optional[Dict[str, Any]]:
        update_data = {"availability": availability}
        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).update(update_data).eq("block_id", block_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error updating block {block_id} in Supabase: {e}")
        return None

    def upsert_batch(self, blocks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not blocks_data:
            return []
        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).upsert(blocks_data).execute()
                return response.data or []
            except Exception as e:
                logger.error(f"Error bulk upserting blocks in Supabase: {e}")
        return blocks_data
