import pandas as pd

df = pd.read_csv('data/messy_IMDB_dataset.csv', sep=';',
                   encoding='utf-8', encoding_errors='replace')

print(df.head())
print(df.info())
print('Nulls per column:')
print(df.isnull().sum())
print('Duplicate rows:', df.duplicated().sum())
print(df.describe())




# FINDINGS
# - 101 rows and 12 columns loaded: 100 movies plus 1 completely empty row.
# - 'Unnamed: 8' is a fully empty column with no name.
# - Column names are messy: odd characters ('Original titlÊ', 'Genrë¨'),
#   a typo ('IMBD'), and stray spaces (' Votes ').
# - Almost every column is stored as text, even ones that should be numbers
#   or dates (Release year, Duration, Income, Votes, Score).
# - Release year is written in many date formats.
# - Numeric columns contain symbols, letters and mixed separators:
#   Income '$ 4o8,035,783', Votes '2.278.845', Score '9,.0', Duration '178c', 'Inf', 'Nan'.
# - Country has spelling variants: 'US', 'USA', 'US.', 'New Zesland', 'Italy1'.
# - Missing values: Content Rating (24), Duration (2).
# - No duplicate rows.