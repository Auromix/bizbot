# 数据库扩展功能使用指南

## 一、新增功能概述

### 1. 外部引流提成系统 (ReferralChannel)
支持管理外部引流渠道（如美团、大众点评、合作门店等），实现精准的提成统计和渠道分析。

### 2. JSON扩展字段 (extra_data)
为关键业务表添加了`extra_data` JSON字段，支持灵活的字段扩展，无需修改数据库结构。

### 3. 插件数据表 (PluginData)
完全自定义的扩展机制，支持插件化的数据存储，适合复杂的业务扩展需求。

## 二、外部引流提成系统使用

### 2.1 创建引流渠道

```python
from db.repository import DatabaseRepository

repo = DatabaseRepository()

# 创建外部引流渠道（如美团）
meituan_channel = repo.get_or_create_referral_channel(
    name="美团",
    channel_type="platform",  # platform/external/internal
    contact_info="美团商家后台",
    commission_rate=15.0  # 15%提成
)

# 创建个人合作方（如李哥）
ligo_channel = repo.get_or_create_referral_channel(
    name="李哥",
    channel_type="external",
    contact_info="微信：ligo123",
    commission_rate=10.0
)

# 创建内部员工渠道（用于区分员工提成）
employee_channel = repo.get_or_create_referral_channel(
    name="张师傅",
    channel_type="internal",
    commission_rate=20.0
)
```

### 2.2 在服务记录中使用引流渠道

```python
# 方式1：直接指定渠道ID
record_data = {
    "customer_name": "王老师",
    "service_or_product": "理疗",
    "date": "2024-01-28",
    "amount": 198,
    "commission": 20,
    "referral_channel_id": meituan_channel.id  # 使用渠道ID
}

# 方式2：使用commission_to（向后兼容，自动创建渠道）
record_data = {
    "customer_name": "王老师",
    "service_or_product": "理疗",
    "date": "2024-01-28",
    "amount": 198,
    "commission": 20,
    "commission_to": "李哥"  # 会自动创建或查找"李哥"渠道
}

repo.save_service_record(record_data, raw_message_id=1)
```

### 2.3 查询引流渠道

```python
# 获取所有活跃的外部渠道
external_channels = repo.get_referral_channels(
    channel_type="external",
    is_active=True
)

# 获取所有平台渠道
platform_channels = repo.get_referral_channels(
    channel_type="platform"
)

# 获取所有渠道（包括内部）
all_channels = repo.get_referral_channels()
```

### 2.4 统计渠道效果

```python
from sqlalchemy import func
from db.models import ServiceRecord, ReferralChannel

with repo.get_session() as session:
    # 统计各渠道的引流金额和提成
    stats = session.query(
        ReferralChannel.name,
        ReferralChannel.channel_type,
        func.sum(ServiceRecord.amount).label('total_revenue'),
        func.sum(ServiceRecord.commission_amount).label('total_commission'),
        func.count(ServiceRecord.id).label('record_count')
    ).join(
        ServiceRecord, ServiceRecord.referral_channel_id == ReferralChannel.id
    ).group_by(
        ReferralChannel.id, ReferralChannel.name, ReferralChannel.channel_type
    ).all()
    
    for stat in stats:
        print(f"{stat.name} ({stat.channel_type}): "
              f"收入¥{stat.total_revenue}, "
              f"提成¥{stat.total_commission}, "
              f"记录数{stat.record_count}")
```

## 三、JSON扩展字段使用

### 3.1 Employee扩展字段

```python
# 保存员工时添加扩展数据
employee = repo.get_or_create_employee("张师傅", "zhang_sf")
employee.extra_data = {
    "department": "理疗部",
    "skill_level": 5,
    "certifications": ["按摩师资格证", "理疗师资格证"],
    "hire_date": "2023-01-01"
}

# 或者直接设置
employee.set_extra("department", "理疗部")
employee.set_extra("skill_level", 5)

# 读取扩展数据
department = employee.get_extra("department")
skill_level = employee.get_extra("skill_level", default=1)
```

### 3.2 Customer扩展字段

```python
# 为顾客添加VIP等级、来源渠道等
customer = repo.get_or_create_customer("王老师")
customer.extra_data = {
    "vip_level": "gold",
    "source": "美团",
    "tags": ["重要客户", "长期会员"],
    "preferred_service": "理疗"
}

# 查询VIP客户
with repo.get_session() as session:
    vip_customers = session.query(Customer).filter(
        Customer.extra_data['vip_level'].astext == 'gold'
    ).all()
```

### 3.3 Product扩展字段

```python
# 为商品添加批次、供应商等信息
product = repo.get_or_create_product("泡脚液")
product.extra_data = {
    "supplier": "XX供应商",
    "batch_number": "B20240101",
    "production_date": "2024-01-01",
    "expiry_date": "2025-01-01",
    "cost_price": 15.0
}
```

### 3.4 ServiceRecord扩展字段

```python
# 在服务记录中添加扩展信息
record_data = {
    "customer_name": "王老师",
    "service_or_product": "理疗",
    "date": "2024-01-28",
    "amount": 198,
    "extra_data": {
        "appointment_id": "APT001",
        "duration": 60,  # 服务时长（分钟）
        "room": "A101",
        "special_notes": "需要重点按摩腰部"
    }
}
```

## 四、插件数据表使用

插件数据表适合需要完全自定义扩展的场景，特别是需要跨表关联或复杂查询的场景。

### 4.1 保存插件数据

```python
# 示例：为理发店插件保存发型师技能标签
repo.save_plugin_data(
    plugin_name="hair_salon",
    entity_type="employee",
    entity_id=employee.id,
    data_key="skills",
    data_value=["剪发", "染发", "烫发", "造型"]
)

# 保存会员积分历史
repo.save_plugin_data(
    plugin_name="membership_points",
    entity_type="customer",
    entity_id=customer.id,
    data_key="points_history",
    data_value=[
        {"date": "2024-01-28", "points": 100, "reason": "消费满200元"},
        {"date": "2024-01-25", "points": 50, "reason": "签到"}
    ]
)
```

### 4.2 读取插件数据

```python
# 读取单个数据键
skills = repo.get_plugin_data(
    plugin_name="hair_salon",
    entity_type="employee",
    entity_id=employee.id,
    data_key="skills"
)

# 读取所有数据键
all_data = repo.get_plugin_data(
    plugin_name="membership_points",
    entity_type="customer",
    entity_id=customer.id
)
# 返回: {"points_history": [...], "total_points": 150, ...}
```

### 4.3 删除插件数据

```python
# 删除单个数据键
repo.delete_plugin_data(
    plugin_name="hair_salon",
    entity_type="employee",
    entity_id=employee.id,
    data_key="skills"
)

# 删除所有插件数据
repo.delete_plugin_data(
    plugin_name="hair_salon",
    entity_type="employee",
    entity_id=employee.id
)
```

## 五、快速接入新门店类型

### 5.1 理发店示例

```python
# 1. 扩展Employee模型（使用extra_data）
def setup_hair_salon_employee(repo, employee_name):
    employee = repo.get_or_create_employee(employee_name)
    employee.extra_data = {
        "position": "发型师",  # 职位
        "skills": ["剪发", "染发", "烫发"],
        "level": "高级",  # 等级
        "commission_rate_by_service": {
            "剪发": 30,  # 剪发提成30%
            "染发": 25,
            "烫发": 20
        }
    }
    return employee

# 2. 创建引流渠道
meituan_channel = repo.get_or_create_referral_channel(
    name="美团",
    channel_type="platform",
    commission_rate=15.0
)

dianping_channel = repo.get_or_create_referral_channel(
    name="大众点评",
    channel_type="platform",
    commission_rate=12.0
)

# 3. 保存服务记录
record_data = {
    "customer_name": "张女士",
    "service_or_product": "剪发",
    "date": "2024-01-28",
    "amount": 80,
    "referral_channel_id": meituan_channel.id,
    "extra_data": {
        "service_duration": 30,  # 服务时长
        "stylist_level": "高级"
    }
}
```

### 5.2 健身房示例

```python
# 1. 使用插件数据表管理会员卡类型和权益
def setup_gym_membership(repo, customer_name, card_type):
    customer = repo.get_or_create_customer(customer_name)
    
    # 使用插件数据存储会员详细信息
    repo.save_plugin_data(
        plugin_name="gym",
        entity_type="customer",
        entity_id=customer.id,
        data_key="membership_info",
        data_value={
            "card_type": card_type,  # 年卡/季卡/月卡
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "remaining_days": 365,
            "access_zones": ["器械区", "瑜伽室", "游泳池"],
            "personal_trainer": "李教练"
        }
    )
    
    return customer

# 2. 管理私教提成
trainer_channel = repo.get_or_create_referral_channel(
    name="李教练",
    channel_type="internal",
    commission_rate=40.0  # 私教提成40%
)

# 3. 保存私教课程记录
record_data = {
    "customer_name": "王先生",
    "service_or_product": "私教课程",
    "date": "2024-01-28",
    "amount": 300,
    "referral_channel_id": trainer_channel.id,
    "extra_data": {
        "course_type": "力量训练",
        "duration": 60,
        "trainer": "李教练"
    }
}
```

## 六、最佳实践

### 6.1 选择扩展方式

- **简单字段扩展**：使用`extra_data` JSON字段
  - 适合：部门、等级、标签等简单属性
  - 优点：无需额外表，查询方便
  - 缺点：不适合复杂查询和关联

- **复杂扩展**：使用`PluginData`表
  - 适合：历史记录、复杂结构、跨表关联
  - 优点：完全灵活，支持复杂查询
  - 缺点：需要额外的表查询

- **业务扩展**：使用`ReferralChannel`等业务表
  - 适合：需要统计、分析的业务实体
  - 优点：结构化，支持复杂查询和统计
  - 缺点：需要修改数据库结构

### 6.2 数据迁移

如果从旧系统迁移，可以：

```python
# 将旧的commission_to字符串迁移到ReferralChannel
with repo.get_session() as session:
    # 查找所有使用commission_to的记录
    records = session.query(ServiceRecord).filter(
        ServiceRecord.commission_to.isnot(None),
        ServiceRecord.referral_channel_id.is_(None)
    ).all()
    
    for record in records:
        # 创建或获取渠道
        channel = repo.get_or_create_referral_channel(
            name=record.commission_to,
            channel_type="external",
            session=session
        )
        # 更新记录
        record.referral_channel_id = channel.id
        session.commit()
```

### 6.3 性能优化

- `extra_data`字段：适合频繁读取的场景，数据量小
- `PluginData`表：适合需要索引和复杂查询的场景
- 考虑在`extra_data`中存储常用字段，在`PluginData`中存储历史数据

## 七、总结

新的扩展机制提供了三个层次的扩展能力：

1. **业务层扩展**：ReferralChannel表，支持外部引流提成管理
2. **字段层扩展**：extra_data JSON字段，快速添加自定义属性
3. **插件层扩展**：PluginData表，完全自定义的数据存储

这三种方式可以组合使用，满足不同复杂度的业务需求，使得系统能够快速适配各种类型的服务业门店。

