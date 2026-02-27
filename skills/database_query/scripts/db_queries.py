from typing import Optional, List, Dict, Any


def get_product_price(尺寸: str, 配置: str) -> Optional[Dict[str, Any]]:
    """
    查询商品价格
    
    Args:
        尺寸: 商品尺寸，如 "55寸"
        配置: 商品配置，如 "单系统/Win10/i5/8+256G"
    
    Returns:
        包含价格信息的字典，如果未找到返回 None
        示例: {"配置": "单系统/Win10/i5/8+256G", "尺寸": "55寸", "价格": 2350, "底价": 2290}
    """
    sql = f"SELECT * FROM 商品报价表 WHERE 尺寸 = '{尺寸}' AND 配置 = '{配置}'"
    return {"type": "sql_query", "sql": sql}


def get_product_by_size(尺寸: str) -> List[Dict[str, Any]]:
    """
    查询指定尺寸的所有商品配置
    
    Args:
        尺寸: 商品尺寸，如 "55寸"
    
    Returns:
        商品配置列表
    """
    sql = f"SELECT * FROM 商品报价表 WHERE 尺寸 = '{尺寸}'"
    return {"type": "sql_query", "sql": sql}


def get_available_configs(尺寸: str) -> List[str]:
    """
    查询指定尺寸的可用配置列表
    
    Args:
        尺寸: 商品尺寸，如 "55寸"
    
    Returns:
        配置列表
    """
    sql = f"SELECT DISTINCT 配置 FROM 商品报价表 WHERE 尺寸 = '{尺寸}'"
    return {"type": "sql_query", "sql": sql}


def get_size_info(尺寸: str) -> Optional[Dict[str, str]]:
    """
    查询尺寸的长宽厚信息
    
    Args:
        尺寸: 商品尺寸，如 "55寸"
    
    Returns:
        包含尺寸信息的字典，如果未找到返回 None
        示例: {"尺寸": "55寸", "长宽厚": "1270.1*768.4*96.2mm"}
    """
    sql = f"SELECT * FROM 尺寸表 WHERE 尺寸 = '{尺寸}'"
    return {"type": "sql_query", "sql": sql}


def get_all_sizes() -> List[Dict[str, str]]:
    """
    查询所有可用尺寸
    
    Returns:
        尺寸列表
    """
    sql = "SELECT * FROM 尺寸表"
    return {"type": "sql_query", "sql": sql}


def get_memory_upgrade(配置: str) -> List[Dict[str, Any]]:
    """
    查询内存硬盘升级报价
    
    Args:
        配置: 基础配置
    
    Returns:
        升级方案列表
    """
    sql = f"SELECT * FROM 内存硬盘升级报价表 WHERE 配置 = '{配置}'"
    return {"type": "sql_query", "sql": sql}


def get_processor_upgrade(机型: str) -> List[Dict[str, Any]]:
    """
    查询处理器升级报价
    
    Args:
        机型: 机型名称
    
    Returns:
        升级方案列表
    """
    sql = f"SELECT * FROM 处理器升级报价表 WHERE 机型 = '{机型}'"
    return {"type": "sql_query", "sql": sql}


def get_anti_glare_upgrade(尺寸: str) -> List[Dict[str, Any]]:
    """
    查询防眩光升级报价
    
    Args:
        尺寸: 商品尺寸
    
    Returns:
        升级方案列表
    """
    sql = f"SELECT * FROM 防眩光升级报价表 WHERE 尺寸 = '{尺寸}'"
    return {"type": "sql_query", "sql": sql}


def get_gifts() -> List[str]:
    """
    查询所有可用赠品
    
    Returns:
        赠品列表
    """
    sql = "SELECT 赠品 FROM 赠品表 ORDER BY 序列"
    return {"type": "sql_query", "sql": sql}


def search_script(script_type: str, query: str) -> Dict[str, Any]:
    """
    查询话术表
    
    Args:
        script_type: 话术表类型，可选值: "产品功能介绍", "常见问题", "开场了解需求"
        query: 查询关键词
    
    Returns:
        查询结果
    """
    table_mapping = {
        "产品功能介绍": "产品功能介绍话术_qa",
        "常见问题": "常见问题话术_qa",
        "开场了解需求": "开场了解需求话术_qa"
    }
    
    table_name = table_mapping.get(script_type)
    if not table_name:
        return {"error": f"未知的话术类型: {script_type}"}
    
    sql = f"SELECT * FROM {table_name}"
    return {"type": "sql_query", "sql": sql}


def calculate_final_price(
    基础价格: float,
    升级差价: float = 0,
    支架类型: str = "移动推车",
    开票类型: Optional[str] = None
) -> Dict[str, float]:
    """
    计算最终价格
    
    Args:
        基础价格: 商品基础价格
        升级差价: 配置升级的差价
        支架类型: "移动推车" 或 "壁挂"
        开票类型: None(不含税), "普票", 或 "专票"
    
    Returns:
        包含最终价格的字典
    """
    total = 基础价格 + 升级差价
    
    if 支架类型 == "壁挂":
        total -= 100
    
    if 开票类型 == "普票":
        total *= 1.03
    elif 开票类型 == "专票":
        total *= 1.10
    
    return {
        "基础价格": 基础价格,
        "升级差价": 升级差价,
        "支架调整": -100 if 支架类型 == "壁挂" else 0,
        "税费": total - (基础价格 + 升级差价 + (-100 if 支架类型 == "壁挂" else 0)),
        "最终价格": round(total, 2)
    }
