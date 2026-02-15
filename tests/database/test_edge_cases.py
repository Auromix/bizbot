"""边界情况和错误处理测试。

测试各种边界情况和错误处理，确保系统的健壮性。
"""
import pytest
from datetime import date, datetime

from db.repository import DatabaseRepository
from tests.conftest import temp_db


class TestEdgeCases:
    """边界情况测试类。"""
    
    def test_empty_strings(self, temp_db):
        """测试空字符串处理。"""
        # 空字符串的顾客名称应该能创建
        customer = temp_db.get_or_create_customer("")
        assert customer.id > 0
        assert customer.name == ""
    
    def test_very_long_strings(self, temp_db):
        """测试超长字符串。"""
        # 测试接近字段长度限制的字符串
        long_name = "A" * 50  # 正好50字符
        customer = temp_db.get_or_create_customer(long_name)
        assert customer.id > 0
        assert customer.name == long_name
    
    def test_special_characters(self, temp_db):
        """测试特殊字符。"""
        # 测试包含特殊字符的名称
        special_name = "测试用户@#$%^&*()"
        customer = temp_db.get_or_create_customer(special_name)
        assert customer.id > 0
        assert customer.name == special_name
    
    def test_unicode_characters(self, temp_db):
        """测试Unicode字符。"""
        # 测试Unicode字符
        unicode_name = "测试用户🚀🎉"
        customer = temp_db.get_or_create_customer(unicode_name)
        assert customer.id > 0
        assert customer.name == unicode_name
    
    def test_zero_amounts(self, temp_db):
        """测试零金额。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("免费服务", 0.0)
        
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "免费服务",
            "date": "2024-01-28",
            "amount": 0.0
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_zero_amount",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id)
        assert record_id > 0
        
        with temp_db.get_session() as session:
            from db.models import ServiceRecord
            record = session.query(ServiceRecord).filter(
                ServiceRecord.id == record_id
            ).first()
            assert float(record.amount) == 0.0
    
    def test_negative_amounts(self, temp_db):
        """测试负金额（退款场景）。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("退款", 0.0)
        
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "退款",
            "date": "2024-01-28",
            "amount": -100.0  # 负金额表示退款
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_negative_amount",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id)
        assert record_id > 0
        
        with temp_db.get_session() as session:
            from db.models import ServiceRecord
            record = session.query(ServiceRecord).filter(
                ServiceRecord.id == record_id
            ).first()
            assert float(record.amount) == -100.0
    
    def test_large_amounts(self, temp_db):
        """测试大金额。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("大额服务", 999999.99)
        
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "大额服务",
            "date": "2024-01-28",
            "amount": 999999.99
        }
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_large_amount",
            "sender_nickname": "测试",
            "content": "测试",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id)
        assert record_id > 0
        
        with temp_db.get_session() as session:
            from db.models import ServiceRecord
            record = session.query(ServiceRecord).filter(
                ServiceRecord.id == record_id
            ).first()
            assert float(record.amount) == 999999.99
    
    def test_multiple_commissions(self, temp_db):
        """测试多条提成记录。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        # 创建多个渠道
        channel1 = temp_db.get_or_create_referral_channel("渠道1", "external", commission_rate=10.0)
        channel2 = temp_db.get_or_create_referral_channel("渠道2", "external", commission_rate=15.0)
        
        # 创建多条记录，使用不同渠道
        for i, channel in enumerate([channel1, channel2]):
            record_data = {
                "customer_name": "测试顾客",
                "service_or_product": "测试服务",
                "date": f"2024-01-{28+i}",
                "amount": 100.0,
                "referral_channel_id": channel.id,
                "commission": float(channel.commission_rate) / 100 * 100.0
            }
            msg_id = temp_db.save_raw_message({
                "wechat_msg_id": f"msg_multi_comm_{i}",
                "sender_nickname": "测试",
                "content": "测试",
                "timestamp": datetime(2024, 1, 28+i, 10, 0, 0)
            })
            temp_db.save_service_record(record_data, msg_id)
        
        # 验证两条记录都创建成功
        with temp_db.get_session() as session:
            from db.models import ServiceRecord
            from sqlalchemy.orm import joinedload
            records = session.query(ServiceRecord).options(
                joinedload(ServiceRecord.referral_channel)
            ).all()
            assert len(records) == 2
            assert records[0].referral_channel is not None
            assert records[0].referral_channel.name == "渠道1"
            assert records[1].referral_channel is not None
            assert records[1].referral_channel.name == "渠道2"
    
    def test_extra_data_nested(self, temp_db):
        """测试嵌套的extra_data。"""
        employee = temp_db.get_or_create_employee("测试员工", "test")
        
        nested_data = {
            "personal": {
                "age": 30,
                "city": "北京"
            },
            "work": {
                "department": "技术部",
                "skills": ["Python", "SQL"]
            }
        }
        
        # 需要在同一个session中更新
        with temp_db.get_session() as session:
            # 重新获取employee对象
            from db.models import Employee
            emp = session.query(Employee).filter(Employee.id == employee.id).first()
            assert emp is not None
            emp.extra_data = nested_data
            session.commit()
            session.refresh(emp)
            assert emp.extra_data == nested_data
            assert emp.extra_data["personal"]["age"] == 30
            assert emp.extra_data["work"]["skills"] == ["Python", "SQL"]
    
    def test_plugin_data_complex_types(self, temp_db):
        """测试插件数据的复杂类型。"""
        employee = temp_db.get_or_create_employee("测试员工", "test")
        
        # 测试列表
        temp_db.save_plugin_data("test_plugin", "employee", employee.id, "list_data", [1, 2, 3])
        list_data = temp_db.get_plugin_data("test_plugin", "employee", employee.id, "list_data")
        assert list_data == [1, 2, 3]
        
        # 测试嵌套字典
        nested_dict = {
            "level1": {
                "level2": {
                    "value": "deep"
                }
            }
        }
        temp_db.save_plugin_data("test_plugin", "employee", employee.id, "nested_dict", nested_dict)
        dict_data = temp_db.get_plugin_data("test_plugin", "employee", employee.id, "nested_dict")
        assert dict_data == nested_dict
    
    def test_concurrent_operations(self, temp_db):
        """测试并发操作（模拟）。"""
        # 同时创建多个顾客
        customers = []
        for i in range(10):
            customer = temp_db.get_or_create_customer(f"并发顾客{i}")
            customers.append(customer)
        
        # 验证所有顾客都创建成功
        assert len(customers) == 10
        assert all(c.id > 0 for c in customers)
        
        # 验证去重功能在并发情况下仍然有效
        customer_again = temp_db.get_or_create_customer("并发顾客0")
        assert customer_again.id == customers[0].id

