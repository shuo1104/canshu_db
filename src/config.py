"""售后参数搜索工具配置。"""
import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DATA_DIR = PROJECT_ROOT / "数据库_副本"
DATA_DIR = Path(os.environ.get("APS_DATA_DIR", DEFAULT_DATA_DIR))


@dataclass(frozen=True)
class MySQLConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    charset: str = "utf8mb4"


DB_CONFIG = MySQLConfig(
    host=os.environ.get("APS_DB_HOST", "127.0.0.1"),
    port=int(os.environ.get("APS_DB_PORT", "3306")),
    database=os.environ.get("APS_DB_NAME", "aftersales"),
    user=os.environ.get("APS_DB_USER", "aftersales"),
    password=os.environ.get("APS_DB_PASSWORD", "aftersales_password"),
    charset=os.environ.get("APS_DB_CHARSET", "utf8mb4"),
)

DB_HOST = DB_CONFIG.host
DB_PORT = DB_CONFIG.port
DB_NAME = DB_CONFIG.database
DB_USER = DB_CONFIG.user
DB_PASSWORD = DB_CONFIG.password
DB_CHARSET = DB_CONFIG.charset

# 搜索分页
PAGE_SIZE = 20
