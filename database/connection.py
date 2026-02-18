"""数据库连接与基础设施管理。

本模块负责数据库的底层基础设施，包括：
- 数据库引擎创建（自动识别 SQLite/PostgreSQL）
- 会话（Session）管理
- 数据库表创建
- 原始SQL执行

本模块不包含任何业务逻辑，仅提供数据库基础操作。
"""
from typing import Optional, Union, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from .models import Base
from config.settings import settings


class DatabaseConnection:
    """数据库连接管理器。

    负责数据库引擎的创建和会话管理，根据数据库URL自动选择
    同步（SQLite）或异步（PostgreSQL）引擎。

    Attributes:
        database_url: 数据库连接URL。
        engine: SQLAlchemy引擎对象（同步或异步）。
        SessionLocal: 会话工厂。
        is_async: 是否为异步引擎。

    Example:
        ```python
        # SQLite（同步，适合开发环境）
        conn = DatabaseConnection("sqlite:///data/store.db")

        # PostgreSQL（异步，适合生产环境）
        conn = DatabaseConnection("postgresql://user:pass@host/db")

        # 使用默认配置
        conn = DatabaseConnection()
        ```
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        """初始化数据库连接。

        Args:
            database_url: 数据库连接URL，如果为None则使用settings中的配置。
                        支持格式：
                        - sqlite:///path/to/db.db (同步)
                        - postgresql://user:pass@host/db (异步)
        """
        self.database_url: str = database_url or settings.database_url

        if self.database_url.startswith("sqlite"):
            self.engine = create_engine(
                self.database_url,
                echo=False,
                connect_args={"check_same_thread": False}
            )
            self.SessionLocal = sessionmaker(
                bind=self.engine, autocommit=False, autoflush=False
            )
            self.is_async: bool = False
        else:
            async_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            self.engine = create_async_engine(async_url, echo=False)
            self.SessionLocal = async_sessionmaker(
                self.engine, class_=AsyncSession
            )
            self.is_async: bool = True

    def create_tables(self) -> None:
        """创建所有数据库表。

        根据 models.py 中定义的所有模型创建对应的数据库表。
        如果表已存在则不会重复创建（幂等操作）。
        """
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Union[Session, AsyncSession]:
        """获取数据库会话。

        Returns:
            数据库会话对象。根据 is_async 属性返回同步或异步会话。
        """
        return self.SessionLocal()

    def execute_raw_sql(self, sql: str, params: Optional[dict] = None) -> Any:
        """执行原始SQL语句。

        注意：此方法应谨慎使用，建议优先使用ORM方法。
        如果必须使用原始SQL，请确保SQL语句安全，避免SQL注入。

        Args:
            sql: SQL语句字符串。
            params: SQL参数字典（可选）。

        Returns:
            SQL执行结果。

        Raises:
            Exception: 如果SQL执行失败。
        """
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            session.commit()
            return result

    def close(self) -> None:
        """关闭数据库连接，释放引擎资源。

        释放连接池中的所有连接。调用后不应再使用此连接实例。
        """
        if self.engine is not None:
            self.engine.dispose()

