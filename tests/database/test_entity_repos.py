"""Entity repository tests.

Tests for all entity repositories:
- StaffRepository: get_or_create, get_active_staff, deactivate, search
- CustomerRepository: get_or_create, search
- ServiceTypeRepository: get_or_create, get_by_category
- ProductRepository: get_or_create, get_low_stock, update_stock
- ChannelRepository: get_or_create, get_active_channels
"""

import pytest

from database.models import Employee, Customer, ServiceType, Product, ReferralChannel


# ============================================================
# StaffRepository Tests
# ============================================================
class TestStaffRepository:
    """Tests for StaffRepository."""

    def test_get_or_create_new_staff(self, temp_db):
        """Creating a new staff member."""
        emp = temp_db.staff.get_or_create("Tony")
        assert emp is not None
        assert emp.name == "Tony"
        assert emp.id > 0

    def test_get_or_create_existing_by_name(self, temp_db):
        """get_or_create returns existing employee when name matches."""
        emp1 = temp_db.staff.get_or_create("Tony")
        emp2 = temp_db.staff.get_or_create("Tony")
        assert emp1.id == emp2.id


    def test_get_or_create_with_session(self, temp_db):
        with temp_db.get_session() as session:
            emp = temp_db.staff.get_or_create("SessStaff", session=session)
            assert emp.id is not None
            session.commit()

    def test_get_active_staff(self, temp_db):
        temp_db.staff.get_or_create("Active1")
        temp_db.staff.get_or_create("Active2")
        active = temp_db.staff.get_active_staff()
        assert len(active) >= 2
        assert all(e.is_active for e in active)

    def test_deactivate_staff(self, temp_db):
        emp = temp_db.staff.get_or_create("ToDeactivate")
        deactivated = temp_db.staff.deactivate(emp.id)
        assert deactivated is not None
        assert deactivated.is_active is False

        # Should no longer appear in active list
        active = temp_db.staff.get_active_staff()
        assert not any(e.id == emp.id for e in active)

    def test_deactivate_nonexistent(self, temp_db):
        result = temp_db.staff.deactivate(99999)
        assert result is None

    def test_search_by_name(self, temp_db):
        temp_db.staff.get_or_create("Alice Stylist")
        temp_db.staff.get_or_create("Bob Manager")
        results = temp_db.staff.search("Alice")
        assert len(results) == 1
        assert results[0].name == "Alice Stylist"

    def test_search_no_match(self, temp_db):
        results = temp_db.staff.search("NoSuchPerson")
        assert results == []

    def test_search_partial_match(self, temp_db):
        temp_db.staff.get_or_create("张三丰")
        results = temp_db.staff.search("张三")
        assert len(results) >= 1


# ============================================================
# CustomerRepository Tests
# ============================================================
class TestCustomerRepository:
    """Tests for CustomerRepository."""

    def test_get_or_create_new_customer(self, temp_db):
        cust = temp_db.customers.get_or_create("Alice")
        assert cust is not None
        assert cust.name == "Alice"
        assert cust.id > 0

    def test_get_or_create_existing(self, temp_db):
        c1 = temp_db.customers.get_or_create("Alice")
        c2 = temp_db.customers.get_or_create("Alice")
        assert c1.id == c2.id

    def test_get_or_create_with_session(self, temp_db):
        with temp_db.get_session() as session:
            cust = temp_db.customers.get_or_create("SessCust", session=session)
            assert cust.id is not None
            session.commit()

    def test_search_by_name(self, temp_db):
        temp_db.customers.get_or_create("段老师")
        results = temp_db.customers.search("段老师")
        assert len(results) == 1
        assert results[0].name == "段老师"

    def test_search_by_phone(self, temp_db):
        cust = temp_db.customers.get_or_create("PhoneUser")
        # Manually set phone
        with temp_db.get_session() as session:
            row = session.query(Customer).filter_by(id=cust.id).first()
            row.phone = "13800001111"
            session.commit()

        results = temp_db.customers.search("1380000")
        assert len(results) == 1
        assert results[0].name == "PhoneUser"

    def test_search_no_match(self, temp_db):
        results = temp_db.customers.search("NonexistentPerson")
        assert results == []

    def test_unicode_names(self, temp_db):
        """Chinese characters and emoji should be handled."""
        cust = temp_db.customers.get_or_create("用户🚀")
        assert cust.name == "用户🚀"

    def test_long_name(self, temp_db):
        name = "A" * 50
        cust = temp_db.customers.get_or_create(name)
        assert cust.name == name


# ============================================================
# ServiceTypeRepository Tests
# ============================================================
class TestServiceTypeRepository:
    """Tests for ServiceTypeRepository."""

    def test_get_or_create_new(self, temp_db):
        st = temp_db.service_types.get_or_create(
            "头疗", default_price=30.0, category="therapy"
        )
        assert st is not None
        assert st.name == "头疗"
        assert float(st.default_price) == 30.0
        assert st.category == "therapy"

    def test_get_or_create_existing(self, temp_db):
        st1 = temp_db.service_types.get_or_create("理疗", default_price=198.0)
        st2 = temp_db.service_types.get_or_create("理疗")
        assert st1.id == st2.id

    def test_get_or_create_with_session(self, temp_db):
        with temp_db.get_session() as session:
            st = temp_db.service_types.get_or_create(
                "SessService", session=session
            )
            assert st.id is not None
            session.commit()

    def test_get_by_category(self, temp_db):
        temp_db.service_types.get_or_create("Haircut", category="hair")
        temp_db.service_types.get_or_create("DyeHair", category="hair")
        temp_db.service_types.get_or_create("Massage", category="therapy")

        hair_services = temp_db.service_types.get_by_category("hair")
        assert len(hair_services) == 2
        assert all(s.category == "hair" for s in hair_services)

    def test_get_by_category_empty(self, temp_db):
        results = temp_db.service_types.get_by_category("nonexistent")
        assert results == []


# ============================================================
# ProductRepository Tests
# ============================================================
class TestProductRepository:
    """Tests for ProductRepository."""

    def test_get_or_create_new(self, temp_db):
        product = temp_db.products.get_or_create(
            "蛋白粉", category="supplement", unit_price=200.0
        )
        assert product is not None
        assert product.name == "蛋白粉"
        assert product.category == "supplement"

    def test_get_or_create_existing(self, temp_db):
        p1 = temp_db.products.get_or_create("Shampoo")
        p2 = temp_db.products.get_or_create("Shampoo")
        assert p1.id == p2.id

    def test_get_or_create_with_session(self, temp_db):
        with temp_db.get_session() as session:
            p = temp_db.products.get_or_create("SessProduct", session=session)
            assert p.id is not None
            session.commit()

    def test_update_stock_increase(self, temp_db):
        product = temp_db.products.get_or_create("StockTest")
        updated = temp_db.products.update_stock(product.id, 20)
        assert updated is not None
        assert updated.stock_quantity == 20

    def test_update_stock_decrease(self, temp_db):
        product = temp_db.products.get_or_create("StockDec")
        temp_db.products.update_stock(product.id, 50)
        updated = temp_db.products.update_stock(product.id, -10)
        assert updated.stock_quantity == 40

    def test_update_stock_nonexistent(self, temp_db):
        result = temp_db.products.update_stock(99999, 10)
        assert result is None

    def test_get_low_stock(self, temp_db):
        # Default stock_quantity=0, low_stock_threshold=10 → always low
        product = temp_db.products.get_or_create("LowStock")
        low = temp_db.products.get_low_stock()
        assert any(p.id == product.id for p in low)

    def test_get_low_stock_excludes_well_stocked(self, temp_db):
        product = temp_db.products.get_or_create("WellStocked")
        temp_db.products.update_stock(product.id, 100)
        low = temp_db.products.get_low_stock()
        assert not any(p.id == product.id for p in low)

    def test_update_stock_with_session(self, temp_db):
        product = temp_db.products.get_or_create("SessStock")
        with temp_db.get_session() as session:
            updated = temp_db.products.update_stock(
                product.id, 15, session=session
            )
            assert updated.stock_quantity == 15
            session.commit()


# ============================================================
# ChannelRepository Tests
# ============================================================
class TestChannelRepository:
    """Tests for ChannelRepository."""

    def test_get_or_create_new(self, temp_db):
        ch = temp_db.channels.get_or_create(
            "美团", "platform", commission_rate=15.0
        )
        assert ch is not None
        assert ch.name == "美团"
        assert ch.channel_type == "platform"
        assert float(ch.commission_rate) == 15.0

    def test_get_or_create_existing(self, temp_db):
        ch1 = temp_db.channels.get_or_create("美团", "platform")
        ch2 = temp_db.channels.get_or_create("美团", "platform")
        assert ch1.id == ch2.id

    def test_get_or_create_with_contact(self, temp_db):
        ch = temp_db.channels.get_or_create(
            "李哥", "external",
            contact_info="13900139000",
            commission_rate=10.0,
        )
        assert ch.contact_info == "13900139000"

    def test_get_or_create_with_session(self, temp_db):
        with temp_db.get_session() as session:
            ch = temp_db.channels.get_or_create(
                "SessChannel", "external", session=session
            )
            assert ch.id is not None
            session.commit()

    def test_get_active_channels_all(self, temp_db):
        temp_db.channels.get_or_create("Ch1", "platform")
        temp_db.channels.get_or_create("Ch2", "external")
        channels = temp_db.channels.get_active_channels()
        assert len(channels) >= 2

    def test_get_active_channels_by_type(self, temp_db):
        temp_db.channels.get_or_create("Platform1", "platform")
        temp_db.channels.get_or_create("External1", "external")
        platforms = temp_db.channels.get_active_channels("platform")
        assert all(c.channel_type == "platform" for c in platforms)

    def test_get_active_channels_excludes_inactive(self, temp_db):
        ch = temp_db.channels.get_or_create("Inactive", "external")
        with temp_db.get_session() as session:
            row = session.query(ReferralChannel).filter_by(id=ch.id).first()
            row.is_active = False
            session.commit()

        active = temp_db.channels.get_active_channels(is_active=True)
        assert not any(c.id == ch.id for c in active)

    def test_get_active_channels_include_all(self, temp_db):
        ch = temp_db.channels.get_or_create("AllCheck", "external")
        with temp_db.get_session() as session:
            row = session.query(ReferralChannel).filter_by(id=ch.id).first()
            row.is_active = False
            session.commit()

        all_channels = temp_db.channels.get_active_channels(is_active=None)
        assert any(c.id == ch.id for c in all_channels)

    def test_default_channel_type_is_external(self, temp_db):
        """Default channel_type parameter is 'external'."""
        ch = temp_db.channels.get_or_create("DefaultType")
        assert ch.channel_type == "external"

