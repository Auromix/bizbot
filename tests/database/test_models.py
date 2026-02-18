"""ORM model behavior tests.

Tests for:
- Model field defaults and nullable constraints
- Relationships between models
- Unique constraints (ServiceType.name, PluginData composite, etc.)
- extra_data JSON field usage
- Model creation with all field types
"""
from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from database.models import (
    Employee, Customer, Membership, ServiceType, ReferralChannel,
    ServiceRecord, Product, ProductSale, InventoryLog,
    RawMessage, Correction, DailySummary, PluginData,
)


class TestEmployeeModel:
    """Test Employee ORM model."""

    def test_create_employee_with_defaults(self, temp_db):
        with temp_db.get_session() as session:
            emp = Employee(name="张三")
            session.add(emp)
            session.commit()

            assert emp.id is not None
            assert emp.name == "张三"
            assert emp.role == "staff"
            assert emp.is_active is True
            assert emp.commission_rate == 0

    def test_employee_all_fields(self, temp_db):
        with temp_db.get_session() as session:
            emp = Employee(
                name="Tony",
                role="manager",
                commission_rate=15.5,
                is_active=True,
                extra_data={"level": "senior", "department": "haircut"},
            )
            session.add(emp)
            session.commit()
            assert emp.role == "manager"
            assert float(emp.commission_rate) == 15.5
            assert emp.extra_data["level"] == "senior"
            assert emp.created_at is not None

    def test_employee_extra_data_json(self, temp_db):
        with temp_db.get_session() as session:
            emp = Employee(name="ExtraData", extra_data={"skills": ["haircut", "dye"]})
            session.add(emp)
            session.commit()
            assert emp.extra_data["skills"] == ["haircut", "dye"]


class TestCustomerModel:
    """Test Customer ORM model."""

    def test_create_customer_with_defaults(self, temp_db):
        with temp_db.get_session() as session:
            cust = Customer(name="Alice")
            session.add(cust)
            session.commit()

            assert cust.id is not None
            assert cust.name == "Alice"
            assert cust.phone is None
            assert cust.notes is None

    def test_customer_with_all_fields(self, temp_db):
        with temp_db.get_session() as session:
            cust = Customer(
                name="Bob",
                phone="13800138000",
                notes="VIP customer",
                extra_data={"source": "meituan", "vip_level": 3},
            )
            session.add(cust)
            session.commit()

            assert cust.phone == "13800138000"
            assert cust.notes == "VIP customer"
            assert cust.extra_data["vip_level"] == 3


class TestServiceTypeModel:
    """Test ServiceType ORM model."""

    def test_create_service_type(self, temp_db):
        with temp_db.get_session() as session:
            st = ServiceType(name="头疗", default_price=30.0, category="therapy")
            session.add(st)
            session.commit()
            assert st.id is not None
            assert st.name == "头疗"

    def test_service_type_unique_name_constraint(self, temp_db):
        """ServiceType.name has unique=True constraint."""
        with temp_db.get_session() as session:
            session.add(ServiceType(name="UniqueService"))
            session.commit()

        with temp_db.get_session() as session:
            session.add(ServiceType(name="UniqueService"))
            with pytest.raises(IntegrityError):
                session.commit()


class TestProductModel:
    """Test Product ORM model."""

    def test_create_product_with_defaults(self, temp_db):
        with temp_db.get_session() as session:
            product = Product(name="蛋白粉")
            session.add(product)
            session.commit()

            assert product.id is not None
            assert product.stock_quantity == 0
            assert product.low_stock_threshold == 10

    def test_product_all_fields(self, temp_db):
        with temp_db.get_session() as session:
            product = Product(
                name="洗发水",
                category="retail",
                unit_price=68.0,
                stock_quantity=50,
                low_stock_threshold=5,
                extra_data={"brand": "KERASTASE"},
            )
            session.add(product)
            session.commit()

            assert product.category == "retail"
            assert float(product.unit_price) == 68.0
            assert product.stock_quantity == 50


class TestReferralChannelModel:
    """Test ReferralChannel ORM model."""

    def test_create_channel(self, temp_db):
        with temp_db.get_session() as session:
            ch = ReferralChannel(
                name="美团", channel_type="platform",
                commission_rate=15.0, commission_type="percentage",
            )
            session.add(ch)
            session.commit()

            assert ch.id is not None
            assert ch.is_active is True
            assert ch.commission_type == "percentage"

    def test_channel_with_contact(self, temp_db):
        with temp_db.get_session() as session:
            ch = ReferralChannel(
                name="李哥", channel_type="external",
                contact_info="13900139000",
                notes="老客户推荐",
            )
            session.add(ch)
            session.commit()
            assert ch.contact_info == "13900139000"


class TestMembershipModel:
    """Test Membership ORM model."""

    def test_create_membership(self, temp_db):
        with temp_db.get_session() as session:
            cust = Customer(name="MemberCust")
            session.add(cust)
            session.flush()

            m = Membership(
                customer_id=cust.id,
                card_type="储值卡",
                total_amount=1000,
                balance=1000,
                opened_at=date(2024, 1, 1),
            )
            session.add(m)
            session.commit()

            assert m.id is not None
            assert m.is_active is True
            assert m.points == 0
            assert m.remaining_sessions is None

    def test_membership_customer_relationship(self, temp_db):
        with temp_db.get_session() as session:
            cust = Customer(name="RelCust")
            session.add(cust)
            session.flush()

            m = Membership(
                customer_id=cust.id, card_type="VIP",
                total_amount=2000, balance=2000,
                opened_at=date(2024, 1, 1),
            )
            session.add(m)
            session.commit()

            assert m.customer.name == "RelCust"
            assert len(cust.memberships) == 1


class TestServiceRecordModel:
    """Test ServiceRecord ORM model and its relationships."""

    def test_service_record_relationships(self, temp_db):
        with temp_db.get_session() as session:
            customer = Customer(name="Bob")
            service_type = ServiceType(name="Massage")
            msg = RawMessage(
                sender_nickname="bot",
                content="message",
                timestamp=datetime(2024, 1, 1, 10, 0, 0),
            )
            session.add_all([customer, service_type, msg])
            session.flush()

            record = ServiceRecord(
                customer_id=customer.id,
                service_type_id=service_type.id,
                service_date=date(2024, 1, 1),
                amount=100,
                raw_message_id=msg.id,
            )
            session.add(record)
            session.commit()

            assert record.customer.name == "Bob"
            assert record.service_type.name == "Massage"
            assert record.raw_message.id == msg.id
            assert record.confirmed is False
            assert record.commission_amount == 0

    def test_service_record_with_employee_and_recorder(self, temp_db):
        with temp_db.get_session() as session:
            emp = Employee(name="Technician")
            recorder = Employee(name="FrontDesk")
            cust = Customer(name="Cust1")
            st = ServiceType(name="Therapy")
            session.add_all([emp, recorder, cust, st])
            session.flush()

            record = ServiceRecord(
                customer_id=cust.id,
                employee_id=emp.id,
                recorder_id=recorder.id,
                service_type_id=st.id,
                service_date=date(2024, 1, 28),
                amount=198,
                commission_amount=20,
                commission_to="李哥",
                net_amount=178,
            )
            session.add(record)
            session.commit()

            assert record.employee.name == "Technician"
            assert record.recorder.name == "FrontDesk"


class TestProductSaleModel:
    """Test ProductSale ORM model."""

    def test_create_product_sale(self, temp_db):
        with temp_db.get_session() as session:
            product = Product(name="Shampoo", unit_price=50)
            customer = Customer(name="SaleCust")
            session.add_all([product, customer])
            session.flush()

            sale = ProductSale(
                product_id=product.id,
                customer_id=customer.id,
                quantity=2,
                unit_price=50,
                total_amount=100,
                sale_date=date(2024, 1, 28),
            )
            session.add(sale)
            session.commit()

            assert sale.id is not None
            assert sale.product.name == "Shampoo"
            assert sale.customer.name == "SaleCust"


class TestInventoryLogModel:
    """Test InventoryLog ORM model."""

    def test_create_inventory_log(self, temp_db):
        with temp_db.get_session() as session:
            product = Product(name="LogProduct")
            session.add(product)
            session.flush()

            log = InventoryLog(
                product_id=product.id,
                change_type="restock",
                quantity_change=50,
                quantity_after=50,
                notes="Initial stock",
            )
            session.add(log)
            session.commit()

            assert log.id is not None
            assert log.product.name == "LogProduct"
            assert log.change_type == "restock"


class TestRawMessageModel:
    """Test RawMessage ORM model."""

    def test_create_raw_message(self, temp_db):
        with temp_db.get_session() as session:
            msg = RawMessage(
                msg_id="wx-001",
                sender_nickname="User1",
                content="Hello",
                timestamp=datetime(2024, 1, 28, 10, 0, 0),
            )
            session.add(msg)
            session.commit()

            assert msg.id is not None
            assert msg.parse_status == "pending"
            assert msg.msg_type == "text"
            assert msg.is_at_bot is False

    def test_raw_message_unique_msg_id(self, temp_db):
        """msg_id should be unique."""
        with temp_db.get_session() as session:
            msg1 = RawMessage(
                msg_id="wx-dup",
                sender_nickname="U1",
                content="C1",
                timestamp=datetime(2024, 1, 1),
            )
            session.add(msg1)
            session.commit()

        with temp_db.get_session() as session:
            msg2 = RawMessage(
                msg_id="wx-dup",
                sender_nickname="U2",
                content="C2",
                timestamp=datetime(2024, 1, 2),
            )
            session.add(msg2)
            with pytest.raises(IntegrityError):
                session.commit()


class TestCorrectionModel:
    """Test Correction ORM model."""

    def test_create_correction(self, temp_db):
        with temp_db.get_session() as session:
            msg = RawMessage(
                sender_nickname="admin",
                content="correction",
                timestamp=datetime(2024, 1, 28),
            )
            session.add(msg)
            session.flush()

            correction = Correction(
                original_record_type="service_records",
                original_record_id=1,
                correction_type="amount_change",
                old_value={"amount": 100},
                new_value={"amount": 120},
                reason="错误金额",
                raw_message_id=msg.id,
            )
            session.add(correction)
            session.commit()

            assert correction.id is not None
            assert correction.raw_message.sender_nickname == "admin"


class TestDailySummaryModel:
    """Test DailySummary ORM model."""

    def test_create_daily_summary(self, temp_db):
        with temp_db.get_session() as session:
            summary = DailySummary(
                summary_date=date(2024, 1, 28),
                total_service_revenue=1000,
                service_count=5,
                summary_text="Good day",
            )
            session.add(summary)
            session.commit()

            assert summary.id is not None
            assert summary.confirmed is False

    def test_daily_summary_unique_date(self, temp_db):
        """summary_date should be unique."""
        with temp_db.get_session() as session:
            session.add(DailySummary(
                summary_date=date(2024, 1, 28),
                total_service_revenue=500,
            ))
            session.commit()

        with temp_db.get_session() as session:
            session.add(DailySummary(
                summary_date=date(2024, 1, 28),
                total_service_revenue=600,
            ))
            with pytest.raises(IntegrityError):
                session.commit()


class TestPluginDataModel:
    """Test PluginData ORM model."""

    def test_create_plugin_data(self, temp_db):
        with temp_db.get_session() as session:
            pd = PluginData(
                plugin_name="gym",
                entity_type="customer",
                entity_id=1,
                data_key="body_fat",
                data_value=18.5,
            )
            session.add(pd)
            session.commit()

            assert pd.id is not None
            assert pd.data_value == 18.5

    def test_plugin_data_unique_constraint(self, temp_db):
        """Composite unique constraint on (plugin_name, entity_type, entity_id, data_key)."""
        with temp_db.get_session() as session:
            pd1 = PluginData(
                plugin_name="gym",
                entity_type="customer",
                entity_id=1,
                data_key="body_fat",
                data_value=18.5,
            )
            pd2 = PluginData(
                plugin_name="gym",
                entity_type="customer",
                entity_id=1,
                data_key="body_fat",
                data_value=19.0,
            )
            session.add(pd1)
            session.commit()
            session.add(pd2)
            with pytest.raises(IntegrityError):
                session.commit()

    def test_plugin_data_different_keys_ok(self, temp_db):
        """Different data_key values should NOT conflict."""
        with temp_db.get_session() as session:
            session.add(PluginData(
                plugin_name="gym", entity_type="customer",
                entity_id=1, data_key="body_fat", data_value=18.5,
            ))
            session.add(PluginData(
                plugin_name="gym", entity_type="customer",
                entity_id=1, data_key="weight", data_value=75,
            ))
            session.commit()  # Should not raise
