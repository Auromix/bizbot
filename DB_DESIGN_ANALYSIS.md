# 数据库设计分析报告 - 服务业门店共性需求覆盖评估

## 一、当前功能覆盖情况

### ✅ 已覆盖的功能

#### 1. 员工管理 (Employee)
- ✅ 基本信息：姓名、微信昵称、微信ID
- ✅ 角色管理：role字段（staff/manager/bot）
- ✅ 提成率：commission_rate字段
- ✅ 状态管理：is_active字段
- ✅ 关联关系：服务记录、商品销售记录

**评估**：基础功能完整，但缺少：
- 部门/岗位管理
- 权限管理
- 员工等级/技能标签
- 多角色支持

#### 2. 会员系统 (Customer, Membership)
- ✅ 顾客基本信息：姓名、电话、备注
- ✅ 会员卡管理：卡类型、总金额、余额
- ✅ 次数管理：remaining_sessions字段
- ✅ 状态管理：is_active字段
- ✅ 关联关系：服务记录、商品销售

**评估**：基础功能完整，但缺少：
- 会员等级/积分系统
- 会员权益管理
- 会员卡有效期
- 会员推荐关系
- 会员标签/分组

#### 3. 库存管理 (Product, InventoryLog)
- ✅ 商品基本信息：名称、类别、单价
- ✅ 库存数量：stock_quantity字段
- ✅ 库存预警：low_stock_threshold字段
- ✅ 库存变动记录：InventoryLog表
- ✅ 变动类型：sale/restock/adjustment

**评估**：基础功能完整，但缺少：
- 批次管理（生产日期、保质期）
- 多仓库/多门店支持
- 库存成本核算
- 库存盘点功能
- 供应商管理

#### 4. 服务记录 (ServiceRecord)
- ✅ 完整的服务记录：顾客、员工、服务类型、日期、金额
- ✅ 提成记录：commission_amount、commission_to
- ✅ 净收入计算：net_amount
- ✅ 会员卡关联：membership_id
- ✅ 确认状态：confirmed字段

**评估**：功能较为完整

### ⚠️ 部分覆盖的功能

#### 1. 外部引流提成
**当前实现**：
- ServiceRecord表中有`commission_to`字段（String类型）
- 可以记录提成对象，但只是简单的字符串

**问题**：
- ❌ 没有专门的引流渠道表（ReferralChannel）
- ❌ 无法区分内部员工提成和外部引流提成
- ❌ 无法管理外部合作方（美团、大众点评、其他门店等）
- ❌ 无法统计各渠道的引流效果
- ❌ 无法设置不同渠道的提成规则

**影响**：
- 理发店、健身房等需要区分内部员工和外部引流的场景无法准确管理
- 无法分析各引流渠道的ROI

### ❌ 缺失的功能

#### 1. 扩展性机制
- ❌ 没有JSON扩展字段
- ❌ 没有插件表（PluginData）支持自定义字段
- ❌ 没有版本化的模型扩展机制

#### 2. 多门店支持
- ❌ 所有表都没有门店ID字段
- ❌ 无法支持连锁店场景

#### 3. 财务相关
- ❌ 没有收支分类（收入/支出）
- ❌ 没有成本核算
- ❌ 没有财务报表

#### 4. 预约系统
- ❌ 没有预约表（Appointment）
- ❌ 无法管理服务预约

## 二、改进方案

### 方案1：增强外部引流提成系统（推荐）

#### 1.1 创建引流渠道表

```python
class ReferralChannel(Base):
    """引流渠道表"""
    __tablename__ = "referral_channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # 渠道名称：美团、大众点评、李哥等
    channel_type = Column(String(20), nullable=False)  # internal/external/platform
    contact_info = Column(String(200))  # 联系方式
    commission_rate = Column(DECIMAL(5, 2))  # 默认提成率
    commission_type = Column(String(20), default="percentage")  # percentage/fixed
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service_records = relationship("ServiceRecord", back_populates="referral_channel")
```

#### 1.2 修改ServiceRecord表

```python
# 在ServiceRecord中添加
referral_channel_id = Column(Integer, ForeignKey("referral_channels.id"))
referral_channel = relationship("ReferralChannel", back_populates="service_records")

# 保留commission_to字段作为向后兼容，但推荐使用referral_channel_id
```

### 方案2：增强扩展性机制

#### 2.1 添加JSON扩展字段

为关键表添加`extra_data` JSON字段：

```python
# 在Employee、Customer、Product、ServiceRecord等表中添加
extra_data = Column(JSON, default={})
```

#### 2.2 创建插件数据表

```python
class PluginData(Base):
    """插件数据表 - 支持自定义扩展"""
    __tablename__ = "plugin_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_name = Column(String(50), nullable=False)  # 插件标识
    entity_type = Column(String(50), nullable=False)  # employee/customer/product等
    entity_id = Column(Integer, nullable=False)  # 关联实体ID
    data_key = Column(String(100), nullable=False)  # 数据键
    data_value = Column(JSON)  # 数据值
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('plugin_name', 'entity_type', 'entity_id', 'data_key', 
                        name='uq_plugin_data'),
    )
```

### 方案3：增强会员系统

```python
class MembershipType(Base):
    """会员卡类型配置表"""
    __tablename__ = "membership_types"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    card_type = Column(String(50))  # 卡类型标识
    default_amount = Column(DECIMAL(10, 2))
    benefits = Column(JSON)  # 权益配置（折扣、积分倍数等）
    validity_days = Column(Integer)  # 有效期（天）
    is_active = Column(Boolean, default=True)

# 在Membership表中添加
membership_type_id = Column(Integer, ForeignKey("membership_types.id"))
expires_at = Column(Date)  # 到期日期
points = Column(Integer, default=0)  # 积分
```

### 方案4：增强库存管理

```python
class ProductBatch(Base):
    """商品批次表"""
    __tablename__ = "product_batches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(50))  # 批次号
    production_date = Column(Date)  # 生产日期
    expiry_date = Column(Date)  # 过期日期
    quantity = Column(Integer, nullable=False)  # 批次数量
    cost_price = Column(DECIMAL(10, 2))  # 成本价
    supplier = Column(String(100))  # 供应商
    created_at = Column(DateTime, default=datetime.utcnow)

# 在InventoryLog中添加
batch_id = Column(Integer, ForeignKey("product_batches.id"))
```

### 方案5：多门店支持

为所有核心表添加门店ID：

```python
# 在所有业务表中添加
store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)  # 支持单店时可为NULL

class Store(Base):
    """门店表"""
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 三、快速接入机制设计

### 3.1 模型扩展接口

创建模型扩展基类：

```python
class ExtensibleModelMixin:
    """可扩展模型混入类"""
    extra_data = Column(JSON, default={})
    
    def set_extra(self, key: str, value: Any):
        """设置扩展数据"""
        if not self.extra_data:
            self.extra_data = {}
        self.extra_data[key] = value
    
    def get_extra(self, key: str, default=None):
        """获取扩展数据"""
        return self.extra_data.get(key, default) if self.extra_data else default
```

### 3.2 业务适配器扩展点

在`BusinessLogicAdapter`中添加扩展方法：

```python
@abstractmethod
def extend_model(self, model_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """扩展模型数据（在保存前调用）"""
    pass

@abstractmethod
def get_custom_fields(self, model_name: str) -> List[Dict[str, Any]]:
    """获取自定义字段定义"""
    pass
```

### 3.3 配置驱动的字段扩展

在`BusinessConfig`中添加：

```python
@abstractmethod
def get_custom_model_fields(self) -> Dict[str, List[Dict[str, Any]]]:
    """
    返回自定义字段定义
    例如：
    {
        "Employee": [
            {"name": "department", "type": "string", "label": "部门"},
            {"name": "skill_level", "type": "integer", "label": "技能等级"}
        ],
        "Customer": [
            {"name": "vip_level", "type": "string", "label": "VIP等级"},
            {"name": "source", "type": "string", "label": "来源渠道"}
        ]
    }
    """
    pass
```

## 四、实施优先级

### 高优先级（必须）
1. ✅ **外部引流提成系统** - 创建ReferralChannel表，修改ServiceRecord
2. ✅ **JSON扩展字段** - 为关键表添加extra_data字段
3. ✅ **插件数据表** - 支持完全自定义的扩展

### 中优先级（推荐）
4. ⚠️ **会员系统增强** - 会员类型配置、积分、有效期
5. ⚠️ **库存批次管理** - 批次表、保质期管理
6. ⚠️ **多门店支持** - Store表和store_id字段

### 低优先级（可选）
7. ⚠️ **预约系统** - Appointment表
8. ⚠️ **财务模块** - 收支分类、成本核算

## 五、兼容性考虑

### 向后兼容
- 保留现有字段（如commission_to），新增字段设为可选
- 提供数据迁移脚本
- 在Repository层提供兼容方法

### 渐进式升级
- 新功能通过配置开关控制
- 支持新旧系统并存
- 提供功能启用/禁用机制

## 六、总结

### 当前状态
- ✅ **基础功能完整**：员工、会员、库存、服务记录都有基本实现
- ⚠️ **外部引流提成不完善**：只有字符串字段，无法管理渠道
- ❌ **扩展性不足**：缺乏灵活的扩展机制

### 改进后
- ✅ **完整的引流渠道管理**：支持内部员工、外部合作方、平台渠道
- ✅ **灵活的扩展机制**：JSON字段 + 插件表，支持任意扩展
- ✅ **快速接入能力**：新门店类型只需实现BusinessConfig和BusinessLogicAdapter

### 建议
1. **立即实施**：外部引流提成系统（高优先级）
2. **短期实施**：JSON扩展字段和插件表（提高扩展性）
3. **长期规划**：根据实际需求逐步添加其他功能

