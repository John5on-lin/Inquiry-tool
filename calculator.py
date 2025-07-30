import logging
from typing import List
from models import Product, CalculationResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Calculator:
    @staticmethod
    def calculate_totals(products: List[Product]) -> CalculationResult:
        """计算产品列表的总价"
        result = CalculationResult()
        result.products = products

        for product in products:
            if product.price is not None:
                product.total = product.price * product.quantity
                result.total_amount += product.total
                logger.info(f"产品'{product.name}'的总价计算完成: {product.total}")
            else:
                logger.warning(f"无法计算产品'{product.name}'的总价，缺少价格信息")

        logger.info(f"所有产品总价计算完成，累计总价: {result.total_amount}")
        return result