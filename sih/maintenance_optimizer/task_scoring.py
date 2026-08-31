import pandas as pd
import numpy as np


class TaskScorer:

    CRITICALITY_MAP = {
        "LOW": 0.25,
        "MEDIUM": 0.50,
        "HIGH": 0.75,
        "CRITICAL": 1.00,
    }

    SEVERITY_MAP = {
        "NONE": 0.00,
        "LOW": 0.25,
        "MEDIUM": 0.50,
        "HIGH": 0.75,
        "CRITICAL": 1.00,
    }

    def score(self, tasks: pd.DataFrame) -> pd.DataFrame:
        df = tasks.copy()

        # Normalize categorical inputs
        for col in [
            "asset_criticality",
            "defect_severity",
            "safety_impact",
            "operational_impact",
        ]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .fillna("NONE")
                    .astype(str)
                    .str.upper()
                    .str.strip()
                )

        # Required because probability_of_failure
        # is assumed to already be calculated.
        if "probability_of_failure" not in df.columns:
            raise ValueError(
                "Raw task must contain probability_of_failure."
            )

        df["probability_of_failure"] = pd.to_numeric(
            df["probability_of_failure"],
            errors="coerce"
        )

        if df["probability_of_failure"].isna().any():
            raise ValueError(
                "Invalid probability_of_failure in task."
            )

        # Calculate overdue days from due_date if not supplied
        if "overdue_days" not in df.columns:
            df["overdue_days"] = 0

        df["overdue_days"] = pd.to_numeric(
            df["overdue_days"],
            errors="coerce"
        ).fillna(0).clip(lower=0)

        # Component scores
        df["criticality_score"] = (
            df["asset_criticality"]
            .map(self.CRITICALITY_MAP)
            .fillna(0.0)
        )

        df["defect_severity_score"] = (
            df["defect_severity"]
            .map(self.SEVERITY_MAP)
            .fillna(0.0)
        )

        df["safety_impact_score"] = (
            df["safety_impact"]
            .map(self.SEVERITY_MAP)
            .fillna(0.0)
        )

        df["operational_impact_score"] = (
            df["operational_impact"]
            .map(self.SEVERITY_MAP)
            .fillna(0.0)
        )

        df["overdue_score"] = (
            df["overdue_days"].clip(0, 30) / 30.0
        )

        # Same priority calculation used in notebook
        df["calculated_priority"] = (
            0.25 * df["probability_of_failure"]
            + 0.20 * df["criticality_score"]
            + 0.20 * df["safety_impact_score"]
            + 0.15 * df["operational_impact_score"]
            + 0.10 * df["defect_severity_score"]
            + 0.10 * df["overdue_score"]
        ).clip(0, 1)

        # IMPORTANT:
        # For a new task, calculated_priority becomes
        # the priority_score consumed by the optimizer.
        df["priority_score"] = df["calculated_priority"]

        df["priority_class"] = pd.cut(
            df["priority_score"],
            bins=[-np.inf, 0.25, 0.50, 0.75, np.inf],
            labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            right=False,
        ).astype(str)

        return df