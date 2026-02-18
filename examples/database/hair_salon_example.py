"""理发店完整业务场景示例

本示例展示理发店业务的完整流程：
1. 初始化数据库和基础数据
2. 美发服务记录（剪发，带提成）
3. 储值卡开卡和余额扣减
4. 零售商品销售（洗发水）
5. 会员积分管理
6. 每日汇总

运行方式：
    python examples/database/hair_salon_example.py
"""
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DatabaseManager


DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "hair_salon_example.db"


def build_manager() -> DatabaseManager:
    """初始化数据库管理器"""
    DATA_DIR.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()  # 删除旧数据库，重新开始
    db = DatabaseManager(f"sqlite:///{DB_PATH}")
    db.create_tables()
    return db


def seed_data(db: DatabaseManager) -> None:
    """设置基础参考数据（员工、服务类型、渠道）"""
    print("\n📋 设置基础参考数据")
    print("-" * 60)

    # 创建员工
    db.staff.get_or_create("Tony", "tony_hair")
    db.staff.get_or_create("Mia", "mia_assistant")
    print("✅ 员工已创建：Tony, Mia")

    # 创建服务类型
    db.service_types.get_or_create("Haircut", default_price=80, category="hair")
    db.service_types.get_or_create("Hair Coloring", default_price=220, category="hair")
    print("✅ 服务类型已创建：Haircut (¥80), Hair Coloring (¥220)")

    # 创建引流渠道
    db.channels.get_or_create("Meituan", channel_type="platform", commission_rate=15)
    db.channels.get_or_create("Referral Friend", channel_type="external", commission_rate=10)
    print("✅ 渠道已创建：Meituan (15%), Referral Friend (10%)")


def run_daily_business(db: DatabaseManager) -> None:
    """执行日常业务流程"""
    print("\n💆 步骤 1: 美发服务记录")
    print("-" * 60)

    # 1.1 保存原始消息
    msg1 = db.save_raw_message(
        {
            "msg_id": "hair-service-001",
            "sender_nickname": "Mia",
            "content": "Alice haircut 80",
            "timestamp": datetime(2024, 1, 28, 10, 0, 0),
        }
    )

    # 1.2 获取渠道
    meituan = db.channels.get_or_create("Meituan", "platform", commission_rate=15)

    # 1.3 保存服务记录（带提成）
    record_id = db.save_service_record(
        {
            "customer_name": "Alice",  # 自动创建顾客
            "service_or_product": "Haircut",  # 自动创建服务类型
            "date": "2024-01-28",
            "amount": 80,
            "commission": 12,  # 提成给美团
            "referral_channel_id": meituan.id,
            "net_amount": 68,  # 净收入 = 金额 - 提成
            "recorder_nickname": "Mia",
            "extra_data": {"stylist": "Tony", "duration_min": 35},  # 扩展数据
        },
        msg1,
    )
    print(f"✅ 服务记录已保存，ID: {record_id}")
    print(f"   服务: Haircut")
    print(f"   金额: ¥80")
    print(f"   提成: ¥12 (给美团)")
    print(f"   净收入: ¥68")

    print("\n💳 步骤 2: 储值卡开卡")
    print("-" * 60)

    # 2.1 保存原始消息
    msg2 = db.save_raw_message(
        {
            "msg_id": "hair-membership-001",
            "sender_nickname": "Tony",
            "content": "Alice top-up 1000",
            "timestamp": datetime(2024, 1, 28, 12, 0, 0),
        }
    )

    # 2.2 创建储值卡
    membership_id = db.save_membership(
        {
            "customer_name": "Alice",
            "date": "2024-01-28",
            "amount": 1000,
            "card_type": "Stored Value",
        },
        msg2,
    )
    print(f"✅ 储值卡已创建，ID: {membership_id}")
    print(f"   顾客: Alice")
    print(f"   卡类型: Stored Value")
    print(f"   金额: ¥1000")

    print("\n🛍️ 步骤 3: 商品销售")
    print("-" * 60)

    # 3.1 保存原始消息
    msg3 = db.save_raw_message(
        {
            "msg_id": "hair-sale-001",
            "sender_nickname": "Tony",
            "content": "Alice shampoo 50",
            "timestamp": datetime(2024, 1, 28, 16, 0, 0),
        }
    )

    # 3.2 保存商品销售记录
    sale_id = db.save_product_sale(
        {
            "service_or_product": "Shampoo",  # 自动创建商品
            "date": "2024-01-28",
            "amount": 50,
            "quantity": 1,
            "unit_price": 50,
            "customer_name": "Alice",
            "recorder_nickname": "Tony",
        },
        msg3,
    )
    print(f"✅ 商品销售记录已保存，ID: {sale_id}")
    print(f"   商品: Shampoo")
    print(f"   数量: 1")
    print(f"   金额: ¥50")

    print("\n🎁 步骤 4: 会员卡操作")
    print("-" * 60)

    # 4.1 扣减余额（使用储值卡支付服务费用）
    updated = db.memberships.deduct_balance(membership_id, 80)
    if updated:
        print(f"✅ 余额已扣减 ¥80")
        print(f"   当前余额: ¥{updated.balance}")

    # 4.2 增加积分（消费获得积分）
    updated = db.memberships.add_points(membership_id, 8)
    if updated:
        print(f"✅ 积分已增加 8")
        print(f"   当前积分: {updated.points}")

    print("\n📊 步骤 5: 每日汇总")
    print("-" * 60)

    # 5.1 保存每日汇总
    summary_id = db.save_daily_summary(
        date(2024, 1, 28),
        {
            "total_service_revenue": 80,      # 服务总收入
            "total_product_revenue": 50,      # 商品总收入
            "total_commissions": 12,          # 总提成
            "net_revenue": 118,               # 净收入
            "service_count": 1,               # 服务次数
            "product_sale_count": 1,          # 商品销售次数
            "membership_revenue": 1000,       # 会员卡收入
            "summary_text": "Haircut + Shampoo + Top-up",
        },
    )
    print(f"✅ 每日汇总已保存，ID: {summary_id}")
    print(f"   服务收入: ¥80")
    print(f"   商品收入: ¥50")
    print(f"   会员卡收入: ¥1000")
    print(f"   总提成: ¥12")
    print(f"   净收入: ¥118")


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
            print(f"   {i}. 服务记录 - {item['service_type']} "
                  f"¥{item['amount']} (净收入: ¥{item.get('net_amount', item['amount'])})")
        else:
            print(f"   {i}. 商品销售 - {item['product_name']} "
                  f"¥{item['total_amount']}")

    # 查询顾客信息
    customer = db.get_customer_info("Alice")
    if customer and customer["memberships"]:
        membership = customer["memberships"][0]
        print(f"\n👤 顾客信息: {customer['name']}")
        print(f"   会员卡:")
        print(f"   - 类型: {membership['card_type']}")
        print(f"   - 余额: ¥{membership['balance']}")
        print(f"   - 积分: {membership['points']}")

    # 查询每日汇总
    summary = db.summaries.get_by_date(date(2024, 1, 28))
    if summary:
        print(f"\n📈 每日汇总:")
        print(f"   服务收入: ¥{summary.total_service_revenue}")
        print(f"   商品收入: ¥{summary.total_product_revenue}")
        print(f"   会员卡收入: ¥{summary.membership_revenue}")
        print(f"   总提成: ¥{summary.total_commissions}")
        print(f"   净收入: ¥{summary.net_revenue}")
        print(f"   服务次数: {summary.service_count}")
        print(f"   商品销售次数: {summary.product_sale_count}")

    print(f"\n💾 数据库文件: {DB_PATH}")


def main() -> None:
    """主函数"""
    print("=" * 60)
    print("💇 理发店完整业务场景示例")
    print("=" * 60)

    # 初始化数据库
    db = build_manager()
    print(f"\n✅ 数据库已初始化: {DB_PATH}")

    # 执行业务流程
    seed_data(db)
    run_daily_business(db)

    # 打印报表
    print_report(db)

    print("\n" + "=" * 60)
    print("✅ 示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
