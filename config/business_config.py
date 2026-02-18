"""
业务配置接口 - 支持可替换的业务配置

新项目可以实现自己的业务配置，替换默认配置。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BusinessConfig(ABC):
    """业务配置抽象基类"""
    
    @abstractmethod
    def get_service_types(self) -> List[Dict[str, Any]]:
        """获取服务类型列表"""
        pass
    
    @abstractmethod
    def get_llm_system_prompt(self) -> str:
        """获取 LLM 系统提示词"""
        pass
    
    @abstractmethod
    def get_noise_patterns(self) -> List[str]:
        """获取噪声消息模式"""
        pass
    
    @abstractmethod
    def get_service_keywords(self) -> List[str]:
        """获取服务关键词"""
        pass
    
    @abstractmethod
    def get_product_keywords(self) -> List[str]:
        """获取商品关键词"""
        pass
    
    @abstractmethod
    def get_membership_keywords(self) -> List[str]:
        """获取会员关键词"""
        pass


class TherapyStoreConfig(BusinessConfig):
    """健康理疗门店业务配置"""
    
    def get_service_types(self) -> List[Dict[str, Any]]:
        return [
            {"name": "头疗", "default_price": 30.0, "category": "therapy"},
            {"name": "理疗", "default_price": 198.0, "category": "therapy"},
            {"name": "泡脚", "default_price": 50.0, "category": "foot_bath"},
            {"name": "按摩", "default_price": 100.0, "category": "therapy"},
            {"name": "推拿", "default_price": 120.0, "category": "therapy"},
            {"name": "刮痧", "default_price": 80.0, "category": "therapy"},
            {"name": "拔罐", "default_price": 60.0, "category": "therapy"},
        ]
    
    def get_llm_system_prompt(self) -> str:
        return """你是一个健康理疗门店的数据录入助手。你的任务是从群聊消息中提取结构化业务数据。

## 门店业务类型
1. 理疗服务：员工为顾客做按摩/头疗/泡脚等，收取费用
2. 保健品销售：泡脚液等产品售卖
3. 会员卡：开卡充值
4. 修正指令：更正之前的错误记录

## 已知人员
- 顾客常以"X老师"称呼：段老师、姚老师、周老师、郑老师等
- 员工/记录员：通过昵称识别
- 提成人员：如"李哥"

## 消息格式特征
- 日期格式多样：1.28、1/28、1|28、1月28日 均表示1月28日
- 金额可能在服务前或后：头疗30 = 30头疗 = 头疗30元
- 可能一条消息包含多笔记录，用换行分隔
- "开卡1000" = 会员充值1000元
- "198-20李哥178" = 总价198，李哥提成20，实收178

## 输出要求
对每条消息，返回 JSON 数组（可能包含多笔记录）。每笔记录格式：

```json
{
  "type": "service" | "product_sale" | "membership" | "correction" | "noise",
  "date": "YYYY-MM-DD",
  "customer_name": "段老师",
  "service_or_product": "头疗",
  "amount": 30,
  "commission": null,
  "commission_to": null,
  "net_amount": 30,
  "notes": "",
  "confidence": 0.95,
  "correction_detail": null
}
```

如果无法识别或是闲聊/噪声，返回 `[{"type": "noise"}]`。

## 关键规则
1. 宁可返回 confidence 低值，也不要编造数据
2. 如果金额不确定，标注 confidence < 0.7
3. 一条消息可能包含多笔交易，全部提取
4. "体验" 通常意味着折扣价/试做价
5. 日期格式要统一转换为 YYYY-MM-DD
"""
    
    def get_noise_patterns(self) -> List[str]:
        return [
            r'^接$', r'^好$', r'^运$',
            r'^\[.*表情\]',
            r'^(好的|收到|谢谢|嗯|哦)',
            r'停在|掉头|车子',
            r'@\S+\s*(好的|收到)',
        ]
    
    def get_service_keywords(self) -> List[str]:
        return ['头疗', '理疗', '泡脚', '按摩', '推拿', '刮痧', '拔罐']
    
    def get_product_keywords(self) -> List[str]:
        return ['泡脚液', '保健品', '药品', '膏药']
    
    def get_membership_keywords(self) -> List[str]:
        return ['开卡', '充值', '会员']


# 全局业务配置实例（可以在 main.py 中替换）
business_config: BusinessConfig = TherapyStoreConfig()

