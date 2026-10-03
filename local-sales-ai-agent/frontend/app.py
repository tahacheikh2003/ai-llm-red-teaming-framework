"""Presentation only: every data/model request goes through FastAPI."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import httpx
import pandas as pd
import plotly.express as px
import streamlit as st
from frontend.ui_logic import comparison_rows

API_URL='http://127.0.0.1:8000'
DEFAULT_MODEL='llama3.2:3b'
st.set_page_config(page_title='Local Sales | AI Analytics',page_icon='📊',layout='wide',initial_sidebar_state='expanded')
st.markdown("""
<style>
.stApp {background:#f5f7fb;}
[data-testid="stSidebar"] {background:#101e35;}
[data-testid="stSidebar"] * {color:#e5eef9;}
[data-testid="stSidebar"] button p {color:#10243b;}\n[data-testid="stSidebar"] input {color:#10243b;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#10243b;}
[data-testid="stMetric"] {background:white;border:1px solid #e1e8f0;padding:20px;border-radius:14px;box-shadow:0 3px 12px #10243b05;}
[data-testid="stMetricLabel"] {color:#596a80;}
[data-testid="stMetricValue"] {color:#10243b;font-size:1.9rem;}
.block-container {padding-top:4rem;padding-bottom:3rem;max-width:1500px;}
h1,h2,h3 {color:#10243b;letter-spacing:-.03em;}
.hero-label {color:#078b80;font-size:.78rem;font-weight:700;letter-spacing:.16em;}
.hero-caption {color:#65758b;margin-bottom:1.2rem;}
.stTabs [data-baseweb="tab-list"] {gap:22px;margin-bottom:18px;}
</style>
""",unsafe_allow_html=True)

def api(method,path,**kwargs):
    try:
        with httpx.Client(trust_env=False,timeout=httpx.Timeout(1700,connect=3)) as client:
            response=client.request(method,API_URL+path,**kwargs)
        body=response.json()
        if response.status_code>=400:
            raise RuntimeError(body.get('detail') or body.get('response') or f'Backend returned HTTP {response.status_code}.')
        return body
    except httpx.ConnectError as exc:
        raise RuntimeError('Cannot reach FastAPI. From the project folder run: .venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000') from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError('The local request timed out. Check Ollama and backend logs, then retry with a smaller local model.') from exc
    except (httpx.HTTPError,ValueError) as exc:
        raise RuntimeError('The backend returned an unreadable response. Check that FastAPI is running on port 8000.') from exc

@st.cache_data(ttl=15,show_spinner=False)
def model_list():
    return api('GET','/models')

@st.cache_data(ttl=30,show_spinner=False)
def dashboard_data(**filters):
    return api('GET','/dashboard',params=filters)

def show_steps(response):
    if response.get('steps'):
        with st.expander('Agent execution steps'):
            for step in response['steps']:
                st.caption(f"Iteration {step['iteration']} · {step.get('tool',step.get('action','action'))}")
                st.json(step,expanded=False)
    else:
        st.caption('No execution steps were returned.')

def show_result(response,debug):
    if response.get('error'): st.error(response['response'])
    elif response.get('blocked'): st.warning(response['response'])
    else: st.text(response['response'])
    st.caption(f"{response['model']} · {response['security_mode'].replace('_',' ').title()} · {response['iterations']}/3 iterations · Tools: {', '.join(response['tools_used']) or 'none'}")
    if debug: show_steps(response)

with st.sidebar:
    st.markdown('## ◈ LOCAL SALES')
    st.caption('Analytics & AI security lab')
    st.divider()
    mode=st.radio('Security Mode',['Vulnerable','Mitigated','Mitigated Final'],index=1).lower().replace(' ','_')
    if mode=='vulnerable': st.warning('Vulnerable mode: prompt-only protection. Synthetic data only.')
    elif mode=='mitigated': st.success('Mitigated mode: original layered guards active.')
    else: st.success('Mitigated Final: scope, capability and observation guards active.')
    models=[]
    try:
        info=model_list()
        models=info['models']
        if DEFAULT_MODEL not in models:
            st.warning('The default model is not installed.')
            st.code('ollama pull llama3.2:3b',language='powershell')
    except RuntimeError as exc:
        st.error(str(exc))
    model=st.selectbox('Local LLM Model',models or [DEFAULT_MODEL],index=models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0,disabled=not models)
    if st.button('Refresh models & data',width='stretch'):
        st.cache_data.clear()
        st.rerun()
    debug=st.checkbox('Show Agent Steps',value=False)
    st.caption('Structured tool calls and observations only.')
    st.divider()
    try:
        health=api('GET','/health')
        st.caption(('●' if health['database'] else '○')+' SQLite · '+('●' if health['ollama'] else '○')+' Ollama')
        for detail in health.get('detail',[]): st.caption(detail)
    except RuntimeError as exc: st.caption(str(exc))
    st.caption('100% local inference · Synthetic 2025 data')
    st.caption('Cloud model entries are excluded.')

st.markdown('<div class="hero-label">LOCAL INTELLIGENCE / SALES ANALYTICS</div>',unsafe_allow_html=True)
st.title('Sales performance, clearly.')
st.markdown('<div class="hero-caption">Explore the business. Ask the agent. Measure the defenses.</div>',unsafe_allow_html=True)
badge={'vulnerable':'🧪 Vulnerable','mitigated':'🛡️ Mitigated','mitigated_final':'🛡️ Mitigated Final'}[mode]
st.caption(f'ACTIVE MODE: {badge}  ·  MODEL: {model}  ·  DATASET: JAN–DEC 2025 / USD')

overview,assistant,security=st.tabs(['Sales Overview','AI Assistant','Security Test'])
with overview:
    try:
        base=dashboard_data()
        cols=st.columns(4)
        filters={}
        for col,key,label in zip(cols,['month','product','category','region'],['Month','Product','Category','Region']):
            options=base['filters'][{'month':'months','product':'products','category':'categories','region':'regions'}[key]]
            selected=col.selectbox(label,['All']+options,key='filter_'+key)
            if selected!='All': filters[key]=selected
        data=dashboard_data(**filters) if filters else base
        kpi=data['kpis']
        cols=st.columns(4)
        cols[0].metric('Total Revenue','$'+f"{kpi['total_revenue']:,.0f}")
        cols[1].metric('Total Profit','$'+f"{kpi['total_profit']:,.0f}")
        cols[2].metric('Orders',f"{kpi['number_of_orders']:,}")
        cols[3].metric('Best Selling Product',kpi['best_selling_product'])
        st.caption('Best selling = units sold. Filters apply to these charts; include the desired period or product explicitly in chat.')
        def chart(rows,x,title,kind='bar',color='#0aa99a'):
            st.subheader(title)
            if not rows:
                st.info('No orders match the selected filters.')
                return
            frame=pd.DataFrame(rows)
            fig=px.area(frame,x=x,y='revenue',markers=True) if kind=='area' else px.bar(frame,x=x,y='revenue',text_auto='.3s')
            _ = fig.update_traces(marker_color=color) if kind=='bar' else fig.update_traces(line_color=color,fillcolor='rgba(10,169,154,0.12)')
            _ = fig.update_layout(height=315,margin=dict(l=12,r=12,t=12,b=12),paper_bgcolor='white',plot_bgcolor='white',font=dict(color='#42546c'),xaxis_title=None,yaxis_title='Revenue (USD)',showlegend=False)
            _ = fig.update_yaxes(gridcolor='#edf1f6')
            st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        left,right=st.columns([1.2,1])
        with left: chart(data['monthly'],'month','Revenue over time','area')
        with right: chart(data['products'],'product','Revenue by product',color='#356bc2')
        left,right=st.columns(2)
        with left: chart(data['categories'],'category','Revenue by category',color='#6d75c5')
        with right: chart(data['regions'],'region','Sales by region')
        with st.expander('View aggregated sales data'):
            st.dataframe(pd.DataFrame(data['products']),hide_index=True,width='stretch')
    except RuntimeError as exc:
        st.error(str(exc))

with assistant:
    st.subheader('Ask your local sales analyst')
    st.caption('Each question starts a fresh agent run. Chat history is displayed here but is not sent back to the model.')
    st.info('Try: “Which product had the highest revenue in March?” · “Compare laptop sales between January and February.” · “Which region generated the most revenue?”')
    if 'chat_history' not in st.session_state: st.session_state.chat_history=[]
    if st.button('Clear chat'): st.session_state.chat_history=[]
    for item in st.session_state.chat_history:
        with st.chat_message('user'): st.text(item['question'])
        with st.chat_message('assistant'): show_result(item['answer'],debug)
    question=st.chat_input('Ask about the synthetic sales data…',disabled=not models,max_chars=4000)
    if question:
        with st.chat_message('user'): st.text(question)
        with st.chat_message('assistant'):
            try:
                with st.spinner('Querying your local agent…'):
                    answer=api('POST','/chat',json={'message':question,'model':model,'security_mode':mode,'show_steps':debug})
                show_result(answer,debug)
                st.session_state.chat_history.append({'question':question,'answer':answer})
            except RuntimeError as exc: st.error(str(exc))

with security:
    st.subheader('One application. Three security modes.')
    st.write('Run a safe demonstration through FastAPI and compare the observed results. The same selected model is used in all three modes.')
    if 'security_history' not in st.session_state: st.session_state.security_history=[]
    try:
        cases=api('GET','/security-tests')['tests']
        selected=st.selectbox('Demonstration',[case['id'] for case in cases],format_func=lambda value:next(c['label'] for c in cases if c['id']==value))
        case=next(c for c in cases if c['id']==selected)
        st.code(case['prompt'],language=None,wrap_lines=True)
        run_col,clear_col=st.columns([1,3])
        run=run_col.button('Run all three modes',type='primary',disabled=not models,width='stretch')
        if clear_col.button('Clear executed results'):
            st.session_state.security_history=[]
        if run:
            with st.spinner('Running the same test in all three modes…'):
                result=api('POST','/security-tests',json={'test_id':selected,'model':model})
            st.session_state.security_history.append(result)
    except RuntimeError as exc: st.error(str(exc))
    history=[r for r in st.session_state.security_history if r['model']==model]
    if history:
        latest=history[-1]
        st.caption(f"Latest execution: {latest['label']} · {latest['timestamp']}")
        for col,security_mode,label in zip(st.columns(3),['vulnerable','mitigated','mitigated_final'],['Vulnerable','Mitigated','Mitigated Final']):
            with col:
                st.markdown('#### '+label)
                if security_mode not in latest['results']:
                    st.info('Not executed in this historical run.')
                    continue
                result=latest['results'][security_mode]
                message=f"{result['verdict'].upper()} — {result['reason']}"
                {'passed':st.success,'failed':st.error,'inconclusive':st.warning,'error':st.error}[result['verdict']](message)
                show_result(result['chat'],debug)
    else:
        st.info('No tests executed for this model yet. Run a demonstration to measure real outcomes.')
    st.markdown('#### Before vs After')
    st.dataframe(pd.DataFrame(comparison_rows(st.session_state.security_history,model)).astype(str),hide_index=True,width='stretch')
    st.caption('Rates use executed tests for the selected model only. Attack rate = observed successes / conclusive attack tests. Errors and inconclusive outcomes are excluded; normal failures remain in the normal-question denominator. Results are heuristic, not a security guarantee.')
    if history:
        st.download_button('Download executed results (JSON)',json.dumps(history,indent=2),file_name='sales-security-results.json',mime='application/json')
        with st.expander('Executed test history'):
            st.dataframe(pd.DataFrame([{'Time':r['timestamp'],'Test':r['label'],'Model':r['model'],'Vulnerable':r['results']['vulnerable']['verdict'],'Mitigated':r['results']['mitigated']['verdict'],'Mitigated Final':r['results'].get('mitigated_final',{}).get('verdict','Not executed')} for r in history]),hide_index=True,width='stretch')
    st.caption('Results live in this browser session. Download them before closing or refreshing the session.')

st.divider()
st.caption('LOCAL SALES AI AGENT  /  University AI security lab  /  No real customer information')
