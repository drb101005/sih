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

## FastAPI Backend & Supabase Integration

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

### Environment Configuration (.env)

Create a `.env` file in the root or `sih/` folder:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-role-key
USE_LOCAL_FALLBACK=true
```

### Database Setup & Migration
1. Run [`database/schema.sql`](file:///c:/Users/USER/Desktop/SIH2026/sih/database/schema.sql) in your Supabase SQL Editor to create:
   - `corridors` (with speed restrictions, status, chainage limits)
   - `tasks` (with ML probability of failure & calculated priority)
   - `blocks` (maintenance windows & traffic metrics)
   - `schedules` (committed assignments & LLM explanation facts)

2. Seed initial corridors into Supabase:
```bash
python database/seed_corridors.py
```

### Endpoints
- `GET /` - Health check and Supabase connection status
- `GET /corridors` - List all corridors (supports `?status=OPERATIONAL`)
- `GET /corridors/{id}` - Inspect corridor details
- `POST /corridors` - Register new corridor
- `PATCH /corridors/{id}` - Update operational status / speed restrictions
- `POST /schedule` - Ingest single task -> ML Risk prediction -> CP-SAT schedule -> Supabase persistence + LLM Explanation facts
- `POST /schedule/batch` - Run batch optimizer across pending tasks in Supabase
- `GET /schedules` - Query committed schedules and validation statistics
- `GET /tasks` - List tasks from database
- `GET /blocks` - List maintenance blocks from database

