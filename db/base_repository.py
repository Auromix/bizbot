"""基础数据库访问层。

提供通用的数据库操作，不包含业务逻辑。
业务逻辑应该通过 BusinessLogicAdapter 实现。
"""
from typing import Optional, Union, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from db.models import Base
from config.settings import settings


class BaseRepository:
    """基础数据库访问层。
    
    只提供通用的数据库操作，不包含业务逻辑。
    业务逻辑应该通过 BusinessLogicAdapter 实现。
    
    Attributes:
        database_url: 数据库连接URL。
        engine: SQLAlchemy引擎对象（同步或异步）。
        SessionLocal: 会话工厂。
        is_async: 是否为异步引擎。
    """
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        """初始化基础数据库访问层。
        
        Args:
            database_url: 数据库连接URL，如果为None则使用settings中的配置。
                        支持格式：
                        - sqlite:///path/to/db.db (同步)
                        - postgresql://user:pass@host/db (异步)
        """
        self.database_url: str = database_url or settings.database_url
        
        # 判断是否为异步数据库URL
        if self.database_url.startswith("sqlite"):
            # SQLite 使用同步引擎
            self.engine = create_engine(
                self.database_url.replace("sqlite:///", "sqlite:///"),
                echo=False,
                connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
            )
            self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
            self.is_async: bool = False
        else:
            # PostgreSQL 等使用异步引擎
            async_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
            self.engine = create_async_engine(async_url, echo=False)
            self.SessionLocal = async_sessionmaker(self.engine, class_=AsyncSession)
            self.is_async: bool = True
    
    def create_tables(self) -> None:
        """创建所有数据库表。
        
        根据models.py中定义的所有模型创建对应的数据库表。
        如果表已存在则不会重复创建。
        """
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Union[Session, AsyncSession]:
        """获取数据库会话。
        
        Returns:
            数据库会话对象。根据is_async属性返回同步或异步会话。
        """
        return self.SessionLocal()
    
    def execute_raw_sql(self, sql: str, params: Optional[dict] = None) -> Any:
        """执行原始SQL（用于复杂查询）。
        
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
            # 使用text()包装SQL字符串，确保安全执行
            result = session.execute(text(sql), params or {})
            session.commit()
            return result

