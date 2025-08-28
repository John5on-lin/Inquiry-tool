# 说明文字
# 诊断Render部署脚本
from diagnostics import print_env_info

print_env_info() 

import logging
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from config import load_config
from dotenv import load_dotenv
import os
import gradio as gr
from typing import List

# 加载.env文件
load_dotenv()
from price_fetcher import PriceFetcher
from calculator import Calculator
from order_fetcher import OrderFetcher

from output_formatter import OutputFormatter
from input_handler import InputHandler
from models import Order, Invoice

# 使用Gradio State管理产品数据，替代全局变量

def load_products(input_text, products_state):
    try:
        # 使用InputHandler解析产品信息
        products = InputHandler.parse_products_from_text(input_text)

        if not products:
            return "未输入任何产品信息", products_state

        config = load_config()
        
        # 获取产品完整数据（价格、重量、尺寸等）
        price_fetcher = PriceFetcher(config)
        updated_products = price_fetcher.fetch_product_data(products)
        
        # 使用OutputFormatter生成产品图片HTML
        html_images = OutputFormatter.format_product_images(updated_products)

        return html_images, updated_products
    except Exception as e:
        return f"处理错误: {str(e)}"

def load_shipping_rules(destination, volume_weight_ratio, products_state):
    try:
        if not products_state:
            logger.info("没有产品数据，返回空的运费规则")
            return [], {}

        if not destination:
            logger.info("没有指定目的地，返回空的运费规则")
            return [], {}

        config = load_config()
        calculator_instance = Calculator(config)
        
        # 调用方法获得匹配的运费规则
        data = calculator_instance.find_applicable_shipping_rules(products_state, destination, volume_weight_ratio)
        logger.info(f"find_applicable_shipping_rules返回数据类型: {type(data)}, 数据长度: {len(data)}")
        if data:
            logger.info(f"返回数据第一项: {data[0]}")
        
        # 初始化变量
        choices = []
        id_map = {}  # 用来把唯一值映射回原数据
        
        for item in data:
            display_text = f"{item['shipping_company']} | 目的地: {item['country']} | 区域: {item['region']} | 货物属性: {item['attribute']} | 首重: {item['first_weight']}g/{item['first_weight_fee']}元 | 续重: {item['additional_weight']}g/{item['additional_weight_price']}元 | 时效: {item['min_delivery_days']}-{item['max_delivery_days']}天 | 挂号费: {item['registration_fee']}元/票"
            value_id = f"{item['shipping_company']}_{item['id']}"  # 唯一 ID
            choices.append((display_text, value_id))
            id_map[value_id] = item
            logger.debug(f"添加到id_map的键: {value_id}, 类型: {type(value_id)}")
        logger.info(f"生成的choices数量: {len(choices)}, id_map键数量: {len(id_map.keys())}")
        return gr.update(choices=choices, value=[]), id_map
    except Exception as e:
        logger.error(f"运输规则处理错误: {str(e)}")
        return [], {}

def show_selection(selected_ids, id_map):
    logger.info(f"show_selection被调用，selected_ids类型: {type(selected_ids)}, 值: {selected_ids}")
    if not selected_ids:
        return "你没有选择任何公司", None
    results = []
    selected_rule = None
    # 确保selected_ids是列表
    if not isinstance(selected_ids, list):
        logger.info(f"将selected_ids从{type(selected_ids)}转换为列表")
        selected_ids = [selected_ids]
    # 使用ID列表
    for sid in selected_ids:
        logger.info(f"遍历ID列表，当前sid类型: {type(sid)}, 值: {sid}")
        if sid in id_map:
            item = id_map[sid]
            results.append(f"{item['shipping_company']}, {item['country']}, {item['region']}, {item['attribute']} - 首重: {item['first_weight']}g/{item['first_weight_fee']}元, 续重: {item['additional_weight']}g/{item['additional_weight_price']}元, 挂号费: {item['registration_fee']}元/票, 时效: {item['min_delivery_days']}-{item['max_delivery_days']}天")
            # 只选择第一个规则
            if selected_rule is None:
                selected_rule = item
        else:
            results.append(f"无效的选择: {sid}")
    return "\n".join(results), selected_rule

def process_excel(file, rate):
    if file is None:
        return None, "请上传Excel文件", ""
    
    try:
        # 加载配置
        config = load_config()

        # 使用OrderFetcher处理订单数据
        order_fetcher = OrderFetcher(config)
        orders = order_fetcher.load_orders_from_excel(file.name)
        
        # 初始化计算器
        calculator = Calculator(config)

        # 计算每个订单的产品价格总和
        order_totals = calculator.calculate_order_total(orders)

        # 创建发票
        invoices = calculator.create_invoices(orders, order_totals)
        
        # 格式化发票信息为HTML
        html_result = OutputFormatter.format_invoices_as_html(invoices, rate)
        
        # 返回数据表格、成功消息和发票HTML
        return f"成功处理{len(orders)}个订单，生成{len(invoices)}张发票", html_result
    except Exception as e:
        logger.error(f"处理Excel文件出错: {str(e)}")
        return None, f"处理Excel文件出错: {str(e)}", ""

def check_pricing(destination, exchange_rate, selected_shipping_rules, products_state):
    try:
        if not products_state:
            return "请先加载产品信息"

        if not destination:
            return "请输入目的地国家"

        if not exchange_rate or exchange_rate <= 0:
            return "请输入有效的美元换算汇率"

        if not selected_shipping_rules:
            return "请选择至少一家货代公司"

        # 确保selected_shipping_rules是字典类型
        if not isinstance(selected_shipping_rules, dict):
            logger.error(f"selected_shipping_rules类型错误: 期望dict, 实际为{type(selected_shipping_rules)}")
            return f"内部错误: 运费规则格式不正确"

        config = load_config()
        
        # 计算总价（包含总运费和IOSS税金）
        calculator = Calculator(config)
        # 传递用户选择的运费规则到计算函数
        result, rule_info, ioss_info = calculator.calculate_totals(
            products_state, 
            destination, 
            selected_shipping_rules
        )

        # 使用OutputFormatter生成HTML格式的结果
        html_result = OutputFormatter.format_results_as_html(result, destination, [rule_info], [ioss_info], exchange_rate)

        return html_result
    except Exception as e:
        return f"处理错误: {str(e)}"

def create_interface():
    with gr.Blocks(title="多功能工具", analytics_enabled=False) as demo:
        gr.Markdown("# 工具集合")

        with gr.Tabs():
            # # Tab 1: 价格查询与运费计算
            # with gr.Tab("产品价格与运费"):
            #     gr.Markdown("## 产品价格查询与运费计算工具")

            #     # 第一步：输入产品信息
            #     with gr.Row():
            #         with gr.Column(scale=4):
            #             input_text = gr.Textbox(
            #                 lines=5,
            #                 label="输入产品信息（每行一个产品，格式：产品名称,数量）",
            #                 placeholder="例如：\n苹果, 2\n香蕉, 3"
            #             )
            #         with gr.Column(scale=1, min_width=100):
            #             load_btn = gr.Button("加载产品")

            #     # 产品图片展示区域
            #     product_images = gr.HTML(label="产品图片")

            #     # 第二步：输入目的地、汇率和体积重量转换比
            #     with gr.Row():
            #         with gr.Column():
            #             destination = gr.Textbox(label="目的地国家", placeholder="例如：美国")
            #         with gr.Column():
            #             exchange_rate = gr.Number(label="美元换算汇率", value=6.9, precision=2)
            #         with gr.Column():
            #             volume_weight_ratio = gr.Number(label="体积重量转换比", value=6000)
            #     shipping_rules_btn = gr.Button("查询运费表")

            #     # 第三步：选择确认货代公司
            #     with gr.Row():
            #         with gr.Column():
            #             gr.Markdown("### 选择货代公司")
            #             checkbox = gr.CheckboxGroup(choices=[], label="可选公司", info="勾选需要的货代公司")
            #             selection_output = gr.Textbox(label="选择结果", lines=5)

            #     # State
            #     id_map_state = gr.State({}) 
            #     selection_text_state = gr.State(None)
            #     products_state = gr.State([]) 

            #     # 交互逻辑
            #     shipping_rules_btn.click(
            #         fn=load_shipping_rules,
            #         inputs=[destination, volume_weight_ratio, products_state],
            #         outputs=[checkbox, id_map_state]
            #     )
            #     checkbox.change(
            #         fn=show_selection,
            #         inputs=[checkbox, id_map_state],
            #         outputs=[selection_output, selection_text_state]
            #     )
            #     logger.info("已更新checkbox.change事件处理")

            #     # 提交按钮
            #     submit_btn = gr.Button("报价查询")
            #     result_output = gr.HTML(label="报价查询结果")

            #     # 按钮事件
            #     load_btn.click(fn=load_products, inputs=[input_text, products_state], outputs=[product_images, products_state])
            #     submit_btn.click(
            #         fn=check_pricing,
            #         inputs=[destination, exchange_rate, selection_text_state, products_state],
            #         outputs=[result_output]
            #     )

            # Tab 2: Invoice 助理
            with gr.Tab("Invoice 助理"):
                gr.Markdown("## 订单详情Excel上传与处理")
                
                # 文件上传组件
                # excel_file = gr.File(label="上传订单详情Excel", file_count="single", file_types=[".xlsx", ".xls"])
                excel_file = gr.File(label="上传订单详情Excel")
                
                # 汇率输入
                exchange_rate = gr.Number(label="美元换算汇率", value=6.9, precision=2)
                
                # 上传按钮
                upload_btn = gr.Button("上传并处理")
                                
                # 状态消息组件
                status_message = gr.Textbox(label="处理状态", lines=1)
                
                # 发票信息展示组件
                invoice_output = gr.HTML(label="发票信息")

                upload_btn.click(fn=process_excel, inputs=[excel_file, exchange_rate], outputs=[status_message, invoice_output])

    return demo

if __name__ == "__main__":
    demo = create_interface()
    
    # Debug API Info
    print("=== DEBUG: API Info ===")
    print(demo.get_api_info())
    print("=== END DEBUG ===")
    
    # 从环境变量获取服务器配置，默认值用于本地开发
    server_name = os.getenv('SERVER_NAME', '0.0.0.0')
    server_port = int(os.getenv('SERVER_PORT', '7860'))
    demo.launch(server_name=server_name, server_port=server_port,show_api=False)