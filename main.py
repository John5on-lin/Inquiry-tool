import sys
import os
import gradio as gr
from config import load_config
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()
from price_fetcher import PriceFetcher
from calculator import Calculator
from models import Product
from output_formatter import OutputFormatter

def process_products(input_text):
    try:
        products = []
        lines = input_text.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) != 2:
                return [[], f"格式错误：{line}。请使用'产品名称,数量'的格式。"]
            name = parts[0].strip()
            try:
                quantity = float(parts[1].strip())
                products.append(Product(name=name, quantity=quantity))
            except ValueError:
                return [[], f"数量错误：{parts[1]}不是有效的数字。"]

        config = load_config()
        price_fetcher = PriceFetcher(config)
        products_with_prices = price_fetcher.fetch_prices(products)
        result = Calculator.calculate_totals(products_with_prices)

        # 修改数据格式，仅返回基本类型的列表
        output_table = []
        # 直接使用CalculationResult对象的属性
        for p in result.products:
            # 确保所有值都是基本类型（字符串和数字）
            price = p.price if p.price else 0
            total = p.total if p.total else 0
            output_table.append([str(p.name), float(price), float(p.quantity), float(total)])
        
        # 使用对象的total_amount属性
        total_amount = result.total_amount

        # 返回纯列表和字符串，避免复杂类型
        return output_table, f"累计总价: {total_amount:.2f}"
    except Exception as e:
        return [[], f"处理错误: {str(e)}"]

def create_interface():
    with gr.Blocks(title="产品价格查询工具", analytics_enabled=False) as demo:
        gr.Markdown("# 产品价格查询工具")
        input_text = gr.Textbox(lines=5, label="输入产品和数量（每行一个产品，格式：产品名称,数量）", placeholder="例如：\n苹果, 2\n香蕉, 3")
        submit_btn = gr.Button("查询")
        output_table = gr.Dataframe(headers=["产品名称", "单价", "数量", "总价"], type="array")
        total_text = gr.Textbox(label="累计总价")

        submit_btn.click(
            fn=process_products,
            inputs=[input_text],
            outputs=[output_table, total_text]
        )

    return demo

if __name__ == "__main__":
    demo = create_interface()
    # 从环境变量获取服务器配置，默认值用于本地开发
    server_name = os.getenv('SERVER_NAME', '127.0.0.1')
    server_port = int(os.getenv('SERVER_PORT', '7860'))
    demo.launch(server_name=server_name, server_port=server_port)