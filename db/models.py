"""SQLAlchemy ORM 模型定义。

本模块定义了所有数据库表的ORM模型，包括：
- 员工、顾客、会员等基础实体
- 服务记录、商品销售等业务记录
- 库存、消息、汇总等辅助数据
- 扩展机制：引流渠道、插件数据等
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, 
    DECIMAL, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, date

# SQLAlchemy declarative base，所有模型都继承自此类
# 设置 __allow_unmapped__ = True 以兼容 SQLAlchemy 2.0 的类型注解要求
Base = declarative_base()

# 为Base类添加__allow_unmapped__属性，允许使用旧式类型注解
Base.__allow_unmapped__ = True


class Employee(Base):
    """员工表模型。
    
    存储员工的基本信息，包括姓名、微信信息、角色、提成率等。
    支持通过extra_data字段扩展存储部门、技能等级等自定义属性。
    
    Attributes:
        id: 主键，自增整数。
        name: 员工姓名，必填，最大长度50字符。
        wechat_nickname: 微信昵称，可选，最大长度100字符。
        wechat_alias: 微信别名，可选，最大长度100字符。
        role: 员工角色，可选值：staff（普通员工）/ manager（管理员）/ bot（机器人），默认staff。
        commission_rate: 提成率，DECIMAL(5,2)，范围0-100，默认0。
        is_active: 是否激活，布尔值，默认True。
        extra_data: JSON扩展字段，用于存储部门、技能等级等自定义属性，默认空字典。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        service_records_as_employee: 作为服务员工的服务记录列表。
        service_records_as_recorder: 作为记录员的服务记录列表。
        product_sales: 作为记录员的商品销售记录列表。
    """
    __tablename__ = "employees"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(50), nullable=False)
    wechat_nickname: Optional[str] = Column(String(100))
    wechat_alias: Optional[str] = Column(String(100))
    role: str = Column(String(20), default="staff")  # staff / manager / bot
    commission_rate: float = Column(DECIMAL(5, 2), default=0)
    is_active: bool = Column(Boolean, default=True)
    extra_data: Dict[str, Any] = Column(JSON, default={})  # 扩展数据：部门、技能等级等
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service_records_as_employee: List["ServiceRecord"] = relationship(
        "ServiceRecord", 
        foreign_keys="ServiceRecord.employee_id", 
        back_populates="employee"
    )
    service_records_as_recorder: List["ServiceRecord"] = relationship(
        "ServiceRecord", 
        foreign_keys="ServiceRecord.recorder_id", 
        back_populates="recorder"
    )
    product_sales: List["ProductSale"] = relationship("ProductSale", back_populates="recorder")


class Customer(Base):
    """顾客/会员表模型。
    
    存储顾客的基本信息，包括姓名、电话、备注等。
    支持通过extra_data字段扩展存储VIP等级、来源渠道、标签等自定义属性。
    
    Attributes:
        id: 主键，自增整数。
        name: 顾客姓名，必填，最大长度50字符。
        phone: 联系电话，可选，最大长度20字符。
        notes: 备注信息，可选，文本类型。
        extra_data: JSON扩展字段，用于存储VIP等级、来源渠道、标签等自定义属性，默认空字典。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        memberships: 该顾客的会员卡列表。
        service_records: 该顾客的服务记录列表。
        product_sales: 该顾客的商品购买记录列表。
    """
    __tablename__ = "customers"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(50), nullable=False)
    phone: Optional[str] = Column(String(20))
    notes: Optional[str] = Column(Text)
    extra_data: Dict[str, Any] = Column(JSON, default={})  # 扩展数据：VIP等级、来源渠道、标签等
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    memberships: List["Membership"] = relationship("Membership", back_populates="customer")
    service_records: List["ServiceRecord"] = relationship("ServiceRecord", back_populates="customer")
    product_sales: List["ProductSale"] = relationship("ProductSale", back_populates="customer")


class Membership(Base):
    """会员卡表模型。
    
    存储会员卡信息，包括卡类型、金额、余额、剩余次数、有效期、积分等。
    支持通过extra_data字段扩展存储权益配置等自定义属性。
    
    Attributes:
        id: 主键，自增整数。
        customer_id: 顾客ID，外键关联customers表，必填。
        card_type: 卡类型，可选，最大长度50字符（如：理疗卡、头疗卡）。
        total_amount: 总金额，DECIMAL(10,2)，必填。
        balance: 余额，DECIMAL(10,2)，必填。
        remaining_sessions: 剩余次数，可选整数。
        opened_at: 开卡日期，必填。
        expires_at: 到期日期，可选。
        points: 积分，整数，默认0。
        is_active: 是否激活，布尔值，默认True。
        extra_data: JSON扩展字段，用于存储权益配置等自定义属性，默认空字典。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        customer: 关联的顾客对象。
        service_records: 使用该会员卡的服务记录列表。
    """
    __tablename__ = "memberships"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    customer_id: int = Column(Integer, ForeignKey("customers.id"), nullable=False)
    card_type: Optional[str] = Column(String(50))
    total_amount: float = Column(DECIMAL(10, 2), nullable=False)
    balance: float = Column(DECIMAL(10, 2), nullable=False)
    remaining_sessions: Optional[int] = Column(Integer)
    opened_at: date = Column(Date, nullable=False)
    expires_at: Optional[date] = Column(Date)  # 到期日期
    points: int = Column(Integer, default=0)  # 积分
    is_active: bool = Column(Boolean, default=True)
    extra_data: Dict[str, Any] = Column(JSON, default={})  # 扩展数据：权益配置等
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer: "Customer" = relationship("Customer", back_populates="memberships")
    service_records: List["ServiceRecord"] = relationship("ServiceRecord", back_populates="membership")


class ServiceType(Base):
    """服务类型字典表模型。
    
    存储服务类型的配置信息，包括服务名称、默认价格、类别等。
    作为服务记录的字典表使用。
    
    Attributes:
        id: 主键，自增整数。
        name: 服务类型名称，必填，唯一，最大长度50字符（如：头疗、理疗、按摩）。
        default_price: 默认价格，DECIMAL(10,2)，可选。
        category: 服务类别，可选，最大长度50字符（如：therapy、foot_bath）。
        
    Relationships:
        service_records: 使用该服务类型的服务记录列表。
    """
    __tablename__ = "service_types"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(50), nullable=False, unique=True)
    default_price: Optional[float] = Column(DECIMAL(10, 2))
    category: Optional[str] = Column(String(50))
    
    # Relationships
    service_records: List["ServiceRecord"] = relationship("ServiceRecord", back_populates="service_type")


class ReferralChannel(Base):
    """引流渠道表模型。
    
    存储外部引流渠道信息，支持管理美团、大众点评、合作方等引流渠道的提成配置。
    用于区分内部员工提成和外部引流提成，实现精准的渠道效果统计。
    
    Attributes:
        id: 主键，自增整数。
        name: 渠道名称，必填，最大长度100字符（如：美团、大众点评、李哥）。
        channel_type: 渠道类型，必填，可选值：internal（内部员工）/ external（外部合作）/ platform（平台），最大长度20字符。
        contact_info: 联系方式，可选，最大长度200字符。
        commission_rate: 默认提成率，DECIMAL(5,2)，范围0-100，可选。
        commission_type: 提成类型，可选值：percentage（百分比）/ fixed（固定金额），默认percentage，最大长度20字符。
        is_active: 是否激活，布尔值，默认True。
        notes: 备注信息，可选，文本类型。
        extra_data: JSON扩展字段，用于存储渠道扩展信息，默认空字典。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        service_records: 关联该渠道的服务记录列表。
    """
    __tablename__ = "referral_channels"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(100), nullable=False)  # 渠道名称：美团、大众点评、李哥等
    channel_type: str = Column(String(20), nullable=False)  # internal/external/platform
    contact_info: Optional[str] = Column(String(200))  # 联系方式
    commission_rate: Optional[float] = Column(DECIMAL(5, 2))  # 默认提成率（百分比）
    commission_type: str = Column(String(20), default="percentage")  # percentage/fixed
    is_active: bool = Column(Boolean, default=True)
    notes: Optional[str] = Column(Text)
    extra_data: Dict[str, Any] = Column(JSON, default={})  # 扩展数据
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service_records: List["ServiceRecord"] = relationship("ServiceRecord", back_populates="referral_channel")


class ServiceRecord(Base):
    """服务记录表模型（核心业务表）。
    
    存储服务记录的核心信息，包括顾客、员工、服务类型、金额、提成等。
    支持通过referral_channel_id关联引流渠道，实现精准的提成管理。
    支持通过extra_data字段扩展存储预约ID、服务时长等自定义属性。
    
    Attributes:
        id: 主键，自增整数。
        customer_id: 顾客ID，外键关联customers表，可选。
        employee_id: 服务员工ID，外键关联employees表，可选。
        recorder_id: 记录员ID，外键关联employees表，可选。
        service_type_id: 服务类型ID，外键关联service_types表，可选。
        service_date: 服务日期，必填。
        amount: 服务金额，DECIMAL(10,2)，必填。
        commission_amount: 提成金额，DECIMAL(10,2)，默认0。
        commission_to: 提成对象（字符串），保留用于向后兼容，推荐使用referral_channel_id，最大长度50字符。
        referral_channel_id: 引流渠道ID，外键关联referral_channels表，可选。
        net_amount: 净收入（金额-提成），DECIMAL(10,2)，可选。
        membership_id: 使用的会员卡ID，外键关联memberships表，可选。
        notes: 备注信息，可选，文本类型。
        raw_message_id: 原始消息ID，外键关联raw_messages表，可选。
        parse_confidence: 解析置信度，DECIMAL(3,2)，范围0-1，可选。
        confirmed: 是否已确认，布尔值，默认False。
        confirmed_at: 确认时间，可选。
        extra_data: JSON扩展字段，用于存储预约ID、服务时长等自定义属性，默认空字典。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        customer: 关联的顾客对象。
        employee: 关联的服务员工对象。
        recorder: 关联的记录员对象。
        service_type: 关联的服务类型对象。
        membership: 关联的会员卡对象。
        referral_channel: 关联的引流渠道对象。
        raw_message: 关联的原始消息对象。
    """
    __tablename__ = "service_records"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    customer_id: Optional[int] = Column(Integer, ForeignKey("customers.id"))
    employee_id: Optional[int] = Column(Integer, ForeignKey("employees.id"))
    recorder_id: Optional[int] = Column(Integer, ForeignKey("employees.id"))
    service_type_id: Optional[int] = Column(Integer, ForeignKey("service_types.id"))
    service_date: date = Column(Date, nullable=False)
    amount: float = Column(DECIMAL(10, 2), nullable=False)
    commission_amount: float = Column(DECIMAL(10, 2), default=0)
    commission_to: Optional[str] = Column(String(50))  # 保留用于向后兼容，推荐使用referral_channel_id
    referral_channel_id: Optional[int] = Column(Integer, ForeignKey("referral_channels.id"))  # 引流渠道ID
    net_amount: Optional[float] = Column(DECIMAL(10, 2))
    membership_id: Optional[int] = Column(Integer, ForeignKey("memberships.id"))
    notes: Optional[str] = Column(Text)
    raw_message_id: Optional[int] = Column(Integer, ForeignKey("raw_messages.id"))
    parse_confidence: Optional[float] = Column(DECIMAL(3, 2))
    confirmed: bool = Column(Boolean, default=False)
    confirmed_at: Optional[datetime] = Column(DateTime)
    extra_data: Dict[str, Any] = Column(JSON, default={})  # 扩展数据
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer: Optional["Customer"] = relationship("Customer", back_populates="service_records")
    employee: Optional["Employee"] = relationship("Employee", foreign_keys=[employee_id], back_populates="service_records_as_employee")
    recorder: Optional["Employee"] = relationship("Employee", foreign_keys=[recorder_id], back_populates="service_records_as_recorder")
    service_type: Optional["ServiceType"] = relationship("ServiceType", back_populates="service_records")
    membership: Optional["Membership"] = relationship("Membership", back_populates="service_records")
    referral_channel: Optional["ReferralChannel"] = relationship("ReferralChannel", back_populates="service_records")
    raw_message: Optional["RawMessage"] = relationship("RawMessage", back_populates="service_records")


class Product(Base):
    """商品表模型。
    
    存储商品的基本信息，包括名称、类别、单价、库存数量等。
    支持通过extra_data字段扩展存储批次信息、供应商等自定义属性。
    
    Attributes:
        id: 主键，自增整数。
        name: 商品名称，必填，最大长度100字符。
        category: 商品类别，可选，最大长度50字符（如：supplement/medicine/accessory）。
        unit_price: 单价，DECIMAL(10,2)，可选。
        stock_quantity: 库存数量，整数，默认0。
        low_stock_threshold: 低库存阈值，整数，默认10。
        extra_data: JSON扩展字段，用于存储批次信息、供应商等自定义属性，默认空字典。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        sales: 该商品的销售记录列表。
        inventory_logs: 该商品的库存变动记录列表。
    """
    __tablename__ = "products"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(100), nullable=False)
    category: Optional[str] = Column(String(50))  # supplement / medicine / accessory
    unit_price: Optional[float] = Column(DECIMAL(10, 2))
    stock_quantity: int = Column(Integer, default=0)
    low_stock_threshold: int = Column(Integer, default=10)
    extra_data: Dict[str, Any] = Column(JSON, default={})  # 扩展数据：批次信息、供应商等
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sales: List["ProductSale"] = relationship("ProductSale", back_populates="product")
    inventory_logs: List["InventoryLog"] = relationship("InventoryLog", back_populates="product")


class ProductSale(Base):
    """商品销售记录表模型。
    
    存储商品销售记录，包括商品、顾客、数量、金额等信息。
    
    Attributes:
        id: 主键，自增整数。
        product_id: 商品ID，外键关联products表，可选。
        customer_id: 顾客ID，外键关联customers表，可选。
        recorder_id: 记录员ID，外键关联employees表，可选。
        quantity: 销售数量，整数，默认1。
        unit_price: 单价，DECIMAL(10,2)，可选。
        total_amount: 总金额，DECIMAL(10,2)，必填。
        sale_date: 销售日期，必填。
        notes: 备注信息，可选，文本类型。
        raw_message_id: 原始消息ID，外键关联raw_messages表，可选。
        parse_confidence: 解析置信度，DECIMAL(3,2)，范围0-1，可选。
        confirmed: 是否已确认，布尔值，默认False。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        product: 关联的商品对象。
        customer: 关联的顾客对象。
        recorder: 关联的记录员对象。
        raw_message: 关联的原始消息对象。
    """
    __tablename__ = "product_sales"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    product_id: Optional[int] = Column(Integer, ForeignKey("products.id"))
    customer_id: Optional[int] = Column(Integer, ForeignKey("customers.id"))
    recorder_id: Optional[int] = Column(Integer, ForeignKey("employees.id"))
    quantity: int = Column(Integer, default=1)
    unit_price: Optional[float] = Column(DECIMAL(10, 2))
    total_amount: float = Column(DECIMAL(10, 2), nullable=False)
    sale_date: date = Column(Date, nullable=False)
    notes: Optional[str] = Column(Text)
    raw_message_id: Optional[int] = Column(Integer, ForeignKey("raw_messages.id"))
    parse_confidence: Optional[float] = Column(DECIMAL(3, 2))
    confirmed: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product: Optional["Product"] = relationship("Product", back_populates="sales")
    customer: Optional["Customer"] = relationship("Customer", back_populates="product_sales")
    recorder: Optional["Employee"] = relationship("Employee", back_populates="product_sales")
    raw_message: Optional["RawMessage"] = relationship("RawMessage", back_populates="product_sales")


class InventoryLog(Base):
    """库存变动记录表模型。
    
    记录库存的变动情况，包括销售、入库、调整等操作。
    
    Attributes:
        id: 主键，自增整数。
        product_id: 商品ID，外键关联products表，可选。
        change_type: 变动类型，必填，可选值：sale（销售）/ restock（入库）/ adjustment（调整），最大长度20字符。
        quantity_change: 数量变动，整数，必填，正数表示入库，负数表示出库。
        quantity_after: 变动后库存数量，整数，必填。
        reference_id: 关联记录ID，可选，通常关联product_sales.id或其他业务记录ID。
        notes: 备注信息，可选，文本类型。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        product: 关联的商品对象。
    """
    __tablename__ = "inventory_logs"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    product_id: Optional[int] = Column(Integer, ForeignKey("products.id"))
    change_type: str = Column(String(20), nullable=False)  # sale / restock / adjustment
    quantity_change: int = Column(Integer, nullable=False)  # 正数入库，负数出库
    quantity_after: int = Column(Integer, nullable=False)
    reference_id: Optional[int] = Column(Integer)  # 关联 product_sales.id 或其他
    notes: Optional[str] = Column(Text)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product: Optional["Product"] = relationship("Product", back_populates="inventory_logs")


class RawMessage(Base):
    """原始消息存档表模型。
    
    存储从微信群聊中接收到的原始消息，用于追溯和审计。
    记录消息的解析状态和结果，支持消息去重。
    
    Attributes:
        id: 主键，自增整数。
        wechat_msg_id: 微信消息ID，唯一，最大长度100字符。
        sender_nickname: 发送者昵称，必填，最大长度100字符。
        sender_wechat_id: 发送者微信ID，可选，最大长度100字符。
        content: 消息内容，必填，文本类型。
        msg_type: 消息类型，可选，默认"text"，最大长度20字符。
        group_id: 群组ID，可选，最大长度100字符。
        timestamp: 消息时间戳，必填。
        is_at_bot: 是否@机器人，布尔值，默认False。
        is_business: 是否为业务消息，布尔值，可选。
        parse_status: 解析状态，可选值：pending（待解析）/ parsed（已解析）/ failed（解析失败）/ ignored（已忽略），默认pending，最大长度20字符。
        parse_result: 解析结果，JSON类型，可选。
        parse_error: 解析错误信息，文本类型，可选。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        service_records: 从该消息解析出的服务记录列表。
        product_sales: 从该消息解析出的商品销售记录列表。
        corrections: 从该消息产生的修正记录列表。
    """
    __tablename__ = "raw_messages"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    wechat_msg_id: Optional[str] = Column(String(100), unique=True)
    sender_nickname: str = Column(String(100), nullable=False)
    sender_wechat_id: Optional[str] = Column(String(100))
    content: str = Column(Text, nullable=False)
    msg_type: str = Column(String(20), default="text")
    group_id: Optional[str] = Column(String(100))
    timestamp: datetime = Column(DateTime, nullable=False)
    is_at_bot: bool = Column(Boolean, default=False)
    is_business: Optional[bool] = Column(Boolean)
    parse_status: str = Column(String(20), default="pending")  # pending / parsed / failed / ignored
    parse_result: Optional[Dict[str, Any]] = Column(JSON)
    parse_error: Optional[str] = Column(Text)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service_records: List["ServiceRecord"] = relationship("ServiceRecord", back_populates="raw_message")
    product_sales: List["ProductSale"] = relationship("ProductSale", back_populates="raw_message")
    corrections: List["Correction"] = relationship("Correction", back_populates="raw_message")


class Correction(Base):
    """修正记录表模型。
    
    记录对已保存业务记录的修正操作，用于审计和追溯。
    
    Attributes:
        id: 主键，自增整数。
        original_record_type: 原始记录类型，可选值：service_records / product_sales，最大长度50字符。
        original_record_id: 原始记录ID，可选整数。
        correction_type: 修正类型，可选值：date_change（日期修改）/ amount_change（金额修改）/ delete（删除），最大长度20字符。
        old_value: 旧值，JSON类型，可选。
        new_value: 新值，JSON类型，可选。
        reason: 修正原因，文本类型，可选。
        raw_message_id: 原始消息ID，外键关联raw_messages表，可选。
        created_at: 创建时间，自动设置为当前UTC时间。
        
    Relationships:
        raw_message: 关联的原始消息对象。
    """
    __tablename__ = "corrections"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    original_record_type: Optional[str] = Column(String(50))  # service_records / product_sales
    original_record_id: Optional[int] = Column(Integer)
    correction_type: Optional[str] = Column(String(20))  # date_change / amount_change / delete
    old_value: Optional[Dict[str, Any]] = Column(JSON)
    new_value: Optional[Dict[str, Any]] = Column(JSON)
    reason: Optional[str] = Column(Text)
    raw_message_id: Optional[int] = Column(Integer, ForeignKey("raw_messages.id"))
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    raw_message: Optional["RawMessage"] = relationship("RawMessage", back_populates="corrections")


class DailySummary(Base):
    """每日汇总快照表模型。
    
    存储每日的业务汇总数据，用于快速查询和报表生成。
    每个日期只有一条记录（通过unique约束保证）。
    
    Attributes:
        id: 主键，自增整数。
        summary_date: 汇总日期，必填，唯一。
        total_service_revenue: 服务总收入，DECIMAL(10,2)，可选。
        total_product_revenue: 商品总收入，DECIMAL(10,2)，可选。
        total_commissions: 总提成支出，DECIMAL(10,2)，可选。
        net_revenue: 净收入，DECIMAL(10,2)，可选。
        service_count: 服务记录数，整数，可选。
        product_sale_count: 商品销售记录数，整数，可选。
        new_members: 新增会员数，整数，可选。
        membership_revenue: 会员卡收入，DECIMAL(10,2)，可选。
        summary_text: 汇总文本，文本类型，可选。
        confirmed: 是否已确认，布尔值，默认False。
        created_at: 创建时间，自动设置为当前UTC时间。
    """
    __tablename__ = "daily_summaries"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    summary_date: date = Column(Date, nullable=False, unique=True)
    total_service_revenue: Optional[float] = Column(DECIMAL(10, 2))
    total_product_revenue: Optional[float] = Column(DECIMAL(10, 2))
    total_commissions: Optional[float] = Column(DECIMAL(10, 2))
    net_revenue: Optional[float] = Column(DECIMAL(10, 2))
    service_count: Optional[int] = Column(Integer)
    product_sale_count: Optional[int] = Column(Integer)
    new_members: Optional[int] = Column(Integer)
    membership_revenue: Optional[float] = Column(DECIMAL(10, 2))
    summary_text: Optional[str] = Column(Text)
    confirmed: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)


class PluginData(Base):
    """插件数据表模型。
    
    支持完全自定义的扩展数据存储，用于插件化的业务扩展。
    通过(plugin_name, entity_type, entity_id, data_key)唯一约束保证数据唯一性。
    
    Attributes:
        id: 主键，自增整数。
        plugin_name: 插件标识，必填，最大长度50字符。
        entity_type: 实体类型，必填，可选值：employee/customer/product/service_record等，最大长度50字符。
        entity_id: 关联实体ID，必填整数。
        data_key: 数据键，必填，最大长度100字符。
        data_value: 数据值，JSON类型，可选。
        created_at: 创建时间，自动设置为当前UTC时间。
        updated_at: 更新时间，自动设置为当前UTC时间，更新时自动更新。
        
    Table Args:
        UniqueConstraint: (plugin_name, entity_type, entity_id, data_key)唯一约束。
    """
    __tablename__ = "plugin_data"
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    plugin_name: str = Column(String(50), nullable=False)  # 插件标识
    entity_type: str = Column(String(50), nullable=False)  # employee/customer/product/service_record等
    entity_id: int = Column(Integer, nullable=False)  # 关联实体ID
    data_key: str = Column(String(100), nullable=False)  # 数据键
    data_value: Optional[Dict[str, Any]] = Column(JSON)  # 数据值
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('plugin_name', 'entity_type', 'entity_id', 'data_key', 
                        name='uq_plugin_data'),
    )

