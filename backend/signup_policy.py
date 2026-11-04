"""Private-beta enrollment gate; allowlisting never verifies mailbox ownership."""
from backend.auth_store import email_value

def policy(env):
    mode=env.get('PETSENSE_SIGNUP_MODE','open')
    if mode not in ('open','closed','allowlist'):raise ValueError('Invalid enrollment policy')
    entries=env.get('PETSENSE_SIGNUP_ALLOWLIST','')
    if len(entries)>32000:raise ValueError('Enrollment list too large')
    allowed={email_value(value) for value in entries.split(',') if value.strip()}
    if len(allowed)>100 or (mode=='allowlist' and not allowed):raise ValueError('Invalid enrollment list')
    return mode,allowed

def permitted(env,email):
    mode,allowed=policy(env)
    return mode=='open' or (mode=='allowlist' and email_value(email) in allowed)
