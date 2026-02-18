"""健身房完整业务场景示例

本示例展示健身房业务的完整流程：
1. 初始化数据库和基础数据
2. 会员开卡（年卡）
3. 私教课程记录（带提成）
4. 商品销售（蛋白粉）
5. 积分系统（通过插件数据）
6. 每日汇总

运行方式：
    python examples/database/gym_example.py
"""
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DatabaseManager

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "gym_example.db"


def build_manager() -> DatabaseManager:
    """初始化数据库管理器"""
    DATA_DIR.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()  # 删除旧数据库，重新开始
    db = DatabaseManager(f"sqlite:///{DB_PATH}")
    db.create_tables()
    return db


def seed_reference_data(db: DatabaseManager) -> None:
    """设置基础参考数据（员工、服务类型、渠道）"""
    print("\n📋 设置基础参考数据")
    print("-" * 60)

    # 创建员工
    db.staff.get_or_create("Coach Li", "coach_li")
    db.staff.get_or_create("Front Desk", "front_desk")
    print("✅ 员工已创建：Coach Li, Front Desk")

    # 创建服务类型
    db.service_types.get_or_create("Personal Training", default_price=300, category="training")
    db.service_types.get_or_create("Group Class", default_price=60, category="class")
    print("✅ 服务类型已创建：Personal Training (¥300), Group Class (¥60)")

    # 创建引流渠道
    db.channels.get_or_create("Meituan", channel_type="platform", commission_rate=15)
    db.channels.get_or_create("Coach Li", channel_type="internal", commission_rate=40)
    print("✅ 渠道已创建：Meituan (15%), Coach Li (40%)")


def create_membership_and_records(db: DatabaseManager) -> None:
    """创建会员卡和业务记录"""
    print("\n💳 步骤 1: 会员开卡")
    print("-" * 60)

    # 1.1 保存原始消息
    member_msg = db.save_raw_message(
        {
            "msg_id": "gym-member-001",
            "sender_nickname": "Front Desk",
            "content": "Bob annual membership 3000",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0),
        }
    )

    # 1.2 创建会员卡（年卡）
    membership_id = db.save_membership(
        {
            "customer_name": "Bob",  # 自动创建顾客
            "date": "2024-01-01",
            "amount": 3000,
            "card_type": "Annual",
        },
        member_msg,
    )
    print(f"✅ 会员卡已创建，ID: {membership_id}")
    print(f"   顾客: Bob")
    print(f"   卡类型: Annual")
    print(f"   金额: ¥3000")

    print("\n💆 步骤 2: 私教课程记录")
    print("-" * 60)

    # 2.1 获取教练渠道（用于提成计算）
    coach_channel = db.channels.get_or_create("Coach Li", "internal", commission_rate=40)

    # 2.2 保存原始消息
    service_msg = db.save_raw_message(
        {
            "msg_id": "gym-service-001",
            "sender_nickname": "Front Desk",
            "content": "Bob personal training 300",
            "timestamp": datetime(2024, 1, 28, 14, 0, 0),
        }
    )

    # 2.3 保存服务记录（带提成）
    record_id = db.save_service_record(
        {
            "customer_name": "Bob",
            "service_or_product": "Personal Training",
            "date": "2024-01-28",
            "amount": 300,
            "commission": 120,  # 提成给教练
            "referral_channel_id": coach_channel.id,
            "membership_id": membership_id,  # 关联会员卡
            "recorder_nickname": "Front Desk",
            "extra_data": {"duration_minutes": 60, "goal": "fat_loss"},  # 扩展数据
        },
        service_msg,
    )
    print(f"✅ 服务记录已保存，ID: {record_id}")
    print(f"   服务: Personal Training")
    print(f"   金额: ¥300")
    print(f"   提成: ¥120 (给 Coach Li)")

    print("\n🛍️ 步骤 3: 商品销售")
    print("-" * 60)

    # 3.1 保存原始消息
    sale_msg = db.save_raw_message(
        {
            "msg_id": "gym-sale-001",
            "sender_nickname": "Front Desk",
            "content": "Bob protein powder 200",
            "timestamp": datetime(2024, 1, 28, 16, 0, 0),
        }
    )

    # 3.2 保存商品销售记录
    sale_id = db.save_product_sale(
        {
            "service_or_product": "Protein Powder",  # 自动创建商品
            "date": "2024-01-28",
            "amount": 200,
            "quantity": 1,
            "unit_price": 200,
            "customer_name": "Bob",
            "recorder_nickname": "Front Desk",
        },
        sale_msg,
    )
    print(f"✅ 商品销售记录已保存，ID: {sale_id}")
    print(f"   商品: Protein Powder")
    print(f"   数量: 1")
    print(f"   金额: ¥200")


def save_extensions_and_summary(db: DatabaseManager) -> None:
    """保存扩展数据和每日汇总"""
    print("\n🔌 步骤 4: 积分系统（插件数据）")
    print("-" * 60)

    # 4.1 获取顾客
    customer = db.customers.get_or_create("Bob")

    # 4.2 保存积分历史（使用插件数据）
    db.plugins.save(
        "gym_points",
        "customer",
        customer.id,
        "history",
        [
            {"date": "2024-01-01", "points": 300, "reason": "membership_open"},
            {"date": "2024-01-28", "points": 30, "reason": "service_consume"},
        ],
    )
    print(f"✅ 积分历史已保存")
    print(f"   - 2024-01-01: +300 积分（开卡）")
    print(f"   - 2024-01-28: +30 积分（消费）")

    # 4.3 查询积分历史
    points_history = db.plugins.get("gym_points", "customer", customer.id, "history")
    print(f"✅ 当前积分历史: {len(points_history)} 条记录")

    print("\n📊 步骤 5: 每日汇总")
    print("-" * 60)

    # 5.1 保存每日汇总
    summary_id = db.save_daily_summary(
        date(2024, 1, 28),
        {
            "total_service_revenue": 300,      # 服务总收入
            "total_product_revenue": 200,      # 商品总收入
            "total_commissions": 120,          # 总提成
            "net_revenue": 380,                # 净收入 = 总收入 - 提成
            "service_count": 1,                # 服务次数
            "product_sale_count": 1,           # 商品销售次数
            "new_members": 0,                  # 新会员数
            "membership_revenue": 0,           # 会员卡收入
            "summary_text": "PT 1 + Product 1",
        },
    )
    print(f"✅ 每日汇总已保存，ID: {summary_id}")
    print(f"   服务收入: ¥300")
    print(f"   商品收入: ¥200")
    print(f"   总提成: ¥120")
    print(f"   净收入: ¥380")


def print_report(db: DatabaseManager) -> None:
    """打印业务报表"""
    print("\n" + "=" * 60)
    print("📊 业务报表")
    print("=" * 60)

    # 查询日报
    records = db.get_daily_records("2024-01-28")
    print(f"\n📅 2024-01-28 的经营记录（共 {len(records)} 条）：")
    for i, item in enumerate(records, 1):
        if item["type"] == "service":
            print(f"   {i}. 服务记录 - {item['customer_name']} "
                  f"{item['service_type']} ¥{item['amount']}")
        else:
            print(f"   {i}. 商品销售 - {item['customer_name']} "
                  f"{item['product_name']} ¥{item['total_amount']}")

    # 查询顾客信息
    customer = db.get_customer_info("Bob")
    if customer:
        print(f"\n👤 顾客信息: {customer['name']}")
        print(f"   会员卡数量: {len(customer['memberships'])}")
        for m in customer['memberships']:
            print(f"   - {m['card_type']}: 余额 ¥{m['balance']}, "
                  f"积分 {m['points']}")

    # 查询每日汇总
    summary = db.summaries.get_by_date(date(2024, 1, 28))
    if summary:
        print(f"\n📈 每日汇总:")
        print(f"   服务收入: ¥{summary.total_service_revenue}")
        print(f"   商品收入: ¥{summary.total_product_revenue}")
        print(f"   总提成: ¥{summary.total_commissions}")
        print(f"   净收入: ¥{summary.net_revenue}")
        print(f"   服务次数: {summary.service_count}")
        print(f"   商品销售次数: {summary.product_sale_count}")

    print(f"\n💾 数据库文件: {DB_PATH}")


def main() -> None:
    """主函数"""
    print("=" * 60)
    print("🏋️ 健身房完整业务场景示例")
    print("=" * 60)

    # 初始化数据库
    db = build_manager()
    print(f"\n✅ 数据库已初始化: {DB_PATH}")

    # 执行业务流程
    seed_reference_data(db)
    create_membership_and_records(db)
    save_extensions_and_summary(db)

    # 打印报表
    print_report(db)

    print("\n" + "=" * 60)
    print("✅ 示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
