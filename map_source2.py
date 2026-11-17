import json
import re

import pandas as pd

from llm import ask

SOURCE_JSON = 'data/movies_source2.json'
CLEAN_CSV = 'data/movies_clean.csv'
MAPPING_FILE = 'mapping_source2.json'
OUT_CSV = 'data/source2_mapped.csv'
MAX_TRIES = 3

TARGET = {
    'imdb_id': 'text, the IMDb title id, looks like tt0111161',
    'title': 'text, the movie title',
    'release_date': 'text, the release date as YYYY-MM-DD',
    'genres': 'text, all genres in one string',
    'duration_min': 'whole number, the running time in minutes',
    'country': 'text, the country',
    'content_rating': 'text, the age rating such as R or PG-13',
    'director': 'text, all directors in one string',
    'income_usd': 'whole number, worldwide income in US dollars',
    'votes': 'whole number, the number of IMDb votes',
    'imdb_score': 'decimal between 0 and 10, the IMDb score',
}

SYSTEM = """You are a data integration assistant. You map the fields of a JSON source onto a target table.
Reply with ONLY one JSON object, with no markdown fences and no extra text.
The keys are the target column names. Each value is the dotted path of the source field
that holds that column, for example "ratings.imdb" for a nested field."""


def flat_paths(item, prefix=''):
    """All field paths in a record, e.g. 'name' and 'ratings.imdb'."""
    paths = []
    for key, value in item.items():
        path = prefix + key
        if isinstance(value, dict):
            paths += flat_paths(value, path + '.')
        else:
            paths.append(path)
    return paths


def get_path(item, path):
    for key in path.split('.'):
        item = item.get(key) if isinstance(item, dict) else None
    return item


def to_cell(value):
    if isinstance(value, list):          # genres and directors arrive as lists
        return ', '.join(str(v) for v in value) or None
    return value


def same(a, b):
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def ask_for_mapping(raw):
    valid_paths = set(flat_paths(raw[0]))
    prompt = ('Target table columns:\n'
              + '\n'.join(f'- {c}: {d}' for c, d in TARGET.items())
              + '\n\nSample records from the JSON source:\n'
              + json.dumps(raw[:3], indent=2, ensure_ascii=False))
    messages = [{'role': 'user', 'content': prompt}]
    for attempt in range(1, MAX_TRIES + 1):
        text = ask(SYSTEM, messages, max_tokens=4000)
        messages.append({'role': 'assistant', 'content': text})
        try:
            text = re.sub(r'^\x60{3}(?:json)?\s*|\s*\x60{3}$', '', text.strip())
            mapping = json.loads(text, strict=False)
            if set(mapping) != set(TARGET):
                raise ValueError(f'the keys must be exactly {list(TARGET)}')
            unknown = [p for p in mapping.values() if p not in valid_paths]
            if unknown:
                raise ValueError(f'these paths do not exist in the source: {unknown}. '
                                 f'Valid paths are: {sorted(valid_paths)}')
            return mapping
        except Exception as e:
            error = f'{type(e).__name__}: {e}'
            print(f'Attempt {attempt} failed:', error)
            messages.append({'role': 'user', 'content':
                f'That mapping was rejected: {error}\nReply again with ONLY the JSON object.'})
    raise SystemExit('Claude did not produce a valid mapping. Run the script again.')


def main():
    with open(SOURCE_JSON, encoding='utf-8') as f:
        raw = json.load(f)
    print(f'Loaded {len(raw)} records from {SOURCE_JSON}')

    mapping = ask_for_mapping(raw)
    print('\nMAPPING PROPOSED BY CLAUDE (target column <- source field):')
    for col, path in mapping.items():
        print(f'  {col:15} <- {path}')
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)

    rows = [{col: to_cell(get_path(item, path)) for col, path in mapping.items()} for item in raw]
    mapped = pd.DataFrame(rows, columns=list(TARGET))
    mapped.to_csv(OUT_CSV, index=False)
    print(f'\nMapped {len(mapped)} rows and saved {OUT_CSV}')

    print('\nSPOT CHECK: 5 records, original JSON on top, mapped row below')
    for i in range(5):
        print('\nJSON  :', json.dumps(raw[i], ensure_ascii=False))
        print('MAPPED:', mapped.iloc[i].to_dict())

    csv_df = pd.read_csv(CLEAN_CSV).set_index('imdb_id')
    diffs = []
    overlap = 0
    for _, row in mapped.iterrows():
        if row['imdb_id'] not in csv_df.index:
            continue
        overlap += 1
        for col in TARGET:
            if col != 'imdb_id' and not same(row[col], csv_df.loc[row['imdb_id'], col]):
                diffs.append((row['imdb_id'], row['title'], col, csv_df.loc[row['imdb_id'], col], row[col]))
    print(f'\nMovies found in both sources: {overlap}')
    print(f'Cells that differ between the CSV and the JSON: {len(diffs)}')
    for imdb_id, title, col, csv_val, json_val in diffs:
        print(f'  {imdb_id}  {title}: {col}  CSV={csv_val}  JSON={json_val}')


if __name__ == '__main__':
    main()
