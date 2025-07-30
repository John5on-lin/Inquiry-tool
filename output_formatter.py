import logging
from typing import List
from models import Product, CalculationResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OutputFormatter:
    @staticmethod
    def format_table(result: CalculationResult) -> List[List[str]]:
        """将计算结果格式化为表格数据"
        table_data = []
        # 添加表头
        table_data.append(["产品名称", "单价", "数量", "总价"])
        
        # 添加产品数据
        for product in result.products:
            price = f"{product.price:.2f}" if product.price else "N/A"
            total = f"{product.total:.2f}" if product.total else "N/A"
            table_data.append([
                product.name,
                price,
                f"{product.quantity:.2f}",
                total
            ])
        
        # 添加总计
        table_data.append(["", "", "累计总价:", f"{result.total_amount:.2f}"])
        
        return table_data
    
    @staticmethod
    def format_text(result: CalculationResult) -> str:
        """将计算结果格式化为文本"
        if result.error_message:
            return f"错误: {result.error_message}"
        
        text = "产品价格计算结果\n"
        text += "====================\n"
        
        for product in result.products:
            price = f"{product.price:.2f}" if product.price else "N/A"
            total = f"{product.total:.2f}" if product.total else "N/A"
            text += f"{product.name}:\n"
            text += f"  单价: {price}\n"
            text += f"  数量: {product.quantity:.2f}\n"
            text += f"  总价: {total}\n\n"
        
        text += f"====================\n"
        text += f"累计总价: {result.total_amount:.2f}"
        
        return text
    
    @staticmethod
    def format_html(result: CalculationResult) -> str:
        """将计算结果格式化为HTML"
        if result.error_message:
            return f"<div class='error'>错误: {result.error_message}</div>"
        
        html = "<div class='result-container'>"
        html += "<h2>产品价格计算结果</h2>"
        
        html += "<table class='result-table'>"
        html += "<tr><th>产品名称</th><th>单价</th><th>数量</th><th>总价</th></tr>"
        
        for product in result.products:
            price = f"{product.price:.2f}" if product.price else "N/A"
            total = f"{product.total:.2f}" if product.total else "N/A"
            html += f"<tr>"
            html += f"<td>{product.name}</td>"
            html += f"<td>{price}</td>"
            html += f"<td>{product.quantity:.2f}</td>"
            html += f"<td>{total}</td>"
            html += "</tr>"
        
        html += "<tr class='total-row'>"
        html += "<td colspan='2'></td>"
        html += f"<td><strong>累计总价:</strong></td>"
        html += f"<td><strong>{result.total_amount:.2f}</strong></td>"
        html += "</tr>"
        html += "</table>"
        
        html += "</div>"
        
        # 添加CSS样式
        html += "<style>"
        html += ".result-container { max-width: 800px; margin: 0 auto; padding: 20px; }"
        html += ".result-table { width: 100%; border-collapse: collapse; margin-top: 15px; }"
        html += ".result-table th, .result-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }"
        html += ".result-table th { background-color: #f2f2f2; }"
        html += ".total-row { background-color: #f9f9f9; }"
        html += ".error { color: #dc3545; font-weight: bold; padding: 10px; border: 1px solid #f5c6cb; background-color: #f8d7da; }"
        html += "</style>"
        
        return html