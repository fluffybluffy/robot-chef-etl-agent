import sqlite3
from pathlib import Path

import pandas as pd

DB_FILE = 'target.db'
CLEAN_CSV = 'data/movies_clean.csv'

SCHEMA = """
CREATE TABLE movies (
    imdb_id        TEXT PRIMARY KEY,
    title          TEXT NOT NULL,
    release_date   TEXT,
    genres         TEXT,
    duration_min   INTEGER,
    country        TEXT,
    content_rating TEXT,
    director       TEXT,
    income_usd     INTEGER,
    votes          INTEGER,
    imdb_score     REAL
)
"""

conn = sqlite3.connect(DB_FILE)
conn.execute('DROP TABLE IF EXISTS movies')
conn.execute(SCHEMA)

df = pd.read_csv(CLEAN_CSV)
df.to_sql('movies', conn, if_exists='append', index=False)
conn.commit()

count = conn.execute('SELECT COUNT(*) FROM movies').fetchone()[0]
print(f'Created {DB_FILE} with table movies')
print('Rows loaded:', count)
print('First 3 rows:')
for row in conn.execute('SELECT imdb_id, title, release_date, imdb_score FROM movies LIMIT 3'):
    print('  ', row)
conn.close()
