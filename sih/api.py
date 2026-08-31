from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database.client import is_supabase_connected
from database.repositories import (
    CorridorRepository,
    TaskRepository,
    BlockRepository,
    ScheduleRepository,
)
from ingestion.pipeline import SupabaseIngestionPipeline
from ingestion.serializers import (
    MaintenanceTaskInput,
    CorridorCreateInput,
    CorridorUpdateInput,
    BatchScheduleRequest,
)

app = FastAPI(
    title="Railway Maintenance Optimizer & Supabase Ingestion API",
    description="Intelligent ML Risk & CP-SAT Constraint Optimization Backend with Supabase Integration",
    version="2.0.0",
)

# Allow CORS for Web Frontend / Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = SupabaseIngestionPipeline(max_time_seconds=120, workers=8)
corridor_repo = CorridorRepository()
task_repo = TaskRepository()
block_repo = BlockRepository()
schedule_repo = ScheduleRepository()


# -----------------------------------------------------------------------------
# System Health & Status
# -----------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": "Railway Maintenance Optimizer API",
        "supabase_connected": is_supabase_connected(),
        "version": "2.0.0",
    }


# -----------------------------------------------------------------------------
# Corridors Management Endpoints
# -----------------------------------------------------------------------------
@app.get("/corridors", tags=["Corridors"])
def list_corridors(status: Optional[str] = Query(None, description="Filter by status (e.g. OPERATIONAL, SPEED_RESTRICTION, CLOSED)")):
    """Lists all corridors stored in Supabase / local storage."""
    corridors = corridor_repo.get_all(status=status)
    return {
        "count": len(corridors),
        "corridors": corridors,
    }


@app.get("/corridors/{corridor_id}", tags=["Corridors"])
def get_corridor(corridor_id: str):
    """Retrieves metadata and current status for a specific corridor."""
    corridor = corridor_repo.get_by_id(corridor_id)
    if not corridor:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found.")
    return corridor


@app.post("/corridors", tags=["Corridors"])
def create_corridor(corridor: CorridorCreateInput):
    """Registers a new railway corridor in the database."""
    try:
        created = corridor_repo.create(corridor.model_dump())
        return {
            "success": True,
            "corridor": created,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/corridors/{corridor_id}", tags=["Corridors"])
def update_corridor_status(corridor_id: str, update: CorridorUpdateInput):
    """Updates operational status, speed restrictions, or maintenance notes for a corridor."""
    updated = corridor_repo.update_status(
        corridor_id=corridor_id,
        status=update.status or "OPERATIONAL",
        speed_restriction_kmph=update.speed_restriction_kmph,
        notes=update.notes,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found or could not be updated.")
    return {
        "success": True,
        "corridor": updated,
    }


# -----------------------------------------------------------------------------
# Scheduling & Optimization Endpoints
# -----------------------------------------------------------------------------
@app.post("/schedule", tags=["Optimizer"])
def schedule_single_task(task: MaintenanceTaskInput):
    """Ingests one maintenance task, predicts failure probability via ML model,

    optimizes the block assignment via CP-SAT, and persists to Supabase.
    """
    try:
        task_data = task.model_dump()
        result = pipeline.schedule_single_task(task_data, save_to_db=task.save_to_db)
        return result
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal scheduling error: {str(e)}")


@app.post("/schedule/batch", tags=["Optimizer"])
def run_batch_schedule(request: BatchScheduleRequest):
    """Ingests pending tasks from Supabase and executes batch CP-SAT optimization across corridors."""
    try:
        result = pipeline.run_batch_schedule(
            corridor_id=request.corridor_id,
            date_from=request.date_from,
            date_to=request.date_to,
            limit_tasks=request.limit_tasks,
            save_to_db=True,
        )
        return result
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch optimization error: {str(e)}")


# -----------------------------------------------------------------------------
# Schedule Queries & Database Inspections
# -----------------------------------------------------------------------------
@app.get("/schedules", tags=["Schedules"])
def get_schedules(
    corridor_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    block_id: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    """Fetches committed / optimized schedules from the database."""
    schedules = schedule_repo.get_schedules(
        corridor_id=corridor_id,
        task_id=task_id,
        block_id=block_id,
        limit=limit,
    )
    return {
        "count": len(schedules),
        "schedules": schedules,
    }


@app.get("/tasks", tags=["Tasks"])
def get_tasks(
    corridor_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Fetches tasks from the database."""
    tasks = task_repo.get_all(corridor_id=corridor_id, status=status, limit=limit)
    return {
        "count": len(tasks),
        "tasks": tasks,
    }


@app.get("/blocks", tags=["Blocks"])
def get_blocks(
    corridor_id: Optional[str] = Query(None),
    availability: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Fetches maintenance blocks from the database."""
    blocks = block_repo.get_all(corridor_id=corridor_id, availability=availability, limit=limit)
    return {
        "count": len(blocks),
        "blocks": blocks,
    }
