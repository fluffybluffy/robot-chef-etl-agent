import pandas as pd

COLUMNS = ['imdb_id', 'title', 'release_date', 'genres', 'duration_min',
           'country', 'content_rating', 'director', 'income_usd',
           'votes', 'imdb_score']
ALLOWED_RATINGS = {'G', 'PG', 'PG-13', 'R', 'NC-17', 'Not Rated'}
BAD_COUNTRIES = {'US', 'US.', 'Italy1', 'New Zesland', 'New Zeland'}


def validate(df):
    """Check every rule. Returns {rule name: list of row numbers that break it}.
    An empty list means the rule passed."""
    results = {}

    def rule(name, bad):
        results[name] = df.index[bad.fillna(False).astype(bool)].tolist()

    text_cols = ['imdb_id', 'title', 'genres', 'country', 'content_rating', 'director']
    dates = pd.to_datetime(df['release_date'], format='%Y-%m-%d', errors='coerce')
    has_date = df['release_date'].notna()

    results['columns_match_schema'] = [] if list(df.columns) == COLUMNS else ['columns']
    rule('no_empty_rows', df.isnull().all(axis=1))
    rule('imdb_id_not_null', df['imdb_id'].isnull())
    rule('imdb_id_unique', df['imdb_id'].duplicated(keep=False))
    rule('imdb_id_format', ~df['imdb_id'].astype(str).str.fullmatch(r'tt\d{7,8}'))
    rule('title_not_null', df['title'].isnull())
    rule('director_not_null', df['director'].isnull())
    rule('genres_not_null', df['genres'].isnull())
    rule('release_date_valid', has_date & dates.isnull())
    rule('release_year_in_range', has_date & ~dates.dt.year.between(1900, 2026))
    rule('duration_whole_minutes_30_to_400',
         df['duration_min'].notna() & (~df['duration_min'].between(30, 400) | (df['duration_min'] % 1 != 0)))
    rule('country_standard_spelling', df['country'].isin(BAD_COUNTRIES) | df['country'].astype(str).str.contains(r'\d|\.$'))
    rule('content_rating_allowed', df['content_rating'].notna() & ~df['content_rating'].isin(ALLOWED_RATINGS))
    rule('income_not_negative', df['income_usd'] < 0)
    rule('income_plausible_100k_plus', df['income_usd'].notna() & (df['income_usd'] < 100_000))
    rule('votes_positive_whole', df['votes'].isnull() | (df['votes'] <= 0) | (df['votes'] % 1 != 0))
    rule('score_between_0_and_10', df['imdb_score'].notna() & ~df['imdb_score'].between(0, 10))
    bad_space = pd.Series(False, index=df.index)
    for c in text_cols:
        s = df[c].dropna().astype(str)
        bad_space.loc[s.index] |= s.ne(s.str.strip())
    rule('no_extra_spaces', bad_space)
    return results
