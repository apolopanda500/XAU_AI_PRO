import pathlib
import pandas as pd


class DataPipeline:

    def __init__(self, df):

        self.df = df.copy()


    def convert_numeric(self):

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

        print(self.df.columns)

        for col in numeric:

            if col not in self.df.columns:
                print(f"Coluna {col} não encontrada.")
                continue

            self.df[col] = pd.to_numeric(
                self.df[col],
                errors="coerce"
            )

        return self

    def remove_empty(self):

        self.df.dropna(inplace=True)

        return self


    def remove_duplicates(self):

        self.df.drop_duplicates(
            subset=[
                "Time",
                "Open",
                "High",
                "Low",
                "Close"
            ],
            inplace=True
        )

        return self

    def clean(self):

        # somente XAUUSD
        self.df = self.df[
            self.df["Symbol"] == "XAUUSD"
        ]


        # remove preços inválidos
        self.df = self.df[
            (self.df["Open"] > 1000) &
            (self.df["Close"] > 1000)
        ]


        # remove spreads absurdos
        self.df = self.df[
            self.df["Spread"] < 200
        ]


        # remove ATR inválido
        self.df = self.df[
            self.df["ATR"] > 0
        ]

        return self

    def sort_time(self):

        if "Time" in self.df.columns:

            self.df["Time"] = pd.to_datetime(
                self.df["Time"],
                errors="coerce"
            )

            self.df.sort_values(
                by="Time",
                inplace=True
            )

        return self


    def reset(self):

        self.df.reset_index(
            drop=True,
            inplace=True
        )

        return self


    def get(self):

        return self.df

    print("PIPELINE VERSÃO 12/07")