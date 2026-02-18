"""业务记录仓库 —— 核心业务数据的数据访问层。

管理系统中的核心业务记录（服务记录、商品销售、会员卡），
这些记录是日常经营活动产生的交易数据。

各仓库会自动处理关联实体的创建（如自动创建顾客、员工等），
简化上层业务代码的复杂度。
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from loguru import logger

from .base_crud import BaseCRUD
from .connection import DatabaseConnection
from .entity_repos import (
    StaffRepository, CustomerRepository,
    ServiceTypeRepository, ProductRepository, ChannelRepository
)
from .models import (
    ServiceRecord, ProductSale, Membership,
    InventoryLog, Customer
)


class ServiceRecordRepository(BaseCRUD):
    """服务记录 仓库。

    管理服务/消费记录，适用于各类门店的核心业务记录：
    - 理发店：剪发、烫发等服务记录
    - 健身房：私教课、团课等课程记录
    - 理疗馆：头疗、理疗等服务记录
    - 餐厅：堂食、外卖等消费记录

    自动处理关联实体（顾客、服务类型、员工、渠道）的创建。
    """

    def __init__(self, conn: DatabaseConnection,
                 staff_repo: StaffRepository,
                 customer_repo: CustomerRepository,
                 service_type_repo: ServiceTypeRepository,
                 channel_repo: ChannelRepository) -> None:
        super().__init__(conn)
        self._staff = staff_repo
        self._customers = customer_repo
        self._service_types = service_type_repo
        self._channels = channel_repo

    def save(self, record_data: Dict[str, Any],
             raw_message_id: int) -> int:
        """保存服务记录。

        自动处理关联实体的创建（顾客、服务类型、员工、渠道）。

        Args:
            record_data: 服务记录数据字典，支持以下键：
                - customer_name: 顾客姓名（必填）
                - service_or_product: 服务类型名称（必填）
                - date: 服务日期，YYYY-MM-DD 或 date 对象（必填）
                - amount: 金额（必填）
                - commission: 提成金额（可选）
                - commission_to: 提成对象（可选，向后兼容）
                - referral_channel_id: 引流渠道ID（可选，推荐）
                - net_amount: 净收入（可选，默认等于amount）
                - recorder_nickname: 记录员昵称（可选）
                - notes: 备注（可选）
                - confidence: 解析置信度（可选，默认0.5）
                - confirmed: 是否已确认（可选，默认False）
                - extra_data: 扩展数据（可选）
            raw_message_id: 关联的原始消息ID。

        Returns:
            新创建的服务记录ID。

        Raises:
            ValueError: 日期格式无效或缺失。
        """
        with self._get_session() as session:
            # 自动创建关联实体
            customer = self._customers.get_or_create(
                record_data.get("customer_name", ""), session=session
            )
            service_type = self._service_types.get_or_create(
                record_data.get("service_or_product", ""),
                record_data.get("default_price"),
                record_data.get("category"),
                session=session
            )

            recorder = None
            if record_data.get("recorder_nickname"):
                recorder = self._staff.get_or_create(
                    record_data["recorder_nickname"],
                    session=session
                )

            # 解析日期
            service_date = self._parse_date(
                record_data.get("date"), "Service date"
            )

            # 处理引流渠道
            referral_channel_id = None
            if record_data.get("referral_channel_id"):
                referral_channel_id = record_data["referral_channel_id"]
            elif record_data.get("commission_to"):
                channel = self._channels.get_or_create(
                    name=record_data["commission_to"],
                    channel_type="external",
                    session=session
                )
                referral_channel_id = channel.id if channel else None

            record = ServiceRecord(
                customer_id=customer.id,
                service_type_id=service_type.id,
                service_date=service_date,
                amount=record_data.get("amount", 0),
                commission_amount=record_data.get("commission") or 0,
                commission_to=record_data.get("commission_to"),
                referral_channel_id=referral_channel_id,
                net_amount=(
                    record_data.get("net_amount")
                    or record_data.get("amount", 0)
                ),
                membership_id=record_data.get("membership_id"),
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

    def get_by_date(self, target_date: date,
                    session: Optional[Session] = None
                    ) -> List[Dict[str, Any]]:
        """获取指定日期的服务记录。

        Args:
            target_date: 目标日期。

        Returns:
            服务记录字典列表。
        """
        def _query(sess):
            records = sess.query(ServiceRecord).filter(
                ServiceRecord.service_date == target_date
            ).all()
            return [
                {
                    "type": "service",
                    "id": r.id,
                    "customer_name": (
                        r.customer.name if r.customer else ""
                    ),
                    "service_type": (
                        r.service_type.name if r.service_type else ""
                    ),
                    "amount": float(r.amount),
                    "commission": (
                        float(r.commission_amount)
                        if r.commission_amount else None
                    ),
                    "commission_to": r.commission_to,
                    "net_amount": (
                        float(r.net_amount)
                        if r.net_amount else float(r.amount)
                    ),
                    "confirmed": r.confirmed,
                }
                for r in records
            ]

        if session:
            return _query(session)

        with self._get_session() as sess:
            return _query(sess)

    def confirm(self, record_id: int,
                session: Optional[Session] = None) -> bool:
        """确认服务记录。

        Args:
            record_id: 记录ID。

        Returns:
            是否成功确认。
        """
        result = self.update_by_id(
            ServiceRecord, record_id, session=session,
            confirmed=True, confirmed_at=datetime.utcnow()
        )
        return result is not None

    @staticmethod
    def _parse_date(date_value: Any, field_name: str = "Date") -> date:
        """解析日期值。

        Args:
            date_value: 日期值（str 或 date 对象）。
            field_name: 字段名称（用于错误提示）。

        Returns:
            date 对象。

        Raises:
            ValueError: 格式无效或缺失。
        """
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(
                    f"Invalid date format: {date_value}, "
                    f"expected YYYY-MM-DD"
                )
        raise ValueError(f"{field_name} is required")


class ProductSaleRepository(BaseCRUD):
    """商品销售 仓库。

    管理商品销售记录，适用于各类门店的产品销售跟踪。
    自动处理商品、顾客、记录员等关联实体的创建。
    """

    def __init__(self, conn: DatabaseConnection,
                 staff_repo: StaffRepository,
                 customer_repo: CustomerRepository,
                 product_repo: ProductRepository) -> None:
        super().__init__(conn)
        self._staff = staff_repo
        self._customers = customer_repo
        self._products = product_repo

    def save(self, sale_data: Dict[str, Any],
             raw_message_id: int) -> int:
        """保存商品销售记录。

        自动处理关联实体的创建。

        Args:
            sale_data: 销售数据字典，支持以下键：
                - service_or_product: 商品名称（必填）
                - date: 销售日期（必填）
                - amount: 总金额（必填）
                - quantity: 数量（可选，默认1）
                - unit_price: 单价（可选）
                - category: 商品类别（可选）
                - customer_name: 顾客姓名（可选）
                - recorder_nickname: 记录员昵称（可选）
                - notes: 备注（可选）
                - confidence: 置信度（可选，默认0.5）
                - confirmed: 是否确认（可选，默认False）
            raw_message_id: 关联的原始消息ID。

        Returns:
            新创建的销售记录ID。
        """
        with self._get_session() as session:
            product = self._products.get_or_create(
                sale_data.get("service_or_product", ""),
                sale_data.get("category"),
                sale_data.get("unit_price"),
                session=session
            )

            customer = None
            if sale_data.get("customer_name"):
                customer = self._customers.get_or_create(
                    sale_data["customer_name"], session=session
                )

            recorder = None
            if sale_data.get("recorder_nickname"):
                recorder = self._staff.get_or_create(
                    sale_data["recorder_nickname"],
                    session=session
                )

            sale_date = ServiceRecordRepository._parse_date(
                sale_data.get("date"), "Sale date"
            )

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

    def get_by_date(self, target_date: date,
                    session: Optional[Session] = None
                    ) -> List[Dict[str, Any]]:
        """获取指定日期的销售记录。

        Args:
            target_date: 目标日期。

        Returns:
            销售记录字典列表。
        """
        def _query(sess):
            sales = sess.query(ProductSale).filter(
                ProductSale.sale_date == target_date
            ).all()
            return [
                {
                    "type": "product_sale",
                    "id": s.id,
                    "product_name": (
                        s.product.name if s.product else ""
                    ),
                    "customer_name": (
                        s.customer.name if s.customer else ""
                    ),
                    "total_amount": float(s.total_amount),
                    "quantity": s.quantity,
                    "confirmed": s.confirmed,
                }
                for s in sales
            ]

        if session:
            return _query(session)

        with self._get_session() as sess:
            return _query(sess)


class MembershipRepository(BaseCRUD):
    """会员卡 仓库。

    管理会员卡/储值卡，适用于需要会员体系的门店：
    - 健身房：年卡、季卡、月卡、次卡
    - 理疗馆：理疗卡、头疗卡、储值卡
    - 理发店：储值卡、VIP卡
    - 餐厅：储值卡、优惠卡

    支持余额管理、次数管理、积分管理。
    """

    def __init__(self, conn: DatabaseConnection,
                 customer_repo: CustomerRepository) -> None:
        super().__init__(conn)
        self._customers = customer_repo

    def save(self, membership_data: Dict[str, Any],
             raw_message_id: int) -> int:
        """保存会员卡记录（开卡）。

        自动处理顾客的创建。

        Args:
            membership_data: 会员卡数据字典，支持以下键：
                - customer_name: 顾客姓名（必填）
                - date: 开卡日期（必填）
                - amount: 充值金额（必填）
                - card_type: 卡类型（可选，默认"储值卡"）
                - remaining_sessions: 剩余次数（可选）
                - expires_at: 到期日期（可选）
            raw_message_id: 关联的原始消息ID。

        Returns:
            新创建的会员卡ID。
        """
        with self._get_session() as session:
            customer = self._customers.get_or_create(
                membership_data.get("customer_name", ""), session=session
            )

            opened_at = ServiceRecordRepository._parse_date(
                membership_data.get("date"), "Membership opened_at date"
            )

            expires_at = None
            if membership_data.get("expires_at"):
                expires_at = ServiceRecordRepository._parse_date(
                    membership_data["expires_at"], "Expires at"
                )

            membership = Membership(
                customer_id=customer.id,
                card_type=membership_data.get("card_type", "储值卡"),
                total_amount=membership_data.get("amount", 0),
                balance=membership_data.get("amount", 0),
                remaining_sessions=membership_data.get("remaining_sessions"),
                opened_at=opened_at,
                expires_at=expires_at
            )

            session.add(membership)
            session.commit()
            session.refresh(membership)
            return membership.id

    def get_active_by_customer(self, customer_id: int,
                               session: Optional[Session] = None
                               ) -> List[Membership]:
        """获取顾客的有效会员卡。

        Args:
            customer_id: 顾客ID。

        Returns:
            有效会员卡列表。
        """
        return self.get_all(
            Membership,
            filters={"customer_id": customer_id, "is_active": True},
            session=session
        )

    def deduct_balance(self, membership_id: int, amount: float,
                       session: Optional[Session] = None
                       ) -> Optional[Membership]:
        """扣减会员卡余额。

        Args:
            membership_id: 会员卡ID。
            amount: 扣减金额。

        Returns:
            更新后的 Membership 对象，余额不足返回 None。
        """
        def _do(sess):
            membership = sess.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            if membership and float(membership.balance) >= amount:
                membership.balance = float(membership.balance) - amount
                sess.flush()
                sess.refresh(membership)
                return membership
            return None

        if session:
            return _do(session)

        with self._get_session() as sess:
            membership = _do(sess)
            if membership:
                sess.commit()
                mid = membership.id
            else:
                return None
        with self._get_session() as sess:
            return sess.query(Membership).filter(
                Membership.id == mid
            ).first()

    def deduct_session(self, membership_id: int, count: int = 1,
                       session: Optional[Session] = None
                       ) -> Optional[Membership]:
        """扣减会员卡次数。

        Args:
            membership_id: 会员卡ID。
            count: 扣减次数，默认1次。

        Returns:
            更新后的 Membership 对象，次数不足返回 None。
        """
        def _do(sess):
            membership = sess.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            if (membership
                    and membership.remaining_sessions is not None
                    and membership.remaining_sessions >= count):
                membership.remaining_sessions -= count
                sess.flush()
                sess.refresh(membership)
                return membership
            return None

        if session:
            return _do(session)

        with self._get_session() as sess:
            membership = _do(sess)
            if membership:
                sess.commit()
                mid = membership.id
            else:
                return None
        with self._get_session() as sess:
            return sess.query(Membership).filter(
                Membership.id == mid
            ).first()

    def add_points(self, membership_id: int, points: int,
                   session: Optional[Session] = None
                   ) -> Optional[Membership]:
        """增加会员积分。

        Args:
            membership_id: 会员卡ID。
            points: 增加的积分数。

        Returns:
            更新后的 Membership 对象。
        """
        def _do(sess):
            membership = sess.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            if membership:
                membership.points = (membership.points or 0) + points
                sess.flush()
                sess.refresh(membership)
            return membership

        if session:
            return _do(session)

        with self._get_session() as sess:
            membership = _do(sess)
            if membership:
                sess.commit()
                mid = membership.id
            else:
                return None
        with self._get_session() as sess:
            return sess.query(Membership).filter(
                Membership.id == mid
            ).first()

