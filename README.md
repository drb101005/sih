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

The `/schedule` endpoint accepts one new task. It rebuilds candidates from
`tasks.csv` + `blocks.csv` and returns the selected block plus structured
explanation facts. The LLM should explain these facts; it should not choose
the block.
