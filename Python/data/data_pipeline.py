from __future__ import annotations

import pandas as pd


class DataPipeline:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df: pd.DataFrame = df.copy()

    def convert_numeric(self) -> DataPipeline:
        numeric = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Spread",
            "ATR",
            "ADX",
            "RSI",
        ]

        for col in numeric:
            if col not in self.df.columns:
                continue
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        return self

    def remove_empty(self) -> DataPipeline:
        self.df.dropna(inplace=True)
        return self

    def remove_duplicates(self) -> DataPipeline:
        self.df.drop_duplicates(
            subset=["Time", "Open", "High", "Low", "Close"],
            inplace=True,
        )
        return self

    def clean(self) -> DataPipeline:
        # Multi-ativo: mantém todos os símbolos (sem filtrar só XAUUSD)
        # remove preços inválidos (não-finitos / non-positivos)
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")
                self.df = self.df[self.df[col].notna() & (self.df[col] > 0)]

        # remove símbolos sem nome
        self.df = self.df[self.df["Symbol"].astype(str).str.strip() != ""]

        # remove spreads absurdos
        if "Spread" in self.df.columns:
            self.df = self.df[self.df["Spread"].between(0, 500)]

        # remove ATR inválido
        if "ATR" in self.df.columns:
            self.df = self.df[self.df["ATR"] > 0]

        return self

    def sort_time(self) -> DataPipeline:
        if "Time" in self.df.columns:
            self.df["Time"] = pd.to_datetime(self.df["Time"], errors="coerce")
            self.df.sort_values(by="Time", inplace=True)
        return self

    def reset(self) -> DataPipeline:
        self.df.reset_index(drop=True, inplace=True)
        return self

    def get(self) -> pd.DataFrame:
        return self.df
