import pytest

RULES = [
    'columns_match_schema',
    'no_empty_rows',
    'imdb_id_not_null',
    'imdb_id_unique',
    'imdb_id_format',
    'title_not_null',
    'director_not_null',
    'genres_not_null',
    'release_date_valid',
    'release_year_in_range',
    'duration_whole_minutes_30_to_400',
    'country_standard_spelling',
    'content_rating_allowed',
    'income_not_negative',
    'income_plausible_100k_plus',
    'votes_positive_whole',
    'score_between_0_and_10',
    'no_extra_spaces',
]


def test_has_100_rows(df):
    assert len(df) == 100


@pytest.mark.parametrize('rule', RULES)
def test_rule(results, rule):
    assert results[rule] == [], f'rows that break this rule: {results[rule]}'
