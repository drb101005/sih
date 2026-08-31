import os
import sys
from pathlib import Path
import pandas as pd

# Add sih directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.repositories.corridor_repo import CorridorRepository
from database.client import is_supabase_connected


def extract_corridors_from_data(data_dir: str = "data") -> list[dict]:
    """Extracts unique corridors and chainage ranges from blocks.csv and tasks.csv."""
    data_path = Path(data_dir)
    corridors = {}

    # Inspect blocks.csv
    blocks_path = data_path / "blocks.csv"
    if blocks_path.exists():
        df_blocks = pd.read_csv(blocks_path)
        for _, row in df_blocks.iterrows():
            cid = str(row.get("corridor_id", "")).strip()
            if not cid or cid == "nan":
                continue
            
            c_from = float(row.get("chainage_from_km", 0.0) or 0.0)
            c_to = float(row.get("chainage_to_km", 0.0) or 0.0)
            station = str(row.get("station", "Station"))

            if cid not in corridors:
                corridors[cid] = {
                    "corridor_id": cid,
                    "corridor_name": f"Corridor {cid} Main Line",
                    "zone": "Northern Railway",
                    "division": "Central Division",
                    "start_station": station,
                    "end_station": f"{station} Terminal",
                    "start_chainage_km": c_from,
                    "end_chainage_km": c_to,
                    "track_type": "DOUBLE",
                    "electrification_type": "25KV_AC",
                    "traffic_density_class": str(row.get("traffic_level", "HIGH")),
                    "status": "OPERATIONAL",
                    "speed_restriction_kmph": None,
                    "notes": "Auto-extracted from initial blocks schedule",
                }
            else:
                corridors[cid]["start_chainage_km"] = min(corridors[cid]["start_chainage_km"], c_from)
                corridors[cid]["end_chainage_km"] = max(corridors[cid]["end_chainage_km"], c_to)

    # Inspect tasks.csv
    tasks_path = data_path / "tasks.csv"
    if tasks_path.exists():
        df_tasks = pd.read_csv(tasks_path)
        for _, row in df_tasks.iterrows():
            cid = str(row.get("corridor_id", "")).strip()
            if not cid or cid == "nan":
                continue
            chainage = float(row.get("chainage_km", 0.0) or 0.0)
            if cid in corridors:
                corridors[cid]["start_chainage_km"] = min(corridors[cid]["start_chainage_km"], chainage)
                corridors[cid]["end_chainage_km"] = max(corridors[cid]["end_chainage_km"], chainage)

    return list(corridors.values())


def seed_corridors(data_dir: str = "data"):
    corridors = extract_corridors_from_data(data_dir)
    print(f"Found {len(corridors)} distinct corridors from data in '{data_dir}'.")
    
    repo = CorridorRepository()
    connected = is_supabase_connected()
    print(f"Supabase connection status: {'CONNECTED' if connected else 'OFFLINE (Local Memory Mode)'}")

    for c in corridors:
        repo.upsert(c)
        print(f"  - Seeded corridor: {c['corridor_id']} [{c['start_chainage_km']:.1f}km - {c['end_chainage_km']:.1f}km] -> {c['status']}")

    print(f"Successfully seeded {len(corridors)} corridors!")


if __name__ == "__main__":
    seed_corridors()
