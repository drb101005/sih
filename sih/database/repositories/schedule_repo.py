import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from ..client import get_supabase_client
from ..config import settings

logger = logging.getLogger(__name__)

# Local in-memory store for generated schedules
_LOCAL_SCHEDULES: List[Dict[str, Any]] = []


def _clean_json_val(v):
    if isinstance(v, (pd.Timestamp, pd.Timedelta)):
        return str(v)
    elif hasattr(v, "isoformat"):
        return v.isoformat()
    elif isinstance(v, (int, float, str, bool)) or v is None:
        return v
    elif hasattr(v, "item"):
        return v.item()
    elif isinstance(v, dict):
        return {k: _clean_json_val(val) for k, val in v.items()}
    elif isinstance(v, (list, tuple, set)):
        return [_clean_json_val(val) for val in v]
    return str(v)


class ScheduleRepository:
    def __init__(self):
        self.table_name = "schedules"

    def get_schedules(
        self,
        corridor_id: Optional[str] = None,
        task_id: Optional[str] = None,
        block_id: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                query = client.table(self.table_name).select("*")
                if corridor_id:
                    query = query.eq("corridor_id", corridor_id)
                if task_id:
                    query = query.eq("task_id", task_id)
                if block_id:
                    query = query.eq("block_id", block_id)
                response = query.order("scheduled_start", desc=False).limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching schedules from Supabase: {e}")

        # Local fallback
        results = list(_LOCAL_SCHEDULES)
        if not results and settings.USE_LOCAL_FALLBACK:
            csv_path = Path(settings.DATA_DIR) / "schedule.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                results = df.to_dict(orient="records")

        if corridor_id:
            results = [r for r in results if r.get("corridor_id") == corridor_id]
        if task_id:
            results = [r for r in results if r.get("task_id") == task_id]
        if block_id:
            results = [r for r in results if r.get("block_id") == block_id]
        return results[:limit]

    def save_single(self, schedule_dict: Dict[str, Any], explanation_facts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        clean_facts = _clean_json_val(explanation_facts or {})
        record = {
            "task_id": schedule_dict.get("task_id"),
            "block_id": schedule_dict.get("block_id"),
            "corridor_id": schedule_dict.get("corridor_id"),
            "scheduled_start": str(schedule_dict.get("scheduled_start")),
            "scheduled_end": str(schedule_dict.get("scheduled_end")),
            "estimated_duration_minutes": int(schedule_dict.get("estimated_duration_minutes", 0)),
            "required_resources": str(schedule_dict.get("required_resources", "")),
            "resource_count": int(schedule_dict.get("resource_count", 1)),
            "max_resources": int(schedule_dict.get("max_resources", 5)),
            "priority_score": float(schedule_dict.get("priority_score", 0.0)),
            "priority_class": str(schedule_dict.get("priority_class", "")),
            "final_score": float(schedule_dict.get("final_score", 0.0)),
            "duration_fit": float(schedule_dict.get("duration_fit", 0.0)),
            "cost_score": float(schedule_dict.get("cost_score", 0.0)),
            "goods_score": float(schedule_dict.get("goods_score", 0.0)),
            "train_conflict_score": float(schedule_dict.get("train_conflict_score", 0.0)),
            "resource_score": float(schedule_dict.get("resource_score", 0.0)),
            "explanation_facts": clean_facts,
            "schedule_status": "SCHEDULED",
        }

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).insert(record).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error persisting schedule to Supabase: {e}")

        _LOCAL_SCHEDULES.append(record)
        return record

    def save_batch(self, schedule_df: pd.DataFrame) -> List[Dict[str, Any]]:
        if schedule_df.empty:
            return []

        records = []
        for _, row in schedule_df.iterrows():
            d = row.to_dict()
            records.append({
                "task_id": d.get("task_id"),
                "block_id": d.get("block_id"),
                "corridor_id": d.get("corridor_id"),
                "scheduled_start": str(d.get("scheduled_start")),
                "scheduled_end": str(d.get("scheduled_end")),
                "estimated_duration_minutes": int(d.get("estimated_duration_minutes", 0)),
                "required_resources": str(d.get("required_resources", "")),
                "resource_count": int(d.get("resource_count", 1)),
                "max_resources": int(d.get("max_resources", 5)),
                "priority_score": float(d.get("priority_score", 0.0)),
                "priority_class": str(d.get("priority_class", "")),
                "final_score": float(d.get("final_score", 0.0)),
                "duration_fit": float(d.get("duration_fit", 0.0)),
                "cost_score": float(d.get("cost_score", 0.0)),
                "goods_score": float(d.get("goods_score", 0.0)),
                "train_conflict_score": float(d.get("train_conflict_score", 0.0)),
                "resource_score": float(d.get("resource_score", 0.0)),
                "schedule_status": "SCHEDULED",
            })

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).upsert(records).execute()
                return response.data or records
            except Exception as e:
                logger.error(f"Error persisting batch schedule to Supabase: {e}")

        _LOCAL_SCHEDULES.extend(records)
        return records
