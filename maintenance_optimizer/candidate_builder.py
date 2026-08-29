import pandas as pd
from .preprocessing import (
    prepare_tasks, prepare_blocks,
    isolation_compatible, time_window_compatible
)
from .scoring import add_scores

class CandidateBuilder:
    def build(self, tasks, blocks):
        tasks, blocks = prepare_tasks(tasks), prepare_blocks(blocks)

        pairs = tasks[[
            "task_id","corridor_id","chainage_km",
            "estimated_duration_minutes","department","isolation_set",
            "has_time_restriction","allowed_start","allowed_end",
            "priority_score","probability_of_failure","overdue_days",
            "required_resources","resource_set","resource_count",
            "priority_class","required_isolation"
        ]].merge(
            blocks[[
                "block_id","corridor_id","chainage_from_km","chainage_to_km",
                "duration_minutes","start_time","end_time","availability",
                "max_resources","operational_cost","traffic_level",
                "goods_impact_score","expected_goods_trains",
                "conflicting_trains","conflict_severity",
                "allowed_department_set","isolation_set"
            ]],
            on="corridor_id", how="inner",
            suffixes=("_task","_block")
        )

        pairs = pairs[
            (pairs["chainage_km"] >= pairs["chainage_from_km"]) &
            (pairs["chainage_km"] <= pairs["chainage_to_km"]) &
            (pairs["estimated_duration_minutes"] <= pairs["duration_minutes"])
        ].copy()

        pairs["department_compatible"] = pairs.apply(
            lambda r: r["department"] in r["allowed_department_set"], axis=1
        )
        pairs["isolation_compatible"] = pairs.apply(
            lambda r: isolation_compatible(
                r["isolation_set_task"], r["isolation_set_block"]
            ), axis=1
        )
        pairs = pairs[
            pairs["department_compatible"] & pairs["isolation_compatible"]
        ].copy()

        pairs["time_compatible"] = pairs.apply(
            lambda r: time_window_compatible(
                r["start_time"], r["end_time"],
                r["allowed_start"], r["allowed_end"],
                r["has_time_restriction"]
            ), axis=1
        )
        pairs = pairs[pairs["time_compatible"]].copy()
        pairs["block_start"] = pairs["start_time"]
        pairs["block_end"] = pairs["end_time"]

        return add_scores(pairs).reset_index(drop=True)
