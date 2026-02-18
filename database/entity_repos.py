"""实体仓库 —— 基础实体的数据访问层。

管理系统中的基础实体（员工、顾客、服务类型、商品、引流渠道），
这些实体是各类商业模式（理发店、健身房、理疗馆、餐厅等）的共性部分。

每个仓库继承 BaseCRUD 获得通用能力，并添加领域特定的查询方法。
"""
from typing import Optional, List
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from .connection import DatabaseConnection
from .models import (
    Employee, Customer, ServiceType, Product, ReferralChannel
)


class StaffRepository(BaseCRUD):
    """员工/Staff 仓库。

    管理员工信息，适用于各类门店的人员管理：
    - 理发店：理发师、前台
    - 健身房：私教、前台、保洁
    - 理疗馆：技师、管理员
    - 餐厅：厨师、服务员、收银
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def get_or_create(self, name: str,
                      session: Optional[Session] = None) -> Employee:
        """获取或创建员工（按姓名匹配）。

        Args:
            name: 员工姓名。
            session: 外部会话（可选）。

        Returns:
            Employee 对象。
        """
        def _do(sess):
            employee = sess.query(Employee).filter(
                Employee.name == name
            ).first()
            if not employee:
                employee = Employee(name=name)
                sess.add(employee)
                sess.flush()
                sess.refresh(employee)
            return employee

        if session:
            return _do(session)

        with self._get_session() as sess:
            employee = _do(sess)
            sess.commit()
            employee_id = employee.id
        with self._get_session() as sess:
            return sess.query(Employee).filter(
                Employee.id == employee_id
            ).first()

    def get_active_staff(self,
                         session: Optional[Session] = None) -> List[Employee]:
        """获取所有在职员工。

        Returns:
            在职员工列表。
        """
        return self.get_all(
            Employee, filters={"is_active": True}, session=session
        )

    def deactivate(self, staff_id: int,
                   session: Optional[Session] = None) -> Optional[Employee]:
        """停用员工。

        Args:
            staff_id: 员工ID。

        Returns:
            更新后的 Employee 对象。
        """
        return self.update_by_id(
            Employee, staff_id, session=session, is_active=False
        )

    def search(self, keyword: str,
               session: Optional[Session] = None) -> List[Employee]:
        """按姓名搜索员工。

        Args:
            keyword: 搜索关键词。

        Returns:
            匹配的员工列表。
        """
        def _query(sess):
            return sess.query(Employee).filter(
                Employee.name.contains(keyword)
            ).all()

        if session:
            return _query(session)

        with self._get_session() as sess:
            return _query(sess)


class CustomerRepository(BaseCRUD):
    """顾客/会员 仓库。

    管理顾客信息，适用于各类门店的客户管理。
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def get_or_create(self, name: str,
                      session: Optional[Session] = None) -> Customer:
        """获取或创建顾客（按姓名匹配）。

        Args:
            name: 顾客姓名。
            session: 外部会话（可选）。

        Returns:
            Customer 对象。
        """
        def _do(sess):
            customer = sess.query(Customer).filter(
                Customer.name == name
            ).first()
            if not customer:
                customer = Customer(name=name)
                sess.add(customer)
                sess.flush()
                sess.refresh(customer)
            return customer

        if session:
            return _do(session)

        with self._get_session() as sess:
            customer = _do(sess)
            sess.commit()
            customer_id = customer.id
        with self._get_session() as sess:
            return sess.query(Customer).filter(
                Customer.id == customer_id
            ).first()

    def search(self, keyword: str,
               session: Optional[Session] = None) -> List[Customer]:
        """按姓名或电话搜索顾客。

        Args:
            keyword: 搜索关键词。

        Returns:
            匹配的顾客列表。
        """
        def _query(sess):
            return sess.query(Customer).filter(
                or_(
                    Customer.name.contains(keyword),
                    Customer.phone.contains(keyword)
                )
            ).all()

        if session:
            return _query(session)

        with self._get_session() as sess:
            return _query(sess)


class ServiceTypeRepository(BaseCRUD):
    """服务类型 仓库。

    管理服务类型字典数据，适用于各类门店：
    - 理发店：剪发、烫发、染发、护理
    - 健身房：私教课、团课、体测
    - 理疗馆：头疗、理疗、按摩、足浴
    - 餐厅：堂食、外卖、宴席
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def get_or_create(self, name: str,
                      default_price: Optional[float] = None,
                      category: Optional[str] = None,
                      session: Optional[Session] = None) -> ServiceType:
        """获取或创建服务类型。

        Args:
            name: 服务类型名称。
            default_price: 默认价格（可选）。
            category: 服务类别（可选）。
            session: 外部会话（可选）。

        Returns:
            ServiceType 对象。
        """
        def _do(sess):
            service_type = sess.query(ServiceType).filter(
                ServiceType.name == name
            ).first()
            if not service_type:
                service_type = ServiceType(
                    name=name,
                    default_price=default_price,
                    category=category
                )
                sess.add(service_type)
                sess.flush()
                sess.refresh(service_type)
            return service_type

        if session:
            return _do(session)

        with self._get_session() as sess:
            service_type = _do(sess)
            sess.commit()
            st_id = service_type.id
        with self._get_session() as sess:
            return sess.query(ServiceType).filter(
                ServiceType.id == st_id
            ).first()

    def get_by_category(self, category: str,
                        session: Optional[Session] = None) -> List[ServiceType]:
        """按类别查询服务类型。

        Args:
            category: 服务类别。

        Returns:
            匹配的服务类型列表。
        """
        return self.get_all(
            ServiceType, filters={"category": category}, session=session
        )


class ProductRepository(BaseCRUD):
    """商品 仓库。

    管理商品信息和库存，适用于各类门店的产品管理：
    - 理发店：洗发水、护发素
    - 健身房：蛋白粉、运动装备
    - 理疗馆：保健品、精油
    - 餐厅：菜品原料、饮品
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def get_or_create(self, name: str,
                      category: Optional[str] = None,
                      unit_price: Optional[float] = None,
                      session: Optional[Session] = None) -> Product:
        """获取或创建商品。

        Args:
            name: 商品名称。
            category: 商品类别（可选）。
            unit_price: 单价（可选）。
            session: 外部会话（可选）。

        Returns:
            Product 对象。
        """
        def _do(sess):
            product = sess.query(Product).filter(
                Product.name == name
            ).first()
            if not product:
                product = Product(
                    name=name, category=category, unit_price=unit_price
                )
                sess.add(product)
                sess.flush()
                sess.refresh(product)
            return product

        if session:
            return _do(session)

        with self._get_session() as sess:
            product = _do(sess)
            sess.commit()
            product_id = product.id
        with self._get_session() as sess:
            return sess.query(Product).filter(
                Product.id == product_id
            ).first()

    def get_low_stock(self,
                      session: Optional[Session] = None) -> List[Product]:
        """获取低库存商品。

        Returns:
            库存低于阈值的商品列表。
        """
        def _query(sess):
            return sess.query(Product).filter(
                Product.stock_quantity <= Product.low_stock_threshold
            ).all()

        if session:
            return _query(session)

        with self._get_session() as sess:
            return _query(sess)

    def update_stock(self, product_id: int, quantity_change: int,
                     session: Optional[Session] = None) -> Optional[Product]:
        """更新商品库存（增/减）。

        Args:
            product_id: 商品ID。
            quantity_change: 变动数量（正数入库，负数出库）。

        Returns:
            更新后的 Product 对象。
        """
        def _do(sess):
            product = sess.query(Product).filter(
                Product.id == product_id
            ).first()
            if product:
                product.stock_quantity += quantity_change
                sess.flush()
                sess.refresh(product)
            return product

        if session:
            return _do(session)

        with self._get_session() as sess:
            product = _do(sess)
            if product:
                sess.commit()
                pid = product.id
            else:
                return None
        with self._get_session() as sess:
            return sess.query(Product).filter(Product.id == pid).first()


class ChannelRepository(BaseCRUD):
    """引流渠道 仓库。

    管理外部引流渠道信息，支持各类门店的渠道管理：
    - 美团、大众点评等平台渠道
    - 合作方引流
    - 员工内部推荐
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def get_or_create(self, name: str,
                      channel_type: str = "external",
                      contact_info: Optional[str] = None,
                      commission_rate: Optional[float] = None,
                      session: Optional[Session] = None) -> ReferralChannel:
        """获取或创建引流渠道。

        Args:
            name: 渠道名称（如：美团、大众点评、李哥）。
            channel_type: 渠道类型，可选值：internal/external/platform。
            contact_info: 联系方式（可选）。
            commission_rate: 默认提成率（可选）。
            session: 外部会话（可选）。

        Returns:
            ReferralChannel 对象。
        """
        def _do(sess):
            channel = sess.query(ReferralChannel).filter(
                ReferralChannel.name == name
            ).first()
            if not channel:
                channel = ReferralChannel(
                    name=name,
                    channel_type=channel_type,
                    contact_info=contact_info,
                    commission_rate=commission_rate
                )
                sess.add(channel)
                sess.flush()
                sess.refresh(channel)
            return channel

        if session:
            return _do(session)

        with self._get_session() as sess:
            channel = _do(sess)
            sess.commit()
            channel_id = channel.id
        with self._get_session() as sess:
            return sess.query(ReferralChannel).filter(
                ReferralChannel.id == channel_id
            ).first()

    def get_active_channels(self, channel_type: Optional[str] = None,
                            is_active: Optional[bool] = True,
                            session: Optional[Session] = None
                            ) -> List[ReferralChannel]:
        """获取引流渠道列表。

        Args:
            channel_type: 渠道类型过滤（可选）。
            is_active: 是否只返回激活的渠道（可选）。

        Returns:
            引流渠道列表。
        """
        def _query(sess):
            query = sess.query(ReferralChannel)
            if channel_type:
                query = query.filter(
                    ReferralChannel.channel_type == channel_type
                )
            if is_active is not None:
                query = query.filter(ReferralChannel.is_active == is_active)
            return query.all()

        if session:
            return _query(session)

        with self._get_session() as sess:
            return _query(sess)

