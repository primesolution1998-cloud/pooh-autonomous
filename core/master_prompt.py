from pathlib import Path

MASTER_PROMPT_PATH = Path(__file__).parent.parent / "config" / "MASTER_PROMPT.md"

def load_master_prompt():
    return MASTER_PROMPT_PATH.read_text(encoding="utf-8")
