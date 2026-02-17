#!/usr/bin/env python3
"""理疗馆智能管理助手 - MiniMax Agent + 数据库集成（交互式）

本示例展示如何使用 MiniMax Agent 结合数据库，实现理疗馆的智能管理：
- 自然语言记账（服务项目、会员卡、产品销售）
- 自动计算技师提成
- 智能查询统计
- 会员信息管理
- 即将到期会员提醒

场景说明：
    理疗馆提供多种服务：推拿按摩、艾灸理疗、拔罐刮痧、足疗、头疗、肩颈调理等。
    技师按服务金额提成（高级技师40%，普通技师30%）。
    同时销售艾条、精油、刮痧板等产品。

使用方法：
    export MINIMAX_API_KEY="sk-api-..."
    python examples/therapy_agent_manager.py

    # 或者直接运行（内置默认 API Key）：
    python examples/therapy_agent_manager.py
"""
import os
import sys
import asyncio
import shutil
import tempfile
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional

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
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)

# ================================================================
# MiniMax API 配置
# ================================================================

MINIMAX_API_KEY = os.getenv(
    "MINIMAX_API_KEY",
)
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

# 全局数据库实例
_db: Optional[DatabaseManager] = None


def _get_db() -> DatabaseManager:
    """获取数据库实例。"""
    assert _db is not None, "数据库未初始化"
    return _db


# ================================================================
# 理疗馆业务函数 —— 直接操作真实数据库
# ================================================================


def record_service_income(
    customer_name: str,
    service_type: str,
    amount: float,
    date_str: Optional[str] = None,
    therapist_name: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict:
    """记录理疗馆服务收入（推拿按摩、艾灸、拔罐、足疗、头疗等）。

    Args:
        customer_name: 顾客姓名（必填）
        service_type: 服务类型，如"推拿按摩"、"艾灸理疗"、"拔罐刮痧"、"足疗"、"头疗"、"肩颈调理"（必填）
        amount: 服务金额（必填）
        date_str: 日期，格式YYYY-MM-DD，默认今天
        therapist_name: 技师名称，如"张师傅"、"王技师"（可选）
        duration_minutes: 服务时长（分钟），如60、90（可选）
        notes: 备注信息（可选）
    """
    db = _get_db()
    try:
        service_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else date.today()
        )

        # 计算提成：高级技师40%，普通技师30%
        commission = 0.0
        referral_channel_id = None
        if therapist_name:
            # 判断是否为高级技师
            senior_therapists = ["张师傅", "李师傅"]
            rate = 40.0 if therapist_name in senior_therapists else 30.0
            channel = db.channels.get_or_create(
                therapist_name, "internal", None, rate
            )
            referral_channel_id = channel.id
            commission = amount * (rate / 100.0)

        # 构建备注（包含时长信息）
        full_notes = ""
        if duration_minutes:
            full_notes += f"时长{duration_minutes}分钟"
        if notes:
            full_notes += f"；{notes}" if full_notes else notes

        msg_id = db.save_raw_message(
            {
                "wechat_msg_id": f"therapy_svc_{datetime.now().timestamp()}",
                "sender_nickname": "理疗馆管理员",
                "content": f"{customer_name} {service_type} {amount}元",
                "timestamp": datetime.now(),
            }
        )

        record_id = db.save_service_record(
            {
                "customer_name": customer_name,
                "service_or_product": service_type,
                "date": service_date,
                "amount": amount,
                "commission": commission,
                "referral_channel_id": referral_channel_id,
                "net_amount": amount - commission,
                "notes": full_notes or None,
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
            "therapist": therapist_name or "未指定",
            "commission": commission,
            "net_income": amount - commission,
            "duration": f"{duration_minutes}分钟" if duration_minutes else "未记录",
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
    """为顾客开通理疗馆会员卡/疗程卡。

    Args:
        customer_name: 顾客姓名（必填）
        card_type: 卡类型，如"年卡"、"季卡"、"月卡"、"次卡"、"疗程卡"（必填）
        amount: 充值金额（必填）
        date_str: 开卡日期，格式YYYY-MM-DD，默认今天
    """
    db = _get_db()
    try:
        opened_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else date.today()
        )

        days_map = {"年卡": 365, "季卡": 90, "月卡": 30, "次卡": 365, "疗程卡": 180}
        days = days_map.get(card_type, 30)

        msg_id = db.save_raw_message(
            {
                "wechat_msg_id": f"therapy_mem_{datetime.now().timestamp()}",
                "sender_nickname": "理疗馆管理员",
                "content": f"{customer_name}开{card_type}{amount}元",
                "timestamp": datetime.now(),
            }
        )

        membership_id = db.save_membership(
            {
                "customer_name": customer_name,
                "card_type": card_type,
                "date": opened_date,
                "amount": amount,
            },
            msg_id,
        )

        # 设置有效期和积分（每10元1积分）
        with db.get_session() as session:
            membership = (
                session.query(Membership)
                .filter(Membership.id == membership_id)
                .first()
            )
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
    """记录理疗馆产品销售（艾条、精油、刮痧板、热敷包等）。

    Args:
        product_name: 产品名称（必填）
        amount: 总金额（必填）
        customer_name: 顾客姓名（可选）
        quantity: 数量，默认1
        date_str: 日期，格式YYYY-MM-DD，默认今天
    """
    db = _get_db()
    try:
        sale_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else date.today()
        )

        msg_id = db.save_raw_message(
            {
                "wechat_msg_id": f"therapy_prod_{datetime.now().timestamp()}",
                "sender_nickname": "理疗馆管理员",
                "content": f"{customer_name or '顾客'}购买{product_name}{amount}元",
                "timestamp": datetime.now(),
            }
        )

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
    """查询理疗馆指定日期的收入统计。

    Args:
        date_str: 日期，格式YYYY-MM-DD，默认今天
    返回当天的服务收入、产品收入、提成支出和净收入。
    """
    db = _get_db()
    try:
        query_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else date.today()
        )

        with db.get_session() as session:
            from sqlalchemy import func

            svc = (
                session.query(
                    func.count(ServiceRecord.id).label("count"),
                    func.coalesce(func.sum(ServiceRecord.amount), 0).label("total"),
                    func.coalesce(func.sum(ServiceRecord.commission_amount), 0).label(
                        "commission"
                    ),
                    func.coalesce(func.sum(ServiceRecord.net_amount), 0).label("net"),
                )
                .filter(ServiceRecord.service_date == query_date)
                .first()
            )

            prod = (
                session.query(
                    func.count(ProductSale.id).label("count"),
                    func.coalesce(func.sum(ProductSale.total_amount), 0).label("total"),
                )
                .filter(ProductSale.sale_date == query_date)
                .first()
            )

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
    """查询理疗馆会员/顾客信息。

    Args:
        customer_name: 顾客姓名（必填）
    返回顾客的所有会员卡、余额、有效期、积分和消费记录统计。
    """
    db = _get_db()
    try:
        with db.get_session() as session:
            customer = (
                session.query(Customer)
                .filter(Customer.name == customer_name)
                .first()
            )

            if not customer:
                return {"success": False, "message": f"未找到顾客：{customer_name}"}

            memberships = []
            for m in customer.memberships:
                memberships.append(
                    {
                        "card_type": m.card_type,
                        "balance": float(m.balance),
                        "total_amount": float(m.total_amount),
                        "opened_at": str(m.opened_at),
                        "expires_at": str(m.expires_at) if m.expires_at else None,
                        "points": m.points,
                        "is_active": m.is_active,
                        "remaining_sessions": m.remaining_sessions,
                    }
                )

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


def query_therapist_commission(
    therapist_name: Optional[str] = None,
    date_str: Optional[str] = None,
) -> dict:
    """查询技师提成统计。

    Args:
        therapist_name: 技师姓名，如"张师傅"（可选，不填则查询所有技师）
        date_str: 日期，格式YYYY-MM-DD（可选，不填则查询所有日期）
    返回技师的服务次数和提成金额。
    """
    db = _get_db()
    try:
        with db.get_session() as session:
            from sqlalchemy import func

            query = (
                session.query(
                    ReferralChannel.name.label("therapist"),
                    func.count(ServiceRecord.id).label("count"),
                    func.coalesce(
                        func.sum(ServiceRecord.commission_amount), 0
                    ).label("total_commission"),
                    func.coalesce(func.sum(ServiceRecord.amount), 0).label(
                        "total_revenue"
                    ),
                )
                .join(
                    ServiceRecord,
                    ServiceRecord.referral_channel_id == ReferralChannel.id,
                )
                .filter(
                    ReferralChannel.channel_type == "internal",
                )
            )

            if therapist_name:
                query = query.filter(ReferralChannel.name == therapist_name)
            if date_str:
                qd = datetime.strptime(date_str, "%Y-%m-%d").date()
                query = query.filter(ServiceRecord.service_date == qd)

            query = query.group_by(ReferralChannel.name)
            results = query.all()

            commissions = []
            total = 0.0
            for r in results:
                amt = float(r.total_commission)
                commissions.append(
                    {
                        "therapist": r.therapist,
                        "service_count": r.count,
                        "commission": amt,
                        "total_revenue": float(r.total_revenue),
                    }
                )
                total += amt

        return {
            "success": True,
            "date": date_str or "所有日期",
            "therapists": commissions,
            "total_commission": total,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_expiring_members(days: int = 7) -> dict:
    """查询即将到期的会员卡/疗程卡。

    Args:
        days: 查询未来多少天内到期的会员卡，默认7天
    返回即将到期的会员列表，方便提前联系续卡。
    """
    db = _get_db()
    try:
        today = date.today()
        deadline = today + timedelta(days=days)

        with db.get_session() as session:
            expiring = (
                session.query(Membership)
                .filter(
                    Membership.is_active == True,
                    Membership.expires_at != None,
                    Membership.expires_at <= deadline,
                    Membership.expires_at >= today,
                )
                .all()
            )

            results = []
            for m in expiring:
                results.append(
                    {
                        "customer": m.customer.name if m.customer else "未知",
                        "card_type": m.card_type,
                        "expires_at": str(m.expires_at),
                        "balance": float(m.balance),
                        "days_left": (m.expires_at - today).days,
                    }
                )

        return {
            "success": True,
            "expiring_count": len(results),
            "members": results,
            "check_range_days": days,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_staff_list() -> dict:
    """获取理疗馆员工/技师列表。

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


def query_customer_history(
    customer_name: str,
    limit: int = 10,
) -> dict:
    """查询顾客的历史消费记录。

    Args:
        customer_name: 顾客姓名（必填）
        limit: 返回记录条数，默认10条
    返回顾客最近的服务记录和产品购买记录。
    """
    db = _get_db()
    try:
        with db.get_session() as session:
            customer = (
                session.query(Customer)
                .filter(Customer.name == customer_name)
                .first()
            )

            if not customer:
                return {"success": False, "message": f"未找到顾客：{customer_name}"}

            # 查询服务记录
            services = (
                session.query(ServiceRecord)
                .filter(ServiceRecord.customer_id == customer.id)
                .order_by(ServiceRecord.service_date.desc())
                .limit(limit)
                .all()
            )

            service_history = []
            for s in services:
                service_history.append(
                    {
                        "date": str(s.service_date),
                        "service": s.service_type_name or "未知",
                        "amount": float(s.amount),
                        "notes": s.notes,
                    }
                )

            # 查询产品购买记录
            products = (
                session.query(ProductSale)
                .filter(ProductSale.customer_id == customer.id)
                .order_by(ProductSale.sale_date.desc())
                .limit(limit)
                .all()
            )

            product_history = []
            for p in products:
                product_history.append(
                    {
                        "date": str(p.sale_date),
                        "product": p.product_name or "未知",
                        "amount": float(p.total_amount),
                        "quantity": p.quantity,
                    }
                )

        return {
            "success": True,
            "customer": customer_name,
            "service_records": service_history,
            "product_records": product_history,
            "total_services": len(service_history),
            "total_products": len(product_history),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ================================================================
# 数据库初始化
# ================================================================


def init_therapy_database(db_url: str) -> DatabaseManager:
    """初始化理疗馆数据库并填充基础数据。"""
    global _db

    db = DatabaseManager(database_url=db_url)
    db.create_tables()

    with db.get_session() as session:
        # ---- 技师/员工 ----
        zhang = db.staff.get_or_create("张师傅", "therapist_zhang", session=session)
        zhang.role = "manager"
        zhang.commission_rate = 40.0

        li = db.staff.get_or_create("李师傅", "therapist_li", session=session)
        li.role = "staff"
        li.commission_rate = 40.0

        wang = db.staff.get_or_create("王技师", "therapist_wang", session=session)
        wang.role = "staff"
        wang.commission_rate = 30.0

        zhao = db.staff.get_or_create("赵技师", "therapist_zhao", session=session)
        zhao.role = "staff"
        zhao.commission_rate = 30.0

        front = db.staff.get_or_create("前台小刘", "reception_liu", session=session)
        front.role = "staff"

        # ---- 服务类型 ----
        db.service_types.get_or_create("推拿按摩", 198.0, "massage", session=session)
        db.service_types.get_or_create("艾灸理疗", 168.0, "moxibustion", session=session)
        db.service_types.get_or_create("拔罐刮痧", 128.0, "cupping", session=session)
        db.service_types.get_or_create("足疗", 138.0, "foot_therapy", session=session)
        db.service_types.get_or_create("头疗", 158.0, "head_therapy", session=session)
        db.service_types.get_or_create("肩颈调理", 188.0, "shoulder_neck", session=session)
        db.service_types.get_or_create("全身精油SPA", 298.0, "spa", session=session)
        db.service_types.get_or_create("中药熏蒸", 238.0, "herbal_steam", session=session)

        # ---- 产品 ----
        db.products.get_or_create("艾条（盒）", "consumable", 68.0, session=session)
        db.products.get_or_create("精油（瓶）", "consumable", 128.0, session=session)
        db.products.get_or_create("刮痧板", "tool", 88.0, session=session)
        db.products.get_or_create("热敷包", "tool", 58.0, session=session)
        db.products.get_or_create("养生茶（盒）", "consumable", 98.0, session=session)
        db.products.get_or_create("颈椎枕", "tool", 168.0, session=session)
        db.products.get_or_create("足浴粉（袋）", "consumable", 38.0, session=session)

        # ---- 引流渠道 ----
        db.channels.get_or_create("美团", "platform", None, 15.0, session=session)
        db.channels.get_or_create("大众点评", "platform", None, 12.0, session=session)
        db.channels.get_or_create("朋友推荐", "external", None, 10.0, session=session)
        db.channels.get_or_create("抖音", "platform", None, 18.0, session=session)

        session.commit()

    _db = db
    return db


# ================================================================
# 创建 Agent
# ================================================================


def create_therapy_agent(api_key: str, model: str) -> Agent:
    """创建理疗馆管理 Agent。"""
    provider = create_provider(
        "minimax",
        api_key=api_key,
        model=model,
    )

    registry = FunctionRegistry()

    # 注册所有业务函数
    registry.register(
        "record_service_income",
        "记录理疗馆服务收入（推拿按摩、艾灸理疗、拔罐刮痧、足疗、头疗、肩颈调理、全身精油SPA、中药熏蒸等）。"
        "参数: customer_name(顾客姓名), service_type(服务类型), amount(金额), "
        "date_str(日期YYYY-MM-DD,默认今天), therapist_name(技师名称,可选), "
        "duration_minutes(时长分钟,可选), notes(备注,可选)",
        record_service_income,
        {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "顾客姓名"},
                "service_type": {
                    "type": "string",
                    "description": "服务类型，如：推拿按摩、艾灸理疗、拔罐刮痧、足疗、头疗、肩颈调理、全身精油SPA、中药熏蒸",
                },
                "amount": {"type": "number", "description": "金额（元）"},
                "date_str": {
                    "type": "string",
                    "description": "日期，格式YYYY-MM-DD，默认今天",
                },
                "therapist_name": {
                    "type": "string",
                    "description": "技师名称，如：张师傅、李师傅（高级技师提成40%）、王技师、赵技师（普通技师提成30%）",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "服务时长（分钟），如60、90",
                },
                "notes": {"type": "string", "description": "备注信息"},
            },
            "required": ["customer_name", "service_type", "amount"],
        },
    )

    registry.register(
        "open_membership_card",
        "为顾客开通理疗馆会员卡或疗程卡。"
        "参数: customer_name(顾客姓名), card_type(年卡/季卡/月卡/次卡/疗程卡), amount(充值金额), "
        "date_str(开卡日期YYYY-MM-DD,默认今天)",
        open_membership_card,
        {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "顾客姓名"},
                "card_type": {
                    "type": "string",
                    "description": "卡类型：年卡、季卡、月卡、次卡、疗程卡",
                },
                "amount": {"type": "number", "description": "充值金额（元）"},
                "date_str": {
                    "type": "string",
                    "description": "开卡日期，格式YYYY-MM-DD，默认今天",
                },
            },
            "required": ["customer_name", "card_type", "amount"],
        },
    )

    registry.register(
        "record_product_sale",
        "记录理疗馆产品销售（艾条、精油、刮痧板、热敷包、养生茶、颈椎枕、足浴粉等）。"
        "参数: product_name(产品名称), amount(总金额), customer_name(顾客姓名,可选), "
        "quantity(数量,默认1), date_str(日期YYYY-MM-DD,默认今天)",
        record_product_sale,
        {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "产品名称，如：艾条、精油、刮痧板、热敷包、养生茶、颈椎枕、足浴粉",
                },
                "amount": {"type": "number", "description": "总金额（元）"},
                "customer_name": {
                    "type": "string",
                    "description": "顾客姓名（可选）",
                },
                "quantity": {"type": "integer", "description": "数量，默认1"},
                "date_str": {
                    "type": "string",
                    "description": "日期，格式YYYY-MM-DD，默认今天",
                },
            },
            "required": ["product_name", "amount"],
        },
    )

    registry.register(
        "query_daily_income",
        "查询理疗馆指定日期的收入统计（服务收入、产品收入、提成、净收入）。"
        "参数: date_str(日期YYYY-MM-DD,默认今天)",
        query_daily_income,
        {
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "日期，格式YYYY-MM-DD，默认今天",
                },
            },
            "required": [],
        },
    )

    registry.register(
        "query_member_info",
        "查询理疗馆会员/顾客信息（会员卡、余额、有效期、积分、消费记录）。"
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
        "query_therapist_commission",
        "查询技师提成统计。"
        "参数: therapist_name(技师姓名,可选), date_str(日期YYYY-MM-DD,可选)",
        query_therapist_commission,
        {
            "type": "object",
            "properties": {
                "therapist_name": {
                    "type": "string",
                    "description": "技师姓名，如：张师傅、王技师",
                },
                "date_str": {
                    "type": "string",
                    "description": "日期，格式YYYY-MM-DD",
                },
            },
            "required": [],
        },
    )

    registry.register(
        "query_expiring_members",
        "查询即将到期的会员卡/疗程卡，方便提前联系顾客续卡。"
        "参数: days(查询未来多少天内到期,默认7天)",
        query_expiring_members,
        {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "查询未来多少天内到期的会员卡，默认7",
                },
            },
            "required": [],
        },
    )

    registry.register(
        "get_staff_list",
        "获取理疗馆员工/技师列表。返回所有在职员工信息。",
        get_staff_list,
        {
            "type": "object",
            "properties": {},
            "required": [],
        },
    )

    registry.register(
        "query_customer_history",
        "查询顾客的历史消费记录（最近的服务记录和产品购买记录）。"
        "参数: customer_name(顾客姓名), limit(返回条数,默认10)",
        query_customer_history,
        {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "顾客姓名"},
                "limit": {
                    "type": "integer",
                    "description": "返回记录条数，默认10",
                },
            },
            "required": ["customer_name"],
        },
    )

    agent = Agent(
        provider,
        function_registry=registry,
        system_prompt="""你是一家理疗馆（健康养生馆）的智能管理助手。你帮助理疗馆老板/管理者处理日常经营事务：

1. **记录服务收入**：推拿按摩(198元)、艾灸理疗(168元)、拔罐刮痧(128元)、足疗(138元)、头疗(158元)、肩颈调理(188元)、全身精油SPA(298元)、中药熏蒸(238元)等
2. **技师提成**：高级技师（张师傅、李师傅）提成40%，普通技师（王技师、赵技师）提成30%
3. **会员管理**：开会员卡（年卡365天/季卡90天/月卡30天/疗程卡180天，每10元1积分）、查询会员信息、检查到期会员
4. **产品销售**：艾条(68元)、精油(128元)、刮痧板(88元)、热敷包(58元)、养生茶(98元)、颈椎枕(168元)、足浴粉(38元)
5. **数据统计**：日收入汇总、技师提成统计、员工列表查询、顾客消费历史

重要规则：
- 高级技师（张师傅、李师傅）提成率为40%，普通技师（王技师、赵技师）提成率为30%
- 记录服务时应尽量指定技师名称
- 认真理解用户的自然语言，准确调用对应工具
- 用中文简洁回复，包含关键数字
- 如果一句话包含多个操作，依次调用对应函数""",
    )

    return agent


# ================================================================
# 演示模式：预设场景自动运行
# ================================================================


async def run_demo_mode(agent: Agent):
    """运行演示模式：模拟理疗馆管理者一天的日常操作。"""
    print("\n" + "=" * 60)
    print("📋 演示模式：模拟理疗馆管理者一天的日常")
    print("=" * 60)

    scenarios = [
        # 早间开门
        ("🌅 早间 - 查看员工", "今天有哪些技师上班？"),
        # 上午营业
        ("🌤️ 上午 - 推拿按摩", "陈阿姨来做推拿按摩，张师傅做的，收费198元，做了60分钟"),
        ("🌤️ 上午 - 艾灸理疗", "李大爷做了艾灸理疗，李师傅给他做的，收费168元"),
        ("🌤️ 上午 - 开会员卡", "王女士想办一张年卡，充值3000元"),
        # 中午时段
        ("🌞 中午 - 足疗", "赵先生来做足疗，王技师做的，138元"),
        ("🌞 中午 - 产品销售", "陈阿姨买了两盒艾条，一共136元"),
        # 下午营业
        ("🌇 下午 - 头疗+肩颈调理", "刘姐做了头疗158元和肩颈调理188元，都是赵技师做的"),
        ("🌇 下午 - 全身SPA", "王女士做了全身精油SPA，张师傅做的，298元，90分钟"),
        ("🌇 下午 - 产品销售", "赵先生买了一瓶精油128元和一个颈椎枕168元"),
        # 傍晚统计
        ("🌆 傍晚 - 查询收入", "帮我看看今天的收入情况"),
        ("🌆 傍晚 - 查询技师提成", "统计一下张师傅今天的提成"),
        ("🌆 傍晚 - 查询会员信息", "查一下王女士的会员卡信息"),
        ("🌆 傍晚 - 查询消费历史", "查一下陈阿姨的消费记录"),
    ]

    passed = 0
    failed = 0

    for title, user_input in scenarios:
        print(f"\n{'─' * 60}")
        print(f"  {title}")
        print(f"{'─' * 60}")
        print(f"  👤 管理者: {user_input}")

        try:
            agent.clear_history()
            response = await agent.chat(user_input, temperature=0.1)
            print(f"  🤖 助手: {response['content']}")
            if response["function_calls"]:
                print(
                    f"  📞 工具调用: {[fc['name'] for fc in response['function_calls']]}"
                )
            passed += 1
            print("  ✅ 成功")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

        await asyncio.sleep(1)  # 避免请求过快

    # 总结
    print(f"\n{'=' * 60}")
    print("📊 演示总结")
    print(f"{'=' * 60}")
    print(f"  成功: {passed}/{len(scenarios)}")
    print(f"  失败: {failed}/{len(scenarios)}")
    if failed == 0:
        print("\n  🎉 所有演示场景运行成功！")
    else:
        print(f"\n  ⚠️  有 {failed} 个场景失败")


# ================================================================
# 交互模式：用户实时输入
# ================================================================


async def run_interactive_mode(agent: Agent):
    """运行交互模式：用户实时输入，Agent 实时响应。"""
    print("\n" + "=" * 60)
    print("💬 交互模式：请输入理疗馆管理指令")
    print("=" * 60)
    print()
    print("你可以输入类似以下的指令：")
    print("  • 陈阿姨来做推拿按摩，张师傅做的，198元")
    print("  • 王女士办一张季卡，充值2000元")
    print("  • 赵先生买了一盒艾条，68元")
    print("  • 帮我看看今天的收入")
    print("  • 查一下王女士的会员卡信息")
    print("  • 统计一下张师傅的提成")
    print("  • 有哪些会员快到期了？")
    print("  • 查一下陈阿姨的消费记录")
    print()
    print("输入 'quit' 或 'exit' 退出，输入 'clear' 清除对话历史")
    print("输入 'demo' 切换到演示模式")
    print("=" * 60)

    while True:
        try:
            print()
            user_input = input("👤 管理者: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("\n👋 再见！祝生意兴隆！")
            break

        if user_input.lower() == "clear":
            agent.clear_history()
            print("🗑️  对话历史已清除")
            continue

        if user_input.lower() == "demo":
            await run_demo_mode(agent)
            agent.clear_history()
            print("\n💬 回到交互模式，请继续输入...")
            continue

        try:
            response = await agent.chat(user_input, temperature=0.1)

            print(f"\n🤖 助手: {response['content']}")

            if response["function_calls"]:
                tool_names = [fc["name"] for fc in response["function_calls"]]
                print(f"📞 调用工具: {', '.join(tool_names)}")

                # 显示工具调用结果摘要
                for fc in response["function_calls"]:
                    if fc.get("result") and isinstance(fc["result"], dict):
                        result = fc["result"]
                        if result.get("success") is False:
                            print(f"   ⚠️  {fc['name']}: {result.get('error', '未知错误')}")

        except Exception as e:
            print(f"\n❌ 出错了: {e}")
            logger.error(f"Agent 调用失败: {e}")
            import traceback

            traceback.print_exc()


# ================================================================
# 主程序
# ================================================================


async def main():
    """主程序入口。"""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         🏥 理疗馆智能管理助手                           ║")
    print("║         MiniMax Agent + Database 集成示例               ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # 检查 API Key
    if not MINIMAX_API_KEY:
        print("❌ 错误: 未设置 MINIMAX_API_KEY 环境变量")
        print("\n使用方法:")
        print('  export MINIMAX_API_KEY="sk-api-..."')
        print("  python examples/therapy_agent_manager.py")
        return

    print(f"🔑 API Key: {MINIMAX_API_KEY[:20]}...")
    print(f"🤖 模型: {MINIMAX_MODEL}")

    # 初始化数据库（使用临时目录，运行结束后自动清理）
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "therapy_agent_example.db"
    db_url = f"sqlite:///{db_path}"

    print(f"\n📊 初始化数据库: {db_path}")
    init_therapy_database(db_url)
    print("✅ 数据库初始化完成（已创建技师、服务类型、产品等基础数据）")

    # 创建 Agent
    print("\n🤖 创建 MiniMax Agent...")
    agent = create_therapy_agent(MINIMAX_API_KEY, MINIMAX_MODEL)
    print("✅ Agent 初始化完成")

    # 选择运行模式
    print("\n" + "=" * 60)
    print("请选择运行模式：")
    print("  1. 交互模式（实时输入指令）")
    print("  2. 演示模式（自动运行预设场景）")
    print("  3. 先演示再交互")
    print("=" * 60)

    try:
        choice = input("\n请输入选项 (1/2/3，默认1): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 再见！")
        return

    if choice == "2":
        await run_demo_mode(agent)
    elif choice == "3":
        await run_demo_mode(agent)
        agent.clear_history()
        print("\n" + "=" * 60)
        print("演示结束，进入交互模式...")
        print("=" * 60)
        await run_interactive_mode(agent)
    else:
        await run_interactive_mode(agent)

    print(f"\n📁 数据库文件: {db_path}")
    print("你可以使用 SQLite 工具查看数据库内容")


if __name__ == "__main__":
    asyncio.run(main())

