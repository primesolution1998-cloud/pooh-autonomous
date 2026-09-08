import requests

def execute(project, department, project_data):
    if department in ("engineering", "qa", "operations"):
        url = project_data.get("domain") or project_data.get("url")
        if not url:
            return {"status":"FAILED","reason":"No project URL configured"}
        try:
            r = requests.get(url, timeout=15, allow_redirects=True)
            return {
                "status":"CHECKED",
                "url":r.url,
                "http_status":r.status_code,
                "healthy":200 <= r.status_code < 400
            }
        except Exception as e:
            return {"status":"FAILED","reason":str(e)}
    return {"status":"PLANNED","reason":"Specialist executor pending"}
