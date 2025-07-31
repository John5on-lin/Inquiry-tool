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
    
    # Google Sheets配置
    google_sheets: dict
    
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
    required_columns = [product_column, price_column]
    
    # Google Sheets配置
    google_sheets_document_id = os.getenv('GOOGLE_SHEETS_DOCUMENT_ID', '1Lrulu0_QClveyiXQHcgMknHYQMkwr-qE-EATwc0A2iQ')
    google_sheets_sheet_name = os.getenv('GOOGLE_SHEETS_SHEET_NAME', 'Sheet1')
    google_credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    
    # 构建配置对象
    config = AppConfig(
        app_version=app_version,
        title=title,
        data_source=data_source,
        excel_path=excel_path,
        required_columns=required_columns,
        product_column=product_column,
        price_column=price_column,
        google_sheets={
            'document_id': google_sheets_document_id,
            'sheet_name': google_sheets_sheet_name,
            'credentials_path': os.path.join(current_dir, google_credentials_path)
        }
    )
    
    return config