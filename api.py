from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from maintenance_optimizer.pipeline import OptimisationPipeline
from model import predict_probability_of_failure

app = FastAPI(title="Maintenance Optimizer API")
pipeline = OptimisationPipeline("data", max_time_seconds=120, workers=8)


class MaintenanceTask(BaseModel):
    task_id: str
    corridor_id: str
    chainage_km: float

    department: str
    task_type: str

    estimated_duration_minutes: int
    required_resources: str

    asset_criticality: str
    defect_severity: str
    safety_impact: str
    operational_impact: str

    due_date: str
    overdue_days: float = 0

    allowed_start_time: str = "00:00:00"
    allowed_end_time: str = "00:00:00"

    required_isolation: str = "NONE"
@app.post("/schedule")
def schedule(task: MaintenanceTask):
    try:
        task_data = task.model_dump()
        predicted_probability_of_failure = predict_probability_of_failure(task_data)
        task_data["probability_of_failure"] = predicted_probability_of_failure
        result = pipeline.schedule_task(task_data)
        row = result["schedule"].iloc[0].to_dict()
        return {
            "success": True,
            "predicted_probability_of_failure": predicted_probability_of_failure,
            "schedule": row,
            "optimizer": result["optimizer"],
            "validation": result["validation"],
            "explanation_facts": {
                k: row.get(k) for k in [
                    "block_id","final_score","priority_score","priority_class",
                    "duration_fit","cost_score","goods_score",
                    "train_conflict_score","resource_score",
                    "operational_cost","goods_impact_score",
                    "conflicting_trains","conflict_severity",
                    "resource_count","max_resources"
                ]
            }
        }
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
