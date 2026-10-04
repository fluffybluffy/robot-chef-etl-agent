import json
import re

import numpy as np
import pandas as pd

from llm import ask
from load_data import load_raw

MAX_TRIES = 5
ALLOWED_IMPORTS = {'pandas', 'numpy', 're'}
FINAL_COLUMNS = ['imdb_id', 'title', 'release_date', 'genres', 'duration_min',
                 'country', 'content_rating', 'director', 'income_usd',
                 'votes', 'imdb_score']

SYSTEM = """You are a careful data-cleaning agent.
You get a pandas DataFrame called df, loaded from a messy movie CSV, and you write
pandas code that cleans it.

Rules for your code:
- df already exists. pd (pandas), np (numpy) and re are already imported.
  Do not import anything else.
- Clean the WHOLE dataframe, not just the rows you were shown.
- Reassign df at the end (df = ...). Keep the variable name df.
- Never read or write files, use the network, or call eval/exec/open.
- Do not print anything.

Reply with ONLY one JSON object, with no markdown fences and no extra text:
{"explanation": "what you fixed and why, in plain English", "code": "the python code as one JSON string"}
Inside "code", use \\n for new lines."""

TASKS = f"""Clean df so that it ends up with exactly these 11 columns, in this order:
{FINAL_COLUMNS}

Required fixes:
1. Drop rows that are completely empty and the column that is completely empty.
2. Rename the columns to the 11 names above. Rename by POSITION, because the
   raw names contain odd characters.
3. imdb_id, title, genres, director: strip spaces; keep accents as they are.
4. release_date: parse every date format you can find into text like YYYY-MM-DD.
   Formats seen: 1995-02-10, '09 21 1972' (month day year), '22 Feb 04',
   '18/11/1976' (day/month/year), '23rd December of 1966', '10-29-99',
   'The 6th of marzo, year 1951', ' 23 -07-2008'. For 2-digit years use 19xx if the
   year is above 26, else 20xx. Impossible dates such as 1984-02-34 become missing (None).
5. duration_min: whole minutes. Values like '178c' should become 178; 'Nan', 'Inf',
   '-', 'NULL', 'Not Applicable', and blanks become missing.
6. country: one standard spelling. US, US. and USA become 'USA'; 'New Zesland' and
   'New Zeland' become 'New Zealand'; 'Italy1' becomes 'Italy'.
7. content_rating: keep G, PG, PG-13, R. 'Unrated' and 'Not Rated' become 'Not Rated'.
   'Approved' stays as 'Approved'. Leave missing values missing.
8. income_usd: whole dollars. Remove '$', spaces and commas. If a stray letter such
   as the 'o' in '4o8,035,783' is clearly a typo for a digit, repair it (o -> 0);
   otherwise make the value missing.
9. votes: whole numbers. Remove the dots used as thousands separators.
10. imdb_score: a decimal between 0 and 10. Repair things like '9,.0', '8..8', '8:8',
    '++8.7', '8,9f', '08.9', '8,7e-0'. If it cannot be repaired, make it missing.
Use pd.to_numeric(..., errors='coerce') style conversions so bad values become
missing instead of crashing. The numeric columns should end as Int64 (duration_min,
income_usd, votes) or float (imdb_score)."""


def profile_for_model(df):
    lines = ['Column names (repr): ' + repr(list(df.columns)),
             'Shape: ' + str(df.shape), '',
             'First 25 rows:', df.head(25).to_string(), '',
             'Value counts, Country:', df['Country'].value_counts(dropna=False).to_string(), '',
             'Value counts, Content Rating:', df['Content Rating'].value_counts(dropna=False).to_string()]
    return '\n'.join(lines)


def parse_reply(text):
    text = text.strip()
    text = re.sub(r'^\x60{3}(?:json)?\s*|\s*\x60{3}$', '', text)   # remove markdown fences if the model added them
    reply = json.loads(text, strict=False)   # strict=False tolerates real line breaks inside the code string
    if 'code' not in reply:
        raise ValueError("the JSON has no 'code' field")
    return reply


def check_code(code):
    """Very simple safety check before we run anything."""
    for name in re.findall(r'^\s*(?:import|from)\s+([A-Za-z_]\w*)', code, re.M):
        if name not in ALLOWED_IMPORTS:
            return f"import of '{name}' is not allowed"
    banned = r'\b(os|sys|subprocess|shutil|socket|requests|pathlib)\.|\b(open|eval|exec|__import__|input)\s*\(|\.to_(csv|sql|excel|pickle|json)\s*\(|\bread_\w+\s*\('
    m = re.search(banned, code)
    if m:
        return f"'{m.group(0)}' is not allowed in cleaning code"
    return None


def run_code(code, df):
    namespace = {'pd': pd, 'np': np, 're': re, 'df': df.copy()}
    exec(code, namespace)
    result = namespace['df']
    if not isinstance(result, pd.DataFrame):
        raise ValueError('df is no longer a DataFrame after your code')
    return result


def find_problems(df):
    """Simple checks on the result. Anything found is sent back to the model."""
    if list(df.columns) != FINAL_COLUMNS:
        return [f'columns must be exactly {FINAL_COLUMNS} but are {list(df.columns)}']
    problems = []
    if df.isnull().all(axis=1).any():
        problems.append('there are still completely empty rows')
    for col in ['duration_min', 'income_usd', 'votes', 'imdb_score']:
        if not pd.api.types.is_numeric_dtype(df[col]):
            problems.append(f'{col} is not numeric yet')
    if pd.api.types.is_numeric_dtype(df['imdb_score']):
        s = df['imdb_score'].dropna()
        if ((s < 0) | (s > 10)).any():
            problems.append('imdb_score has values outside 0-10')
    dates = df['release_date'].dropna().astype(str)
    if (~dates.str.fullmatch(r'\d{4}-\d{2}-\d{2}')).any() or pd.to_datetime(dates, format='%Y-%m-%d', errors='coerce').isna().any():
        problems.append('release_date has values that are not real YYYY-MM-DD dates')
    bad_countries = {'US', 'US.', 'Italy1', 'New Zesland', 'New Zeland'} & set(df['country'].dropna())
    if bad_countries:
        problems.append(f'country still has bad spellings: {sorted(bad_countries)}')
    if not df['imdb_id'].is_unique:
        problems.append('imdb_id has duplicates')
    return problems


def main():
    raw = load_raw()
    print('Raw shape:', raw.shape)

    prompt = TASKS + '\n\nHere is the data:\n' + profile_for_model(raw)
    try:
        prompt += '\n\nA first quality review found these issues:\n' + open('ai_issues.txt').read()
    except FileNotFoundError:
        pass

    messages = [{'role': 'user', 'content': prompt}]
    cleaned = None

    for attempt in range(1, MAX_TRIES + 1):
        print(f'\n===== Attempt {attempt} of {MAX_TRIES} =====')
        text = ask(SYSTEM, messages, max_tokens=16000)
        messages.append({'role': 'assistant', 'content': text})
        try:
            reply = parse_reply(text)
            code = reply['code']
            print('\nEXPLANATION:', reply.get('explanation', ''))
            print('\nCODE THE AGENT WROTE:\n' + '-' * 60 + '\n' + code + '\n' + '-' * 60)

            danger = check_code(code)
            if danger:
                raise ValueError('safety check failed: ' + danger)

            if input('\nRead the code above. Run it? [y/N] ').strip().lower() != 'y':
                print('Stopped. Nothing was run.')
                return

            result = run_code(code, raw)
            problems = find_problems(result)
            if problems:
                print('Ran fine, but problems remain:', problems)
                messages.append({'role': 'user', 'content':
                    'Your code ran, but the result still has these problems:\n- '
                    + '\n- '.join(problems)
                    + '\nWrite corrected code that starts again from the ORIGINAL raw df '
                      '(the same df you were given the first time). Reply with ONLY the JSON object.'})
                continue
            cleaned = result
            with open('generated_cleaning_code.py', 'w') as f:
                f.write(code)
            break
        except Exception as e:
            error = f'{type(e).__name__}: {e}'
            print('ERROR:', error)
            messages.append({'role': 'user', 'content':
                f'Your last reply failed with this error:\n{error}\n'
                'Fix it. The code runs again on the ORIGINAL raw df. '
                'Reply with ONLY the JSON object.'})

    if cleaned is None:
        print('\nThe agent did not finish within', MAX_TRIES, 'attempts.')
        return

    print('\n===== RESULT =====')
    print('Shape:', cleaned.shape)
    print(cleaned.dtypes)
    print(cleaned.head(10).to_string())
    print('\nNulls per column:\n', cleaned.isnull().sum())
    cleaned.to_csv('data/movies_clean.csv', index=False)
    print('\nSaved data/movies_clean.csv and generated_cleaning_code.py')


if __name__ == '__main__':
    main()
