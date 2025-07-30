import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    """应用程序配置"
    # 数据源配置
    data_source: str = "google_sheets"  # 支持 "excel" 或 "google_sheets"
    
    # Excel配置
    excel_path: str = "price.xlsx"
    required_columns: list[str] = None
    product_column: str = "产品"  # 添加产品列配置
    price_column: str = "价格"    # 添加价格列配置
    
    # Google Sheets配置
    google_sheets: dict = None
    
    # 应用信息
    app_version: str = "v3.0"
    title: str = "产品价格查询工具"

def load_config() -> AppConfig:
    """加载应用配置"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 默认配置
    config = AppConfig(
        required_columns=['产品', '价格'],
        google_sheets={
            'document_id': '1Lrulu0_QClveyiXQHcgMknHYQMkwr-qE-EATwc0A2iQ',
            'sheet_name': 'Sheet1',
            'credentials_path': os.path.join(current_dir, 'credentials.json')
        }
    )
    
    # 可从环境变量或配置文件加载实际配置
    # 这里简化处理，实际项目中建议使用JSON或环境变量
    config.data_source = os.getenv('DATA_SOURCE', 'google_sheets')
    
    return config