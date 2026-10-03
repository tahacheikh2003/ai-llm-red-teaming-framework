"""The immutable execution boundary is shared by all three security modes."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from tools.sales_tools import normalize_month,choice,PRODUCTS,CATEGORIES,REGIONS

class StrictArgs(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
class Monthly(StrictArgs):
    month: str|None=None
class Top(Monthly):
    limit:int=Field(default=5,ge=1,le=7)
    sort_by:Literal['revenue','quantity']='revenue'
class Compare(StrictArgs):
    period1:str
    period2:str
    product:Literal['Laptop','Smartphone','Tablet','Monitor','Headphones','Keyboard','Mouse']|None=None
class Category(StrictArgs):
    category:Literal['Computers','Mobile Devices','Accessories']|None=None
class Region(StrictArgs):
    region:Literal['North','South','East','West']|None=None

ARGUMENT_MODELS={'get_monthly_sales':Monthly,'get_top_products':Top,'compare_sales_periods':Compare,'get_category_sales':Category,'get_region_sales':Region,'calculate_growth':Compare}
ALLOWED_TOOLS=tuple(ARGUMENT_MODELS)

class ToolPolicyError(ValueError):
    pass

def validate_tool(name,arguments):
    if name not in ARGUMENT_MODELS:
        raise ToolPolicyError('Tool is not approved. Use an available sales tool.')
    try:
        values = ARGUMENT_MODELS[name].model_validate(arguments).model_dump()
        for key in ('month','period1','period2'):
            if key in values: values[key]=normalize_month(values[key])
        for key,options in [('product',PRODUCTS),('category',CATEGORIES),('region',REGIONS)]:
            if key in values: values[key]=choice(values[key],options,key)
        return values
    except (ValueError,TypeError) as exc:
        # Validation errors can echo malicious input. Return a fixed safe message.
        raise ToolPolicyError('Invalid tool arguments. Check required periods, 2025 months, allowed products/regions/categories, and limit 1-7.') from exc
