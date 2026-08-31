import pandas as pd
from maintenance_optimizer.optimiser import Optimiser


blocks_df = pd.read_csv("data/blocks.csv")

optimizer = Optimiser(
    blocks=blocks_df
)


task = {
    "task_id": "TEST-001",
    "corridor_id": "C040",
    "chainage_km": 22.06,
    "department": "Signal",
    "task_type": "Telecommunication Cable Inspection",
    "estimated_duration_minutes": 55,
    "required_resources": "Signal_Team_08",

    "asset_criticality": "HIGH",
    "defect_severity": "NONE",
    "safety_impact": "HIGH",
    "operational_impact": "MEDIUM",

    "probability_of_failure": 0.8959,

    "due_date": "2026-09-11",
    "overdue_days": 0,

    "allowed_start_time": "06:00:00",
    "allowed_end_time": "18:00:00",
    "required_isolation": "NONE",
}


result = optimizer.schedule_task(task)

print("\n=== SINGLE TASK RESULT ===")
print(result)

#For batch testing

# import pandas as pd

# from maintenance_optimizer.optimiser import Optimiser


# # Load the production input data
# tasks_df = pd.read_csv("data/tasks.csv")
# blocks_df = pd.read_csv("data/blocks.csv")


# # Create optimizer
# optimizer = Optimiser(
#     tasks=tasks_df,
#     blocks=blocks_df
# )


# print("=== PREPARING BATCH CANDIDATES ===")

# candidates = optimizer.prepare_candidates()

# print(f"Candidate rows: {len(candidates)}")
# print(f"Candidate tasks: {candidates['task_id'].nunique()}")
# print(f"Candidate blocks: {candidates['block_id'].nunique()}")


# print("\n=== RUNNING BATCH OPTIMIZER ===")

# result = optimizer.schedule_batch()

# print("\n=== BATCH RESULT ===")

# # schedule_batch currently returns whatever CP_SATOptimizer.optimize()
# # returns, so handle both common forms.
# if isinstance(result, tuple):
#     schedule_df, solver_info = result

#     print("\nSolver:")
#     print(solver_info)

#     print("\nSchedule:")
#     print(schedule_df.to_string(index=False))

# else:
#     schedule_df = result

#     print(schedule_df.to_string(index=False))