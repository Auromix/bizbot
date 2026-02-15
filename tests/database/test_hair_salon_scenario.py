"""理发店业务场景测试。

使用真实的理发店业务场景测试数据库功能，包括：
- 员工管理（发型师、助理）
- 服务记录（剪发、染发、烫发）
- 外部引流（美团、大众点评）
- 会员管理
- 商品销售（洗发水、护发素等）
"""
import pytest
from datetime import date, datetime

from db.repository import DatabaseRepository
from tests.conftest import temp_db


class TestHairSalonScenario:
    """理发店业务场景测试类。"""
    
    def test_hair_salon_setup(self, temp_db):
        """测试理发店基础设置。"""
        # 1. 创建员工（发型师）
        tony = temp_db.get_or_create_employee("Tony", "tony_hair")
        # 在session内更新员工信息
        with temp_db.get_session() as session:
            from db.models import Employee
            tony_obj = session.query(Employee).filter(Employee.id == tony.id).first()
            tony_obj.role = "manager"
            tony_obj.commission_rate = 40.0  # 发型师提成40%
            tony_obj.extra_data = {
                "position": "高级发型师",
                "skills": ["剪发", "染发", "烫发", "造型"],
                "level": "高级"
            }
            session.commit()
        
        # 2. 创建助理
        assistant = temp_db.get_or_create_employee("小美", "assistant_mei")
        with temp_db.get_session() as session:
            from db.models import Employee
            assistant_obj = session.query(Employee).filter(Employee.id == assistant.id).first()
            assistant_obj.role = "staff"
            assistant_obj.commission_rate = 10.0
            assistant_obj.extra_data = {
                "position": "助理",
                "skills": ["洗头", "吹发"]
            }
            session.commit()
        
        # 3. 创建引流渠道
        meituan = temp_db.get_or_create_referral_channel(
            name="美团",
            channel_type="platform",
            contact_info="美团商家后台",
            commission_rate=15.0
        )
        
        dianping = temp_db.get_or_create_referral_channel(
            name="大众点评",
            channel_type="platform",
            contact_info="大众点评商家后台",
            commission_rate=12.0
        )
        
        # 4. 创建服务类型
        haircut = temp_db.get_or_create_service_type("剪发", 80.0, "haircut")
        dye = temp_db.get_or_create_service_type("染发", 200.0, "dye")
        perm = temp_db.get_or_create_service_type("烫发", 300.0, "perm")
        
        # 验证
        assert tony.id > 0
        with temp_db.get_session() as session:
            from db.models import Employee
            tony_obj = session.query(Employee).filter(Employee.id == tony.id).first()
            assert tony_obj.extra_data["position"] == "高级发型师"
        
        assert meituan.id > 0
        assert float(meituan.commission_rate) == 15.0
        
        assert haircut.id > 0
    
    def test_hair_salon_service_records(self, temp_db):
        """测试理发店服务记录。"""
        # 设置
        customer = temp_db.get_or_create_customer("王女士")
        tony = temp_db.get_or_create_employee("Tony", "tony_hair")
        haircut = temp_db.get_or_create_service_type("剪发", 80.0)
        meituan = temp_db.get_or_create_referral_channel("美团", "platform", commission_rate=15.0)
        
        # 场景1：美团引流的剪发服务
        record_data = {
            "customer_name": "王女士",
            "service_or_product": "剪发",
            "date": "2024-01-28",
            "amount": 80.0,
            "commission": 12.0,  # 美团提成15% = 80 * 0.15 = 12
            "referral_channel_id": meituan.id,
            "net_amount": 68.0,
            "recorder_nickname": "小美",
            "extra_data": {
                "duration": 30,
                "stylist": "Tony",
                "service_room": "A101"
            }
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_001",
            "sender_nickname": "小美",
            "content": "1.28王女士剪发80，美团引流",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id)
        assert record_id > 0
        
        # 验证记录
        with temp_db.get_session() as session:
            from db.models import ServiceRecord
            from sqlalchemy.orm import joinedload
            record = session.query(ServiceRecord).options(
                joinedload(ServiceRecord.referral_channel)
            ).filter(ServiceRecord.id == record_id).first()
            assert record is not None
            assert float(record.amount) == 80.0
            assert float(record.commission_amount) == 12.0
            assert record.referral_channel_id == meituan.id
            assert record.referral_channel is not None
            assert record.referral_channel.name == "美团"
            assert record.extra_data["duration"] == 30
            assert record.extra_data["stylist"] == "Tony"
    
    def test_hair_salon_membership(self, temp_db):
        """测试理发店会员管理。"""
        customer = temp_db.get_or_create_customer("张女士")
        customer.extra_data = {
            "vip_level": "gold",
            "preferred_stylist": "Tony"
        }
        
        # 开卡
        membership_data = {
            "customer_name": "张女士",
            "date": "2024-01-01",
            "amount": 1000.0,
            "card_type": "储值卡"
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_002",
            "sender_nickname": "Tony",
            "content": "张女士开卡1000",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0)
        })
        
        membership_id = temp_db.save_membership(membership_data, msg_id)
        assert membership_id > 0
        
        # 验证会员卡
        with temp_db.get_session() as session:
            from db.models import Membership
            membership = session.query(Membership).filter(Membership.id == membership_id).first()
            assert membership is not None
            assert float(membership.total_amount) == 1000.0
            assert float(membership.balance) == 1000.0
            assert membership.card_type == "储值卡"
            assert membership.customer.name == "张女士"
    
    def test_hair_salon_product_sales(self, temp_db):
        """测试理发店商品销售。"""
        customer = temp_db.get_or_create_customer("李女士")
        product = temp_db.get_or_create_product("洗发水", "accessory", 50.0)
        product.extra_data = {
            "supplier": "XX供应商",
            "brand": "知名品牌"
        }
        
        # 销售记录
        sale_data = {
            "service_or_product": "洗发水",
            "date": "2024-01-28",
            "amount": 50.0,
            "quantity": 1,
            "unit_price": 50.0,
            "customer_name": "李女士",
            "recorder_nickname": "Tony"
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_003",
            "sender_nickname": "Tony",
            "content": "1.28李女士购买洗发水50",
            "timestamp": datetime(2024, 1, 28, 15, 0, 0)
        })
        
        sale_id = temp_db.save_product_sale(sale_data, msg_id)
        assert sale_id > 0
        
        # 验证销售记录
        with temp_db.get_session() as session:
            from db.models import ProductSale
            sale = session.query(ProductSale).filter(ProductSale.id == sale_id).first()
            assert sale is not None
            assert float(sale.total_amount) == 50.0
            assert sale.quantity == 1
            assert sale.customer.name == "李女士"
            assert sale.product.name == "洗发水"
    
    def test_hair_salon_referral_channels(self, temp_db):
        """测试理发店引流渠道管理。"""
        # 创建多个渠道
        meituan = temp_db.get_or_create_referral_channel("美团", "platform", commission_rate=15.0)
        dianping = temp_db.get_or_create_referral_channel("大众点评", "platform", commission_rate=12.0)
        friend = temp_db.get_or_create_referral_channel("朋友推荐", "external", commission_rate=10.0)
        
        # 查询渠道（get_or_create_referral_channel会自动提交）
        platforms = temp_db.get_referral_channels(channel_type="platform")
        assert len(platforms) >= 2
        assert any(c.name == "美团" for c in platforms)
        assert any(c.name == "大众点评" for c in platforms)
        
        # 测试渠道统计
        customer = temp_db.get_or_create_customer("王女士")
        haircut = temp_db.get_or_create_service_type("剪发", 80.0)
        
        # 创建多个服务记录，使用不同渠道
        for i, channel in enumerate([meituan, dianping, friend]):
            record_data = {
                "customer_name": "王女士",
                "service_or_product": "剪发",
                "date": f"2024-01-{28+i}",
                "amount": 80.0,
                "referral_channel_id": channel.id,
                "commission": float(channel.commission_rate) / 100 * 80.0
            }
            msg_id = temp_db.save_raw_message({
                "wechat_msg_id": f"msg_{i}",
                "sender_nickname": "Tony",
                "content": f"1.{28+i}王女士剪发80",
                "timestamp": datetime(2024, 1, 28+i, 10, 0, 0)
            })
            temp_db.save_service_record(record_data, msg_id)
        
        # 验证渠道关联
        with temp_db.get_session() as session:
            from db.models import ServiceRecord
            from sqlalchemy.orm import joinedload
            records = session.query(ServiceRecord).options(
                joinedload(ServiceRecord.referral_channel)
            ).all()
            assert len(records) == 3
            channels_used = {r.referral_channel.name for r in records if r.referral_channel}
            assert "美团" in channels_used
            assert "大众点评" in channels_used
            assert "朋友推荐" in channels_used
    
    def test_hair_salon_plugin_data(self, temp_db):
        """测试理发店插件数据扩展。"""
        # 为员工添加技能标签
        tony = temp_db.get_or_create_employee("Tony", "tony_hair")
        
        temp_db.save_plugin_data(
            plugin_name="hair_salon",
            entity_type="employee",
            entity_id=tony.id,
            data_key="skills",
            data_value=["剪发", "染发", "烫发", "造型"]
        )
        
        temp_db.save_plugin_data(
            plugin_name="hair_salon",
            entity_type="employee",
            entity_id=tony.id,
            data_key="certifications",
            data_value=["高级发型师资格证", "色彩搭配师资格证"]
        )
        
        # 读取插件数据
        skills = temp_db.get_plugin_data("hair_salon", "employee", tony.id, "skills")
        assert skills == ["剪发", "染发", "烫发", "造型"]
        
        all_data = temp_db.get_plugin_data("hair_salon", "employee", tony.id)
        assert "skills" in all_data
        assert "certifications" in all_data
        assert len(all_data) == 2
    
    def test_hair_salon_daily_summary(self, temp_db):
        """测试理发店每日汇总。"""
        # 创建一些服务记录
        customer = temp_db.get_or_create_customer("王女士")
        haircut = temp_db.get_or_create_service_type("剪发", 80.0)
        dye = temp_db.get_or_create_service_type("染发", 200.0)
        
        target_date = date(2024, 1, 28)
        
        # 创建多条记录
        for i, (service_name, amount) in enumerate([("剪发", 80.0), ("染发", 200.0)]):
            record_data = {
                "customer_name": "王女士",
                "service_or_product": service_name,
                "date": target_date,
                "amount": amount
            }
            msg_id = temp_db.save_raw_message({
                "wechat_msg_id": f"msg_{i}",
                "sender_nickname": "Tony",
                "content": f"1.28王女士{service_name}{amount}",
                "timestamp": datetime(2024, 1, 28, 10+i, 0, 0)
            })
            temp_db.save_service_record(record_data, msg_id)
        
        # 获取记录
        records = temp_db.get_records_by_date(target_date)
        assert len(records) == 2
        
        # 创建汇总
        summary_data = {
            "total_service_revenue": 280.0,
            "service_count": 2,
            "summary_text": "今日服务2单，总收入280元"
        }
        
        summary_id = temp_db.save_daily_summary(target_date, summary_data)
        assert summary_id > 0
        
        # 验证汇总
        with temp_db.get_session() as session:
            from db.models import DailySummary
            summary = session.query(DailySummary).filter(
                DailySummary.summary_date == target_date
            ).first()
            assert summary is not None
            assert float(summary.total_service_revenue) == 280.0
            assert summary.service_count == 2

