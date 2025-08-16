from typing import List, Dict, Any
import logging
import math
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
        # 计算产品总重量和收集产品属性
        total_weight = 0
        product_attributes = set()
        for product in products:
            total_weight += product.quantity * product.weight
            product_attributes.add(product.attribute)
        logger.info(f"累积物品重量: {total_weight}g")

        # 定义属性优先级: 药品 > 保健品 > 敏感品 > 带电 > 普货
        attribute_priority = ['药品', '保健品', '敏感品', '带电', '普货']

        # 根据优先级确定最高优先级的属性
        for attr in attribute_priority:
            if attr in product_attributes:
                attribute = attr
                break
        else:
            attribute = '普货'  # 默认值

        logger.info(f"确定最高优先级属性: {attribute}")

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

        # 转换为字典列表直接返回，并包含total_weight
        return [{
            'id': i,
            'shipping_company': rule.shipping_company,
            'country': rule.country,
            'attribute': rule.attribute,
            'region': rule.region,
            'weight_min': rule.weight_min,
            'weight_max': rule.weight_max,
            'first_weight': rule.first_weight,
            'first_weight_fee': round(rule.first_weight_fee, 3),
            'additional_weight': rule.additional_weight,
            'additional_weight_price': round(rule.additional_weight_price, 3),
            'min_delivery_days': rule.min_delivery_days,
            'max_delivery_days': rule.max_delivery_days,
            'registration_fee': rule.registration_fee,
            'volume_weight_ratio': rule.volume_weight_ratio,
            'total_weight': total_weight  # 添加total_weight到返回数据中
        } for i, rule in enumerate(applicable_rules)]

    def calculate_shipping_fee(self, products: List[Product], selected_shipping_rules: dict) -> tuple[float, dict]:
        """计算产品的运费

        Args:
            products: 产品列表
            selected_shipping_rules: 选择的运费规则

        Returns:
            运费金额和使用的规则信息
        """
        # 尝试从selected_shipping_rules中获取total_weight
        total_weight = selected_shipping_rules.get('total_weight')
        
        # 如果没有提供total_weight，则计算
        if total_weight is None:
            total_weight = sum(product.quantity * product.weight for product in products)
            logger.info(f"计算累积物品重量: {total_weight}g")
        else:
            logger.info(f"使用已计算的累积物品重量: {total_weight}g")

        # 记录命中的规则信息
        logger.info(f"使用运费规则: 国家={selected_shipping_rules['country']}, 属性={selected_shipping_rules['attribute']}, 区域={selected_shipping_rules['region']}, 重量范围={selected_shipping_rules['weight_min']}-{selected_shipping_rules['weight_max']}g, 首重={selected_shipping_rules['first_weight']}g, 首重费用={selected_shipping_rules['first_weight_fee']}元, 续重={selected_shipping_rules['additional_weight']}g, 续重单价={selected_shipping_rules['additional_weight_price']}元, 挂号费={selected_shipping_rules['registration_fee']}元/票")

        # 计算运费
        first_weight = selected_shipping_rules['first_weight']
        first_weight_fee = selected_shipping_rules['first_weight_fee']
        additional_weight = selected_shipping_rules['additional_weight']
        additional_weight_price = selected_shipping_rules['additional_weight_price']
        registration_fee = selected_shipping_rules['registration_fee']

        if total_weight <= first_weight:
            # 未超过首重
            shipping_fee = first_weight_fee + registration_fee
        else:
            # 超过首重，计算续重费用
            remaining_weight = total_weight - first_weight
            # 计算需要多少个续重单位
            additional_units = remaining_weight / additional_weight
            # 向上取整
            additional_units = math.ceil(additional_units)
            shipping_fee = first_weight_fee + (additional_units * additional_weight_price) + registration_fee

        logger.info(f"计算运费成功: 总重量={total_weight}g, 运费={shipping_fee}")

        # 计算时效信息
        min_days = selected_shipping_rules['min_delivery_days']
        max_days = selected_shipping_rules['max_delivery_days']
        estimated_delivery_time = f"{min_days}-{max_days}天" if min_days > 0 and max_days > 0 else ""

        # 返回运费和规则信息
        rule_info = {
            'shipping_company': selected_shipping_rules.get('shipping_company', ''),
            'region': selected_shipping_rules.get('region', ''),
            'estimated_delivery_time': estimated_delivery_time,
            'min_delivery_days': min_days,
            'max_delivery_days': max_days,
            'first_weight': first_weight,
            'first_weight_fee': first_weight_fee,
            'additional_weight': additional_weight,
            'additional_weight_price': additional_weight_price,
            'registration_fee': registration_fee,
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