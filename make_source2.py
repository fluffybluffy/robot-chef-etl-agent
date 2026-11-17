import json

import pandas as pd

CLEAN_CSV = 'data/movies_clean.csv'
OUT_JSON = 'data/movies_source2.json'

df = pd.read_csv(CLEAN_CSV)

# The second supplier only knows the movies from position 40 onward,
# so about 60 movies exist in both sources.
part = df.iloc[40:].copy().reset_index(drop=True)

# Plant a few conflicts on purpose: values that differ from the CSV.
changes = []


def plant(col, how_many, new_value):
    for i in part[part[col].notna()].index[:how_many]:
        old = part.loc[i, col]
        new = new_value(old)
        changes.append((part.loc[i, 'imdb_id'], part.loc[i, 'title'], col, old, new))
        part.loc[i, col] = new


plant('duration_min', 2, lambda v: v + 10)
plant('imdb_score', 2, lambda v: round(v - 0.5, 1))


def num(v, kind):
    return None if pd.isna(v) else kind(v)


def text(v):
    return None if pd.isna(v) else v


def split_list(v):
    return [] if pd.isna(v) else [x.strip() for x in v.split(',')]


records = []
for _, r in part.iterrows():
    records.append({
        'id': r['imdb_id'],
        'name': r['title'],
        'released': text(r['release_date']),
        'genres': split_list(r['genres']),
        'runtime_minutes': num(r['duration_min'], int),
        'origin': text(r['country']),
        'certificate': text(r['content_rating']),
        'directed_by': split_list(r['director']),
        'box_office': {'worldwide_usd': num(r['income_usd'], int)},
        'ratings': {'imdb': num(r['imdb_score'], float), 'votes': num(r['votes'], int)},
    })

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(records, f, indent=2, ensure_ascii=False)

print(f'Wrote {OUT_JSON} with {len(records)} movies')
print('Conflicts planted on purpose (remember these for Week 6):')
for imdb_id, title, col, old, new in changes:
    print(f'  {imdb_id}  {title}: {col} was {old}, now {new}')
