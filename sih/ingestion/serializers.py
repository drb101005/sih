from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MaintenanceTaskInput(BaseModel):
    task_id: str
    corridor_id: str
    chainage_km: float

    department: str
    task_type: str

    estimated_duration_minutes: int
    required_resources: str

    asset_criticality: str = "MEDIUM"
    defect_severity: str = "NONE"
    safety_impact: str = "MEDIUM"
    operational_impact: str = "MEDIUM"

    due_date: str
    overdue_days: float = 0.0

    allowed_start_time: str = "00:00:00"
    allowed_end_time: str = "00:00:00"

    required_isolation: str = "NONE"

    # Optional metadata fields
    asset_id: Optional[str] = None
    asset_type: Optional[str] = None
    defect_id: Optional[str] = "NONE"
    defect_information: Optional[str] = "NONE"
    save_to_db: bool = True


class CorridorCreateInput(BaseModel):
    corridor_id: str = Field(..., description="Unique corridor identifier (e.g. C040)")
    corridor_name: str = Field(..., description="Human-readable corridor name")
    zone: str = "Northern Railway"
    division: str = "Delhi Division"
    start_station: str
    end_station: str
    start_chainage_km: float = 0.0
    end_chainage_km: float
    track_type: str = "DOUBLE"
    electrification_type: str = "25KV_AC"
    traffic_density_class: str = "HIGH"
    status: str = "OPERATIONAL"  # 'OPERATIONAL', 'SPEED_RESTRICTION', 'MAINTENANCE_BLOCKED', 'CLOSED'
    speed_restriction_kmph: Optional[int] = None
    notes: Optional[str] = None


class CorridorUpdateInput(BaseModel):
    status: Optional[str] = Field(None, description="OPERATIONAL, SPEED_RESTRICTION, MAINTENANCE_BLOCKED, CLOSED")
    speed_restriction_kmph: Optional[int] = None
    notes: Optional[str] = None


class BatchScheduleRequest(BaseModel):
    corridor_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit_tasks: int = 500


class ScheduleResponse(BaseModel):
    success: bool
    schedule: Dict[str, Any]
    optimizer: Dict[str, Any]
    validation: Dict[str, Any]
    explanation_facts: Dict[str, Any]
