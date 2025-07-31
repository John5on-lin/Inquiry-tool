from dataclasses import dataclass

@dataclass
class Product:
    """产品数据模型"""
    name: str
    quantity: float
    price: float = 0.0
    total: float = 0.0

@dataclass
class CalculationResult:
    """计算结果数据模型"""
    products: list[Product]
    total_amount: float