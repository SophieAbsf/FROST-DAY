import pandas as pd


def load_weather_data(filepath):
    return pd.read_csv(
        filepath,
        compression="gzip",
        sep=";"
    )