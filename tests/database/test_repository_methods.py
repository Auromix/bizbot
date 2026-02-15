"""Repository方法详细测试。

测试所有Repository方法的详细功能，包括边界情况、错误处理等。
"""
import pytest
from datetime import date, datetime

from db.repository import DatabaseRepository
from db.models import RawMessage
from tests.conftest import temp_db


class TestRepositoryMethods:
    """Repository方法详细测试类。"""
    
    def test_save_raw_message_deduplication(self, temp_db):
        """测试原始消息去重功能。"""
        msg_data = {
            "wechat_msg_id": "unique_msg_001",
            "sender_nickname": "测试用户",
            "content": "测试消息",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        }
        
        # 第一次保存
        msg_id1 = temp_db.save_raw_message(msg_data)
        assert msg_id1 > 0
        
        # 第二次保存相同消息（应该返回同一个ID）
        msg_id2 = temp_db.save_raw_message(msg_data)
        assert msg_id1 == msg_id2
        
        # 验证数据库中只有一条记录
        with temp_db.get_session() as session:
            count = session.query(RawMessage).filter(
                RawMessage.wechat_msg_id == "unique_msg_001"
            ).count()
            assert count == 1
    
    def test_save_raw_message_all_fields(self, temp_db):
        """测试保存原始消息的所有字段。"""
        msg_data = {
            "wechat_msg_id": "msg_all_fields",
            "sender_nickname": "完整用户",
            "sender_wechat_id": "wechat_123",
            "content": "完整消息内容",
            "msg_type": "text",
            "group_id": "group_001",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
            "is_at_bot": True,
            "is_business": True,
            "parse_status": "pending"
        }
        
        msg_id = temp_db.save_raw_message(msg_data)
        
        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter(RawMessage.id == msg_id).first()
            assert msg is not None
            assert msg.wechat_msg_id == "msg_all_fields"
            assert msg.sender_nickname == "完整用户"
            assert msg.sender_wechat_id == "wechat_123"
            assert msg.content == "完整消息内容"
            assert msg.msg_type == "text"
            assert msg.group_id == "group_001"
            assert msg.is_at_bot is True
            assert msg.is_business is True
            assert msg.parse_status == "pending"
    
    def test_update_parse_status(self, temp_db):
        """测试更新解析状态。"""
        # 先创建消息
        msg_data = {
            "wechat_msg_id": "msg_parse_test",
            "sender_nickname": "测试",
            "content": "测试消息",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
            "parse_status": "pending"
        }
        msg_id = temp_db.save_raw_message(msg_data)
        
        # 更新解析状态为已解析
        parse_result = {"type": "service", "amount": 100}
        temp_db.update_parse_status(msg_id, "parsed", result=parse_result)
        
        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter(RawMessage.id == msg_id).first()
            assert msg.parse_status == "parsed"
            assert msg.parse_result == parse_result
        
        # 更新解析状态为失败
        error_msg = "解析失败：无法识别金额"
        temp_db.update_parse_status(msg_id, "failed", error=error_msg)
        
        with temp_db.get_session() as session:
            msg = session.query(RawMessage).filter(RawMessage.id == msg_id).first()
            assert msg.parse_status == "failed"
            assert msg.parse_error == error_msg
    
    def test_get_or_create_employee_by_name_or_nickname(self, temp_db):
        """测试通过姓名或微信昵称查找员工。"""
        # 通过姓名创建
        emp1 = temp_db.get_or_create_employee("张三", "zhang_san")
        assert emp1.id > 0
        
        # 通过姓名查找（应该返回同一个）
        emp2 = temp_db.get_or_create_employee("张三", None)
        assert emp1.id == emp2.id
        
        # 通过微信昵称查找（应该返回同一个）
        emp3 = temp_db.get_or_create_employee("李四", "zhang_san")
        assert emp1.id == emp3.id
    
    def test_save_service_record_date_formats(self, temp_db):
        """测试服务记录日期格式处理。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        # 测试字符串日期格式
        record_data1 = {
            "customer_name": "测试顾客",
            "service_or_product": "测试服务",
            "date": "2024-01-28",  # 字符串格式
            "amount": 100.0
        }
        msg_id1 = temp_db.save_raw_message({
            "wechat_msg_id": "msg_date_str",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        record_id1 = temp_db.save_service_record(record_data1, msg_id1)
        assert record_id1 > 0
        
        # 测试date对象格式
        record_data2 = {
            "customer_name": "测试顾客",
            "service_or_product": "测试服务",
            "date": date(2024, 1, 29),  # date对象
            "amount": 100.0
        }
        msg_id2 = temp_db.save_raw_message({
            "wechat_msg_id": "msg_date_obj",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 29, 10, 0, 0)
        })
        record_id2 = temp_db.save_service_record(record_data2, msg_id2)
        assert record_id2 > 0
    
    def test_save_service_record_invalid_date(self, temp_db):
        """测试服务记录无效日期格式。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "测试服务",
            "date": "invalid-date",  # 无效格式
            "amount": 100.0
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_invalid_date",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        with pytest.raises(ValueError, match="Invalid date format"):
            temp_db.save_service_record(record_data, msg_id)
    
    def test_save_service_record_missing_date(self, temp_db):
        """测试服务记录缺失日期。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "测试服务",
            # 缺少date字段
            "amount": 100.0
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_missing_date",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        with pytest.raises(ValueError, match="Service date is required"):
            temp_db.save_service_record(record_data, msg_id)
    
    def test_save_service_record_with_employee(self, temp_db):
        """测试服务记录关联员工。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        # 创建员工
        employee = temp_db.get_or_create_employee("服务员工", "service_emp")
        
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "测试服务",
            "date": "2024-01-28",
            "amount": 100.0,
            "recorder_nickname": "服务员工"
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_with_emp",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id)
        
        with temp_db.get_session() as session:
            from db.models import ServiceRecord
            record = session.query(ServiceRecord).filter(
                ServiceRecord.id == record_id
            ).first()
            assert record.recorder_id == employee.id
            assert record.recorder.name == "服务员工"
    
    def test_save_product_sale_invalid_date(self, temp_db):
        """测试商品销售无效日期格式。"""
        product = temp_db.get_or_create_product("测试商品", "test", 50.0)
        
        sale_data = {
            "service_or_product": "测试商品",
            "date": "invalid-date",
            "amount": 50.0
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_sale_invalid_date",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        with pytest.raises(ValueError, match="Invalid date format"):
            temp_db.save_product_sale(sale_data, msg_id)
    
    def test_save_membership_invalid_date(self, temp_db):
        """测试会员卡无效日期格式。"""
        membership_data = {
            "customer_name": "测试会员",
            "date": "invalid-date",
            "amount": 1000.0
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_member_invalid_date",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0)
        })
        
        with pytest.raises(ValueError, match="Invalid date format"):
            temp_db.save_membership(membership_data, msg_id)
    
    def test_save_membership_missing_date(self, temp_db):
        """测试会员卡缺失日期。"""
        membership_data = {
            "customer_name": "测试会员",
            # 缺少date字段
            "amount": 1000.0
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_member_missing_date",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0)
        })
        
        with pytest.raises(ValueError, match="Membership opened_at date is required"):
            temp_db.save_membership(membership_data, msg_id)
    
    def test_get_records_by_date_empty(self, temp_db):
        """测试查询空日期的记录。"""
        empty_date = date(2024, 12, 31)
        records = temp_db.get_records_by_date(empty_date)
        assert records == []
    
    def test_get_referral_channels_filtering(self, temp_db):
        """测试引流渠道过滤功能。"""
        # 创建不同类型的渠道
        platform1 = temp_db.get_or_create_referral_channel("美团", "platform")
        platform2 = temp_db.get_or_create_referral_channel("大众点评", "platform")
        external1 = temp_db.get_or_create_referral_channel("朋友推荐", "external")
        internal1 = temp_db.get_or_create_referral_channel("内部员工", "internal")
        
        # 测试按类型过滤（get_or_create_referral_channel会自动提交）
        platforms = temp_db.get_referral_channels(channel_type="platform")
        assert len(platforms) >= 2
        assert all(c.channel_type == "platform" for c in platforms)
        
        externals = temp_db.get_referral_channels(channel_type="external")
        assert len(externals) >= 1
        assert all(c.channel_type == "external" for c in externals)
        
        internals = temp_db.get_referral_channels(channel_type="internal")
        assert len(internals) >= 1
        assert all(c.channel_type == "internal" for c in internals)
    
    def test_get_plugin_data_nonexistent(self, temp_db):
        """测试获取不存在的插件数据。"""
        employee = temp_db.get_or_create_employee("测试员工", "test")
        
        # 获取不存在的键
        data = temp_db.get_plugin_data("test_plugin", "employee", employee.id, "nonexistent_key")
        assert data is None
        
        # 获取不存在的实体
        all_data = temp_db.get_plugin_data("test_plugin", "employee", 99999)
        assert all_data == {}
    
    def test_save_daily_summary_partial_update(self, temp_db):
        """测试每日汇总部分更新。"""
        target_date = date(2024, 1, 28)
        
        # 创建完整汇总
        full_data = {
            "total_service_revenue": 500.0,
            "total_product_revenue": 200.0,
            "total_commissions": 50.0,
            "net_revenue": 650.0,
            "service_count": 5,
            "product_sale_count": 2
        }
        summary_id = temp_db.save_daily_summary(target_date, full_data)
        
        # 部分更新
        partial_data = {
            "total_service_revenue": 600.0
        }
        updated_id = temp_db.save_daily_summary(target_date, partial_data)
        assert summary_id == updated_id
        
        # 验证部分更新后其他字段保持不变
        with temp_db.get_session() as session:
            from db.models import DailySummary
            summary = session.query(DailySummary).filter(
                DailySummary.summary_date == target_date
            ).first()
            assert float(summary.total_service_revenue) == 600.0
            assert float(summary.total_product_revenue) == 200.0  # 保持不变
            assert summary.service_count == 5  # 保持不变

