"""初始化数据库"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from config.business_config import business_config
from loguru import logger


def init_database():
    """初始化数据库和种子数据"""
    logger.info("Initializing database...")

    # 创建数据库管理器
    db = DatabaseManager()

    # 创建所有表
    logger.info("Creating tables...")
    db.create_tables()

    # 插入种子数据
    logger.info("Inserting seed data...")

    # 插入服务类型（从 business_config 获取）
    for service_type in business_config.get_service_types():
        db.service_types.get_or_create(
            name=service_type['name'],
            default_price=service_type.get('default_price'),
            category=service_type.get('category')
        )
        logger.info(f"Created service type: {service_type['name']}")

    logger.info("Database initialization completed!")


if __name__ == "__main__":
    init_database()
