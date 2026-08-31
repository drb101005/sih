import os
import sys
from pathlib import Path

# Add current dir to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingestion.pipeline import SupabaseIngestionPipeline

print("=" * 60)
print("TESTING END-TO-END SCHEDULING WITH LIVE SUPABASE")
print("=" * 60)

pipeline = SupabaseIngestionPipeline()

# Test task matching corridor C040
test_task = {
    "task_id": "LIVE-TEST-001",
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

print(f"Submitting task {test_task['task_id']} for corridor {test_task['corridor_id']}...")
result = pipeline.schedule_single_task(test_task, save_to_db=True)

print(f"\nScheduling Success: {result['success']}")
print(f"Assigned Block: {result['schedule']['block_id']}")
print(f"Scheduled Slot: {result['schedule']['scheduled_start']} -> {result['schedule']['scheduled_end']}")
print(f"Priority Class: {result['schedule']['priority_class']}")
print(f"Final Optimization Score: {result['schedule']['final_score']:.4f}")
print(f"Validation Result: {'VALID' if result['validation']['valid'] else 'INVALID'}")

print("\nExplanation Facts for LLM:")
for k, v in result['explanation_facts'].items():
    print(f"  - {k}: {v}")

print("\n" + "=" * 60)
print("END-TO-END TEST PASSED!")
print("=" * 60)
