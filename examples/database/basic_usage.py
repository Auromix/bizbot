"""基础使用示例 - Database 模块入门

本示例展示 DatabaseManager 的基本使用方法：
1. 初始化数据库
2. 创建数据表
3. 保存原始消息
4. 保存服务记录
5. 查询数据

运行方式：
    python examples/database/basic_usage.py
"""
import sys
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DatabaseManager

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "basic_usage_example.db"


def main():
    """基础使用示例主函数"""
    print("=" * 60)
    print("Database 模块 - 基础使用示例")
    print("=" * 60)

    # ============================================================
    # 步骤 1: 初始化数据库管理器
    # ============================================================
    print("\n📦 步骤 1: 初始化数据库管理器")
    print("-" * 60)

    # 确保数据目录存在
    DATA_DIR.mkdir(exist_ok=True)

    # 如果数据库已存在，可以选择删除重新开始（可选）
    # if DB_PATH.exists():
    #     DB_PATH.unlink()

    # 创建数据库管理器
    # 支持 SQLite（开发环境）和 PostgreSQL（生产环境）
    db = DatabaseManager(f"sqlite:///{DB_PATH}")
    print(f"✅ 数据库管理器已创建")
    print(f"   数据库路径: {DB_PATH}")
    print(f"   连接 URL: {db.database_url}")
    print(f"   是否异步: {db.is_async}")

    # ============================================================
    # 步骤 2: 创建数据表
    # ============================================================
    print("\n📋 步骤 2: 创建数据表")
    print("-" * 60)

    # 创建所有数据表（幂等操作，已存在则跳过）
    db.create_tables()
    print("✅ 数据表已创建（包括：")
    print("   - employees（员工表）")
    print("   - customers（顾客表）")
    print("   - service_types（服务类型表）")
    print("   - products（商品表）")
    print("   - referral_channels（渠道表）")
    print("   - service_records（服务记录表）")
    print("   - product_sales（商品销售表）")
    print("   - memberships（会员卡表）")
    print("   - raw_messages（原始消息表）")
    print("   - daily_summaries（每日汇总表）")
    print("   - plugin_data（插件数据表）")
    print("   - 等等...")

    # ============================================================
    # 步骤 3: 保存原始消息
    # ============================================================
    print("\n💬 步骤 3: 保存原始消息")
    print("-" * 60)

    # 保存一条原始消息（模拟从群聊接收到的消息）
    msg_data = {
        "msg_id": "basic-msg-001",         # 消息ID（用于去重）
        "sender_nickname": "前台",          # 发送者昵称
        "content": "张三 头疗 198元",        # 消息内容
        "timestamp": datetime.now(),        # 消息时间戳
        "is_business": True,                # 是否为业务消息
    }

    msg_id = db.save_raw_message(msg_data)
    print(f"✅ 原始消息已保存，ID: {msg_id}")
    print(f"   消息内容: {msg_data['content']}")

    # 再次保存相同消息（测试去重功能）
    msg_id_dup = db.save_raw_message(msg_data)
    print(f"✅ 重复消息已处理（去重），返回 ID: {msg_id_dup}")
    print(f"   与第一次保存的 ID 相同: {msg_id == msg_id_dup}")

    # ============================================================
    # 步骤 4: 保存服务记录
    # ============================================================
    print("\n📝 步骤 4: 保存服务记录")
    print("-" * 60)

    # 保存服务记录
    # 注意：只需传入名称字符串，系统会自动创建顾客和服务类型
    record_data = {
        "customer_name": "张三",           # 顾客姓名（自动创建）
        "service_or_product": "头疗",     # 服务类型（自动创建）
        "date": "2024-01-28",             # 服务日期
        "amount": 198,                     # 金额
        "recorder_nickname": "前台",      # 记录员（自动创建员工）
    }

    record_id = db.save_service_record(record_data, msg_id)
    print(f"✅ 服务记录已保存，ID: {record_id}")
    print(f"   顾客: {record_data['customer_name']}")
    print(f"   服务: {record_data['service_or_product']}")
    print(f"   金额: ¥{record_data['amount']}")

    # ============================================================
    # 步骤 5: 查询数据
    # ============================================================
    print("\n🔍 步骤 5: 查询数据")
    print("-" * 60)

    # 5.1 查询某日的所有记录
    target_date = "2024-01-28"
    records = db.get_daily_records(target_date)
    print(f"\n📊 {target_date} 的经营记录（共 {len(records)} 条）：")
    for i, r in enumerate(records, 1):
        record_type = r.get('type', 'unknown')
        if record_type == 'service':
            print(f"   {i}. 服务记录 - {r['customer_name']} "
                  f"{r.get('service_type', 'N/A')} ¥{r['amount']}")
        elif record_type == 'product':
            print(f"   {i}. 商品销售 - {r['customer_name']} "
                  f"{r.get('product_name', 'N/A')} ¥{r['total_amount']}")

    # 5.2 查询顾客信息
    customer_name = "张三"
    customer_info = db.get_customer_info(customer_name)
    if customer_info:
        print(f"\n👤 顾客信息: {customer_info['name']}")
        print(f"   会员卡数量: {len(customer_info['memberships'])}")
        if customer_info['memberships']:
            for m in customer_info['memberships']:
                print(f"   - {m['card_type']}: 余额 ¥{m['balance']}, "
                      f"积分 {m['points']}")
    else:
        print(f"\n❌ 未找到顾客: {customer_name}")

    # 5.3 查询员工列表
    staff_list = db.get_staff_list(active_only=True)
    print(f"\n👥 在职员工列表（共 {len(staff_list)} 人）：")
    for s in staff_list:
        print(f"   - {s['name']}")

    # ============================================================
    # 步骤 6: 使用子仓库进行精细操作
    # ============================================================
    print("\n🔧 步骤 6: 使用子仓库进行精细操作")
    print("-" * 60)

    # 通过子仓库直接访问（返回 ORM 对象）
    customer = db.customers.get_or_create("李四")
    print(f"✅ 通过子仓库创建顾客: {customer.name} (ID: {customer.id})")

    # 搜索顾客
    search_results = db.customers.search("张")
    print(f"✅ 搜索包含'张'的顾客: 找到 {len(search_results)} 人")
    for c in search_results:
        print(f"   - {c.name}")

    # ============================================================
    # 总结
    # ============================================================
    print("\n" + "=" * 60)
    print("✅ 基础使用示例完成！")
    print("=" * 60)
    print(f"\n💡 提示：")
    print(f"   - 数据库文件位置: {DB_PATH}")
    print(f"   - 可以使用 SQLite 工具查看数据库内容")
    print(f"   - 下一步：运行 entity_repos_example.py 学习实体管理")
    print(f"   - 下一步：运行 business_repos_example.py 学习业务记录")


if __name__ == "__main__":
    main()

