import math
import pandas as pd
from ortools.sat.python import cp_model

class CP_SATOptimizer:
    TIME_UNIT = 5

    def __init__(self, max_time_seconds=600, workers=8):
        self.max_time_seconds = max_time_seconds
        self.workers = workers

    @staticmethod
    def _resources(value):
        if pd.isna(value): return []
        return [x.strip() for x in str(value).split(";") if x.strip()]

    def _build_model(self, opt):
        model = cp_model.CpModel()
        vars_ = {i: model.NewBoolVar(f"x_{i}") for i in opt.index}

        for _, group in opt.groupby("task_id"):
            model.Add(sum(vars_[i] for i in group.index) <= 1)

        origin = opt["block_start"].min()
        opt = opt.copy()
        opt["duration_units"] = (
            opt["estimated_duration_minutes"] / self.TIME_UNIT
        ).apply(math.ceil).astype(int)
        opt["block_start_units"] = (
            (opt["block_start"] - origin).dt.total_seconds() / 60 / self.TIME_UNIT
        ).astype(int)
        opt["block_end_units"] = (
            (opt["block_end"] - origin).dt.total_seconds() / 60 / self.TIME_UNIT
        ).astype(int)

        starts, ends, intervals = {}, {}, {}
        for i in opt.index:
            bs, be = int(opt.at[i,"block_start_units"]), int(opt.at[i,"block_end_units"])
            dur = int(opt.at[i,"duration_units"])
            if be - bs < dur:
                raise ValueError(f"Candidate {i} does not fit its block.")
            starts[i] = model.NewIntVar(bs, be-dur, f"start_{i}")
            ends[i] = model.NewIntVar(bs+dur, be, f"end_{i}")
            model.Add(ends[i] == starts[i] + dur)
            intervals[i] = model.NewOptionalIntervalVar(
                starts[i], dur, ends[i], vars_[i], f"interval_{i}"
            )

        for _, group in opt.groupby("block_id"):
            ids = list(group.index)
            if len(ids) <= 1: continue
            model.AddCumulative(
                [intervals[i] for i in ids],
                [int(opt.at[i,"resource_count"]) for i in ids],
                int(opt.loc[ids,"max_resources"].min())
            )

        resource_map = {}
        for i in opt.index:
            for r in self._resources(opt.at[i,"required_resources"]):
                resource_map.setdefault(r, []).append(intervals[i])

        for ints in resource_map.values():
            if len(ints) > 1:
                model.AddNoOverlap(ints)

        return model, vars_, starts, ends, origin, opt

    def _stage(self, opt, priority, locks=None):
        model, vars_, starts, ends, origin, opt = self._build_model(opt)

        if locks:
            for i, v in locks.items():
                model.Add(vars_[i] == v)

        ids = [
            i for i in opt.index
            if str(opt.at[i,"priority_class"]).upper() == priority
        ]
        model.Maximize(sum(vars_[i] for i in ids))

        validation = model.Validate()
        if validation:
            raise RuntimeError(f"Invalid {priority} model: {validation}")

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_time_seconds
        solver.parameters.num_search_workers = self.workers
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(
                f"{priority} stage failed: {solver.StatusName(status)}"
            )

        selected = {i: int(solver.Value(vars_[i])) for i in opt.index}
        return {
            "selected": selected, "count": sum(selected[i] for i in ids),
            "solver": solver, "vars": vars_, "starts": starts,
            "ends": ends, "origin": origin, "opt": opt,
            "status": solver.StatusName(status),
            "best_bound": solver.BestObjectiveBound()
        }

    def optimize(self, candidates):
        opt = candidates.copy().reset_index(drop=True)
        required = [
            "task_id","block_id","block_start","block_end",
            "estimated_duration_minutes","duration_minutes",
            "resource_count","max_resources","required_resources",
            "priority_score","priority_class","final_score"
        ]
        missing = [c for c in required if c not in opt.columns]
        if missing: raise ValueError(f"Optimizer candidates missing: {missing}")

        opt["block_start"] = pd.to_datetime(opt["block_start"])
        opt["block_end"] = pd.to_datetime(opt["block_end"])
        for c in [
            "estimated_duration_minutes","duration_minutes",
            "resource_count","max_resources","priority_score","final_score"
        ]:
            opt[c] = pd.to_numeric(opt[c], errors="coerce")
        opt = opt.dropna(subset=[
            "task_id","block_id","block_start","block_end",
            "estimated_duration_minutes","resource_count",
            "max_resources","priority_score"
        ])
        opt = opt[
            (opt["estimated_duration_minutes"] <= opt["duration_minutes"]) &
            (opt["resource_count"] <= opt["max_resources"])
        ].reset_index(drop=True)
        if opt.empty: raise ValueError("No feasible candidates.")

        s1 = self._stage(opt, "CRITICAL")
        s2 = self._stage(opt, "HIGH", s1["selected"])
        s3 = self._stage(opt, "MEDIUM", s2["selected"])
        s4 = self._stage(opt, "LOW", s3["selected"])

        ids = [i for i,v in s4["selected"].items() if v == 1]
        result = opt.loc[ids].copy()
        result["scheduled_start"] = [
            s4["origin"] + pd.to_timedelta(
                s4["solver"].Value(s4["starts"][i]) * self.TIME_UNIT, unit="m"
            ) for i in ids
        ]
        result["scheduled_end"] = [
            s4["origin"] + pd.to_timedelta(
                s4["solver"].Value(s4["ends"][i]) * self.TIME_UNIT, unit="m"
            ) for i in ids
        ]

        return result.reset_index(drop=True), {
            "critical": s1["count"], "high": s2["count"],
            "medium": s3["count"], "low": sum(
                s4["selected"][i] for i in opt.index
                if str(opt.at[i,"priority_class"]).upper() == "LOW"
            ),
            "status": s4["status"], "best_bound": s4["best_bound"]
        }

    def schedule_single(self, candidates):
        opt = candidates.copy().reset_index(drop=True)
        if opt.empty: raise ValueError("No feasible candidates.")
        if opt["task_id"].nunique() != 1:
            raise ValueError("schedule_single expects exactly one task.")

        model, vars_, starts, ends, origin, opt = self._build_model(opt)
        model.Maximize(sum(
            int(round(float(opt.at[i,"final_score"]) * 1_000_000)) * vars_[i]
            for i in opt.index
        ))
        if model.Validate():
            raise RuntimeError(f"Invalid single-task model: {model.Validate()}")

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_time_seconds
        solver.parameters.num_search_workers = self.workers
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(f"Single-task solve failed: {solver.StatusName(status)}")

        ids = [i for i in opt.index if solver.Value(vars_[i]) == 1]
        if not ids: raise RuntimeError("Solver selected no candidate.")
        i = ids[0]

        result = opt.loc[[i]].copy()
        result["scheduled_start"] = origin + pd.to_timedelta(
            solver.Value(starts[i]) * self.TIME_UNIT, unit="m"
        )
        result["scheduled_end"] = origin + pd.to_timedelta(
            solver.Value(ends[i]) * self.TIME_UNIT, unit="m"
        )
        return result.reset_index(drop=True), {
            "status": solver.StatusName(status),
            "objective": solver.ObjectiveValue()
        }
