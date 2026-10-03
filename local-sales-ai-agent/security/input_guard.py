"""Transparent heuristic screening, not a complete prompt-injection detector."""
import re
import unicodedata

def assess_input(message):
    text = unicodedata.normalize('NFKC',message).lower()
    patterns = {
        'instruction_override':r'\b(ignore|disregard|forget)\b.{0,60}\b(previous|prior|system|instructions|rules|role)\b',
        'prompt_extraction':r'\b(show|reveal|print|repeat|dump|give|expose|tell)\b.{0,70}\b(system prompt|system instructions|hidden instructions|hidden system|protected|demo value|secret)\b',
        'role_override':r'\byou are now\b.{0,40}\b(administrator|admin|unrestricted|developer)\b',
        'policy_override':r'\b(disable|bypass|override)\b.{0,40}\b(security|policy|policies|guard|restrictions)\b',
        'canary_request':r'demo[\s_-]*secret[\s_-]*2026|\bwhat is\b.{0,40}\b(protected|secret|demo value)\b',
    }
    signals = [name for name,pattern in patterns.items() if re.search(pattern,text,re.S)]
    if signals:
        return {'level':'high','signals':signals,'reject':True}
    suspicious = any(term in text for term in ('system prompt','hidden instruction','administrator','prompt injection'))
    return {'level':'medium' if suspicious else 'low','signals':['security_related_language'] if suspicious else [],'reject':False}
