"""业务仓库示例 - 核心业务记录管理

本示例展示如何使用业务仓库管理核心业务数据：
1. 服务记录管理（ServiceRecordRepository）
2. 商品销售管理（ProductSaleRepository）
3. 会员卡管理（MembershipRepository）

运行方式：
    python examples/database/business_repos_example.py
"""
import sys
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DatabaseManager

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "business_repos_example.db"


def setup_reference_data(db: DatabaseManager):
    """设置基础参考数据"""
    print("\n📋 设置基础参考数据")
    print("-" * 60)

    # 创建员工
    db.staff.get_or_create("前台", "front_desk")
    db.staff.get_or_create("技师A", "tech_a")
    print("✅ 员工已创建")

    # 创建服务类型
    db.service_types.get_or_create("头疗", default_price=198, category="理疗")
    db.service_types.get_or_create("按摩", default_price=158, category="理疗")
    print("✅ 服务类型已创建")

    # 创建商品
    db.products.get_or_create("洗发水", category="日用品", unit_price=50)
    db.products.get_or_create("护发素", category="日用品", unit_price=60)
    print("✅ 商品已创建")

    # 创建渠道
    db.channels.get_or_create("美团", channel_type="platform", commission_rate=15.0)
    print("✅ 渠道已创建")


def demo_service_record(db: DatabaseManager):
    """服务记录管理示例"""
    print("\n" + "=" * 60)
    print("💆 服务记录管理（ServiceRecordRepository）")
    print("=" * 60)

    # 1. 保存原始消息
    print("\n1️⃣ 保存服务记录")
    print("-" * 60)

    msg_id = db.save_raw_message({
        "msg_id": "service-001",
        "sender_nickname": "前台",
        "content": "张三 头疗 198元",
        "timestamp": datetime.now(),
    })

    # 2. 保存基本服务记录（自动创建顾客和服务类型）
    record_data = {
        "customer_name": "张三",           # 自动创建顾客
        "service_or_product": "头疗",     # 自动创建服务类型
        "date": "2024-01-28",
        "amount": 198,
        "recorder_nickname": "前台",      # 自动创建记录员
    }

    record_id = db.save_service_record(record_data, msg_id)
    print(f"✅ 服务记录已保存，ID: {record_id}")
    print(f"   顾客: {record_data['customer_name']}")
    print(f"   服务: {record_data['service_or_product']}")
    print(f"   金额: ¥{record_data['amount']}")

    # 3. 保存带提成的服务记录
    print("\n2️⃣ 保存带提成的服务记录")
    print("-" * 60)

    msg_id2 = db.save_raw_message({
        "msg_id": "service-002",
        "sender_nickname": "前台",
        "content": "李四 按摩 158元 提成20给技师A",
        "timestamp": datetime.now(),
    })

    meituan_channel = db.channels.get_or_create("美团", "platform", commission_rate=15.0)

    record_data2 = {
        "customer_name": "李四",
        "service_or_product": "按摩",
        "date": "2024-01-28",
        "amount": 158,
        "commission": 20,
        "commission_to": "技师A",
        "referral_channel_id": meituan_channel.id,
        "net_amount": 138,  # 净收入 = 金额 - 提成
        "recorder_nickname": "前台",
        "notes": "客户满意",
    }

    record_id2 = db.save_service_record(record_data2, msg_id2)
    print(f"✅ 服务记录已保存，ID: {record_id2}")
    print(f"   金额: ¥{record_data2['amount']}")
    print(f"   提成: ¥{record_data2['commission']}")
    print(f"   净收入: ¥{record_data2['net_amount']}")

    # 4. 查询某日的服务记录
    print("\n3️⃣ 查询某日的服务记录")
    print("-" * 60)

    target_date = date(2024, 1, 28)
    records = db.service_records.get_by_date(target_date)
    print(f"✅ {target_date} 的服务记录: {len(records)} 条")
    for r in records:
        print(f"   - {r['customer_name']}: {r['service_type']} "
              f"¥{r['amount']} (净收入: ¥{r.get('net_amount', r['amount'])})")

    # 5. 确认服务记录
    print("\n4️⃣ 确认服务记录")
    print("-" * 60)

    confirmed = db.service_records.confirm(record_id)
    if confirmed:
        print(f"✅ 服务记录已确认，ID: {record_id}")
        # 重新查询确认状态
        from database.models import ServiceRecord
        record = db.service_records.get_by_id(ServiceRecord, record_id)
        if record:
            print(f"   确认状态: {record.confirmed}")
            print(f"   确认时间: {record.confirmed_at}")


def demo_product_sale(db: DatabaseManager):
    """商品销售管理示例"""
    print("\n" + "=" * 60)
    print("🛍️ 商品销售管理（ProductSaleRepository）")
    print("=" * 60)

    # 1. 保存商品销售记录
    print("\n1️⃣ 保存商品销售记录")
    print("-" * 60)

    msg_id = db.save_raw_message({
        "msg_id": "sale-001",
        "sender_nickname": "前台",
        "content": "张三 购买 洗发水 2瓶 100元",
        "timestamp": datetime.now(),
    })

    sale_data = {
        "service_or_product": "洗发水",  # 自动创建商品（如果不存在）
        "customer_name": "张三",         # 自动创建顾客（如果不存在）
        "date": "2024-01-28",
        "quantity": 2,
        "unit_price": 50,
        "total_amount": 100,
        "recorder_nickname": "前台",
        "notes": "客户主动购买",
    }

    sale_id = db.save_product_sale(sale_data, msg_id)
    print(f"✅ 商品销售记录已保存，ID: {sale_id}")
    print(f"   商品: {sale_data['service_or_product']}")
    print(f"   数量: {sale_data['quantity']}")
    print(f"   单价: ¥{sale_data['unit_price']}")
    print(f"   总金额: ¥{sale_data['total_amount']}")

    # 注意：保存销售记录会自动更新商品库存
    # 查询商品信息（通过名称）
    product = db.products.get_or_create(sale_data['service_or_product'])
    print(f"   商品当前库存: {product.stock_quantity}")

    # 2. 查询某日的销售记录
    print("\n2️⃣ 查询某日的销售记录")
    print("-" * 60)

    target_date = date(2024, 1, 28)
    sales = db.product_sales.get_by_date(target_date)
    print(f"✅ {target_date} 的商品销售记录: {len(sales)} 条")
    for s in sales:
        print(f"   - {s['customer_name']}: {s['product_name']} "
              f"x{s['quantity']} = ¥{s['total_amount']}")


def demo_membership(db: DatabaseManager):
    """会员卡管理示例"""
    print("\n" + "=" * 60)
    print("💳 会员卡管理（MembershipRepository）")
    print("=" * 60)

    # 1. 开卡（创建会员卡）
    print("\n1️⃣ 开卡（创建会员卡）")
    print("-" * 60)

    msg_id = db.save_raw_message({
        "msg_id": "membership-001",
        "sender_nickname": "前台",
        "content": "王五 开卡 储值卡 1000元",
        "timestamp": datetime.now(),
    })

    membership_data = {
        "customer_name": "王五",      # 自动创建顾客
        "date": "2024-01-28",
        "amount": 1000,
        "card_type": "储值卡",
    }

    membership_id = db.save_membership(membership_data, msg_id)
    print(f"✅ 会员卡已创建，ID: {membership_id}")
    print(f"   顾客: {membership_data['customer_name']}")
    print(f"   卡类型: {membership_data['card_type']}")
    print(f"   金额: ¥{membership_data['amount']}")

    # 2. 查询顾客的会员卡
    print("\n2️⃣ 查询顾客的会员卡")
    print("-" * 60)

    customer = db.customers.get_or_create("王五")
    memberships = db.memberships.get_active_by_customer(customer.id)
    print(f"✅ 顾客 {customer.name} 的活跃会员卡: {len(memberships)} 张")
    for m in memberships:
        print(f"   - {m.card_type}: 余额 ¥{m.balance}, "
              f"剩余次数 {m.remaining_sessions}, 积分 {m.points or 0}")

    # 3. 扣减余额（储值卡）
    print("\n3️⃣ 扣减余额（储值卡）")
    print("-" * 60)

    updated = db.memberships.deduct_balance(membership_id, 198)
    if updated:
        print(f"✅ 余额已扣减 ¥198")
        print(f"   当前余额: ¥{updated.balance}")

    # 4. 增加积分
    print("\n4️⃣ 增加积分")
    print("-" * 60)

    updated = db.memberships.add_points(membership_id, 20)
    if updated:
        print(f"✅ 积分已增加 20")
        print(f"   当前积分: {updated.points}")

    # 5. 创建次卡并扣减次数
    print("\n5️⃣ 创建次卡并扣减次数")
    print("-" * 60)

    msg_id2 = db.save_raw_message({
        "msg_id": "membership-002",
        "sender_nickname": "前台",
        "content": "赵六 开卡 次卡 10次",
        "timestamp": datetime.now(),
    })

    session_card_data = {
        "customer_name": "赵六",
        "date": "2024-01-28",
        "amount": 500,
        "card_type": "次卡",
        "remaining_sessions": 10,
    }

    session_card_id = db.save_membership(session_card_data, msg_id2)
    print(f"✅ 次卡已创建，ID: {session_card_id}")
    print(f"   剩余次数: {session_card_data['remaining_sessions']}")

    # 扣减次数
    updated = db.memberships.deduct_session(session_card_id, 1)
    if updated:
        print(f"✅ 次数已扣减 1 次")
        print(f"   剩余次数: {updated.remaining_sessions}")


def main():
    """主函数"""
    print("=" * 60)
    print("Database 模块 - 业务仓库示例")
    print("=" * 60)

    # 初始化数据库
    DATA_DIR.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()  # 删除旧数据库，重新开始

    db = DatabaseManager(f"sqlite:///{DB_PATH}")
    db.create_tables()
    print(f"\n✅ 数据库已初始化: {DB_PATH}")

    # 设置基础数据
    setup_reference_data(db)

    # 运行各个示例
    demo_service_record(db)
    demo_product_sale(db)
    demo_membership(db)

    # 总结
    print("\n" + "=" * 60)
    print("✅ 业务仓库示例完成！")
    print("=" * 60)
    print(f"\n💡 提示：")
    print(f"   - 数据库文件位置: {DB_PATH}")
    print(f"   - 下一步：运行 system_repos_example.py 学习系统功能")
    print(f"   - 下一步：运行 gym_example.py 或 hair_salon_example.py 查看完整场景")


if __name__ == "__main__":
    main()

