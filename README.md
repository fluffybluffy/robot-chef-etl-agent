# Robot Chef: an AI ETL agent

An AI agent that profiles a messy IMDb movie dataset, writes its own pandas cleaning code, runs it, and loads the clean data into a SQLite table. Built week by week.

## Evaluation score (19 pytest checks)

| Stage | Checks passed |
|---|---|
| Week 4, first run | <X>/19 |
| Week 4, after improving the Week 3 prompt | <Y>/19 |

## What changed between the two runs
<which rules failed, and what you changed in the Week 3 prompt>

## Week 6: merging two sources

- Source 1: the cleaned CSV (100 movies). Source 2: a JSON file mapped to the same columns (60 movies, 60 of them also in the CSV).
- Movies are matched on `imdb_id`.
- **Conflict rule:** if only one source has a value, use it. If both have a value and only one passes the schema rules, keep that one. If both pass, keep the JSON value, because when both values pass the rules there is no way to tell which is right, so I chose a fixed tie-break and log every conflict in conflicts.csv for review. Every conflict is written to `conflicts.csv`.
- Result: 100 movies in `target.db`, 4 conflicts resolved, pytest score 19/19 after merging.
