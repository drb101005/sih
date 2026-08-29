import numpy as np

def add_scores(candidates):
    df = candidates.copy()

    df["maintenance_benefit"] = df["priority_score"] * (1 + df["probability_of_failure"])
    df["unused_block_minutes"] = df["duration_minutes"] - df["estimated_duration_minutes"]
    df["unused_block_ratio"] = (
        df["unused_block_minutes"] /
        df["duration_minutes"].replace(0, np.nan)
    )

    df["duration_fit"] = (
        df["estimated_duration_minutes"] /
        df["duration_minutes"].replace(0, np.nan)
    ).clip(0, 1).fillna(0)

    lo, hi = df["operational_cost"].min(), df["operational_cost"].max()
    df["cost_score"] = (
        1.0 if hi == lo else
        (1 - (df["operational_cost"] - lo) / (hi - lo)).clip(0, 1)
    )

    goods_max = df["goods_impact_score"].max()
    df["goods_impact_score_normalized"] = (
        0.0 if goods_max == 0 else df["goods_impact_score"] / goods_max
    )
    df["goods_score"] = (1 - df["goods_impact_score_normalized"]).clip(0, 1)

    df["train_conflict_score"] = (
        0.6 * df["conflict_severity"] / 8 +
        0.4 * df["conflicting_trains"] / 3
    ).clip(0, 1)

    df["resource_feasible"] = df["resource_count"] <= df["max_resources"]
    df = df[df["resource_feasible"]].copy()

    df["resource_score"] = (
        1 - df["resource_count"] /
        df["max_resources"].replace(0, np.nan)
    ).clip(0, 1).fillna(0)

    df["final_score"] = (
        0.30 * df["priority_score"] +
        0.15 * df["duration_fit"] +
        0.15 * df["cost_score"] +
        0.15 * df["goods_score"] +
        0.15 * (1 - df["train_conflict_score"]) +
        0.10 * df["resource_score"]
    )
    return df
