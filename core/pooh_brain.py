from core.router import route_task
from core.project_manager import list_projects, assign_manager

def detect_project(task):
    text = task.lower()
    for project in list_projects():
        if project.replace("_", " ") in text or project in text:
            return project
    return "portfolio"

def analyze_task(task):
    project = detect_project(task)
    department = route_task(task)

    if project == "portfolio":
        manager = "portfolio_business_manager"
    else:
        manager = assign_manager(project)["manager"]

    return {
        "task": task,
        "project": project,
        "department": department,
        "manager": manager,
        "reports_to": "POOH"
    }
