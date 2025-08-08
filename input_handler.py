from models import Product
from typing import List

class InputHandler:
    """用户输入处理器"""
    @staticmethod
    def get_products_from_user() -> tuple[list[Product], str]:
        """从用户获取产品信息列表和目的地国家（命令行方式）"""
        products = []
        print("\n请输入产品信息（输入空产品名称结束）")
        
        while True:
            product_name = input("请输入产品名称: ").strip()
            
            # 检查是否结束输入
            if not product_name:
                print("产品输入已结束")
                break
            
            # 获取并验证数量
            quantity = InputHandler._get_valid_quantity()
            
            print(f"已添加产品: {product_name}, 数量: {quantity}")
            products.append(Product(
                name=product_name, 
                quantity=quantity, 
                weight=0.0,  # 重量将从Sheet1获取
                attribute="",  # 属性将从Sheet1获取
            ))
        
        # 获取目的地国家
        if products:
            destination = input("请输入所有产品的目的地国家: ").strip()
            while not destination:
                print("错误: 目的地国家不能为空")
                destination = input("请输入所有产品的目的地国家: ").strip()
        else:
            destination = ""
        
        return products, destination
    
    @staticmethod
    def parse_products_from_text(input_text: str) -> List[Product]:
        """从文本输入解析产品信息列表"""
        products = []
        lines = input_text.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) != 2:
                raise ValueError(f"格式错误：{line}。请使用'产品名称,数量'的格式。例如：苹果,2")
            name = parts[0].strip()
            try:
                quantity = float(parts[1].strip())
                products.append(Product(
                    name=name, 
                    quantity=quantity, 
                    weight=0.0,  # 重量将从Sheet1获取
                    attribute="",  # 属性将从Sheet1获取
                ))
            except ValueError as e:
                raise ValueError(f"数据错误：{str(e)}。数量必须是数字。")
        
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