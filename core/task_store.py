import json
import os
import tempfile
from pathlib import Path

STORE = Path(os.getenv("POOH_TASK_STORE", "projects/task_history.json"))


def _load():
    if not STORE.exists():
        return []
    try:
        with STORE.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write(data):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="pooh-task-", suffix=".json", dir=str(STORE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STORE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save_task(task):
    data = _load()
    replaced = False
    for i, existing in enumerate(data):
        if existing.get("id") == task.get("id"):
            data[i] = task
            replaced = True
            break
    if not replaced:
        data.append(task)
    _write(data)
    return task


def get_task(task_id):
    for task in reversed(_load()):
        if task.get("id") == task_id:
            return task
    return None


def list_tasks(limit=50, status=None):
    data = _load()
    if status:
        data = [x for x in data if x.get("status") == status]
    return list(reversed(data[-max(1, min(int(limit), 500)):]))
