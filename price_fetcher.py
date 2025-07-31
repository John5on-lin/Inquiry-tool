import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from models import Product
from typing import List, Dict, Optional
import logging
from config import AppConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceDataSource:
    """价格数据源抽象基类"""
    def load_prices(self) -> Dict[str, float]:
        raise NotImplementedError("子类必须实现load_prices方法")

class ExcelPriceSource(PriceDataSource):
    """Excel价格数据源"""
    def __init__(self, config: AppConfig):
        self.file_path = config.excel_path
        self.required_columns = config.required_columns
        self.product_column = config.product_column
        self.price_column = config.price_column
        self.price_data: Optional[Dict[str, float]] = None

    def load_prices(self) -> Dict[str, float]:
        """加载Excel文件中的价格数据并返回产品-价格字典"""
        if self.price_data is not None:
            return self.price_data

        try:
            logger.info(f"开始从Excel文件加载价格数据: {self.file_path}")
            df = pd.read_excel(self.file_path, engine='openpyxl')

            # 验证必要列是否存在
            if not all(col in df.columns for col in self.required_columns):
                missing_cols = [col for col in self.required_columns if col not in df.columns]
                raise ValueError(f"Excel文件缺少必要列: {missing_cols}")

            # 验证价格列数据类型
            if not pd.api.types.is_numeric_dtype(df[self.price_column]):
                raise TypeError(f"价格列'{self.price_column}'必须包含数字类型数据")

            # 转换为产品-价格字典并缓存
            self.price_data = dict(zip(df[self.product_column], df[self.price_column]))
            logger.info(f"成功加载{len(self.price_data)}个产品的价格数据")
            return self.price_data

        except FileNotFoundError:
            logger.error(f"Excel文件未找到: {self.file_path}")
            raise
        except Exception as e:
            logger.error(f"加载Excel价格数据失败: {str(e)}", exc_info=True)
            raise

class GoogleSheetsPriceSource(PriceDataSource):
    """Google Sheets价格数据源"""
    def __init__(self, config: AppConfig):  # 将Config改为AppConfig
        self.document_id = config.google_sheets['document_id']
        self.sheet_name = config.google_sheets['sheet_name']  # 修正属性名
        self.credentials_path = config.google_sheets['credentials_path']  # 修正属性名
        self.product_column = config.product_column
        self.price_column = config.price_column
        self.price_data: Optional[Dict[str, float]] = None

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

    def load_prices(self) -> Dict[str, float]:
        """加载Google Sheets中的价格数据并返回产品-价格字典"""
        if self.price_data is not None:
            return self.price_data

        try:
            logger.info(f"开始从Google Sheets加载价格数据: {self.document_id} - {self.sheet_name}")

            # 加载凭证并授权
            credentials = self.get_credentials()
            client = gspread.authorize(credentials)

            # 打开表格并获取数据
            sheet = client.open_by_key(self.document_id).worksheet(self.sheet_name)
            data = sheet.get_all_records()

            if not data:
                raise ValueError("Google Sheets中没有找到数据")

            # 验证必要列是否存在
            required_columns = [self.product_column, self.price_column]
            if not all(col in data[0] for col in required_columns):
                missing_cols = [col for col in required_columns if col not in data[0]]
                raise ValueError(f"Google Sheets缺少必要列: {missing_cols}")

            # 转换为产品-价格字典并缓存
            self.price_data = {}
            for row in data:
                product = row[self.product_column]
                price = row[self.price_column]
                try:
                    self.price_data[product] = float(price)
                except (ValueError, TypeError):
                    logger.warning(f"产品'{product}'的价格'{price}'不是有效的数字，已跳过")

            if not self.price_data:
                raise ValueError("没有从Google Sheets中加载到有效的产品价格数据")

            logger.info(f"成功加载{len(self.price_data)}个产品的价格数据")
            return self.price_data

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
            logger.error(f"加载Google Sheets价格数据失败: {str(e)}", exc_info=True)
            raise

class PriceFetcher:
    """价格查询器，支持多种数据源"""
    def __init__(self, config: AppConfig):  # 将Config改为AppConfig
        self.config = config
        self.data_source: Optional[PriceDataSource] = None
        self._initialize_data_source()

    def _initialize_data_source(self) -> None:
        """根据配置初始化适当的数据源"""
        try:
            if self.config.data_source == "google_sheets": 
                self.data_source = GoogleSheetsPriceSource(self.config)
                logger.info("已初始化Google Sheets价格数据源")
            else:
                self.data_source = ExcelPriceSource(self.config)
                logger.info("已初始化Excel价格数据源")
        except Exception as e:
            logger.error(f"初始化价格数据源失败: {str(e)}")
            raise

    def fetch_prices(self, products: List[Product]) -> List[Product]:
        """为产品列表获取价格"""
        if not self.data_source:
            raise RuntimeError("价格数据源未初始化，请检查配置")

        try:
            price_data = self.data_source.load_prices()

            for product in products:
                if product.name in price_data:
                    product.price = price_data[product.name]
                    logger.info(f"已找到产品'{product.name}'的价格: {product.price}")
                else:
                    logger.warning(f"未找到产品'{product.name}'的价格数据")

            return products

        except Exception as e:
            logger.error(f"获取产品价格失败: {str(e)}")