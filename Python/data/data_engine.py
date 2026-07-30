from pathlib import Path
import os
import pandas as pd

from data.data_engine_xau import DataEngineXAU


class DataEngine:
    def __init__(self):
        self.engine = DataEngineXAU()

    def exists(self):
        return self.engine.exists()

    def load(self):
        return self.engine.load()

    def rows(self):
        if self.engine.df is None:
            return 0
        return len(self.engine.df)

    def columns(self):
        if self.engine.df is None:
            return []
        return list(self.engine.df.columns)

    def summary(self):
        if self.engine.df is None:
            return None
        return self.engine.df.describe(include="all")
