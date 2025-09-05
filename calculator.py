from typing import List, Dict, Any
from collections import defaultdict
import logging
import math
from config import AppConfig
from shipping_fetcher import GoogleSheetsShippingSource
from price_fetcher import PriceFetcher
from ioss_fetcher import IossFetcher
from models import Product, ShippingRule, CalculationResult, IossRule, Order, Invoice

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
        self.price_fetcher = PriceFetcher(config)

    def find_applicable_shipping_rules(self, products: List[Product], destination: str, volume_weight_ratio: int) -> List[Dict[str, Any]]:
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
            # 计算实际重量
            actual_weight = product.quantity * product.weight
            # 存储实际重量到产品对象
            product.actual_weight = actual_weight
            
            # 计算体积重量（如果长、宽、高都有值）
            if product.length and product.width and product.height:
                volume_weight = product.length * product.width * product.height / volume_weight_ratio
                # 体积重量乘以数量
                volume_weight *= product.quantity
                # 存储体积重量到产品对象
                product.volume_weight = volume_weight
                # 取实际重量和体积重量中的较大值
                product_total_weight = max(actual_weight, volume_weight)
            else:
                product.volume_weight = 0
                product_total_weight = actual_weight
            
            total_weight += product_total_weight
            product_attributes.add(product.attribute)
        logger.info(f"累积物品重量: {total_weight}g")

        # 定义属性优先级: 食品 > 纯电 > 特货 > 带电 > 普货
        attribute_priority = ['食品', '纯电', '特货', '带电', '普货']

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
                logger.info(f"开始计算，产品 {product.sku} 总价格")
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

    def _group_orders_by_number(self, orders: List[Order]) -> Dict[str, List[Order]]:
        """按交易编号分组订单的辅助方法"""
        grouped = defaultdict(list)
        for order in orders:
            grouped[order.order_number].append(order)
        return grouped

    def calculate_order_totals(self, orders: List[Order]) -> tuple[Dict[str, float], Dict[str, float]]:
        """同时计算每个订单的产品总价和IOSS费用

        Args:
            orders: 订单对象列表

        Returns:
            tuple: 包含产品总价字典和IOSS费用字典的元组
        """
        if not orders:
            logger.warning("订单列表为空，无法计算订单总计")
            return {}, {}

        # 获取第一个订单的国家作为基准
        base_country = orders[0].country
        # 验证所有订单国家是否一致
        for order in orders:
            if order.country.lower() != base_country.lower():
                logger.warning(f"订单国家不一致: 基准国家={base_country}, 订单{order.order_number}国家={order.country}")

        # 只获取一次IOSS规则
        ioss_rule = self.ioss_fetcher.get_ioss_rule(base_country)
        if not ioss_rule:
            logger.warning(f"未找到国家'{base_country}'的IOSS税率规则，所有订单IOSS费用将为0")
            ioss_available = False
        else:
            ioss_available = True

        # 获取产品数据(利用缓存机制)
        product_data = self.price_fetcher.data_source.load_product_data()

        # 按交易编号分组订单
        grouped_orders = self._group_orders_by_number(orders)

        order_product_totals = {}
        order_ioss_totals = {}

        for order_number, order_list in grouped_orders.items():
            total_order_price = 0.0
            # 计算产品总价
            for order in order_list:
                # 优先使用uniform_cost_price，如果有值的话
                if order.uniform_cost_price > 0:
                    total_order_price += order.uniform_cost_price * order.quantity
                    logger.info(f"使用统一成本价: {order.sku}, 单价: {order.uniform_cost_price}, 数量: {order.quantity}")
                elif order.sku in product_data:
                    # 否则使用product_data中的价格
                    price = product_data[order.sku]['price']
                    total_order_price += price * order.quantity
                else:
                    logger.warning(f"未找到SKU '{order.sku}' 的价格信息")

            order_product_totals[order_number] = total_order_price
            logger.info(f"订单 '{order_number}' 的产品价格总和: {total_order_price:.2f} 元")

            # 计算IOSS费用
            if total_order_price > 0 and ioss_available:
                ioss_cost = total_order_price * (ioss_rule.vat_rate + ioss_rule.service_rate)
                order_ioss_totals[order_number] = round(ioss_cost, 2)
                logger.info(f"订单 '{order_number}' 的IOSS费用: {ioss_cost:.2f} 元")
            else:
                order_ioss_totals[order_number] = 0.0
                if total_order_price <= 0:
                    logger.warning(f"订单 '{order_number}' 的产品总价无效: {total_order_price}")
                else:
                    logger.info(f"订单 '{order_number}' 未计算IOSS费用: 国家规则不存在")

        return order_product_totals, order_ioss_totals

    def create_invoices(self, orders: List[Order], order_totals: Dict[str, float], order_ioss_totals: Dict[str, float], shipping_cost_map: Dict[str, float]) -> List[Invoice]:
        """创建发票对象列表

        Args:
            orders: 订单对象列表
            order_totals: 每个订单的产品价格总和字典
            order_ioss_totals: 每个订单的IOSS费用字典

        Returns:
            发票对象列表
        """
        # 按交易编号分组订单
        grouped_orders = self._group_orders_by_number(orders)

        # 创建发票对象
        invoices = []
        for order_number, order_list in grouped_orders.items():
            # 取第一个订单的国家信息
            country = order_list[0].country if order_list else ''
            # 获取产品总价
            product_cost = order_totals.get(order_number, 0.0)
            # 获取IOSS费用
            ioss_cost = order_ioss_totals.get(order_number, 0.0)
            # 获取并验证运费
            shipping_cost = shipping_cost_map.get(order_number, 0.0)
            
            # 验证运费值
            if order_number not in shipping_cost_map:
                logger.warning(f"订单 '{order_number}' 未找到对应的运费记录，将使用默认值0.0")
            elif shipping_cost < 0:
                logger.error(f"订单 '{order_number}' 的运费值为负数 ({shipping_cost})，已修正为0.0")
                shipping_cost = 0.0
            
            # 创建发票
            invoice = Invoice(
                country=country,
                order_number=order_number,
                product_cost=product_cost,
                shipping_cost=shipping_cost,
                ioss_cost=ioss_cost, 
                redelivery_cost=0.0
            )
            
            # 计算总费用
            invoice.total_charges = invoice.product_cost + invoice.shipping_cost + invoice.ioss_cost + invoice.redelivery_cost
            invoices.append(invoice)
            logger.info(f"已创建发票: 订单编号 '{order_number}', 产品成本: {product_cost:.2f} 元, IOSS成本: {ioss_cost:.2f} 元, 总费用: {invoice.total_charges:.2f} 元")

        return invoices