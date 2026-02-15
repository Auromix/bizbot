"""数据库测试专用fixtures。"""
import pytest
import tempfile
import shutil
import os
from datetime import datetime

from db.repository import DatabaseRepository


@pytest.fixture
def temp_db():
    """创建临时数据库。
    
    Yields:
        DatabaseRepository: 临时数据库的Repository实例。
    """
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    db_url = f"sqlite:///{db_path}"
    
    # 创建数据库
    repo = DatabaseRepository(database_url=db_url)
    repo.create_tables()
    
    yield repo
    
    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_datetime():
    """示例日期时间。
    
    Returns:
        datetime: 示例日期时间对象。
    """
    return datetime(2024, 1, 28, 10, 0, 0)

