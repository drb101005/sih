import pandas as pd
from .candidate_builder import CandidateBuilder
from .optimizer import CP_SATOptimizer
from .preprocessing import prepare_tasks, prepare_blocks
from .task_scoring import TaskScorer

class Optimiser:
    def __init__(self, tasks=None, blocks=None, existing_schedule=None,
                 max_time_seconds=600, workers=8):
        self.tasks = prepare_tasks(tasks) if tasks is not None else None
        self.blocks = prepare_blocks(blocks) if blocks is not None else None
        self.existing_schedule = existing_schedule
        self.builder = CandidateBuilder()
        self.optimizer = CP_SATOptimizer(max_time_seconds, workers)
        self.task_scorer = TaskScorer()

    def prepare_candidates(self, tasks=None):
        if self.tasks is None or self.blocks is None:
            raise ValueError("tasks and blocks are required.")
        task_df = self.tasks if tasks is None else prepare_tasks(tasks)
        return self.builder.build(task_df, self.blocks)

    def schedule_task(self, task):
        if isinstance(task, dict):
            task_df = pd.DataFrame([task])
        elif isinstance(task, pd.DataFrame):
            task_df = task.copy()
        else:
            raise ValueError("task must be a dict or DataFrame")

        if len(task_df) != 1:
            raise ValueError(
            "schedule_task expects exactly one task."
            )

    # 1. RAW TASK
    # 2. DERIVE PRIORITY FIELDS
        task_df = self.task_scorer.score(task_df)

    # 3. BUILD FEASIBLE BLOCK CANDIDATES
        candidates = self.builder.build(
        task_df,
        self.blocks
        )

    # 4. RUN CP-SAT
        return self.optimizer.schedule_single(candidates)

    def schedule_batch(self, tasks=None):
        candidates = self.prepare_candidates(tasks)
        return self.optimizer.optimize(candidates)
