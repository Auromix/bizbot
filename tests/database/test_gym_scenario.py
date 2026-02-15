"""健身房业务场景测试。

使用真实的健身房业务场景测试数据库功能，包括：
- 员工管理（私教、前台）
- 服务记录（私教课程、团课）
- 会员管理（年卡、季卡、月卡）
- 会员积分系统
- 商品销售（蛋白粉、运动装备等）
"""
import pytest
from datetime import date, datetime

from db.repository import DatabaseRepository
from tests.conftest import temp_db


class TestGymScenario:
    """健身房业务场景测试类。"""
    
    def test_gym_setup(self, temp_db):
        """测试健身房基础设置。"""
        # 1. 创建私教
        trainer_li = temp_db.get_or_create_employee("李教练", "trainer_li")
        trainer_li.role = "manager"
        trainer_li.commission_rate = 40.0  # 私教提成40%
        trainer_li.extra_data = {
            "position": "高级私教",
            "specialties": ["力量训练", "减脂", "增肌"],
            "certifications": ["健身教练资格证", "营养师资格证"]
        }
        
        # 2. 创建前台
        receptionist = temp_db.get_or_create_employee("小张", "reception_zhang")
        receptionist.role = "staff"
        receptionist.commission_rate = 5.0
        receptionist.extra_data = {
            "position": "前台接待"
        }
        
        # 3. 创建服务类型
        personal_training = temp_db.get_or_create_service_type("私教课程", 300.0, "training")
        group_class = temp_db.get_or_create_service_type("团课", 50.0, "class")
        
        # 验证
        assert trainer_li.id > 0
        assert trainer_li.extra_data["position"] == "高级私教"
        assert personal_training.id > 0
    
    def test_gym_membership_types(self, temp_db):
        """测试健身房会员卡类型。"""
        # 创建不同类型的会员
        customers = [
            ("王先生", "年卡", 3000.0, 365),
            ("李女士", "季卡", 800.0, 90),
            ("张先生", "月卡", 300.0, 30)
        ]
        
        membership_ids = []
        for name, card_type, amount, days in customers:
            customer = temp_db.get_or_create_customer(name)
            customer.extra_data = {
                "source": "美团",
                "preferred_trainer": "李教练" if name == "王先生" else None
            }
            
            membership_data = {
                "customer_name": name,
                "date": "2024-01-01",
                "amount": amount,
                "card_type": card_type
            }
            
            msg_id = temp_db.save_raw_message({
                "wechat_msg_id": f"msg_{name}",
                "sender_nickname": "小张",
                "content": f"{name}开{card_type}{amount}",
                "timestamp": datetime(2024, 1, 1, 10, 0, 0)
            })
            
            membership_id = temp_db.save_membership(membership_data, msg_id)
            membership_ids.append(membership_id)
            
            # 设置有效期和积分
            with temp_db.get_session() as session:
                from db.models import Membership
                membership = session.query(Membership).filter(
                    Membership.id == membership_id
                ).first()
                from datetime import timedelta
                membership.expires_at = membership.opened_at + timedelta(days=days)
                membership.points = int(amount / 10)  # 每10元1积分
                session.commit()
        
        # 验证会员卡
        with temp_db.get_session() as session:
            from db.models import Membership
            memberships = session.query(Membership).filter(
                Membership.id.in_(membership_ids)
            ).all()
            
            assert len(memberships) == 3
            for membership in memberships:
                assert membership.expires_at is not None
                assert membership.points > 0
                assert membership.is_active is True
    
    def test_gym_personal_training(self, temp_db):
        """测试私教课程记录。"""
        # 设置
        customer = temp_db.get_or_create_customer("王先生")
        trainer = temp_db.get_or_create_employee("李教练", "trainer_li")
        personal_training = temp_db.get_or_create_service_type("私教课程", 300.0)
        
        # 创建内部员工渠道（用于私教提成）
        trainer_channel = temp_db.get_or_create_referral_channel(
            name="李教练",
            channel_type="internal",
            commission_rate=40.0
        )
        
        # 私教课程记录
        record_data = {
            "customer_name": "王先生",
            "service_or_product": "私教课程",
            "date": "2024-01-28",
            "amount": 300.0,
            "commission": 120.0,  # 私教提成40% = 300 * 0.4 = 120
            "referral_channel_id": trainer_channel.id,
            "net_amount": 180.0,
            "recorder_nickname": "小张",
            "extra_data": {
                "course_type": "力量训练",
                "duration": 60,  # 60分钟
                "trainer": "李教练",
                "training_plan": "增肌计划"
            }
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_pt_001",
            "sender_nickname": "小张",
            "content": "1.28王先生私教课程300，李教练",
            "timestamp": datetime(2024, 1, 28, 14, 0, 0)
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
            assert float(record.amount) == 300.0
            assert float(record.commission_amount) == 120.0
            assert record.referral_channel is not None
            assert record.referral_channel.name == "李教练"
            assert record.referral_channel.channel_type == "internal"
            assert record.extra_data["course_type"] == "力量训练"
            assert record.extra_data["duration"] == 60
    
    def test_gym_membership_points(self, temp_db):
        """测试会员积分系统。"""
        customer = temp_db.get_or_create_customer("王先生")
        
        # 开卡
        membership_data = {
            "customer_name": "王先生",
            "date": "2024-01-01",
            "amount": 3000.0,
            "card_type": "年卡"
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_member_001",
            "sender_nickname": "小张",
            "content": "王先生开年卡3000",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0)
        })
        
        membership_id = temp_db.save_membership(membership_data, msg_id)
        
        # 设置初始积分
        with temp_db.get_session() as session:
            from db.models import Membership
            membership = session.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            membership.points = 300  # 开卡送300积分
            session.commit()
        
        # 使用插件数据存储积分历史
        temp_db.save_plugin_data(
            plugin_name="gym_points",
            entity_type="customer",
            entity_id=customer.id,
            data_key="points_history",
            data_value=[
                {"date": "2024-01-01", "points": 300, "reason": "开卡赠送"},
                {"date": "2024-01-28", "points": 30, "reason": "消费满300元"}
            ]
        )
        
        # 读取积分历史
        points_history = temp_db.get_plugin_data(
            "gym_points", "customer", customer.id, "points_history"
        )
        assert len(points_history) == 2
        assert points_history[0]["points"] == 300
        assert points_history[1]["points"] == 30
    
    def test_gym_product_sales(self, temp_db):
        """测试健身房商品销售。"""
        customer = temp_db.get_or_create_customer("王先生")
        
        # 创建商品
        protein = temp_db.get_or_create_product("蛋白粉", "supplement", 200.0)
        protein.extra_data = {
            "brand": "知名品牌",
            "flavor": "巧克力味",
            "weight": "2kg"
        }
        
        # 销售记录
        sale_data = {
            "service_or_product": "蛋白粉",
            "date": "2024-01-28",
            "amount": 200.0,
            "quantity": 1,
            "unit_price": 200.0,
            "customer_name": "王先生",
            "recorder_nickname": "小张"
        }
        
        msg_id = temp_db.save_raw_message({
            "wechat_msg_id": "msg_product_001",
            "sender_nickname": "小张",
            "content": "1.28王先生购买蛋白粉200",
            "timestamp": datetime(2024, 1, 28, 16, 0, 0)
        })
        
        sale_id = temp_db.save_product_sale(sale_data, msg_id)
        assert sale_id > 0
        
        # 验证销售记录
        with temp_db.get_session() as session:
            from db.models import ProductSale
            sale = session.query(ProductSale).filter(ProductSale.id == sale_id).first()
            assert sale is not None
            assert float(sale.total_amount) == 200.0
            assert sale.customer.name == "王先生"
            assert sale.product.name == "蛋白粉"
    
    def test_gym_referral_channels(self, temp_db):
        """测试健身房引流渠道。"""
        # 创建不同类型的渠道
        meituan = temp_db.get_or_create_referral_channel(
            "美团", "platform", commission_rate=15.0
        )
        friend = temp_db.get_or_create_referral_channel(
            "朋友推荐", "external", commission_rate=10.0
        )
        trainer_li = temp_db.get_or_create_referral_channel(
            "李教练", "internal", commission_rate=40.0
        )
        
        # 查询不同类型的渠道（需要确保数据已提交）
        with temp_db.get_session() as session:
            session.commit()  # 确保数据已提交
        
        platforms = temp_db.get_referral_channels(channel_type="platform")
        assert len(platforms) >= 1
        assert any(c.name == "美团" for c in platforms)
        
        internals = temp_db.get_referral_channels(channel_type="internal")
        assert len(internals) >= 1
        assert any(c.name == "李教练" for c in internals)
    
    def test_gym_complex_scenario(self, temp_db):
        """测试健身房复杂业务场景。"""
        # 场景：新会员通过美团引流，购买年卡，然后上私教课
        
        # 1. 创建美团渠道
        meituan = temp_db.get_or_create_referral_channel(
            "美团", "platform", commission_rate=15.0
        )
        
        # 2. 创建会员（通过美团引流）
        customer = temp_db.get_or_create_customer("新会员")
        # 在session内设置extra_data
        with temp_db.get_session() as session:
            from db.models import Customer
            customer_obj = session.query(Customer).filter(Customer.id == customer.id).first()
            customer_obj.extra_data = {
                "source": "美团",
                "referral_channel": "美团"
            }
            session.commit()
        
        # 3. 开年卡
        membership_data = {
            "customer_name": "新会员",
            "date": "2024-01-01",
            "amount": 3000.0,
            "card_type": "年卡"
        }
        
        msg_id1 = temp_db.save_raw_message({
            "wechat_msg_id": "msg_complex_001",
            "sender_nickname": "小张",
            "content": "新会员开年卡3000，美团引流",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0)
        })
        
        membership_id = temp_db.save_membership(membership_data, msg_id1)
        
        # 设置会员卡信息
        with temp_db.get_session() as session:
            from db.models import Membership
            membership = session.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            from datetime import timedelta
            membership.expires_at = membership.opened_at + timedelta(days=365)
            membership.points = 300
            session.commit()
        
        # 4. 上私教课
        trainer = temp_db.get_or_create_employee("李教练", "trainer_li")
        trainer_channel = temp_db.get_or_create_referral_channel(
            "李教练", "internal", commission_rate=40.0
        )
        personal_training = temp_db.get_or_create_service_type("私教课程", 300.0)
        
        record_data = {
            "customer_name": "新会员",
            "service_or_product": "私教课程",
            "date": "2024-01-05",
            "amount": 300.0,
            "commission": 120.0,
            "referral_channel_id": trainer_channel.id,
            "net_amount": 180.0,
            "membership_id": membership_id,
            "extra_data": {
                "course_type": "减脂",
                "duration": 60
            }
        }
        
        msg_id2 = temp_db.save_raw_message({
            "wechat_msg_id": "msg_complex_002",
            "sender_nickname": "小张",
            "content": "1.5新会员私教课程300",
            "timestamp": datetime(2024, 1, 5, 14, 0, 0)
        })
        
        record_id = temp_db.save_service_record(record_data, msg_id2)
        
        # 5. 验证完整流程
        with temp_db.get_session() as session:
            from db.models import Customer, Membership, ServiceRecord
            
            # 验证会员
            customer_obj = session.query(Customer).filter(
                Customer.id == customer.id
            ).first()
            assert customer_obj is not None
            assert customer_obj.extra_data["source"] == "美团"
            
            # 验证会员卡
            membership_obj = session.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            assert float(membership_obj.total_amount) == 3000.0
            assert membership_obj.points == 300
            assert membership_obj.expires_at is not None
            
            # 验证服务记录
            from sqlalchemy.orm import joinedload
            record_obj = session.query(ServiceRecord).options(
                joinedload(ServiceRecord.referral_channel)
            ).filter(ServiceRecord.id == record_id).first()
            assert record_obj is not None
            assert float(record_obj.amount) == 300.0
            assert record_obj.membership_id == membership_id
            assert record_obj.referral_channel is not None
            assert record_obj.referral_channel.name == "李教练"
            
            # 验证关联关系
            assert len(customer_obj.memberships) == 1
            assert len(customer_obj.service_records) == 1
            assert record_obj.customer.name == "新会员"
            assert record_obj.membership.customer.name == "新会员"

