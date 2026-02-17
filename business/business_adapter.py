"""业务逻辑适配器接口 - 用于解耦业务逻辑"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BusinessLogicAdapter(ABC):
    """
    业务逻辑适配器抽象基类
    
    新项目只需要实现这个接口，就可以替换业务逻辑
    而不需要修改 Pipeline、Bot 等核心代码
    """
    
    @abstractmethod
    def save_business_record(self, record_type: str, data: Dict[str, Any], 
                            raw_message_id: int, confirmed: bool) -> int:
        """
        保存业务记录
        
        Args:
            record_type: 记录类型（由 LLM 解析返回）
            data: 记录数据
            raw_message_id: 原始消息ID
            confirmed: 是否已确认
            
        Returns:
            保存的记录ID
        """
        pass
    
    @abstractmethod
    def get_records_by_date(self, target_date, record_types: Optional[list] = None) -> list:
        """
        按日期查询记录
        
        Args:
            target_date: 目标日期
            record_types: 记录类型列表，None 表示查询所有类型
            
        Returns:
            记录列表
        """
        pass
    
    @abstractmethod
    def generate_summary(self, summary_type: str, **kwargs) -> str:
        """
        生成汇总报告
        
        Args:
            summary_type: 汇总类型（daily/monthly/inventory/membership等）
            **kwargs: 其他参数
            
        Returns:
            汇总文本
        """
        pass
    
    @abstractmethod
    def handle_command(self, command: str, args: list, context: Dict[str, Any]) -> str:
        """
        处理命令
        
        Args:
            command: 命令名称
            args: 命令参数
            context: 上下文信息（如 group_id）
            
        Returns:
            命令响应文本
        """
        pass

