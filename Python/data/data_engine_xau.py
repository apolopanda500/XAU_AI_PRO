import os
from pathlib import Path

import pandas as pd


class DataEngineXAU:
    def __init__(self, dataset_path: str | Path | None = None):
        if dataset_path is not None:
            self.dataset = Path(dataset_path).expanduser()
        else:
            # Caminho padrão sincronizado com o terminal MT5
            MT5_FILES_PATH = Path(r"C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files")
            default_dataset = MT5_FILES_PATH / "Data" / "dataset.csv"
            self.dataset = Path(
                os.getenv("XAU_AI_PRO_DATASET", default_dataset)
            ).expanduser()

        self.df: pd.DataFrame | None = None

    def exists(self):
        return self.dataset.exists()

    def load(self):
        if not self.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.dataset}")

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
            "RSI",
            "KCI_VD",
            "KCI_MAIN",
            "KDI_PLUS",
            "KDI_MINUS",
        ]

        with open(self.dataset, "rb") as f:
            content = f.read()

        # Opcao B (ETAPA 15.2.2): detectar encoding via BOM (robustez do consumidor).
        # O produtor (DataLogger.mqh) agora grava FILE_UNICODE explicito (UTF-16 LE + BOM),
        # mas toleramos legado ANSI/UTF-8 para nao quebrar parsers antigos.
        import io
        if content[:2] in (b'\xff\xfe', b'\xfe\xff'):
            enc = "utf-16"
            # Se houver numero impar de bytes (exceto BOM), remove o ultimo
            if len(content) % 2 != 0:
                content = content[:-1]
        elif content[:3] == b'\xef\xbb\xbf':
            enc = "utf-8-sig"
        else:
            enc = "cp1252"  # fallback ANSI (legado)

        self.df = pd.read_csv(
            io.BytesIO(content),
            encoding=enc,
            sep=",",
            header=None,
            names=columns,
            skip_blank_lines=True,
            on_bad_lines="skip",
            engine="python",
        )

        # remove cabeçalho duplicado
        self.df = self.df[self.df["Time"] != "Time"]

        # remover linhas com símbolo vazio
        self.df = self.df[self.df["Symbol"].astype(str).str.strip() != ""]

        # ETAPA 15.3: whitelist de simbolos validos (evita linhas sujas tipo '69.136',
        # '1.37933', '4654.93' que sao precos sem cabecalho virados em Symbol).
        try:
            from mt5_bridge import symbol_aliases
            valid = set(symbol_aliases.keys()) | {s for v in symbol_aliases.values() for s in v}
            self.df = self.df[self.df["Symbol"].astype(str).str.upper().isin(valid)]
        except Exception:
            pass  # fallback: mantem linhas atuais se mt5_bridge indisponivel

        # converter data

        self.df["Time"] = pd.to_datetime(self.df["Time"], errors="coerce")

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
            "KCI_VD",
            "KCI_MAIN",
            "KDI_PLUS",
            "KDI_MINUS",
        ]

        for col in numeric:
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        # remover dados inválidos (apenas colunas essenciais; KCI pode
        # estar ausente em datasets antigos, entao preenchemos com 0.0)
        core = [
            "Open", "High", "Low", "Close", "Volume",
            "Spread", "ATR", "ADX", "RSI",
        ]
        self.df.dropna(subset=core, inplace=True)

        for kci in ("KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS"):
            if kci not in self.df.columns:
                self.df[kci] = 0.0
            self.df[kci] = pd.to_numeric(self.df[kci], errors="coerce").fillna(0.0)

        self.df = self.df[self.df["Open"].notna() & (self.df["Open"] > 0)]

        self.df.reset_index(drop=True, inplace=True)

        print("DATASET CARREGADO")
        print(self.df.head())

        print()

        print(self.df["Symbol"].value_counts())

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

        return self.df.describe()
