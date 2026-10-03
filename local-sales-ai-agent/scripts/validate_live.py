"""Explicit opt-in live checks: real localhost HTTP, Ollama and SQLite."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from datetime import datetime, timezone
from tools.sales_tools import SalesTools

def main():
    evidence=[]
    sales=SalesTools()
    with httpx.Client(base_url='http://127.0.0.1:8000',trust_env=False,timeout=580) as client:
        health=client.get('/health').json()
        evidence.append({'check':'health','status':'PASS' if health['status']=='ok' else 'FAILED','detail':health})
        dashboard=client.get('/dashboard').json()
        evidence.append({'check':'dashboard API','status':'PASS' if dashboard['kpis']['number_of_orders']==2400 else 'FAILED'})
        cases=[
            ('Top product March','Which product had the highest revenue in March? Include the product name and revenue.','get_top_products'),
            ('Laptop comparison','Compare laptop sales between January and February. Include both revenue totals.','compare_sales_periods'),
            ('Region revenue','Which region generated the most revenue? Include the revenue.','get_region_sales'),
            ('Monthly growth','What was the monthly revenue growth rate from January to February?','calculate_growth'),
        ]
        for name,question,tool in cases:
            result=client.post('/chat',json={'message':question,'model':'llama3.2:3b','security_mode':'mitigated','show_steps':True}).json()
            passed=not result.get('error') and not result['blocked'] and tool in result['tools_used'] and 1<=result['iterations']<=3
            import re
            numbers=[float(n.replace(',','')) for n in re.findall(r'-?\d[\d,]*\.\d+',result['response'])]
            def contains_amount(value):
                return any(abs(n-value)<0.011 for n in numbers)
            if name=='Top product March':
                expected=sales.get_top_products('March',1)[0]
                passed=passed and expected['product'] in result['response'] and contains_amount(expected['revenue'])
            elif name=='Laptop comparison':
                expected=sales.compare_sales_periods('January','February','Laptop')
                passed=passed and all(contains_amount(expected[p]['revenue']) for p in ('period1','period2'))
            elif name=='Region revenue':
                expected=sales.get_region_sales()[0]
                passed=passed and expected['region'] in result['response'] and contains_amount(expected['revenue'])
            else:
                passed=passed and contains_amount(sales.calculate_growth('January','February')['growth_rate_pct'])
            evidence.append({'check':name,'status':'PASS' if passed else 'FAILED','detail':result})
            print(name,evidence[-1]['status'],result['response'],flush=True)
        folder = Path(__file__).resolve().parents[1] / "docs"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = folder / f"live-validation-mitigated-{stamp}.json"
        path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print('Saved',path,flush=True)
    return evidence

if __name__=='__main__': main()
