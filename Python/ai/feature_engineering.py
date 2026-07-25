import pandas as pd


class FeatureEngineering:


    def __init__(self, df):

        self.df = df.copy()



    def create(self):

        df = self.df


        # retorno do preço

        df["return"] = (
            df["Close"]
            .pct_change()
        )


        # tamanho candle

        df["candle_size"] = (
            df["High"] -
            df["Low"]
        )


        # direção

        df["direction"] = 0


        df.loc[
            df["Close"] > df["Open"],
            "direction"
        ] = 1


        df.loc[
            df["Close"] < df["Open"],
            "direction"
        ] = -1



        # médias

        df["ema_fast"] = (
            df["Close"]
            .ewm(span=10)
            .mean()
        )


        df["ema_slow"] = (
            df["Close"]
            .ewm(span=50)
            .mean()
        )


        # distância tendência

        df["trend"] = (
            df["ema_fast"]
            -
            df["ema_slow"]
        )


        # volatilidade

        df["volatility"] = (
            df["return"]
            .rolling(10)
            .std()
        )


        df.dropna(
            inplace=True
        )


        self.df = df


        return self



    def get(self):

        return self.df