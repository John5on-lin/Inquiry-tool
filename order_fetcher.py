import pandas as pd
import logging
from models import Order, ShippingOrder
from typing import List, Dict
from config import AppConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderFetcher:
    """订单数据获取器"""
    def __init__(self, config: AppConfig):
        self.config = config

    def load_orders_from_excel(self, file_path: str) -> List[Order]:
        """从Excel文件加载订单数据并转换为Order对象列表"""
        try:
            logger.info(f"开始从Excel文件加载订单数据: {file_path}")
            df = pd.read_excel(file_path)

            # 验证必要列是否存在
            required_columns = [
                self.config.order_excel_columns['order_number'],
                self.config.order_excel_columns['order_status'],
                self.config.order_excel_columns['sku'],
                self.config.order_excel_columns['quantity']
            ]
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                raise ValueError(f"Excel文件缺少必要列: {missing_cols}")

            # 转换为Order对象列表
            orders = []
            for _, row in df.iterrows():
                try:
                    order = Order(
                        order_number=str(row[self.config.order_excel_columns['order_number']]),
                        order_status=str(row[self.config.order_excel_columns['order_status']]),
                        order_note=str(row.get(self.config.order_excel_columns['order_note'], '')),
                        payment_time=str(row.get(self.config.order_excel_columns['payment_time'], '')),
                        country_code=str(row.get(self.config.order_excel_columns['country_code'], '')),
                        country=str(row.get(self.config.order_excel_columns['country'], '')),
                        product_name=str(row.get(self.config.order_excel_columns['product_name'], '')),
                        shop_name=str(row.get(self.config.order_excel_columns['shop_name'], '')),
                        sku=str(row[self.config.order_excel_columns['sku']]),
                        combination_sku=str(row.get(self.config.order_excel_columns['combination_sku'], '')),
                        quantity=int(row[self.config.order_excel_columns['quantity']]),
                        total_weight=float(row.get(self.config.order_excel_columns['total_weight'], 0.0)),
                        uniform_cost_price=float(row.get(self.config.order_excel_columns['uniform_cost_price'], 0.0))
                    )
                    orders.append(order)
                except (ValueError, TypeError) as e:
                    logger.warning(f"行数据无效，已跳过: {row}. 错误: {str(e)}")

            logger.info(f"成功加载{len(orders)}条订单数据")
            return orders
        except FileNotFoundError:
            logger.error(f"Excel文件未找到: {file_path}")
            raise
        except Exception as e:
            logger.error(f"加载Excel订单数据失败: {str(e)}", exc_info=True)
            raise

class ShippingOrderFetcher:
    def __init__(self, config: AppConfig):
        self.config = config

    def load_shipping_orders_from_excel(self, file_path: str) -> List[ShippingOrder]:
        """从Excel文件加载运费订单数据并进行验证

        Args:
            file_path: Excel文件路径

        Returns:
            验证后的ShippingOrder对象列表

        Raises:
            ValueError: 当Excel文件缺少必要列或数据格式错误时
        """
        logger.info(f"开始从Excel文件加载运费数据: {file_path}")
        shipping_orders = []
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            logger.debug(f"成功读取Excel文件，共{len(df)}行数据")
        
            # 验证必要列是否存在
            required_columns = [
                self.config.shipping_excel_columns['order_number'],
                self.config.shipping_excel_columns['actual_shipping_fee']
            ]
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"运费Excel文件缺少必要列: {missing_cols}")
        
            # 处理每一行数据
            for idx, row in df.iterrows():
                row_num = idx + 2  # Excel行号从2开始(标题行+数据行索引)
                try:
                    # 基本验证
                    order_number = row.get(self.config.shipping_excel_columns['order_number'])
                    if pd.isna(order_number) or str(order_number).strip() == '':
                        logger.warning(f"行{row_num}: 订单编号为空，跳过该行数据")
                        continue
        
                    # 转换并验证运费金额
                    actual_shipping_fee = row.get(self.config.shipping_excel_columns['actual_shipping_fee'])
                    if pd.isna(actual_shipping_fee):
                        logger.warning(f"行{row_num}: 订单编号{order_number}的运费金额为空，跳过该行数据")
                        continue
        
                    try:
                        actual_shipping_fee = float(actual_shipping_fee)
                        if actual_shipping_fee < 0:
                            raise ValueError("运费金额不能为负数")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"行{row_num}: 订单编号{order_number}的运费金额无效({actual_shipping_fee})，错误: {str(e)}")
                        continue
        
                    # 创建ShippingOrder对象
                    shipping_order = ShippingOrder(
                        order_number=str(order_number).strip(),
                        shipping_channel=str(row.get(self.config.shipping_excel_columns['shipping_channel'], '')).strip(),
                        tracking_number=str(row.get(self.config.shipping_excel_columns['tracking_number'], '')).strip(),
                        country=str(row.get(self.config.shipping_excel_columns['country'], '')).strip(),
                        total_weight=float(row.get(self.config.shipping_excel_columns['total_weight'], 0.0)),
                        actual_shipping_fee=actual_shipping_fee
                    )
                    shipping_orders.append(shipping_order)
        
                except Exception as e:
                    logger.error(f"行{row_num}: 处理订单数据时发生错误，跳过该行: {str(e)}")
                    continue
        
            logger.info(f"成功加载并验证{len(shipping_orders)}条运费数据，共跳过{len(df)-len(shipping_orders)}行无效数据")
            return shipping_orders
        
        except FileNotFoundError:
            logger.error(f"运费Excel文件未找到: {file_path}")
            raise
        except Exception as e:
            logger.error(f"加载运费Excel文件失败: {str(e)}", exc_info=True)
            raise