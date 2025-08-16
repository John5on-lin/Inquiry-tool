import os
import gspread
from google.oauth2.service_account import Credentials
from models import Product, ShippingRule
from typing import List, Optional
import logging
from config import AppConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ShippingDataSource:
    """运费数据源抽象基类"""
    def load_rules(self) -> List[ShippingRule]:
        raise NotImplementedError("子类必须实现load_rules方法")

class GoogleSheetsShippingSource(ShippingDataSource):
    """Google Sheets运费数据源"""
    def __init__(self, config: AppConfig):
        self.document_id = config.google_sheets['document_id']
        self.sheet_name = config.google_sheets_shipping_sheet_name
        self.credentials_path = config.google_sheets['credentials_path']
        self.shipping_company_column = '货代公司'
        self.attribute_column = '货物属性'
        self.country_column = '国家'
        self.region_column = '区域'
        self.weight_min_column = '重量下限(g)'
        self.weight_max_column = '重量上限(g)'
        self.first_weight_column = '首重（g）'
        self.first_weight_fee_column = '首重费用（元）'
        self.additional_weight_column = '续重（g）'
        self.additional_weight_price_column = '续重单价（元）'
        self.min_delivery_days_column = '时效最早天数'
        self.max_delivery_days_column = '时效最晚天数'
        self.registration_fee_column = '挂号费(RMB/票)'
        self.volume_weight_ratio_column = '体积重量转换比'
        self.shipping_rules: Optional[List[ShippingRule]] = None

    def get_credentials(self):
        """获取Google认证凭证"""
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

    def load_rules(self) -> List[ShippingRule]:
        """加载Google Sheets中的运费规则"""
        if self.shipping_rules is not None:
            return self.shipping_rules

        try:
            logger.info(f"开始从Google Sheets加载运费规则: {self.document_id} - {self.sheet_name}")

            # 加载凭证并授权
            credentials = self.get_credentials()
            client = gspread.authorize(credentials)

            # 打开表格并获取数据
            sheet = client.open_by_key(self.document_id).worksheet(self.sheet_name)
            data = sheet.get_all_records()

            if not data:
                raise ValueError("Google Sheets中没有找到运费规则数据")

            # 验证必要列是否存在
            required_columns = [
                self.shipping_company_column,
                self.attribute_column,
                self.country_column,
                self.region_column,
                self.weight_min_column,
                self.weight_max_column,
                self.first_weight_column,
                self.first_weight_fee_column,
                self.additional_weight_column,
                self.additional_weight_price_column,
                self.min_delivery_days_column,
                self.max_delivery_days_column,
                self.registration_fee_column,
                self.volume_weight_ratio_column
            ]
            if not all(col in data[0] for col in required_columns):
                missing_cols = [col for col in required_columns if col not in data[0]]
                raise ValueError(f"Google Sheets缺少必要列: {missing_cols}")

            # 转换为ShippingRule列表并缓存
            self.shipping_rules = []
            for row in data:
                try:
                    # 处理可能的空值
                    def safe_float(value):
                        if value == '' or value == '-':
                            return 0.0
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return 0.0
                            
                    def safe_int(value):
                        if value == '' or value == '-':
                            return 0
                        try:
                            return int(float(value))  # 先转为float处理小数，再转为int
                        except (ValueError, TypeError):
                            return 0
                    
                    rule = ShippingRule(
                        shipping_company=row[self.shipping_company_column],
                        attribute=row[self.attribute_column],
                        country=row[self.country_column],
                        region=row[self.region_column],
                        weight_min=safe_float(row[self.weight_min_column]),
                        weight_max=safe_float(row[self.weight_max_column]),
                        first_weight=safe_float(row[self.first_weight_column]),
                        first_weight_fee=safe_float(row[self.first_weight_fee_column]),
                        additional_weight=safe_float(row[self.additional_weight_column]),
                        additional_weight_price=safe_float(row[self.additional_weight_price_column]),
                        min_delivery_days=safe_int(row[self.min_delivery_days_column]),
                        max_delivery_days=safe_int(row[self.max_delivery_days_column]),
                        registration_fee=safe_float(row[self.registration_fee_column]),
                        volume_weight_ratio=safe_float(row[self.volume_weight_ratio_column])
                    )
                    self.shipping_rules.append(rule)
                except (ValueError, TypeError) as e:
                    logger.warning(f"行数据无效，已跳过: {row}. 错误: {str(e)}")

            if not self.shipping_rules:
                raise ValueError("没有从Google Sheets中加载到有效的运费规则数据")

            logger.info(f"成功加载{len(self.shipping_rules)}条运费规则")
            return self.shipping_rules

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
            logger.error(f"加载Google Sheets运费规则失败: {str(e)}", exc_info=True)
            raise