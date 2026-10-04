from dotenv import load_dotenv
import anthropic

load_dotenv()  # reads ANTHROPIC_API_KEY from your .env file

# If you get a "model not found" error, check the exact name at
# https://docs.claude.com/en/docs/about-claude/models and paste it here.
MODEL = 'claude-sonnet-5-5'

client = anthropic.Anthropic()


def ask(system, messages, max_tokens=8000):
    """Send one request to Claude and return the reply text."""
    resp = client.messages.create(
        model=MODEL, max_tokens=max_tokens,
        system=system, messages=messages)
    if resp.stop_reason == 'max_tokens':
        print('\nWARNING: the reply was cut off. Raise max_tokens and run again.\n')
    # keep only the text blocks (ignores any thinking blocks)
    return ''.join(b.text for b in resp.content if b.type == 'text')
