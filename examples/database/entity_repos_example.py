"""实体仓库示例 - 基础实体管理

本示例展示如何使用实体仓库管理基础数据：
1. 员工管理（StaffRepository）
2. 顾客管理（CustomerRepository）
3. 服务类型管理（ServiceTypeRepository）
4. 商品管理（ProductRepository）
5. 渠道管理（ChannelRepository）

运行方式：
    python examples/database/entity_repos_example.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DatabaseManager

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "entity_repos_example.db"


def demo_staff_management(db: DatabaseManager):
    """员工管理示例"""
    print("\n" + "=" * 60)
    print("👥 员工管理（StaffRepository）")
    print("=" * 60)

    # 1. 创建员工（get_or_create - 幂等操作）
    print("\n1️⃣ 创建员工")
    print("-" * 60)
    employee1 = db.staff.get_or_create("张三")
    print(f"✅ 员工已创建/获取: {employee1.name} (ID: {employee1.id})")

    employee2 = db.staff.get_or_create("李四")
    print(f"✅ 员工已创建/获取: {employee2.name} (ID: {employee2.id})")

    # 再次创建相同员工（测试幂等性）
    employee1_dup = db.staff.get_or_create("张三")
    print(f"✅ 重复创建相同员工，返回已存在的记录: {employee1_dup.id == employee1.id}")

    # 2. 查询在职员工
    print("\n2️⃣ 查询在职员工")
    print("-" * 60)
    active_staff = db.staff.get_active_staff()
    print(f"✅ 在职员工数量: {len(active_staff)}")
    for emp in active_staff:
        print(f"   - {emp.name} - "
              f"角色: {emp.role or 'N/A'} - 活跃: {emp.is_active}")

    # 3. 搜索员工
    print("\n3️⃣ 搜索员工")
    print("-" * 60)
    search_results = db.staff.search("张")
    print(f"✅ 搜索包含'张'的员工: 找到 {len(search_results)} 人")
    for emp in search_results:
        print(f"   - {emp.name}")

    # 4. 停用员工
    print("\n4️⃣ 停用员工")
    print("-" * 60)
    deactivated = db.staff.deactivate(employee2.id)
    if deactivated:
        print(f"✅ 员工已停用: {deactivated.name}")
        print(f"   当前状态: is_active = {deactivated.is_active}")

    # 再次查询在职员工
    active_staff_after = db.staff.get_active_staff()
    print(f"✅ 停用后在职员工数量: {len(active_staff_after)}")


def demo_customer_management(db: DatabaseManager):
    """顾客管理示例"""
    print("\n" + "=" * 60)
    print("👤 顾客管理（CustomerRepository）")
    print("=" * 60)

    # 1. 创建顾客
    print("\n1️⃣ 创建顾客")
    print("-" * 60)
    customer1 = db.customers.get_or_create("王五")
    print(f"✅ 顾客已创建/获取: {customer1.name} (ID: {customer1.id})")

    customer2 = db.customers.get_or_create("赵六")
    # 更新电话信息
    from database.models import Customer
    customer2 = db.customers.update_by_id(Customer, customer2.id, phone="13800138000")
    print(f"✅ 顾客已创建/获取: {customer2.name} (ID: {customer2.id})")
    print(f"   电话: {customer2.phone}")

    # 2. 搜索顾客
    print("\n2️⃣ 搜索顾客")
    print("-" * 60)
    search_results = db.customers.search("王")
    print(f"✅ 搜索包含'王'的顾客: 找到 {len(search_results)} 人")
    for cust in search_results:
        print(f"   - {cust.name} (电话: {cust.phone or 'N/A'})")

    # 3. 更新顾客信息
    print("\n3️⃣ 更新顾客信息")
    print("-" * 60)
    from database.models import Customer
    updated = db.customers.update_by_id(
        Customer,
        customer1.id,
        phone="13900139000",
        notes="VIP客户"
    )
    if updated:
        print(f"✅ 顾客信息已更新: {updated.name}")
        print(f"   电话: {updated.phone}")
        print(f"   备注: {updated.notes}")


def demo_service_type_management(db: DatabaseManager):
    """服务类型管理示例"""
    print("\n" + "=" * 60)
    print("💆 服务类型管理（ServiceTypeRepository）")
    print("=" * 60)

    # 1. 创建服务类型
    print("\n1️⃣ 创建服务类型")
    print("-" * 60)
    service1 = db.service_types.get_or_create(
        "头疗", default_price=198, category="理疗"
    )
    print(f"✅ 服务类型已创建/获取: {service1.name} (ID: {service1.id})")
    print(f"   默认价格: ¥{service1.default_price}")
    print(f"   分类: {service1.category}")

    service2 = db.service_types.get_or_create(
        "按摩", default_price=158, category="理疗"
    )
    print(f"✅ 服务类型已创建/获取: {service2.name} (ID: {service2.id})")

    service3 = db.service_types.get_or_create(
        "剪发", default_price=80, category="美发"
    )
    print(f"✅ 服务类型已创建/获取: {service3.name} (ID: {service3.id})")

    # 2. 按分类查询服务类型
    print("\n2️⃣ 按分类查询服务类型")
    print("-" * 60)
    therapy_services = db.service_types.get_by_category("理疗")
    print(f"✅ '理疗'分类的服务类型: {len(therapy_services)} 个")
    for svc in therapy_services:
        print(f"   - {svc.name}: ¥{svc.default_price}")

    # 3. 查询所有服务类型
    print("\n3️⃣ 查询所有服务类型")
    print("-" * 60)
    from database.models import ServiceType
    all_services = db.service_types.get_all(ServiceType)
    print(f"✅ 所有服务类型: {len(all_services)} 个")
    for svc in all_services:
        print(f"   - {svc.name} ({svc.category or 'N/A'}): ¥{svc.default_price}")


def demo_product_management(db: DatabaseManager):
    """商品管理示例"""
    print("\n" + "=" * 60)
    print("🛍️ 商品管理（ProductRepository）")
    print("=" * 60)

    # 1. 创建商品
    print("\n1️⃣ 创建商品")
    print("-" * 60)
    product1 = db.products.get_or_create(
        "洗发水", category="日用品", unit_price=50
    )
    print(f"✅ 商品已创建/获取: {product1.name} (ID: {product1.id})")
    print(f"   分类: {product1.category}")
    print(f"   单价: ¥{product1.unit_price}")
    print(f"   库存: {product1.stock_quantity}")

    product2 = db.products.get_or_create(
        "护发素", category="日用品", unit_price=60
    )
    # 更新库存数量
    from database.models import Product
    product2 = db.products.update_by_id(Product, product2.id, stock_quantity=20)
    print(f"✅ 商品已创建/获取: {product2.name} (ID: {product2.id})")
    print(f"   库存: {product2.stock_quantity}")

    # 2. 更新库存
    print("\n2️⃣ 更新库存")
    print("-" * 60)
    # 销售 5 件商品（库存减少）
    updated_product = db.products.update_stock(product1.id, quantity_change=-5)
    if updated_product:
        print(f"✅ 库存已更新: {updated_product.name}")
        print(f"   库存变化: -5")
        print(f"   当前库存: {updated_product.stock_quantity}")

    # 进货 10 件商品（库存增加）
    updated_product = db.products.update_stock(product1.id, quantity_change=10)
    if updated_product:
        print(f"✅ 库存已更新: {updated_product.name}")
        print(f"   库存变化: +10")
        print(f"   当前库存: {updated_product.stock_quantity}")

    # 3. 设置低库存阈值并查询低库存商品
    print("\n3️⃣ 设置低库存阈值并查询低库存商品")
    print("-" * 60)
    # 设置低库存阈值
    from database.models import Product
    product2 = db.products.update_by_id(Product, product2.id, low_stock_threshold=15)
    print(f"✅ 已设置 {product2.name} 的低库存阈值为 15")

    # 查询低库存商品
    low_stock_products = db.products.get_low_stock()
    print(f"✅ 低库存商品: {len(low_stock_products)} 个")
    for prod in low_stock_products:
        print(f"   - {prod.name}: 库存 {prod.stock_quantity} "
              f"(阈值: {prod.low_stock_threshold})")


def demo_channel_management(db: DatabaseManager):
    """渠道管理示例"""
    print("\n" + "=" * 60)
    print("📢 渠道管理（ChannelRepository）")
    print("=" * 60)

    # 1. 创建渠道
    print("\n1️⃣ 创建渠道")
    print("-" * 60)
    channel1 = db.channels.get_or_create(
        "美团", channel_type="platform", commission_rate=15.0
    )
    print(f"✅ 渠道已创建/获取: {channel1.name} (ID: {channel1.id})")
    print(f"   渠道类型: {channel1.channel_type}")
    print(f"   提成率: {channel1.commission_rate}%")

    channel2 = db.channels.get_or_create(
        "朋友推荐", channel_type="external", commission_rate=10.0
    )
    print(f"✅ 渠道已创建/获取: {channel2.name} (ID: {channel2.id})")

    channel3 = db.channels.get_or_create(
        "内部员工", channel_type="internal", commission_rate=20.0
    )
    print(f"✅ 渠道已创建/获取: {channel3.name} (ID: {channel3.id})")

    # 2. 查询活跃渠道
    print("\n2️⃣ 查询活跃渠道")
    print("-" * 60)
    all_active = db.channels.get_active_channels()
    print(f"✅ 所有活跃渠道: {len(all_active)} 个")
    for ch in all_active:
        print(f"   - {ch.name} ({ch.channel_type}): "
              f"提成率 {ch.commission_rate}%")

    # 3. 按类型查询渠道
    print("\n3️⃣ 按类型查询渠道")
    print("-" * 60)
    platform_channels = db.channels.get_active_channels("platform")
    print(f"✅ 'platform' 类型的活跃渠道: {len(platform_channels)} 个")
    for ch in platform_channels:
        print(f"   - {ch.name}: 提成率 {ch.commission_rate}%")


def main():
    """主函数"""
    print("=" * 60)
    print("Database 模块 - 实体仓库示例")
    print("=" * 60)

    # 初始化数据库
    DATA_DIR.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()  # 删除旧数据库，重新开始

    db = DatabaseManager(f"sqlite:///{DB_PATH}")
    db.create_tables()
    print(f"\n✅ 数据库已初始化: {DB_PATH}")

    # 运行各个示例
    demo_staff_management(db)
    demo_customer_management(db)
    demo_service_type_management(db)
    demo_product_management(db)
    demo_channel_management(db)

    # 总结
    print("\n" + "=" * 60)
    print("✅ 实体仓库示例完成！")
    print("=" * 60)
    print(f"\n💡 提示：")
    print(f"   - 数据库文件位置: {DB_PATH}")
    print(f"   - 下一步：运行 business_repos_example.py 学习业务记录管理")


if __name__ == "__main__":
    main()

