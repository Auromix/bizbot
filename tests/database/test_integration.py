"""End-to-end integration tests with realistic business scenarios.

Tests realistic workflows that span multiple repositories:
- Hair salon: message → parse → record → query → summary
- Gym: membership → training → product sale → plugin data
- Multi-business-type: various record types in one day
- Data flow: message → service record → daily records → summary
"""
from datetime import date, datetime

from database.models import ServiceRecord, ReferralChannel
from tests.database.conftest import make_raw_message


class TestHairSalonScenario:
    """Hair salon business scenario tests."""

    def test_daily_service_flow(self, temp_db):
        """Full daily flow: channel setup → message → service → query."""
        # Setup referral channel
        meituan = temp_db.channels.get_or_create(
            "美团", "platform", commission_rate=15.0
        )
        temp_db.staff.get_or_create("Tony", "tony_hair")

        # Save raw message
        msg_id = temp_db.save_raw_message({
            "msg_id": "hair-daily-1",
            "sender_nickname": "assistant",
            "content": "Alice haircut 80",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        })

        # Save service record with referral channel
        rid = temp_db.save_service_record(
            {
                "customer_name": "Alice",
                "service_or_product": "Haircut",
                "date": "2024-01-28",
                "amount": 80,
                "commission": 12,
                "referral_channel_id": meituan.id,
                "net_amount": 68,
                "recorder_nickname": "Tony",
            },
            msg_id,
        )
        assert rid > 0

        # Update parse status
        temp_db.update_parse_status(msg_id, "parsed", result={"records": 1})

        # Query records
        records = temp_db.get_daily_records(date(2024, 1, 28))
        assert len(records) == 1
        assert records[0]["type"] == "service"
        assert records[0]["amount"] == 80.0
        assert records[0]["customer_name"] == "Alice"

    def test_membership_and_summary(self, temp_db):
        """Membership creation + daily summary."""
        msg_id = temp_db.save_raw_message({
            "msg_id": "hair-member-1",
            "sender_nickname": "tony",
            "content": "Alice topup 1000",
            "timestamp": datetime(2024, 1, 1, 9, 0, 0),
        })
        mid = temp_db.save_membership(
            {
                "customer_name": "Alice",
                "date": "2024-01-01",
                "amount": 1000,
                "card_type": "VIP",
            },
            msg_id,
        )
        assert mid > 0

        # Create daily summary
        sid = temp_db.save_daily_summary(
            date(2024, 1, 28),
            {
                "total_service_revenue": 280,
                "service_count": 2,
                "summary_text": "2 services today",
            },
        )
        assert sid > 0

        # Check customer info includes membership
        info = temp_db.get_customer_info("Alice")
        assert info is not None
        assert len(info["memberships"]) == 1
        assert info["memberships"][0]["card_type"] == "VIP"

    def test_multiple_services_same_day(self, temp_db):
        """Multiple service records on the same day."""
        msg1 = make_raw_message(temp_db, "hair-multi-1")
        msg2 = make_raw_message(temp_db, "hair-multi-2")
        msg3 = make_raw_message(temp_db, "hair-multi-3")

        temp_db.save_service_record(
            {
                "customer_name": "Alice",
                "service_or_product": "Haircut",
                "date": "2024-01-28",
                "amount": 80,
            },
            msg1,
        )
        temp_db.save_service_record(
            {
                "customer_name": "Bob",
                "service_or_product": "DyeHair",
                "date": "2024-01-28",
                "amount": 200,
                "commission": 30,
                "commission_to": "李哥",
            },
            msg2,
        )
        temp_db.save_product_sale(
            {
                "service_or_product": "Shampoo",
                "date": "2024-01-28",
                "amount": 68,
                "customer_name": "Alice",
            },
            msg3,
        )

        records = temp_db.get_daily_records("2024-01-28")
        assert len(records) == 3
        service_records = [r for r in records if r["type"] == "service"]
        sale_records = [r for r in records if r["type"] == "product_sale"]
        assert len(service_records) == 2
        assert len(sale_records) == 1


class TestGymScenario:
    """Gym business scenario tests."""

    def test_member_training_and_product_sale(self, temp_db):
        """Full gym flow: membership → training → product sale."""
        # Setup
        trainer = temp_db.staff.get_or_create("Coach Li", "coach_li")
        channel = temp_db.channels.get_or_create(
            "Coach Li", "internal", commission_rate=40.0
        )

        # Create membership
        mem_msg = make_raw_message(temp_db, "gym-mem")
        membership_id = temp_db.save_membership(
            {
                "customer_name": "Bob",
                "date": "2024-01-01",
                "amount": 3000,
                "card_type": "Annual",
                "remaining_sessions": 50,
            },
            mem_msg,
        )

        # Record training session
        train_msg = make_raw_message(temp_db, "gym-train")
        rid = temp_db.save_service_record(
            {
                "customer_name": "Bob",
                "service_or_product": "Personal Training",
                "date": "2024-01-28",
                "amount": 300,
                "commission": 120,
                "referral_channel_id": channel.id,
                "membership_id": membership_id,
                "recorder_nickname": "Coach Li",
            },
            train_msg,
        )

        # Deduct session
        temp_db.memberships.deduct_session(membership_id, 1)

        # Record product sale
        sale_msg = make_raw_message(temp_db, "gym-sale")
        sale_id = temp_db.save_product_sale(
            {
                "service_or_product": "Protein Powder",
                "date": "2024-01-28",
                "amount": 200,
                "quantity": 1,
                "customer_name": "Bob",
            },
            sale_msg,
        )

        assert rid > 0
        assert sale_id > 0

        # Verify daily records
        records = temp_db.get_daily_records("2024-01-28")
        assert len(records) == 2

        # Verify membership sessions deducted
        from database.models import Membership
        with temp_db.get_session() as session:
            m = session.query(Membership).filter_by(id=membership_id).first()
            assert m.remaining_sessions == 49

    def test_plugin_data_body_stats(self, temp_db):
        """Store and retrieve gym-specific plugin data."""
        customer = temp_db.customers.get_or_create("GymUser")

        # Store body stats
        temp_db.plugins.save("gym", "customer", customer.id, "body_fat", 18.5)
        temp_db.plugins.save("gym", "customer", customer.id, "weight", 75.0)
        temp_db.plugins.save("gym", "customer", customer.id, "height", 180)

        # Retrieve individual
        assert temp_db.plugins.get("gym", "customer", customer.id, "body_fat") == 18.5

        # Retrieve all
        all_data = temp_db.plugins.get("gym", "customer", customer.id)
        assert all_data == {"body_fat": 18.5, "weight": 75.0, "height": 180}

        # Update
        temp_db.plugins.save("gym", "customer", customer.id, "body_fat", 17.8)
        assert temp_db.plugins.get("gym", "customer", customer.id, "body_fat") == 17.8

    def test_points_history(self, temp_db):
        """Store points history as plugin data."""
        customer = temp_db.customers.get_or_create("PointsGym")
        history = [
            {"date": "2024-01-01", "points": 300, "reason": "signup"},
            {"date": "2024-01-28", "points": 30, "reason": "training"},
        ]
        temp_db.plugins.save("gym_points", "customer", customer.id, "history", history)

        result = temp_db.plugins.get("gym_points", "customer", customer.id, "history")
        assert len(result) == 2
        assert result[0]["points"] == 300


class TestTherapyStoreScenario:
    """Therapy store (理疗馆) scenario tests."""

    def test_full_day_operations(self, temp_db):
        """Full day: messages → parse → records → summary."""
        # Morning message
        msg1_id = temp_db.save_raw_message({
            "msg_id": "therapy-1",
            "sender_nickname": "小助手",
            "content": "1.28段老师头疗30",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        })
        temp_db.save_service_record(
            {
                "customer_name": "段老师",
                "service_or_product": "头疗",
                "date": "2024-01-28",
                "amount": 30,
            },
            msg1_id,
        )
        temp_db.update_parse_status(msg1_id, "parsed")

        # Afternoon message with commission
        msg2_id = temp_db.save_raw_message({
            "msg_id": "therapy-2",
            "sender_nickname": "小助手",
            "content": "1.28姚老师理疗198-20李哥178",
            "timestamp": datetime(2024, 1, 28, 14, 0, 0),
        })
        temp_db.save_service_record(
            {
                "customer_name": "姚老师",
                "service_or_product": "理疗",
                "date": "2024-01-28",
                "amount": 198,
                "commission": 20,
                "commission_to": "李哥",
                "net_amount": 178,
            },
            msg2_id,
        )
        temp_db.update_parse_status(msg2_id, "parsed")

        # Product sale
        msg3_id = temp_db.save_raw_message({
            "msg_id": "therapy-3",
            "sender_nickname": "小助手",
            "content": "泡脚液销售",
            "timestamp": datetime(2024, 1, 28, 16, 0, 0),
        })
        temp_db.save_product_sale(
            {
                "service_or_product": "泡脚液",
                "date": "2024-01-28",
                "amount": 68,
                "customer_name": "周老师",
            },
            msg3_id,
        )

        # Query all records
        records = temp_db.get_daily_records("2024-01-28")
        assert len(records) == 3

        # Generate and save summary
        service_total = sum(
            r["amount"] for r in records if r["type"] == "service"
        )
        product_total = sum(
            r["total_amount"] for r in records if r["type"] == "product_sale"
        )
        temp_db.save_daily_summary(
            date(2024, 1, 28),
            {
                "total_service_revenue": service_total,
                "total_product_revenue": product_total,
                "service_count": 2,
                "product_sale_count": 1,
                "net_revenue": service_total + product_total - 20,
            },
        )

        summary = temp_db.summaries.get_by_date(date(2024, 1, 28))
        assert summary is not None
        assert float(summary.total_service_revenue) == 228
        assert float(summary.total_product_revenue) == 68

    def test_membership_with_deduction(self, temp_db):
        """Membership flow: create → use → deduct."""
        msg1 = make_raw_message(temp_db, "therapy-mem-create")
        mid = temp_db.save_membership(
            {
                "customer_name": "VIP客户",
                "date": "2024-01-01",
                "amount": 2000,
                "card_type": "理疗卡",
                "remaining_sessions": 20,
            },
            msg1,
        )

        # Use membership for service
        msg2 = make_raw_message(temp_db, "therapy-mem-use")
        temp_db.save_service_record(
            {
                "customer_name": "VIP客户",
                "service_or_product": "理疗",
                "date": "2024-01-28",
                "amount": 198,
                "membership_id": mid,
            },
            msg2,
        )

        # Deduct
        temp_db.memberships.deduct_balance(mid, 198)
        temp_db.memberships.deduct_session(mid, 1)
        temp_db.memberships.add_points(mid, 20)

        # Verify final state
        info = temp_db.get_customer_info("VIP客户")
        assert info is not None
        m = info["memberships"][0]
        assert m["balance"] == 1802.0
        assert m["remaining_sessions"] == 19
        assert m["points"] == 20


class TestDataFlowIntegration:
    """Test the complete data flow from message to summary."""

    def test_message_to_summary_pipeline(self, temp_db):
        """Simulate the full pipeline: message → parse → record → summary."""
        # Step 1: Save raw message
        msg_id = temp_db.save_raw_message({
            "msg_id": "pipeline-1",
            "sender_nickname": "recorder",
            "content": "张三 头疗 30",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
            "is_business": True,
        })

        # Step 2: Save parsed record
        record_id = temp_db.save_service_record(
            {
                "customer_name": "张三",
                "service_or_product": "头疗",
                "date": "2024-01-28",
                "amount": 30,
                "confidence": 0.95,
                "recorder_nickname": "recorder",
            },
            msg_id,
        )

        # Step 3: Update parse status
        temp_db.update_parse_status(
            msg_id, "parsed",
            result={"records": [{"id": record_id, "type": "service"}]},
        )

        # Step 4: Confirm record
        temp_db.service_records.confirm(record_id)

        # Step 5: Generate summary
        records = temp_db.get_daily_records("2024-01-28")
        temp_db.save_daily_summary(
            date(2024, 1, 28),
            {
                "total_service_revenue": sum(
                    r.get("amount", 0) or r.get("total_amount", 0) for r in records
                ),
                "service_count": len([r for r in records if r["type"] == "service"]),
            },
        )

        # Verify
        summary = temp_db.summaries.get_by_date(date(2024, 1, 28))
        assert summary is not None
        assert float(summary.total_service_revenue) == 30
        assert summary.service_count == 1

    def test_correction_flow(self, temp_db):
        """Simulate correction: original record → correction → verify."""
        msg1 = make_raw_message(temp_db, "correct-orig")
        rid = temp_db.save_service_record(
            {
                "customer_name": "错误客户",
                "service_or_product": "头疗",
                "date": "2024-01-28",
                "amount": 100,
            },
            msg1,
        )

        # Save correction
        msg2 = make_raw_message(temp_db, "correct-fix")
        correction_id = temp_db.messages.save_correction({
            "original_record_type": "service_records",
            "original_record_id": rid,
            "correction_type": "amount_change",
            "old_value": {"amount": 100},
            "new_value": {"amount": 198},
            "reason": "金额录入错误",
            "raw_message_id": msg2,
        })
        assert correction_id > 0

        # Update original record
        temp_db.service_records.update_by_id(ServiceRecord, rid, amount=198)

        with temp_db.get_session() as session:
            record = session.query(ServiceRecord).filter_by(id=rid).first()
            assert float(record.amount) == 198


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_zero_amount_service(self, temp_db):
        msg_id = make_raw_message(temp_db, "edge-zero")
        rid = temp_db.save_service_record(
            {
                "customer_name": "FreeTrial",
                "service_or_product": "Trial",
                "date": "2024-01-28",
                "amount": 0,
            },
            msg_id,
        )
        assert rid > 0

    def test_special_characters_in_names(self, temp_db):
        """Handle various special characters."""
        temp_db.customers.get_or_create("O'Brien")
        temp_db.customers.get_or_create("张三-VIP")
        temp_db.customers.get_or_create("用户(test)")

        results = temp_db.customers.search("O'Brien")
        assert len(results) == 1

    def test_empty_extra_data(self, temp_db):
        msg_id = make_raw_message(temp_db, "edge-empty-extra")
        rid = temp_db.save_service_record(
            {
                "customer_name": "EmptyExtra",
                "service_or_product": "Test",
                "date": "2024-01-28",
                "amount": 100,
                "extra_data": {},
            },
            msg_id,
        )
        with temp_db.get_session() as session:
            r = session.query(ServiceRecord).filter_by(id=rid).first()
            assert r.extra_data == {}

    def test_concurrent_customer_creation(self, temp_db):
        """Multiple get_or_create calls for same customer should be idempotent."""
        c1 = temp_db.customers.get_or_create("SharedCustomer")
        c2 = temp_db.customers.get_or_create("SharedCustomer")
        c3 = temp_db.customers.get_or_create("SharedCustomer")
        assert c1.id == c2.id == c3.id

