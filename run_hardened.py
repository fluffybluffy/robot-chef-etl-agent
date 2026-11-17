import argparse
import json
import re
import sqlite3
import sys

import pandas as pd

from map_source2 import get_path, to_cell          # Week 5 helpers
from merge_sources import (ALLOWED_RATINGS, COLUMNS, SCHEMA, merge)   # Week 6 merge
from validate import validate                       # Week 4 rules

BAD_COUNTRIES = {'US', 'US.', 'Italy1', 'New Zesland', 'New Zeland'}


class FatalError(Exception):
    """Something is wrong with a whole source: stop the whole run."""


class RowError(Exception):
    """Something is wrong with ONE row: skip it, log it, keep going."""


def blank(v):
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ''


def check_row(raw):
    """Turn one raw row into a clean row, or raise RowError listing EVERY problem found."""
    problems, row = [], {}

    def text(col, required=False):
        v = raw.get(col)
        if blank(v):
            if required:
                problems.append(f'{col} is missing')
            return None
        return str(v).strip()

    def number(col, required=False, whole=True, low=None, high=None):
        v = raw.get(col)
        if blank(v):
            if required:
                problems.append(f'{col} is missing')
            return None
        try:
            x = float(str(v).strip())
        except ValueError:
            problems.append(f"{col} '{v}' is not a number")
            return None
        if whole and x != int(x):
            problems.append(f'{col} {v} is not a whole number')
            return None
        if (low is not None and x < low) or (high is not None and x > high):
            problems.append(f'{col} {v} is outside the allowed range {low} to {high}')
            return None
        return int(x) if whole else x

    row['imdb_id'] = text('imdb_id', required=True)
    if row['imdb_id'] and not re.fullmatch(r'tt\d{7,8}', row['imdb_id']):
        problems.append(f"imdb_id '{row['imdb_id']}' does not look like tt0000000")
    row['title'] = text('title', required=True)
    row['release_date'] = text('release_date')
    if row['release_date']:
        d = pd.to_datetime(row['release_date'], format='%Y-%m-%d', errors='coerce')
        if pd.isna(d):
            problems.append(f"release_date '{row['release_date']}' is not a real YYYY-MM-DD date")
        elif not 1900 <= d.year <= 2026:
            problems.append(f"release_date '{row['release_date']}' is outside 1900-2026")
    row['genres'] = text('genres', required=True)
    row['duration_min'] = number('duration_min', low=30, high=400)
    row['country'] = text('country')
    if row['country'] in BAD_COUNTRIES:
        problems.append(f"country '{row['country']}' is a known bad spelling")
    row['content_rating'] = text('content_rating')
    if row['content_rating'] and row['content_rating'] not in ALLOWED_RATINGS:
        problems.append(f"content_rating '{row['content_rating']}' is not allowed")
    row['director'] = text('director', required=True)
    row['income_usd'] = number('income_usd', low=100_000)
    row['votes'] = number('votes', required=True, low=1)
    row['imdb_score'] = number('imdb_score', whole=False, low=0, high=10)

    if problems:
        raise RowError('; '.join(problems))
    return row


def read_csv_rows(path):
    try:
        df = pd.read_csv(path, dtype=str)
    except FileNotFoundError:
        raise FatalError(f'file not found: {path}')
    except Exception as e:
        raise FatalError(f'cannot read {path}: {e}')
    df = df.astype(object).where(df.notna(), None)
    return [(i + 2, r) for i, r in enumerate(df.to_dict('records'))]     # +2: header is line 1


def read_json_rows(path, mapping):
    try:
        with open(path, encoding='utf-8') as f:
            records = json.load(f)
    except FileNotFoundError:
        raise FatalError(f'file not found: {path}')
    except json.JSONDecodeError as e:
        raise FatalError(f'{path} is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}')
    if not isinstance(records, list):
        raise FatalError(f'{path} must contain a list of records')
    out = []
    for i, rec in enumerate(records, start=1):
        out.append((i, {col: to_cell(get_path(rec, p)) for col, p in mapping.items()}))
    return out


def process_source(name, numbered_rows, errors):
    """Run every row through check_row. One bad row never stops the others."""
    good, seen = [], {}
    for position, raw in numbered_rows:
        try:
            row = check_row(raw)
            if row['imdb_id'] in seen:
                raise RowError(f"duplicate imdb_id (first seen at position {seen[row['imdb_id']]})")
            seen[row['imdb_id']] = position
            good.append(row)
        except RowError as e:
            errors.append((name, position, raw.get('imdb_id'), raw.get('title'), str(e)))
        except Exception as e:           # a bug or surprise in one row must not kill the run
            errors.append((name, position, raw.get('imdb_id'), raw.get('title'), f'unexpected {type(e).__name__}: {e}'))
    return good


def to_frame(rows):
    df = pd.DataFrame(rows, columns=COLUMNS)
    for col in ['duration_min', 'income_usd', 'votes', 'imdb_score']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def load_to_db(merged, db_file):
    merged = merged.copy()
    for col in ['duration_min', 'income_usd', 'votes']:
        merged[col] = merged[col].astype('Int64')
    conn = sqlite3.connect(db_file)
    conn.execute(SCHEMA)
    conn.execute('DELETE FROM movies')
    merged.to_sql('movies', conn, if_exists='append', index=False)
    conn.commit()
    table = pd.read_sql('SELECT * FROM movies', conn)
    conn.close()
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='data/movies_clean.csv')
    ap.add_argument('--json', default='data/movies_source2.json')
    ap.add_argument('--mapping', default='mapping_source2.json')
    ap.add_argument('--db', default='target.db')
    ap.add_argument('--log', default='errors.log')
    args = ap.parse_args()

    errors = []
    try:
        with open(args.mapping) as f:
            mapping = json.load(f)
        csv_rows = read_csv_rows(args.csv)
        json_rows = read_json_rows(args.json, mapping)
    except FatalError as e:
        with open(args.log, 'w') as f:
            f.write(f'FATAL | {e}\n')
        print(f'\nFATAL ERROR: {e}\nNothing was loaded. {args.db} was not touched.')
        sys.exit(1)

    good_csv = process_source('csv', csv_rows, errors)
    good_json = process_source('json', json_rows, errors)
    merged, conflicts, both, only_csv, only_json = merge(to_frame(good_csv), to_frame(good_json))
    table = load_to_db(merged, args.db)

    with open(args.log, 'w') as f:
        f.write('source | position | imdb_id | title | reason\n')
        for src, pos, imdb_id, title, reason in errors:
            f.write(f'{src} | {pos} | {imdb_id} | {title} | {reason}\n')

    n_csv_bad = sum(1 for e in errors if e[0] == 'csv')
    n_json_bad = sum(1 for e in errors if e[0] == 'json')
    print('SUMMARY')
    print(f'  CSV : {len(csv_rows)} rows read, {len(good_csv)} succeeded, {n_csv_bad} failed')
    print(f'  JSON: {len(json_rows)} records read, {len(good_json)} succeeded, {n_json_bad} failed')
    print(f'  Merge: {both} movies in both, {len(conflicts)} conflicts resolved')
    print(f'  Loaded into {args.db}: {len(table)} movies')
    broken = {k: v for k, v in validate(table).items() if v}
    print('  Schema rules on the loaded table:', 'all pass' if not broken else f'BROKEN: {broken}')
    print(f'  Failures logged in {args.log}')
    for src, pos, imdb_id, title, reason in errors:
        print(f'    - {src} #{pos} {imdb_id} {title}: {reason}')


if __name__ == '__main__':
    main()
