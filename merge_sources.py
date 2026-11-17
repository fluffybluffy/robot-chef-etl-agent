import sqlite3

import pandas as pd

CSV_FILE = 'data/movies_clean.csv'            # source 1: cleaned by the agent in Week 3
JSON_MAPPED = 'data/source2_mapped.csv'       # source 2: mapped from JSON in Week 5
MERGED_CSV = 'data/movies_merged.csv'
CONFLICT_LOG = 'conflicts.csv'
DB_FILE = 'target.db'

# CONFLICT RULE: when both sources have the same movie and the same field
# holds two different values:
#   1. if only one value passes the schema rules, keep that one;
#   2. if both pass (or both fail), keep the value from PREFER.
PREFER = 'json'          # change to 'csv' to prefer source 1 instead

COLUMNS = ['imdb_id', 'title', 'release_date', 'genres', 'duration_min',
           'country', 'content_rating', 'director', 'income_usd',
           'votes', 'imdb_score']
NUMERIC = ['duration_min', 'income_usd', 'votes', 'imdb_score']
ALLOWED_RATINGS = {'G', 'PG', 'PG-13', 'R', 'NC-17', 'Not Rated'}

# same table as create_db.py
SCHEMA = """
CREATE TABLE IF NOT EXISTS movies (
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


def clean_source_1(df):
    """Source 1 was cleaned by the agent in Week 3, so we only line up the columns."""
    return df[COLUMNS].copy()


def clean_source_2(df):
    """Source 2 comes from the JSON mapping: line up columns, strip text, fix number types."""
    df = df[COLUMNS].copy()
    for col in COLUMNS:
        if col in NUMERIC:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = df[col].astype('string').str.strip()
    return df


def valid(col, v):
    """Does this single value pass the schema rule for its column?"""
    if pd.isna(v):
        return False
    if col == 'imdb_score':
        return 0 <= v <= 10
    if col == 'duration_min':
        return 30 <= v <= 400
    if col == 'income_usd':
        return v >= 100_000
    if col == 'votes':
        return v > 0
    if col == 'content_rating':
        return v in ALLOWED_RATINGS
    return True


def same(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def merge(csv_df, json_df):
    csv_df = csv_df.set_index('imdb_id', drop=False)
    json_df = json_df.set_index('imdb_id', drop=False)
    ids = list(csv_df.index) + [i for i in json_df.index if i not in csv_df.index]

    rows, conflicts = [], []
    both = only_csv = only_json = 0
    for imdb_id in ids:
        a = csv_df.loc[imdb_id] if imdb_id in csv_df.index else None
        b = json_df.loc[imdb_id] if imdb_id in json_df.index else None
        if b is None:
            only_csv += 1
            rows.append(a.to_dict())
            continue
        if a is None:
            only_json += 1
            rows.append(b.to_dict())
            continue
        both += 1
        row = {'imdb_id': imdb_id}
        for col in COLUMNS[1:]:
            va, vb = a[col], b[col]
            if pd.isna(va):
                row[col] = vb
            elif pd.isna(vb) or same(va, vb):
                row[col] = va
            else:
                ok_a, ok_b = valid(col, va), valid(col, vb)
                if ok_a and not ok_b:
                    pick, why = 'csv', 'only the CSV value passes the rules'
                elif ok_b and not ok_a:
                    pick, why = 'json', 'only the JSON value passes the rules'
                else:
                    pick, why = PREFER, f'no clear winner, so the rule prefers {PREFER}'
                row[col] = va if pick == 'csv' else vb
                conflicts.append({'imdb_id': imdb_id, 'title': a['title'], 'column': col,
                                  'csv_value': va, 'json_value': vb, 'kept': pick, 'reason': why})
        rows.append(row)

    merged = pd.DataFrame(rows)[COLUMNS]
    for col in ['duration_min', 'income_usd', 'votes']:
        merged[col] = pd.to_numeric(merged[col], errors='coerce').astype('Int64')
    merged['imdb_score'] = pd.to_numeric(merged['imdb_score'], errors='coerce').astype(float)
    return merged, pd.DataFrame(conflicts), both, only_csv, only_json


def main():
    csv_df = clean_source_1(pd.read_csv(CSV_FILE))
    json_df = clean_source_2(pd.read_csv(JSON_MAPPED))
    merged, conflicts, both, only_csv, only_json = merge(csv_df, json_df)

    print(f'Source 1 (CSV):  {len(csv_df)} movies')
    print(f'Source 2 (JSON): {len(json_df)} movies')
    print(f'In both: {both}   only in the CSV: {only_csv}   only in the JSON: {only_json}')
    print(f'\nConflicts found: {len(conflicts)}   (rule: keep the valid value; if unclear, prefer {PREFER})')
    for _, c in conflicts.iterrows():
        print(f"  {c['imdb_id']}  {c['title']}: {c['column']}  CSV={c['csv_value']}  JSON={c['json_value']}  -> kept {c['kept']}")
    conflicts.to_csv(CONFLICT_LOG, index=False)

    merged.to_csv(MERGED_CSV, index=False)
    conn = sqlite3.connect(DB_FILE)
    conn.execute(SCHEMA)
    conn.execute('DELETE FROM movies')
    merged.to_sql('movies', conn, if_exists='append', index=False)
    conn.commit()
    count = conn.execute('SELECT COUNT(*) FROM movies').fetchone()[0]
    conn.close()
    print(f'\nMerged movies: {len(merged)}')
    print(f'Loaded into {DB_FILE}, table movies: {count} rows')
    print(f'Saved {MERGED_CSV} and {CONFLICT_LOG}')


if __name__ == '__main__':
    main()
