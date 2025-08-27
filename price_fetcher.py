import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from models import Product
from typing import List, Dict, Optional, Any
import logging
from config import AppConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceDataSource:
    """价格数据源抽象基类"""
    def load_product_data(self) -> Dict[str, Dict[str, Any]]:
        raise NotImplementedError("子类必须实现load_product_data方法")

class ExcelPriceSource(PriceDataSource):
    """Excel价格数据源"""
    def __init__(self, config: AppConfig):
        self.file_path = config.excel_path
        self.required_columns = config.required_columns
        self.product_column = config.product_column
        self.price_column = config.price_column
        self.attribute_column = config.attribute_column
        self.weight_column = config.weight_column
        self.length_column = config.length_column
        self.width_column = config.width_column
        self.height_column = config.height_column
        self.ioss_price_column = config.ioss_price_column
        self.image_url_column = config.image_url_column
        self.product_data: Optional[Dict[str, Dict[str, Any]]] = None

    def load_product_data(self) -> Dict[str, Dict[str, Any]]:
        """加载Excel文件中的产品数据并返回产品-数据字典"""
        if self.product_data is not None:
            return self.product_data

        try:
            logger.info(f"开始从Excel文件加载产品数据: {self.file_path}")
            df = pd.read_excel(self.file_path, engine='openpyxl')

            # 验证必要列是否存在
            if not all(col in df.columns for col in self.required_columns):
                missing_cols = [col for col in self.required_columns if col not in df.columns]
                raise ValueError(f"Excel文件缺少必要列: {missing_cols}")

            # 将数值列转换为数字类型，将非数字值转换为NaN
            numeric_columns = [self.price_column, self.weight_column, self.length_column, self.width_column, self.height_column, self.ioss_price_column]
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # 将NaN值填充为0
            df[numeric_columns] = df[numeric_columns].fillna(0)

            # 转换为产品-数据字典并缓存
            self.product_data = {}
            for _, row in df.iterrows():
                product_name = row[self.product_column]
                self.product_data[product_name] = {
                    'price': float(row[self.price_column]),
                    'attribute': row[self.attribute_column],
                    'weight': float(row[self.weight_column]),
                    'length': float(row[self.length_column]),
                    'width': float(row[self.width_column]),
                    'height': float(row[self.height_column]),
                    'ioss_price': float(row[self.ioss_price_column]),
                    'image_url': row[self.image_url_column] if self.image_url_column in row else ''
                }

            logger.info(f"成功加载{len(self.product_data)}个产品的数据")
            return self.product_data

        except FileNotFoundError:
            logger.error(f"Excel文件未找到: {self.file_path}")
            raise
        except Exception as e:
            logger.error(f"加载Excel产品数据失败: {str(e)}", exc_info=True)
            raise

class GoogleSheetsPriceSource(PriceDataSource):
    """Google Sheets价格数据源"""
    def __init__(self, config: AppConfig):
        self.document_id = config.google_sheets['document_id']
        self.sheet_name = config.google_sheets['sheet_name']
        self.credentials_path = config.google_sheets['credentials_path']
        self.product_column = config.product_column
        self.price_column = config.price_column
        self.attribute_column = config.attribute_column
        self.weight_column = config.weight_column
        self.length_column = config.length_column
        self.width_column = config.width_column
        self.height_column = config.height_column
        self.ioss_price_column = config.ioss_price_column
        self.image_url_column = config.image_url_column
        self.product_data: Optional[Dict[str, Dict[str, Any]]] = None

    def get_credentials(self):
        """获取Google认证凭证
        优先从环境变量GOOGLE_APPLICATION_CREDENTIALS获取路径，
        如果不存在则使用配置中的路径
        """
        # 检查是否有GOOGLE_APPLICATION_CREDENTIALS环境变量
        env_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if env_credentials_path:
            logger.info(f"使用环境变量GOOGLE_APPLICATION_CREDENTIALS指定的凭证路径: {env_credentials_path}")
            return Credentials.from_service_account_file(
                env_credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
        else:
            logger.info(f"使用配置中的凭证路径: {self.credentials_path}")
            return Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )

    def load_product_data(self) -> Dict[str, Dict[str, Any]]:
        """加载Google Sheets中的产品数据并返回产品-数据字典"""
        if self.product_data is not None:
            return self.product_data

        try:
            logger.info(f"开始从Google Sheets加载产品数据: {self.document_id} - {self.sheet_name}")

            # 加载凭证并授权
            credentials = self.get_credentials()
            client = gspread.authorize(credentials)

            # 打开表格并获取数据
            sheet = client.open_by_key(self.document_id).worksheet(self.sheet_name)
            data = sheet.get_all_records()

            if not data:
                raise ValueError("Google Sheets中没有找到数据")

            # 验证必要列是否存在
            required_columns = [self.product_column, self.price_column, self.attribute_column, self.weight_column, self.length_column, self.width_column, self.height_column, self.ioss_price_column, self.image_url_column]
            if not all(col in data[0] for col in required_columns):
                missing_cols = [col for col in required_columns if col not in data[0]]
                raise ValueError(f"Google Sheets缺少必要列: {missing_cols}")

            # 转换为产品-数据字典并缓存
            self.product_data = {}
            for row in data:
                product = row[self.product_column]
                try:
                    # 处理价格字段
                    price_str = row[self.price_column]
                    price = float(price_str) if price_str else 0.0

                    attribute = row[self.attribute_column]

                    # 处理重量字段
                    weight_str = row[self.weight_column]
                    weight = float(weight_str) if weight_str else 0.0

                    # 处理长度字段
                    length_str = row[self.length_column]
                    length = float(length_str) if length_str else 0.0

                    # 处理宽度字段
                    width_str = row[self.width_column]
                    width = float(width_str) if width_str else 0.0

                    # 处理高度字段
                    height_str = row[self.height_column]
                    height = float(height_str) if height_str else 0.0

                    # 处理IOSS价格字段
                    ioss_price_str = row[self.ioss_price_column]
                    ioss_price = float(ioss_price_str) if ioss_price_str else 0.0

                    # 处理产品图片地址字段
                    image_url = row.get(self.image_url_column, '')

                    self.product_data[product] = {
                        'price': price,
                        'attribute': attribute,
                        'weight': weight,
                        'length': length,
                        'width': width,
                        'height': height,
                        'ioss_price': ioss_price,
                        'image_url': image_url
                    }
                except (ValueError, TypeError) as e:
                    logger.warning(f"产品'{product}'的数据无效: {str(e)}，已跳过")

            if not self.product_data:
                raise ValueError("没有从Google Sheets中加载到有效的产品数据")

            logger.info(f"成功加载{len(self.product_data)}个产品的数据")
            return self.product_data

        except FileNotFoundError:
            logger.error(f"凭证文件未找到: {self.credentials_path}")
            raise
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"找不到指定的Google Sheets文档: {self.document_id}")
            raise
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"在文档中找不到指定的工作表: {self.sheet_name}")
            raise
        except Exception as e:
            logger.error(f"加载Google Sheets产品数据失败: {str(e)}", exc_info=True)
            raise

class PriceFetcher:
    """价格查询器，支持多种数据源"""
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_source: Optional[PriceDataSource] = None
        self._initialize_data_source()

    def _initialize_data_source(self) -> None:
        """根据配置初始化适当的数据源"""
        try:
            if self.config.data_source == "google_sheets": 
                self.data_source = GoogleSheetsPriceSource(self.config)
                logger.info("已初始化Google Sheets产品数据源")
            else:
                self.data_source = ExcelPriceSource(self.config)
                logger.info("已初始化Excel产品数据源")
        except Exception as e:
            logger.error(f"初始化产品数据源失败: {str(e)}")
            raise

    def fetch_product_data(self, products: List[Product]) -> List[Product]:
        """为产品列表获取完整数据（价格、重量、尺寸等）"""
        if not self.data_source:
            raise RuntimeError("产品数据源未初始化，请检查配置")

        try:
            product_data = self.data_source.load_product_data()

            for product in products:
                if product.sku in product_data:
                    data = product_data[product.sku]
                    product.price = data['price']
                    product.attribute = data['attribute']
                    product.weight = data['weight']
                    product.length = data['length']
                    product.width = data['width']
                    product.height = data['height']
                    product.ioss_price = data['ioss_price']
                    if 'image_url' in data:
                        product.image_url = data['image_url']
                    logger.info(f"已找到产品'{product.sku}'的完整数据")
                else:
                    logger.warning(f"未找到产品'{product.sku}'的产品数据")

            return products

        except Exception as e:
            logger.error(f"获取产品数据失败: {str(e)}")
            raise
