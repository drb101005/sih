"""Repositories for accessing Supabase tables."""
from .corridor_repo import CorridorRepository
from .task_repo import TaskRepository
from .block_repo import BlockRepository
from .schedule_repo import ScheduleRepository

__all__ = [
    "CorridorRepository",
    "TaskRepository",
    "BlockRepository",
    "ScheduleRepository",
]
