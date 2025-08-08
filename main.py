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

from input_handler import InputHandler

# 全局变量存储产品数据
products_with_data = []

def load_products(input_text):
    try:
        # 使用InputHandler解析产品信息
        products = InputHandler.parse_products_from_text(input_text)

        if not products:
            return "未输入任何产品信息"

        config = load_config()
        
        # 获取产品完整数据（价格、重量、尺寸等）
        price_fetcher = PriceFetcher(config)
        global products_with_data
        products_with_data = price_fetcher.fetch_product_data(products)
        
        # 使用OutputFormatter生成产品图片HTML
        html_images = OutputFormatter.format_product_images(products_with_data)

        return html_images
    except Exception as e:
        return f"处理错误: {str(e)}"

def process_products(destination, exchange_rate):
    try:
        global products_with_data
        if not products_with_data:
            return "请先加载产品信息"

        if not destination:
            return "请输入目的地国家"

        if not exchange_rate or exchange_rate <= 0:
            return "请输入有效的美元换算汇率"

        config = load_config()
        
        # 计算运费和总价
        calculator = Calculator(config)
        product_rule_infos = []  # 存储每个产品的运费规则信息
        product_ioss_infos = []  # 存储每个产品的IOSS税金信息
        for product in products_with_data:
            # 设置产品的目的地国家
            product.destination = destination
            total_price, rule_info, ioss_info = calculator.calculate_product_total(product)
            product_rule_infos.append(rule_info)
            product_ioss_infos.append(ioss_info)
        
        # 计算总价
        result = Calculator.calculate_totals(products_with_data)

        # 使用OutputFormatter生成HTML格式的结果
        html_result = OutputFormatter.format_results_as_html(result, product_rule_infos, product_ioss_infos, exchange_rate)

        return html_result
    except Exception as e:
        return f"处理错误: {str(e)}"

def create_interface():
    with gr.Blocks(title="产品价格查询与运费计算工具", analytics_enabled=False) as demo:
        gr.Markdown("# 产品价格查询与运费计算工具")
        
        # 第一步：输入产品信息
        with gr.Row():
            input_text = gr.Textbox(
                lines=5, 
                label="输入产品信息（每行一个产品，格式：产品名称,数量）", 
                placeholder="例如：\n苹果, 2\n香蕉, 3"
            )
        
        load_btn = gr.Button("加载产品")
        
        # 产品图片展示区域
        product_images = gr.HTML(label="产品图片")
        
        # 第二步：输入目的地和汇率
        with gr.Row():
            destination = gr.Textbox(
                label="目的地国家", 
                placeholder="例如：美国"
            )
        
        with gr.Row():
            exchange_rate = gr.Number(
                label="美元换算汇率", 
                value=6.9, 
                precision=2
            )
        
        submit_btn = gr.Button("查询")
        
        # 结果展示部分
        result_output = gr.HTML(label="查询结果")

        # 设置按钮事件
        load_btn.click(
            fn=load_products,
            inputs=[input_text],
            outputs=[product_images]
        )

        submit_btn.click(
            fn=process_products,
            inputs=[destination, exchange_rate],
            outputs=[result_output]
        )

    return demo

if __name__ == "__main__":
    demo = create_interface()
    # 从环境变量获取服务器配置，默认值用于本地开发
    server_name = os.getenv('SERVER_NAME', '127.0.0.1')
    server_port = int(os.getenv('SERVER_PORT', '7860'))
    demo.launch(server_name=server_name, server_port=server_port)