from datetime import datetime
import pandas as pd

def parse_resources(value):
    if pd.isna(value): return set()
    return {x.strip() for x in str(value).split(";") if x.strip()}

def parse_departments(value):
    if pd.isna(value): return set()
    return {x.strip() for x in str(value).split(";") if x.strip()}

def parse_isolation(value):
    if pd.isna(value): return set()
    value = str(value).strip().upper()
    if value in ("", "NONE"): return set()
    if value == "ALL": return {"TRACK", "OHE", "SIGNAL"}
    return {x.strip() for x in value.split("+") if x.strip()}

def parse_time(value):
    if pd.isna(value): return None
    if hasattr(value, "hour"): return value
    return datetime.strptime(str(value), "%H:%M:%S").time()

def isolation_compatible(task_isolation, block_isolation):
    if not task_isolation: return True
    if block_isolation == {"TRACK", "OHE", "SIGNAL"}: return True
    return task_isolation.issubset(block_isolation)

def time_window_compatible(block_start, block_end, allowed_start, allowed_end, has_restriction):
    if not has_restriction: return True
    bs, be = block_start.time(), block_end.time()
    if allowed_start <= allowed_end:
        return bs >= allowed_start and be <= allowed_end
    return bs >= allowed_start or be <= allowed_end

def prepare_tasks(tasks):
    df = tasks.copy()
    required = [
        "task_id","corridor_id","chainage_km","department",
        "estimated_duration_minutes","required_resources",
        "required_isolation","priority_score","probability_of_failure",
        "due_date","allowed_start_time","allowed_end_time"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing: raise ValueError(f"tasks.csv is missing columns: {missing}")

    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
    df["resource_set"] = df["required_resources"].apply(parse_resources)
    df["resource_count"] = df["resource_set"].apply(len)
    df["isolation_set"] = df["required_isolation"].apply(parse_isolation)
    df["allowed_start"] = df["allowed_start_time"].apply(parse_time)
    df["allowed_end"] = df["allowed_end_time"].apply(parse_time)
    df["has_time_restriction"] = ~(
        (df["allowed_start_time"].astype(str) == "00:00:00") &
        (df["allowed_end_time"].astype(str) == "00:00:00")
    )
    return df

def prepare_blocks(blocks):
    df = blocks.copy()
    required = [
        "block_id","corridor_id","chainage_from_km","chainage_to_km",
        "start_time","end_time","duration_minutes","availability",
        "allowed_departments","isolation_required","max_resources",
        "operational_cost"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing: raise ValueError(f"blocks is missing required columns: {missing}")

    # Set default values for optional traffic & impact scores if not in table
    for opt_col in ["goods_impact_score", "conflicting_trains", "conflict_severity", "expected_goods_trains"]:
        if opt_col not in df.columns:
            df[opt_col] = 0.0
    if "traffic_level" not in df.columns:
        df["traffic_level"] = "MEDIUM"

    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce")
    df = df[df["availability"].isin(["AVAILABLE","PROVISIONAL"])].copy()
    df["allowed_department_set"] = df["allowed_departments"].apply(parse_departments)
    df["isolation_set"] = df["isolation_required"].apply(parse_isolation)

    for c in ["duration_minutes","max_resources","operational_cost",
              "goods_impact_score","conflicting_trains","conflict_severity"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

