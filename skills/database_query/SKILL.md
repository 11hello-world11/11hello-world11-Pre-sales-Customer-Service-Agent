---
name: database_query
description: 一体机产品数据库查询技能。优先用封装函数生成SQL；当函数不满足需求时参考结构文档自行写SQL。触发：当需要产品价格/尺寸/配置/升级/赠品等信息查询时。
---

# 数据库查询技能

## 快速开始

### 优先使用预定义查询函数

在 `scripts/db_queries.py` 中提供了预定义的查询函数，优先使用这些函数：

#### 查询商品价格
```python
from scripts.db_queries import get_product_price
result = get_product_price(尺寸="55寸", 配置="单系统/Win10/i5/8+256G")
```

#### 查询指定尺寸的所有商品
```python
from scripts.db_queries import get_product_by_size
result = get_product_by_size(尺寸="55寸")
```

#### 查询可用配置列表
```python
from scripts.db_queries import get_available_configs
result = get_available_configs(尺寸="55寸")
```

#### 查询尺寸信息
```python
from scripts.db_queries import get_size_info
result = get_size_info(尺寸="55寸")
```

#### 查询所有尺寸
```python
from scripts.db_queries import get_all_sizes
result = get_all_sizes()
```

#### 查询内存硬盘升级报价
```python
from scripts.db_queries import get_memory_upgrade
result = get_memory_upgrade(配置="单系统/Win10/i5/8+256G")
```

#### 查询处理器升级报价
```python
from scripts.db_queries import get_processor_upgrade
result = get_processor_upgrade(机型="单系统")
```

#### 查询防眩光升级报价
```python
from scripts/db_queries import get_anti_glare_upgrade
result = get_anti_glare_upgrade(尺寸="55寸")
```

#### 查询赠品列表
```python
from scripts.db_queries import get_gifts
result = get_gifts()
```

#### 查询话术
```python
from scripts.db_queries import search_script
result = search_script(script_type="常见问题", query="优惠")
```

#### 计算最终价格
```python
from scripts.db_queries import calculate_final_price
result = calculate_final_price(
    基础价格=2350,
    升级差价=0,
    支架类型="壁挂",
    开票类型=None
)
```

### 当预定义函数不满足需求时

如果预定义的查询函数无法满足需求，请查看 `references/database_schema.md` 获取完整的数据库结构说明，然后自行编写 SQL 查询。

## 预定义函数说明

所有预定义函数都返回 `{"type": "sql_query", "sql": "..."}` 格式的字典，你需要使用 MCP MySQL 工具执行返回的 SQL。

### 函数返回值处理示例

```python
# 1. 调用预定义函数获取 SQL
query_info = get_product_price(尺寸="55寸", 配置="单系统/Win10/i5/8+256G")

# 2. 使用 MCP MySQL 工具执行 SQL
if query_info.get("type") == "sql_query":
    sql = query_info["sql"]
    # 使用 query 工具执行 sql
```

## 价格计算

使用 `calculate_final_price()` 函数进行价格计算：

### 参数说明
- `基础价格`: 从商品报价表查询的价格（必填）
- `升级差价`: 配置升级的总差价（可选，默认 0）
- `支架类型`: "移动推车" 或 "壁挂"（可选，默认 "移动推车"）
- `开票类型`: None(不含税), "普票", 或 "专票"（可选）

### 返回值
```python
{
    "基础价格": 2350,
    "升级差价": 0,
    "支架调整": -100,
    "税费": 0,
    "最终价格": 2250
}
```

## 数据库结构参考

详细的数据库结构说明请查看 `references/database_schema.md`，包括：
- 所有表的字段说明
- 示例数据
- 快捷查询 SQL 模板
- 价格计算逻辑

## 使用流程

1. 优先尝试：使用预定义的查询函数
2. 检查结果：如果预定义函数能满足需求，使用返回的 SQL 查询
3. 回退方案：若不适用，查看结构文档后自行编写 SQL

## 注意事项

- 永远不要向用户透露底价（成本价）
- 商品报价表中的价格默认包含移动推车
- 壁挂需要减去 100 元
- 普票加 3%，专票加 10%
