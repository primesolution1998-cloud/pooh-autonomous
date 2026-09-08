AGENT_ROUTES = {
    "engineering": ["website","app","bug","error","github","code","api","database","deploy"],
    "product": ["product","book","course","feature","pricing","offer","bundle"],
    "research": ["market","competitor","demand","trend","opportunity","location"],
    "growth": ["campaign","ads","seo","traffic","roas","conversion","growth"],
    "sales": ["lead","sales","followup","whatsapp","customer","crm","admission"],
    "content": ["reel","video","creative","script","post","copy","publish"],
    "finance": ["budget","revenue","expense","profit","loss","turnover","cac"],
    "qa": ["test","check","verify","security","performance"],
    "operations": ["status","progress","priority","plan","daily","report"]
}

def route_task(task):
    text = task.lower()
    scores = {
        department: sum(word in text for word in words)
        for department, words in AGENT_ROUTES.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "operations"
