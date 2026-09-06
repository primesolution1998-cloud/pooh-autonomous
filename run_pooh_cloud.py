from keep_alive import keep_alive
keep_alive()
import time
import json
import os

QUEUE_FILE = "tasks_queue.json"

def process_queue():
    if not os.path.exists(QUEUE_FILE):
        return
    with open(QUEUE_FILE, "r") as f:
        try:
            tasks = json.load(f)
        except:
            tasks = []
            
    for task in tasks:
        if task["status"] == "pending":
            print(f"[POOH WORKER] Processing task: {task['task']}")
            time.sleep(2)
            task["status"] = "completed"
            print(f"[POOH WORKER] Task completed: {task['task']}")
            
    with open(QUEUE_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

if __name__ == "__main__":
    print("[POOH CLOUD RUNNER] Worker active. Monitoring tasks_queue.json...")
    while True:
        process_queue()
        time.sleep(5)
