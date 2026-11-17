# Robot Chef: an AI ETL agent

An AI agent that profiles a messy IMDb movie dataset, writes its own pandas cleaning code, runs it, and loads the clean data into a SQLite table. Built week by week.

## Evaluation score (19 pytest checks)

| Stage | Checks passed |
|---|---|
| Week 4, first run | 17/19 |
| Week 4, after improving the Week 3 prompt | 19/19 |

## What changed between the two runs
content_rating_allowed failed because 'Approved' is not an allowed rating, and income_plausible_100k_plus failed for two incomes below $100,000. I changed the Week 3 prompt so 'Approved' becomes 'Not Rated' and incomes below 100000 become missing.

## Week 6: merging two sources

- Source 1: the cleaned CSV (100 movies). Source 2: a JSON file mapped to the same columns (60 movies, 60 of them also in the CSV).
- Movies are matched on `imdb_id`.
- **Conflict rule:** if only one source has a value, use it. If both have a value and only one passes the schema rules, keep that one. If both pass, keep the JSON value, because when both values pass the rules there is no way to tell which is right, so I chose a fixed tie-break and log every conflict in conflicts.csv for review. Every conflict is written to `conflicts.csv`.
- Result: 100 movies in `target.db`, 4 conflicts resolved, pytest score 19/19 after merging.

## Week 7: surviving bad data

- `run_hardened.py` checks every row on its own. A bad row is skipped and logged in `errors.log` (source, position, imdb_id, title, reason) while the other rows continue.
- Fatal problems (a missing file, JSON that cannot be parsed) stop the run with a clear message and leave the database untouched.
- Test with deliberately corrupted copies (`make_corrupt_data.py`): 102 CSV rows gave 97 loaded and 5 rejected, 60 JSON records gave 58 loaded and 2 rejected, and all 97 loaded movies pass the schema rules.
