import sqlite3
import pytest
from database.create_database import create_database, generate_sales_rows
from tools.sales_tools import SalesTools, DatabaseError, normalize_month

@pytest.fixture
def sales(tmp_path):
    db = tmp_path / 'sales.db'
    create_database(db, None)
    return SalesTools(db)

def test_database(sales):
    assert sales.database_health()
    rows = generate_sales_rows()
    assert len(rows) == 2400 and len({r['month'] for r in rows}) == 12
    assert all(round(r['revenue']-r['cost'],2) == r['profit'] for r in rows)
    assert all(r['salesperson'].startswith('SYNTH-REP-') for r in rows)

def test_months(sales):
    assert normalize_month('March') == '2025-03'
    assert len(sales.get_monthly_sales()) == 12
    assert sales.get_monthly_sales('March')[0]['orders'] == 200

def test_top_products(sales):
    top = sales.get_top_products('March',7)
    assert len(top)==7 and top[0]['revenue'] >= top[-1]['revenue']
    assert sum(p['revenue'] for p in top) == pytest.approx(sales.get_monthly_sales('March')[0]['revenue'])
    quantities = sales.get_top_products(sort_by='quantity')
    assert quantities[0]['quantity'] >= quantities[-1]['quantity']

def test_compare_growth(sales):
    comparison = sales.compare_sales_periods('January','February','Laptop')
    first,second = comparison['period1']['revenue'],comparison['period2']['revenue']
    assert comparison['revenue_change'] == round(second-first,2)
    assert comparison['growth_rate_pct'] == round((second-first)/first*100,2)
    assert comparison == sales.calculate_growth('January','February','Laptop')

def test_category_region(sales):
    assert len(sales.get_category_sales()) == 3
    assert len(sales.get_region_sales()) == 4
    assert sales.get_category_sales('computers')[0]['category']=='Computers'
    assert sales.get_region_sales('north')[0]['region']=='North'
    assert sum(r['revenue'] for r in sales.get_region_sales()) == pytest.approx(sum(r['revenue'] for r in sales.get_category_sales()))

def test_dashboard(sales):
    all_data = sales.get_dashboard_data()
    filtered = sales.get_dashboard_data(month='March',product='Laptop',region='North')
    assert all_data['kpis']['number_of_orders']==2400
    assert filtered['kpis']['number_of_orders'] < 200
    assert filtered['products'][0]['product']=='Laptop'
    assert filtered['filters']==all_data['filters']
    assert sales.get_dashboard_data(product='Laptop',category='Accessories')['kpis']['number_of_orders']==0

@pytest.mark.parametrize('method,args', [('get_monthly_sales',{'month':"March'; DROP TABLE sales;--"}),('get_top_products',{'limit':True}),('get_top_products',{'limit':999}),('get_top_products',{'sort_by':'revenue;DROP TABLE sales'}),('get_region_sales',{'region':'Moon'}),('compare_sales_periods',{'period1':None,'period2':'March'})])
def test_validation(sales,method,args):
    with pytest.raises(ValueError):
        sales.execute(method,args)
    assert sales.database_health()

def test_no_arbitrary_tool_or_missing_db(sales,tmp_path):
    with pytest.raises(ValueError): sales.execute('_query',{'sql':'DELETE FROM sales'})
    missing = SalesTools(tmp_path/'missing.db')
    with pytest.raises(DatabaseError): missing.get_monthly_sales()
    assert not missing.db_path.exists()

def test_readonly_connection(sales):
    with pytest.raises(DatabaseError): sales._query('DELETE FROM sales')
    assert sales.get_dashboard_data()['kpis']['number_of_orders']==2400
