from core.pooh_brain import analyze_task
from core.project_manager import get_project
from core.execution_engine import execute
from core.approval_gate import needs_approval

def process_command(text):
    result = analyze_task(text)

    if needs_approval(text):
        return (
            f"🧠 POOH\n"
            f"Project: {result['project']}\n"
            f"Manager: {result['manager']}\n"
            f"Team: {result['department']}\n"
            f"Task: {result['task']}\n"
            f"Execution: AWAITING_APPROVAL"
        )

    execution = {"status":"ROUTED"}
    if result["project"] != "portfolio":
        project_data = get_project(result["project"]) or {}
        execution = execute(
            result["project"],
            result["department"],
            project_data
        )

    return (
        f"🧠 POOH\n"
        f"Project: {result['project']}\n"
        f"Manager: {result['manager']}\n"
        f"Team: {result['department']}\n"
        f"Task: {result['task']}\n"
        f"Execution: {execution}"
    )
