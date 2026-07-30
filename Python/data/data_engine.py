from pathlib import Path
import os
import pandas as pd

class DataEngine:
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
            raise FileNotFoundError(self.dataset)

        encodings = [
            "utf-16",
            "utf-16-le",
            "utf-8",
            "utf-8-sig",
            "latin1"
        ]

        for enc in encodings:

            try:

                df = pd.read_csv(
                    self.dataset,
                    sep=",",
                    encoding=enc
                )

                print("Encoding utilizado:", enc)
                print(df.head())
                print(df.columns)

                self.df = df

                return self.df

            except Exception as e:

                print(enc, "->", e)

        raise Exception("Não foi possível abrir o dataset.")

        print(self.df.head())
        print(self.df.columns)

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
        if self.df is None:
            return None
        return self.df.describe(include="all")
