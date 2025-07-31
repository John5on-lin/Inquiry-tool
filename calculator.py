from models import Product, CalculationResult

class Calculator:
    """价格计算器"""
    @staticmethod
    def calculate_totals(products: list[Product]) -> CalculationResult:
        """计算产品总价和累计总价"""
        total_amount = 0.0
        
        for product in products:
            if product.price > 0:
                product.total = product.price * product.quantity
                total_amount += product.total
        
        return CalculationResult(products=products, total_amount=total_amount)