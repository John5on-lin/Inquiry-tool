from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Product:
    """产品模型"""
    name: str
    quantity: float
    price: Optional[float] = None
    total: Optional[float] = None

    def __repr__(self):
        return f"Product(name='{self.name}', quantity={self.quantity}, price={self.price}, total={self.total})

@dataclass
class CalculationResult:
    """计算结果模型"""
    products: List[Product] = None
    total_amount: float = 0.0
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.products is None:
            self.products = []