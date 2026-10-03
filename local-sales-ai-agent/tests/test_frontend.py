from unittest.mock import patch
import httpx
import streamlit as st
from streamlit.testing.v1 import AppTest
from frontend.ui_logic import comparison_rows
from tools.sales_tools import SalesTools
from backend.security_tests import TEST_CASES

def test_empty_metrics_and_denominators():
    rows=comparison_rows([],'m')
    assert next(r for r in rows if r['Metric']=='Attack success rate')['Before mitigation']=='Not measured'
    def run(verdict,kind='attack',model='m'):
        return {'model':model,'kind':kind,'results':{m:{'verdict':verdict,'chat':{'blocked':False}} for m in ('vulnerable','mitigated')}}
    rows=comparison_rows([run('failed'),run('passed'),run('error'),run('inconclusive'),run('failed',model='other')],'m')
    assert next(r for r in rows if r['Metric']=='Attack success rate')['Before mitigation']=='50.0%'
    assert next(r for r in rows if r['Metric']=='Execution errors')['Before mitigation']==1

def handler(self,method,url,**kwargs):
    path=url.split(':8000')[-1]
    if path=='/models': data={'models':['llama3.2:3b','mistral:7b'],'default_model':'llama3.2:3b'}
    elif path=='/health': data={'database':True,'ollama':True,'detail':[]}
    elif path=='/dashboard': data=SalesTools().get_dashboard_data(**kwargs.get('params',{}))
    elif path=='/security-tests': data={'tests':TEST_CASES}
    else: raise AssertionError(path)
    return httpx.Response(200,json=data,request=httpx.Request(method,url))

def test_dashboard_filters_modes_and_model_selection():
    st.cache_data.clear()
    with patch.object(httpx.Client,'request',handler):
        at=AppTest.from_file('frontend/app.py',default_timeout=20).run()
        assert not at.exception
        assert [metric.label for metric in at.metric]==['Total Revenue','Total Profit','Orders','Best Selling Product']
        assert at.metric[2].value=='2,400'
        assert len(at.get('plotly_chart'))==4
        at.selectbox(key='filter_month').select('2025-03').run()
        assert at.metric[2].value=='200'
        at.radio[0].set_value('Vulnerable').run()
        assert not at.exception and at.radio[0].value=='Vulnerable'
        model_box=next(box for box in at.selectbox if box.label=='Local LLM Model')
        model_box.select('mistral:7b').run()
        assert not at.exception
        assert next(box for box in at.selectbox if box.label=='Local LLM Model').value=='mistral:7b'

def test_backend_unavailable_shows_help():
    st.cache_data.clear()
    def offline(*args,**kwargs): raise httpx.ConnectError('Offline')
    with patch.object(httpx.Client,'request',offline):
        at=AppTest.from_file('frontend/app.py',default_timeout=20).run()
        assert not at.exception
        assert any('Cannot reach FastAPI' in err.value for err in at.error)
        assert at.chat_input[0].disabled
