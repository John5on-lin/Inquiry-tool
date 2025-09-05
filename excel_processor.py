import os
import pandas as pd
import logging
from order_fetcher import OrderFetcher, ShippingOrderFetcher
from calculator import Calculator
from output_formatter import OutputFormatter

logger = logging.getLogger(__name__)

def validate_excel_files(product_excel_file, shipping_excel_file):
    if not product_excel_file or not shipping_excel_file:
        error_msg = "产品Excel文件和物流Excel文件都必须提供"
        logger.warning(error_msg)
        return False, error_msg
    if not os.path.exists(product_excel_file):
        error_msg = f"产品Excel文件不存在: {product_excel_file}"
        logger.warning(error_msg)
        return False, error_msg
    if not os.path.exists(shipping_excel_file):
        error_msg = f"物流Excel文件不存在: {shipping_excel_file}"
        logger.warning(error_msg)
        return False, error_msg
    return True, ""

def load_excel_data(config, product_excel_file, shipping_excel_file):
    logger.info("开始加载订单数据...")
    order_fetcher = OrderFetcher(config)
    orders = order_fetcher.load_orders_from_excel(product_excel_file)
    logger.info(f"成功加载 {len(orders)} 条订单数据")

    logger.info("开始加载物流数据...")
    shipping_fetcher = ShippingOrderFetcher(config)
    shipping_orders = shipping_fetcher.load_shipping_orders_from_excel(shipping_excel_file)
    logger.info(f"成功加载 {len(shipping_orders)} 条物流数据")
    return orders, shipping_orders

def process_results(config, orders, shipping_orders, exchange_rate):
    shipping_cost_map = {order.order_number: order.actual_shipping_fee for order in shipping_orders}
    logger.info("开始生成发票...")
    calculator = Calculator(config)
    # 计算订单总计和IOSS税费
    order_totals, order_ioss_totals = calculator.calculate_order_totals(orders)
    invoices = calculator.create_invoices(orders, order_totals, order_ioss_totals, shipping_cost_map)
    logger.info(f"成功生成 {len(invoices)} 张发票")

    result_msg = f"处理完成。共生成 {len(invoices)} 张发票。"
    html_result = OutputFormatter.format_invoices_as_html(invoices, exchange_rate)
    return result_msg, html_result