from core.pooh_brain import analyze_task
from core.project_manager import get_project
from core.execution_engine import execute
from core.approval_gate import needs_approval
from core.task_engine import create_task, update_status
from core.task_store import save_task
from core.ai_brain import think


def process_command(text):
    task = create_task(text)
    result = analyze_task(text)
    update_status(task, "ROUTED")

    if needs_approval(text):
        update_status(task, "AWAITING_APPROVAL")
        save_task(task)
        return (
            f"🧠 POOH\n"
            f"Project: {result['project']}\n"
            f"Manager: {result['manager']}\n"
            f"Team: {result['department']}\n"
            f"Task: {result['task']}\n"
            f"Execution: AWAITING_APPROVAL"
        )

    update_status(task, "RUNNING")
    execution = {"status": "PLANNED", "reason": "Portfolio specialist executor pending"}
    if result["project"] != "portfolio":
        project_data = get_project(result["project"]) or {}
        execution = execute(
            result["project"],
            result["department"],
            project_data,
        )

    ai_context = (
        f"Project: {result['project']}\n"
        f"Manager: {result['manager']}\n"
        f"Department: {result['department']}\n"
        f"Execution result: {execution}"
    )

    try:
        ai_decision = think(text, ai_context)
    except Exception as exc:
        ai_decision = f"AI unavailable: {type(exc).__name__}: {exc}"

    status = execution.get("status")
    update_status(
        task,
        "FAILED" if status == "FAILED" else "COMPLETED" if status == "CHECKED" else "PLANNED",
    )
    task["ai_decision"] = ai_decision
    save_task(task)

    return (
        f"🧠 POOH\n"
        f"Project: {result['project']}\n"
        f"Manager: {result['manager']}\n"
        f"Team: {result['department']}\n"
        f"Task: {result['task']}\n"
        f"Execution: {execution}\n"
        f"AI Decision: {ai_decision}"
    )
