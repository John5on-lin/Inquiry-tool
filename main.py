# 说明文字
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

# 加载.env文件
load_dotenv()
from price_fetcher import PriceFetcher
from calculator import Calculator

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

def load_shipping_rules(destination, volume_weight_ratio):
    try:
        global products_with_data
        if not products_with_data:
            logger.info("没有产品数据，返回空的运费规则")
            return [], {}

        if not destination:
            logger.info("没有指定目的地，返回空的运费规则")
            return [], {}

        config = load_config()
        calculator_instance = Calculator(config)
        
        # 调用方法获得匹配的运费规则
        data = calculator_instance.find_applicable_shipping_rules(products_with_data, destination, volume_weight_ratio)
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

def check_pricing(destination, exchange_rate, selected_shipping_rules):
    try:
        global products_with_data
        if not products_with_data:
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
            products_with_data, 
            destination, 
            selected_shipping_rules
        )

        # 使用OutputFormatter生成HTML格式的结果
        html_result = OutputFormatter.format_results_as_html(result, destination, [rule_info], [ioss_info], exchange_rate)

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
        
        # 第二步：输入目的地、汇率和体积重量转换比
        with gr.Row():
            with gr.Column():
                destination = gr.Textbox(
                    label="目的地国家", 
                    placeholder="例如：美国"
                )
            with gr.Column():
                exchange_rate = gr.Number(
                    label="美元换算汇率", 
                    value=6.9, 
                    precision=2
                )
            with gr.Column():
                volume_weight_ratio = gr.Number(
                    label="体积重量转换比", 
                    value=6000, 
                    precision=0
                )
        
        shipping_rules_btn = gr.Button("查询运费表")
        
        # 第三步：选择确认货代公司
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 选择货代公司")
                checkbox = gr.CheckboxGroup(
                    choices=[],
                    label="可选公司",
                    info="勾选需要的货代公司"
                )
                selection_output = gr.Textbox(label="选择结果", lines=5)
        
        # 在 Blocks 内创建 State
        id_map_state = gr.State({})     # 存 ID -> 数据映射
        selection_text_state = gr.State(None)  # 存选择的规则对象

        # 点击按钮时更新 checkbox 的 choices，并把 id_map 存入 state
        shipping_rules_btn.click(fn=load_shipping_rules, inputs=[destination, volume_weight_ratio], outputs=[checkbox, id_map_state])

        # 当 checkbox 改变时，把 checkbox 的值和 id_map_state 传给回调以显示/用于计算
        checkbox.change(
            fn=show_selection,
            inputs=[checkbox, id_map_state],
            outputs=[selection_output, selection_text_state]
        )
        logger.info("已更新checkbox.change事件处理")
        
        # 第三步：选择确认货代公司
        submit_btn = gr.Button("报价查询")
        
        # 结果展示部分
        result_output = gr.HTML(label="报价查询结果")

        # 设置按钮事件
        load_btn.click(
            fn=load_products,
            inputs=[input_text],
            outputs=[product_images]
        )

        submit_btn.click(
            fn=check_pricing,
            inputs=[destination, exchange_rate, selection_text_state],
            outputs=[result_output]
        )

    return demo

if __name__ == "__main__":
    demo = create_interface()
    # 从环境变量获取服务器配置，默认值用于本地开发
    server_name = os.getenv('SERVER_NAME', '127.0.0.1')
    server_port = int(os.getenv('SERVER_PORT', '7860'))
    demo.launch(server_name=server_name, server_port=server_port)