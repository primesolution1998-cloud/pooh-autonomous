from core.pooh_brain import analyze_task
from core.project_manager import get_project
from core.execution_engine import execute
from core.approval_gate import needs_approval, approval_reason
from core.task_engine import create_task, update_status
from core.task_store import save_task, get_task
from core.ai_brain import think


def _run_task(task, result):
    update_status(task, "RUNNING")
    project_data = get_project(result["project"]) or {}
    execution = {"status": "PLANNED", "reason": "Portfolio specialist executor pending"}
    if result["project"] != "portfolio":
        execution = execute(result["project"], result["department"], project_data)

    ai_context = (
        f"Project: {result['project']}\n"
        f"Manager: {result['manager']}\n"
        f"Department: {result['department']}\n"
        f"Execution result: {execution}"
    )
    try:
        ai_decision = think(task["command"], ai_context)
    except Exception as exc:
        ai_decision = f"AI unavailable: {type(exc).__name__}: {exc}"

    status = execution.get("status")
    update_status(task, "FAILED" if status == "FAILED" else "COMPLETED" if status == "CHECKED" else "PLANNED")
    task["execution"] = execution
    task["ai_decision"] = ai_decision
    save_task(task)
    return task, result


def process_command(text):
    task = create_task(text)
    result = analyze_task(text)
    task["routing"] = result
    update_status(task, "ROUTED")

    if needs_approval(text):
        update_status(task, "AWAITING_APPROVAL")
        task["approval_reason"] = approval_reason(text)
        save_task(task)
        return (
            f"🧠 POOH\nTask ID: {task['id']}\nProject: {result['project']}\n"
            f"Manager: {result['manager']}\nTeam: {result['department']}\nTask: {result['task']}\n"
            f"Execution: AWAITING_APPROVAL ({task['approval_reason']})"
        )

    task, result = _run_task(task, result)
    return (
        f"🧠 POOH\nTask ID: {task['id']}\nProject: {result['project']}\n"
        f"Manager: {result['manager']}\nTeam: {result['department']}\nTask: {result['task']}\n"
        f"Execution: {task.get('execution')}\nAI Decision: {task.get('ai_decision')}"
    )


def approve_task(task_id):
    task = get_task(task_id)
    if not task:
        return {"ok": False, "error": "task_not_found"}
    if task.get("status") != "AWAITING_APPROVAL":
        return {"ok": False, "error": "task_not_awaiting_approval", "status": task.get("status")}
    result = task.get("routing") or analyze_task(task.get("command", ""))
    update_status(task, "APPROVED")
    task["approved"] = True
    task, _ = _run_task(task, result)
    return {"ok": True, "task": task}
