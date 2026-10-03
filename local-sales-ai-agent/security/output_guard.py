"""Block recognizable canary/policy disclosure; semantic paraphrases may evade it."""
import base64
import re
import unicodedata
from security.system_prompts import DEMO_CANARY,PROTECTED_MARKERS
SECURITY_MESSAGE = 'Security guard blocked a request or response that attempted to expose protected instructions or information. Ask a sales analytics question instead.'

def compact(text):
    return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKC',text).casefold())

def leakage_reason(text):
    normalized = compact(text)
    if compact(DEMO_CANARY) in normalized:
        return 'protected_canary'
    for encoded in (base64.b64encode(DEMO_CANARY.encode()).decode(),DEMO_CANARY.encode().hex()):
        if encoded.lower() in text.lower():
            return 'encoded_canary'
    if any(compact(marker) in normalized for marker in PROTECTED_MARKERS):
        return 'protected_instructions'
    return None

def guard_output(text):
    reason = leakage_reason(text)
    return (SECURITY_MESSAGE,True,reason) if reason else (text,False,None)
