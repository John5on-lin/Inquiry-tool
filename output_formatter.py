from models import CalculationResult

class OutputFormatter:
    """输出格式化器"""
    @staticmethod
    def print_welcome_message(config) -> None:
        """打印欢迎信息"""
        print(f"===== {config.title} {config.app_version} =====")
        print(f"价格文件路径: {config.excel_path}")
    
    @staticmethod
    def print_results(result: CalculationResult) -> None:
        """打印计算结果"""
        print("\n\n==================== 查询结果 ====================")
        print(f"{'产品名称':<15} {'单价':<10} {'数量':<10} {'总价':<10}")
        print("-------------------------------------------------")
        
        for product in result.products:
            if product.price > 0:
                print(f"{product.name:<15} {product.price:<10.2f} {product.quantity:<10} {product.total:<10.2f}")
            else:
                print(f"{product.name:<15} {'-':<10} {product.quantity:<10} {'-':<10}  (产品未找到)")
        
        # 打印累计总价
        print("-------------------------------------------------")
        print(f"{'累计总价:':<35} {result.total_amount:.2f}")
        print("=================================================")
    
    @staticmethod
    def print_no_products_message() -> None:
        """打印无产品输入信息"""
        print("未输入任何产品信息，程序退出。")