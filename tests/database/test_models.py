"""测试数据库模型。

验证所有ORM模型的字段定义、关系、约束等是否正确。
"""
import pytest
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError

from db.models import (
    Employee, Customer, Membership, ServiceType, ServiceRecord,
    Product, ReferralChannel, PluginData
)
from tests.conftest import temp_db


class TestModels:
    """数据库模型测试类。"""
    
    def test_employee_model(self, temp_db):
        """测试Employee模型。"""
        with temp_db.get_session() as session:
            employee = Employee(
                name="张师傅",
                wechat_nickname="tony_zhang",
                role="staff",
                commission_rate=30.0,
                extra_data={"department": "剪发部", "skill_level": 5}
            )
            session.add(employee)
            session.commit()
            session.refresh(employee)
            
            assert employee.id > 0
            assert employee.name == "张师傅"
            assert employee.wechat_nickname == "tony_zhang"
            assert employee.role == "staff"
            assert float(employee.commission_rate) == 30.0
            assert employee.extra_data == {"department": "剪发部", "skill_level": 5}
            assert employee.is_active is True
            assert employee.created_at is not None
    
    def test_customer_model(self, temp_db):
        """测试Customer模型。"""
        with temp_db.get_session() as session:
            customer = Customer(
                name="王女士",
                phone="13800138000",
                notes="VIP客户",
                extra_data={"vip_level": "gold", "source": "美团"}
            )
            session.add(customer)
            session.commit()
            session.refresh(customer)
            
            assert customer.id > 0
            assert customer.name == "王女士"
            assert customer.phone == "13800138000"
            assert customer.notes == "VIP客户"
            assert customer.extra_data == {"vip_level": "gold", "source": "美团"}
    
    def test_membership_model(self, temp_db):
        """测试Membership模型。"""
        with temp_db.get_session() as session:
            # 先创建顾客
            customer = Customer(name="李先生")
            session.add(customer)
            session.flush()
            
            membership = Membership(
                customer_id=customer.id,
                card_type="年卡",
                total_amount=3000.0,
                balance=3000.0,
                remaining_sessions=365,
                opened_at=date(2024, 1, 1),
                expires_at=date(2024, 12, 31),
                points=0,
                extra_data={"benefits": ["器械区", "瑜伽室", "游泳池"]}
            )
            session.add(membership)
            session.commit()
            session.refresh(membership)
            
            assert membership.id > 0
            assert membership.customer_id == customer.id
            assert membership.card_type == "年卡"
            assert float(membership.total_amount) == 3000.0
            assert float(membership.balance) == 3000.0
            assert membership.remaining_sessions == 365
            assert membership.expires_at == date(2024, 12, 31)
            assert membership.points == 0
            assert membership.extra_data == {"benefits": ["器械区", "瑜伽室", "游泳池"]}
    
    def test_referral_channel_model(self, temp_db):
        """测试ReferralChannel模型。"""
        with temp_db.get_session() as session:
            channel = ReferralChannel(
                name="美团",
                channel_type="platform",
                contact_info="美团商家后台",
                commission_rate=15.0,
                commission_type="percentage",
                extra_data={"platform_id": "MT001"}
            )
            session.add(channel)
            session.commit()
            session.refresh(channel)
            
            assert channel.id > 0
            assert channel.name == "美团"
            assert channel.channel_type == "platform"
            assert channel.contact_info == "美团商家后台"
            assert float(channel.commission_rate) == 15.0
            assert channel.commission_type == "percentage"
            assert channel.extra_data == {"platform_id": "MT001"}
            assert channel.is_active is True
    
    def test_service_record_model(self, temp_db):
        """测试ServiceRecord模型。"""
        with temp_db.get_session() as session:
            # 创建关联实体
            customer = Customer(name="王女士")
            employee = Employee(name="张师傅")
            service_type = ServiceType(name="剪发", default_price=80.0)
            channel = ReferralChannel(name="美团", channel_type="platform")
            session.add_all([customer, employee, service_type, channel])
            session.flush()
            
            record = ServiceRecord(
                customer_id=customer.id,
                employee_id=employee.id,
                service_type_id=service_type.id,
                service_date=date(2024, 1, 28),
                amount=80.0,
                commission_amount=12.0,
                referral_channel_id=channel.id,
                net_amount=68.0,
                extra_data={"duration": 30, "room": "A101"}
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            
            assert record.id > 0
            assert record.customer_id == customer.id
            assert record.employee_id == employee.id
            assert record.service_type_id == service_type.id
            assert record.service_date == date(2024, 1, 28)
            assert float(record.amount) == 80.0
            assert float(record.commission_amount) == 12.0
            assert record.referral_channel_id == channel.id
            assert float(record.net_amount) == 68.0
            assert record.extra_data == {"duration": 30, "room": "A101"}
    
    def test_product_model(self, temp_db):
        """测试Product模型。"""
        with temp_db.get_session() as session:
            product = Product(
                name="洗发水",
                category="accessory",
                unit_price=50.0,
                stock_quantity=100,
                low_stock_threshold=20,
                extra_data={"supplier": "XX供应商", "batch_number": "B20240101"}
            )
            session.add(product)
            session.commit()
            session.refresh(product)
            
            assert product.id > 0
            assert product.name == "洗发水"
            assert product.category == "accessory"
            assert float(product.unit_price) == 50.0
            assert product.stock_quantity == 100
            assert product.low_stock_threshold == 20
            assert product.extra_data == {"supplier": "XX供应商", "batch_number": "B20240101"}
    
    def test_plugin_data_model(self, temp_db):
        """测试PluginData模型。"""
        with temp_db.get_session() as session:
            # 创建员工
            employee = Employee(name="李教练")
            session.add(employee)
            session.flush()
            
            plugin_data = PluginData(
                plugin_name="gym",
                entity_type="employee",
                entity_id=employee.id,
                data_key="certifications",
                data_value=["健身教练资格证", "营养师资格证"]
            )
            session.add(plugin_data)
            session.commit()
            session.refresh(plugin_data)
            
            assert plugin_data.id > 0
            assert plugin_data.plugin_name == "gym"
            assert plugin_data.entity_type == "employee"
            assert plugin_data.entity_id == employee.id
            assert plugin_data.data_key == "certifications"
            assert plugin_data.data_value == ["健身教练资格证", "营养师资格证"]
            
            # 测试唯一约束
            plugin_data2 = PluginData(
                plugin_name="gym",
                entity_type="employee",
                entity_id=employee.id,
                data_key="certifications",
                data_value=["新证书"]
            )
            session.add(plugin_data2)
            with pytest.raises(IntegrityError):
                session.commit()
    
    def test_relationships(self, temp_db):
        """测试模型之间的关系。"""
        with temp_db.get_session() as session:
            # 创建关联实体
            customer = Customer(name="王女士")
            employee = Employee(name="张师傅")
            service_type = ServiceType(name="剪发")
            session.add_all([customer, employee, service_type])
            session.flush()
            
            record = ServiceRecord(
                customer_id=customer.id,
                employee_id=employee.id,
                service_type_id=service_type.id,
                service_date=date(2024, 1, 28),
                amount=80.0
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            
            # 测试关系
            assert record.customer.name == "王女士"
            assert record.employee.name == "张师傅"
            assert record.service_type.name == "剪发"
            assert len(customer.service_records) == 1
            assert len(employee.service_records_as_employee) == 1

