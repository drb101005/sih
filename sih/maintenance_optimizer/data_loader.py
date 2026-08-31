from pathlib import Path
import pandas as pd

class DataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)

    def _read(self, name):
        path = self.data_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Missing data file: {path}")
        return pd.read_csv(path)

    def tasks(self): return self._read("tasks.csv")
    def blocks(self): return self._read("blocks.csv")
    def trains(self):
        p = self.data_dir / "trains.csv"
        return pd.read_csv(p) if p.exists() else None
    def forecasts(self):
        p = self.data_dir / "forecasts.csv"
        return pd.read_csv(p) if p.exists() else None
    def schedule(self):
        p = self.data_dir / "schedule.csv"
        return pd.read_csv(p) if p.exists() else pd.DataFrame()
    def candidates_reference(self):
        p = self.data_dir / "candidates.csv"
        return pd.read_csv(p) if p.exists() else None
