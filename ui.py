import gradio as gr

def create_interface():
    # 函数内导入以避免循环依赖
    from main import process_excel, load_shipping_rules, show_selection, load_products, check_pricing
    with gr.Blocks(title="多功能工具") as interface:
        gr.Markdown("# 工具集合")

        with gr.Tabs():
            # 第一个Tab: 产品价格与运费查询
            with gr.Tab("产品价格与运费"):
                gr.Markdown("## 产品价格查询与运费计算工具")

                # 第一步：输入产品信息
                with gr.Row():
                    with gr.Column(scale=4):
                        input_text = gr.Textbox(
                            lines=5,
                            label="输入产品信息（每行一个产品，格式：产品名称,数量）",
                            placeholder="例如：\n苹果, 2\n香蕉, 3"
                        )
                    with gr.Column(scale=1, min_width=100):
                        load_btn = gr.Button("加载产品")

                # 产品图片展示区域
                product_images = gr.HTML(label="产品图片")

                # 第二步：输入目的地、汇率和体积重量转换比
                with gr.Row():
                    with gr.Column():
                        destination = gr.Textbox(label="目的地国家", placeholder="例如：美国")
                    with gr.Column():
                        exchange_rate = gr.Number(label="美元换算汇率", value=6.9, precision=2)
                    with gr.Column():
                        volume_weight_ratio = gr.Number(label="体积重量转换比", value=6000)
                shipping_rules_btn = gr.Button("查询运费表")

                # 第三步：选择确认货代公司
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 选择货代公司")
                        checkbox = gr.CheckboxGroup(choices=[], label="可选公司", info="勾选需要的货代公司")
                        selection_output = gr.Textbox(label="选择结果", lines=5)

                # 使用Gradio State管理产品数据
                id_map_state = gr.State({}) 
                selection_text_state = gr.State(None)
                products_state = gr.State([]) 

                # 交互逻辑
                shipping_rules_btn.click(
                    fn=load_shipping_rules,
                    inputs=[destination, volume_weight_ratio, products_state],
                    outputs=[checkbox, id_map_state]
                )
                checkbox.change(
                    fn=show_selection,
                    inputs=[checkbox, id_map_state],
                    outputs=[selection_output, selection_text_state]
                )

                # 提交按钮
                submit_btn = gr.Button("报价查询")
                result_output = gr.HTML(label="报价查询结果")

                # 按钮事件
                load_btn.click(fn=load_products, inputs=[input_text, products_state], outputs=[product_images, products_state])
                submit_btn.click(
                    fn=check_pricing,
                    inputs=[destination, exchange_rate, selection_text_state, products_state],
                    outputs=[result_output]
                )

            # 第二个Tab: Invoice 助理
            with gr.Tab("Invoice 助理"):
                gr.Markdown("## 订单相关Excel上传与处理")

                # 文件上传组件
                product_excel = gr.File(label="上传订单详情Excel", file_count="single", file_types=[".xlsx", ".xls"])
                shipping_excel = gr.File(label="上传订单运费Excel", file_count="single", file_types=[".xlsx", ".xls"])

                # 汇率输入
                exchange_rate = gr.Number(label="美元换算汇率", value=6.9, precision=2)

                # 上传按钮
                upload_btn = gr.Button("上传并处理")

                # 状态消息组件
                status_message = gr.Textbox(label="处理状态", lines=1)

                # 发票信息展示组件
                invoice_output = gr.HTML(label="发票信息")

                upload_btn.click(fn=process_excel, inputs=[product_excel, shipping_excel, exchange_rate], outputs=[status_message, invoice_output])

    return interface