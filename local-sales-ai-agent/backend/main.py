"""Run: uvicorn backend.main:app --host 127.0.0.1 --port 8000"""
from typing import Literal
from fastapi import FastAPI,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field,field_validator
from backend.agent import Agent
from backend.ollama_client import OllamaError,DEFAULT_MODEL
from backend.logging_config import log_result
from backend.security_tests import TEST_CASES,run_case
from tools.sales_tools import DatabaseError

app=FastAPI(title='Local Sales Analytics AI Agent',version='1.0.0',description='Local Ollama inference and synthetic, read-only SQLite analytics.')
agent=Agent()

class ChatRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    message:str=Field(min_length=1,max_length=4000)
    model:str=Field(default=DEFAULT_MODEL,min_length=1,max_length=100,pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:/-]*$')
    security_mode:Literal['vulnerable','mitigated','mitigated_final']='mitigated'
    show_steps:bool=False

    @field_validator('message')
    @classmethod
    def nonempty(cls,value):
        if not value.strip(): raise ValueError('Message must not be blank.')
        return value.strip()

class SecurityRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    test_id:str=Field(max_length=40)
    model:str=Field(default=DEFAULT_MODEL,min_length=1,max_length=100,pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:/-]*$')

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse(status_code=422,content={'detail':'Invalid request. Use a nonempty message (max 4000 characters), an installed model name, security_mode vulnerable, mitigated or mitigated_final, and optional show_steps boolean. Extra fields are not accepted.'})

@app.get('/health')
def health():
    database=agent.sales.database_health()
    detail=[]
    try:
        local_models=agent.client.list_models()
        ollama=True
        if DEFAULT_MODEL not in local_models: detail.append('Default model missing. Run: ollama pull llama3.2:3b')
    except OllamaError as exc:
        ollama=False; local_models=[]; detail.append(str(exc))
    if not database: detail.append('Database missing or unreadable. Run: python -m database.create_database')
    return {'status':'ok' if ollama and database and DEFAULT_MODEL in local_models else 'degraded','ollama':ollama,'database':database,'default_model':DEFAULT_MODEL,'default_model_installed':DEFAULT_MODEL in local_models,'detail':detail}

@app.get('/models')
def models():
    try:
        available=agent.client.list_models()
        return {'models':available,'default_model':DEFAULT_MODEL,'warning':None if DEFAULT_MODEL in available else 'Run: ollama pull llama3.2:3b'}
    except OllamaError as exc: raise HTTPException(503,detail=str(exc)) from exc

@app.get('/dashboard')
def dashboard(month:str|None=None,product:str|None=None,category:str|None=None,region:str|None=None):
    try: return agent.sales.get_dashboard_data(month,product,category,region)
    except ValueError as exc: raise HTTPException(422,detail=str(exc)) from exc
    except DatabaseError as exc: raise HTTPException(503,detail=str(exc)) from exc

@app.post('/chat')
def chat(request:ChatRequest):
    result=agent.run(**request.model_dump())
    log_result(result)
    status=503 if result['error'] in ('ollama_unavailable','database_unavailable') else 200
    return JSONResponse(status_code=status,content=result)

@app.get('/security-tests')
def security_cases():
    return {'tests':TEST_CASES}

@app.post('/security-tests')
def security_test(request:SecurityRequest):
    case=next((c for c in TEST_CASES if c['id']==request.test_id),None)
    if case is None: raise HTTPException(422,detail='Unknown test_id. Use GET /security-tests to list safe test cases.')
    result=run_case(case,request.model,agent)
    for mode_result in result['results'].values(): log_result(mode_result['chat'])
    return result
