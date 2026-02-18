"""DatabaseManager facade tests.

Tests for all convenience methods on DatabaseManager:
- save_raw_message / update_parse_status
- save_service_record / save_product_sale / save_membership
- save_daily_summary
- get_daily_records (combined service + product sale)
- get_staff_list (active_only / all)
- get_customer_info (with memberships)
- get_channel_list (with type filter)
- execute_raw_sql
- Property accessors (database_url, engine, is_async)
- Sub-repository attribute access
"""
from datetime import date, datetime

import pytest

from database.models import DailySummary, ServiceRecord
from tests.database.conftest import make_raw_message


class TestManagerProperties:
    """Test DatabaseManager property accessors."""

    def test_database_url_property(self, temp_db):
        assert temp_db.database_url.startswith("sqlite:///")

    def test_engine_property(self, temp_db):
        assert temp_db.engine is not None

    def test_is_async_property(self, temp_db):
        assert temp_db.is_async is False

    def test_sub_repositories_accessible(self, temp_db):
        """All sub-repositories should be accessible attributes."""
        assert temp_db.staff is not None
        assert temp_db.customers is not None
        assert temp_db.service_types is not None
        assert temp_db.products is not None
        assert temp_db.channels is not None
        assert temp_db.service_records is not None
        assert temp_db.product_sales is not None
        assert temp_db.memberships is not None
        assert temp_db.messages is not None
        assert temp_db.summaries is not None
        assert temp_db.plugins is not None


class TestManagerSaveRawMessage:
    """Test DatabaseManager.save_raw_message()."""

    def test_save_and_dedup(self, temp_db):
        payload = {
            "msg_id": "dm-msg-1",
            "sender_nickname": "user",
            "content": "hello",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        }
        id1 = temp_db.save_raw_message(payload)
        id2 = temp_db.save_raw_message(payload)
        assert id1 == id2


class TestManagerUpdateParseStatus:
    """Test DatabaseManager.update_parse_status()."""

    def test_update_status(self, temp_db):
        msg_id = make_raw_message(temp_db, "dm-parse")
        temp_db.update_parse_status(msg_id, "parsed", result={"n": 1})

        from database.models import RawMessage
        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter_by(id=msg_id).first()
            assert msg.parse_status == "parsed"
            assert msg.parse_result == {"n": 1}


class TestManagerSaveServiceRecord:
    """Test DatabaseManager.save_service_record()."""

    def test_basic_save(self, temp_db):
        msg_id = make_raw_message(temp_db, "dm-sr")
        record_id = temp_db.save_service_record(
            {
                "customer_name": "张三",
                "service_or_product": "头疗",
                "date": "2024-01-28",
                "amount": 198,
            },
            msg_id,
        )
        assert record_id > 0


class TestManagerSaveProductSale:
    """Test DatabaseManager.save_product_sale()."""

    def test_basic_save(self, temp_db):
        msg_id = make_raw_message(temp_db, "dm-ps")
        sale_id = temp_db.save_product_sale(
            {
                "service_or_product": "蛋白粉",
                "date": "2024-01-28",
                "amount": 200,
            },
            msg_id,
        )
        assert sale_id > 0


class TestManagerSaveMembership:
    """Test DatabaseManager.save_membership()."""

    def test_basic_save(self, temp_db):
        msg_id = make_raw_message(temp_db, "dm-mem")
        mid = temp_db.save_membership(
            {
                "customer_name": "会员用户",
                "date": "2024-01-01",
                "amount": 1000,
            },
            msg_id,
        )
        assert mid > 0


class TestManagerSaveDailySummary:
    """Test DatabaseManager.save_daily_summary()."""

    def test_basic_save(self, temp_db):
        sid = temp_db.save_daily_summary(
            date(2024, 1, 28),
            {"total_service_revenue": 500, "service_count": 3},
        )
        assert sid > 0

    def test_upsert(self, temp_db):
        sid1 = temp_db.save_daily_summary(
            date(2024, 1, 28),
            {"total_service_revenue": 500},
        )
        sid2 = temp_db.save_daily_summary(
            date(2024, 1, 28),
            {"total_service_revenue": 600},
        )
        assert sid1 == sid2


class TestManagerGetDailyRecords:
    """Test DatabaseManager.get_daily_records()."""

    def test_combines_services_and_sales(self, temp_db):
        msg1 = make_raw_message(temp_db, "dm-daily-sr")
        msg2 = make_raw_message(temp_db, "dm-daily-ps")

        temp_db.save_service_record(
            {
                "customer_name": "Alice",
                "service_or_product": "Therapy",
                "date": "2024-01-28",
                "amount": 100,
            },
            msg1,
        )
        temp_db.save_product_sale(
            {
                "service_or_product": "Product",
                "date": "2024-01-28",
                "amount": 50,
            },
            msg2,
        )

        records = temp_db.get_daily_records(date(2024, 1, 28))
        assert len(records) == 2
        types = {r["type"] for r in records}
        assert types == {"service", "product_sale"}

    def test_accepts_string_date(self, temp_db):
        msg_id = make_raw_message(temp_db, "dm-daily-str")
        temp_db.save_service_record(
            {
                "customer_name": "Alice",
                "service_or_product": "Therapy",
                "date": "2024-01-28",
                "amount": 100,
            },
            msg_id,
        )
        records = temp_db.get_daily_records("2024-01-28")
        assert len(records) >= 1

    def test_empty_date(self, temp_db):
        records = temp_db.get_daily_records(date(2099, 1, 1))
        assert records == []


class TestManagerGetStaffList:
    """Test DatabaseManager.get_staff_list()."""

    def test_active_only(self, temp_db):
        temp_db.staff.get_or_create("ActiveEmp")
        inactive = temp_db.staff.get_or_create("InactiveEmp")
        temp_db.staff.deactivate(inactive.id)

        staff_list = temp_db.get_staff_list(active_only=True)
        assert all(s["is_active"] for s in staff_list)
        assert any(s["name"] == "ActiveEmp" for s in staff_list)
        assert not any(s["name"] == "InactiveEmp" for s in staff_list)

    def test_include_inactive(self, temp_db):
        temp_db.staff.get_or_create("Active2")
        inactive2 = temp_db.staff.get_or_create("Inactive2")
        temp_db.staff.deactivate(inactive2.id)

        all_staff = temp_db.get_staff_list(active_only=False)
        assert any(s["name"] == "Active2" for s in all_staff)
        assert any(s["name"] == "Inactive2" for s in all_staff)

    def test_staff_list_dict_format(self, temp_db):
        """Verify all expected keys in returned dicts."""
        temp_db.staff.get_or_create("FmtStaff")
        staff_list = temp_db.get_staff_list()
        s = staff_list[0]
        expected_keys = {"id", "name", "role", "commission_rate", "is_active"}
        assert expected_keys.issubset(set(s.keys()))


class TestManagerGetCustomerInfo:
    """Test DatabaseManager.get_customer_info()."""

    def test_found_with_membership(self, temp_db):
        msg_id = make_raw_message(temp_db, "dm-ci-mem")
        temp_db.save_membership(
            {
                "customer_name": "InfoCustomer",
                "date": "2024-01-01",
                "amount": 1000,
                "card_type": "VIP",
            },
            msg_id,
        )

        info = temp_db.get_customer_info("InfoCustomer")
        assert info is not None
        assert info["name"] == "InfoCustomer"
        assert len(info["memberships"]) == 1
        assert info["memberships"][0]["card_type"] == "VIP"

    def test_found_without_membership(self, temp_db):
        temp_db.customers.get_or_create("NoMemCustomer")
        info = temp_db.get_customer_info("NoMemCustomer")
        assert info is not None
        assert info["memberships"] == []

    def test_not_found(self, temp_db):
        result = temp_db.get_customer_info("NonexistentPerson")
        assert result is None

    def test_partial_name_search(self, temp_db):
        temp_db.customers.get_or_create("张三丰")
        info = temp_db.get_customer_info("张三")
        assert info is not None
        assert info["name"] == "张三丰"

    def test_customer_info_dict_format(self, temp_db):
        """Verify all expected keys."""
        temp_db.customers.get_or_create("FmtCust")
        info = temp_db.get_customer_info("FmtCust")
        expected_keys = {"id", "name", "phone", "notes", "memberships"}
        assert expected_keys.issubset(set(info.keys()))


class TestManagerGetChannelList:
    """Test DatabaseManager.get_channel_list()."""

    def test_all_channels(self, temp_db):
        temp_db.channels.get_or_create("Ch1", "platform")
        temp_db.channels.get_or_create("Ch2", "external")
        channels = temp_db.get_channel_list()
        assert len(channels) >= 2

    def test_filter_by_type(self, temp_db):
        temp_db.channels.get_or_create("Platform1", "platform")
        temp_db.channels.get_or_create("External1", "external")
        platforms = temp_db.get_channel_list("platform")
        assert all(c["channel_type"] == "platform" for c in platforms)

    def test_channel_dict_format(self, temp_db):
        temp_db.channels.get_or_create("FmtCh", "platform", commission_rate=15)
        channels = temp_db.get_channel_list()
        c = [ch for ch in channels if ch["name"] == "FmtCh"][0]
        expected_keys = {"id", "name", "channel_type", "commission_rate", "commission_type", "is_active"}
        assert expected_keys.issubset(set(c.keys()))


class TestManagerExecuteRawSQL:
    """Test DatabaseManager.execute_raw_sql()."""

    def test_select_count(self, temp_db):
        temp_db.customers.get_or_create("SQLUser")
        result = temp_db.execute_raw_sql("SELECT COUNT(*) FROM customers")
        assert result.scalar() >= 1

    def test_with_params(self, temp_db):
        temp_db.customers.get_or_create("ParamUser")
        result = temp_db.execute_raw_sql(
            "SELECT COUNT(*) FROM customers WHERE name = :name",
            {"name": "ParamUser"},
        )
        assert result.scalar() == 1

