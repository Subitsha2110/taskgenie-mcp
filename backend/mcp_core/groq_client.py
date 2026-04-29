# Groq LLM Client
# Loads API key from .env and wraps Groq SDK calls.

import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load .env from backend/
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def call_llm(prompt: str) -> str:
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        stream=False,
    )
    return response.choices[0].message.content
