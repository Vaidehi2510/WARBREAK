import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "openrouter/auto"
PROVIDER = "openrouter"
provider_status = {"openrouter": "active", "fallback": "none"}

def call_llm(prompt: str, temperature: float = 0.3, max_tokens: int = 800) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers={
            "HTTP-Referer": "https://warbreak.app",
            "X-Title": "WARBREAK",
        }
    )
    return response.choices[0].message.content.strip()

def call_llm_json(prompt: str, temperature: float = 0.2, max_tokens: int = 800) -> str:
    suffix = "\n\nCRITICAL: Return ONLY raw JSON. No markdown. No backticks. No explanation. Start with { and end with }."
    return call_llm(prompt + suffix, temperature=temperature, max_tokens=800)