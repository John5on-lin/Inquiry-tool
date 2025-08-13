import gspread
from google.oauth2.service_account import Credentials
from models import IossRule
from typing import List, Optional
import logging
import os
from config import AppConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IossDataSource:
    """IOSS税率数据源抽象基类"""
    def load_rules(self) -> List[IossRule]:
        raise NotImplementedError("子类必须实现load_rules方法")

class GoogleSheetsIossSource(IossDataSource):
    """Google Sheets IOSS税率数据源"""
    def __init__(self, config: AppConfig):
        self.document_id = config.google_sheets['document_id']
        self.sheet_name = config.google_sheets_ioss_sheet_name
        self.credentials_path = config.google_sheets['credentials_path']
        self.country_column = config.ioss_country_column
        self.vat_rate_column = config.ioss_vat_rate_column
        self.service_rate_column = config.ioss_service_rate_column
        self.ioss_rules: Optional[List[IossRule]] = None

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

    def load_rules(self) -> List[IossRule]:
        """加载Google Sheets中的IOSS税率规则"""
        if self.ioss_rules is not None:
            return self.ioss_rules

        try:
            logger.info(f"开始从Google Sheets加载IOSS税率规则: {self.document_id} - {self.sheet_name}")

            # 加载凭证并授权
            credentials = self.get_credentials()
            client = gspread.authorize(credentials)

            # 打开表格并获取数据
            sheet = client.open_by_key(self.document_id).worksheet(self.sheet_name)
            data = sheet.get_all_records()

            if not data:
                raise ValueError("Google Sheets中没有找到IOSS税率规则数据")

            # 验证必要列是否存在
            required_columns = [
                self.country_column,
                self.vat_rate_column,
                self.service_rate_column
            ]
            if not all(col in data[0] for col in required_columns):
                missing_cols = [col for col in required_columns if col not in data[0]]
                raise ValueError(f"Google Sheets缺少必要列: {missing_cols}")

            # 转换为IossRule列表并缓存
            self.ioss_rules = []
            for row in data:
                try:
                    # 处理带百分号的税率值
                    vat_rate_str = str(row[self.vat_rate_column]).replace('%', '').strip()
                    service_rate_str = str(row[self.service_rate_column]).replace('%', '').strip()
                    
                    rule = IossRule(
                        country=row[self.country_column],
                        vat_rate=float(vat_rate_str) if vat_rate_str else 0.0,
                        service_rate=float(service_rate_str) if service_rate_str else 0.0
                    )
                    self.ioss_rules.append(rule)
                except (ValueError, TypeError) as e:
                    logger.warning(f"行数据无效，已跳过: {row}. 错误: {str(e)}")

            if not self.ioss_rules:
                raise ValueError("没有从Google Sheets中加载到有效的IOSS税率规则数据")

            logger.info(f"成功加载{len(self.ioss_rules)}条IOSS税率规则")
            return self.ioss_rules

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
            logger.error(f"加载Google Sheets IOSS税率规则失败: {str(e)}", exc_info=True)
            raise

class IossFetcher:
    """IOSS税率查询器"""
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_source = GoogleSheetsIossSource(config)
        self.ioss_rules = None  # 初始化为None，实现懒加载

    def _ensure_rules_loaded(self):
        """确保IOSS税率规则已加载"""
        if self.ioss_rules is None:
            self.ioss_rules = self.data_source.load_rules()

    def get_ioss_rule(self, country: str) -> Optional[IossRule]:
        """根据国家获取IOSS税率规则"""
        self._ensure_rules_loaded()  # 调用懒加载方法
        for rule in self.ioss_rules:
            if rule.country.lower() == country.lower():
                return rule
        logger.warning(f"未找到国家'{country}'的IOSS税率规则")
        return None