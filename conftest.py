from pathlib import Path

import pandas as pd
import pytest

from validate import validate

CLEAN_CSV = Path(__file__).parent / 'data' / 'movies_clean.csv'


@pytest.fixture(scope='session')
def df():
    return pd.read_csv(CLEAN_CSV)


@pytest.fixture(scope='session')
def results(df):
    return validate(df)
