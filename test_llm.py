from llm import ask

print(ask('You are a helpful assistant.',
          [{'role': 'user', 'content': 'Reply with exactly one word: ready'}],
          max_tokens=20))
