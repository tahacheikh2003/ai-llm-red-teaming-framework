"""Metadata-only JSON logs: no user prompts, system prompts or model text."""
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime,timezone
from pathlib import Path
from security.output_guard import leakage_reason

def configure_logging():
    logger=logging.getLogger('sales_agent')
    if not logger.handlers:
        folder=Path(__file__).resolve().parents[1]/'logs'
        folder.mkdir(exist_ok=True)
        handler=RotatingFileHandler(folder/'application.jsonl',maxBytes=2_000_000,backupCount=2,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate=False
    return logger

def log_result(result):
    metadata={key:result.get(key) for key in ('request_id','model','security_mode','tools_used','iterations','blocked','guard','error')}
    if leakage_reason(str(metadata.get('model',''))): metadata['model']='[redacted]'
    metadata['timestamp']=datetime.now(timezone.utc).isoformat()
    configure_logging().info(json.dumps(metadata))
