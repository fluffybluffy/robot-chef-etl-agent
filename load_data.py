import pandas as pd

DATA_FILE = 'data/messy_IMDB_dataset.csv'


def load_raw():
    """Load the messy IMDb CSV exactly as it is (no cleaning)."""
    return pd.read_csv(DATA_FILE, sep=';',
                       encoding='utf-8', encoding_errors='replace')
