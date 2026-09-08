import uuid
from datetime import datetime, timezone

def create_task(command):
    return {
        "id": str(uuid.uuid4())[:8],
        "command": command,
        "status": "RECEIVED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "history": ["RECEIVED"]
    }

def update_status(task, status):
    task["status"] = status
    task["history"].append(status)
    return task
