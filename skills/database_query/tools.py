from langchain_core.tools import tool
from .scripts import db_queries as dq


@tool
def dbq_price_by_size_config(尺寸: str, 配置: str) -> dict:
    """
    查询指定尺寸与配置的商品价格。用于直接获取某个尺寸+配置的一行报价数据。
    """
    r = dq.get_product_price(尺寸, 配置)
    return r


@tool
def dbq_configs_by_size(尺寸: str) -> dict:
    """
    查询给定尺寸下的可用配置列表。用于快速获取该尺寸下所有配置选项。
    """
    r = dq.get_available_configs(尺寸)
    return r


@tool
def dbq_i5_i7_price_rows(尺寸: str) -> dict:
    """
    一次性查询同一尺寸下 i5 与 i7 相关配置的价格行。用于对比 i5 与 i7 价格差。
    """
    sql = f"SELECT 配置, 尺寸, 价格, 底价 FROM 商品报价表 WHERE 尺寸 = '{尺寸}' AND (配置 LIKE '%i5%' OR 配置 LIKE '%i7%')"
    return {"type": "sql_query", "sql": sql}


@tool
def dbq_size_info(尺寸: str) -> dict:
    """
    查询指定尺寸的长宽厚等尺寸信息。用于生成报价单中的尺寸字段。
    """
    r = dq.get_size_info(尺寸)
    return r
