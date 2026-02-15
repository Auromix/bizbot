"""数据库初始化测试。

测试数据库创建、表结构、连接等基础功能。
"""
import pytest
import tempfile
import shutil
import os

from db.repository import DatabaseRepository
from db.models import Base


class TestDatabaseInitialization:
    """数据库初始化测试类。"""
    
    def test_create_tables(self):
        """测试创建数据库表。"""
        # 创建临时数据库
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_init.db")
        db_url = f"sqlite:///{db_path}"
        
        try:
            repo = DatabaseRepository(database_url=db_url)
            repo.create_tables()
            
            # 验证表已创建（通过查询表名）
            with repo.get_session() as session:
                from sqlalchemy import inspect
                inspector = inspect(repo.engine)
                tables = inspector.get_table_names()
                
                # 检查关键表是否存在
                assert "employees" in tables
                assert "customers" in tables
                assert "memberships" in tables
                assert "service_types" in tables
                assert "service_records" in tables
                assert "products" in tables
                assert "product_sales" in tables
                assert "referral_channels" in tables
                assert "plugin_data" in tables
                assert "raw_messages" in tables
                assert "daily_summaries" in tables
        finally:
            shutil.rmtree(temp_dir)
    
    def test_database_url_configuration(self):
        """测试数据库URL配置。"""
        # SQLite配置
        sqlite_url = "sqlite:///test.db"
        repo_sqlite = DatabaseRepository(database_url=sqlite_url)
        assert repo_sqlite.database_url == sqlite_url
        assert repo_sqlite.is_async is False
        
        # PostgreSQL配置（应该识别为异步，但可能缺少asyncpg驱动）
        postgres_url = "postgresql://user:pass@localhost/db"
        try:
            repo_postgres = DatabaseRepository(database_url=postgres_url)
            assert repo_postgres.database_url == postgres_url
            assert repo_postgres.is_async is True
        except ModuleNotFoundError:
            # 如果没有安装asyncpg，跳过此测试
            pytest.skip("asyncpg not installed, skipping PostgreSQL test")
    
    def test_get_session(self):
        """测试获取数据库会话。"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_session.db")
        db_url = f"sqlite:///{db_path}"
        
        try:
            repo = DatabaseRepository(database_url=db_url)
            repo.create_tables()
            
            # 测试获取会话
            session = repo.get_session()
            assert session is not None
            
            # 测试会话可以正常使用
            with session:
                from db.models import Employee
                count = session.query(Employee).count()
                assert count >= 0  # 应该能正常查询
        finally:
            shutil.rmtree(temp_dir)
    
    def test_multiple_repositories_independent(self):
        """测试多个Repository实例相互独立。"""
        temp_dir = tempfile.mkdtemp()
        db_path1 = os.path.join(temp_dir, "test1.db")
        db_path2 = os.path.join(temp_dir, "test2.db")
        
        try:
            repo1 = DatabaseRepository(database_url=f"sqlite:///{db_path1}")
            repo2 = DatabaseRepository(database_url=f"sqlite:///{db_path2}")
            
            repo1.create_tables()
            repo2.create_tables()
            
            # 在repo1中创建数据
            customer1 = repo1.get_or_create_customer("客户1")
            
            # 在repo2中创建数据
            customer2 = repo2.get_or_create_customer("客户2")
            
            # 验证两个数据库独立
            assert customer1.id > 0
            assert customer2.id > 0
            
            # 验证repo1中只有客户1（需要提交）
            with repo1.get_session() as session:
                from db.models import Customer
                session.commit()  # 确保数据已提交
                customers = session.query(Customer).all()
                assert len(customers) == 1
                assert customers[0].name == "客户1"
            
            # 验证repo2中只有客户2（需要提交）
            with repo2.get_session() as session:
                from db.models import Customer
                session.commit()  # 确保数据已提交
                customers = session.query(Customer).all()
                assert len(customers) == 1
                assert customers[0].name == "客户2"
        finally:
            shutil.rmtree(temp_dir)

