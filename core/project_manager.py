import json

def load_portfolio():
    with open("projects/portfolio.json", encoding="utf-8") as f:
        return json.load(f)

def get_project(name):
    projects = load_portfolio()
    return projects.get(name.lower())

def list_projects():
    return load_portfolio()

def assign_manager(project):
    return {
        "project": project,
        "manager": f"{project}_business_manager",
        "reports_to": "POOH",
        "objective": "maximize profitable growth",
        "status": "ACTIVE"
    }
