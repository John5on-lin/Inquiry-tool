# 说明文字
import logging
import gradio as gr
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from config import load_config
from dotenv import load_dotenv
import os
from ui import create_interface
from typing import List

# 加载.env文件
load_dotenv()
from price_fetcher import PriceFetcher
from calculator import Calculator
from excel_processor import validate_excel_files, load_excel_data, process_results

from output_formatter import OutputFormatter
from input_handler import InputHandler

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

def process_excel(product_excel_file, shipping_excel_file, exchange_rate):
    try:
        # 验证文件
        valid, message = validate_excel_files(product_excel_file.name, shipping_excel_file.name)
        if not valid:
            return message, ""

        # 加载配置
        config = load_config()

        # 加载数据
        orders, shipping_orders = load_excel_data(config, product_excel_file.name, shipping_excel_file.name)

        # 处理结果
        result_msg, html_result = process_results(config, orders, shipping_orders, exchange_rate)

        return result_msg, html_result
    except Exception as e:
        logger.error(f"处理Excel文件出错: {str(e)}")
        return f"处理Excel文件出错: {str(e)}", ""

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

if __name__ == "__main__":
    # 诊断Render部署脚本
    from diagnostics import print_env_info
    print_env_info()
    logging.basicConfig(level=logging.INFO)
    interface = create_interface()
    server_name = os.getenv('SERVER_NAME', '0.0.0.0')
    server_port = int(os.getenv('SERVER_PORT', '7860'))
    interface.launch(server_name=server_name, server_port=server_port)