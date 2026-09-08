import os
from dotenv import load_dotenv
from openai import OpenAI
from core.master_prompt import load_master_prompt

load_dotenv()

DEFAULT_MODEL = os.getenv("POOH_MODEL", "gpt-5.6")


def think(command: str, context: str = "") -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI()
    master_prompt = load_master_prompt()
    user_input = command.strip()
    if context.strip():
        user_input = f"Context:\n{context.strip()}\n\nCommand:\n{user_input}"

    response = client.responses.create(
        model=DEFAULT_MODEL,
        instructions=master_prompt,
        input=user_input,
    )
    return response.output_text.strip()
