RISK_RULES = {
    "PAYMENT": ["payment", "spend", "charge", "purchase", "buy"],
    "PRODUCTION_DELETE": ["delete production", "drop database", "truncate", "destroy production"],
    "DNS_DOMAIN": ["dns", "domain transfer", "nameserver"],
    "SECRETS": ["secret", "api key", "access token", "password"],
    "GIT_FORCE": ["force push", "reset --hard"],
    "REAL_MESSAGE_SEND": ["send whatsapp", "bulk whatsapp", "send sms", "broadcast"],
}


def approval_reason(command):
    text = (command or "").lower()
    for reason, phrases in RISK_RULES.items():
        if any(phrase in text for phrase in phrases):
            return reason
    return None


def needs_approval(command):
    return approval_reason(command) is not None
