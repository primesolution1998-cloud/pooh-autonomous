from core.pooh_brain import analyze_task

def process_command(text):
    result = analyze_task(text)
    return (
        f"🧠 POOH\n"
        f"Project: {result['project']}\n"
        f"Manager: {result['manager']}\n"
        f"Team: {result['department']}\n"
        f"Task: {result['task']}\n"
        f"Status: ROUTED"
    )
