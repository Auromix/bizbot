#!/usr/bin/env python3
"""健身房场景 —— Database + Agent 联合集成测试

使用真实 MiniMax API + 真实 SQLite 数据库，模拟健身房管理者的日常操作：
- 早间开门：查看昨日汇总、检查会员到期
- 上午营业：记录私教课、团课收入
- 中午时段：开会员卡、处理续卡
- 下午营业：记录商品销售、记录更多服务
- 傍晚时段：查询收入、统计提成
- 晚间收尾：生成日报、多轮复杂对话

运行方式：
    export MINIMAX_API_KEY='sk-api-...'
    pytest tests/test_gym_db_agent_integration.py -v -s

或直接运行：
    python tests/test_gym_db_agent_integration.py
"""
import os
import sys
import asyncio
import shutil
import tempfile
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent import Agent, create_provider
from agent.functions.registry import FunctionRegistry
from database import DatabaseManager
from database.models import (
    ServiceRecord, Membership, ProductSale, Customer,
    Employee, ReferralChannel, ServiceType, Product,
)

# ================================================================
# MiniMax API 配置
# ================================================================

MINIMAX_API_KEY = os.getenv(
    "MINIMAX_API_KEY",
    "sk-api-5f9qnjoJN8Ocha9Y4uyLkTW1s8aLUi4H5BqUm9htaW46_Qrx1GYlpGBFpu5wkmdjSdftmQjgff99iQ_sK8UFBrEnQ8eLiLBXLjxHyklQwyy1loOMOr4OOIo"
)
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

skip_no_key = pytest.mark.skipif(
    not MINIMAX_API_KEY,
    reason="需要 MINIMAX_API_KEY 环境变量",
)


# ================================================================
# 健身房业务函数 —— 直接操作真实数据库
# ================================================================

# 全局数据库实例（由 fixture 注入）
_db: Optional[DatabaseManager] = None


def _get_db() -> DatabaseManager:
    """获取数据库实例。"""
    assert _db is not None, "数据库未初始化"
    return _db


def record_service_income(
    customer_name: str,
    service_type: str,
    amount: float,
    date_str: Optional[str] = None,
    trainer_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """记录健身房服务收入（私教课、团课、体测等）。

    Args:
        customer_name: 顾客姓名（必填）
        service_type: 服务类型，如"私教课程"、"团课"、"体测"（必填）
        amount: 服务金额（必填）
        date_str: 日期，格式YYYY-MM-DD，默认今天
        trainer_name: 教练名称，如"李教练"（可选，私教课必填）
        notes: 备注信息（可选）
    """
    db = _get_db()
    try:
        service_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else date.today()
        )

        commission = 0.0
        referral_channel_id = None
        if trainer_name and "私教" in service_type:
            channel = db.channels.get_or_create(
                trainer_name, "internal", None, 40.0
            )
            referral_channel_id = channel.id
            commission = amount * 0.4

        msg_id = db.save_raw_message({
            "wechat_msg_id": f"gym_svc_{datetime.now().timestamp()}",
            "sender_nickname": "健身房管理员",
            "content": f"{customer_name} {service_type} {amount}元",
            "timestamp": datetime.now(),
        })

        record_id = db.save_service_record(
            {
                "customer_name": customer_name,
                "service_or_product": service_type,
                "date": service_date,
                "amount": amount,
                "commission": commission,
                "referral_channel_id": referral_channel_id,
                "net_amount": amount - commission,
                "notes": notes,
                "confirmed": True,
            },
            msg_id,
        )

        return {
            "success": True,
            "record_id": record_id,
            "customer": customer_name,
            "service": service_type,
            "amount": amount,
            "commission": commission,
            "net_income": amount - commission,
            "date": str(service_date),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def open_membership_card(
    customer_name: str,
    card_type: str,
    amount: float,
    date_str: Optional[str] = None,
) -> dict:
    """为顾客开通健身房会员卡。

    Args:
        customer_name: 顾客姓名（必填）
        card_type: 卡类型，如"年卡"、"季卡"、"月卡"、"次卡"（必填）
        amount: 充值金额（必填）
        date_str: 开卡日期，格式YYYY-MM-DD，默认今天
    """
    db = _get_db()
    try:
        opened_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else date.today()
        )

        days_map = {"年卡": 365, "季卡": 90, "月卡": 30, "次卡": 365}
        days = days_map.get(card_type, 30)

        msg_id = db.save_raw_message({
            "wechat_msg_id": f"gym_mem_{datetime.now().timestamp()}",
            "sender_nickname": "健身房管理员",
            "content": f"{customer_name}开{card_type}{amount}元",
            "timestamp": datetime.now(),
        })

        membership_id = db.save_membership(
            {
                "customer_name": customer_name,
                "card_type": card_type,
                "date": opened_date,
                "amount": amount,
            },
            msg_id,
        )

        # 设置有效期和积分
        with db.get_session() as session:
            membership = session.query(Membership).filter(
                Membership.id == membership_id
            ).first()
            membership.expires_at = opened_date + timedelta(days=days)
            membership.points = int(amount / 10)
            session.commit()

        return {
            "success": True,
            "membership_id": membership_id,
            "customer": customer_name,
            "card_type": card_type,
            "amount": amount,
            "valid_days": days,
            "expires_at": str(opened_date + timedelta(days=days)),
            "points": int(amount / 10),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def record_product_sale(
    product_name: str,
    amount: float,
    customer_name: Optional[str] = None,
    quantity: int = 1,
    date_str: Optional[str] = None,
) -> dict:
    """记录健身房商品销售（蛋白粉、运动装备等）。

    Args:
        product_name: 商品名称（必填）
        amount: 总金额（必填）
        customer_name: 顾客姓名（可选）
        quantity: 数量，默认1
        date_str: 日期，格式YYYY-MM-DD，默认今天
    """
    db = _get_db()
    try:
        sale_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else date.today()
        )

        msg_id = db.save_raw_message({
            "wechat_msg_id": f"gym_prod_{datetime.now().timestamp()}",
            "sender_nickname": "健身房管理员",
            "content": f"{customer_name or '顾客'}购买{product_name}{amount}元",
            "timestamp": datetime.now(),
        })

        sale_id = db.save_product_sale(
            {
                "service_or_product": product_name,
                "date": sale_date,
                "amount": amount,
                "quantity": quantity,
                "unit_price": amount / quantity,
                "customer_name": customer_name,
                "confirmed": True,
            },
            msg_id,
        )

        return {
            "success": True,
            "sale_id": sale_id,
            "product": product_name,
            "quantity": quantity,
            "amount": amount,
            "customer": customer_name or "散客",
            "date": str(sale_date),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_daily_income(date_str: Optional[str] = None) -> dict:
    """查询健身房指定日期的收入统计。

    Args:
        date_str: 日期，格式YYYY-MM-DD，默认今天
    返回当天的服务收入、商品收入、提成支出和净收入。
    """
    db = _get_db()
    try:
        query_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else date.today()
        )

        with db.get_session() as session:
            from sqlalchemy import func

            svc = session.query(
                func.count(ServiceRecord.id).label("count"),
                func.coalesce(func.sum(ServiceRecord.amount), 0).label("total"),
                func.coalesce(func.sum(ServiceRecord.commission_amount), 0).label("commission"),
                func.coalesce(func.sum(ServiceRecord.net_amount), 0).label("net"),
            ).filter(ServiceRecord.service_date == query_date).first()

            prod = session.query(
                func.count(ProductSale.id).label("count"),
                func.coalesce(func.sum(ProductSale.total_amount), 0).label("total"),
            ).filter(ProductSale.sale_date == query_date).first()

            records = db.get_daily_records(query_date)

        return {
            "date": str(query_date),
            "service": {
                "count": svc.count,
                "revenue": float(svc.total),
                "commission": float(svc.commission),
                "net": float(svc.net),
            },
            "product": {
                "count": prod.count,
                "revenue": float(prod.total),
            },
            "total_revenue": float(svc.total) + float(prod.total),
            "total_commission": float(svc.commission),
            "total_net": float(svc.net) + float(prod.total),
            "records": records[:10],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_member_info(customer_name: str) -> dict:
    """查询健身房会员信息。

    Args:
        customer_name: 顾客姓名（必填）
    返回顾客的所有会员卡、余额、有效期、积分等信息。
    """
    db = _get_db()
    try:
        with db.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.name == customer_name
            ).first()

            if not customer:
                return {"success": False, "message": f"未找到会员：{customer_name}"}

            memberships = []
            for m in customer.memberships:
                memberships.append({
                    "card_type": m.card_type,
                    "balance": float(m.balance),
                    "total_amount": float(m.total_amount),
                    "opened_at": str(m.opened_at),
                    "expires_at": str(m.expires_at) if m.expires_at else None,
                    "points": m.points,
                    "is_active": m.is_active,
                    "remaining_sessions": m.remaining_sessions,
                })

            service_count = len(customer.service_records)
            product_count = len(customer.product_sales)

        return {
            "success": True,
            "customer": customer_name,
            "memberships": memberships,
            "statistics": {
                "total_cards": len(memberships),
                "service_count": service_count,
                "product_count": product_count,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_trainer_commission(
    trainer_name: Optional[str] = None,
    date_str: Optional[str] = None,
) -> dict:
    """查询私教提成统计。

    Args:
        trainer_name: 私教姓名，如"李教练"（可选，不填则查询所有私教）
        date_str: 日期，格式YYYY-MM-DD（可选，不填则查询所有日期）
    返回私教的课时数和提成金额。
    """
    db = _get_db()
    try:
        with db.get_session() as session:
            from sqlalchemy import func

            query = session.query(
                ReferralChannel.name.label("trainer"),
                func.count(ServiceRecord.id).label("count"),
                func.coalesce(
                    func.sum(ServiceRecord.commission_amount), 0
                ).label("total_commission"),
            ).join(
                ServiceRecord,
                ServiceRecord.referral_channel_id == ReferralChannel.id,
            ).filter(
                ReferralChannel.channel_type == "internal",
            )

            if trainer_name:
                query = query.filter(ReferralChannel.name == trainer_name)
            if date_str:
                qd = datetime.strptime(date_str, "%Y-%m-%d").date()
                query = query.filter(ServiceRecord.service_date == qd)

            query = query.group_by(ReferralChannel.name)
            results = query.all()

            commissions = []
            total = 0.0
            for r in results:
                amt = float(r.total_commission)
                commissions.append({
                    "trainer": r.trainer,
                    "session_count": r.count,
                    "commission": amt,
                })
                total += amt

        return {
            "success": True,
            "date": date_str or "所有日期",
            "trainers": commissions,
            "total_commission": total,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_expiring_members(days: int = 7) -> dict:
    """查询即将到期的会员卡。

    Args:
        days: 查询未来多少天内到期的会员卡，默认7天
    返回即将到期的会员列表。
    """
    db = _get_db()
    try:
        today = date.today()
        deadline = today + timedelta(days=days)

        with db.get_session() as session:
            expiring = session.query(Membership).filter(
                Membership.is_active == True,
                Membership.expires_at != None,
                Membership.expires_at <= deadline,
                Membership.expires_at >= today,
            ).all()

            results = []
            for m in expiring:
                results.append({
                    "customer": m.customer.name if m.customer else "未知",
                    "card_type": m.card_type,
                    "expires_at": str(m.expires_at),
                    "balance": float(m.balance),
                    "days_left": (m.expires_at - today).days,
                })

        return {
            "success": True,
            "expiring_count": len(results),
            "members": results,
            "check_range_days": days,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_staff_list() -> dict:
    """获取健身房员工/教练列表。

    返回所有在职员工的姓名、角色和提成率。
    """
    db = _get_db()
    try:
        staff = db.get_staff_list(active_only=True)
        return {
            "success": True,
            "staff_count": len(staff),
            "staff": staff,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ================================================================
# Fixtures
# ================================================================

@pytest.fixture(scope="module")
def gym_database():
    """创建健身房测试数据库（模块级共享）。"""
    temp_dir = tempfile.mkdtemp(prefix="gym-integration-")
    db_path = os.path.join(temp_dir, "gym_test.db")
    db_url = f"sqlite:///{db_path}"

    db = DatabaseManager(database_url=db_url)
    db.create_tables()

    # 初始化健身房基础数据
    with db.get_session() as session:
        # 教练/员工
        trainer_li = db.staff.get_or_create("李教练", "trainer_li", session=session)
        trainer_li.role = "manager"
        trainer_li.commission_rate = 40.0

        trainer_wang = db.staff.get_or_create("王教练", "trainer_wang", session=session)
        trainer_wang.role = "staff"
        trainer_wang.commission_rate = 35.0

        receptionist = db.staff.get_or_create("前台小张", "reception_zhang", session=session)
        receptionist.role = "staff"

        # 服务类型
        db.service_types.get_or_create("私教课程", 300.0, "training", session=session)
        db.service_types.get_or_create("团课", 50.0, "class", session=session)
        db.service_types.get_or_create("体测", 100.0, "assessment", session=session)
        db.service_types.get_or_create("游泳课", 200.0, "swimming", session=session)

        # 商品
        db.products.get_or_create("蛋白粉", "supplement", 200.0, session=session)
        db.products.get_or_create("运动护腕", "equipment", 50.0, session=session)
        db.products.get_or_create("运动水壶", "equipment", 80.0, session=session)
        db.products.get_or_create("健身手套", "equipment", 60.0, session=session)
        db.products.get_or_create("BCAA氨基酸", "supplement", 150.0, session=session)

        # 引流渠道
        db.channels.get_or_create("美团", "platform", None, 15.0, session=session)
        db.channels.get_or_create("大众点评", "platform", None, 12.0, session=session)
        db.channels.get_or_create("朋友推荐", "external", None, 10.0, session=session)

        session.commit()

    # 设置全局数据库
    global _db
    _db = db

    yield db

    # 清理
    _db = None
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def gym_registry():
    """创建注册了所有健身房业务函数的 FunctionRegistry。"""
    registry = FunctionRegistry()

    registry.register(
        "record_service_income",
        "记录健身房服务收入（私教课、团课、体测、游泳课等）。"
        "参数: customer_name(顾客姓名), service_type(服务类型), amount(金额), "
        "date_str(日期YYYY-MM-DD,默认今天), trainer_name(教练名称,可选), notes(备注,可选)",
        record_service_income,
        {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "顾客姓名"},
                "service_type": {"type": "string", "description": "服务类型，如：私教课程、团课、体测、游泳课"},
                "amount": {"type": "number", "description": "金额（元）"},
                "date_str": {"type": "string", "description": "日期，格式YYYY-MM-DD，默认今天"},
                "trainer_name": {"type": "string", "description": "教练名称，如：李教练、王教练"},
                "notes": {"type": "string", "description": "备注信息"},
            },
            "required": ["customer_name", "service_type", "amount"],
        },
    )

    registry.register(
        "open_membership_card",
        "为顾客开通健身房会员卡。"
        "参数: customer_name(顾客姓名), card_type(年卡/季卡/月卡/次卡), amount(充值金额), "
        "date_str(开卡日期YYYY-MM-DD,默认今天)",
        open_membership_card,
        {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "顾客姓名"},
                "card_type": {"type": "string", "description": "卡类型：年卡、季卡、月卡、次卡"},
                "amount": {"type": "number", "description": "充值金额（元）"},
                "date_str": {"type": "string", "description": "开卡日期，格式YYYY-MM-DD，默认今天"},
            },
            "required": ["customer_name", "card_type", "amount"],
        },
    )

    registry.register(
        "record_product_sale",
        "记录健身房商品销售（蛋白粉、运动装备等）。"
        "参数: product_name(商品名称), amount(总金额), customer_name(顾客姓名,可选), "
        "quantity(数量,默认1), date_str(日期YYYY-MM-DD,默认今天)",
        record_product_sale,
        {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "商品名称，如：蛋白粉、运动护腕"},
                "amount": {"type": "number", "description": "总金额（元）"},
                "customer_name": {"type": "string", "description": "顾客姓名（可选）"},
                "quantity": {"type": "integer", "description": "数量，默认1"},
                "date_str": {"type": "string", "description": "日期，格式YYYY-MM-DD，默认今天"},
            },
            "required": ["product_name", "amount"],
        },
    )

    registry.register(
        "query_daily_income",
        "查询健身房指定日期的收入统计（服务收入、商品收入、提成、净收入）。"
        "参数: date_str(日期YYYY-MM-DD,默认今天)",
        query_daily_income,
        {
            "type": "object",
            "properties": {
                "date_str": {"type": "string", "description": "日期，格式YYYY-MM-DD，默认今天"},
            },
            "required": [],
        },
    )

    registry.register(
        "query_member_info",
        "查询健身房会员信息（会员卡、余额、有效期、积分、消费记录）。"
        "参数: customer_name(顾客姓名)",
        query_member_info,
        {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "顾客姓名"},
            },
            "required": ["customer_name"],
        },
    )

    registry.register(
        "query_trainer_commission",
        "查询私教提成统计。"
        "参数: trainer_name(私教姓名,可选), date_str(日期YYYY-MM-DD,可选)",
        query_trainer_commission,
        {
            "type": "object",
            "properties": {
                "trainer_name": {"type": "string", "description": "私教姓名，如：李教练"},
                "date_str": {"type": "string", "description": "日期，格式YYYY-MM-DD"},
            },
            "required": [],
        },
    )

    registry.register(
        "query_expiring_members",
        "查询即将到期的健身房会员卡。"
        "参数: days(查询未来多少天内到期,默认7天)",
        query_expiring_members,
        {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "查询未来多少天内到期的会员卡，默认7"},
            },
            "required": [],
        },
    )

    registry.register(
        "get_staff_list",
        "获取健身房员工/教练列表。返回所有在职员工信息。",
        get_staff_list,
        {
            "type": "object",
            "properties": {},
            "required": [],
        },
    )

    return registry


@pytest.fixture
def gym_agent(gym_registry):
    """创建健身房管理 Agent（使用 MiniMax）。"""
    provider = create_provider(
        "minimax",
        api_key=MINIMAX_API_KEY,
        model=MINIMAX_MODEL,
    )

    agent = Agent(
        provider,
        function_registry=gym_registry,
        system_prompt="""你是一家健身房的智能管理助手。你帮助健身房老板/管理者处理日常经营事务：

1. **记录收入**：私教课（提成40%给教练）、团课（无提成）、体测、游泳课等
2. **会员管理**：开会员卡（年卡365天/季卡90天/月卡30天，每10元1积分）、查询会员信息、检查到期会员
3. **商品销售**：蛋白粉、运动装备等商品销售记录
4. **数据统计**：日收入汇总、教练提成统计、员工列表查询

重要规则：
- 私教课程提成率为40%，团课和其他课程无提成
- 记录私教课时必须指定教练名称
- 认真理解用户的自然语言，准确调用对应工具
- 用中文简洁回复，包含关键数字
- 如果一句话包含多个操作，依次调用对应函数""",
    )
    return agent


# ================================================================
# 测试类：模拟健身房管理者一天的日常操作
# ================================================================

@skip_no_key
class TestGymDailyOperations:
    """健身房管理者日常操作 —— Database + Agent 联合测试。

    按照健身房管理者一天的工作流程编排测试用例，
    每个测试验证 Agent 能否正确理解自然语言并操作真实数据库。
    """

    # ---- 早间：记录第一笔私教课 ----

    @pytest.mark.asyncio
    async def test_01_morning_private_training(self, gym_agent, gym_database):
        """早上第一节：张伟上了李教练的私教课，300元。"""
        print("\n" + "=" * 60)
        print("场景 1: 早间 - 记录私教课")
        print("=" * 60)

        response = await gym_agent.chat(
            "早上好，张伟刚上完李教练的私教课，收费300元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        # 验证 Agent 调用了正确的函数
        assert len(response["function_calls"]) > 0, "应该调用了工具"
        assert any(
            fc["name"] == "record_service_income"
            for fc in response["function_calls"]
        ), "应该调用 record_service_income"

        # 验证数据库
        with gym_database.get_session() as session:
            records = session.query(ServiceRecord).filter(
                ServiceRecord.service_date == date.today()
            ).all()
            assert len(records) >= 1, "数据库应有服务记录"

            # 找到张伟的记录
            zw_record = None
            for r in records:
                if r.customer and r.customer.name == "张伟":
                    zw_record = r
                    break
            assert zw_record is not None, "应有张伟的服务记录"
            assert float(zw_record.amount) == 300.0, "金额应为300"
            assert float(zw_record.commission_amount) == 120.0, "私教提成应为120（40%）"

        print("✅ 早间私教课记录通过")

    # ---- 上午：开会员卡 ----

    @pytest.mark.asyncio
    async def test_02_open_annual_membership(self, gym_agent, gym_database):
        """上午：刘芳来办年卡，充值5000元。"""
        print("\n" + "=" * 60)
        print("场景 2: 上午 - 开年卡")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "刘芳要办一张年卡，充值5000元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "open_membership_card"
            for fc in response["function_calls"]
        ), "应该调用 open_membership_card"

        # 验证数据库
        with gym_database.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.name == "刘芳"
            ).first()
            assert customer is not None, "应创建刘芳的顾客记录"

            membership = session.query(Membership).filter(
                Membership.customer_id == customer.id
            ).first()
            assert membership is not None, "应创建会员卡"
            assert float(membership.total_amount) == 5000.0, "充值金额应为5000"
            assert membership.points == 500, "积分应为500（5000/10）"
            assert membership.expires_at is not None, "应设置到期日期"

        print("✅ 开年卡通过")

    # ---- 上午：开季卡 ----

    @pytest.mark.asyncio
    async def test_03_open_quarterly_membership(self, gym_agent, gym_database):
        """上午：陈强要办季卡，充值2000元。"""
        print("\n" + "=" * 60)
        print("场景 3: 上午 - 开季卡")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "陈强办一张季卡，2000块",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "open_membership_card"
            for fc in response["function_calls"]
        )

        with gym_database.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.name == "陈强"
            ).first()
            assert customer is not None
            membership = session.query(Membership).filter(
                Membership.customer_id == customer.id
            ).first()
            assert membership is not None
            assert float(membership.total_amount) == 2000.0

        print("✅ 开季卡通过")

    # ---- 中午：记录团课 ----

    @pytest.mark.asyncio
    async def test_04_group_class(self, gym_agent, gym_database):
        """中午：赵磊上了团课，50元（无教练提成）。"""
        print("\n" + "=" * 60)
        print("场景 4: 中午 - 记录团课")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "赵磊参加了今天的团课，收费50元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "record_service_income"
            for fc in response["function_calls"]
        )

        # 验证团课没有提成
        with gym_database.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.name == "赵磊"
            ).first()
            if customer:
                record = session.query(ServiceRecord).filter(
                    ServiceRecord.customer_id == customer.id,
                    ServiceRecord.service_date == date.today(),
                ).first()
                if record:
                    # 团课不应有提成（或提成为0）
                    assert float(record.commission_amount) == 0.0, "团课不应有提成"

        print("✅ 团课记录通过")

    # ---- 下午：记录商品销售 ----

    @pytest.mark.asyncio
    async def test_05_product_sale_protein(self, gym_agent, gym_database):
        """下午：张伟买了一桶蛋白粉，200元。"""
        print("\n" + "=" * 60)
        print("场景 5: 下午 - 商品销售（蛋白粉）")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "张伟买了一桶蛋白粉，200块钱",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "record_product_sale"
            for fc in response["function_calls"]
        )

        with gym_database.get_session() as session:
            sales = session.query(ProductSale).filter(
                ProductSale.sale_date == date.today()
            ).all()
            assert len(sales) >= 1, "应有商品销售记录"

        print("✅ 商品销售（蛋白粉）通过")

    # ---- 下午：又一节私教课 ----

    @pytest.mark.asyncio
    async def test_06_afternoon_private_training(self, gym_agent, gym_database):
        """下午：刘芳上了王教练的私教课，350元。"""
        print("\n" + "=" * 60)
        print("场景 6: 下午 - 又一节私教课")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "刘芳下午上了王教练的私教课，收费350元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "record_service_income"
            for fc in response["function_calls"]
        )

        print("✅ 下午私教课通过")

    # ---- 下午：多件商品销售 ----

    @pytest.mark.asyncio
    async def test_07_multi_product_sale(self, gym_agent, gym_database):
        """下午：陈强买了两副健身手套，共120元。"""
        print("\n" + "=" * 60)
        print("场景 7: 下午 - 多件商品销售")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "陈强买了2副健身手套，总共120元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "record_product_sale"
            for fc in response["function_calls"]
        )

        print("✅ 多件商品销售通过")

    # ---- 傍晚：查询今日收入 ----

    @pytest.mark.asyncio
    async def test_08_query_daily_income(self, gym_agent, gym_database):
        """傍晚：管理者想看看今天的收入情况。"""
        print("\n" + "=" * 60)
        print("场景 8: 傍晚 - 查询今日收入")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "帮我看看今天健身房一共收入多少",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "query_daily_income"
            for fc in response["function_calls"]
        ), "应调用 query_daily_income"

        # 回复应包含收入相关信息
        content = response["content"]
        assert any(
            kw in content for kw in ["收入", "元", "营收", "总计", "合计"]
        ), "回复应包含收入信息"

        print("✅ 查询今日收入通过")

    # ---- 傍晚：查询会员信息 ----

    @pytest.mark.asyncio
    async def test_09_query_member_info(self, gym_agent, gym_database):
        """傍晚：查询刘芳的会员信息。"""
        print("\n" + "=" * 60)
        print("场景 9: 傍晚 - 查询会员信息")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "查一下刘芳的会员卡信息",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "query_member_info"
            for fc in response["function_calls"]
        )
        assert "刘芳" in response["content"], "回复应包含刘芳"

        print("✅ 查询会员信息通过")

    # ---- 傍晚：查询教练提成 ----

    @pytest.mark.asyncio
    async def test_10_query_trainer_commission(self, gym_agent, gym_database):
        """傍晚：统计李教练今天的提成。"""
        print("\n" + "=" * 60)
        print("场景 10: 傍晚 - 查询教练提成")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "统计一下李教练今天的提成有多少",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "query_trainer_commission"
            for fc in response["function_calls"]
        )
        assert any(
            kw in response["content"]
            for kw in ["李教练", "提成", "元"]
        ), "回复应包含提成信息"

        print("✅ 查询教练提成通过")

    # ---- 傍晚：查询员工列表 ----

    @pytest.mark.asyncio
    async def test_11_query_staff_list(self, gym_agent, gym_database):
        """傍晚：查看健身房有哪些教练。"""
        print("\n" + "=" * 60)
        print("场景 11: 傍晚 - 查询员工列表")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "我们健身房现在有哪些教练和员工？",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        assert any(
            fc["name"] == "get_staff_list"
            for fc in response["function_calls"]
        )

        print("✅ 查询员工列表通过")


@skip_no_key
class TestGymComplexScenarios:
    """健身房复杂场景测试 —— 多轮对话、批量操作、综合查询。"""

    # ---- 一句话记录多笔业务 ----

    @pytest.mark.asyncio
    async def test_12_batch_record(self, gym_agent, gym_database):
        """一句话包含多笔业务：两个人上了私教课。"""
        print("\n" + "=" * 60)
        print("场景 12: 复杂 - 批量记录")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "今天下午有两个人上了李教练的私教课：孙悟空300元，猪八戒280元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")
        print(f"工具调用: {[fc['name'] for fc in response['function_calls']]}")

        # 应该至少调用了2次 record_service_income
        svc_calls = [
            fc for fc in response["function_calls"]
            if fc["name"] == "record_service_income"
        ]
        assert len(svc_calls) >= 2, f"应至少调用2次 record_service_income，实际 {len(svc_calls)} 次"

        print("✅ 批量记录通过")

    # ---- 多轮对话：先记录再查询 ----

    @pytest.mark.asyncio
    async def test_13_multi_turn_record_then_query(self, gym_agent, gym_database):
        """多轮对话：先记录一笔，再查询当天收入。"""
        print("\n" + "=" * 60)
        print("场景 13: 复杂 - 多轮对话（记录+查询）")
        print("=" * 60)

        gym_agent.clear_history()

        # 第1轮：记录
        print("\n[轮次 1] 记录服务")
        r1 = await gym_agent.chat(
            "唐僧刚上完李教练的私教课，收费320元",
            temperature=0.1,
        )
        print(f"Agent: {r1['content']}")
        assert any(
            fc["name"] == "record_service_income"
            for fc in r1["function_calls"]
        )

        # 第2轮：查询（同一个 Agent，保持上下文）
        print("\n[轮次 2] 查询收入")
        r2 = await gym_agent.chat(
            "那现在今天一共收入多少了？",
            temperature=0.1,
        )
        print(f"Agent: {r2['content']}")
        assert any(
            fc["name"] == "query_daily_income"
            for fc in r2["function_calls"]
        )

        print("✅ 多轮对话（记录+查询）通过")

    # ---- 多轮对话：开卡后查询会员信息 ----

    @pytest.mark.asyncio
    async def test_14_multi_turn_membership_then_query(self, gym_agent, gym_database):
        """多轮对话：先开卡，再查询该会员信息。"""
        print("\n" + "=" * 60)
        print("场景 14: 复杂 - 多轮对话（开卡+查询）")
        print("=" * 60)

        gym_agent.clear_history()

        # 第1轮：开卡
        print("\n[轮次 1] 开会员卡")
        r1 = await gym_agent.chat(
            "沙悟净要办一张月卡，充值800元",
            temperature=0.1,
        )
        print(f"Agent: {r1['content']}")
        assert any(
            fc["name"] == "open_membership_card"
            for fc in r1["function_calls"]
        )

        # 第2轮：查询
        print("\n[轮次 2] 查询会员信息")
        r2 = await gym_agent.chat(
            "帮我看看沙悟净的会员卡信息",
            temperature=0.1,
        )
        print(f"Agent: {r2['content']}")
        assert any(
            fc["name"] == "query_member_info"
            for fc in r2["function_calls"]
        )
        assert "沙悟净" in r2["content"]

        print("✅ 多轮对话（开卡+查询）通过")

    # ---- 综合场景：记录+销售+查询 ----

    @pytest.mark.asyncio
    async def test_15_comprehensive_workflow(self, gym_agent, gym_database):
        """综合场景：记录服务 → 卖商品 → 查询汇总。"""
        print("\n" + "=" * 60)
        print("场景 15: 复杂 - 综合工作流")
        print("=" * 60)

        gym_agent.clear_history()

        # 第1轮：记录私教课
        print("\n[轮次 1] 记录私教课")
        r1 = await gym_agent.chat(
            "白龙马上了王教练的私教课，收费280元",
            temperature=0.1,
        )
        print(f"Agent: {r1['content']}")

        # 第2轮：记录商品销售
        print("\n[轮次 2] 记录商品销售")
        r2 = await gym_agent.chat(
            "白龙马还买了一瓶BCAA氨基酸，150元",
            temperature=0.1,
        )
        print(f"Agent: {r2['content']}")

        # 第3轮：查询当日汇总
        print("\n[轮次 3] 查询汇总")
        r3 = await gym_agent.chat(
            "今天的收入情况怎么样？给我一个汇总",
            temperature=0.1,
        )
        print(f"Agent: {r3['content']}")

        assert any(
            fc["name"] == "query_daily_income"
            for fc in r3["function_calls"]
        )

        print("✅ 综合工作流通过")


@skip_no_key
class TestGymDataIntegrity:
    """数据完整性验证 —— 确保 Agent 操作后数据库状态正确。"""

    @pytest.mark.asyncio
    async def test_16_verify_commission_calculation(self, gym_agent, gym_database):
        """验证私教课提成计算准确（40%）。"""
        print("\n" + "=" * 60)
        print("场景 16: 数据完整性 - 提成计算")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "铁扇公主上了李教练的私教课，收费500元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")

        with gym_database.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.name == "铁扇公主"
            ).first()
            assert customer is not None

            record = session.query(ServiceRecord).filter(
                ServiceRecord.customer_id == customer.id,
                ServiceRecord.service_date == date.today(),
            ).first()
            assert record is not None
            assert float(record.amount) == 500.0, "金额应为500"
            assert float(record.commission_amount) == 200.0, "提成应为200（40%）"
            assert float(record.net_amount) == 300.0, "净收入应为300"

        print("✅ 提成计算验证通过")

    @pytest.mark.asyncio
    async def test_17_verify_membership_points(self, gym_agent, gym_database):
        """验证会员卡积分计算准确（每10元1积分）。"""
        print("\n" + "=" * 60)
        print("场景 17: 数据完整性 - 积分计算")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "牛魔王要办一张年卡，充值8000元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")

        with gym_database.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.name == "牛魔王"
            ).first()
            assert customer is not None

            membership = session.query(Membership).filter(
                Membership.customer_id == customer.id,
            ).first()
            assert membership is not None
            assert float(membership.total_amount) == 8000.0
            assert float(membership.balance) == 8000.0
            assert membership.points == 800, "积分应为800（8000/10）"

            # 验证有效期
            expected_expires = date.today() + timedelta(days=365)
            assert membership.expires_at == expected_expires, \
                f"年卡到期日应为 {expected_expires}，实际 {membership.expires_at}"

        print("✅ 积分计算验证通过")

    @pytest.mark.asyncio
    async def test_18_verify_product_sale_record(self, gym_agent, gym_database):
        """验证商品销售记录正确写入数据库。"""
        print("\n" + "=" * 60)
        print("场景 18: 数据完整性 - 商品销售记录")
        print("=" * 60)

        gym_agent.clear_history()

        response = await gym_agent.chat(
            "红孩儿买了一个运动水壶，80元",
            temperature=0.1,
        )

        print(f"Agent: {response['content']}")

        with gym_database.get_session() as session:
            customer = session.query(Customer).filter(
                Customer.name == "红孩儿"
            ).first()
            assert customer is not None

            sale = session.query(ProductSale).filter(
                ProductSale.customer_id == customer.id,
                ProductSale.sale_date == date.today(),
            ).first()
            assert sale is not None
            assert float(sale.total_amount) == 80.0, "销售金额应为80"

        print("✅ 商品销售记录验证通过")


# ================================================================
# 主函数（可直接运行）
# ================================================================

async def main():
    """直接运行所有测试场景。"""
    print("=" * 60)
    print("健身房 Database + Agent 联合集成测试")
    print("=" * 60)
    print(f"MiniMax Model: {MINIMAX_MODEL}")
    print(f"API Key: {MINIMAX_API_KEY[:20]}..." if MINIMAX_API_KEY else "API Key: 未设置")
    print()

    if not MINIMAX_API_KEY:
        print("❌ 未设置 MINIMAX_API_KEY 环境变量")
        return False

    # 初始化数据库
    temp_dir = tempfile.mkdtemp(prefix="gym-integration-")
    db_path = os.path.join(temp_dir, "gym_test.db")
    db_url = f"sqlite:///{db_path}"

    db = DatabaseManager(database_url=db_url)
    db.create_tables()

    # 初始化基础数据
    with db.get_session() as session:
        trainer_li = db.staff.get_or_create("李教练", "trainer_li", session=session)
        trainer_li.role = "manager"
        trainer_li.commission_rate = 40.0

        trainer_wang = db.staff.get_or_create("王教练", "trainer_wang", session=session)
        trainer_wang.role = "staff"
        trainer_wang.commission_rate = 35.0

        receptionist = db.staff.get_or_create("前台小张", "reception_zhang", session=session)
        receptionist.role = "staff"

        db.service_types.get_or_create("私教课程", 300.0, "training", session=session)
        db.service_types.get_or_create("团课", 50.0, "class", session=session)
        db.service_types.get_or_create("体测", 100.0, "assessment", session=session)

        db.products.get_or_create("蛋白粉", "supplement", 200.0, session=session)
        db.products.get_or_create("运动护腕", "equipment", 50.0, session=session)
        db.products.get_or_create("运动水壶", "equipment", 80.0, session=session)
        db.products.get_or_create("健身手套", "equipment", 60.0, session=session)
        db.products.get_or_create("BCAA氨基酸", "supplement", 150.0, session=session)

        db.channels.get_or_create("美团", "platform", None, 15.0, session=session)

        session.commit()

    global _db
    _db = db

    # 创建 Agent
    registry = FunctionRegistry()
    for name, desc, func, params in [
        ("record_service_income", "记录服务收入", record_service_income,
         {"type": "object", "properties": {
             "customer_name": {"type": "string"}, "service_type": {"type": "string"},
             "amount": {"type": "number"}, "date_str": {"type": "string"},
             "trainer_name": {"type": "string"}, "notes": {"type": "string"},
         }, "required": ["customer_name", "service_type", "amount"]}),
        ("open_membership_card", "开会员卡", open_membership_card,
         {"type": "object", "properties": {
             "customer_name": {"type": "string"}, "card_type": {"type": "string"},
             "amount": {"type": "number"}, "date_str": {"type": "string"},
         }, "required": ["customer_name", "card_type", "amount"]}),
        ("record_product_sale", "记录商品销售", record_product_sale,
         {"type": "object", "properties": {
             "product_name": {"type": "string"}, "amount": {"type": "number"},
             "customer_name": {"type": "string"}, "quantity": {"type": "integer"},
             "date_str": {"type": "string"},
         }, "required": ["product_name", "amount"]}),
        ("query_daily_income", "查询每日收入", query_daily_income,
         {"type": "object", "properties": {
             "date_str": {"type": "string"},
         }, "required": []}),
        ("query_member_info", "查询会员信息", query_member_info,
         {"type": "object", "properties": {
             "customer_name": {"type": "string"},
         }, "required": ["customer_name"]}),
        ("query_trainer_commission", "查询教练提成", query_trainer_commission,
         {"type": "object", "properties": {
             "trainer_name": {"type": "string"}, "date_str": {"type": "string"},
         }, "required": []}),
        ("get_staff_list", "获取员工列表", get_staff_list,
         {"type": "object", "properties": {}, "required": []}),
    ]:
        registry.register(name, desc, func, params)

    provider = create_provider("minimax", api_key=MINIMAX_API_KEY, model=MINIMAX_MODEL)
    agent = Agent(
        provider,
        function_registry=registry,
        system_prompt="""你是一家健身房的智能管理助手。帮助健身房管理者：
1. 记录收入（私教课提成40%、团课无提成）
2. 会员管理（年卡365天/季卡90天/月卡30天，每10元1积分）
3. 商品销售记录
4. 数据统计查询

规则：私教课提成40%，团课无提成。认真理解自然语言，准确调用工具。""",
    )

    # 运行场景
    scenarios = [
        ("记录私教课", "张伟上了李教练的私教课，收费300元"),
        ("开年卡", "刘芳要办一张年卡，充值5000元"),
        ("记录团课", "赵磊参加了团课，收费50元"),
        ("商品销售", "张伟买了一桶蛋白粉，200元"),
        ("查询今日收入", "帮我看看今天的收入情况"),
        ("查询会员信息", "查一下刘芳的会员卡信息"),
        ("查询教练提成", "统计一下李教练今天的提成"),
        ("查询员工列表", "我们健身房有哪些教练？"),
        ("批量记录", "孙悟空300元、猪八戒280元，都上了李教练的私教课"),
    ]

    passed = 0
    failed = 0

    for name, user_input in scenarios:
        print(f"\n{'=' * 60}")
        print(f"场景: {name}")
        print(f"{'=' * 60}")
        print(f"👤 管理者: {user_input}")

        try:
            agent.clear_history()
            response = await agent.chat(user_input, temperature=0.1)
            print(f"🤖 助手: {response['content']}")
            if response["function_calls"]:
                print(f"📞 工具: {[fc['name'] for fc in response['function_calls']]}")
            passed += 1
            print("✅ 通过")
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

        await asyncio.sleep(1)  # 避免请求过快

    # 总结
    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")
    print(f"通过: {passed}/{len(scenarios)}")
    print(f"失败: {failed}/{len(scenarios)}")

    if failed == 0:
        print("\n🎉 所有场景测试通过！")
    else:
        print(f"\n⚠️  有 {failed} 个场景失败")

    # 清理
    _db = None
    shutil.rmtree(temp_dir, ignore_errors=True)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

