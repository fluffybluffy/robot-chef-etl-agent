from load_data import load_raw
from llm import ask

df = load_raw()

sample = df.head(20).to_string()
info = 'Columns and types:\n' + df.dtypes.to_string()

system = (
    'You are a data quality analyst. You will receive a sample of a messy '
    'movie dataset. List every data quality issue you can find. Group them '
    'by column. For each issue give a short description and one or two real '
    'example values from the sample. Do not fix anything yet.'
)

reply = ask(system, [{'role': 'user', 'content': info + '\n\nSample (first 20 rows):\n' + sample}])

print(reply)

with open('ai_issues.txt', 'w') as f:
    f.write(reply)
print('\nSaved to ai_issues.txt')
