"""系统仓库示例 - 系统级功能

本示例展示如何使用系统仓库管理辅助数据：
1. 消息管理（MessageRepository）
2. 每日汇总（SummaryRepository）
3. 插件数据（PluginRepository）

运行方式：
    python examples/database/system_repos_example.py
"""
import sys
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DatabaseManager

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "system_repos_example.db"


def demo_message_management(db: DatabaseManager):
    """消息管理示例"""
    print("\n" + "=" * 60)
    print("💬 消息管理（MessageRepository）")
    print("=" * 60)

    # 1. 保存原始消息
    print("\n1️⃣ 保存原始消息")
    print("-" * 60)

    msg_data = {
        "msg_id": "msg-001",
        "sender_nickname": "前台",
        "content": "张三 头疗 198元",
        "msg_type": "text",
        "group_id": "group-001",
        "timestamp": datetime.now(),
        "is_at_bot": True,
        "is_business": True,
        "parse_status": "pending",
    }

    msg_id = db.save_raw_message(msg_data)
    print(f"✅ 原始消息已保存，ID: {msg_id}")
    print(f"   消息内容: {msg_data['content']}")
    print(f"   发送者: {msg_data['sender_nickname']}")

    # 2. 消息去重（再次保存相同消息）
    print("\n2️⃣ 消息去重测试")
    print("-" * 60)

    msg_id_dup = db.save_raw_message(msg_data)
    print(f"✅ 重复消息已处理（去重），返回 ID: {msg_id_dup}")
    print(f"   与第一次保存的 ID 相同: {msg_id == msg_id_dup}")

    # 3. 更新解析状态
    print("\n3️⃣ 更新解析状态")
    print("-" * 60)

    # 模拟解析成功
    db.update_parse_status(
        msg_id,
        status="parsed",
        result={
            "type": "service_record",
            "customer_name": "张三",
            "service": "头疗",
            "amount": 198
        }
    )
    print(f"✅ 消息解析状态已更新为 'parsed'")

    # 模拟解析失败
    msg_id2 = db.save_raw_message({
        "msg_id": "msg-002",
        "sender_nickname": "前台",
        "content": "这是一条无法解析的消息",
        "timestamp": datetime.now(),
    })

    db.update_parse_status(
        msg_id2,
        status="failed",
        error="无法识别业务类型"
    )
    print(f"✅ 消息解析状态已更新为 'failed'")

    # 4. 查询消息
    print("\n4️⃣ 查询消息")
    print("-" * 60)

    from database.models import RawMessage
    all_messages = db.messages.get_all(RawMessage)
    print(f"✅ 所有消息: {len(all_messages)} 条")
    for msg in all_messages:
        print(f"   - ID {msg.id}: {msg.content[:30]}... "
              f"(状态: {msg.parse_status})")


def demo_daily_summary(db: DatabaseManager):
    """每日汇总示例"""
    print("\n" + "=" * 60)
    print("📊 每日汇总（SummaryRepository）")
    print("=" * 60)

    # 1. 保存每日汇总
    print("\n1️⃣ 保存每日汇总")
    print("-" * 60)

    summary_date = date(2024, 1, 28)
    summary_data = {
        "total_service_revenue": 356,      # 服务总收入
        "total_product_revenue": 100,      # 商品总收入
        "total_commissions": 20,          # 总提成
        "net_revenue": 436,               # 净收入
        "service_count": 2,                # 服务次数
        "product_sale_count": 1,           # 商品销售次数
        "new_members": 1,                  # 新会员数
        "membership_revenue": 1000,        # 会员卡收入
        "summary_text": "头疗2次，商品销售1次，新会员1人",
        "confirmed": False,
    }

    summary_id = db.save_daily_summary(summary_date, summary_data)
    print(f"✅ 每日汇总已保存，ID: {summary_id}")
    print(f"   日期: {summary_date}")
    print(f"   服务收入: ¥{summary_data['total_service_revenue']}")
    print(f"   商品收入: ¥{summary_data['total_product_revenue']}")
    print(f"   净收入: ¥{summary_data['net_revenue']}")

    # 2. 更新每日汇总（幂等操作）
    print("\n2️⃣ 更新每日汇总（幂等操作）")
    print("-" * 60)

    updated_summary_data = {
        "total_service_revenue": 400,      # 更新后的数据
        "total_product_revenue": 100,
        "total_commissions": 25,
        "net_revenue": 475,
        "service_count": 3,
        "product_sale_count": 1,
        "new_members": 1,
        "membership_revenue": 1000,
        "summary_text": "更新后的汇总",
        "confirmed": True,
    }

    summary_id2 = db.save_daily_summary(summary_date, updated_summary_data)
    print(f"✅ 每日汇总已更新，ID: {summary_id2}")
    print(f"   与第一次保存的 ID 相同: {summary_id == summary_id2}")
    print(f"   更新后的净收入: ¥{updated_summary_data['net_revenue']}")

    # 3. 查询每日汇总
    print("\n3️⃣ 查询每日汇总")
    print("-" * 60)

    summary = db.summaries.get_by_date(summary_date)
    if summary:
        print(f"✅ 查询到 {summary_date} 的汇总")
        print(f"   服务收入: ¥{summary.total_service_revenue}")
        print(f"   商品收入: ¥{summary.total_product_revenue}")
        print(f"   净收入: ¥{summary.net_revenue}")
        print(f"   服务次数: {summary.service_count}")
        print(f"   是否确认: {summary.confirmed}")
    else:
        print(f"❌ 未找到 {summary_date} 的汇总")


def demo_plugin_data(db: DatabaseManager):
    """插件数据示例"""
    print("\n" + "=" * 60)
    print("🔌 插件数据（PluginRepository）")
    print("=" * 60)

    # 插件数据用于存储扩展信息，不修改核心模型
    # 适用于不同业态的特殊需求

    # 1. 保存插件数据（健身房场景：体测数据）
    print("\n1️⃣ 保存插件数据（健身房场景：体测数据）")
    print("-" * 60)

    # 先创建一个顾客
    customer = db.customers.get_or_create("健身会员A")

    # 保存体测数据
    db.plugins.save(
        "gym",                    # 插件名称
        "customer",              # 实体类型
        customer.id,             # 实体ID
        "body_fat",              # 数据键
        18.5                     # 数据值
    )
    print(f"✅ 体脂率已保存: 18.5%")

    db.plugins.save("gym", "customer", customer.id, "weight", 75.0)
    print(f"✅ 体重已保存: 75.0 kg")

    db.plugins.save("gym", "customer", customer.id, "muscle_mass", 55.0)
    print(f"✅ 肌肉量已保存: 55.0 kg")

    # 2. 读取单个插件数据
    print("\n2️⃣ 读取单个插件数据")
    print("-" * 60)

    body_fat = db.plugins.get("gym", "customer", customer.id, "body_fat")
    weight = db.plugins.get("gym", "customer", customer.id, "weight")
    print(f"✅ 体脂率: {body_fat}%")
    print(f"✅ 体重: {weight} kg")

    # 3. 读取所有插件数据（不指定 key）
    print("\n3️⃣ 读取所有插件数据")
    print("-" * 60)

    all_data = db.plugins.get("gym", "customer", customer.id)
    print(f"✅ 所有体测数据: {all_data}")
    # 输出: {"body_fat": 18.5, "weight": 75.0, "muscle_mass": 55.0}

    # 4. 保存插件数据（理发店场景：发型偏好）
    print("\n4️⃣ 保存插件数据（理发店场景：发型偏好）")
    print("-" * 60)

    customer2 = db.customers.get_or_create("美发顾客B")

    db.plugins.save(
        "hair_salon",
        "customer",
        customer2.id,
        "hair_style_preference",
        {"style": "短发", "color": "棕色", "length": "5cm"}
    )
    print(f"✅ 发型偏好已保存")

    preference = db.plugins.get("hair_salon", "customer", customer2.id, "hair_style_preference")
    print(f"✅ 发型偏好: {preference}")

    # 5. 删除插件数据
    print("\n5️⃣ 删除插件数据")
    print("-" * 60)

    db.plugins.delete("gym", "customer", customer.id, "muscle_mass")
    print(f"✅ 肌肉量数据已删除")

    # 验证删除
    remaining_data = db.plugins.get("gym", "customer", customer.id)
    print(f"✅ 剩余数据: {remaining_data}")
    # 输出: {"body_fat": 18.5, "weight": 75.0}


def main():
    """主函数"""
    print("=" * 60)
    print("Database 模块 - 系统仓库示例")
    print("=" * 60)

    # 初始化数据库
    DATA_DIR.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()  # 删除旧数据库，重新开始

    db = DatabaseManager(f"sqlite:///{DB_PATH}")
    db.create_tables()
    print(f"\n✅ 数据库已初始化: {DB_PATH}")

    # 运行各个示例
    demo_message_management(db)
    demo_daily_summary(db)
    demo_plugin_data(db)

    # 总结
    print("\n" + "=" * 60)
    print("✅ 系统仓库示例完成！")
    print("=" * 60)
    print(f"\n💡 提示：")
    print(f"   - 数据库文件位置: {DB_PATH}")
    print(f"   - 插件数据可用于存储业态特有的扩展信息")
    print(f"   - 下一步：运行 gym_example.py 或 hair_salon_example.py 查看完整场景")


if __name__ == "__main__":
    main()

