import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

@dataclass
class AppConfig:
    """应用程序配置"""
    # 数据源配置
    data_source: str
    
    # Excel配置
    excel_path: str
    required_columns: list[str]
    product_column: str
    price_column: str
    attribute_column: str
    weight_column: str
    length_column: str
    width_column: str
    height_column: str
    ioss_price_column: str
    image_url_column: str
    
    # Google Sheets配置
    google_sheets: dict
    google_sheets_shipping_sheet_name: str
    google_sheets_ioss_sheet_name: str
    
    # IOSS税率表列名配置
    ioss_country_column: str
    ioss_vat_rate_column: str
    ioss_service_rate_column: str
    
    # 应用信息
    app_version: str
    title: str

def load_config() -> AppConfig:
    """加载应用配置"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 从环境变量加载配置
    app_version = os.getenv('APP_VERSION', 'v3.0')
    title = os.getenv('TITLE', '产品价格查询工具')
    data_source = os.getenv('DATA_SOURCE', 'google_sheets')
    
    # Excel配置
    excel_path = os.getenv('EXCEL_PATH', 'price.xlsx')
    product_column = os.getenv('PRODUCT_COLUMN', '产品')
    price_column = os.getenv('PRICE_COLUMN', '价格')
    attribute_column = os.getenv('ATTRIBUTE_COLUMN', '属性')
    weight_column = os.getenv('WEIGHT_COLUMN', '重量')
    length_column = os.getenv('LENGTH_COLUMN', '长')
    width_column = os.getenv('WIDTH_COLUMN', '宽')
    height_column = os.getenv('HEIGHT_COLUMN', '高')
    ioss_price_column = os.getenv('IOSS_PRICE_COLUMN', 'IOSS价格')
    image_url_column = os.getenv('IMAGE_URL_COLUMN', '产品图片地址')
    required_columns = [product_column, price_column, attribute_column, weight_column, length_column, width_column, height_column, ioss_price_column, image_url_column]
    
    # Google Sheets配置
    google_sheets_document_id = os.getenv('GOOGLE_SHEETS_DOCUMENT_ID', '1Lrulu0_QClveyiXQHcgMknHYQMkwr-qE-EATwc0A2iQ')
    google_sheets_sheet_name = os.getenv('GOOGLE_SHEETS_SHEET_NAME', 'Sheet1')
    google_sheets_shipping_sheet_name = os.getenv('GOOGLE_SHEETS_SHIPPING_SHEET_NAME', 'Sheet2')
    google_sheets_ioss_sheet_name = os.getenv('GOOGLE_SHEETS_IOSS_SHEET_NAME', 'Sheet3')
    google_credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    
    # IOSS税率表列名配置
    ioss_country_column = os.getenv('IOSS_COUNTRY_COLUMN', '国家')
    ioss_vat_rate_column = os.getenv('IOSS_VAT_RATE_COLUMN', 'VAT税率')
    ioss_service_rate_column = os.getenv('IOSS_SERVICE_RATE_COLUMN', '服务费率')
    
    # 构建配置对象
    config = AppConfig(
        app_version=app_version,
        title=title,
        data_source=data_source,
        excel_path=excel_path,
        required_columns=required_columns,
        product_column=product_column,
        price_column=price_column,
        attribute_column=attribute_column,
        weight_column=weight_column,
        length_column=length_column,
        width_column=width_column,
        height_column=height_column,
        ioss_price_column=ioss_price_column,
        image_url_column=image_url_column,
        google_sheets={
            'document_id': google_sheets_document_id,
            'sheet_name': google_sheets_sheet_name,
            'credentials_path': os.path.join(current_dir, google_credentials_path)
        },
        google_sheets_shipping_sheet_name=google_sheets_shipping_sheet_name,
        google_sheets_ioss_sheet_name=google_sheets_ioss_sheet_name,
        ioss_country_column=ioss_country_column,
        ioss_vat_rate_column=ioss_vat_rate_column,
        ioss_service_rate_column=ioss_service_rate_column
    )
    return config