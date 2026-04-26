import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client: OpenAI | None = None

MODEL = "openrouter/auto"

def get_client() -> OpenAI:
    global client
    if client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured.")
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    return client

def call_llm(prompt: str, temperature: float = 0.3, max_tokens: int = 1500) -> str:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers={
            "HTTP-Referer": "https://warbreak.app",
            "X-Title": "WARBREAK"
        }
    )
    return response.choices[0].message.content.strip()

def call_llm_json(prompt: str, temperature: float = 0.2, max_tokens: int = 1500) -> str:
    suffix = "\n\nCRITICAL: Return ONLY raw JSON. No markdown. No backticks. No explanation. Start with { and end with }."
    return call_llm(prompt + suffix, temperature=temperature, max_tokens=max_tokens)
