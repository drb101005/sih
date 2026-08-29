import pandas as pd

def validate_schedule(schedule):
    required = [
        "task_id","block_id","scheduled_start","scheduled_end",
        "estimated_duration_minutes","required_resources",
        "resource_count","max_resources"
    ]
    missing = [c for c in required if c not in schedule.columns]
    if missing:
        return {"valid": False, "errors": [f"Missing columns: {missing}"]}

    df = schedule.copy()
    df["scheduled_start"] = pd.to_datetime(df["scheduled_start"])
    df["scheduled_end"] = pd.to_datetime(df["scheduled_end"])
    errors = []

    if df["task_id"].duplicated().any(): errors.append("Duplicate task assignments.")
    if df[["task_id","block_id"]].duplicated().any():
        errors.append("Duplicate task-block assignments.")

    actual = (df["scheduled_end"] - df["scheduled_start"]).dt.total_seconds()/60
    if (actual - df["estimated_duration_minutes"]).abs().gt(0.01).any():
        errors.append("Duration violation.")
    if df["required_resources"].isna().any(): errors.append("Missing resources.")

    usage = []
    for _, row in df.iterrows():
        for r in str(row["required_resources"]).split(";"):
            r = r.strip()
            if r and r.lower() != "nan":
                usage.append({
                    "resource": r, "task_id": row["task_id"],
                    "start": row["scheduled_start"], "end": row["scheduled_end"]
                })

    conflicts = 0
    if usage:
        u = pd.DataFrame(usage)
        for _, g in u.groupby("resource"):
            rows = g.sort_values("start").to_dict("records")
            for i in range(len(rows)):
                for j in range(i+1, len(rows)):
                    if rows[j]["start"] < rows[i]["end"] and rows[j]["end"] > rows[i]["start"]:
                        conflicts += 1
    if conflicts: errors.append(f"Physical resource conflicts: {conflicts}")

    return {
        "valid": not errors, "errors": errors,
        "scheduled_rows": len(df),
        "unique_tasks": df["task_id"].nunique(),
        "unique_blocks": df["block_id"].nunique(),
        "resource_conflicts": conflicts
    }
