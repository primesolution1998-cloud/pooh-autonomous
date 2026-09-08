import json, os

STORE = "projects/task_history.json"

def save_task(task):
    os.makedirs("projects", exist_ok=True)
    data = []
    if os.path.exists(STORE):
        try:
            with open(STORE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(task)
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return task
