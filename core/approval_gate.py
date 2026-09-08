RISKY = [
    "payment", "spend", "dns", "delete production",
    "drop database", "secret", "api key",
    "force push", "domain transfer"
]

def needs_approval(command):
    text = command.lower()
    return any(x in text for x in RISKY)
