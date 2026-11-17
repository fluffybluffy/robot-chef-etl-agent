import json
from pathlib import Path

import pandas as pd

Path('data/test').mkdir(exist_ok=True)

# ---- corrupt a COPY of the CSV (the real files are never touched) ----
df = pd.read_csv('data/movies_clean.csv', dtype=str)
print('Corruptions planted in data/test/movies_clean_corrupt.csv (line = line in the file):')

df.loc[3, 'imdb_id'] = None
print(f'  line 5:   imdb_id blanked')
df.loc[5, 'imdb_score'] = 'abc'
print(f"  line 7:   {df.loc[5, 'title']}: imdb_score set to 'abc'")
df.loc[7, 'duration_min'] = '-5'
print(f"  line 9:   {df.loc[7, 'title']}: duration_min set to -5")

dup = df.loc[10].copy()
df = pd.concat([df, dup.to_frame().T], ignore_index=True)
print(f"  line {len(df) + 1}:  duplicate of {dup['title']} ({dup['imdb_id']})")

fake = df.loc[20].copy()
fake['imdb_id'], fake['title'], fake['release_date'] = 'tt9999991', 'Test Movie', '2031-13-45'
df = pd.concat([df, fake.to_frame().T], ignore_index=True)
print(f"  line {len(df) + 1}:  new movie 'Test Movie' with release_date 2031-13-45")
df.to_csv('data/test/movies_clean_corrupt.csv', index=False)

# ---- corrupt a COPY of the JSON ----
with open('data/movies_source2.json', encoding='utf-8') as f:
    records = json.load(f)
print('\nCorruptions planted in data/test/movies_source2_corrupt.json (record = position, starting at 1):')
title = records[1]['name']
del records[1]['ratings']
print(f'  record 2: {title}: the whole ratings block removed')
title = records[3]['name']
records[3]['runtime_minutes'] = 'N/A'
print(f"  record 4: {title}: runtime_minutes set to 'N/A'")
text = json.dumps(records, indent=2, ensure_ascii=False)
Path('data/test/movies_source2_corrupt.json').write_text(text, encoding='utf-8')

# ---- a JSON file that is cut off in the middle (a fatal problem) ----
Path('data/test/movies_source2_broken.json').write_text(text[:-120], encoding='utf-8')
print('\nAlso wrote data/test/movies_source2_broken.json: the same file cut off in the middle (fatal test)')
