from load_data import load_raw

df = load_raw()

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

# WEEK 2 COMPARISON (AI report vs my findings)
# - AI found, I missed: the day/month order is ambiguous (09 21 1972 vs 18/11/1976),
#   and two-digit years do not say which century they mean.
# - AI found, I missed: genres and directors hold several values in one cell.
# - AI found, I missed: 'Approved' is an old rating, and 'Not Rated' is not the same as missing.
# - AI found, I missed: Duration 220 for The Godfather: Part II looks wrong (as far as I know it is 202).
# - I found, AI missed: Country spellings further down the file, such as 'US.' and 'Italy1'.
#   The AI only saw the first 20 rows.
