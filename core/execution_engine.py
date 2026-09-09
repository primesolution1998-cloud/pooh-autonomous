import os
import requests


def _health_check(project_data):
    url = project_data.get("domain") or project_data.get("url")
    if not url:
        return {"status": "FAILED", "reason": "No project URL configured"}
    try:
        r = requests.get(url, timeout=15, allow_redirects=True)
        return {
            "status": "CHECKED",
            "url": r.url,
            "http_status": r.status_code,
            "healthy": 200 <= r.status_code < 400,
        }
    except Exception as exc:
        return {"status": "FAILED", "reason": str(exc)}


def _cmts_check(project_data):
    base = os.getenv("CMTS_BASE_URL") or project_data.get("cmts_url")
    if not base:
        return {"status": "PLANNED", "reason": "CMTS_BASE_URL not configured"}
    try:
        r = requests.get(base.rstrip("/") + "/health", timeout=10)
        return {"status": "CHECKED", "service": "cmts", "http_status": r.status_code, "healthy": r.ok}
    except Exception as exc:
        return {"status": "FAILED", "reason": f"CMTS check failed: {exc}"}


def execute(project, department, project_data):
    department = (department or "").lower()
    if department in ("engineering", "qa", "operations", "deployment", "support"):
        site = _health_check(project_data)
        if project.lower() == "leadsindia":
            site["cmts"] = _cmts_check(project_data)
        return site
    if department in ("marketing", "seo", "finance", "writing", "publishing", "whatsapp_crm"):
        return {
            "status": "PLANNED",
            "reason": "Specialist plan generated; external side effects require an explicit adapter and approval where applicable",
        }
    return {"status": "PLANNED", "reason": "No executor registered for this department"}
