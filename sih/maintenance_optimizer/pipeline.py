from .data_loader import DataLoader
from .optimiser import Optimiser
from .validator import validate_schedule

class OptimisationPipeline:
    def __init__(self, data_dir="data", max_time_seconds=600, workers=8):
        self.loader = DataLoader(data_dir)
        self.max_time_seconds = max_time_seconds
        self.workers = workers

    def optimiser(self):
        return Optimiser(
            tasks=self.loader.tasks(),
            blocks=self.loader.blocks(),
            existing_schedule=self.loader.schedule(),
            max_time_seconds=self.max_time_seconds,
            workers=self.workers,
        )

    def schedule_task(self, task):
        o = self.optimiser()
        schedule, meta = o.schedule_task(task)
        return {
            "schedule": schedule,
            "optimizer": meta,
            "validation": validate_schedule(schedule)
        }

    def run_batch(self):
        o = self.optimiser()
        schedule, meta = o.schedule_batch()
        return {
            "schedule": schedule,
            "optimizer": meta,
            "validation": validate_schedule(schedule)
        }
