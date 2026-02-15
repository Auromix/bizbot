"""数据访问层。

本模块提供数据库访问的Repository模式实现，封装了所有数据库操作。
支持同步和异步数据库引擎，自动根据数据库URL类型选择。
"""
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from loguru import logger

from db.models import (
    Base, Employee, Customer, Membership, ServiceType, ServiceRecord,
    Product, ProductSale, InventoryLog, RawMessage, Correction, DailySummary,
    ReferralChannel, PluginData
)
from config.settings import settings


class DatabaseRepository:
    """数据库访问层。
    
    提供统一的数据库访问接口，封装了所有业务相关的数据库操作。
    支持SQLite（同步）和PostgreSQL等（异步）数据库引擎。
    
    Attributes:
        database_url: 数据库连接URL。
        engine: SQLAlchemy引擎对象（同步或异步）。
        SessionLocal: 会话工厂。
        is_async: 是否为异步引擎。
    """
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        """初始化数据库访问层。
        
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
    
    # ========== RawMessage 相关 ==========
    
    def save_raw_message(self, msg_data: Dict[str, Any]) -> int:
        """保存原始消息。
        
        保存从微信群聊接收到的原始消息。如果消息已存在（通过wechat_msg_id判断），
        则返回已存在消息的ID，实现去重。
        
        Args:
            msg_data: 消息数据字典，包含以下键：
                - wechat_msg_id: 微信消息ID（用于去重）
                - sender_nickname: 发送者昵称（必填）
                - sender_wechat_id: 发送者微信ID（可选）
                - content: 消息内容（必填）
                - msg_type: 消息类型（可选，默认"text"）
                - group_id: 群组ID（可选）
                - timestamp: 消息时间戳（必填）
                - is_at_bot: 是否@机器人（可选，默认False）
                - is_business: 是否为业务消息（可选）
                - parse_status: 解析状态（可选，默认"pending"）
        
        Returns:
            消息记录ID（新建或已存在的）。
        """
        with self.get_session() as session:
            # 检查是否已存在（去重）
            existing = session.query(RawMessage).filter(
                RawMessage.wechat_msg_id == msg_data.get("wechat_msg_id")
            ).first()
            
            if existing:
                return existing.id
            
            msg = RawMessage(
                wechat_msg_id=msg_data.get("wechat_msg_id"),
                sender_nickname=msg_data.get("sender_nickname"),
                sender_wechat_id=msg_data.get("sender_wechat_id"),
                content=msg_data.get("content"),
                msg_type=msg_data.get("msg_type", "text"),
                group_id=msg_data.get("group_id"),
                timestamp=msg_data.get("timestamp"),
                is_at_bot=msg_data.get("is_at_bot", False),
                is_business=msg_data.get("is_business"),
                parse_status=msg_data.get("parse_status", "pending")
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            return msg.id
    
    def update_parse_status(self, msg_id: int, status: str, 
                           result: Optional[Dict[str, Any]] = None, 
                           error: Optional[str] = None) -> None:
        """更新消息解析状态。
        
        Args:
            msg_id: 消息记录ID。
            status: 新的解析状态（pending/parsed/failed/ignored）。
            result: 解析结果字典（可选）。
            error: 解析错误信息（可选）。
        """
        with self.get_session() as session:
            msg = session.query(RawMessage).filter(RawMessage.id == msg_id).first()
            if msg:
                msg.parse_status = status
                if result:
                    msg.parse_result = result
                if error:
                    msg.parse_error = error
                session.commit()
    
    # ========== Employee 相关 ==========
    
    def get_or_create_employee(self, name: str, wechat_nickname: Optional[str] = None, 
                               session: Optional[Session] = None) -> Employee:
        """获取或创建员工。
        
        根据姓名或微信昵称查找员工，如果不存在则创建新员工。
        
        Args:
            name: 员工姓名（必填）。
            wechat_nickname: 微信昵称（可选）。
            session: 数据库会话（可选）。如果为None，创建新会话并自动提交。
        
        Returns:
            员工对象（已存在或新创建的）。
        """
        if session is None:
            with self.get_session() as sess:
                result = self._get_or_create_employee_in_session(name, wechat_nickname, sess)
                sess.commit()  # 自动提交，确保数据持久化
                employee_id = result.id
            # session关闭后，重新查询对象
            with self.get_session() as sess:
                return sess.query(Employee).filter(Employee.id == employee_id).first()
        else:
            return self._get_or_create_employee_in_session(name, wechat_nickname, session)
    
    def _get_or_create_employee_in_session(self, name: str, wechat_nickname: Optional[str], 
                                           session: Session) -> Employee:
        """在指定会话中获取或创建员工（内部方法）。
        
        Args:
            name: 员工姓名。
            wechat_nickname: 微信昵称。
            session: 数据库会话。
        
        Returns:
            员工对象。
        """
        employee = session.query(Employee).filter(
            or_(
                Employee.name == name,
                Employee.wechat_nickname == wechat_nickname
            )
        ).first()
        
        if not employee:
            employee = Employee(name=name, wechat_nickname=wechat_nickname)
            session.add(employee)
            session.flush()  # 使用 flush 而不是 commit，让外层会话控制提交
            session.refresh(employee)
        
        return employee
    
    # ========== Customer 相关 ==========
    
    def get_or_create_customer(self, name: str, session: Optional[Session] = None) -> Customer:
        """获取或创建顾客。
        
        根据姓名查找顾客，如果不存在则创建新顾客。
        
        Args:
            name: 顾客姓名（必填）。
            session: 数据库会话（可选）。如果为None，创建新会话并自动提交。
        
        Returns:
            顾客对象（已存在或新创建的）。
        """
        if session is None:
            with self.get_session() as sess:
                result = self._get_or_create_customer_in_session(name, sess)
                sess.commit()  # 自动提交，确保数据持久化
                customer_id = result.id
            # session关闭后，重新查询对象
            with self.get_session() as sess:
                return sess.query(Customer).filter(Customer.id == customer_id).first()
        else:
            return self._get_or_create_customer_in_session(name, session)
    
    def _get_or_create_customer_in_session(self, name: str, session: Session) -> Customer:
        """在指定会话中获取或创建顾客（内部方法）。
        
        Args:
            name: 顾客姓名。
            session: 数据库会话。
        
        Returns:
            顾客对象。
        """
        customer = session.query(Customer).filter(Customer.name == name).first()
        
        if not customer:
            customer = Customer(name=name)
            session.add(customer)
            session.flush()  # 使用 flush 而不是 commit
            session.refresh(customer)
        
        return customer
    
    # ========== ServiceType 相关 ==========
    
    def get_or_create_service_type(self, name: str, default_price: Optional[float] = None, 
                                   category: Optional[str] = None, 
                                   session: Optional[Session] = None) -> ServiceType:
        """获取或创建服务类型。
        
        根据名称查找服务类型，如果不存在则创建新服务类型。
        
        Args:
            name: 服务类型名称（必填）。
            default_price: 默认价格（可选）。
            category: 服务类别（可选）。
            session: 数据库会话（可选）。如果为None，创建新会话并自动提交。
        
        Returns:
            服务类型对象（已存在或新创建的）。
        """
        if session is None:
            with self.get_session() as sess:
                result = self._get_or_create_service_type_in_session(name, default_price, category, sess)
                sess.commit()  # 自动提交，确保数据持久化
                service_type_id = result.id
            # session关闭后，重新查询对象
            with self.get_session() as sess:
                return sess.query(ServiceType).filter(ServiceType.id == service_type_id).first()
        else:
            return self._get_or_create_service_type_in_session(name, default_price, category, session)
    
    def _get_or_create_service_type_in_session(self, name: str, default_price: Optional[float], 
                                               category: Optional[str], 
                                               session: Session) -> ServiceType:
        """在指定会话中获取或创建服务类型（内部方法）。
        
        Args:
            name: 服务类型名称。
            default_price: 默认价格。
            category: 服务类别。
            session: 数据库会话。
        
        Returns:
            服务类型对象。
        """
        service_type = session.query(ServiceType).filter(ServiceType.name == name).first()
        
        if not service_type:
            service_type = ServiceType(name=name, default_price=default_price, category=category)
            session.add(service_type)
            session.flush()  # 使用 flush 而不是 commit
            session.refresh(service_type)
        
        return service_type
    
    # ========== ServiceRecord 相关 ==========
    
    def save_service_record(self, record_data: Dict[str, Any], raw_message_id: int) -> int:
        """保存服务记录。
        
        保存服务记录，自动处理关联实体的创建（顾客、服务类型、员工等）。
        支持引流渠道的自动创建（向后兼容commission_to字段）。
        
        Args:
            record_data: 服务记录数据字典，包含以下键：
                - customer_name: 顾客姓名（必填）
                - service_or_product: 服务类型名称（必填）
                - date: 服务日期，格式YYYY-MM-DD或date对象（必填）
                - amount: 服务金额（必填）
                - commission: 提成金额（可选）
                - commission_to: 提成对象字符串（可选，向后兼容）
                - referral_channel_id: 引流渠道ID（可选，推荐使用）
                - net_amount: 净收入（可选，默认等于amount）
                - recorder_nickname: 记录员微信昵称（可选）
                - notes: 备注（可选）
                - confidence: 解析置信度（可选，默认0.5）
                - confirmed: 是否已确认（可选，默认False）
                - extra_data: 扩展数据字典（可选）
            raw_message_id: 原始消息ID。
        
        Returns:
            服务记录ID。
        
        Raises:
            ValueError: 如果日期格式无效或服务日期缺失。
        """
        with self.get_session() as session:
            # 获取或创建相关实体（使用当前会话）
            customer = self.get_or_create_customer(record_data.get("customer_name", ""), session=session)
            service_type = self.get_or_create_service_type(
                record_data.get("service_or_product", ""),
                record_data.get("default_price"),
                record_data.get("category"),
                session=session
            )
            
            recorder = None
            if record_data.get("recorder_nickname"):
                recorder = self.get_or_create_employee(
                    name=record_data.get("recorder_nickname"),
                    wechat_nickname=record_data.get("recorder_nickname"),
                    session=session
                )
            
            # 解析日期
            service_date = record_data.get("date")
            if isinstance(service_date, str):
                try:
                    service_date = datetime.strptime(service_date, "%Y-%m-%d").date()
                except ValueError:
                    logger.error(f"Invalid date format: {service_date}")
                    raise ValueError(f"Invalid date format: {service_date}, expected YYYY-MM-DD")
            elif service_date is None:
                raise ValueError("Service date is required")
            
            # 处理引流渠道
            referral_channel_id = None
            if record_data.get("referral_channel_id"):
                referral_channel_id = record_data.get("referral_channel_id")
            elif record_data.get("commission_to"):
                # 向后兼容：如果提供了commission_to，尝试查找或创建渠道
                referral_channel = self.get_or_create_referral_channel(
                    name=record_data.get("commission_to"),
                    channel_type="external",  # 默认为外部渠道
                    session=session
                )
                referral_channel_id = referral_channel.id if referral_channel else None
            
            record = ServiceRecord(
                customer_id=customer.id,
                service_type_id=service_type.id,
                service_date=service_date,
                amount=record_data.get("amount", 0),
                commission_amount=record_data.get("commission") or 0,
                commission_to=record_data.get("commission_to"),  # 保留向后兼容
                referral_channel_id=referral_channel_id,
                net_amount=record_data.get("net_amount") or record_data.get("amount", 0),
                membership_id=record_data.get("membership_id"),  # 会员卡ID
                notes=record_data.get("notes"),
                raw_message_id=raw_message_id,
                parse_confidence=record_data.get("confidence", 0.5),
                confirmed=record_data.get("confirmed", False),
                recorder_id=recorder.id if recorder else None,
                extra_data=record_data.get("extra_data", {})
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.id
    
    def get_records_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """获取指定日期的所有记录。
        
        查询指定日期的所有服务记录和商品销售记录，返回统一的字典格式。
        
        Args:
            target_date: 目标日期。
        
        Returns:
            记录列表，每个记录为字典，包含以下键：
            - type: 记录类型（"service"或"product_sale"）
            - id: 记录ID
            - customer_name: 顾客姓名
            - amount/total_amount: 金额
            - confirmed: 是否已确认
            对于服务记录还包含：
            - service_type: 服务类型名称
            - commission: 提成金额
            - commission_to: 提成对象
            - net_amount: 净收入
            对于商品销售还包含：
            - product_name: 商品名称
            - quantity: 数量
        """
        with self.get_session() as session:
            service_records = session.query(ServiceRecord).filter(
                ServiceRecord.service_date == target_date
            ).all()
            
            product_sales = session.query(ProductSale).filter(
                ProductSale.sale_date == target_date
            ).all()
            
            results = []
            for sr in service_records:
                results.append({
                    "type": "service",
                    "id": sr.id,
                    "customer_name": sr.customer.name if sr.customer else "",
                    "service_type": sr.service_type.name if sr.service_type else "",
                    "amount": float(sr.amount),
                    "commission": float(sr.commission_amount) if sr.commission_amount else None,
                    "commission_to": sr.commission_to,
                    "net_amount": float(sr.net_amount) if sr.net_amount else float(sr.amount),
                    "confirmed": sr.confirmed
                })
            
            for ps in product_sales:
                results.append({
                    "type": "product_sale",
                    "id": ps.id,
                    "product_name": ps.product.name if ps.product else "",
                    "customer_name": ps.customer.name if ps.customer else "",
                    "total_amount": float(ps.total_amount),
                    "quantity": ps.quantity,
                    "confirmed": ps.confirmed
                })
            
            return results
    
    # ========== Product 相关 ==========
    
    def get_or_create_product(self, name: str, category: Optional[str] = None, 
                              unit_price: Optional[float] = None, 
                              session: Optional[Session] = None) -> Product:
        """获取或创建商品。
        
        根据名称查找商品，如果不存在则创建新商品。
        
        Args:
            name: 商品名称（必填）。
            category: 商品类别（可选）。
            unit_price: 单价（可选）。
            session: 数据库会话（可选）。如果为None，创建新会话并自动提交。
        
        Returns:
            商品对象（已存在或新创建的）。
        """
        if session is None:
            with self.get_session() as sess:
                result = self._get_or_create_product_in_session(name, category, unit_price, sess)
                sess.commit()  # 自动提交，确保数据持久化
                product_id = result.id
            # session关闭后，重新查询对象
            with self.get_session() as sess:
                return sess.query(Product).filter(Product.id == product_id).first()
        else:
            return self._get_or_create_product_in_session(name, category, unit_price, session)
    
    def _get_or_create_product_in_session(self, name: str, category: Optional[str], 
                                          unit_price: Optional[float], 
                                          session: Session) -> Product:
        """在指定会话中获取或创建商品（内部方法）。
        
        Args:
            name: 商品名称。
            category: 商品类别。
            unit_price: 单价。
            session: 数据库会话。
        
        Returns:
            商品对象。
        """
        product = session.query(Product).filter(Product.name == name).first()
        
        if not product:
            product = Product(name=name, category=category, unit_price=unit_price)
            session.add(product)
            session.flush()
            session.refresh(product)
        
        return product
    
    def save_product_sale(self, sale_data: Dict[str, Any], raw_message_id: int) -> int:
        """保存商品销售记录。
        
        保存商品销售记录，自动处理关联实体的创建。
        
        Args:
            sale_data: 销售数据字典，包含以下键：
                - service_or_product: 商品名称（必填）
                - date: 销售日期，格式YYYY-MM-DD或date对象（必填）
                - amount: 总金额（必填）
                - quantity: 数量（可选，默认1）
                - unit_price: 单价（可选）
                - category: 商品类别（可选）
                - customer_name: 顾客姓名（可选）
                - recorder_nickname: 记录员微信昵称（可选）
                - notes: 备注（可选）
                - confidence: 解析置信度（可选，默认0.5）
                - confirmed: 是否已确认（可选，默认False）
            raw_message_id: 原始消息ID。
        
        Returns:
            销售记录ID。
        
        Raises:
            ValueError: 如果日期格式无效或销售日期缺失。
        """
        with self.get_session() as session:
            product = self.get_or_create_product(
                sale_data.get("service_or_product", ""),
                sale_data.get("category"),
                sale_data.get("unit_price"),
                session=session
            )
            
            customer = None
            if sale_data.get("customer_name"):
                customer = self.get_or_create_customer(sale_data.get("customer_name"), session=session)
            
            recorder = None
            if sale_data.get("recorder_nickname"):
                recorder = self.get_or_create_employee(
                    name=sale_data.get("recorder_nickname"),
                    wechat_nickname=sale_data.get("recorder_nickname"),
                    session=session
                )
            
            sale_date = sale_data.get("date")
            if isinstance(sale_date, str):
                try:
                    sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
                except ValueError:
                    logger.error(f"Invalid date format: {sale_date}")
                    raise ValueError(f"Invalid date format: {sale_date}, expected YYYY-MM-DD")
            elif sale_date is None:
                raise ValueError("Sale date is required")
            
            sale = ProductSale(
                product_id=product.id,
                customer_id=customer.id if customer else None,
                recorder_id=recorder.id if recorder else None,
                quantity=sale_data.get("quantity", 1),
                unit_price=sale_data.get("unit_price"),
                total_amount=sale_data.get("amount", 0),
                sale_date=sale_date,
                notes=sale_data.get("notes"),
                raw_message_id=raw_message_id,
                parse_confidence=sale_data.get("confidence", 0.5),
                confirmed=sale_data.get("confirmed", False)
            )
            
            session.add(sale)
            session.commit()
            session.refresh(sale)
            return sale.id
    
    # ========== Membership 相关 ==========
    
    def save_membership(self, membership_data: Dict[str, Any], raw_message_id: int) -> int:
        """保存会员卡记录。
        
        保存会员卡开卡记录，自动处理顾客的创建。
        
        Args:
            membership_data: 会员卡数据字典，包含以下键：
                - customer_name: 顾客姓名（必填）
                - date: 开卡日期，格式YYYY-MM-DD或date对象（必填）
                - amount: 充值金额（必填，同时作为total_amount和balance）
                - card_type: 卡类型（可选，默认"理疗卡"）
            raw_message_id: 原始消息ID。
        
        Returns:
            会员卡记录ID。
        
        Raises:
            ValueError: 如果日期格式无效或开卡日期缺失。
        """
        with self.get_session() as session:
            customer = self.get_or_create_customer(membership_data.get("customer_name", ""), session=session)
            
            opened_at = membership_data.get("date")
            if isinstance(opened_at, str):
                try:
                    opened_at = datetime.strptime(opened_at, "%Y-%m-%d").date()
                except ValueError:
                    logger.error(f"Invalid date format: {opened_at}")
                    raise ValueError(f"Invalid date format: {opened_at}, expected YYYY-MM-DD")
            elif opened_at is None:
                raise ValueError("Membership opened_at date is required")
            
            membership = Membership(
                customer_id=customer.id,
                card_type=membership_data.get("card_type", "理疗卡"),
                total_amount=membership_data.get("amount", 0),
                balance=membership_data.get("amount", 0),
                opened_at=opened_at
            )
            
            session.add(membership)
            session.commit()
            session.refresh(membership)
            return membership.id
    
    # ========== ReferralChannel 相关 ==========
    
    def get_or_create_referral_channel(self, name: str, channel_type: str = "external",
                                      contact_info: Optional[str] = None,
                                      commission_rate: Optional[float] = None,
                                      session: Optional[Session] = None) -> ReferralChannel:
        """获取或创建引流渠道。
        
        根据名称查找引流渠道，如果不存在则创建新渠道。
        
        Args:
            name: 渠道名称（必填，如：美团、大众点评、李哥）。
            channel_type: 渠道类型，可选值：internal/external/platform，默认external。
            contact_info: 联系方式（可选）。
            commission_rate: 默认提成率，范围0-100（可选）。
            session: 数据库会话（可选）。如果为None，创建新会话并自动提交。
        
        Returns:
            引流渠道对象（已存在或新创建的）。
        """
        if session is None:
            with self.get_session() as sess:
                result = self._get_or_create_referral_channel_in_session(
                    name, channel_type, contact_info, commission_rate, sess
                )
                sess.commit()  # 自动提交，确保数据持久化
                # 在session关闭前获取所有需要的属性值
                channel_id = result.id
                channel_name = result.name
                channel_type_val = result.channel_type
                # 重新查询以确保对象可访问
                sess.refresh(result)
            # session关闭后，重新查询对象
            with self.get_session() as sess:
                return sess.query(ReferralChannel).filter(ReferralChannel.id == channel_id).first()
        else:
            return self._get_or_create_referral_channel_in_session(
                name, channel_type, contact_info, commission_rate, session
            )
    
    def _get_or_create_referral_channel_in_session(self, name: str, channel_type: str,
                                                   contact_info: Optional[str],
                                                   commission_rate: Optional[float],
                                                   session: Session) -> ReferralChannel:
        """在指定会话中获取或创建引流渠道（内部方法）。
        
        Args:
            name: 渠道名称。
            channel_type: 渠道类型。
            contact_info: 联系方式。
            commission_rate: 默认提成率。
            session: 数据库会话。
        
        Returns:
            引流渠道对象。
        """
        channel = session.query(ReferralChannel).filter(
            ReferralChannel.name == name
        ).first()
        
        if not channel:
            channel = ReferralChannel(
                name=name,
                channel_type=channel_type,
                contact_info=contact_info,
                commission_rate=commission_rate
            )
            session.add(channel)
            session.flush()
            session.refresh(channel)
        
        return channel
    
    def get_referral_channels(self, channel_type: Optional[str] = None, 
                             is_active: Optional[bool] = True) -> List[ReferralChannel]:
        """获取引流渠道列表。
        
        Args:
            channel_type: 渠道类型过滤（可选）。如果提供，只返回该类型的渠道。
            is_active: 是否只返回激活的渠道（可选）。如果为None，则不过滤。
        
        Returns:
            引流渠道对象列表。
        """
        with self.get_session() as session:
            query = session.query(ReferralChannel)
            if channel_type:
                query = query.filter(ReferralChannel.channel_type == channel_type)
            if is_active is not None:
                query = query.filter(ReferralChannel.is_active == is_active)
            return query.all()
    
    # ========== PluginData 相关 ==========
    
    def save_plugin_data(self, plugin_name: str, entity_type: str, entity_id: int,
                        data_key: str, data_value: Any) -> int:
        """保存插件数据。
        
        保存或更新插件数据。如果数据已存在则更新，否则创建新记录。
        
        Args:
            plugin_name: 插件标识（必填）。
            entity_type: 实体类型（必填，如：employee/customer/product）。
            entity_id: 实体ID（必填）。
            data_key: 数据键（必填）。
            data_value: 数据值（必填，可以是任意JSON可序列化的对象）。
        
        Returns:
            插件数据记录ID。
        """
        with self.get_session() as session:
            # 检查是否已存在
            existing = session.query(PluginData).filter(
                PluginData.plugin_name == plugin_name,
                PluginData.entity_type == entity_type,
                PluginData.entity_id == entity_id,
                PluginData.data_key == data_key
            ).first()
            
            if existing:
                existing.data_value = data_value
                existing.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                return existing.id
            else:
                plugin_data = PluginData(
                    plugin_name=plugin_name,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    data_key=data_key,
                    data_value=data_value
                )
                session.add(plugin_data)
                session.commit()
                session.refresh(plugin_data)
                return plugin_data.id
    
    def get_plugin_data(self, plugin_name: str, entity_type: str, entity_id: int,
                       data_key: Optional[str] = None) -> Union[Dict[str, Any], Any, None]:
        """获取插件数据。
        
        Args:
            plugin_name: 插件标识（必填）。
            entity_type: 实体类型（必填）。
            entity_id: 实体ID（必填）。
            data_key: 数据键（可选）。如果提供，返回单个值；否则返回所有键值对的字典。
        
        Returns:
            如果data_key提供，返回对应的值（可能为None）；否则返回字典。
        """
        with self.get_session() as session:
            query = session.query(PluginData).filter(
                PluginData.plugin_name == plugin_name,
                PluginData.entity_type == entity_type,
                PluginData.entity_id == entity_id
            )
            if data_key:
                query = query.filter(PluginData.data_key == data_key)
            
            results = query.all()
            if data_key:
                return results[0].data_value if results else None
            else:
                return {item.data_key: item.data_value for item in results}
    
    def delete_plugin_data(self, plugin_name: str, entity_type: str, entity_id: int,
                          data_key: Optional[str] = None) -> None:
        """删除插件数据。
        
        Args:
            plugin_name: 插件标识（必填）。
            entity_type: 实体类型（必填）。
            entity_id: 实体ID（必填）。
            data_key: 数据键（可选）。如果提供，只删除该键；否则删除所有数据。
        """
        with self.get_session() as session:
            query = session.query(PluginData).filter(
                PluginData.plugin_name == plugin_name,
                PluginData.entity_type == entity_type,
                PluginData.entity_id == entity_id
            )
            if data_key:
                query = query.filter(PluginData.data_key == data_key)
            
            query.delete()
            session.commit()
    
    # ========== DailySummary 相关 ==========
    
    def save_daily_summary(self, summary_date: date, summary_data: Dict[str, Any]) -> int:
        """保存每日汇总。
        
        保存或更新指定日期的汇总数据。如果该日期的汇总已存在则更新，否则创建新记录。
        
        Args:
            summary_date: 汇总日期（必填）。
            summary_data: 汇总数据字典，包含以下可选键：
                - total_service_revenue: 服务总收入
                - total_product_revenue: 商品总收入
                - total_commissions: 总提成支出
                - net_revenue: 净收入
                - service_count: 服务记录数
                - product_sale_count: 商品销售记录数
                - new_members: 新增会员数
                - membership_revenue: 会员卡收入
                - summary_text: 汇总文本
                - confirmed: 是否已确认
        
        Returns:
            汇总记录ID。
        """
        with self.get_session() as session:
            # 检查是否已存在
            existing = session.query(DailySummary).filter(
                DailySummary.summary_date == summary_date
            ).first()
            
            if existing:
                # 更新现有记录
                for key, value in summary_data.items():
                    setattr(existing, key, value)
                session.commit()
                session.refresh(existing)
                return existing.id
            else:
                # 创建新记录
                summary = DailySummary(summary_date=summary_date, **summary_data)
                session.add(summary)
                session.commit()
                session.refresh(summary)
                return summary.id

