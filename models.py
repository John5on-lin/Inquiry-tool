from dataclasses import dataclass

@dataclass
class Product:
    """产品数据模型"""
    sku: str
    quantity: float
    weight: float  # 单个产品重量(g)
    attribute: str  # 产品属性(如: 带电)
    length: float = 0.0  # 长度(cm)
    width: float = 0.0  # 宽度(cm)
    height: float = 0.0  # 高度(cm)
    price: float = 0.0
    ioss_price: float = 0.0  # IOSS价格
    image_url: str = ""  # 产品图片地址
    shipping_fee: float = 0.0  # 运费
    total: float = 0.0
    actual_weight: float = 0.0  # 实际重量(g)
    volume_weight: float = 0.0  # 体积重量(g)

@dataclass
class ShippingRule:
    """运费规则数据模型"""
    shipping_company: str  # 货代公司
    attribute: str  # 货物属性
    country: str  # 国家
    region: str  # 区域
    weight_min: float  # 重量下限(g)
    weight_max: float  # 重量上限(g)
    first_weight: float  # 首重（g）
    first_weight_fee: float  # 首重费用（元）
    additional_weight: float  # 续重（g）
    additional_weight_price: float  # 续重单价（元）
    min_delivery_days: int  # 时效最早天数
    max_delivery_days: int  # 时效最晚天数
    registration_fee: float  # 挂号费(RMB/票)

@dataclass
class IossRule:
    """IOSS税率规则数据模型"""
    country: str
    vat_rate: float  # VAT税率
    service_rate: float  # 服务费率

@dataclass
class Order:
    """订单数据模型，用于存储导入的订单Excel信息"""
    order_number: str
    order_status: str
    order_note: str
    payment_time: str
    country_code: str
    country: str
    product_name: str
    shop_name: str
    sku: str
    combination_sku: str
    quantity: int
    total_weight: float

@dataclass
class Invoice:
    """发票数据模型，用于展示最终发票信息"""
    country: str
    order_number: str
    product_cost: float
    shipping_cost: float
    redelivery_cost: float = 0.0
    total_charges: float = 0.0

@dataclass
class CalculationResult:
    """计算结果数据模型"""
    products: list[Product]
    total_amount: float
    ioss_taxes: float = 0.0  # IOSS税金总额