import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from validate import validate

DB_FILE = Path(__file__).parent / 'target.db'


@pytest.fixture(scope='session')
def df():
    """The final table: what actually landed in the target database."""
    conn = sqlite3.connect(DB_FILE)
    table = pd.read_sql('SELECT * FROM movies', conn)
    conn.close()
    return table


@pytest.fixture(scope='session')
def results(df):
    return validate(df)
