"""数据库管理器 —— 统一门面（Facade）。

DatabaseManager 是 database 模块的统一入口，组合了所有子仓库，
提供两套 API：

1. **子仓库访问**（细粒度）：
   通过 ``db.staff``、``db.customers`` 等属性直接访问子仓库，
   返回 ORM 对象，适合需要精细控制的场景。

2. **便捷方法**（粗粒度）：
   提供扁平化的方法（如 ``save_service_record()``、``get_daily_records()``），
   返回字典/基本类型，适合上层业务代码和 API 调用。

设计目标：
- 适应多种商业模式的共性需求（理发店、健身房、理疗馆、餐厅等）
- 模块相对独立，可单独使用
- 便捷方法覆盖高频操作，低频操作通过子仓库访问
"""
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import DatabaseConnection
from .entity_repos import (
    StaffRepository, CustomerRepository,
    ServiceTypeRepository, ProductRepository, ChannelRepository
)
from .business_repos import (
    ServiceRecordRepository, ProductSaleRepository, MembershipRepository
)
from .system_repos import (
    MessageRepository, SummaryRepository, PluginRepository
)
from .models import Employee, Membership


class DatabaseManager:
    """数据库管理器 —— 统一门面。

    组合了所有子仓库，提供统一的数据库访问接口。
    支持 SQLite（同步）和 PostgreSQL（异步）数据库引擎。

    Attributes:
        conn: 数据库连接管理器。
        staff: 员工仓库。
        customers: 顾客仓库。
        service_types: 服务类型仓库。
        products: 商品仓库。
        channels: 引流渠道仓库。
        service_records: 服务记录仓库。
        product_sales: 商品销售仓库。
        memberships: 会员卡仓库。
        messages: 消息仓库。
        summaries: 汇总仓库。
        plugins: 插件数据仓库。

    Example::

        db = DatabaseManager("sqlite:///data/store.db")
        db.create_tables()

        # 通过子仓库访问（返回 ORM 对象）
        employee = db.staff.get_or_create("张三")

        # 通过便捷方法访问（返回字典）
        records = db.get_daily_records("2024-01-28")
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        """初始化数据库管理器。

        Args:
            database_url: 数据库连接URL。如果为None则使用settings配置。
                        支持 ``sqlite:///`` 和 ``postgresql://`` 格式。
        """
        # 基础设施层
        self.conn = DatabaseConnection(database_url)

        # 实体仓库
        self.staff = StaffRepository(self.conn)
        self.customers = CustomerRepository(self.conn)
        self.service_types = ServiceTypeRepository(self.conn)
        self.products = ProductRepository(self.conn)
        self.channels = ChannelRepository(self.conn)

        # 业务记录仓库
        self.service_records = ServiceRecordRepository(
            self.conn, self.staff, self.customers,
            self.service_types, self.channels
        )
        self.product_sales = ProductSaleRepository(
            self.conn, self.staff, self.customers, self.products
        )
        self.memberships = MembershipRepository(
            self.conn, self.customers
        )

        # 系统数据仓库
        self.messages = MessageRepository(self.conn)
        self.summaries = SummaryRepository(self.conn)
        self.plugins = PluginRepository(self.conn)

    # ================================================================
    # 基础设施方法
    # ================================================================

    def create_tables(self) -> None:
        """创建所有数据库表（幂等操作）。"""
        self.conn.create_tables()

    def get_session(self) -> Union[Session, AsyncSession]:
        """获取数据库会话。"""
        return self.conn.get_session()

    @property
    def database_url(self) -> str:
        """数据库连接URL。"""
        return self.conn.database_url

    @property
    def engine(self):
        """SQLAlchemy 引擎对象。"""
        return self.conn.engine

    @property
    def is_async(self) -> bool:
        """是否为异步引擎。"""
        return self.conn.is_async

    def execute_raw_sql(self, sql: str,
                        params: Optional[dict] = None) -> Any:
        """执行原始 SQL 语句。

        注意：应优先使用 ORM 方法，仅在必要时使用原始 SQL。

        Args:
            sql: SQL 语句字符串。
            params: SQL 参数字典（可选）。

        Returns:
            SQL 执行结果。
        """
        return self.conn.execute_raw_sql(sql, params)

    def close(self) -> None:
        """关闭数据库连接，释放所有资源。"""
        self.conn.close()

    # ================================================================
    # 便捷写入方法
    # ================================================================

    def save_raw_message(self, msg_data: Dict[str, Any]) -> int:
        """保存原始消息（自动去重）。

        Args:
            msg_data: 消息数据字典，详见 MessageRepository.save_raw_message。

        Returns:
            消息记录 ID。
        """
        return self.messages.save_raw_message(msg_data)

    def update_parse_status(self, msg_id: int, status: str,
                            result: Optional[Dict[str, Any]] = None,
                            error: Optional[str] = None) -> None:
        """更新消息解析状态。

        Args:
            msg_id: 消息记录 ID。
            status: 新的解析状态（pending/parsed/failed/ignored）。
            result: 解析结果字典（可选）。
            error: 解析错误信息（可选）。
        """
        self.messages.update_parse_status(msg_id, status, result, error)

    def save_service_record(self, record_data: Dict[str, Any],
                            raw_message_id: int) -> int:
        """保存服务记录。

        自动处理关联实体的创建（顾客、服务类型、员工、渠道）。

        Args:
            record_data: 服务记录数据字典，详见 ServiceRecordRepository.save。
            raw_message_id: 关联的原始消息 ID。

        Returns:
            新创建的服务记录 ID。
        """
        return self.service_records.save(record_data, raw_message_id)

    def save_product_sale(self, sale_data: Dict[str, Any],
                          raw_message_id: int) -> int:
        """保存商品销售记录。

        自动处理关联实体的创建。

        Args:
            sale_data: 销售数据字典，详见 ProductSaleRepository.save。
            raw_message_id: 关联的原始消息 ID。

        Returns:
            新创建的销售记录 ID。
        """
        return self.product_sales.save(sale_data, raw_message_id)

    def save_membership(self, membership_data: Dict[str, Any],
                        raw_message_id: int) -> int:
        """保存会员卡记录（开卡）。

        自动处理顾客的创建。

        Args:
            membership_data: 会员卡数据字典，详见 MembershipRepository.save。
            raw_message_id: 关联的原始消息 ID。

        Returns:
            新创建的会员卡 ID。
        """
        return self.memberships.save(membership_data, raw_message_id)

    def save_daily_summary(self, summary_date: date,
                           summary_data: Dict[str, Any]) -> int:
        """保存每日汇总（幂等，已存在则更新）。

        Args:
            summary_date: 汇总日期。
            summary_data: 汇总数据字典，详见 SummaryRepository.save。

        Returns:
            汇总记录 ID。
        """
        return self.summaries.save(summary_date, summary_data)

    # ================================================================
    # 便捷查询方法
    # ================================================================

    def get_daily_records(self, target_date: Union[str, date]
                          ) -> List[Dict[str, Any]]:
        """获取指定日期的所有经营记录。

        包括服务记录和商品销售记录。

        Args:
            target_date: 日期，支持 ``YYYY-MM-DD`` 字符串或 date 对象。

        Returns:
            记录列表，每条记录包含 type、id、customer_name、amount 等字段。
        """
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        services = self.service_records.get_by_date(target_date)
        sales = self.product_sales.get_by_date(target_date)
        return services + sales

    def get_staff_list(self, active_only: bool = True
                       ) -> List[Dict[str, Any]]:
        """获取员工列表。

        Args:
            active_only: 是否只返回在职员工，默认 True。

        Returns:
            员工信息字典列表。
        """
        if active_only:
            employees = self.staff.get_active_staff()
        else:
            employees = self.staff.get_all(Employee)

        return [
            {
                "id": e.id,
                "name": e.name,
                "role": e.role,
                "commission_rate": (
                    float(e.commission_rate) if e.commission_rate else 0
                ),
                "is_active": e.is_active,
            }
            for e in employees
        ]

    def get_customer_info(self, name: str) -> Optional[Dict[str, Any]]:
        """按姓名查询顾客信息（含会员卡）。

        Args:
            name: 顾客姓名。

        Returns:
            顾客信息字典（含 memberships 列表），不存在返回 None。
        """
        results = self.customers.search(name)
        if not results:
            return None

        customer = results[0]
        memberships = self.memberships.get_active_by_customer(customer.id)

        return {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "notes": customer.notes,
            "memberships": [
                {
                    "id": m.id,
                    "card_type": m.card_type,
                    "balance": float(m.balance) if m.balance else 0,
                    "remaining_sessions": m.remaining_sessions,
                    "points": m.points or 0,
                    "is_active": m.is_active,
                }
                for m in memberships
            ],
        }

    def get_channel_list(self, channel_type: Optional[str] = None
                         ) -> List[Dict[str, Any]]:
        """获取引流渠道列表。

        Args:
            channel_type: 渠道类型过滤（可选）。

        Returns:
            渠道信息字典列表。
        """
        channels = self.channels.get_active_channels(channel_type)
        return [
            {
                "id": c.id,
                "name": c.name,
                "channel_type": c.channel_type,
                "commission_rate": (
                    float(c.commission_rate) if c.commission_rate else None
                ),
                "commission_type": c.commission_type,
                "is_active": c.is_active,
            }
            for c in channels
        ]
