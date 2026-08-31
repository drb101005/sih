# Maintenance Optimizer

Production Python refactor of the final CP-SAT scheduling logic in `sih(2).ipynb`.

## Correct notebook artifacts

`data/tasks.csv` must be the notebook's **tasks_df**, not `canonical_tasks`.
`data/blocks.csv` must be the final `usable_blocks_df`.
`data/schedule.csv` is the existing committed schedule.
`data/candidates.csv` is a reference/regression artifact.
`trains.csv` and `forecasts.csv` are retained source artifacts.

## Notebook logic reproduced

Candidate generation:
1. corridor match
2. chainage containment
3. duration fit
4. department compatibility
5. isolation compatibility
6. time-window compatibility
7. resource feasibility

Scores:
- duration_fit
- cost_score
- goods_score
- train_conflict_score
- resource_score
- final_score

CP-SAT:
- at most one candidate per task
- optional 5-minute intervals
- block cumulative resource capacity
- physical resource NoOverlap
- lexicographic optimization:
  CRITICAL -> HIGH -> MEDIUM -> LOW

The stage optimum is calculated dynamically rather than hard-coded.

## Run

```bash
pip install -r requirements.txt
```

## FastAPI

```bash
uvicorn api:app --reload
```

Open Swagger UI at `http://127.0.0.1:8000/docs`.

### `POST /schedule`

The endpoint accepts one new task, predicts its failure probability with
`risk_model_v3_50.pkl`, rebuilds candidates from `tasks.csv` and `blocks.csv`,
and returns the selected block plus explanation facts.

Do not send `probability_of_failure`; the API derives it from these model
inputs:

- `defect_severity`, `safety_impact`, `operational_impact`, `asset_criticality`
- `department`, `task_type`
- `overdue_days`, `estimated_duration_minutes`, `chainage_km`

The successful response includes `predicted_probability_of_failure`,
`schedule`, `optimizer`, `validation`, and `explanation_facts`.

The LLM should explain these facts; it should not choose the block.
