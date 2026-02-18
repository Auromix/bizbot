# Database 模块快速开始指南

本指南帮助您在 5 分钟内快速上手 `database/` 模块。

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 基本使用（3 步上手）

### 步骤 1：初始化数据库

```python
from database import DatabaseManager

# 创建数据库管理器（SQLite 示例）
db = DatabaseManager("sqlite:///data/my_store.db")

# 创建所有数据表
db.create_tables()
```

### 步骤 2：保存业务记录

```python
from datetime import datetime

# 1. 保存原始消息
msg_id = db.save_raw_message({
    "msg_id": "msg-001",
    "sender_nickname": "前台",
    "content": "张三 头疗 198元",
    "timestamp": datetime.now()
})

# 2. 保存服务记录（自动创建顾客和服务类型）
record_id = db.save_service_record({
    "customer_name": "张三",           # 自动创建顾客
    "service_or_product": "头疗",     # 自动创建服务类型
    "date": "2024-01-28",
    "amount": 198
}, msg_id)

print(f"服务记录已保存，ID: {record_id}")
```

### 步骤 3：查询数据

```python
# 查询某日的所有记录
records = db.get_daily_records("2024-01-28")
for r in records:
    print(f"{r['customer_name']} - {r['type']} - ¥{r['amount']}")

# 查询顾客信息
customer = db.get_customer_info("张三")
if customer:
    print(f"顾客: {customer['name']}")
    print(f"会员卡数量: {len(customer['memberships'])}")
```

## 3. 完整示例

运行以下代码，体验完整流程：

```python
"""快速开始示例"""
from datetime import datetime, date
from database import DatabaseManager

# 初始化
db = DatabaseManager("sqlite:///data/quickstart.db")
db.create_tables()

# === 1. 保存原始消息 ===
msg_id = db.save_raw_message({
    "msg_id": "quickstart-001",
    "sender_nickname": "前台",
    "content": "张三 头疗 198元",
    "timestamp": datetime.now()
})

# === 2. 保存服务记录 ===
record_id = db.save_service_record({
    "customer_name": "张三",
    "service_or_product": "头疗",
    "date": "2024-01-28",
    "amount": 198,
    "recorder_nickname": "前台"
}, msg_id)

print(f"✅ 服务记录已保存，ID: {record_id}")

# === 3. 查询日报 ===
records = db.get_daily_records("2024-01-28")
print(f"\n📊 2024-01-28 的经营记录（共 {len(records)} 条）：")
for r in records:
    print(f"  - {r['customer_name']}: {r.get('service_type', r.get('product_name'))} ¥{r['amount']}")

# === 4. 查询顾客信息 ===
customer = db.get_customer_info("张三")
if customer:
    print(f"\n👤 顾客信息：{customer['name']}")
    print(f"   会员卡数量: {len(customer['memberships'])}")

# === 5. 保存每日汇总 ===
db.save_daily_summary(date(2024, 1, 28), {
    "total_service_revenue": 198,
    "total_product_revenue": 0,
    "net_revenue": 198,
    "service_count": 1,
    "summary_text": "头疗服务 1 次"
})

print("\n✅ 快速开始示例完成！")
```

保存为 `quickstart_demo.py` 并运行：

```bash
python quickstart_demo.py
```

## 4. 常用操作速查

### 员工管理

```python
# 创建员工
employee = db.staff.get_or_create("张三")

# 查询在职员工
active_staff = db.staff.get_active_staff()

# 停用员工
db.staff.deactivate(employee.id)
```

### 顾客管理

```python
# 创建顾客
customer = db.customers.get_or_create("李四")

# 搜索顾客
results = db.customers.search("李")

# 查询顾客信息（含会员卡）
info = db.get_customer_info("李四")
```

### 服务记录

```python
# 保存服务记录（带提成）
record_id = db.save_service_record({
    "customer_name": "张三",
    "service_or_product": "头疗",
    "date": "2024-01-28",
    "amount": 198,
    "commission": 20,
    "commission_to": "李哥",
    "net_amount": 178
}, msg_id)

# 查询某日服务记录
records = db.service_records.get_by_date(date(2024, 1, 28))
```

### 会员卡管理

```python
# 开卡
membership_id = db.save_membership({
    "customer_name": "张三",
    "date": "2024-01-28",
    "amount": 1000,
    "card_type": "储值卡"
}, msg_id)

# 扣减余额
db.memberships.deduct_balance(membership_id, 198)

# 扣减次数（次卡）
db.memberships.deduct_session(membership_id, 1)

# 增加积分
db.memberships.add_points(membership_id, 20)
```

### 商品管理

```python
# 创建商品
product = db.products.get_or_create(
    "洗发水", category="日用品", price=50
)

# 更新库存
db.products.update_stock(product.id, quantity_change=-5)

# 查询低库存商品
low_stock = db.products.get_low_stock()
```

## 5. 下一步

- 📖 **深入学习**：查看 `README.md` 了解所有功能
- 💼 **业务场景**：运行 `gym_example.py` 或 `hair_salon_example.py`
- 🔧 **功能示例**：运行 `entity_repos_example.py`、`business_repos_example.py` 等
- 📚 **架构设计**：阅读 `design/database.md` 了解设计原理

## 6. 常见问题

### Q: 数据库文件在哪里？

A: 默认在 `data/` 目录下，文件名由连接 URL 指定。

### Q: 如何查看数据库内容？

A: 使用 SQLite 命令行工具：
```bash
sqlite3 data/quickstart.db
.tables
SELECT * FROM service_records;
```

### Q: 支持哪些数据库？

A: 支持 SQLite（开发）和 PostgreSQL（生产），根据连接 URL 自动适配。

### Q: 如何切换数据库？

A: 修改连接 URL：
```python
# SQLite
db = DatabaseManager("sqlite:///data/store.db")

# PostgreSQL
db = DatabaseManager("postgresql://user:pass@localhost/dbname")
```

---

**🎉 恭喜！您已经掌握了 database 模块的基本用法。现在可以开始构建您的业务应用了！**
