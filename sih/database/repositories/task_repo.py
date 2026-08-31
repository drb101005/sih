import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from ..client import get_supabase_client
from ..config import settings

logger = logging.getLogger(__name__)


class TaskRepository:
    def __init__(self):
        # Matches exact Supabase table name: maintenance_tasks
        self.table_name = "maintenance_tasks"

    def get_pending_tasks(self, corridor_id: Optional[str] = None, limit: int = 2000) -> List[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                query = client.table(self.table_name).select("*").eq("status", "PENDING")
                if corridor_id:
                    query = query.eq("corridor_id", corridor_id)
                response = query.limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching pending tasks from Supabase: {e}")

        # Local CSV Fallback
        if settings.USE_LOCAL_FALLBACK:
            csv_path = Path(settings.DATA_DIR) / "tasks.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                if "status" in df.columns:
                    df = df[df["status"].str.upper() == "PENDING"]
                if corridor_id and "corridor_id" in df.columns:
                    df = df[df["corridor_id"] == corridor_id]
                return df.head(limit).to_dict(orient="records")
        return []

    def get_all(self, corridor_id: Optional[str] = None, status: Optional[str] = None, limit: int = 2000) -> List[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                query = client.table(self.table_name).select("*")
                if corridor_id:
                    query = query.eq("corridor_id", corridor_id)
                if status:
                    query = query.eq("status", status)
                response = query.limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching tasks from Supabase: {e}")

        # Local CSV Fallback
        if settings.USE_LOCAL_FALLBACK:
            csv_path = Path(settings.DATA_DIR) / "tasks.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                if corridor_id and "corridor_id" in df.columns:
                    df = df[df["corridor_id"] == corridor_id]
                if status and "status" in df.columns:
                    df = df[df["status"].str.upper() == status.upper()]
                return df.head(limit).to_dict(orient="records")
        return []

    def get_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).select("*").eq("task_id", task_id).execute()
                if response.data:
                    return response.data[0]
                return None
            except Exception as e:
                logger.error(f"Error fetching task {task_id} from Supabase: {e}")

        if settings.USE_LOCAL_FALLBACK:
            csv_path = Path(settings.DATA_DIR) / "tasks.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                row = df[df["task_id"] == task_id]
                if not row.empty:
                    return row.iloc[0].to_dict()
        return None

    def create(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        tid = task_data.get("task_id")
        if not tid:
            raise ValueError("task_id is required.")

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).insert(task_data).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error inserting task {tid} into Supabase: {e}")
                raise e
        return task_data

    def update_status(
        self,
        task_id: str,
        status: str,
        probability_of_failure: Optional[float] = None,
        priority_score: Optional[float] = None,
        priority_class: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        update_data: Dict[str, Any] = {"status": status}
        if probability_of_failure is not None:
            update_data["probability_of_failure"] = probability_of_failure
        if priority_score is not None:
            update_data["priority_score"] = priority_score
        if priority_class is not None:
            update_data["priority_class"] = priority_class

        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).update(update_data).eq("task_id", task_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error updating task {task_id} in Supabase: {e}")
        return None

    def upsert_batch(self, tasks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tasks_data:
            return []
        client = get_supabase_client()
        if client is not None:
            try:
                response = client.table(self.table_name).upsert(tasks_data).execute()
                return response.data or []
            except Exception as e:
                logger.error(f"Error bulk upserting tasks in Supabase: {e}")
        return tasks_data
