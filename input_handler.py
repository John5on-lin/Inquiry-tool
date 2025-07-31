from models import Product

class InputHandler:
    """用户输入处理器"""
    @staticmethod
    def get_products_from_user() -> list[Product]:
        """从用户获取产品信息列表"""
        products = []
        print("\n请输入产品信息（输入空产品名称结束）")
        
        while True:
            product_name = input("请输入产品名称: ").strip()
            
            # 检查是否结束输入
            if not product_name:
                print("产品输入已结束，开始处理查询...")
                break
            
            # 获取并验证数量
            quantity = InputHandler._get_valid_quantity()
            print(f"已添加产品: {product_name}, 数量: {quantity}")
            products.append(Product(name=product_name, quantity=quantity))
        
        return products
    
    @staticmethod
    def _get_valid_quantity() -> float:
        """获取并验证数量输入"""
        while True:
            try:
                quantity_input = input("请输入购买数量: ").strip()
                quantity = float(quantity_input)
                if quantity <= 0:
                    print("错误: 数量必须大于0，请重新输入。")
                    continue
                return quantity
            except ValueError:
                print(f"错误: '{quantity_input}' 不是有效的数字，请重新输入。")