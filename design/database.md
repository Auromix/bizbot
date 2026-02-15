# 数据库技术架构与内容设计

## 一、技术架构

### 1.1 架构概览

本系统采用 **Repository 模式** 和 **ORM 框架**，提供统一的数据库访问接口，支持多种数据库引擎。

```mermaid
graph TB
    A[业务逻辑层] --> B[Repository层]
    B --> C[BaseRepository<br/>基础访问层]
    B --> D[DatabaseRepository<br/>业务访问层]
    C --> E[SQLAlchemy ORM]
    D --> E
    E --> F{数据库引擎}
    F -->|同步| G[SQLite]
    F -->|异步| H[PostgreSQL]
    
    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#ffe1f5
    style D fill:#ffe1f5
    style E fill:#e1ffe1
    style F fill:#f5e1ff
```

### 1.2 技术栈

- **ORM框架**: SQLAlchemy
- **数据库支持**:
  - SQLite（同步引擎，开发/小规模使用）
  - PostgreSQL（异步引擎，生产环境推荐）
- **设计模式**: Repository 模式
- **架构层次**: 两层 Repository 设计

### 1.3 架构层次说明

#### BaseRepository（基础访问层）
- **职责**: 提供通用的数据库操作，不包含业务逻辑
- **功能**:
  - 数据库连接管理
  - 表创建（`create_tables`）
  - 会话管理（`get_session`）
  - 原始SQL执行（`execute_raw_sql`）

#### DatabaseRepository（业务访问层）
- **职责**: 封装业务相关的数据库操作
- **功能**:
  - 业务实体的CRUD操作
  - 关联关系处理
  - 业务逻辑封装（如自动创建关联实体）

### 1.4 数据库引擎选择

系统根据数据库URL自动选择引擎类型：

```python
# SQLite（同步）
database_url = "sqlite:///path/to/db.db"
# 使用同步引擎，适合开发和小规模使用

# PostgreSQL（异步）
database_url = "postgresql://user:pass@host/db"
# 自动转换为异步引擎，适合生产环境
```

## 二、数据模型设计

### 2.1 模型概览

系统包含 **13个核心数据模型**，分为以下类别：

```mermaid
graph LR
    A[数据模型] --> B[基础实体]
    A --> C[业务记录]
    A --> D[辅助数据]
    A --> E[扩展机制]
    
    B --> B1[Employee<br/>员工]
    B --> B2[Customer<br/>顾客]
    B --> B3[ServiceType<br/>服务类型]
    B --> B4[Product<br/>商品]
    B --> B5[ReferralChannel<br/>引流渠道]
    
    C --> C1[ServiceRecord<br/>服务记录]
    C --> C2[ProductSale<br/>商品销售]
    C --> C3[Membership<br/>会员卡]
    
    D --> D1[RawMessage<br/>原始消息]
    D --> D2[InventoryLog<br/>库存变动]
    D --> D3[Correction<br/>修正记录]
    D --> D4[DailySummary<br/>每日汇总]
    
    E --> E1[PluginData<br/>插件数据]
    
    style B fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#ffe1f5
    style E fill:#e1ffe1
```

### 2.2 实体关系图（ERD）

```mermaid
erDiagram
    Employee ||--o{ ServiceRecord : "服务员工"
    Employee ||--o{ ServiceRecord : "记录员"
    Employee ||--o{ ProductSale : "记录员"
    
    Customer ||--o{ Membership : "拥有"
    Customer ||--o{ ServiceRecord : "消费"
    Customer ||--o{ ProductSale : "购买"
    
    ServiceType ||--o{ ServiceRecord : "类型"
    
    ReferralChannel ||--o{ ServiceRecord : "引流渠道"
    
    Membership ||--o{ ServiceRecord : "使用"
    
    Product ||--o{ ProductSale : "销售"
    Product ||--o{ InventoryLog : "库存变动"
    
    RawMessage ||--o{ ServiceRecord : "来源"
    RawMessage ||--o{ ProductSale : "来源"
    RawMessage ||--o{ Correction : "修正"
    
    Employee {
        int id PK
        string name
        string wechat_nickname
        string role
        decimal commission_rate
        json extra_data
    }
    
    Customer {
        int id PK
        string name
        string phone
        text notes
        json extra_data
    }
    
    Membership {
        int id PK
        int customer_id FK
        string card_type
        decimal total_amount
        decimal balance
        int remaining_sessions
        date expires_at
        int points
        json extra_data
    }
    
    ServiceType {
        int id PK
        string name UK
        decimal default_price
        string category
    }
    
    ReferralChannel {
        int id PK
        string name
        string channel_type
        decimal commission_rate
        string commission_type
    }
    
    ServiceRecord {
        int id PK
        int customer_id FK
        int employee_id FK
        int recorder_id FK
        int service_type_id FK
        int referral_channel_id FK
        int membership_id FK
        int raw_message_id FK
        date service_date
        decimal amount
        decimal commission_amount
        decimal net_amount
        json extra_data
    }
    
    Product {
        int id PK
        string name
        string category
        decimal unit_price
        int stock_quantity
        json extra_data
    }
    
    ProductSale {
        int id PK
        int product_id FK
        int customer_id FK
        int recorder_id FK
        int raw_message_id FK
        date sale_date
        int quantity
        decimal total_amount
    }
    
    InventoryLog {
        int id PK
        int product_id FK
        string change_type
        int quantity_change
        int quantity_after
    }
    
    RawMessage {
        int id PK
        string wechat_msg_id UK
        string sender_nickname
        text content
        datetime timestamp
        string parse_status
        json parse_result
    }
    
    PluginData {
        int id PK
        string plugin_name
        string entity_type
        int entity_id
        string data_key
        json data_value
    }
```

### 2.3 核心表设计

#### 2.3.1 基础实体表

##### Employee（员工表）
- **用途**: 存储员工基本信息
- **关键字段**:
  - `name`: 员工姓名
  - `wechat_nickname`: 微信昵称（用于识别）
  - `role`: 角色（staff/manager/bot）
  - `commission_rate`: 提成率（0-100）
  - `extra_data`: JSON扩展字段（部门、技能等级等）

##### Customer（顾客表）
- **用途**: 存储顾客基本信息
- **关键字段**:
  - `name`: 顾客姓名
  - `phone`: 联系电话
  - `notes`: 备注信息
  - `extra_data`: JSON扩展字段（VIP等级、来源渠道、标签等）

##### ServiceType（服务类型表）
- **用途**: 服务类型字典表
- **关键字段**:
  - `name`: 服务类型名称（唯一）
  - `default_price`: 默认价格
  - `category`: 服务类别

##### Product（商品表）
- **用途**: 存储商品信息
- **关键字段**:
  - `name`: 商品名称
  - `category`: 商品类别
  - `unit_price`: 单价
  - `stock_quantity`: 库存数量
  - `low_stock_threshold`: 低库存阈值
  - `extra_data`: JSON扩展字段（批次、供应商等）

##### ReferralChannel（引流渠道表）
- **用途**: 管理外部引流渠道，支持精准提成统计
- **关键字段**:
  - `name`: 渠道名称（如：美团、大众点评、李哥）
  - `channel_type`: 渠道类型（internal/external/platform）
  - `commission_rate`: 默认提成率
  - `commission_type`: 提成类型（percentage/fixed）

#### 2.3.2 业务记录表

##### ServiceRecord（服务记录表）⭐ 核心业务表
- **用途**: 记录服务消费，是系统的核心业务表
- **关键字段**:
  - `customer_id`: 顾客ID
  - `employee_id`: 服务员工ID
  - `recorder_id`: 记录员ID
  - `service_type_id`: 服务类型ID
  - `referral_channel_id`: 引流渠道ID（新增）
  - `membership_id`: 使用的会员卡ID
  - `service_date`: 服务日期
  - `amount`: 服务金额
  - `commission_amount`: 提成金额
  - `net_amount`: 净收入（金额-提成）
  - `confirmed`: 是否已确认
  - `extra_data`: JSON扩展字段（预约ID、服务时长等）

##### ProductSale（商品销售表）
- **用途**: 记录商品销售
- **关键字段**:
  - `product_id`: 商品ID
  - `customer_id`: 顾客ID
  - `recorder_id`: 记录员ID
  - `sale_date`: 销售日期
  - `quantity`: 销售数量
  - `total_amount`: 总金额

##### Membership（会员卡表）
- **用途**: 存储会员卡信息
- **关键字段**:
  - `customer_id`: 顾客ID
  - `card_type`: 卡类型（如：理疗卡、头疗卡）
  - `total_amount`: 总金额
  - `balance`: 余额
  - `remaining_sessions`: 剩余次数
  - `expires_at`: 到期日期
  - `points`: 积分

#### 2.3.3 辅助数据表

##### RawMessage（原始消息表）
- **用途**: 存储从微信群聊接收的原始消息，用于追溯和审计
- **关键字段**:
  - `wechat_msg_id`: 微信消息ID（唯一，用于去重）
  - `sender_nickname`: 发送者昵称
  - `content`: 消息内容
  - `timestamp`: 消息时间戳
  - `parse_status`: 解析状态（pending/parsed/failed/ignored）
  - `parse_result`: 解析结果（JSON）

##### InventoryLog（库存变动表）
- **用途**: 记录库存变动情况
- **关键字段**:
  - `product_id`: 商品ID
  - `change_type`: 变动类型（sale/restock/adjustment）
  - `quantity_change`: 数量变动（正数入库，负数出库）
  - `quantity_after`: 变动后库存数量

##### Correction（修正记录表）
- **用途**: 记录对已保存业务记录的修正操作
- **关键字段**:
  - `original_record_type`: 原始记录类型（service_records/product_sales）
  - `original_record_id`: 原始记录ID
  - `correction_type`: 修正类型（date_change/amount_change/delete）
  - `old_value`: 旧值（JSON）
  - `new_value`: 新值（JSON）

##### DailySummary（每日汇总表）
- **用途**: 存储每日业务汇总数据，用于快速查询和报表
- **关键字段**:
  - `summary_date`: 汇总日期（唯一）
  - `total_service_revenue`: 服务总收入
  - `total_product_revenue`: 商品总收入
  - `total_commissions`: 总提成支出
  - `net_revenue`: 净收入
  - `service_count`: 服务记录数
  - `product_sale_count`: 商品销售记录数

#### 2.3.4 扩展机制表

##### PluginData（插件数据表）
- **用途**: 支持完全自定义的扩展数据存储，用于插件化的业务扩展
- **关键字段**:
  - `plugin_name`: 插件标识
  - `entity_type`: 实体类型（employee/customer/product等）
  - `entity_id`: 关联实体ID
  - `data_key`: 数据键
  - `data_value`: 数据值（JSON）
- **唯一约束**: (plugin_name, entity_type, entity_id, data_key)

## 三、扩展机制设计

### 3.1 三层扩展机制

系统提供了三个层次的扩展能力，满足不同复杂度的业务需求：

```mermaid
graph TB
    A[扩展需求] --> B{扩展复杂度}
    B -->|简单字段| C[extra_data<br/>JSON字段]
    B -->|业务实体| D[业务表扩展<br/>ReferralChannel等]
    B -->|完全自定义| E[PluginData<br/>插件数据表]
    
    C --> C1[适用场景<br/>部门、等级、标签等]
    D --> D1[适用场景<br/>引流渠道、统计需求]
    E --> E1[适用场景<br/>历史记录、复杂结构]
    
    style C fill:#e1f5ff
    style D fill:#fff4e1
    style E fill:#ffe1f5
```

### 3.2 JSON扩展字段（extra_data）

**适用场景**: 简单字段扩展

- **支持的表**:** Employee, Customer, Membership, Product, ServiceRecord
- **使用方式**: 直接存储JSON数据
- **优点**: 无需修改数据库结构，查询方便
- **缺点**: 不适合复杂查询和关联

**示例**:
```python
# Employee扩展：部门、技能等级
employee.extra_data = {
    "department": "理疗部",
    "skill_level": 5,
    "certifications": ["按摩师资格证"]
}

# Customer扩展：VIP等级、来源渠道
customer.extra_data = {
    "vip_level": "gold",
    "source": "美团",
    "tags": ["重要客户"]
}
```

### 3.3 业务表扩展

**适用场景**: 需要统计、分析的业务实体

- **示例**: ReferralChannel（引流渠道表）
- **优点**: 结构化，支持复杂查询和统计
- **缺点**: 需要修改数据库结构

**示例**:
```python
# 创建引流渠道
channel = repo.get_or_create_referral_channel(
    name="美团",
    channel_type="platform",
    commission_rate=15.0
)

# 在服务记录中使用
service_record.referral_channel_id = channel.id
```

### 3.4 插件数据表（PluginData）

**适用场景**: 完全自定义的扩展需求

- **特点**: 通过(plugin_name, entity_type, entity_id, data_key)唯一约束
- **优点**: 完全灵活，支持复杂查询
- **缺点**: 需要额外的表查询

**示例**:
```python
# 保存插件数据
repo.save_plugin_data(
    plugin_name="hair_salon",
    entity_type="employee",
    entity_id=employee.id,
    data_key="skills",
    data_value=["剪发", "染发", "烫发"]
)

# 读取插件数据
skills = repo.get_plugin_data(
    plugin_name="hair_salon",
    entity_type="employee",
    entity_id=employee.id,
    data_key="skills"
)
```

## 四、数据流转设计

### 4.1 消息处理流程

```mermaid
sequenceDiagram
    participant WX as 微信群聊
    participant Parser as 消息解析器
    participant Repo as DatabaseRepository
    participant DB as 数据库
    
    WX->>Parser: 接收原始消息
    Parser->>Repo: save_raw_message()
    Repo->>DB: 保存RawMessage
    DB-->>Repo: 返回msg_id
    
    Parser->>Parser: 解析业务数据
    Parser->>Repo: save_service_record()
    Repo->>DB: 自动创建关联实体
    Repo->>DB: 保存ServiceRecord
    DB-->>Repo: 返回record_id
    
    Parser->>Repo: update_parse_status()
    Repo->>DB: 更新解析状态
```

### 4.2 服务记录创建流程

```mermaid
flowchart TD
    A[接收服务记录数据] --> B{检查关联实体}
    B -->|不存在| C[自动创建Customer]
    B -->|不存在| D[自动创建ServiceType]
    B -->|不存在| E[自动创建Employee]
    B -->|存在| F[使用现有实体]
    
    C --> G[处理引流渠道]
    D --> G
    E --> G
    F --> G
    
    G --> H{是否有referral_channel_id?}
    H -->|有| I[使用指定渠道]
    H -->|无| J{是否有commission_to?}
    J -->|有| K[自动创建/查找渠道]
    J -->|无| L[不关联渠道]
    
    I --> M[创建ServiceRecord]
    K --> M
    L --> M
    
    M --> N[计算net_amount]
    N --> O[保存到数据库]
    
    style A fill:#e1f5ff
    style M fill:#fff4e1
    style O fill:#e1ffe1
```

## 五、关键设计特点

### 5.1 自动关联实体创建

系统在保存业务记录时，会自动创建不存在的关联实体：

- **Customer**: 根据姓名自动创建
- **ServiceType**: 根据名称自动创建
- **Employee**: 根据姓名或微信昵称自动创建
- **ReferralChannel**: 根据名称自动创建（向后兼容）

### 5.2 向后兼容设计

- **commission_to字段**: 保留字符串字段，同时推荐使用`referral_channel_id`
- **可选字段**: 新增字段都设为可选，不影响现有数据
- **渐进式升级**: 支持新旧系统并存

### 5.3 数据追溯能力

- **RawMessage关联**: 所有业务记录都可以追溯到原始消息
- **解析状态跟踪**: 记录消息的解析状态和结果
- **修正记录**: 记录所有数据修正操作

### 5.4 灵活的扩展机制

- **三层扩展**: JSON字段 + 业务表 + 插件表
- **无需修改结构**: 通过扩展机制快速适配新业务
- **插件化支持**: PluginData表支持完全自定义扩展

## 六、数据库操作示例

### 6.1 基础操作

```python
from db.repository import DatabaseRepository

# 初始化
repo = DatabaseRepository()

# 创建表
repo.create_tables()

# 获取会话
session = repo.get_session()
```

### 6.2 业务操作

```python
# 保存服务记录（自动创建关联实体）
record_data = {
    "customer_name": "王老师",
    "service_or_product": "理疗",
    "date": "2024-01-28",
    "amount": 198,
    "referral_channel_id": channel.id
}
record_id = repo.save_service_record(record_data, raw_message_id=1)

# 查询指定日期的记录
from datetime import date
records = repo.get_records_by_date(date(2024, 1, 28))
```

### 6.3 扩展数据操作

```python
# 使用JSON扩展字段
employee = repo.get_or_create_employee("张师傅")
employee.extra_data = {"department": "理疗部", "skill_level": 5}

# 使用插件数据表
repo.save_plugin_data(
    plugin_name="hair_salon",
    entity_type="employee",
    entity_id=employee.id,
    data_key="skills",
    data_value=["剪发", "染发"]
)
```

## 七、总结

### 7.1 架构优势

1. **统一接口**: Repository模式提供统一的数据库访问接口
2. **多引擎支持**: 自动适配SQLite和PostgreSQL
3. **业务封装**: DatabaseRepository封装业务逻辑，简化使用
4. **扩展灵活**: 三层扩展机制满足不同需求

### 7.2 设计亮点

1. **自动关联**: 自动创建关联实体，简化业务代码
2. **向后兼容**: 保留旧字段，支持渐进式升级
3. **数据追溯**: 完整的消息和修正记录追溯
4. **扩展机制**: JSON字段 + 业务表 + 插件表三层扩展

### 7.3 适用场景

- ✅ 服务业门店（理疗店、理发店、健身房等）
- ✅ 需要提成管理的场景
- ✅ 需要会员卡管理的场景
- ✅ 需要库存管理的场景
- ✅ 需要快速扩展的业务场景

