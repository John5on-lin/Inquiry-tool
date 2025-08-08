from typing import List, Dict, Any
import logging
from config import AppConfig
from shipping_fetcher import GoogleSheetsShippingSource
from ioss_fetcher import IossFetcher
from models import Product, ShippingRule, CalculationResult, IossRule

logger = logging.getLogger(__name__)

class Calculator:
    """价格计算器，包含产品价格、运费和IOSS税金计算逻辑"""
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_source = GoogleSheetsShippingSource(config)
        self.shipping_rules = self.data_source.load_rules()
        self.ioss_fetcher = IossFetcher(config)

    def calculate_shipping_fee(self, product: Product) -> tuple[float, dict]:
        """计算单个产品的运费并返回运费规则信息"""
        # 计算物品重量 = 数量 * 重量
        item_weight = product.quantity * product.weight

        # 查找适用的运费规则
        applicable_rules = [
            rule for rule in self.shipping_rules
            if rule.country.lower() == product.destination.lower()
            and rule.attribute.lower() == product.attribute.lower()
            and rule.weight_min < item_weight <= rule.weight_max
        ]

        if not applicable_rules:
            logger.warning(f"未找到适用的运费规则: 国家={product.destination}, 属性={product.attribute}, 重量={item_weight}")
            return 0.0, {}

        # 使用找到的第一条规则
        rule = applicable_rules[0]

        # 记录命中的规则信息
        logger.info(f"命中运费规则: 国家={rule.country}, 属性={rule.attribute}, 重量范围={rule.weight_min}-{rule.weight_max}KG, 最低计费重={rule.min_charge_weight}KG, 运费率={rule.shipping_rate}RMB/KG, 挂号费={rule.registration_fee}RMB/票")

        # 计算运费: max(物品重量,最低计费重) * 运费 + 挂号费
        charge_weight = max(item_weight, rule.min_charge_weight)
        shipping_fee = charge_weight * rule.shipping_rate + rule.registration_fee

        logger.info(f"计算运费成功: 产品={product.name}, 重量={item_weight}, 运费={shipping_fee}")

        # 返回运费和规则信息
        rule_info = {
            'shipping_company': rule.shipping_company,
            'estimated_delivery_time': rule.estimated_delivery_time,
            'shipping_rate': rule.shipping_rate,
            'registration_fee': rule.registration_fee,
            'actual_weight': item_weight
        }

        return shipping_fee, rule_info

    def calculate_ioss_tax(self, product: Product) -> tuple[float, Dict[str, Any]]:
        """计算单个产品的IOSS税金并返回相关信息"""
        # 获取IOSS税率规则
        ioss_rule = self.ioss_fetcher.get_ioss_rule(product.destination)
        if not ioss_rule:
            return 0.0, {}

        # 计算VAT税费和服务费
        vat_tax = product.ioss_price * product.quantity * ioss_rule.vat_rate
        service_fee = product.ioss_price * product.quantity * ioss_rule.service_rate
        ioss_tax = vat_tax + service_fee

        logger.info(f"计算IOSS税金成功: 产品={product.name}, VAT税费={vat_tax:.2f}, 服务费={service_fee:.2f}, 总IOSS税金={ioss_tax:.2f}")

        # 返回IOSS税金和规则信息
        ioss_info = {
            'vat_rate': ioss_rule.vat_rate,
            'service_rate': ioss_rule.service_rate,
            'vat_tax': vat_tax,
            'service_fee': service_fee,
            'ioss_tax': ioss_tax
        }

        return ioss_tax, ioss_info

    def calculate_product_total(self, product: Product) -> tuple[float, dict, dict]:
        """计算单个产品的总价(包含运费和IOSS税金)并返回相关信息"""
        # 计算基础价格
        base_price = product.price * product.quantity
        # 计算运费
        shipping_fee, rule_info = self.calculate_shipping_fee(product)
        # 保存运费
        product.shipping_fee = shipping_fee
        # 计算IOSS税金
        ioss_tax, ioss_info = self.calculate_ioss_tax(product)
        # 保存IOSS税金
        product.ioss_tax = ioss_tax
        # 计算总价
        total_price = base_price + shipping_fee + ioss_tax
        # 保存总价
        product.total = total_price

        return total_price, rule_info, ioss_info

    @staticmethod
    def calculate_totals(products: List[Product]) -> CalculationResult:
        """计算产品总价、运费和IOSS税金的累计值"""
        total_amount = 0.0
        total_ioss_taxes = 0.0

        for product in products:
            if product.total <= 0 and product.price > 0:
                logger.warning(f"产品 {product.name} 的总价未设置，将使用基础价格")
                product.total = product.price * product.quantity

            total_amount += product.total
            total_ioss_taxes += getattr(product, 'ioss_tax', 0.0)

        return CalculationResult(products=products, total_amount=total_amount, ioss_taxes=total_ioss_taxes)