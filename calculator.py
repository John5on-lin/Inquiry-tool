from typing import List, Dict, Any
import logging
from config import AppConfig
from shipping_fetcher import GoogleSheetsShippingSource
from ioss_fetcher import IossFetcher
from models import Product, ShippingRule, CalculationResult, IossRule

logger = logging.getLogger(__name__)

class Calculator:
    """价格计算器，包含产品价格、运费和IOSS税金计算逻辑"""
    # 使用类变量缓存shipping_rules
    _shipping_rules_cache = None
    _data_source_cache = None

    def __init__(self, config: AppConfig):
        self.config = config
        
        # 初始化或复用data_source
        if Calculator._data_source_cache is None:
            Calculator._data_source_cache = GoogleSheetsShippingSource(config)
        self.data_source = Calculator._data_source_cache
        
        # 加载或复用shipping_rules
        if Calculator._shipping_rules_cache is None:
            Calculator._shipping_rules_cache = self.data_source.load_rules()
        self.shipping_rules = Calculator._shipping_rules_cache
        
        self.ioss_fetcher = IossFetcher(config)

    def find_applicable_shipping_rules(self, products: List[Product], destination: str) -> List[Dict[str, Any]]:
        """查找所有适用的运费规则,给前端展示

        Args:
            products: 产品列表
            destination: 目的地国家

        Returns:
            适用运费规则列表
        """
        # 计算累积物品重量
        total_weight = sum(product.quantity * product.weight for product in products)
        logger.info(f"累积物品重量: {total_weight}KG")

        # 默认设定产品属性为"带电"
        attribute = "带电"

        # 查找适用的运费规则
        applicable_rules = [
            rule for rule in self.shipping_rules
            if rule.country.lower() == destination.lower()
            and rule.attribute.lower() == attribute.lower()
            and rule.weight_min < total_weight <= rule.weight_max
        ]

        if not applicable_rules:
            logger.warning(f"未找到适用的运费规则: 国家={destination}, 属性={attribute}, 重量={total_weight}")
            return []

        # 转换为字典列表直接返回
        return [{
            'id': i,
            'shipping_company': rule.shipping_company,
            'country': rule.country,
            'attribute': rule.attribute,
            'weight_min': rule.weight_min,
            'weight_max': rule.weight_max,
            'min_charge_weight': rule.min_charge_weight,
            'shipping_rate': rule.shipping_rate,
            'estimated_delivery_time': rule.estimated_delivery_time,
            'registration_fee': rule.registration_fee,
        } for i, rule in enumerate(applicable_rules)]

    def calculate_total_shipping_fee(self, products: List[Product], destination: str) -> tuple[float, dict]:
        """计算所有产品的总运费，包含寻找运输规则的逻辑

        Args:
            products: 产品列表
            destination: 目的地国家

        Returns:
            总运费金额和规则信息
        """
        # 计算累积物品重量
        total_weight = sum(product.quantity * product.weight for product in products)
        logger.info(f"累积物品重量: {total_weight}KG")

        # 默认设定产品属性为"带电"
        attribute = "带电"

        # 查找适用的运费规则
        applicable_rules = [
            rule for rule in self.shipping_rules
            if rule.country.lower() == destination.lower()
            and rule.attribute.lower() == attribute.lower()
            and rule.weight_min < total_weight <= rule.weight_max
        ]

        if not applicable_rules:
            logger.warning(f"未找到适用的运费规则: 国家={destination}, 属性={attribute}, 重量={total_weight}")
            return 0.0, {}

        # 锁定第一条适用规则
        rule = applicable_rules[0]

        # 记录命中的规则信息
        logger.info(f"使用运费规则: 国家={rule.country}, 属性={rule.attribute}, 重量范围={rule.weight_min}-{rule.weight_max}KG, 最低计费重={rule.min_charge_weight}KG, 运费率={rule.shipping_rate}RMB/KG, 挂号费={rule.registration_fee}RMB/票")

        # 计算运费: max(物品重量,最低计费重) * 运费 + 挂号费
        charge_weight = max(total_weight, rule.min_charge_weight)
        shipping_fee = charge_weight * rule.shipping_rate + rule.registration_fee

        logger.info(f"计算总运费成功: 重量={total_weight}, 运费={shipping_fee}")

        # 返回运费和规则信息
        rule_info = {
            'shipping_company': rule.shipping_company,
            'estimated_delivery_time': rule.estimated_delivery_time,
            'shipping_rate': rule.shipping_rate,
            'registration_fee': rule.registration_fee,
            'actual_weight': total_weight
        }

        return shipping_fee, rule_info

    def calculate_shipping_fee(self, products: List[Product], selected_shipping_rules: dict) -> tuple[float, dict]:
        """计算产品的运费

        Args:
            products: 产品列表
            rule: 选择的运费规则

        Returns:
            运费金额和使用的规则信息
        """
        # 计算累积物品重量
        total_weight = sum(product.quantity * product.weight for product in products)
        logger.info(f"累积物品重量: {total_weight}KG")

        # 记录命中的规则信息
        logger.info(f"使用运费规则: 国家={selected_shipping_rules['country']}, 属性={selected_shipping_rules['attribute']}, 重量范围={selected_shipping_rules['weight_min']}-{selected_shipping_rules['weight_max']}KG, 最低计费重={selected_shipping_rules['min_charge_weight']}KG, 运费率={selected_shipping_rules['shipping_rate']}RMB/KG, 挂号费={selected_shipping_rules['registration_fee']}RMB/票")

        # 计算运费: max(物品重量,最低计费重) * 运费 + 挂号费
        charge_weight = max(total_weight, selected_shipping_rules['min_charge_weight'])
        shipping_fee = charge_weight * selected_shipping_rules['shipping_rate'] + selected_shipping_rules['registration_fee']

        logger.info(f"计算运费成功: 总重量={total_weight}, 运费={shipping_fee}")

        # 返回运费和规则信息
        rule_info = {
            'shipping_company': selected_shipping_rules.get('shipping_company', ''),
            'estimated_delivery_time': selected_shipping_rules.get('estimated_delivery_time', ''),
            'shipping_rate': selected_shipping_rules.get('shipping_rate', 0),
            'registration_fee': selected_shipping_rules.get('registration_fee', 0),
            'actual_weight': total_weight
        }

        return shipping_fee, rule_info

    def calculate_total_ioss_tax(self, products: List[Product], destination: str) -> tuple[float, Dict[str, Any]]:
        """计算所有产品的总IOSS税金并返回相关信息"""
        logger.info(f"开始计算所有产品的IOSS税金，目的地: {destination}")

        # 计算总IOSS价格
        total_ioss_price = sum(product.ioss_price * product.quantity for product in products if product.ioss_price > 0)
        logger.info(f"总IOSS价格: {total_ioss_price}")

        if total_ioss_price <= 0:
            logger.warning("所有产品的IOSS价格均无效，无法计算IOSS税金")
            return 0.0, {}

        # 获取IOSS税率规则
        ioss_rule = self.ioss_fetcher.get_ioss_rule(destination)
        if not ioss_rule:
            logger.warning(f"未找到目的地'{destination}'的IOSS税率规则，无法计算IOSS税金")
            return 0.0, {}

        # 计算VAT税费和服务费（注意：税率已在ioss_fetcher中转换为小数）
        vat_tax = total_ioss_price * ioss_rule.vat_rate
        service_fee = total_ioss_price * ioss_rule.service_rate
        total_ioss_tax = vat_tax + service_fee

        logger.info(f"计算IOSS税金成功: 总IOSS价格={total_ioss_price}, VAT税率={ioss_rule.vat_rate*100}%, 服务费率={ioss_rule.service_rate*100}%, VAT税费={vat_tax:.2f}, 服务费={service_fee:.2f}, 总IOSS税金={total_ioss_tax:.2f}")

        # 返回总IOSS税金和规则信息
        ioss_info = {
            'vat_rate': ioss_rule.vat_rate,
            'service_rate': ioss_rule.service_rate,
            'vat_tax': vat_tax,
            'service_fee': service_fee,
            'total_ioss_tax': total_ioss_tax,
            'total_ioss_price': total_ioss_price
        }

        return total_ioss_tax, ioss_info

    def calculate_totals(self, products: List[Product], destination: str, selected_shipping_rules: dict = None) -> tuple[CalculationResult, dict, dict]:
        """计算产品总价、运费和IOSS税金的累计值"""
        if not products:
            return CalculationResult(products=[], total_amount=0.0, ioss_taxes=0.0), {}, {}

        # 检查selected_shipping_rules是否为空
        if not selected_shipping_rules:
            logger.error("未选择运费规则")
            raise ValueError("请先选择运费规则")

        # 检查必要字段是否存在
        required_fields = ['shipping_company']
        for field in required_fields:
            if field not in selected_shipping_rules:
                logger.error(f"运费规则缺少必要字段: {field}")
                raise ValueError(f"运费规则缺少必要字段: {field}")

        # 计算总运费
        total_shipping_fee, rule_info = self.calculate_shipping_fee(products, selected_shipping_rules)

        # 计算产品基础总价
        total_product_price = 0.0
        for product in products:
            if product.total <= 0 and product.price > 0:
                logger.info(f"开始计算，产品 {product.name} 总价格")
                product.total = product.price * product.quantity
            total_product_price += product.total

        # 计算总IOSS税金
        total_ioss_tax, ioss_info = self.calculate_total_ioss_tax(products, destination)

        # 计算总金额（产品基础总价 + 总IOSS税金 + 总运费）
        total_amount = total_product_price + total_ioss_tax + total_shipping_fee

        # 保存总运费和总IOSS税金到每个产品
        for product in products:
            product.shipping_fee = total_shipping_fee / len(products)  # 平均分摊运费
            product.ioss_tax = total_ioss_tax / len(products)  # 平均分摊IOSS税金
            product.total = product.total + product.shipping_fee + product.ioss_tax

        logger.info(f"总产品基础价格: {total_product_price}, 总IOSS税金: {total_ioss_tax}, 总运费: {total_shipping_fee}, 总金额: {total_amount}")

        return CalculationResult(products=products, total_amount=total_amount, ioss_taxes=total_ioss_tax), rule_info, ioss_info