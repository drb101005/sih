import logging
from typing import Optional, List, Dict, Any
from ..client import get_supabase_client
from ..config import settings

logger = logging.getLogger(__name__)

# Fallback in-memory corridor store for local testing/dev
_LOCAL_CORRIDORS: Dict[str, Dict[str, Any]] = {}


class CorridorRepository:
    def __init__(self):
        self.table_name = "corridors"

    def get_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                query = client.table(self.table_name).select("*")
                if status:
                    query = query.eq("status", status)
                response = query.execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching corridors from Supabase: {e}")

        # Fallback
        results = list(_LOCAL_CORRIDORS.values())
        if status:
            results = [c for c in results if c.get("status") == status]
        return results

    def get_by_id(self, corridor_id: str) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).select("*").eq("corridor_id", corridor_id).execute()
                if response.data:
                    return response.data[0]
                return None
            except Exception as e:
                logger.error(f"Error fetching corridor {corridor_id} from Supabase: {e}")

        return _LOCAL_CORRIDORS.get(corridor_id)

    def create(self, corridor_data: Dict[str, Any]) -> Dict[str, Any]:
        cid = corridor_data.get("corridor_id")
        if not cid:
            raise ValueError("corridor_id is required.")

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).insert(corridor_data).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error inserting corridor {cid} into Supabase: {e}")
                raise e

        _LOCAL_CORRIDORS[cid] = corridor_data
        return corridor_data

    def update_status(
        self,
        corridor_id: str,
        status: str,
        speed_restriction_kmph: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        update_data: Dict[str, Any] = {"status": status}
        if speed_restriction_kmph is not None:
            update_data["speed_restriction_kmph"] = speed_restriction_kmph
        if notes is not None:
            update_data["notes"] = notes

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).update(update_data).eq("corridor_id", corridor_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error updating corridor {corridor_id} in Supabase: {e}")

        if corridor_id in _LOCAL_CORRIDORS:
            _LOCAL_CORRIDORS[corridor_id].update(update_data)
            return _LOCAL_CORRIDORS[corridor_id]
        return None

    def upsert(self, corridor_data: Dict[str, Any]) -> Dict[str, Any]:
        cid = corridor_data.get("corridor_id")
        if not cid:
            raise ValueError("corridor_id is required.")

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).upsert(corridor_data).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error upserting corridor {cid} into Supabase: {e}")

        _LOCAL_CORRIDORS[cid] = corridor_data
        return corridor_data
