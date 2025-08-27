import pandas as pd
import logging
from models import Order
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
            required_columns = ['交易编号', '订单状态', 'SKU', '商品数量']
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                raise ValueError(f"Excel文件缺少必要列: {missing_cols}")

            # 转换为Order对象列表
            orders = []
            for _, row in df.iterrows():
                try:
                    order = Order(
                        order_number=str(row['交易编号']),
                        order_status=str(row['订单状态']),
                        order_note=str(row.get('订单备注', '')),
                        payment_time=str(row.get('支付时间', '')),
                        country_code=str(row.get('国家代码', '')),
                        country=str(row.get('国家', '')),
                        product_name=str(row.get('产品名称', '')),
                        shop_name=str(row.get('店铺名称', '')),
                        sku=str(row['SKU']),
                        combination_sku=str(row.get('组合SKU', '')),
                        quantity=int(row['商品数量']),
                        total_weight=float(row.get('总重量', 0.0))
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