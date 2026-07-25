from pathlib import Path
import os
import pandas as pd


class DataEngineXAU:

    def __init__(self):

        project_root = Path(__file__).resolve().parents[2]
        default_dataset = project_root / "MQL5" / "Files" / "Data" / "dataset.csv"

        self.dataset = Path(
            os.getenv("XAU_AI_PRO_DATASET", default_dataset)
        ).expanduser()

        self.df = None


    def exists(self):

        return self.dataset.exists()



    def load(self):

        if not self.exists():

            raise FileNotFoundError(
                f"Arquivo não encontrado: {self.dataset}"
            )


        columns = [
            "Time",
            "Symbol",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Spread",
            "ATR",
            "ADX",
            "RSI"
        ]


        self.df = pd.read_csv(
            self.dataset,
            encoding="utf-16",
            sep=",",
            header=None,
            names=columns,
            skip_blank_lines=True
        )


        # remove cabeçalho duplicado
        self.df = self.df[
            self.df["Time"] != "Time"
        ]


        # somente ouro
        self.df = self.df[
            self.df["Symbol"] == "XAUUSD"
        ]


        # converter data

        self.df["Time"] = pd.to_datetime(
            self.df["Time"],
            errors="coerce"
        )


        numeric = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Spread",
            "ATR",
            "ADX",
            "RSI"
        ]


        for col in numeric:

            self.df[col] = pd.to_numeric(
                self.df[col],
                errors="coerce"
            )


        # remover dados inválidos

        self.df.dropna(
            inplace=True
        )


        self.df = self.df[
            self.df["Open"] > 1000
        ]


        self.df.reset_index(
            drop=True,
            inplace=True
        )


        print("DATASET XAUUSD CARREGADO")
        print(self.df.head())

        print()

        print(
            self.df["Symbol"].value_counts()
        )


        return self.df



    def rows(self):

        if self.df is None:
            return 0

        return len(self.df)



    def columns(self):

        if self.df is None:
            return []

        return list(self.df.columns)



    def summary(self):

        return self.df.describe()