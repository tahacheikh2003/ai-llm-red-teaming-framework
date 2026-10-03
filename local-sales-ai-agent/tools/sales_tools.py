"""Small, read-only analytics tools. All user values use SQL parameters."""
from __future__ import annotations
import calendar
import sqlite3
from contextlib import closing
from pathlib import Path
from database.create_database import DEFAULT_DB_PATH, PRODUCTS, CATEGORIES, REGIONS

class DatabaseError(RuntimeError):
    pass

def normalize_month(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Month must be a month name or YYYY-MM, for example March or 2025-03.")
    value = value.strip()
    for number in range(1, 13):
        if value.lower() in (calendar.month_name[number].lower(), calendar.month_abbr[number].lower()):
            return f"2025-{number:02d}"
    if len(value) == 7 and value[:5] == '2025-' and value[5:].isdigit() and 1 <= int(value[5:]) <= 12:
        return value
    raise ValueError("Use a month in the synthetic 2025 dataset, such as March or 2025-03.")

def choice(value, options, label):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Invalid {label}.")
    for option in options:
        if value.strip().lower() == option.lower():
            return option
    raise ValueError(f"{label} must be one of: {', '.join(options)}.")

TOTALS = "COUNT(*) AS orders, COALESCE(SUM(quantity),0) AS quantity, ROUND(COALESCE(SUM(revenue),0),2) AS revenue, ROUND(COALESCE(SUM(profit),0),2) AS profit"

class SalesTools:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH).resolve()

    def _query(self, sql, params=()):
        if not self.db_path.is_file():
            raise DatabaseError("Database missing. Run: python -m database.create_database")
        try:
            with closing(sqlite3.connect(self.db_path.as_uri() + '?mode=ro', uri=True)) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA query_only = ON')
                return [dict(row) for row in conn.execute(sql, params).fetchall()]
        except sqlite3.Error as exc:
            raise DatabaseError("Database cannot be read. Rebuild the synthetic data with: python -m database.create_database --force") from exc

    def database_health(self):
        try:
            row = self._query('SELECT COUNT(*) AS count FROM sales')[0]
            return row['count'] > 0
        except DatabaseError:
            return False

    def get_monthly_sales(self, month=None):
        month = normalize_month(month)
        return self._query('SELECT month, ' + TOTALS + ' FROM sales' + (' WHERE month = ?' if month else '') + ' GROUP BY month ORDER BY month', (month,) if month else ())

    def get_top_products(self, month=None, limit=5, sort_by='revenue'):
        month = normalize_month(month)
        if type(limit) is not int or not 1 <= limit <= 7:
            raise ValueError('limit must be an integer between 1 and 7.')
        if sort_by not in ('revenue', 'quantity'):
            raise ValueError('sort_by must be revenue or quantity.')
        # sort_by is a fixed enum, never raw SQL from the user/model.
        return self._query('SELECT product, ' + TOTALS + ' FROM sales' + (' WHERE month = ?' if month else '') + ' GROUP BY product ORDER BY ' + sort_by + ' DESC, product LIMIT ?', (month, limit) if month else (limit,))

    def compare_sales_periods(self, period1, period2, product=None):
        period1, period2 = normalize_month(period1), normalize_month(period2)
        if period1 is None or period2 is None:
            raise ValueError('Both periods are required.')
        product = choice(product, PRODUCTS, 'product')
        def totals(period):
            return self._query('SELECT ' + TOTALS + ' FROM sales WHERE month = ?' + (' AND product = ?' if product else ''), (period, product) if product else (period,))[0]
        first, second = totals(period1), totals(period2)
        change = round(second['revenue'] - first['revenue'], 2)
        growth = round(change / first['revenue'] * 100, 2) if first['revenue'] else None
        growth_text = f'{growth:.2f}%' if growth is not None else 'undefined (zero baseline)'
        summary = (
            f"{product or 'All products'} revenue: {period1} USD {first['revenue']:.2f}; "
            f"{period2} USD {second['revenue']:.2f}. Change: USD {change:.2f} ({growth_text})."
        )
        return {'period1': {'month': period1, **first}, 'period2': {'month': period2, **second},
                'product': product, 'revenue_change': change, 'growth_rate_pct': growth,
                'summary': summary}

    def calculate_growth(self, period1, period2, product=None):
        return self.compare_sales_periods(period1, period2, product)

    def get_category_sales(self, category=None):
        category = choice(category, CATEGORIES, 'category')
        return self._query('SELECT category, ' + TOTALS + ' FROM sales' + (' WHERE category = ?' if category else '') + ' GROUP BY category ORDER BY revenue DESC', (category,) if category else ())

    def get_region_sales(self, region=None):
        region = choice(region, REGIONS, 'region')
        return self._query('SELECT region, ' + TOTALS + ' FROM sales' + (' WHERE region = ?' if region else '') + ' GROUP BY region ORDER BY revenue DESC', (region,) if region else ())

    def execute(self, name, arguments):
        registry = {name: getattr(self, name) for name in ('get_monthly_sales','get_top_products','compare_sales_periods','get_category_sales','get_region_sales','calculate_growth')}
        if name not in registry:
            raise ValueError('Tool is not approved.')
        return registry[name](**arguments)

    def get_dashboard_data(self, month=None, product=None, category=None, region=None):
        values = {'month':normalize_month(month), 'product':choice(product, PRODUCTS,'product'), 'category':choice(category,CATEGORIES,'category'), 'region':choice(region,REGIONS,'region')}
        clauses, params = [], []
        for column, value in values.items():
            if value is not None:
                clauses.append(column + ' = ?')
                params.append(value)
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        totals = self._query('SELECT ' + TOTALS + ' FROM sales' + where, params)[0]
        groups = {}
        for key, column in [('monthly','month'),('products','product'),('categories','category'),('regions','region')]:
            groups[key] = self._query('SELECT ' + column + ', ' + TOTALS + ' FROM sales' + where + ' GROUP BY ' + column + ' ORDER BY ' + ('month' if column == 'month' else 'revenue DESC'), params)
        best = sorted(groups['products'], key=lambda p: (-p['quantity'],p['product']))
        filters = {'months':[f'2025-{n:02d}' for n in range(1,13)],'products':list(PRODUCTS),'categories':list(CATEGORIES),'regions':list(REGIONS)}
        return {'kpis':{'total_revenue':totals['revenue'],'total_profit':totals['profit'],'number_of_orders':totals['orders'],'best_selling_product':best[0]['product'] if best else 'No orders'}, **groups, 'filters':filters}

def database_health(db_path=None):
    return SalesTools(db_path).database_health()
