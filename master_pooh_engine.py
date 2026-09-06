import os
import json
import time

QUEUE_FILE = "tasks_queue.json"

def init_queue():
    if not os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "w") as f:
            json.dump([], f)

def add_task(task_name):
    init_queue()
    with open(QUEUE_FILE, "r") as f:
        tasks = json.load(f)
    tasks.append({"task": task_name, "status": "pending"})
    with open(QUEUE_FILE, "w") as f:
        json.dump(tasks, f, indent=4)
    print(f"[MASTER POOH] Task added: {task_name}")

if __name__ == "__main__":
    init_queue()
    print("[MASTER POOH ENGINE] Initialized and ready to process local workspace tasks.")
