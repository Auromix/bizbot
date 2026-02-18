"""System repository tests.

Tests for:
- MessageRepository: save_raw_message (with dedup), update_parse_status, save_correction
- SummaryRepository: save (upsert), get_by_date
- PluginRepository: save (upsert), get (single/all), delete (single/all)
"""
from datetime import date, datetime

import pytest

from database.models import (
    RawMessage, Correction, DailySummary, PluginData,
)
from tests.database.conftest import make_raw_message


# ============================================================
# MessageRepository Tests
# ============================================================
class TestMessageRepository:
    """Tests for MessageRepository."""

    def test_save_raw_message_basic(self, temp_db):
        msg_id = temp_db.messages.save_raw_message({
            "msg_id": "wx-001",
            "sender_nickname": "User1",
            "content": "Hello",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        })
        assert msg_id > 0

    def test_save_raw_message_all_fields(self, temp_db):
        msg_id = temp_db.messages.save_raw_message({
            "msg_id": "wx-full",
            "sender_nickname": "FullUser",
            "content": "Full message",
            "msg_type": "text",
            "group_id": "group-001",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
            "is_at_bot": True,
            "is_business": True,
            "parse_status": "pending",
        })

        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter_by(id=msg_id).first()
            assert msg.group_id == "group-001"
            assert msg.is_at_bot is True
            assert msg.is_business is True

    def test_save_raw_message_dedup(self, temp_db):
        """Duplicate msg_id should return the existing ID."""
        payload = {
            "msg_id": "wx-dup",
            "sender_nickname": "user",
            "content": "hello",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        }
        first_id = temp_db.messages.save_raw_message(payload)
        second_id = temp_db.messages.save_raw_message(payload)
        assert first_id == second_id

    def test_save_raw_message_without_msg_id(self, temp_db):
        """Message without msg_id should be saved (no dedup)."""
        msg_id = temp_db.messages.save_raw_message({
            "sender_nickname": "NoIDUser",
            "content": "No ID",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        })
        assert msg_id > 0

    def test_save_raw_message_default_msg_type(self, temp_db):
        msg_id = temp_db.messages.save_raw_message({
            "msg_id": "wx-defaults",
            "sender_nickname": "user",
            "content": "test",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        })
        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter_by(id=msg_id).first()
            assert msg.msg_type == "text"
            assert msg.parse_status == "pending"
            assert msg.is_at_bot is False

    def test_update_parse_status(self, temp_db):
        msg_id = make_raw_message(temp_db, "parse-update")
        temp_db.messages.update_parse_status(msg_id, "parsed")

        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter_by(id=msg_id).first()
            assert msg.parse_status == "parsed"

    def test_update_parse_status_with_result(self, temp_db):
        msg_id = make_raw_message(temp_db, "parse-result")
        temp_db.messages.update_parse_status(
            msg_id, "parsed",
            result={"records": 2, "type": "service"},
        )

        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter_by(id=msg_id).first()
            assert msg.parse_status == "parsed"
            assert msg.parse_result["records"] == 2

    def test_update_parse_status_with_error(self, temp_db):
        msg_id = make_raw_message(temp_db, "parse-error")
        temp_db.messages.update_parse_status(
            msg_id, "failed",
            error="LLM timeout",
        )

        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter_by(id=msg_id).first()
            assert msg.parse_status == "failed"
            assert msg.parse_error == "LLM timeout"

    def test_update_parse_status_nonexistent(self, temp_db):
        """Updating non-existent message should not raise."""
        temp_db.messages.update_parse_status(99999, "parsed")
        # No error expected

    def test_save_correction(self, temp_db):
        msg_id = make_raw_message(temp_db, "correction-msg")
        correction_id = temp_db.messages.save_correction({
            "original_record_type": "service_records",
            "original_record_id": 10,
            "correction_type": "amount_change",
            "old_value": {"amount": 100},
            "new_value": {"amount": 120},
            "reason": "手动修正",
            "raw_message_id": msg_id,
        })
        assert correction_id > 0

        with temp_db.get_session() as session:
            c = session.query(Correction).filter_by(id=correction_id).first()
            assert c.original_record_type == "service_records"
            assert c.correction_type == "amount_change"
            assert c.old_value["amount"] == 100
            assert c.new_value["amount"] == 120
            assert c.reason == "手动修正"
            assert c.raw_message_id == msg_id

    def test_save_correction_minimal(self, temp_db):
        """Correction with minimal fields."""
        correction_id = temp_db.messages.save_correction({
            "correction_type": "delete",
        })
        assert correction_id > 0


# ============================================================
# SummaryRepository Tests
# ============================================================
class TestSummaryRepository:
    """Tests for SummaryRepository."""

    def test_save_new_summary(self, temp_db):
        sid = temp_db.summaries.save(
            date(2024, 1, 28),
            {
                "total_service_revenue": 500,
                "service_count": 3,
                "summary_text": "Good day",
            },
        )
        assert sid > 0

    def test_save_upsert_updates_existing(self, temp_db):
        """Saving to same date should update, not create a new record."""
        sid1 = temp_db.summaries.save(
            date(2024, 1, 28),
            {"total_service_revenue": 500, "service_count": 3},
        )
        sid2 = temp_db.summaries.save(
            date(2024, 1, 28),
            {"total_service_revenue": 600},
        )

        assert sid1 == sid2

        with temp_db.get_session() as session:
            s = session.query(DailySummary).filter_by(id=sid1).first()
            # Updated field
            assert float(s.total_service_revenue) == 600
            # Previous field preserved
            assert s.service_count == 3

    def test_save_different_dates(self, temp_db):
        sid1 = temp_db.summaries.save(
            date(2024, 1, 28),
            {"service_count": 3},
        )
        sid2 = temp_db.summaries.save(
            date(2024, 1, 29),
            {"service_count": 5},
        )
        assert sid1 != sid2

    def test_save_all_fields(self, temp_db):
        sid = temp_db.summaries.save(
            date(2024, 1, 28),
            {
                "total_service_revenue": 1000,
                "total_product_revenue": 200,
                "total_commissions": 100,
                "net_revenue": 1100,
                "service_count": 5,
                "product_sale_count": 2,
                "new_members": 1,
                "membership_revenue": 3000,
                "summary_text": "Full report",
                "confirmed": True,
            },
        )

        with temp_db.get_session() as session:
            s = session.query(DailySummary).filter_by(id=sid).first()
            assert float(s.total_service_revenue) == 1000
            assert float(s.total_product_revenue) == 200
            assert s.service_count == 5
            assert s.new_members == 1
            assert s.confirmed is True

    def test_get_by_date(self, temp_db):
        temp_db.summaries.save(
            date(2024, 1, 28),
            {"service_count": 3},
        )
        summary = temp_db.summaries.get_by_date(date(2024, 1, 28))
        assert summary is not None
        assert summary.service_count == 3

    def test_get_by_date_not_found(self, temp_db):
        result = temp_db.summaries.get_by_date(date(2099, 1, 1))
        assert result is None


# ============================================================
# PluginRepository Tests
# ============================================================
class TestPluginRepository:
    """Tests for PluginRepository."""

    def test_save_new_data(self, temp_db):
        cust = temp_db.customers.get_or_create("PluginCust")
        pid = temp_db.plugins.save("gym", "customer", cust.id, "body_fat", 18.5)
        assert pid > 0

    def test_save_updates_existing(self, temp_db):
        """Saving same key should update value (upsert)."""
        cust = temp_db.customers.get_or_create("UpsertCust")
        pid1 = temp_db.plugins.save("gym", "customer", cust.id, "weight", 75)
        pid2 = temp_db.plugins.save("gym", "customer", cust.id, "weight", 80)
        assert pid1 == pid2

        value = temp_db.plugins.get("gym", "customer", cust.id, "weight")
        assert value == 80

    def test_get_single_key(self, temp_db):
        cust = temp_db.customers.get_or_create("SingleKey")
        temp_db.plugins.save("test", "customer", cust.id, "key1", "value1")
        result = temp_db.plugins.get("test", "customer", cust.id, "key1")
        assert result == "value1"

    def test_get_all_keys(self, temp_db):
        cust = temp_db.customers.get_or_create("AllKeys")
        temp_db.plugins.save("test", "customer", cust.id, "k1", "v1")
        temp_db.plugins.save("test", "customer", cust.id, "k2", "v2")
        result = temp_db.plugins.get("test", "customer", cust.id)
        assert result == {"k1": "v1", "k2": "v2"}

    def test_get_nonexistent_key(self, temp_db):
        result = temp_db.plugins.get("test", "customer", 99999, "nokey")
        assert result is None

    def test_get_nonexistent_all(self, temp_db):
        result = temp_db.plugins.get("test", "customer", 99999)
        assert result == {}

    def test_delete_single_key(self, temp_db):
        cust = temp_db.customers.get_or_create("DeleteKey")
        temp_db.plugins.save("test", "customer", cust.id, "k1", "v1")
        temp_db.plugins.save("test", "customer", cust.id, "k2", "v2")

        temp_db.plugins.delete("test", "customer", cust.id, "k1")
        result = temp_db.plugins.get("test", "customer", cust.id)
        assert result == {"k2": "v2"}

    def test_delete_all_keys(self, temp_db):
        cust = temp_db.customers.get_or_create("DeleteAll")
        temp_db.plugins.save("test", "customer", cust.id, "k1", "v1")
        temp_db.plugins.save("test", "customer", cust.id, "k2", "v2")

        temp_db.plugins.delete("test", "customer", cust.id)
        result = temp_db.plugins.get("test", "customer", cust.id)
        assert result == {}

    def test_delete_nonexistent(self, temp_db):
        """Deleting non-existent data should not raise."""
        temp_db.plugins.delete("test", "customer", 99999, "nokey")

    def test_save_complex_values(self, temp_db):
        """Plugin data should support nested JSON structures."""
        cust = temp_db.customers.get_or_create("Complex")
        nested = {"a": {"b": [1, 2, {"c": True}]}}
        temp_db.plugins.save("test", "customer", cust.id, "nested", nested)
        result = temp_db.plugins.get("test", "customer", cust.id, "nested")
        assert result == nested

    def test_save_numeric_value(self, temp_db):
        cust = temp_db.customers.get_or_create("Numeric")
        temp_db.plugins.save("gym", "customer", cust.id, "weight", 75.5)
        assert temp_db.plugins.get("gym", "customer", cust.id, "weight") == 75.5

    def test_save_list_value(self, temp_db):
        cust = temp_db.customers.get_or_create("ListVal")
        history = [
            {"date": "2024-01-01", "points": 300},
            {"date": "2024-01-28", "points": 30},
        ]
        temp_db.plugins.save("gym", "customer", cust.id, "history", history)
        result = temp_db.plugins.get("gym", "customer", cust.id, "history")
        assert len(result) == 2
        assert result[0]["points"] == 300

    def test_different_plugins_different_data(self, temp_db):
        """Different plugin_name values should be isolated."""
        cust = temp_db.customers.get_or_create("MultiPlugin")
        temp_db.plugins.save("gym", "customer", cust.id, "score", 90)
        temp_db.plugins.save("salon", "customer", cust.id, "score", 80)

        gym_score = temp_db.plugins.get("gym", "customer", cust.id, "score")
        salon_score = temp_db.plugins.get("salon", "customer", cust.id, "score")
        assert gym_score == 90
        assert salon_score == 80

    def test_different_entity_types(self, temp_db):
        """Different entity_type values should be isolated."""
        temp_db.plugins.save("test", "customer", 1, "tag", "cust_tag")
        temp_db.plugins.save("test", "employee", 1, "tag", "emp_tag")

        cust_tag = temp_db.plugins.get("test", "customer", 1, "tag")
        emp_tag = temp_db.plugins.get("test", "employee", 1, "tag")
        assert cust_tag == "cust_tag"
        assert emp_tag == "emp_tag"

