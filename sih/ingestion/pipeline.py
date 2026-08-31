import logging
from typing import Optional, Dict, Any, List
import pandas as pd

from database.repositories import (
    CorridorRepository,
    TaskRepository,
    BlockRepository,
    ScheduleRepository,
)
from maintenance_optimizer.optimiser import Optimiser
from maintenance_optimizer.validator import validate_schedule
from model import predict_probability_of_failure

logger = logging.getLogger(__name__)


class SupabaseIngestionPipeline:
    def __init__(self, max_time_seconds: int = 120, workers: int = 8):
        self.corridor_repo = CorridorRepository()
        self.task_repo = TaskRepository()
        self.block_repo = BlockRepository()
        self.schedule_repo = ScheduleRepository()
        self.max_time_seconds = max_time_seconds
        self.workers = workers

    def schedule_single_task(self, task_data: Dict[str, Any], save_to_db: bool = True) -> Dict[str, Any]:
        """Ingests a single raw task, runs ML risk prediction, optimizes block assignment,

        and updates Supabase tables.
        """
        task = dict(task_data)
        corridor_id = task.get("corridor_id")

        # 1. Corridor status check
        corridor = self.corridor_repo.get_by_id(corridor_id)
        if corridor:
            c_status = str(corridor.get("status", "OPERATIONAL")).upper()
            if c_status in ("CLOSED", "MAINTENANCE_BLOCKED"):
                raise ValueError(
                    f"Corridor '{corridor_id}' is currently '{c_status}'. "
                    f"New maintenance tasks cannot be scheduled on this corridor."
                )

        # 2. Run ML Failure Probability Prediction if not provided
        if "probability_of_failure" not in task or task["probability_of_failure"] is None:
            task["probability_of_failure"] = predict_probability_of_failure(task)

        # 3. Fetch available blocks from Supabase (filtered by corridor)
        blocks_data = self.block_repo.get_available_blocks(corridor_id=corridor_id)
        if not blocks_data:
            # Try fetching all available blocks as fallback
            blocks_data = self.block_repo.get_available_blocks()

        if not blocks_data:
            raise ValueError(f"No available maintenance blocks found for corridor '{corridor_id}'.")

        blocks_df = pd.DataFrame(blocks_data)

        # 4. Instantiate Optimiser and schedule task
        optimiser = Optimiser(
            blocks=blocks_df,
            max_time_seconds=self.max_time_seconds,
            workers=self.workers,
        )

        schedule_df, optimizer_meta = optimiser.schedule_task(task)
        if schedule_df.empty:
            raise RuntimeError(f"Optimizer found no feasible block slot for task '{task.get('task_id')}'.")

        validation = validate_schedule(schedule_df)
        row = schedule_df.iloc[0].to_dict()

        # 5. Build structured explanation facts for LLM / Frontend
        explanation_facts = {
            k: row.get(k)
            for k in [
                "task_id",
                "block_id",
                "corridor_id",
                "final_score",
                "priority_score",
                "priority_class",
                "probability_of_failure",
                "duration_fit",
                "cost_score",
                "goods_score",
                "train_conflict_score",
                "resource_score",
                "operational_cost",
                "goods_impact_score",
                "conflicting_trains",
                "conflict_severity",
                "resource_count",
                "max_resources",
                "scheduled_start",
                "scheduled_end",
            ]
            if k in row
        }

        # 6. Save results back to Supabase if requested
        if save_to_db:
            try:
                # Save schedule record
                self.schedule_repo.save_single(row, explanation_facts=explanation_facts)

                # Upsert task with updated priority and status
                self.task_repo.update_status(
                    task_id=task.get("task_id"),
                    status="SCHEDULED",
                    probability_of_failure=task.get("probability_of_failure"),
                    priority_score=row.get("priority_score"),
                    priority_class=row.get("priority_class"),
                )
            except Exception as e:
                logger.error(f"Error persisting single schedule to database: {e}")

        return {
            "success": True,
            "schedule": row,
            "optimizer": optimizer_meta,
            "validation": validation,
            "explanation_facts": explanation_facts,
        }

    def run_batch_schedule(
        self,
        corridor_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit_tasks: int = 500,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """Ingests pending tasks and available blocks from Supabase, runs batch ML + CP-SAT,

        and updates Supabase.
        """
        # 1. Fetch pending tasks
        tasks_data = self.task_repo.get_pending_tasks(corridor_id=corridor_id, limit=limit_tasks)
        if not tasks_data:
            # Fallback to all tasks if no PENDING status explicitly marked
            tasks_data = self.task_repo.get_all(corridor_id=corridor_id, limit=limit_tasks)

        if not tasks_data:
            raise ValueError(f"No tasks available for batch scheduling (corridor={corridor_id}).")

        # 2. Check corridor availability
        active_corridors = {
            c["corridor_id"]: c for c in self.corridor_repo.get_all()
        }

        valid_tasks = []
        for t in tasks_data:
            cid = t.get("corridor_id")
            if cid in active_corridors:
                c_status = str(active_corridors[cid].get("status", "OPERATIONAL")).upper()
                if c_status in ("CLOSED", "MAINTENANCE_BLOCKED"):
                    continue  # Skip tasks on blocked corridors
            
            # Predict ML probability if missing
            if "probability_of_failure" not in t or pd.isna(t.get("probability_of_failure")):
                t["probability_of_failure"] = predict_probability_of_failure(t)
            valid_tasks.append(t)

        if not valid_tasks:
            raise ValueError("No eligible tasks after corridor status filtering.")

        tasks_df = pd.DataFrame(valid_tasks)

        # 3. Fetch available blocks
        blocks_data = self.block_repo.get_available_blocks(
            corridor_id=corridor_id, date_from=date_from, date_to=date_to
        )
        if not blocks_data:
            raise ValueError(f"No available blocks found for batch scheduling (corridor={corridor_id}).")

        blocks_df = pd.DataFrame(blocks_data)

        # 4. Fetch existing committed schedules
        existing_schedules = self.schedule_repo.get_schedules(corridor_id=corridor_id)
        existing_df = pd.DataFrame(existing_schedules) if existing_schedules else pd.DataFrame()

        # 5. Run Batch Optimiser
        optimiser = Optimiser(
            tasks=tasks_df,
            blocks=blocks_df,
            existing_schedule=existing_df if not existing_df.empty else None,
            max_time_seconds=self.max_time_seconds,
            workers=self.workers,
        )

        schedule_df, optimizer_meta = optimiser.schedule_batch()
        validation = validate_schedule(schedule_df)

        # 6. Save batch results back to Supabase
        if save_to_db and not schedule_df.empty:
            try:
                self.schedule_repo.save_batch(schedule_df)
                for tid in schedule_df["task_id"].unique():
                    self.task_repo.update_status(task_id=tid, status="SCHEDULED")
            except Exception as e:
                logger.error(f"Error persisting batch schedule to database: {e}")

        return {
            "success": True,
            "total_tasks_evaluated": len(tasks_df),
            "total_tasks_scheduled": len(schedule_df),
            "schedule": schedule_df.head(100).to_dict(orient="records"),
            "optimizer": optimizer_meta,
            "validation": validation,
        }
