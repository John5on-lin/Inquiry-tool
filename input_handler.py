import logging
from typing import List
from models import Product

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputHandler:
    @staticmethod
    def parse_input(input_text: str) -> List[Product]:
        """解析用户输入的产品和数量文本，返回产品列表"
        products = []
        lines = input_text.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                # 分割产品名称和数量（支持逗号或空格分隔）
                if ',' in line:
                    name, quantity_str = line.split(',', 1)
                else:
                    parts = line.split(maxsplit=1)
                    if len(parts) < 2:
                        raise ValueError("格式错误，缺少数量")
                    name, quantity_str = parts
                
                name = name.strip()
                quantity = float(quantity_str.strip())
                
                if quantity <= 0:
                    raise ValueError("数量必须大于零")
                
                products.append(Product(name=name, quantity=quantity))
                logger.info(f"已解析产品: {name}, 数量: {quantity}")
            except ValueError as e:
                logger.error(f"第{line_num}行解析失败: {str(e)}")
                raise ValueError(f"第{line_num}行格式错误: {str(e)}. 请使用'产品名称,数量'或'产品名称 数量'的格式。")
        
        if not products:
            raise ValueError("未解析到任何产品，请检查输入")
        
        return products