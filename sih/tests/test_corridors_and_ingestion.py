import pytest
from fastapi.testclient import TestClient
import pandas as pd

from database.repositories.corridor_repo import CorridorRepository
from database.seed_corridors import extract_corridors_from_data
from ingestion.pipeline import SupabaseIngestionPipeline
from api import app

client = TestClient(app)


def test_extract_corridors():
    corridors = extract_corridors_from_data("data")
    assert len(corridors) > 0
    c_ids = {c["corridor_id"] for c in corridors}
    assert "C040" in c_ids or "C005" in c_ids


def test_corridor_repository_crud():
    repo = CorridorRepository()
    test_c = {
        "corridor_id": "TEST_C999",
        "corridor_name": "Test High Speed Corridor",
        "start_station": "Station A",
        "end_station": "Station B",
        "start_chainage_km": 0.0,
        "end_chainage_km": 150.0,
        "status": "OPERATIONAL",
    }
    created = repo.create(test_c)
    assert created["corridor_id"] == "TEST_C999"

    fetched = repo.get_by_id("TEST_C999")
    assert fetched is not None
    assert fetched["status"] == "OPERATIONAL"

    updated = repo.update_status("TEST_C999", "SPEED_RESTRICTION", speed_restriction_kmph=60)
    assert updated["status"] == "SPEED_RESTRICTION"
    assert updated["speed_restriction_kmph"] == 60


def test_ingestion_single_task_scheduling():
    pipeline = SupabaseIngestionPipeline()
    task = {
        "task_id": "TEST-INT-001",
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
        "due_date": "2026-09-11",
        "overdue_days": 0,
        "allowed_start_time": "06:00:00",
        "allowed_end_time": "18:00:00",
        "required_isolation": "NONE",
    }

    result = pipeline.schedule_single_task(task, save_to_db=True)
    assert result["success"] is True
    assert "schedule" in result
    assert "explanation_facts" in result
    assert result["schedule"]["task_id"] == "TEST-INT-001"
    assert result["validation"]["valid"] is True


def test_blocked_corridor_rejection():
    repo = CorridorRepository()
    repo.upsert({
        "corridor_id": "BLOCKED_CORR",
        "corridor_name": "Blocked Corridor",
        "start_station": "A",
        "end_station": "B",
        "start_chainage_km": 0,
        "end_chainage_km": 100,
        "status": "CLOSED",
    })

    pipeline = SupabaseIngestionPipeline()
    task = {
        "task_id": "TEST-BLOCKED-001",
        "corridor_id": "BLOCKED_CORR",
        "chainage_km": 10.0,
        "department": "Signal",
        "task_type": "Telecommunication Cable Inspection",
        "estimated_duration_minutes": 55,
        "required_resources": "Signal_Team_08",
        "due_date": "2026-09-11",
    }

    with pytest.raises(ValueError, match="CLOSED"):
        pipeline.schedule_single_task(task)


def test_api_endpoints():
    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["service"] == "Railway Maintenance Optimizer API"

    # 2. Corridors API
    res = client.post("/corridors", json={
        "corridor_id": "API_CORR_1",
        "corridor_name": "API Express Line",
        "start_station": "Stn 1",
        "end_station": "Stn 2",
        "end_chainage_km": 120.0,
    })
    assert res.status_code == 200

    res = client.get("/corridors")
    assert res.status_code == 200
    assert res.json()["count"] >= 1

    res = client.patch("/corridors/API_CORR_1", json={
        "status": "SPEED_RESTRICTION",
        "speed_restriction_kmph": 45,
    })
    assert res.status_code == 200
    assert res.json()["corridor"]["speed_restriction_kmph"] == 45

    # 3. Schedule API
    task_payload = {
        "task_id": "API-TASK-001",
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
        "due_date": "2026-09-11",
        "allowed_start_time": "06:00:00",
        "allowed_end_time": "18:00:00",
        "required_isolation": "NONE",
    }
    res = client.post("/schedule", json=task_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["schedule"]["task_id"] == "API-TASK-001"
    assert "explanation_facts" in body
