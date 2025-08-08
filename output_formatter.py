from typing import List
from models import Product, CalculationResult

class OutputFormatter:
    """输出格式化器"""
    @staticmethod
    def print_welcome_message(config) -> None:
        """打印欢迎信息"""
        print(f"===== {config.title} {config.app_version} =====")
        print(f"价格文件路径: {config.excel_path}")
    
    @staticmethod
    def print_results(result: CalculationResult, product_rule_infos: list = None, product_ioss_infos: list = None, exchange_rate: float = 6.9) -> None:
        """打印计算结果(命令行)"""
        print("\n\n==================== 查询结果 ====================")
        
        total_product_price = 0.0
        total_shipping_fee = 0.0
        
        # 打印所有产品价格信息
        print("\n------------- 产品价格信息 -------------")
        print(f"{'产品名称':<15} {'单价':<10} {'数量':<10} {'产品价格':<10}")
        print("-----------------------------------------")
        for i, product in enumerate(result.products):
            if product.price > 0:
                product_total = product.price * product.quantity
                total_product_price += product_total
                print(f"{product.name:<15} {product.price:<10.2f} {product.quantity:<10} {product_total:<10.2f}")
            else:
                print(f"{product.name:<15} {'-':<10} {'-':<10} {'-':<10}")
                print(f"产品 '{product.name}' 未找到价格信息")
        
        # 打印所有运费价格信息
        print("\n\n------------- 运费价格信息 -------------")
        print(f"{'产品名称':<15} {'货代公司':<15} {'目的地':<10} {'参考时效':<10} {'重量(KG)':<10} {'运费率':<10} {'手续费':<10} {'运费':<10}")
        print("-----------------------------------------------------------------------------------------------------------")
        for i, product in enumerate(result.products):
            if product.price > 0:
                rule_info = product_rule_infos[i] if (product_rule_infos and i < len(product_rule_infos)) else {}
                shipping_company = rule_info.get('shipping_company', '')
                estimated_delivery_time = rule_info.get('estimated_delivery_time', '')
                actual_weight = rule_info.get('actual_weight', 0)
                shipping_rate = rule_info.get('shipping_rate', 0)
                registration_fee = rule_info.get('registration_fee', 0)
                
                total_shipping_fee += product.shipping_fee
                print(f"{product.name:<15} {shipping_company:<15} {product.destination:<10} {estimated_delivery_time:<10} {actual_weight:<10.2f} {shipping_rate:<10.2f} {registration_fee:<10.2f} {product.shipping_fee:<10.2f}")
            else:
                print(f"{product.name:<15} {'-':<15} {'-':<10} {'-':<10} {'-':<10} {'-':<10} {'-':<10} {'-':<10}")
        
        # 打印IOSS税金信息
        print("\n\n------------- IOSS税金信息 -------------")
        total_ioss_tax = result.ioss_taxes
        ioss_tax_usd = total_ioss_tax / exchange_rate
        print(f"{'总IOSS税金:':<35} {total_ioss_tax:.2f} RMB ({ioss_tax_usd:.2f} USD)")
        
        if total_ioss_tax > 0 and product_ioss_infos:
            print(f"{'产品名称':<15} {'目的地':<10} {'VAT税率':<10} {'服务费率':<10} {'VAT税费':<10} {'服务费':<10} {'IOSS税金':<10}")
            print("-----------------------------------------------------------------------------------------------------------")
            for i, product in enumerate(result.products):
                if product.price > 0 and i < len(product_ioss_infos):
                    ioss_info = product_ioss_infos[i]
                    if ioss_info:
                        vat_rate = ioss_info.get('vat_rate', 0) * 100
                        service_rate = ioss_info.get('service_rate', 0) * 100
                        vat_tax = ioss_info.get('vat_tax', 0)
                        service_fee = ioss_info.get('service_fee', 0)
                        ioss_tax = ioss_info.get('ioss_tax', 0)
                        print(f"{product.name:<15} {product.destination:<10} {vat_rate:<10.1f}% {service_rate:<10.1f}% {vat_tax:<10.2f} {service_fee:<10.2f} {ioss_tax:<10.2f}")
        
        # 打印总价格部分 #
        print("\n\n------------- 总价格 -------------")
        product_total_usd = total_product_price / exchange_rate
        shipping_total_usd = total_shipping_fee / exchange_rate
        ioss_tax_usd = total_ioss_tax / exchange_rate
        total_amount_usd = result.total_amount / exchange_rate
        print(f"{'产品总价格:':<35} {total_product_price:.2f} RMB ({product_total_usd:.2f} USD)")
        print(f"{'IOSS税金总价格:':<35} {total_ioss_tax:.2f} RMB ({ioss_tax_usd:.2f} USD)")
        print(f"{'运费总价格:':<35} {total_shipping_fee:.2f} RMB ({shipping_total_usd:.2f} USD)")
        print(f"{'累计总价格:':<35} {result.total_amount:.2f} RMB ({total_amount_usd:.2f} USD)")
        print("=================================================================================================")
    
    @staticmethod
    def format_results_as_html(result: CalculationResult, product_rule_infos: list = None, product_ioss_infos: list = None, exchange_rate: float = 6.9) -> str:
        """生成HTML格式的查询结果"""
        html_result = "<div style='font-family: Arial, sans-serif;'>"
        html_result += "<h2>查询结果</h2>"

        total_product_price = 0.0
        total_shipping_fee = 0.0

        # 产品价格信息部分
        html_result += "<div style='margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>"
        html_result += "<h3>产品价格信息</h3>"
        html_result += "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse: collapse;'>"
        html_result += "<tr><th>产品名称</th><th>单价</th><th>数量</th><th>产品价格</th></tr>"

        for i, p in enumerate(result.products):
            if p.price > 0:
                product_total = p.price * p.quantity
                total_product_price += product_total
                product_total_usd = product_total / exchange_rate
                html_result += f"<tr><td>{p.name}</td><td>{p.price:.2f}</td><td>{p.quantity}</td><td>{product_total:.2f} RMB ({product_total_usd:.2f} USD)</td></tr>"
            else:
                html_result += f"<tr><td>{p.name}</td><td>-</td><td>{p.quantity}</td><td>-</td></tr>"

        html_result += "</table>"
        html_result += "</div>"

        # IOSS税金信息部分
        total_ioss_tax = result.ioss_taxes
        html_result += "<div style='margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>"
        html_result += "<h3>IOSS税金信息</h3>"
        html_result += "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse: collapse;'>"
        html_result += "<tr><th>产品名称</th><th>目的地</th><th>VAT税率</th><th>服务费率</th><th>VAT税费</th><th>服务费</th><th>IOSS税金</th></tr>"

        if total_ioss_tax > 0 and product_ioss_infos:
            for i, p in enumerate(result.products):
                if p.price > 0 and i < len(product_ioss_infos):
                    ioss_info = product_ioss_infos[i]
                    if ioss_info:
                        vat_rate = ioss_info.get('vat_rate', 0) * 100
                        service_rate = ioss_info.get('service_rate', 0) * 100
                        vat_tax = ioss_info.get('vat_tax', 0)
                        service_fee = ioss_info.get('service_fee', 0)
                        ioss_tax = ioss_info.get('ioss_tax', 0)
                        ioss_tax_usd = ioss_tax / exchange_rate
                        html_result += f"<tr><td>{p.name}</td><td>{p.destination}</td><td>{vat_rate:.1f}%</td><td>{service_rate:.1f}%</td><td>{vat_tax:.2f}</td><td>{service_fee:.2f}</td><td>{ioss_tax:.2f} RMB ({ioss_tax_usd:.2f} USD)</td></tr>"
        else:
            html_result += "<tr><td colspan='7'>没有适用的IOSS税金信息</td></tr>"

        html_result += "</table>"
        html_result += "</div>"

        # 运费价格信息部分
        html_result += "<div style='margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>"
        html_result += "<h3>运费价格信息</h3>"
        html_result += "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse: collapse;'>"
        html_result += "<tr><th>产品名称</th><th>货代公司</th><th>目的地</th><th>参考时效</th><th>重量(KG)</th><th>运费率(RMB/KG)</th><th>手续费(RMB/票)</th><th>运费价格</th></tr>"

        for i, p in enumerate(result.products):
            if p.price > 0:
                rule_info = product_rule_infos[i] if (product_rule_infos and i < len(product_rule_infos)) else {}
                shipping_company = rule_info.get('shipping_company', '')
                estimated_delivery_time = rule_info.get('estimated_delivery_time', '')
                actual_weight = rule_info.get('actual_weight', 0)
                shipping_rate = rule_info.get('shipping_rate', 0)
                registration_fee = rule_info.get('registration_fee', 0)
                shipping_fee = p.shipping_fee
                total_shipping_fee += shipping_fee

                shipping_fee_usd = shipping_fee / exchange_rate
                html_result += f"<tr><td>{p.name}</td><td>{shipping_company}</td><td>{p.destination}</td><td>{estimated_delivery_time}</td><td>{actual_weight:.2f}</td><td>{shipping_rate:.2f}</td><td>{registration_fee:.2f}</td><td>{shipping_fee:.2f} RMB ({shipping_fee_usd:.2f} USD)</td></tr>"
            else:
                html_result += f"<tr><td>{p.name}</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"

        html_result += "</table>"
        html_result += "</div>"

        # 总价格部分
        total_amount = result.total_amount
        html_result += "<div style='margin-top: 20px; padding: 10px; border: 2px solid #4CAF50; border-radius: 5px;'>"
        html_result += "<h3>总价格</h3>"
        product_total_usd = total_product_price / exchange_rate
        shipping_total_usd = total_shipping_fee / exchange_rate
        total_ioss_tax = result.ioss_taxes
        ioss_tax_usd = total_ioss_tax / exchange_rate
        total_amount_usd = total_amount / exchange_rate
        html_result += f"<p>产品总价格: {total_product_price:.2f} RMB ({product_total_usd:.2f} USD)</p>"
        html_result += f"<p>IOSS税金总价格: {total_ioss_tax:.2f} RMB ({ioss_tax_usd:.2f} USD)</p>"
        html_result += f"<p>运费总价格: {total_shipping_fee:.2f} RMB ({shipping_total_usd:.2f} USD)</p>"
        html_result += f"<p>累计总价格: {total_amount:.2f} RMB ({total_amount_usd:.2f} USD)</p>"
        html_result += "</div>"
        html_result += "</div>"

        return html_result
    
    @staticmethod
    def format_product_images(products: List[Product]) -> str:
        """生成产品图片的HTML展示"""
        html_images = "<div style='display: flex; flex-wrap: wrap; gap: 20px;'>"
        for product in products:
            html_images += f"<div style='text-align: center;'>"
            html_images += f"<h3>{product.name}</h3>"
            if hasattr(product, 'image_url') and product.image_url:
                html_images += f"<img src='{product.image_url}' alt='{product.name}' style='max-width: 200px; max-height: 200px;'>"
            else:
                html_images += f"<p>没有找到产品图片</p>"
            html_images += f"<p>数量: {product.quantity}</p>"
            html_images += f"</div>"
        html_images += "</div>"
        return html_images

    @staticmethod
    def print_no_products_message() -> None:
        """打印无产品输入信息"""
        print("未输入任何产品信息，程序退出。")