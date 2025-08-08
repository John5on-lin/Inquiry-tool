from dataclasses import dataclass

@dataclass
class Product:
    """产品数据模型"""
    name: str
    quantity: float
    weight: float  # 单个产品重量(KG)
    attribute: str  # 产品属性(如: 带电)
    length: float = 0.0  # 长度(cm)
    width: float = 0.0  # 宽度(cm)
    height: float = 0.0  # 高度(cm)
    price: float = 0.0
    ioss_price: float = 0.0  # IOSS价格
    image_url: str = ""  # 产品图片地址
    shipping_fee: float = 0.0  # 运费
    total: float = 0.0

@dataclass
class ShippingRule:
    """运费规则数据模型"""
    country: str
    attribute: str
    weight_min: float
    weight_max: float
    min_charge_weight: float
    shipping_rate: float
    registration_fee: float
    shipping_company: str  # 货代公司
    estimated_delivery_time: str  # 参考时效

@dataclass
class IossRule:
    """IOSS税率规则数据模型"""
    country: str
    vat_rate: float  # VAT税率
    service_rate: float  # 服务费率

@dataclass
class CalculationResult:
    """计算结果数据模型"""
    products: list[Product]
    total_amount: float
    ioss_taxes: float = 0.0  # IOSS税金总额