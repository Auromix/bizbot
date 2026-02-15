"""数据库Repository综合测试。

测试所有Repository方法的功能，确保数据库操作的正确性。
"""
import pytest
from datetime import date, datetime

from db.repository import DatabaseRepository
from db.models import (
    Employee, Customer, Membership, ServiceType, ServiceRecord,
    Product, ProductSale, ReferralChannel, PluginData, DailySummary
)
from tests.conftest import temp_db


class TestRepositoryComprehensive:
    """Repository综合测试类。"""
    
    def test_referral_channel_operations(self, temp_db):
        """测试引流渠道操作。"""
        # 创建渠道
        channel1 = temp_db.get_or_create_referral_channel(
            "美团", "platform", commission_rate=15.0
        )
        channel2 = temp_db.get_or_create_referral_channel(
            "美团", "platform", commission_rate=15.0  # 应该返回已存在的
        )
        assert channel1.id == channel2.id
        
        # 查询渠道（get_or_create_referral_channel会自动提交）
        platforms = temp_db.get_referral_channels(channel_type="platform")
        assert len(platforms) >= 1
        assert any(c.name == "美团" for c in platforms)
        
        # 查询所有激活的渠道
        all_active = temp_db.get_referral_channels(is_active=True)
        assert len(all_active) >= 1
        
        # 查询所有渠道（不过滤）
        all_channels = temp_db.get_referral_channels(is_active=None)
        assert len(all_channels) >= 1
    
    def test_plugin_data_operations(self, temp_db):
        """测试插件数据操作。"""
        # 创建实体
        employee = temp_db.get_or_create_employee("测试员工", "test_emp")
        
        # 保存插件数据
        data_id1 = temp_db.save_plugin_data(
            "test_plugin", "employee", employee.id, "key1", {"value": "data1"}
        )
        assert data_id1 > 0
        
        # 更新插件数据（应该返回同一个ID）
        data_id2 = temp_db.save_plugin_data(
            "test_plugin", "employee", employee.id, "key1", {"value": "data2"}
        )
        assert data_id1 == data_id2
        
        # 读取单个键
        data = temp_db.get_plugin_data("test_plugin", "employee", employee.id, "key1")
        assert data == {"value": "data2"}
        
        # 保存多个键
        temp_db.save_plugin_data(
            "test_plugin", "employee", employee.id, "key2", {"value": "data3"}
        )
        
        # 读取所有键
        all_data = temp_db.get_plugin_data("test_plugin", "employee", employee.id)
        assert "key1" in all_data
        assert "key2" in all_data
        assert len(all_data) == 2
        
        # 删除单个键
        temp_db.delete_plugin_data("test_plugin", "employee", employee.id, "key1")
        remaining = temp_db.get_plugin_data("test_plugin", "employee", employee.id)
        assert "key1" not in remaining
        assert "key2" in remaining
        
        # 删除所有键
        temp_db.delete_plugin_data("test_plugin", "employee", employee.id)
        all_after_delete = temp_db.get_plugin_data("test_plugin", "employee", employee.id)
        assert len(all_after_delete) == 0
    
    def test_service_record_with_referral_channel(self, temp_db):
        """测试服务记录与引流渠道的关联。"""
        # 创建渠道
        channel = temp_db.get_or_create_referral_channel(
            "测试渠道", "external", commission_rate=10.0
        )
        
        # 使用referral_channel_id创建记录
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "测试服务",
            "date": "2024-01-28",
            "amount": 100.0,
            "referral_channel_id": channel.id,
            "commission": 10.0
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_test_001",
            "sender_nickname": "测试",
            "content": "测试消息",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id)
        
        # 验证关联
        with temp_db.get_session() as session:
            from sqlalchemy.orm import joinedload
            record = session.query(ServiceRecord).options(
                joinedload(ServiceRecord.referral_channel)
            ).filter(ServiceRecord.id == record_id).first()
            assert record.referral_channel_id == channel.id
            assert record.referral_channel is not None
            assert record.referral_channel.name == "测试渠道"
    
    def test_service_record_backward_compatibility(self, temp_db):
        """测试服务记录的向后兼容性（commission_to字段）。"""
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        # 使用commission_to字段（应该自动创建渠道）
        record_data = {
            "customer_name": "测试顾客",
            "service_or_product": "测试服务",
            "date": "2024-01-28",
            "amount": 100.0,
            "commission": 10.0,
            "commission_to": "李哥"  # 向后兼容字段
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_test_002",
            "sender_nickname": "测试",
            "content": "测试消息",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id)
        
        # 验证自动创建的渠道
        with temp_db.get_session() as session:
            record = session.query(ServiceRecord).filter(
                ServiceRecord.id == record_id
            ).first()
            assert record.commission_to == "李哥"
            assert record.referral_channel_id is not None
            assert record.referral_channel.name == "李哥"
            assert record.referral_channel.channel_type == "external"
    
    def test_get_records_by_date(self, temp_db):
        """测试按日期查询记录。"""
        target_date = date(2024, 1, 28)
        
        # 创建服务记录
        customer = temp_db.get_or_create_customer("测试顾客")
        service_type = temp_db.get_or_create_service_type("测试服务", 100.0)
        
        for i in range(3):
            record_data = {
                "customer_name": "测试顾客",
                "service_or_product": "测试服务",
                "date": target_date,
                "amount": 100.0 + i * 10
            }
            msg_id = temp_db.save_raw_message({
                "wechat_msg_id": f"msg_date_{i}",
                "sender_nickname": "测试",
                "content": f"测试消息{i}",
                "timestamp": datetime(2024, 1, 28, 10+i, 0, 0)
            })
            temp_db.save_service_record(record_data, msg_id)
        
        # 创建商品销售记录
        product = temp_db.get_or_create_product("测试商品", "test", 50.0)
        for i in range(2):
            sale_data = {
                "service_or_product": "测试商品",
                "date": target_date,
                "amount": 50.0,
                "quantity": 1
            }
            msg_id = temp_db.save_raw_message({
                "wechat_msg_id": f"msg_sale_{i}",
                "sender_nickname": "测试",
                "content": f"销售消息{i}",
                "timestamp": datetime(2024, 1, 28, 15+i, 0, 0)
            })
            temp_db.save_product_sale(sale_data, msg_id)
        
        # 查询记录
        records = temp_db.get_records_by_date(target_date)
        assert len(records) == 5
        
        # 验证记录类型
        service_records = [r for r in records if r["type"] == "service"]
        product_records = [r for r in records if r["type"] == "product_sale"]
        assert len(service_records) == 3
        assert len(product_records) == 2
    
    def test_daily_summary_operations(self, temp_db):
        """测试每日汇总操作。"""
        target_date = date(2024, 1, 28)
        
        # 创建汇总
        summary_data = {
            "total_service_revenue": 500.0,
            "total_product_revenue": 200.0,
            "total_commissions": 50.0,
            "net_revenue": 650.0,
            "service_count": 5,
            "product_sale_count": 2,
            "summary_text": "今日汇总测试"
        }
        
        summary_id1 = temp_db.save_daily_summary(target_date, summary_data)
        assert summary_id1 > 0
        
        # 更新汇总（应该返回同一个ID）
        updated_data = {
            "total_service_revenue": 600.0,
            "service_count": 6
        }
        summary_id2 = temp_db.save_daily_summary(target_date, updated_data)
        assert summary_id1 == summary_id2
        
        # 验证更新
        with temp_db.get_session() as session:
            summary = session.query(DailySummary).filter(
                DailySummary.summary_date == target_date
            ).first()
            assert float(summary.total_service_revenue) == 600.0
            assert summary.service_count == 6
            # 其他字段应该保持不变
            assert float(summary.total_product_revenue) == 200.0
    
    def test_extra_data_fields(self, temp_db):
        """测试扩展数据字段。"""
        # Employee extra_data
        employee = temp_db.get_or_create_employee("测试员工", "test")
        with temp_db.get_session() as session:
            from db.models import Employee
            emp = session.query(Employee).filter(Employee.id == employee.id).first()
            assert emp is not None
            emp.extra_data = {"department": "测试部", "level": 5}
            session.commit()
            session.refresh(emp)
            assert emp.extra_data == {"department": "测试部", "level": 5}
        
        # Customer extra_data
        customer = temp_db.get_or_create_customer("测试顾客")
        with temp_db.get_session() as session:
            from db.models import Customer
            cust = session.query(Customer).filter(Customer.id == customer.id).first()
            assert cust is not None
            cust.extra_data = {"vip_level": "gold", "source": "美团"}
            session.commit()
            session.refresh(cust)
            assert cust.extra_data == {"vip_level": "gold", "source": "美团"}
        
        # Product extra_data
        product = temp_db.get_or_create_product("测试商品", "test", 100.0)
        with temp_db.get_session() as session:
            from db.models import Product
            prod = session.query(Product).filter(Product.id == product.id).first()
            assert prod is not None
            prod.extra_data = {"supplier": "XX供应商", "batch": "B001"}
            session.commit()
            session.refresh(prod)
            assert prod.extra_data == {"supplier": "XX供应商", "batch": "B001"}
    
    def test_membership_with_expires_and_points(self, temp_db):
        """测试会员卡的有效期和积分。"""
        customer = temp_db.get_or_create_customer("测试会员")
        
        membership_data = {
            "customer_name": "测试会员",
            "date": "2024-01-01",
            "amount": 1000.0,
            "card_type": "年卡"
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_member_test",
            "sender_nickname": "测试",
            "content": "开卡测试",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0)
        })
        
        membership_id = temp_db.save_membership(membership_data, msg_id)
        
        # 设置有效期和积分
        with temp_db.get_session() as session:
            membership = session.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            from datetime import timedelta
            membership.expires_at = membership.opened_at + timedelta(days=365)
            membership.points = 100
            session.commit()
            session.refresh(membership)
            
            assert membership.expires_at is not None
            assert membership.points == 100
            assert membership.expires_at > membership.opened_at

